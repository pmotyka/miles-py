"""
Unit tests for DataAggregator class.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from processors.data_aggregator import DataAggregator
from models.workout import Workout
from models.aggregated_data import AggregatedData


class TestDataAggregator:
    """Test cases for DataAggregator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.aggregator = DataAggregator()
        self.current_year = datetime.now().year
        
        # Sample Peloton CSV data
        self.sample_peloton_data = [
            {
                'Workout Timestamp': '2024-01-15T10:30:00Z',
                'Length (minutes)': '30',
                'Distance (mi)': '8.5',
                'Fitness Discipline': 'cycling',
                'Calories Burned': '250',
                'Avg Heart Rate (bpm)': '145'
            },
            {
                'Workout Timestamp': '2024-02-01T09:00:00Z',
                'Length (minutes)': '45',
                'Distance (mi)': '12.3',
                'Fitness Discipline': 'cycling',
                'Calories Burned': '380',
                'Avg Heart Rate (bpm)': '152'
            },
            {
                'Workout Timestamp': '2023-12-15T10:30:00Z',  # Previous year
                'Length (minutes)': '30',
                'Distance (mi)': '7.0',
                'Fitness Discipline': 'cycling',
                'Calories Burned': '200',
                'Avg Heart Rate (bpm)': '140'
            }
        ]
        
        # Sample Strava JSON data
        self.sample_strava_data = {
            'ytd_ride_totals': {
                'distance': 32186.88,  # meters
                'moving_time': 7200,    # seconds
                'count': 15
            },
            'recent_ride_totals': {
                'distance': 16093.44,  # meters
                'moving_time': 3600,    # seconds
                'count': 8
            }
        }
    
    def test_aggregate_cycling_data_success(self):
        """Test successful data aggregation from multiple sources."""
        result = self.aggregator.aggregate_cycling_data(
            self.sample_peloton_data, 
            self.sample_strava_data
        )
        
        assert isinstance(result, AggregatedData)
        assert result.total_miles > 0
        assert result.workout_count > 0
        assert len(result.sources) > 0
        assert result.period_start.year == self.current_year
        assert result.period_end.year == self.current_year
    
    def test_aggregate_cycling_data_empty_inputs(self):
        """Test aggregation with empty input data."""
        result = self.aggregator.aggregate_cycling_data([], {})
        
        assert isinstance(result, AggregatedData)
        assert result.total_miles == 0.0
        assert result.workout_count == 0
        assert len(result.sources) == 0
        assert len(result.workouts) == 0
    
    def test_normalize_peloton_data_success(self):
        """Test successful normalization of Peloton CSV data."""
        workouts = self.aggregator._normalize_peloton_data(self.sample_peloton_data)
        
        assert len(workouts) == 3  # All workouts should be processed
        assert all(isinstance(w, Workout) for w in workouts)
        assert all(w.source == 'peloton' for w in workouts)
        
        # Check first workout details
        first_workout = workouts[0]
        assert first_workout.distance_miles == 8.5
        assert first_workout.duration_minutes == 30
        assert first_workout.calories == 250
        assert first_workout.avg_heart_rate == 145
    
    def test_normalize_peloton_data_invalid_data(self):
        """Test Peloton normalization with invalid data."""
        invalid_data = [
            {
                'Workout Timestamp': 'invalid-date',
                'Length (minutes)': 'invalid',
                'Distance (mi)': 'invalid',
                'Fitness Discipline': 'cycling'
            }
        ]
        
        workouts = self.aggregator._normalize_peloton_data(invalid_data)
        
        # Should handle invalid data gracefully
        assert len(workouts) == 0  # Invalid workout should be skipped
    
    def test_normalize_strava_data_success(self):
        """Test successful normalization of Strava JSON data."""
        workouts = self.aggregator._normalize_strava_data(self.sample_strava_data)
        
        assert len(workouts) == 1  # Should create one summary workout
        assert workouts[0].source == 'strava'
        assert workouts[0].workout_type == 'cycling'
        assert workouts[0].distance_miles > 0
        assert workouts[0].duration_minutes > 0
    
    def test_normalize_strava_data_empty(self):
        """Test Strava normalization with empty data."""
        workouts = self.aggregator._normalize_strava_data({})
        
        assert len(workouts) == 0
    
    def test_filter_current_year_workouts(self):
        """Test filtering workouts by current year."""
        # Create workouts from different years
        workouts = [
            Workout(
                id='1', source='peloton', 
                date=datetime(self.current_year, 1, 15, tzinfo=timezone.utc),
                duration_minutes=30, distance_miles=8.5, workout_type='cycling'
            ),
            Workout(
                id='2', source='peloton',
                date=datetime(self.current_year - 1, 12, 15, tzinfo=timezone.utc),
                duration_minutes=30, distance_miles=7.0, workout_type='cycling'
            ),
            Workout(
                id='3', source='strava',
                date=datetime(self.current_year, 6, 1, tzinfo=timezone.utc),
                duration_minutes=45, distance_miles=12.0, workout_type='cycling'
            )
        ]
        
        filtered = self.aggregator._filter_current_year_workouts(workouts)
        
        assert len(filtered) == 2  # Only current year workouts
        assert all(w.date.year == self.current_year for w in filtered)
    
    def test_calculate_total_miles(self):
        """Test total miles calculation with proper rounding."""
        workouts = [
            Workout(
                id='1', source='peloton', 
                date=datetime.now(timezone.utc),
                duration_minutes=30, distance_miles=8.567, workout_type='cycling'
            ),
            Workout(
                id='2', source='strava',
                date=datetime.now(timezone.utc),
                duration_minutes=45, distance_miles=12.333, workout_type='cycling'
            )
        ]
        
        total = self.aggregator._calculate_total_miles(workouts)
        
        assert total == 20.90  # 8.567 + 12.333 = 20.9 (rounded to 2 decimals)
        assert isinstance(total, float)
    
    def test_get_active_sources(self):
        """Test getting active sources from workouts."""
        workouts = [
            Workout(
                id='1', source='peloton', 
                date=datetime.now(timezone.utc),
                duration_minutes=30, distance_miles=8.5, workout_type='cycling'
            ),
            Workout(
                id='2', source='strava',
                date=datetime.now(timezone.utc),
                duration_minutes=45, distance_miles=12.0, workout_type='cycling'
            ),
            Workout(
                id='3', source='peloton',
                date=datetime.now(timezone.utc),
                duration_minutes=20, distance_miles=5.0, workout_type='cycling'
            )
        ]
        
        sources = self.aggregator._get_active_sources(workouts)
        
        assert sources == ['peloton', 'strava']  # Sorted unique sources
        assert isinstance(sources, list)
    
    def test_validate_aggregated_data_success(self):
        """Test validation of valid aggregated data."""
        valid_data = AggregatedData(
            total_miles=25.5,
            workout_count=2,
            last_updated=datetime.now(timezone.utc),
            sources=['peloton', 'strava'],
            period_start=datetime(self.current_year, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(self.current_year, 12, 31, tzinfo=timezone.utc),
            workouts=[
                Workout(
                    id='1', source='peloton', 
                    date=datetime.now(timezone.utc),
                    duration_minutes=30, distance_miles=15.5, workout_type='cycling'
                ),
                Workout(
                    id='2', source='strava',
                    date=datetime.now(timezone.utc),
                    duration_minutes=45, distance_miles=10.0, workout_type='cycling'
                )
            ]
        )
        
        assert self.aggregator._validate_aggregated_data(valid_data) is True
    
    def test_validate_aggregated_data_failure(self):
        """Test validation failure with invalid data."""
        # Test with inconsistent data that will fail AggregatedData validation
        invalid_workouts = [
            Workout(
                id='1', source='peloton', 
                date=datetime.now(timezone.utc),
                duration_minutes=30, distance_miles=15.5, workout_type='cycling'
            )
        ]
        
        # This will fail validation due to total miles mismatch
        try:
            invalid_data = AggregatedData(
                total_miles=25.5,  # Doesn't match workout total (15.5)
                workout_count=1,
                last_updated=datetime.now(timezone.utc),
                sources=['peloton'],
                period_start=datetime(self.current_year, 1, 1, tzinfo=timezone.utc),
                period_end=datetime(self.current_year, 12, 31, tzinfo=timezone.utc),
                workouts=invalid_workouts
            )
            # Should not reach here due to validation error
            assert False, "Expected validation error"
        except ValueError:
            # Expected behavior - validation should fail during construction
            pass
        
        # Test the validation method directly by creating valid data first, then modifying it
        valid_workouts = [
            Workout(
                id='1', source='peloton', 
                date=datetime.now(timezone.utc),
                duration_minutes=30, distance_miles=15.5, workout_type='cycling'
            )
        ]
        
        valid_data = AggregatedData(
            total_miles=15.5,  # Matches workout total
            workout_count=1,
            last_updated=datetime.now(timezone.utc),
            sources=['peloton'],
            period_start=datetime(self.current_year, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(self.current_year, 12, 31, tzinfo=timezone.utc),
            workouts=valid_workouts
        )
        
        # Now modify it to have negative miles (bypassing validation)
        valid_data.total_miles = -10.0
        
        # This should fail validation
        assert self.aggregator._validate_aggregated_data(valid_data) is False
    
    def test_create_fallback_data(self):
        """Test creation of fallback data."""
        fallback = self.aggregator._create_fallback_data()
        
        assert isinstance(fallback, AggregatedData)
        assert fallback.total_miles == 0.0
        assert fallback.workout_count == 0
        assert len(fallback.sources) == 0
        assert len(fallback.workouts) == 0
        assert fallback.period_start.year == self.current_year
        assert fallback.period_end.year == self.current_year
    
    def test_parse_peloton_date_iso_format(self):
        """Test parsing Peloton date in ISO format."""
        date_str = '2024-01-15T10:30:00Z'
        result = self.aggregator._parse_peloton_date(date_str)
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
    
    def test_parse_peloton_date_simple_format(self):
        """Test parsing Peloton date in simple format."""
        date_str = '2024-01-15 10:30:00'
        result = self.aggregator._parse_peloton_date(date_str)
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
    
    def test_parse_peloton_date_invalid(self):
        """Test parsing invalid Peloton date."""
        date_str = 'invalid-date'
        result = self.aggregator._parse_peloton_date(date_str)
        
        assert isinstance(result, datetime)
        # Should return current time as fallback
    
    def test_parse_duration_valid(self):
        """Test parsing valid duration string."""
        assert self.aggregator._parse_duration('30') == 30
        assert self.aggregator._parse_duration('45.5') == 45
    
    def test_parse_duration_invalid(self):
        """Test parsing invalid duration string."""
        assert self.aggregator._parse_duration('invalid') == 0
        assert self.aggregator._parse_duration('') == 0
        assert self.aggregator._parse_duration(None) == 0
    
    def test_parse_distance_valid(self):
        """Test parsing valid distance string."""
        assert self.aggregator._parse_distance('8.5') == 8.5
        assert self.aggregator._parse_distance('12') == 12.0
    
    def test_parse_distance_invalid(self):
        """Test parsing invalid distance string."""
        assert self.aggregator._parse_distance('invalid') == 0.0
        assert self.aggregator._parse_distance('') == 0.0
        assert self.aggregator._parse_distance(None) == 0.0
    
    def test_parse_optional_int_valid(self):
        """Test parsing valid optional integer."""
        assert self.aggregator._parse_optional_int('150') == 150
        assert self.aggregator._parse_optional_int('150.7') == 150
        assert self.aggregator._parse_optional_int(150) == 150
    
    def test_parse_optional_int_invalid(self):
        """Test parsing invalid optional integer."""
        assert self.aggregator._parse_optional_int('') is None
        assert self.aggregator._parse_optional_int(None) is None
        assert self.aggregator._parse_optional_int('invalid') is None
    
    def test_is_cycling_workout_valid(self):
        """Test identification of cycling workouts."""
        cycling_workout = Workout(
            id='1', source='peloton', 
            date=datetime.now(timezone.utc),
            duration_minutes=30, distance_miles=8.5, workout_type='cycling'
        )
        
        assert self.aggregator._is_cycling_workout(cycling_workout) is True
        
        # Test other cycling types
        cycling_workout.workout_type = 'bike'
        assert self.aggregator._is_cycling_workout(cycling_workout) is True
        
        cycling_workout.workout_type = 'Indoor Cycling'
        assert self.aggregator._is_cycling_workout(cycling_workout) is True
    
    def test_is_cycling_workout_invalid(self):
        """Test identification of non-cycling workouts."""
        running_workout = Workout(
            id='1', source='peloton', 
            date=datetime.now(timezone.utc),
            duration_minutes=30, distance_miles=3.0, workout_type='running'
        )
        
        assert self.aggregator._is_cycling_workout(running_workout) is False
    
    def test_edge_case_no_cycling_workouts(self):
        """Test aggregation when no cycling workouts are found."""
        non_cycling_data = [
            {
                'Workout Timestamp': '2024-01-15T10:30:00Z',
                'Length (minutes)': '30',
                'Distance (mi)': '3.0',
                'Fitness Discipline': 'running',  # Not cycling
                'Calories Burned': '250',
                'Avg Heart Rate (bpm)': '145'
            }
        ]
        
        result = self.aggregator.aggregate_cycling_data(non_cycling_data, {})
        
        assert result.total_miles == 0.0
        assert result.workout_count == 0
        assert len(result.workouts) == 0
    
    def test_edge_case_very_large_distance(self):
        """Test handling of unrealistic distance values."""
        large_distance_data = [
            {
                'Workout Timestamp': '2024-01-15T10:30:00Z',
                'Length (minutes)': '30',
                'Distance (mi)': '100000',  # Unrealistic distance
                'Fitness Discipline': 'cycling',
                'Calories Burned': '250',
                'Avg Heart Rate (bpm)': '145'
            }
        ]
        
        # Should still process but log warning
        result = self.aggregator.aggregate_cycling_data(large_distance_data, {})
        
        assert isinstance(result, AggregatedData)
        # The validation should still pass but may log warnings
    
    def test_different_current_year(self):
        """Test aggregation with different current year."""
        # Create aggregator with specific year
        aggregator = DataAggregator()
        aggregator.current_year = 2023
        
        # Data from 2023 should be included
        data_2023 = [
            {
                'Workout Timestamp': '2023-01-15T10:30:00Z',
                'Length (minutes)': '30',
                'Distance (mi)': '8.5',
                'Fitness Discipline': 'cycling',
                'Calories Burned': '250',
                'Avg Heart Rate (bpm)': '145'
            }
        ]
        
        result = aggregator.aggregate_cycling_data(data_2023, {})
        
        assert result.workout_count == 1
        assert result.total_miles == 8.5
        assert result.period_start.year == 2023
        assert result.period_end.year == 2023