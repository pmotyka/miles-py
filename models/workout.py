"""
Workout data model with validation methods.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import re


@dataclass
class Workout:
    """Data model for individual workout records from fitness platforms."""
    
    id: str
    source: str  # 'peloton' or 'strava'
    date: datetime
    duration_minutes: int
    distance_miles: float
    workout_type: str
    calories: Optional[int] = None
    avg_heart_rate: Optional[int] = None
    
    def __post_init__(self):
        """Validate workout data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate all workout data fields."""
        self._validate_id()
        self._validate_source()
        self._validate_date()
        self._validate_duration()
        self._validate_distance()
        self._validate_workout_type()
        self._validate_optional_fields()
    
    def _validate_id(self) -> None:
        """Validate workout ID is not empty."""
        if not self.id or not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Workout ID must be a non-empty string")
    
    def _validate_source(self) -> None:
        """Validate source is one of the supported platforms."""
        valid_sources = {'peloton', 'strava'}
        if self.source not in valid_sources:
            raise ValueError(f"Source must be one of {valid_sources}, got: {self.source}")
    
    def _validate_date(self) -> None:
        """Validate date is a datetime object."""
        if not isinstance(self.date, datetime):
            raise ValueError("Date must be a datetime object")
    
    def _validate_duration(self) -> None:
        """Validate duration is a positive integer."""
        if not isinstance(self.duration_minutes, int) or self.duration_minutes <= 0:
            raise ValueError("Duration must be a positive integer (minutes)")
    
    def _validate_distance(self) -> None:
        """Validate distance is a non-negative float."""
        if not isinstance(self.distance_miles, (int, float)) or self.distance_miles < 0:
            raise ValueError("Distance must be a non-negative number (miles)")
    
    def _validate_workout_type(self) -> None:
        """Validate workout type is not empty."""
        if not self.workout_type or not isinstance(self.workout_type, str) or not self.workout_type.strip():
            raise ValueError("Workout type must be a non-empty string")
    
    def _validate_optional_fields(self) -> None:
        """Validate optional fields when present."""
        if self.calories is not None:
            if not isinstance(self.calories, int) or self.calories < 0:
                raise ValueError("Calories must be a non-negative integer")
        
        if self.avg_heart_rate is not None:
            if not isinstance(self.avg_heart_rate, int) or not (30 <= self.avg_heart_rate <= 250):
                raise ValueError("Average heart rate must be between 30 and 250 bpm")
    
    @classmethod
    def from_peloton_data(cls, data: dict) -> 'Workout':
        """Create Workout instance from Peloton API data."""
        return cls(
            id=str(data.get('id', '')),
            source='peloton',
            date=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
            duration_minutes=int(data.get('total_work', 0) / 60),  # Convert seconds to minutes
            distance_miles=float(data.get('distance', 0)) * 0.000621371,  # Convert meters to miles
            workout_type=data.get('fitness_discipline', 'cycling'),
            calories=data.get('calories'),
            avg_heart_rate=data.get('avg_heart_rate')
        )
    
    @classmethod
    def from_strava_data(cls, data: dict) -> 'Workout':
        """Create Workout instance from Strava API data."""
        return cls(
            id=str(data.get('id', '')),
            source='strava',
            date=datetime.fromisoformat(data['start_date'].replace('Z', '+00:00')),
            duration_minutes=int(data.get('moving_time', 0) / 60),  # Convert seconds to minutes
            distance_miles=float(data.get('distance', 0)) * 0.000621371,  # Convert meters to miles
            workout_type=data.get('type', 'Ride'),
            calories=data.get('calories'),
            avg_heart_rate=data.get('average_heartrate')
        )