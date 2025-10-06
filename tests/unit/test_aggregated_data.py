"""
Unit tests for AggregatedData data model.
"""
import pytest
from datetime import datetime
from models.aggregated_data import AggregatedData
from models.workout import Workout


class TestAggregatedData:
    """Test cases for AggregatedData data model."""
    
    def create_sample_workout(self, workout_id="test_1", source="peloton", distance=5.0):
        """Helper method to create sample workout."""
        return Workout(
            id=workout_id,
            source=source,
            date=datetime(2023, 1, 1, 12, 0, 0),
            duration_minutes=30,
            distance_miles=distance,
            workout_type="cycling"
        )
    
    def test_valid_aggregated_data_creation(self):
        """Test creating valid aggregated data."""
        workouts = [
            self.create_sample_workout("1", "peloton", 5.0),
            self.create_sample_workout("2", "strava", 3.0)
        ]
        
        aggregated = AggregatedData(
            total_miles=8.0,
            workout_count=2,
            last_updated=datetime(2023, 1, 1, 15, 0, 0),
            sources=["peloton", "strava"],
            period_start=datetime(2023, 1, 1, 0, 0, 0),
            period_end=datetime(2023, 1, 31, 23, 59, 59),
            workouts=workouts
        )
        
        assert aggregated.total_miles == 8.0
        assert aggregated.workout_count == 2
        assert len(aggregated.sources) == 2
        assert len(aggregated.workouts) == 2
    
    def test_invalid_total_miles_validation(self):
        """Test validation of total miles."""
        with pytest.raises(ValueError, match="Total miles must be a non-negative number"):
            AggregatedData(
                total_miles=-5.0,
                workout_count=1,
                last_updated=datetime(2023, 1, 1),
                sources=["peloton"],
                period_start=datetime(2023, 1, 1),
                period_end=datetime(2023, 1, 31),
                workouts=[self.create_sample_workout()]
            )
    
    def test_invalid_workout_count_validation(self):
        """Test validation of workout count."""
        with pytest.raises(ValueError, match="Workout count must be a non-negative integer"):
            AggregatedData(
                total_miles=5.0,
                workout_count=-1,
                last_updated=datetime(2023, 1, 1),
                sources=["peloton"],
                period_start=datetime(2023, 1, 1),
                period_end=datetime(2023, 1, 31),
                workouts=[self.create_sample_workout()]
            )
    
    def test_invalid_last_updated_validation(self):
        """Test validation of last updated timestamp."""
        with pytest.raises(ValueError, match="Last updated must be a datetime object"):
            AggregatedData(
                total_miles=5.0,
                workout_count=1,
                last_updated="2023-01-01",  # String instead of datetime
                sources=["peloton"],
                period_start=datetime(2023, 1, 1),
                period_end=datetime(2023, 1, 31),
                workouts=[self.create_sample_workout()]
            )
    
    def test_invalid_sources_validation(self):
        """Test validation of sources list."""
        with pytest.raises(ValueError, match="Invalid source"):
            AggregatedData(
                total_miles=5.0,
                workout_count=1,
                last_updated=datetime(2023, 1, 1),
                sources=["invalid_source"],
                period_start=datetime(2023, 1, 1),
                period_end=datetime(2023, 1, 31),
                workouts=[self.create_sample_workout()]
            )
    
    def test_invalid_period_validation(self):
        """Test validation of period start and end."""
        with pytest.raises(ValueError, match="Period start must be before or equal to period end"):
            AggregatedData(
                total_miles=5.0,
                workout_count=1,
                last_updated=datetime(2023, 1, 1),
                sources=["peloton"],
                period_start=datetime(2023, 1, 31),  # After period_end
                period_end=datetime(2023, 1, 1),
                workouts=[self.create_sample_workout()]
            )
    
    def test_workout_count_consistency_validation(self):
        """Test validation of workout count consistency."""
        workouts = [
            self.create_sample_workout("1", "peloton", 5.0),
            self.create_sample_workout("2", "strava", 3.0)
        ]
        
        with pytest.raises(ValueError, match="Workout count mismatch"):
            AggregatedData(
                total_miles=8.0,
                workout_count=1,  # Inconsistent with actual workout list length
                last_updated=datetime(2023, 1, 1),
                sources=["peloton", "strava"],
                period_start=datetime(2023, 1, 1),
                period_end=datetime(2023, 1, 31),
                workouts=workouts
            )
    
    def test_total_miles_consistency_validation(self):
        """Test validation of total miles consistency."""
        workouts = [
            self.create_sample_workout("1", "peloton", 5.0),
            self.create_sample_workout("2", "strava", 3.0)
        ]
        
        with pytest.raises(ValueError, match="Total miles mismatch"):
            AggregatedData(
                total_miles=10.0,  # Inconsistent with actual workout distances (5.0 + 3.0 = 8.0)
                workout_count=2,
                last_updated=datetime(2023, 1, 1),
                sources=["peloton", "strava"],
                period_start=datetime(2023, 1, 1),
                period_end=datetime(2023, 1, 31),
                workouts=workouts
            )
    
    def test_get_miles_by_source(self):
        """Test getting miles breakdown by source."""
        workouts = [
            self.create_sample_workout("1", "peloton", 5.0),
            self.create_sample_workout("2", "peloton", 2.0),
            self.create_sample_workout("3", "strava", 3.0)
        ]
        
        aggregated = AggregatedData(
            total_miles=10.0,
            workout_count=3,
            last_updated=datetime(2023, 1, 1),
            sources=["peloton", "strava"],
            period_start=datetime(2023, 1, 1),
            period_end=datetime(2023, 1, 31),
            workouts=workouts
        )
        
        miles_by_source = aggregated.get_miles_by_source()
        assert miles_by_source["peloton"] == 7.0
        assert miles_by_source["strava"] == 3.0
    
    def test_get_workouts_by_source(self):
        """Test getting workouts filtered by source."""
        workouts = [
            self.create_sample_workout("1", "peloton", 5.0),
            self.create_sample_workout("2", "peloton", 2.0),
            self.create_sample_workout("3", "strava", 3.0)
        ]
        
        aggregated = AggregatedData(
            total_miles=10.0,
            workout_count=3,
            last_updated=datetime(2023, 1, 1),
            sources=["peloton", "strava"],
            period_start=datetime(2023, 1, 1),
            period_end=datetime(2023, 1, 31),
            workouts=workouts
        )
        
        peloton_workouts = aggregated.get_workouts_by_source("peloton")
        strava_workouts = aggregated.get_workouts_by_source("strava")
        
        assert len(peloton_workouts) == 2
        assert len(strava_workouts) == 1
        assert all(w.source == "peloton" for w in peloton_workouts)
        assert all(w.source == "strava" for w in strava_workouts)
    
    def test_add_workout(self):
        """Test adding a workout to aggregated data."""
        initial_workout = self.create_sample_workout("1", "peloton", 5.0)
        
        aggregated = AggregatedData(
            total_miles=5.0,
            workout_count=1,
            last_updated=datetime(2023, 1, 1, 12, 0, 0),
            sources=["peloton"],
            period_start=datetime(2023, 1, 1),
            period_end=datetime(2023, 1, 31),
            workouts=[initial_workout]
        )
        
        new_workout = self.create_sample_workout("2", "strava", 3.0)
        aggregated.add_workout(new_workout)
        
        assert aggregated.total_miles == 8.0
        assert aggregated.workout_count == 2
        assert len(aggregated.workouts) == 2
        assert "strava" in aggregated.sources
        assert aggregated.last_updated > datetime(2023, 1, 1, 12, 0, 0)
    
    def test_add_invalid_workout(self):
        """Test adding invalid workout to aggregated data."""
        aggregated = AggregatedData(
            total_miles=5.0,
            workout_count=1,
            last_updated=datetime(2023, 1, 1),
            sources=["peloton"],
            period_start=datetime(2023, 1, 1),
            period_end=datetime(2023, 1, 31),
            workouts=[self.create_sample_workout()]
        )
        
        with pytest.raises(ValueError, match="Must provide a valid Workout instance"):
            aggregated.add_workout("not_a_workout")