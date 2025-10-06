"""
Data aggregation processor for combining workout data from multiple sources.
"""
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import logging
from models.workout import Workout
from models.aggregated_data import AggregatedData


logger = logging.getLogger(__name__)


class DataAggregator:
    """Processor for aggregating cycling data from multiple fitness platforms."""
    
    def __init__(self):
        """Initialize the data aggregator."""
        self.current_year = datetime.now().year
    
    def aggregate_cycling_data(self, peloton_data: List[Dict], strava_data: Dict) -> AggregatedData:
        """
        Combine cycling data from all sources into aggregated format.
        
        Args:
            peloton_data: List of Peloton workout dictionaries (CSV format)
            strava_data: Strava athlete statistics dictionary (JSON format)
            
        Returns:
            AggregatedData: Processed and validated aggregated workout data
        """
        logger.info("Starting data aggregation process")
        
        # Normalize and filter data from each source
        peloton_workouts = self._normalize_peloton_data(peloton_data)
        strava_workouts = self._normalize_strava_data(strava_data)
        
        # Filter workouts for current year
        current_year_workouts = self._filter_current_year_workouts(
            peloton_workouts + strava_workouts
        )
        
        # Calculate aggregated metrics
        total_miles = self._calculate_total_miles(current_year_workouts)
        sources = self._get_active_sources(current_year_workouts)
        
        # Create period boundaries for current year
        period_start = datetime(self.current_year, 1, 1, tzinfo=timezone.utc)
        period_end = datetime(self.current_year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        
        # Create aggregated data object
        aggregated_data = AggregatedData(
            total_miles=round(total_miles, 2),
            workout_count=len(current_year_workouts),
            last_updated=datetime.now(timezone.utc),
            sources=sources,
            period_start=period_start,
            period_end=period_end,
            workouts=current_year_workouts
        )
        
        # Validate the aggregated data
        if not self._validate_aggregated_data(aggregated_data):
            logger.warning("Aggregated data validation failed, using fallback data")
            return self._create_fallback_data()
        
        logger.info(f"Data aggregation complete: {total_miles:.2f} miles from {len(current_year_workouts)} workouts")
        return aggregated_data
    
    def _normalize_peloton_data(self, peloton_data: List[Dict]) -> List[Workout]:
        """
        Normalize Peloton CSV data to Workout objects.
        
        Args:
            peloton_data: List of Peloton workout dictionaries from CSV
            
        Returns:
            List[Workout]: Normalized workout objects
        """
        workouts = []
        
        for data in peloton_data:
            try:
                # Handle CSV format from Peloton (different structure than API)
                workout = Workout(
                    id=str(data.get('Workout Timestamp', '')),  # Use timestamp as ID for CSV
                    source='peloton',
                    date=self._parse_peloton_date(data.get('Workout Timestamp', '')),
                    duration_minutes=self._parse_duration(data.get('Length (minutes)', '0')),
                    distance_miles=self._parse_distance(data.get('Distance (mi)', '0')),
                    workout_type=data.get('Fitness Discipline', 'cycling'),
                    calories=self._parse_optional_int(data.get('Calories Burned')),
                    avg_heart_rate=self._parse_optional_int(data.get('Avg Heart Rate (bpm)'))
                )
                
                # Only include cycling workouts
                if self._is_cycling_workout(workout):
                    workouts.append(workout)
                    
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to normalize Peloton workout data: {e}")
                continue
        
        logger.info(f"Normalized {len(workouts)} Peloton cycling workouts")
        return workouts
    
    def _normalize_strava_data(self, strava_data: Dict) -> List[Workout]:
        """
        Normalize Strava JSON data to Workout objects.
        
        Args:
            strava_data: Strava athlete statistics dictionary
            
        Returns:
            List[Workout]: Normalized workout objects (summary data)
        """
        workouts = []
        
        try:
            # Strava provides summary statistics, not individual workouts
            # Create a summary workout entry for current year cycling
            recent_ride_totals = strava_data.get('recent_ride_totals', {})
            ytd_ride_totals = strava_data.get('ytd_ride_totals', {})
            
            # Use year-to-date totals for current year summary
            if ytd_ride_totals and ytd_ride_totals.get('distance', 0) > 0:
                summary_workout = Workout(
                    id=f"strava_ytd_{self.current_year}",
                    source='strava',
                    date=datetime(self.current_year, 1, 1, tzinfo=timezone.utc),
                    duration_minutes=int(ytd_ride_totals.get('moving_time', 0) / 60),
                    distance_miles=float(ytd_ride_totals.get('distance', 0)) * 0.000621371,  # meters to miles
                    workout_type='cycling',
                    calories=None,  # Strava doesn't provide calories in summary
                    avg_heart_rate=None
                )
                workouts.append(summary_workout)
                
        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to normalize Strava data: {e}")
        
        logger.info(f"Normalized {len(workouts)} Strava cycling summaries")
        return workouts
    
    def _filter_current_year_workouts(self, workouts: List[Workout]) -> List[Workout]:
        """
        Filter workouts to include only those from the current year.
        
        Args:
            workouts: List of all workout objects
            
        Returns:
            List[Workout]: Workouts from current year only
        """
        current_year_workouts = [
            workout for workout in workouts 
            if workout.date.year == self.current_year
        ]
        
        logger.info(f"Filtered to {len(current_year_workouts)} workouts from {self.current_year}")
        return current_year_workouts
    
    def _calculate_total_miles(self, workouts: List[Workout]) -> float:
        """
        Calculate total cycling miles from all workouts with proper rounding.
        
        Args:
            workouts: List of workout objects
            
        Returns:
            float: Total miles with 2 decimal precision
        """
        total_miles = sum(workout.distance_miles for workout in workouts)
        return round(total_miles, 2)
    
    def _get_active_sources(self, workouts: List[Workout]) -> List[str]:
        """
        Get list of active data sources from workouts.
        
        Args:
            workouts: List of workout objects
            
        Returns:
            List[str]: Unique source names
        """
        sources = list(set(workout.source for workout in workouts))
        return sorted(sources)  # Sort for consistency
    
    def _validate_aggregated_data(self, data: AggregatedData) -> bool:
        """
        Validate aggregated data completeness and consistency.
        
        Args:
            data: AggregatedData object to validate
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            # Use built-in validation from AggregatedData
            data.validate()
            
            # Additional business logic validation
            if data.total_miles < 0:
                logger.error("Total miles cannot be negative")
                return False
            
            if data.workout_count < 0:
                logger.error("Workout count cannot be negative")
                return False
            
            # Check for reasonable data ranges
            if data.total_miles > 50000:  # Sanity check: 50k miles per year is unrealistic
                logger.warning(f"Total miles seems unrealistic: {data.total_miles}")
            
            return True
            
        except ValueError as e:
            logger.error(f"Data validation failed: {e}")
            return False
    
    def _create_fallback_data(self) -> AggregatedData:
        """
        Create fallback aggregated data when processing fails.
        
        Returns:
            AggregatedData: Empty/zero data structure
        """
        logger.info("Creating fallback aggregated data")
        
        period_start = datetime(self.current_year, 1, 1, tzinfo=timezone.utc)
        period_end = datetime(self.current_year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        
        return AggregatedData(
            total_miles=0.0,
            workout_count=0,
            last_updated=datetime.now(timezone.utc),
            sources=[],
            period_start=period_start,
            period_end=period_end,
            workouts=[]
        )
    
    def _parse_peloton_date(self, date_str: str) -> datetime:
        """Parse Peloton date string to datetime object."""
        try:
            # Handle various Peloton date formats
            if 'T' in date_str:
                # ISO format: "2024-01-15T10:30:00Z"
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                # Simple date format: "2024-01-15 10:30:00"
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            logger.warning(f"Failed to parse Peloton date: {date_str}")
            return datetime.now(timezone.utc)
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string to integer minutes."""
        try:
            return int(float(duration_str))
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse duration: {duration_str}")
            return 0
    
    def _parse_distance(self, distance_str: str) -> float:
        """Parse distance string to float miles."""
        try:
            return float(distance_str)
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse distance: {distance_str}")
            return 0.0
    
    def _parse_optional_int(self, value: Any) -> Optional[int]:
        """Parse optional integer value."""
        if value is None or value == '':
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _is_cycling_workout(self, workout: Workout) -> bool:
        """Check if workout is a cycling workout."""
        cycling_types = {
            'cycling', 'bike', 'ride', 'spin', 'indoor cycling', 
            'outdoor cycling', 'road cycling', 'mountain biking'
        }
        return workout.workout_type.lower() in cycling_types