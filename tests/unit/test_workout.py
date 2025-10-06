"""
Unit tests for Workout data model.
"""
import pytest
from datetime import datetime
from models.workout import Workout


class TestWorkout:
    """Test cases for Workout data model."""
    
    def test_valid_workout_creation(self):
        """Test creating a valid workout."""
        workout = Workout(
            id="test_123",
            source="peloton",
            date=datetime(2023, 1, 1, 12, 0, 0),
            duration_minutes=30,
            distance_miles=5.5,
            workout_type="cycling",
            calories=250,
            avg_heart_rate=140
        )
        
        assert workout.id == "test_123"
        assert workout.source == "peloton"
        assert workout.distance_miles == 5.5
        assert workout.calories == 250
        assert workout.avg_heart_rate == 140
    
    def test_workout_with_minimal_fields(self):
        """Test creating workout with only required fields."""
        workout = Workout(
            id="minimal_123",
            source="strava",
            date=datetime(2023, 1, 1, 12, 0, 0),
            duration_minutes=45,
            distance_miles=10.0,
            workout_type="ride"
        )
        
        assert workout.id == "minimal_123"
        assert workout.source == "strava"
        assert workout.calories is None
        assert workout.avg_heart_rate is None
    
    def test_invalid_id_validation(self):
        """Test validation of workout ID."""
        with pytest.raises(ValueError, match="Workout ID must be a non-empty string"):
            Workout(
                id="",
                source="peloton",
                date=datetime(2023, 1, 1),
                duration_minutes=30,
                distance_miles=5.0,
                workout_type="cycling"
            )
        
        with pytest.raises(ValueError, match="Workout ID must be a non-empty string"):
            Workout(
                id="   ",
                source="peloton",
                date=datetime(2023, 1, 1),
                duration_minutes=30,
                distance_miles=5.0,
                workout_type="cycling"
            )
    
    def test_invalid_source_validation(self):
        """Test validation of workout source."""
        with pytest.raises(ValueError, match="Source must be one of"):
            Workout(
                id="test_123",
                source="invalid_source",
                date=datetime(2023, 1, 1),
                duration_minutes=30,
                distance_miles=5.0,
                workout_type="cycling"
            )
    
    def test_invalid_date_validation(self):
        """Test validation of workout date."""
        with pytest.raises(ValueError, match="Date must be a datetime object"):
            Workout(
                id="test_123",
                source="peloton",
                date="2023-01-01",  # String instead of datetime
                duration_minutes=30,
                distance_miles=5.0,
                workout_type="cycling"
            )
    
    def test_invalid_duration_validation(self):
        """Test validation of workout duration."""
        with pytest.raises(ValueError, match="Duration must be a positive integer"):
            Workout(
                id="test_123",
                source="peloton",
                date=datetime(2023, 1, 1),
                duration_minutes=0,
                distance_miles=5.0,
                workout_type="cycling"
            )
        
        with pytest.raises(ValueError, match="Duration must be a positive integer"):
            Workout(
                id="test_123",
                source="peloton",
                date=datetime(2023, 1, 1),
                duration_minutes=-10,
                distance_miles=5.0,
                workout_type="cycling"
            )
    
    def test_invalid_distance_validation(self):
        """Test validation of workout distance."""
        with pytest.raises(ValueError, match="Distance must be a non-negative number"):
            Workout(
                id="test_123",
                source="peloton",
                date=datetime(2023, 1, 1),
                duration_minutes=30,
                distance_miles=-5.0,
                workout_type="cycling"
            )
    
    def test_invalid_workout_type_validation(self):
        """Test validation of workout type."""
        with pytest.raises(ValueError, match="Workout type must be a non-empty string"):
            Workout(
                id="test_123",
                source="peloton",
                date=datetime(2023, 1, 1),
                duration_minutes=30,
                distance_miles=5.0,
                workout_type=""
            )
    
    def test_invalid_calories_validation(self):
        """Test validation of optional calories field."""
        with pytest.raises(ValueError, match="Calories must be a non-negative integer"):
            Workout(
                id="test_123",
                source="peloton",
                date=datetime(2023, 1, 1),
                duration_minutes=30,
                distance_miles=5.0,
                workout_type="cycling",
                calories=-100
            )
    
    def test_invalid_heart_rate_validation(self):
        """Test validation of optional heart rate field."""
        with pytest.raises(ValueError, match="Average heart rate must be between 30 and 250"):
            Workout(
                id="test_123",
                source="peloton",
                date=datetime(2023, 1, 1),
                duration_minutes=30,
                distance_miles=5.0,
                workout_type="cycling",
                avg_heart_rate=300
            )
        
        with pytest.raises(ValueError, match="Average heart rate must be between 30 and 250"):
            Workout(
                id="test_123",
                source="peloton",
                date=datetime(2023, 1, 1),
                duration_minutes=30,
                distance_miles=5.0,
                workout_type="cycling",
                avg_heart_rate=20
            )
    
    def test_from_peloton_data(self):
        """Test creating workout from Peloton API data."""
        peloton_data = {
            'id': 12345,
            'created_at': '2023-01-01T12:00:00Z',
            'total_work': 1800,  # 30 minutes in seconds
            'distance': 8046.72,  # 5 miles in meters
            'fitness_discipline': 'cycling',
            'calories': 250,
            'avg_heart_rate': 140
        }
        
        workout = Workout.from_peloton_data(peloton_data)
        
        assert workout.id == "12345"
        assert workout.source == "peloton"
        assert workout.duration_minutes == 30
        assert abs(workout.distance_miles - 5.0) < 0.1  # Allow small floating point differences
        assert workout.workout_type == "cycling"
        assert workout.calories == 250
        assert workout.avg_heart_rate == 140
    
    def test_from_strava_data(self):
        """Test creating workout from Strava API data."""
        strava_data = {
            'id': 67890,
            'start_date': '2023-01-01T12:00:00Z',
            'moving_time': 2700,  # 45 minutes in seconds
            'distance': 16093.4,  # 10 miles in meters
            'type': 'Ride',
            'calories': 400,
            'average_heartrate': 135
        }
        
        workout = Workout.from_strava_data(strava_data)
        
        assert workout.id == "67890"
        assert workout.source == "strava"
        assert workout.duration_minutes == 45
        assert abs(workout.distance_miles - 10.0) < 0.1  # Allow small floating point differences
        assert workout.workout_type == "Ride"
        assert workout.calories == 400
        assert workout.avg_heart_rate == 135