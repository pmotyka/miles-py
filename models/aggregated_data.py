"""
Aggregated data model for processed workout results.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List
from .workout import Workout


@dataclass
class AggregatedData:
    """Data model for aggregated workout data from multiple sources."""
    
    total_miles: float
    workout_count: int
    last_updated: datetime
    sources: List[str]
    period_start: datetime
    period_end: datetime
    workouts: List[Workout]
    
    def __post_init__(self):
        """Validate aggregated data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate all aggregated data fields."""
        self._validate_total_miles()
        self._validate_workout_count()
        self._validate_last_updated()
        self._validate_sources()
        self._validate_period()
        self._validate_workouts()
        self._validate_data_consistency()
    
    def _validate_total_miles(self) -> None:
        """Validate total miles is non-negative."""
        if not isinstance(self.total_miles, (int, float)) or self.total_miles < 0:
            raise ValueError("Total miles must be a non-negative number")
    
    def _validate_workout_count(self) -> None:
        """Validate workout count is non-negative."""
        if not isinstance(self.workout_count, int) or self.workout_count < 0:
            raise ValueError("Workout count must be a non-negative integer")
    
    def _validate_last_updated(self) -> None:
        """Validate last updated is a datetime object."""
        if not isinstance(self.last_updated, datetime):
            raise ValueError("Last updated must be a datetime object")
    
    def _validate_sources(self) -> None:
        """Validate sources list contains valid platform names."""
        if not isinstance(self.sources, list):
            raise ValueError("Sources must be a list")
        
        valid_sources = {'peloton', 'strava'}
        for source in self.sources:
            if source not in valid_sources:
                raise ValueError(f"Invalid source: {source}. Must be one of {valid_sources}")
    
    def _validate_period(self) -> None:
        """Validate period start and end dates."""
        if not isinstance(self.period_start, datetime):
            raise ValueError("Period start must be a datetime object")
        
        if not isinstance(self.period_end, datetime):
            raise ValueError("Period end must be a datetime object")
        
        if self.period_start > self.period_end:
            raise ValueError("Period start must be before or equal to period end")
    
    def _validate_workouts(self) -> None:
        """Validate workouts list contains valid Workout objects."""
        if not isinstance(self.workouts, list):
            raise ValueError("Workouts must be a list")
        
        for workout in self.workouts:
            if not isinstance(workout, Workout):
                raise ValueError("All workouts must be Workout instances")
    
    def _validate_data_consistency(self) -> None:
        """Validate consistency between aggregated data and workout list."""
        # Check workout count consistency
        if len(self.workouts) != self.workout_count:
            raise ValueError(f"Workout count mismatch: expected {self.workout_count}, got {len(self.workouts)}")
        
        # Check total miles consistency (allow small floating point differences)
        calculated_miles = sum(workout.distance_miles for workout in self.workouts)
        if abs(calculated_miles - self.total_miles) > 0.01:
            raise ValueError(f"Total miles mismatch: expected {self.total_miles}, calculated {calculated_miles}")
        
        # Check sources consistency
        workout_sources = set(workout.source for workout in self.workouts)
        if workout_sources and not workout_sources.issubset(set(self.sources)):
            raise ValueError("Workout sources must be subset of declared sources")
    
    def get_miles_by_source(self) -> dict:
        """Get total miles broken down by source."""
        miles_by_source = {}
        for workout in self.workouts:
            source = workout.source
            miles_by_source[source] = miles_by_source.get(source, 0) + workout.distance_miles
        return miles_by_source
    
    def get_workouts_by_source(self, source: str) -> List[Workout]:
        """Get all workouts from a specific source."""
        return [workout for workout in self.workouts if workout.source == source]
    
    def add_workout(self, workout: Workout) -> None:
        """Add a workout to the aggregated data and update totals."""
        if not isinstance(workout, Workout):
            raise ValueError("Must provide a valid Workout instance")
        
        self.workouts.append(workout)
        self.workout_count = len(self.workouts)
        self.total_miles = sum(w.distance_miles for w in self.workouts)
        
        # Update sources if new source is added
        if workout.source not in self.sources:
            self.sources.append(workout.source)
        
        # Update last_updated timestamp
        self.last_updated = datetime.now()