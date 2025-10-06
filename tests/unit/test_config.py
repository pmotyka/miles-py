"""
Unit tests for configuration management.
"""
import os
import pytest
import tempfile
from unittest.mock import patch, mock_open

from config import Config, ConfigError


class TestConfig:
    """Test configuration validation and management."""
    
    def test_config_validation_success(self):
        """Test successful configuration validation with all required variables."""
        env_vars = {
            'PELOTON_USER_ID': 'test_user_id',
            'PELOTON_SESSION_ID': 'test_session_id',
            'STRAVA_CLIENT_ID': 'test_client_id',
            'STRAVA_CLIENT_SECRET': 'test_client_secret',
            'STRAVA_REFRESH_TOKEN': 'test_refresh_token',
            'STRAVA_ATHLETE_ID': 'test_athlete_id',
            'GCS_BUCKET_NAME': 'test_bucket',
            'GCS_CREDENTIALS_PATH': '/tmp/test_credentials.json',
        }
        
        with patch.dict(os.environ, env_vars), \
             patch('os.path.exists', return_value=True):
            config = Config()
            
            assert config.peloton_user_id == 'test_user_id'
            assert config.peloton_session_id == 'test_session_id'
            assert config.strava_client_id == 'test_client_id'
            assert config.strava_client_secret == 'test_client_secret'
            assert config.strava_refresh_token == 'test_refresh_token'
            assert config.strava_athlete_id == 'test_athlete_id'
            assert config.gcs_bucket_name == 'test_bucket'
            assert config.gcs_credentials_path == '/tmp/test_credentials.json'
    
    def test_config_validation_missing_required_vars(self):
        """Test configuration validation fails with missing required variables."""
        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigError) as exc_info:
                Config()
            
            error_message = str(exc_info.value)
            assert "Missing required environment variables" in error_message
            assert "PELOTON_USER_ID" in error_message
            assert "STRAVA_CLIENT_ID" in error_message
    
    def test_config_validation_missing_credentials_file(self):
        """Test configuration validation warns when GCS credentials file doesn't exist."""
        env_vars = {
            'PELOTON_USER_ID': 'test_user_id',
            'PELOTON_SESSION_ID': 'test_session_id',
            'STRAVA_CLIENT_ID': 'test_client_id',
            'STRAVA_CLIENT_SECRET': 'test_client_secret',
            'STRAVA_REFRESH_TOKEN': 'test_refresh_token',
            'STRAVA_ATHLETE_ID': 'test_athlete_id',
            'GCS_BUCKET_NAME': 'test_bucket',
            'GCS_CREDENTIALS_PATH': '/nonexistent/credentials.json',
        }
        
        with patch.dict(os.environ, env_vars), \
             patch('os.path.exists', return_value=False):
            with pytest.warns(UserWarning, match="Google Cloud credentials file not found"):
                config = Config()
                # Should set GCS_CREDENTIALS_PATH to None when file doesn't exist
                assert config.gcs_credentials_path is None
    
    def test_config_optional_vars_with_defaults(self):
        """Test optional configuration variables use defaults when not set."""
        env_vars = {
            'PELOTON_USER_ID': 'test_user_id',
            'PELOTON_SESSION_ID': 'test_session_id',
            'STRAVA_CLIENT_ID': 'test_client_id',
            'STRAVA_CLIENT_SECRET': 'test_client_secret',
            'STRAVA_REFRESH_TOKEN': 'test_refresh_token',
            'STRAVA_ATHLETE_ID': 'test_athlete_id',
            'GCS_BUCKET_NAME': 'test_bucket',
            'GCS_CREDENTIALS_PATH': '/tmp/test_credentials.json',
        }
        
        with patch.dict(os.environ, env_vars, clear=True), \
             patch('os.path.exists', return_value=True):
            config = Config()
            
            assert config.timezone == 'UTC'
            assert config.cache_dir == '.cache'
            assert config.log_level == 'INFO'
            assert config.api_timeout == 30
            assert config.cache_expiry_hours == 24
    
    def test_config_optional_vars_custom_values(self):
        """Test optional configuration variables use custom values when set."""
        env_vars = {
            'PELOTON_USER_ID': 'test_user_id',
            'PELOTON_SESSION_ID': 'test_session_id',
            'STRAVA_CLIENT_ID': 'test_client_id',
            'STRAVA_CLIENT_SECRET': 'test_client_secret',
            'STRAVA_REFRESH_TOKEN': 'test_refresh_token',
            'STRAVA_ATHLETE_ID': 'test_athlete_id',
            'GCS_BUCKET_NAME': 'test_bucket',
            'GCS_CREDENTIALS_PATH': '/tmp/test_credentials.json',
            'TIMEZONE': 'America/New_York',
            'CACHE_DIR': '/tmp/cache',
            'LOG_LEVEL': 'DEBUG',
            'API_TIMEOUT': '60',
            'CACHE_EXPIRY_HOURS': '12',
        }
        
        with patch.dict(os.environ, env_vars), \
             patch('os.path.exists', return_value=True):
            config = Config()
            
            assert config.timezone == 'America/New_York'
            assert config.cache_dir == '/tmp/cache'
            assert config.log_level == 'DEBUG'
            assert config.api_timeout == 60
            assert config.cache_expiry_hours == 12
    
    def test_config_get_methods(self):
        """Test configuration getter methods."""
        env_vars = {
            'PELOTON_USER_ID': 'test_user_id',
            'PELOTON_SESSION_ID': 'test_session_id',
            'STRAVA_CLIENT_ID': 'test_client_id',
            'STRAVA_CLIENT_SECRET': 'test_client_secret',
            'STRAVA_REFRESH_TOKEN': 'test_refresh_token',
            'STRAVA_ATHLETE_ID': 'test_athlete_id',
            'GCS_BUCKET_NAME': 'test_bucket',
            'GCS_CREDENTIALS_PATH': '/tmp/test_credentials.json',
            'TEST_BOOL': 'true',
            'TEST_INT': '42',
        }
        
        with patch.dict(os.environ, env_vars, clear=True), \
             patch('os.path.exists', return_value=True):
            config = Config()
            
            assert config.get('TEST_BOOL') == 'true'
            assert config.get('NONEXISTENT', 'default') == 'default'
            assert config.get_int('TEST_INT') == 42
            assert config.get_int('NONEXISTENT', 10) == 10
            assert config.get_bool('TEST_BOOL') is True
            assert config.get_bool('NONEXISTENT', False) is False