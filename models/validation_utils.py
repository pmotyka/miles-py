"""
Data validation utilities for distance parsing and timestamp handling.
"""
import re
from datetime import datetime
from typing import Union, Optional


class ValidationUtils:
    """Utility class for common data validation operations."""
    
    @staticmethod
    def parse_distance(distance_input: Union[str, int, float], unit: str = 'miles') -> float:
        """
        Parse distance from various input formats and convert to miles.
        
        Args:
            distance_input: Distance value as string, int, or float
            unit: Input unit ('miles', 'km', 'meters', 'm')
            
        Returns:
            Distance in miles as float
            
        Raises:
            ValueError: If distance cannot be parsed or is negative
        """
        if distance_input is None:
            raise ValueError("Distance input cannot be None")
        
        # Handle string inputs
        if isinstance(distance_input, str):
            # Remove common distance units and whitespace
            cleaned = re.sub(r'\s*(miles?|mi|km|kilometers?|meters?|m)\s*$', '', distance_input.strip(), flags=re.IGNORECASE)
            
            # Try to parse as float
            try:
                distance_value = float(cleaned)
            except ValueError:
                raise ValueError(f"Cannot parse distance from string: '{distance_input}'")
        else:
            distance_value = float(distance_input)
        
        # Validate non-negative
        if distance_value < 0:
            raise ValueError(f"Distance cannot be negative: {distance_value}")
        
        # Convert to miles based on unit
        unit_lower = unit.lower()
        if unit_lower in ['miles', 'mile', 'mi']:
            return distance_value
        elif unit_lower in ['km', 'kilometers', 'kilometer']:
            return distance_value * 0.621371
        elif unit_lower in ['meters', 'meter', 'm']:
            return distance_value * 0.000621371
        else:
            raise ValueError(f"Unsupported distance unit: {unit}")
    
    @staticmethod
    def parse_timestamp(timestamp_input: Union[str, datetime, int, float]) -> datetime:
        """
        Parse timestamp from various input formats.
        
        Args:
            timestamp_input: Timestamp as string, datetime, or Unix timestamp
            
        Returns:
            Parsed datetime object
            
        Raises:
            ValueError: If timestamp cannot be parsed
        """
        if timestamp_input is None:
            raise ValueError("Timestamp input cannot be None")
        
        # Already a datetime object
        if isinstance(timestamp_input, datetime):
            return timestamp_input
        
        # Unix timestamp (int or float)
        if isinstance(timestamp_input, (int, float)):
            try:
                return datetime.fromtimestamp(timestamp_input)
            except (ValueError, OSError) as e:
                raise ValueError(f"Cannot parse Unix timestamp: {timestamp_input}") from e
        
        # String timestamp
        if isinstance(timestamp_input, str):
            timestamp_str = timestamp_input.strip()
            
            # Common ISO formats
            iso_patterns = [
                '%Y-%m-%dT%H:%M:%S.%fZ',      # 2023-01-01T12:00:00.000Z
                '%Y-%m-%dT%H:%M:%SZ',         # 2023-01-01T12:00:00Z
                '%Y-%m-%dT%H:%M:%S.%f',       # 2023-01-01T12:00:00.000
                '%Y-%m-%dT%H:%M:%S',          # 2023-01-01T12:00:00
                '%Y-%m-%d %H:%M:%S',          # 2023-01-01 12:00:00
                '%Y-%m-%d',                   # 2023-01-01
            ]
            
            # Try ISO format parsing first
            for pattern in iso_patterns:
                try:
                    return datetime.strptime(timestamp_str, pattern)
                except ValueError:
                    continue
            
            # Try fromisoformat for more flexible parsing
            try:
                # Handle Z suffix
                if timestamp_str.endswith('Z'):
                    timestamp_str = timestamp_str[:-1] + '+00:00'
                return datetime.fromisoformat(timestamp_str)
            except ValueError:
                pass
            
            raise ValueError(f"Cannot parse timestamp string: '{timestamp_input}'")
        
        raise ValueError(f"Unsupported timestamp type: {type(timestamp_input)}")
    
    @staticmethod
    def validate_heart_rate(heart_rate: Optional[Union[int, float, str]]) -> Optional[int]:
        """
        Validate and normalize heart rate value.
        
        Args:
            heart_rate: Heart rate value in various formats
            
        Returns:
            Validated heart rate as integer, or None if input is None
            
        Raises:
            ValueError: If heart rate is invalid
        """
        if heart_rate is None:
            return None
        
        # Convert to int
        try:
            hr_value = int(float(heart_rate))
        except (ValueError, TypeError):
            raise ValueError(f"Cannot parse heart rate: {heart_rate}")
        
        # Validate range (reasonable human heart rate range)
        if not (30 <= hr_value <= 250):
            raise ValueError(f"Heart rate must be between 30 and 250 bpm, got: {hr_value}")
        
        return hr_value
    
    @staticmethod
    def validate_duration(duration_input: Union[int, float, str], unit: str = 'minutes') -> int:
        """
        Validate and normalize duration value.
        
        Args:
            duration_input: Duration value in various formats
            unit: Input unit ('minutes', 'seconds', 'hours')
            
        Returns:
            Duration in minutes as integer
            
        Raises:
            ValueError: If duration is invalid
        """
        if duration_input is None:
            raise ValueError("Duration input cannot be None")
        
        # Parse duration value
        try:
            duration_value = float(duration_input)
        except (ValueError, TypeError):
            raise ValueError(f"Cannot parse duration: {duration_input}")
        
        # Validate non-negative
        if duration_value < 0:
            raise ValueError(f"Duration cannot be negative: {duration_value}")
        
        # Convert to minutes based on unit
        unit_lower = unit.lower()
        if unit_lower in ['minutes', 'minute', 'min']:
            return int(duration_value)
        elif unit_lower in ['seconds', 'second', 'sec', 's']:
            return int(duration_value / 60)
        elif unit_lower in ['hours', 'hour', 'hr', 'h']:
            return int(duration_value * 60)
        else:
            raise ValueError(f"Unsupported duration unit: {unit}")
    
    @staticmethod
    def validate_calories(calories: Optional[Union[int, float, str]]) -> Optional[int]:
        """
        Validate and normalize calories value.
        
        Args:
            calories: Calories value in various formats
            
        Returns:
            Validated calories as integer, or None if input is None
            
        Raises:
            ValueError: If calories value is invalid
        """
        if calories is None:
            return None
        
        # Convert to int
        try:
            cal_value = int(float(calories))
        except (ValueError, TypeError):
            raise ValueError(f"Cannot parse calories: {calories}")
        
        # Validate non-negative
        if cal_value < 0:
            raise ValueError(f"Calories cannot be negative: {cal_value}")
        
        # Validate reasonable range (0 to 10000 calories per workout)
        if cal_value > 10000:
            raise ValueError(f"Calories value seems unreasonably high: {cal_value}")
        
        return cal_value