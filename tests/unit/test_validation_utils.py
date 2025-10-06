"""
Unit tests for ValidationUtils.
"""
import pytest
from datetime import datetime
from models.validation_utils import ValidationUtils


class TestValidationUtils:
    """Test cases for ValidationUtils class."""
    
    def test_parse_distance_miles(self):
        """Test parsing distance in miles."""
        assert ValidationUtils.parse_distance(5.0, 'miles') == 5.0
        assert ValidationUtils.parse_distance("10.5", 'miles') == 10.5
        assert ValidationUtils.parse_distance(15, 'miles') == 15.0
        assert ValidationUtils.parse_distance("5.5 miles", 'miles') == 5.5
        assert ValidationUtils.parse_distance("10 mi", 'miles') == 10.0
    
    def test_parse_distance_kilometers(self):
        """Test parsing distance in kilometers."""
        # 1 km = 0.621371 miles
        result = ValidationUtils.parse_distance(10.0, 'km')
        assert abs(result - 6.21371) < 0.001
        
        result = ValidationUtils.parse_distance("5 km", 'km')
        assert abs(result - 3.106855) < 0.001
    
    def test_parse_distance_meters(self):
        """Test parsing distance in meters."""
        # 1000 meters = 0.621371 miles
        result = ValidationUtils.parse_distance(1000, 'meters')
        assert abs(result - 0.621371) < 0.001
        
        result = ValidationUtils.parse_distance("1609.34 m", 'meters')
        assert abs(result - 1.0) < 0.01  # Approximately 1 mile
    
    def test_parse_distance_invalid_input(self):
        """Test parsing invalid distance inputs."""
        with pytest.raises(ValueError, match="Distance input cannot be None"):
            ValidationUtils.parse_distance(None)
        
        with pytest.raises(ValueError, match="Cannot parse distance from string"):
            ValidationUtils.parse_distance("not_a_number")
        
        with pytest.raises(ValueError, match="Distance cannot be negative"):
            ValidationUtils.parse_distance(-5.0)
        
        with pytest.raises(ValueError, match="Unsupported distance unit"):
            ValidationUtils.parse_distance(5.0, "invalid_unit")
    
    def test_parse_timestamp_datetime(self):
        """Test parsing datetime objects."""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = ValidationUtils.parse_timestamp(dt)
        assert result == dt
    
    def test_parse_timestamp_unix(self):
        """Test parsing Unix timestamps."""
        # Unix timestamp for 2023-01-01 12:00:00 UTC
        unix_timestamp = 1672574400
        result = ValidationUtils.parse_timestamp(unix_timestamp)
        expected = datetime.fromtimestamp(unix_timestamp)
        assert result == expected
        
        # Test float timestamp
        result = ValidationUtils.parse_timestamp(1672574400.5)
        expected = datetime.fromtimestamp(1672574400.5)
        assert result == expected
    
    def test_parse_timestamp_iso_strings(self):
        """Test parsing various ISO format strings."""
        test_cases = [
            ("2023-01-01T12:00:00.000Z", datetime(2023, 1, 1, 12, 0, 0)),
            ("2023-01-01T12:00:00Z", datetime(2023, 1, 1, 12, 0, 0)),
            ("2023-01-01T12:00:00.000", datetime(2023, 1, 1, 12, 0, 0)),
            ("2023-01-01T12:00:00", datetime(2023, 1, 1, 12, 0, 0)),
            ("2023-01-01 12:00:00", datetime(2023, 1, 1, 12, 0, 0)),
            ("2023-01-01", datetime(2023, 1, 1, 0, 0, 0))
        ]
        
        for timestamp_str, expected in test_cases:
            result = ValidationUtils.parse_timestamp(timestamp_str)
            assert result == expected
    
    def test_parse_timestamp_invalid(self):
        """Test parsing invalid timestamps."""
        with pytest.raises(ValueError, match="Timestamp input cannot be None"):
            ValidationUtils.parse_timestamp(None)
        
        with pytest.raises(ValueError, match="Cannot parse timestamp string"):
            ValidationUtils.parse_timestamp("invalid_timestamp")
        
        with pytest.raises(ValueError, match="Unsupported timestamp type"):
            ValidationUtils.parse_timestamp([2023, 1, 1])
    
    def test_validate_heart_rate_valid(self):
        """Test validating valid heart rates."""
        assert ValidationUtils.validate_heart_rate(None) is None
        assert ValidationUtils.validate_heart_rate(120) == 120
        assert ValidationUtils.validate_heart_rate(120.5) == 120
        assert ValidationUtils.validate_heart_rate("140") == 140
        assert ValidationUtils.validate_heart_rate(30) == 30  # Minimum
        assert ValidationUtils.validate_heart_rate(250) == 250  # Maximum
    
    def test_validate_heart_rate_invalid(self):
        """Test validating invalid heart rates."""
        with pytest.raises(ValueError, match="Cannot parse heart rate"):
            ValidationUtils.validate_heart_rate("not_a_number")
        
        with pytest.raises(ValueError, match="Heart rate must be between 30 and 250"):
            ValidationUtils.validate_heart_rate(29)  # Too low
        
        with pytest.raises(ValueError, match="Heart rate must be between 30 and 250"):
            ValidationUtils.validate_heart_rate(251)  # Too high
    
    def test_validate_duration_minutes(self):
        """Test validating duration in minutes."""
        assert ValidationUtils.validate_duration(30, 'minutes') == 30
        assert ValidationUtils.validate_duration(45.5, 'minutes') == 45
        assert ValidationUtils.validate_duration("60", 'minutes') == 60
    
    def test_validate_duration_seconds(self):
        """Test validating duration in seconds."""
        assert ValidationUtils.validate_duration(1800, 'seconds') == 30  # 30 minutes
        assert ValidationUtils.validate_duration(3600, 'seconds') == 60  # 60 minutes
    
    def test_validate_duration_hours(self):
        """Test validating duration in hours."""
        assert ValidationUtils.validate_duration(1, 'hours') == 60  # 60 minutes
        assert ValidationUtils.validate_duration(1.5, 'hours') == 90  # 90 minutes
    
    def test_validate_duration_invalid(self):
        """Test validating invalid durations."""
        with pytest.raises(ValueError, match="Duration input cannot be None"):
            ValidationUtils.validate_duration(None)
        
        with pytest.raises(ValueError, match="Cannot parse duration"):
            ValidationUtils.validate_duration("not_a_number")
        
        with pytest.raises(ValueError, match="Duration cannot be negative"):
            ValidationUtils.validate_duration(-30)
        
        with pytest.raises(ValueError, match="Unsupported duration unit"):
            ValidationUtils.validate_duration(30, "invalid_unit")
    
    def test_validate_calories_valid(self):
        """Test validating valid calories."""
        assert ValidationUtils.validate_calories(None) is None
        assert ValidationUtils.validate_calories(250) == 250
        assert ValidationUtils.validate_calories(250.5) == 250
        assert ValidationUtils.validate_calories("300") == 300
        assert ValidationUtils.validate_calories(0) == 0
        assert ValidationUtils.validate_calories(10000) == 10000  # Maximum
    
    def test_validate_calories_invalid(self):
        """Test validating invalid calories."""
        with pytest.raises(ValueError, match="Cannot parse calories"):
            ValidationUtils.validate_calories("not_a_number")
        
        with pytest.raises(ValueError, match="Calories cannot be negative"):
            ValidationUtils.validate_calories(-100)
        
        with pytest.raises(ValueError, match="Calories value seems unreasonably high"):
            ValidationUtils.validate_calories(10001)  # Too high