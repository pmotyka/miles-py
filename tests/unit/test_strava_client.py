"""
Unit tests for Strava API client.
"""
import asyncio
import json
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
import requests
from requests.exceptions import RequestException, Timeout

from clients.strava_client import StravaClient, StravaRateLimitError, StravaAuthenticationError


class TestStravaClient:
    """Test cases for StravaClient."""
    
    @pytest.fixture
    def strava_client(self):
        """Create a StravaClient instance for testing."""
        return StravaClient(
            client_id="test_client_id",
            client_secret="test_client_secret", 
            refresh_token="test_refresh_token",
            athlete_id="12345",
            api_timeout=30
        )
    
    @pytest.fixture
    def mock_token_response(self):
        """Mock successful token refresh response."""
        return {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_at': int(time.time()) + 3600,  # 1 hour from now
            'expires_in': 3600
        }
    
    @pytest.fixture
    def mock_athlete_stats(self):
        """Mock athlete stats response from Strava API."""
        return {
            'ytd_ride_totals': {
                'count': 50,
                'distance': 1609344,  # 1000 miles in meters
                'moving_time': 180000,  # 50 hours in seconds
                'elevation_gain': 15000
            },
            'all_ride_totals': {
                'count': 200,
                'distance': 8046720,  # 5000 miles in meters
                'moving_time': 720000,  # 200 hours in seconds
                'elevation_gain': 75000
            },
            'recent_ride_totals': {
                'count': 5,
                'distance': 160934,  # 100 miles in meters
                'moving_time': 18000,  # 5 hours in seconds
                'elevation_gain': 1500
            }
        }
    
    def test_init(self, strava_client):
        """Test StravaClient initialization."""
        assert strava_client.client_id == "test_client_id"
        assert strava_client.client_secret == "test_client_secret"
        assert strava_client.refresh_token == "test_refresh_token"
        assert strava_client.athlete_id == "12345"
        assert strava_client.api_timeout == 30
        assert strava_client.access_token is None
        assert strava_client.token_expires_at is None
        assert strava_client.base_url == "https://www.strava.com/api/v3"
        assert strava_client.token_url == "https://www.strava.com/oauth/token"
    
    def test_setup_session(self, strava_client):
        """Test HTTP session setup."""
        expected_headers = {
            'User-Agent': 'Miles-Aggregator/1.0',
            'Accept': 'application/json',
        }
        
        for key, value in expected_headers.items():
            assert strava_client.session.headers[key] == value
    
    def test_is_token_valid_no_token(self, strava_client):
        """Test token validation when no token exists."""
        assert not strava_client._is_token_valid()
    
    def test_is_token_valid_expired_token(self, strava_client):
        """Test token validation with expired token."""
        strava_client.access_token = "test_token"
        strava_client.token_expires_at = int(time.time()) - 3600  # 1 hour ago
        
        assert not strava_client._is_token_valid()
    
    def test_is_token_valid_valid_token(self, strava_client):
        """Test token validation with valid token."""
        strava_client.access_token = "test_token"
        strava_client.token_expires_at = int(time.time()) + 3600  # 1 hour from now
        
        assert strava_client._is_token_valid()
    
    def test_is_token_valid_soon_to_expire(self, strava_client):
        """Test token validation with token expiring soon (within 5 minutes)."""
        strava_client.access_token = "test_token"
        strava_client.token_expires_at = int(time.time()) + 200  # 3 minutes from now
        
        assert not strava_client._is_token_valid()  # Should be invalid due to 5-minute buffer
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, strava_client, mock_token_response):
        """Test successful access token refresh."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response
        
        with patch.object(strava_client.session, 'post', return_value=mock_response):
            result = await strava_client._refresh_access_token()
            
            assert result is True
            assert strava_client.access_token == "new_access_token"
            assert strava_client.token_expires_at == mock_token_response['expires_at']
            assert strava_client.session.headers['Authorization'] == 'Bearer new_access_token'
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_failure(self, strava_client):
        """Test failed access token refresh."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid refresh token"
        
        with patch.object(strava_client.session, 'post', return_value=mock_response):
            result = await strava_client._refresh_access_token()
            
            assert result is False
            assert strava_client.access_token is None
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_request_exception(self, strava_client):
        """Test access token refresh with request exception."""
        with patch.object(strava_client.session, 'post', side_effect=RequestException("Network error")):
            result = await strava_client._refresh_access_token()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_authenticate_with_valid_token(self, strava_client):
        """Test authentication when valid token already exists."""
        strava_client.access_token = "valid_token"
        strava_client.token_expires_at = int(time.time()) + 3600
        
        result = await strava_client.authenticate()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_authenticate_with_token_refresh(self, strava_client, mock_token_response):
        """Test authentication with token refresh."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response
        
        with patch.object(strava_client.session, 'post', return_value=mock_response):
            result = await strava_client.authenticate()
            
            assert result is True
            assert strava_client.access_token == "new_access_token"
    
    @pytest.mark.asyncio
    async def test_authenticate_failure(self, strava_client):
        """Test authentication failure."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid credentials"
        
        with patch.object(strava_client.session, 'post', return_value=mock_response):
            result = await strava_client.authenticate()
            
            assert result is False
    
    def test_meters_to_miles(self, strava_client):
        """Test meters to miles conversion."""
        # Test known conversions
        assert strava_client._meters_to_miles(1609.344) == pytest.approx(1.0, rel=1e-3)
        assert strava_client._meters_to_miles(0) == 0.0
        assert strava_client._meters_to_miles(1000) == pytest.approx(0.621371, rel=1e-3)
    
    def test_extract_cycling_stats(self, strava_client, mock_athlete_stats):
        """Test extraction of cycling statistics."""
        result = strava_client._extract_cycling_stats(mock_athlete_stats)
        
        # Check structure
        assert 'ytd_ride_totals' in result
        assert 'all_ride_totals' in result
        assert 'recent_ride_totals' in result
        
        # Check computed fields
        assert result['ytd_distance_miles'] == pytest.approx(1000.0, rel=1e-3)
        assert result['ytd_ride_count'] == 50
        assert result['ytd_moving_time_hours'] == 50.0
        assert result['all_time_distance_miles'] == pytest.approx(5000.0, rel=1e-3)
        assert result['all_time_ride_count'] == 200
    
    def test_extract_cycling_stats_empty_data(self, strava_client):
        """Test extraction of cycling statistics with empty data."""
        result = strava_client._extract_cycling_stats({})
        
        # Should return default values
        assert result['ytd_distance_miles'] == 0.0
        assert result['ytd_ride_count'] == 0
        assert result['ytd_moving_time_hours'] == 0.0
        assert result['all_time_distance_miles'] == 0.0
        assert result['all_time_ride_count'] == 0
    
    def test_extract_cycling_stats_malformed_data(self, strava_client):
        """Test extraction with malformed data."""
        malformed_data = {
            'ytd_ride_totals': 'not_a_dict',
            'all_ride_totals': None
        }
        
        result = strava_client._extract_cycling_stats(malformed_data)
        
        # Should handle gracefully and return defaults
        assert result['ytd_distance_miles'] == 0.0
        assert result['all_time_distance_miles'] == 0.0
    
    @pytest.mark.asyncio
    async def test_handle_rate_limiting_within_limits(self, strava_client):
        """Test rate limiting when within limits."""
        # Should not raise any exceptions
        await strava_client._handle_rate_limiting()
        
        assert len(strava_client._request_times) == 1
        assert strava_client._daily_requests == 1
    
    @pytest.mark.asyncio
    async def test_handle_rate_limiting_daily_limit_exceeded(self, strava_client):
        """Test rate limiting when daily limit is exceeded."""
        strava_client._daily_requests = strava_client.RATE_LIMIT_DAILY
        
        with pytest.raises(StravaRateLimitError, match="Daily rate limit exceeded"):
            await strava_client._handle_rate_limiting()
    
    @pytest.mark.asyncio
    async def test_handle_rate_limiting_15min_limit_approached(self, strava_client):
        """Test rate limiting when 15-minute limit is approached."""
        # Fill up the 15-minute request buffer to exactly the limit
        current_time = time.time()
        strava_client._request_times = [current_time - 100] * strava_client.RATE_LIMIT_15MIN
        
        # This should trigger a wait
        with patch('asyncio.sleep') as mock_sleep:
            await strava_client._handle_rate_limiting()
            mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_rate_limiting_cleanup_old_requests(self, strava_client):
        """Test cleanup of old request times."""
        # Add old request times (older than 15 minutes)
        old_time = time.time() - 1000  # 16+ minutes ago
        strava_client._request_times = [old_time] * 50
        
        await strava_client._handle_rate_limiting()
        
        # Old requests should be cleaned up
        assert len(strava_client._request_times) == 1  # Only the new request
    
    @pytest.mark.asyncio
    async def test_make_request_success(self, strava_client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        
        with patch.object(strava_client.session, 'request', return_value=mock_response):
            result = await strava_client._make_request('GET', 'https://test.com')
            
            assert result.status_code == 200
    
    @pytest.mark.asyncio
    async def test_make_request_rate_limit_retry(self, strava_client):
        """Test API request with rate limit and retry."""
        # First response: rate limited
        rate_limited_response = Mock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {
            'X-RateLimit-Limit': '100,1000',
            'X-RateLimit-Usage': '100,500'
        }
        
        # Second response: success
        success_response = Mock()
        success_response.status_code = 200
        
        with patch.object(strava_client.session, 'request', side_effect=[rate_limited_response, success_response]):
            with patch('asyncio.sleep'):  # Mock sleep to speed up test
                result = await strava_client._make_request('GET', 'https://test.com')
                
                assert result.status_code == 200
    
    @pytest.mark.asyncio
    async def test_make_request_rate_limit_max_retries(self, strava_client):
        """Test API request with rate limit exceeding max retries."""
        rate_limited_response = Mock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {
            'X-RateLimit-Limit': '100,1000',
            'X-RateLimit-Usage': '100,500'
        }
        
        with patch.object(strava_client.session, 'request', return_value=rate_limited_response):
            with patch('asyncio.sleep'):  # Mock sleep to speed up test
                with pytest.raises(StravaRateLimitError, match="Rate limit exceeded, max retries reached"):
                    await strava_client._make_request('GET', 'https://test.com')
    
    @pytest.mark.asyncio
    async def test_make_request_auth_error_with_refresh(self, strava_client, mock_token_response):
        """Test API request with auth error and successful token refresh."""
        # First response: unauthorized
        auth_error_response = Mock()
        auth_error_response.status_code = 401
        
        # Second response: success after token refresh
        success_response = Mock()
        success_response.status_code = 200
        
        # Mock token refresh
        token_refresh_response = Mock()
        token_refresh_response.status_code = 200
        token_refresh_response.json.return_value = mock_token_response
        
        with patch.object(strava_client.session, 'request', side_effect=[auth_error_response, success_response]):
            with patch.object(strava_client.session, 'post', return_value=token_refresh_response):
                result = await strava_client._make_request('GET', 'https://test.com')
                
                assert result.status_code == 200
    
    @pytest.mark.asyncio
    async def test_make_request_auth_error_refresh_fails(self, strava_client):
        """Test API request with auth error and failed token refresh."""
        auth_error_response = Mock()
        auth_error_response.status_code = 401
        
        # Mock failed token refresh
        token_refresh_response = Mock()
        token_refresh_response.status_code = 400
        token_refresh_response.text = "Invalid refresh token"
        
        with patch.object(strava_client.session, 'request', return_value=auth_error_response):
            with patch.object(strava_client.session, 'post', return_value=token_refresh_response):
                with pytest.raises(StravaAuthenticationError, match="Authentication failed"):
                    await strava_client._make_request('GET', 'https://test.com')
    
    @pytest.mark.asyncio
    async def test_make_request_server_error_retry(self, strava_client):
        """Test API request with server error and retry."""
        # First response: server error
        server_error_response = Mock()
        server_error_response.status_code = 500
        server_error_response.text = "Internal server error"
        
        # Second response: success
        success_response = Mock()
        success_response.status_code = 200
        
        with patch.object(strava_client.session, 'request', side_effect=[server_error_response, success_response]):
            with patch('asyncio.sleep'):  # Mock sleep to speed up test
                result = await strava_client._make_request('GET', 'https://test.com')
                
                assert result.status_code == 200
    
    @pytest.mark.asyncio
    async def test_make_request_timeout_retry(self, strava_client):
        """Test API request with timeout and retry."""
        # First request: timeout
        # Second request: success
        success_response = Mock()
        success_response.status_code = 200
        
        with patch.object(strava_client.session, 'request', side_effect=[Timeout("Request timeout"), success_response]):
            with patch('asyncio.sleep'):  # Mock sleep to speed up test
                result = await strava_client._make_request('GET', 'https://test.com')
                
                assert result.status_code == 200
    
    @pytest.mark.asyncio
    async def test_make_request_timeout_max_retries(self, strava_client):
        """Test API request with timeout exceeding max retries."""
        with patch.object(strava_client.session, 'request', side_effect=Timeout("Request timeout")):
            with patch('asyncio.sleep'):  # Mock sleep to speed up test
                with pytest.raises(Timeout):
                    await strava_client._make_request('GET', 'https://test.com')
    
    @pytest.mark.asyncio
    async def test_get_athlete_stats_success(self, strava_client, mock_athlete_stats, mock_token_response):
        """Test successful athlete stats retrieval."""
        # Mock authentication
        token_response = Mock()
        token_response.status_code = 200
        token_response.json.return_value = mock_token_response
        
        # Mock stats response
        stats_response = Mock()
        stats_response.status_code = 200
        stats_response.json.return_value = mock_athlete_stats
        
        with patch.object(strava_client.session, 'post', return_value=token_response):
            with patch.object(strava_client.session, 'request', return_value=stats_response):
                with patch('asyncio.sleep'):  # Mock sleep for rate limiting
                    result = await strava_client.get_athlete_stats()
                    
                    assert 'ytd_distance_miles' in result
                    assert result['ytd_distance_miles'] == pytest.approx(1000.0, rel=1e-3)
                    assert result['ytd_ride_count'] == 50
    
    @pytest.mark.asyncio
    async def test_get_athlete_stats_auth_failure(self, strava_client):
        """Test athlete stats retrieval with authentication failure."""
        # Mock failed authentication
        token_response = Mock()
        token_response.status_code = 400
        token_response.text = "Invalid credentials"
        
        with patch.object(strava_client.session, 'post', return_value=token_response):
            with pytest.raises(StravaAuthenticationError, match="Failed to authenticate with Strava"):
                await strava_client.get_athlete_stats()
    
    @pytest.mark.asyncio
    async def test_get_athlete_stats_api_error(self, strava_client, mock_token_response):
        """Test athlete stats retrieval with API error."""
        # Mock successful authentication
        token_response = Mock()
        token_response.status_code = 200
        token_response.json.return_value = mock_token_response
        
        # Mock API error
        error_response = Mock()
        error_response.status_code = 404
        error_response.text = "Athlete not found"
        
        with patch.object(strava_client.session, 'post', return_value=token_response):
            with patch.object(strava_client.session, 'request', return_value=error_response):
                with patch('asyncio.sleep'):  # Mock sleep for rate limiting
                    result = await strava_client.get_athlete_stats()
                    
                    assert result == {}  # Should return empty dict on error
    
    @pytest.mark.asyncio
    async def test_get_athlete_stats_rate_limit_error(self, strava_client):
        """Test athlete stats retrieval with rate limit error."""
        # Mock authentication success
        strava_client.access_token = "valid_token"
        strava_client.token_expires_at = int(time.time()) + 3600
        
        # Simulate rate limit exceeded
        strava_client._daily_requests = strava_client.RATE_LIMIT_DAILY
        
        with pytest.raises(StravaRateLimitError):
            await strava_client.get_athlete_stats()
    
    def test_get_current_year_distance_placeholder(self, strava_client):
        """Test get_current_year_distance placeholder method."""
        # This is currently a placeholder method
        result = strava_client.get_current_year_distance()
        assert result == 0.0
    
    def test_get_config_summary(self, strava_client):
        """Test configuration summary."""
        result = strava_client.get_config_summary()
        
        expected_keys = [
            'client_id', 'athlete_id', 'base_url', 'api_timeout',
            'has_access_token', 'token_valid', 'daily_requests',
            'rate_limit_15min_usage'
        ]
        
        for key in expected_keys:
            assert key in result
        
        assert result['client_id'] == "test_client_id"
        assert result['athlete_id'] == "12345"
        assert result['base_url'] == "https://www.strava.com/api/v3"
        assert result['api_timeout'] == 30
        assert result['has_access_token'] is False
        assert result['token_valid'] is False
        assert result['daily_requests'] == 0
        assert result['rate_limit_15min_usage'] == 0


class TestStravaClientIntegration:
    """Integration tests for StravaClient (require mocking external services)."""
    
    @pytest.fixture
    def strava_client(self):
        """Create a StravaClient instance for integration testing."""
        return StravaClient(
            client_id="integration_test_client",
            client_secret="integration_test_secret",
            refresh_token="integration_test_refresh_token",
            athlete_id="integration_test_athlete",
            api_timeout=10  # Shorter timeout for tests
        )
    
    @pytest.mark.asyncio
    async def test_full_authentication_and_stats_flow(self, strava_client):
        """Test complete flow from authentication to stats retrieval."""
        # Mock token refresh
        token_response = Mock()
        token_response.status_code = 200
        token_response.json.return_value = {
            'access_token': 'integration_test_token',
            'expires_at': int(time.time()) + 3600
        }
        
        # Mock athlete stats
        stats_response = Mock()
        stats_response.status_code = 200
        stats_response.json.return_value = {
            'ytd_ride_totals': {
                'count': 25,
                'distance': 804672,  # 500 miles in meters
                'moving_time': 90000  # 25 hours in seconds
            },
            'all_ride_totals': {
                'count': 100,
                'distance': 3218688,  # 2000 miles in meters
                'moving_time': 360000  # 100 hours in seconds
            },
            'recent_ride_totals': {
                'count': 3,
                'distance': 48280,  # 30 miles in meters
                'moving_time': 5400  # 1.5 hours in seconds
            }
        }
        
        with patch.object(strava_client.session, 'post', return_value=token_response):
            with patch.object(strava_client.session, 'request', return_value=stats_response):
                with patch('asyncio.sleep'):  # Mock sleep for rate limiting
                    # Test authentication
                    auth_result = await strava_client.authenticate()
                    assert auth_result is True
                    
                    # Test stats retrieval
                    stats_result = await strava_client.get_athlete_stats()
                    
                    assert stats_result['ytd_distance_miles'] == pytest.approx(500.0, rel=1e-3)
                    assert stats_result['ytd_ride_count'] == 25
                    assert stats_result['all_time_distance_miles'] == pytest.approx(2000.0, rel=1e-3)
                    assert stats_result['all_time_ride_count'] == 100