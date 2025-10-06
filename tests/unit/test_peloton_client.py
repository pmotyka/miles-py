"""
Unit tests for Peloton API client.
"""
import pytest
import json
import os
import requests
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
import responses
import pytz

from clients.peloton_client import PelotonClient


class TestPelotonClient:
    """Test cases for PelotonClient class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.user_id = "test_user_123"
        self.session_id = "test_session_456"
        self.timezone_str = "America/New_York"
        # Pass credentials explicitly to avoid environment variable dependency
        self.client = PelotonClient(
            user_id=self.user_id, 
            session_id=self.session_id, 
            timezone_str=self.timezone_str
        )
    
    def test_init(self):
        """Test client initialization."""
        assert self.client.user_id == self.user_id
        assert self.client.session_id == self.session_id
        assert self.client.timezone == pytz.timezone(self.timezone_str)
        assert self.client.peloton_timezone == self.timezone_str
        assert self.client.platform == "web"  # default value
        assert self.client.output_file == "activities.csv"  # default value
        
        # Check session headers
        assert 'User-Agent' in self.client.session.headers
        assert 'Accept' in self.client.session.headers
        
        # Check cookies
        assert self.client.session.cookies.get('peloton_session_id') == self.session_id
        assert self.client.session.cookies.get('user_id') == self.user_id
    
    @responses.activate
    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """Test successful authentication."""
        responses.add(
            responses.GET,
            f"https://api.onepeloton.com/api/user/{self.user_id}",
            json={"id": self.user_id, "username": "testuser"},
            status=200
        )
        
        result = await self.client.authenticate()
        assert result is True
    
    @responses.activate
    @pytest.mark.asyncio
    async def test_authenticate_failure(self):
        """Test authentication failure."""
        responses.add(
            responses.GET,
            f"https://api.onepeloton.com/api/user/{self.user_id}",
            json={"error": "Unauthorized"},
            status=401
        )
        
        result = await self.client.authenticate()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_authenticate_network_error(self):
        """Test authentication with network error."""
        with patch.object(self.client.session, 'get') as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Network error")
            
            result = await self.client.authenticate()
            assert result is False
    
    def test_parse_csv_response(self):
        """Test CSV response parsing."""
        csv_content = """Workout Timestamp,Fitness Discipline,Class Timestamp,Length (minutes),Distance (mi),Calories Burned,Avg Heart Rate (bpm)
1640995200,Cycling,2022-01-01 10:00:00,30,12.5,350,145
1641081600,Cycling,2022-01-02 11:00:00,45,18.2,480,152"""
        
        workouts = self.client._parse_csv_response(csv_content)
        
        assert len(workouts) == 2
        assert workouts[0]['type'] == 'Cycling'
        assert workouts[0]['duration'] == 30.0
        assert workouts[0]['distance'] == 12.5
        assert workouts[0]['calories'] == 350
        assert workouts[0]['avg_heart_rate'] == 145
    
    def test_parse_json_response(self):
        """Test JSON response parsing."""
        json_data = {
            "data": [
                {
                    "id": "workout_123",
                    "created_at": "2022-01-01T10:00:00Z",
                    "fitness_discipline": "cycling",
                    "title": "30 Min HIIT Ride",
                    "total_work": 1800,  # 30 minutes in seconds
                    "distance": 20116.8,  # meters (12.5 miles)
                    "calories": 350,
                    "avg_heart_rate": 145
                }
            ]
        }
        
        workouts = self.client._parse_json_response(json_data)
        
        assert len(workouts) == 1
        assert workouts[0]['id'] == 'workout_123'
        assert workouts[0]['type'] == 'cycling'
        assert workouts[0]['duration'] == 30.0  # 1800 seconds / 60
        assert abs(workouts[0]['distance'] - 12.5) < 0.1  # meters to miles conversion
        assert workouts[0]['calories'] == 350
    
    def test_filter_cycling_workouts(self):
        """Test filtering for cycling workouts."""
        workouts = [
            {
                'id': '1',
                'created_at': '1640995200',  # 2022-01-01
                'type': 'Cycling',
                'distance': 12.5
            },
            {
                'id': '2', 
                'created_at': '1641081600',  # 2022-01-02
                'type': 'Running',
                'distance': 5.0
            },
            {
                'id': '3',
                'created_at': '1641168000',  # 2022-01-03
                'type': 'Bike Bootcamp',
                'distance': 8.0
            }
        ]
        
        start_timestamp = 1640995200  # 2022-01-01
        end_timestamp = 1641254400    # 2022-01-04
        
        cycling_workouts = self.client._filter_cycling_workouts(
            workouts, start_timestamp, end_timestamp
        )
        
        # Should include cycling and bike workouts, exclude running
        assert len(cycling_workouts) == 2
        assert cycling_workouts[0]['type'] == 'Cycling'
        assert cycling_workouts[1]['type'] == 'Bike Bootcamp'
    
    def test_apply_timezone(self):
        """Test timezone conversion."""
        # Test with ISO format timestamp
        iso_timestamp = "2022-01-01T15:00:00Z"
        result = self.client._apply_timezone(iso_timestamp)
        
        # Should convert UTC to America/New_York (EST, UTC-5)
        assert result.tzinfo.zone == 'America/New_York'
        assert result.hour == 10  # 15:00 UTC = 10:00 EST
    
    def test_parse_timestamp(self):
        """Test timestamp parsing."""
        # Test with Unix timestamp
        timestamp = 1640995200  # 2022-01-01 00:00:00 UTC
        result = self.client._parse_timestamp(str(timestamp))
        assert result.year == 2022
        assert result.month == 1
        assert result.day == 1
        
        # Test with ISO format
        iso_timestamp = "2022-01-01T10:00:00Z"
        result = self.client._parse_timestamp(iso_timestamp)
        assert result.year == 2022
        assert result.hour == 10
    
    def test_parse_duration(self):
        """Test duration parsing."""
        assert self.client._parse_duration("30") == 30.0
        assert self.client._parse_duration("45.5") == 45.5
        assert self.client._parse_duration("invalid") == 0.0
        assert self.client._parse_duration("") == 0.0
    
    def test_parse_distance(self):
        """Test distance parsing."""
        assert self.client._parse_distance("12.5") == 12.5
        assert self.client._parse_distance("0") == 0.0
        assert self.client._parse_distance("invalid") == 0.0
        assert self.client._parse_distance("") == 0.0
    
    def test_parse_int(self):
        """Test integer parsing."""
        assert self.client._parse_int("150") == 150
        assert self.client._parse_int("150.7") == 150
        assert self.client._parse_int("invalid") == 0
        assert self.client._parse_int("") == 0
    
    def test_summarize_current_year_distance(self):
        """Test current year distance summarization."""
        current_year = datetime.now().year
        
        workouts = [
            {
                'created_at': f'{current_year}-01-01T10:00:00Z',
                'distance': 12.5
            },
            {
                'created_at': f'{current_year}-02-01T10:00:00Z', 
                'distance': 15.0
            },
            {
                'created_at': f'{current_year - 1}-01-01T10:00:00Z',  # Previous year
                'distance': 10.0
            }
        ]
        
        total_distance = self.client.summarize_current_year_distance(workouts)
        
        # Should only include current year workouts
        assert total_distance == 27.5  # 12.5 + 15.0
    
    @responses.activate
    @pytest.mark.asyncio
    async def test_get_cycling_workouts_csv_response(self):
        """Test getting cycling workouts with CSV response."""
        csv_content = """Workout Timestamp,Fitness Discipline,Class Timestamp,Length (minutes),Distance (mi),Calories Burned,Avg Heart Rate (bpm)
1640995200,Cycling,2022-01-01 10:00:00,30,12.5,350,145"""
        
        # Mock the CSV export endpoint (the primary endpoint the client tries first)
        csv_export_url = f"https://api.onepeloton.com/api/user/{self.user_id}/workout_history_csv?timezone=America/New_York"
        responses.add(
            responses.GET,
            csv_export_url,
            body=csv_content,
            status=200,
            content_type='text/csv'
        )
        
        start_date = datetime(2022, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2022, 12, 31, tzinfo=timezone.utc)
        
        workouts = await self.client.get_cycling_workouts(start_date, end_date)
        
        assert len(workouts) == 1
        assert workouts[0]['type'] == 'Cycling'
        assert workouts[0]['distance'] == 12.5
    
    @responses.activate
    @pytest.mark.asyncio
    async def test_get_cycling_workouts_json_response(self):
        """Test getting cycling workouts with JSON response."""
        json_data = {
            "data": [
                {
                    "id": "workout_123",
                    "created_at": 1640995200,
                    "fitness_discipline": "cycling",
                    "title": "30 Min HIIT Ride",
                    "total_work": 1800,
                    "distance": 20116.8,  # meters
                    "calories": 350,
                    "avg_heart_rate": 145
                }
            ]
        }
        
        responses.add(
            responses.GET,
            f"https://api.onepeloton.com/api/user/{self.user_id}/workouts",
            json=json_data,
            status=200,
            content_type='application/json'
        )
        
        start_date = datetime(2022, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2022, 12, 31, tzinfo=timezone.utc)
        
        workouts = await self.client.get_cycling_workouts(start_date, end_date)
        
        assert len(workouts) == 1
        assert workouts[0]['type'] == 'cycling'
        assert abs(workouts[0]['distance'] - 12.5) < 0.1
    
    @responses.activate
    @pytest.mark.asyncio
    async def test_get_cycling_workouts_api_error(self):
        """Test handling API errors when getting workouts."""
        responses.add(
            responses.GET,
            f"https://api.onepeloton.com/api/user/{self.user_id}/workouts",
            json={"error": "Server error"},
            status=500
        )
        
        start_date = datetime(2022, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2022, 12, 31, tzinfo=timezone.utc)
        
        with pytest.raises(Exception):
            await self.client.get_cycling_workouts(start_date, end_date)


    def test_build_csv_export_url(self):
        """Test CSV export URL building."""
        url = self.client._build_csv_export_url()
        
        # Should contain user ID and timezone
        assert self.client.user_id in url
        assert self.client.peloton_timezone in url
        assert 'workout_history_csv' in url
    
    def test_get_config_summary(self):
        """Test configuration summary."""
        config = self.client.get_config_summary()
        
        assert 'user_id' in config
        assert 'session_id' in config
        assert 'timezone' in config
        assert 'api_base' in config
        assert 'platform' in config
        assert 'api_path' in config
        assert 'output_file' in config
        
        # Check that sensitive data is masked
        assert config['user_id'].endswith('...')
        assert config['session_id'].endswith('...')
    
    def test_save_workouts_to_csv(self):
        """Test saving workouts to CSV."""
        import tempfile
        import os
        
        workouts = [
            {'id': '1', 'type': 'Cycling', 'distance': 12.5, 'calories': 350},
            {'id': '2', 'type': 'Cycling', 'distance': 15.0, 'calories': 400}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
            tmp_path = tmp.name
        
        try:
            result_path = self.client.save_workouts_to_csv(workouts, tmp_path)
            assert result_path == tmp_path
            
            # Verify file contents
            with open(tmp_path, 'r') as f:
                content = f.read()
                assert 'id,type,distance,calories' in content
                assert 'Cycling' in content
                assert '12.5' in content
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_init_with_env_variables(self):
        """Test initialization with environment variables."""
        with patch.dict(os.environ, {
            'PELOTON_USER_ID': 'env_user_123',
            'PELOTON_SESSION_ID': 'env_session_456',
            'PELOTON_TIMEZONE': 'America/Los_Angeles',
            'PELOTON_PLATFORM': 'mobile',
            'PELOTON_OUTPUT_FILE': 'my_workouts.csv'
        }):
            client = PelotonClient()
            
            assert client.user_id == 'env_user_123'
            assert client.session_id == 'env_session_456'
            assert client.peloton_timezone == 'America/Los_Angeles'
            assert client.platform == 'mobile'
            assert client.output_file == 'my_workouts.csv'
    
    def test_init_missing_credentials(self):
        """Test initialization with missing credentials."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="PELOTON_USER_ID and PELOTON_SESSION_ID must be provided"):
                PelotonClient()


if __name__ == "__main__":
    pytest.main([__file__])