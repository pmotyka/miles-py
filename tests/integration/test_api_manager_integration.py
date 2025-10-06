"""
Integration tests for APIManager multi-source data collection.
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from services.api_manager import APIManager, APIManagerError
from clients.peloton_client import PelotonClient
from clients.strava_client import StravaClient, StravaRateLimitError, StravaAuthenticationError


class TestAPIManagerIntegration:
    """Integration tests for APIManager coordinating multiple data sources."""
    
    @pytest.fixture
    def mock_peloton_client(self):
        """Create a mock Peloton client."""
        client = Mock(spec=PelotonClient)
        client.authenticate = AsyncMock(return_value=True)
        client.get_cycling_workouts = AsyncMock(return_value=[
            {
                'id': 'peloton_1',
                'created_at': datetime(2024, 1, 15, tzinfo=timezone.utc),
                'type': 'cycling',
                'distance': 10.5,
                'duration': 30,
                'calories': 250
            }
        ])
        client.summarize_current_year_distance = Mock(return_value=125.5)
        return client
    
    @pytest.fixture
    def mock_strava_client(self):
        """Create a mock Strava client."""
        client = Mock(spec=StravaClient)
        client.authenticate = AsyncMock(return_value=True)
        client.get_athlete_stats = AsyncMock(return_value={
            'ytd_distance_miles': 89.3,
            'ytd_ride_count': 15,
            'ytd_moving_time_hours': 45.2
        })
        return client   
 
    @pytest.fixture
    def api_manager(self, mock_peloton_client, mock_strava_client):
        """Create APIManager with mock clients."""
        return APIManager(
            peloton_client=mock_peloton_client,
            strava_client=mock_strava_client,
            default_timeout=30,
            max_retries=2,
            base_retry_delay=0.1  # Faster for tests
        )
    
    @pytest.mark.asyncio
    async def test_fetch_all_data_success(self, api_manager, mock_peloton_client, mock_strava_client):
        """Test successful data collection from both sources."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
        
        result = await api_manager.fetch_all_data(start_date, end_date)
        
        # Verify both sources were called
        mock_peloton_client.authenticate.assert_called_once()
        mock_peloton_client.get_cycling_workouts.assert_called_once_with(start_date, end_date)
        mock_strava_client.authenticate.assert_called_once()
        mock_strava_client.get_athlete_stats.assert_called_once()
        
        # Verify result structure
        assert 'peloton_data' in result
        assert 'strava_data' in result
        assert 'successful_sources' in result
        assert 'failed_sources' in result
        assert 'fetch_timestamp' in result
        
        # Verify successful sources
        assert 'peloton' in result['successful_sources']
        assert 'strava' in result['successful_sources']
        assert len(result['failed_sources']) == 0
        
        # Verify data content
        assert result['peloton_data']['total_distance_miles'] == 125.5
        assert result['strava_data']['total_distance_miles'] == 89.3 
   
    @pytest.mark.asyncio
    async def test_graceful_degradation_peloton_fails(self, mock_peloton_client, mock_strava_client):
        """Test graceful degradation when Peloton API fails."""
        # Make Peloton authentication fail
        mock_peloton_client.authenticate.side_effect = Exception("Peloton auth failed")
        
        api_manager = APIManager(
            peloton_client=mock_peloton_client,
            strava_client=mock_strava_client,
            max_retries=1,
            base_retry_delay=0.1
        )
        
        result = await api_manager.fetch_all_data()
        
        # Should still succeed with Strava data
        assert 'strava' in result['successful_sources']
        assert 'peloton' in result['failed_sources']
        assert result['strava_data'] is not None
        assert result['peloton_data'] is None
        
        # Check API status
        status = api_manager.get_api_status()
        assert not status['api_status']['peloton']['available']
        assert status['api_status']['strava']['available']
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_strava_fails(self, mock_peloton_client, mock_strava_client):
        """Test graceful degradation when Strava API fails."""
        # Make Strava authentication fail
        mock_strava_client.authenticate.side_effect = StravaAuthenticationError("Invalid token")
        
        api_manager = APIManager(
            peloton_client=mock_peloton_client,
            strava_client=mock_strava_client,
            max_retries=1,
            base_retry_delay=0.1
        )
        
        result = await api_manager.fetch_all_data()
        
        # Should still succeed with Peloton data
        assert 'peloton' in result['successful_sources']
        assert 'strava' in result['failed_sources']
        assert result['peloton_data'] is not None
        assert result['strava_data'] is None    

    @pytest.mark.asyncio
    async def test_all_apis_fail_raises_error(self, mock_peloton_client, mock_strava_client):
        """Test that APIManagerError is raised when all APIs fail."""
        # Make both APIs fail
        mock_peloton_client.authenticate.side_effect = Exception("Peloton failed")
        mock_strava_client.authenticate.side_effect = Exception("Strava failed")
        
        api_manager = APIManager(
            peloton_client=mock_peloton_client,
            strava_client=mock_strava_client,
            max_retries=1,
            base_retry_delay=0.1
        )
        
        with pytest.raises(APIManagerError, match="All API sources failed"):
            await api_manager.fetch_all_data()
    
    @pytest.mark.asyncio
    async def test_retry_logic_with_transient_failures(self, mock_peloton_client, mock_strava_client):
        """Test retry logic with transient failures."""
        # Make Peloton fail twice then succeed
        mock_peloton_client.authenticate.side_effect = [
            Exception("Temporary failure"),
            Exception("Another failure"),
            True  # Success on third attempt
        ]
        
        api_manager = APIManager(
            peloton_client=mock_peloton_client,
            strava_client=mock_strava_client,
            max_retries=2,
            base_retry_delay=0.1
        )
        
        result = await api_manager.fetch_all_data()
        
        # Should eventually succeed
        assert 'peloton' in result['successful_sources']
        assert 'strava' in result['successful_sources']
        
        # Verify retry attempts
        assert mock_peloton_client.authenticate.call_count == 3 
   
    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_peloton_client, mock_strava_client):
        """Test timeout handling for API requests."""
        # Make Peloton take too long
        async def slow_auth():
            await asyncio.sleep(2)  # Longer than timeout
            return True
        
        mock_peloton_client.authenticate.side_effect = slow_auth
        
        api_manager = APIManager(
            peloton_client=mock_peloton_client,
            strava_client=mock_strava_client,
            default_timeout=0.5,  # Short timeout for test
            max_retries=1,
            base_retry_delay=0.1
        )
        
        result = await api_manager.fetch_all_data()
        
        # Should timeout on Peloton but succeed with Strava
        assert 'strava' in result['successful_sources']
        assert 'peloton' in result['failed_sources']
    
    @pytest.mark.asyncio
    async def test_strava_rate_limit_handling(self, mock_peloton_client, mock_strava_client):
        """Test handling of Strava rate limit errors."""
        # Make Strava hit rate limit then succeed
        mock_strava_client.authenticate.side_effect = [
            StravaRateLimitError("Rate limit exceeded"),
            True  # Success on retry
        ]
        
        api_manager = APIManager(
            peloton_client=mock_peloton_client,
            strava_client=mock_strava_client,
            max_retries=2,
            base_retry_delay=0.1
        )
        
        result = await api_manager.fetch_all_data()
        
        # Should eventually succeed after rate limit retry
        assert 'strava' in result['successful_sources']
        assert mock_strava_client.authenticate.call_count == 2
    
    @pytest.mark.asyncio
    async def test_sequential_api_calls(self, mock_peloton_client, mock_strava_client):
        """Test that API calls are made sequentially, not in parallel."""
        call_order = []
        
        async def track_peloton_auth():
            call_order.append('peloton_start')
            await asyncio.sleep(0.1)
            call_order.append('peloton_end')
            return True
        
        async def track_strava_auth():
            call_order.append('strava_start')
            await asyncio.sleep(0.1)
            call_order.append('strava_end')
            return True
        
        mock_peloton_client.authenticate.side_effect = track_peloton_auth
        mock_strava_client.authenticate.side_effect = track_strava_auth
        
        api_manager = APIManager(
            peloton_client=mock_peloton_client,
            strava_client=mock_strava_client
        )
        
        await api_manager.fetch_all_data()
        
        # Verify sequential execution (Peloton completes before Strava starts)
        assert call_order == ['peloton_start', 'peloton_end', 'strava_start', 'strava_end']
    
    @pytest.mark.asyncio
    async def test_connectivity_test(self, mock_peloton_client, mock_strava_client):
        """Test connectivity testing functionality."""
        api_manager = APIManager(
            peloton_client=mock_peloton_client,
            strava_client=mock_strava_client
        )
        
        results = await api_manager.test_connectivity()
        
        assert 'peloton' in results
        assert 'strava' in results
        assert results['peloton'] is True
        assert results['strava'] is True
        
        # Verify authentication was called for both
        mock_peloton_client.authenticate.assert_called_once()
        mock_strava_client.authenticate.assert_called_once() 
   
    @pytest.mark.asyncio
    async def test_api_status_tracking(self, mock_peloton_client, mock_strava_client):
        """Test API status tracking and error counting."""
        # Make Peloton fail multiple times
        mock_peloton_client.authenticate.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            Exception("Error 3")
        ]
        
        api_manager = APIManager(
            peloton_client=mock_peloton_client,
            strava_client=mock_strava_client,
            max_retries=2,
            base_retry_delay=0.1
        )
        
        # This should fail for Peloton but succeed for Strava
        result = await api_manager.fetch_all_data()
        
        status = api_manager.get_api_status()
        
        # Check error tracking
        assert not status['api_status']['peloton']['available']
        assert status['api_status']['peloton']['error_count'] == 3  # 3 attempts
        assert status['api_status']['peloton']['last_error'] is not None
        
        # Strava should be fine
        assert status['api_status']['strava']['available']
        assert status['api_status']['strava']['error_count'] == 0
    
    def test_api_manager_with_no_clients(self):
        """Test APIManager behavior with no configured clients."""
        api_manager = APIManager()
        
        status = api_manager.get_api_status()
        assert not status['configured_clients']['peloton']
        assert not status['configured_clients']['strava']
    
    @pytest.mark.asyncio
    async def test_no_clients_configured_raises_error(self):
        """Test that error is raised when no clients are configured."""
        api_manager = APIManager()
        
        with pytest.raises(APIManagerError, match="All API sources failed"):
            await api_manager.fetch_all_data()
    
    def test_has_recent_data(self, api_manager):
        """Test recent data checking functionality."""
        # Initially no recent data
        assert not api_manager.has_recent_data()
        
        # Simulate recent fetch
        api_manager.last_results['fetch_timestamp'] = datetime.now(timezone.utc)
        assert api_manager.has_recent_data(max_age_minutes=60)
        
        # Simulate old fetch
        old_time = datetime.now(timezone.utc).replace(hour=0)  # Much earlier today
        api_manager.last_results['fetch_timestamp'] = old_time
        assert not api_manager.has_recent_data(max_age_minutes=60)