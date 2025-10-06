"""
Configuration management and environment variable validation for Miles Aggregator.
"""
import os
import logging
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class ConfigError(Exception):
    """Raised when configuration validation fails."""
    pass

class Config:
    """Application configuration with environment variable validation."""
    
    # Required environment variables with backward compatibility mappings
    REQUIRED_VARS = {
        'PELOTON_USER_ID': 'Peloton user ID from browser cookies',
        'PELOTON_SESSION_ID': 'Peloton session ID from browser cookies',
        'STRAVA_CLIENT_ID': 'Strava API client ID',
        'STRAVA_CLIENT_SECRET': 'Strava API client secret',
        'STRAVA_REFRESH_TOKEN': 'Strava OAuth2 refresh token',
    }
    
    # Optional required variables (can be derived from existing env vars)
    OPTIONAL_REQUIRED_VARS = {
        'STRAVA_ATHLETE_ID': ('Strava athlete ID', None),  # Can be extracted from API path
        'GCS_BUCKET_NAME': ('Google Cloud Storage bucket name', 'GOOGLE_STORAGE_BUCKET'),
        'GCS_CREDENTIALS_PATH': ('Path to Google Cloud service account credentials JSON file', 'GOOGLE_APPLICATION_CREDENTIALS'),
    }
    
    # Optional environment variables with defaults
    OPTIONAL_VARS = {
        'TIMEZONE': 'UTC',
        'CACHE_DIR': '.cache',
        'LOG_LEVEL': 'INFO',
        'API_TIMEOUT': '30',
        'CACHE_EXPIRY_HOURS': '24',
    }
    
    def __init__(self):
        """Initialize configuration and validate environment variables."""
        self._config = {}
        self._validate_environment()
    
    def _validate_environment(self) -> None:
        """Validate all required environment variables are present."""
        missing_vars = []
        
        # Check required variables
        for var_name, description in self.REQUIRED_VARS.items():
            value = os.getenv(var_name)
            if not value:
                missing_vars.append(f"{var_name} ({description})")
            else:
                self._config[var_name] = value
        
        # Check optional required variables with backward compatibility
        for var_name, (description, fallback_var) in self.OPTIONAL_REQUIRED_VARS.items():
            value = os.getenv(var_name)
            if not value and fallback_var:
                value = os.getenv(fallback_var)
            
            if var_name == 'STRAVA_ATHLETE_ID' and not value:
                # Try to extract athlete ID from STRAVA_API_PATH
                api_path = os.getenv('STRAVA_API_PATH', '')
                if '/athletes/' in api_path:
                    try:
                        athlete_id = api_path.split('/athletes/')[1].split('/')[0]
                        if athlete_id.isdigit():
                            value = athlete_id
                    except (IndexError, AttributeError):
                        pass
            
            if not value:
                missing_vars.append(f"{var_name} ({description})")
            else:
                self._config[var_name] = value
        
        if missing_vars:
            error_msg = (
                f"Missing required environment variables:\n"
                + "\n".join(f"  - {var}" for var in missing_vars)
                + f"\n\nPlease check your .env file or environment configuration."
            )
            raise ConfigError(error_msg)
        
        # Set optional variables with defaults
        for var_name, default_value in self.OPTIONAL_VARS.items():
            self._config[var_name] = os.getenv(var_name, default_value)
        
        # Validate GCS credentials file exists (if specified)
        gcs_creds_path = self._config.get('GCS_CREDENTIALS_PATH')
        if gcs_creds_path and not os.path.exists(gcs_creds_path):
            # For now, just warn instead of failing - cloud functionality comes later
            import warnings
            warnings.warn(f"Google Cloud credentials file not found: {gcs_creds_path}. Cloud storage features will be disabled.")
            self._config['GCS_CREDENTIALS_PATH'] = None
    
    def get(self, key: str, default: Optional[str] = None) -> str:
        """Get configuration value by key."""
        # First check our internal config, then environment, then default
        if key in self._config:
            return self._config[key]
        return os.getenv(key, default)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get configuration value as integer."""
        try:
            value = self.get(key, str(default))
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get configuration value as boolean."""
        value = self.get(key, str(default))
        if value is None:
            return default
        return str(value).lower() in ('true', '1', 'yes', 'on')
    
    @property
    def peloton_user_id(self) -> str:
        return self._config['PELOTON_USER_ID']
    
    @property
    def peloton_session_id(self) -> str:
        return self._config['PELOTON_SESSION_ID']
    
    @property
    def strava_client_id(self) -> str:
        return self._config['STRAVA_CLIENT_ID']
    
    @property
    def strava_client_secret(self) -> str:
        return self._config['STRAVA_CLIENT_SECRET']
    
    @property
    def strava_refresh_token(self) -> str:
        return self._config['STRAVA_REFRESH_TOKEN']
    
    @property
    def strava_athlete_id(self) -> str:
        return self._config['STRAVA_ATHLETE_ID']
    
    @property
    def gcs_bucket_name(self) -> str:
        return self._config['GCS_BUCKET_NAME']
    
    @property
    def gcs_credentials_path(self) -> Optional[str]:
        return self._config.get('GCS_CREDENTIALS_PATH')
    
    @property
    def timezone(self) -> str:
        return self._config['TIMEZONE']
    
    @property
    def cache_dir(self) -> str:
        return self._config['CACHE_DIR']
    
    @property
    def log_level(self) -> str:
        return self._config['LOG_LEVEL']
    
    @property
    def api_timeout(self) -> int:
        return self.get_int('API_TIMEOUT', 30)
    
    @property
    def cache_expiry_hours(self) -> int:
        return self.get_int('CACHE_EXPIRY_HOURS', 24)

# Global configuration instance - only initialize if not in test mode
_config_instance = None

def get_config() -> Config:
    """Get the global configuration instance, initializing if needed."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

# Only initialize config if not running tests
import sys
if 'pytest' not in sys.modules:
    config = get_config()
else:
    config = None