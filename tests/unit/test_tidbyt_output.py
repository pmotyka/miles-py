"""
Unit tests for TidbytOutput data model.
"""
import pytest
import json
from datetime import datetime
from models.tidbyt_output import TidbytOutput
from models.aggregated_data import AggregatedData
from models.workout import Workout


class TestTidbytOutput:
    """Test cases for TidbytOutput data model."""
    
    def test_valid_tidbyt_output_creation(self):
        """Test creating valid Tidbyt output."""
        output = TidbytOutput(
            total_miles="15.50",
            last_updated="2023-01-01T12:00:00",
            source_count=2,
            display_message="15.50 miles from peloton, strava"
        )
        
        assert output.total_miles == "15.50"
        assert output.last_updated == "2023-01-01T12:00:00"
        assert output.source_count == 2
        assert "15.50 miles" in output.display_message
    
    def test_invalid_total_miles_validation(self):
        """Test validation of total miles string."""
        with pytest.raises(ValueError, match="Total miles must be a valid number string"):
            TidbytOutput(
                total_miles="not_a_number",
                last_updated="2023-01-01T12:00:00",
                source_count=1,
                display_message="Test message"
            )
        
        with pytest.raises(ValueError, match="Total miles must be a string"):
            TidbytOutput(
                total_miles=15.5,  # Number instead of string
                last_updated="2023-01-01T12:00:00",
                source_count=1,
                display_message="Test message"
            )
    
    def test_invalid_last_updated_validation(self):
        """Test validation of last updated timestamp string."""
        with pytest.raises(ValueError, match="Last updated must be a string"):
            TidbytOutput(
                total_miles="15.50",
                last_updated=datetime(2023, 1, 1),  # datetime instead of string
                source_count=1,
                display_message="Test message"
            )
        
        with pytest.raises(ValueError, match="Last updated must be a valid ISO format datetime string"):
            TidbytOutput(
                total_miles="15.50",
                last_updated="invalid_date",
                source_count=1,
                display_message="Test message"
            )
    
    def test_invalid_source_count_validation(self):
        """Test validation of source count."""
        with pytest.raises(ValueError, match="Source count must be a non-negative integer"):
            TidbytOutput(
                total_miles="15.50",
                last_updated="2023-01-01T12:00:00",
                source_count=-1,
                display_message="Test message"
            )
        
        with pytest.raises(ValueError, match="Source count must be a non-negative integer"):
            TidbytOutput(
                total_miles="15.50",
                last_updated="2023-01-01T12:00:00",
                source_count="2",  # String instead of int
                display_message="Test message"
            )
    
    def test_invalid_display_message_validation(self):
        """Test validation of display message."""
        with pytest.raises(ValueError, match="Display message cannot be empty"):
            TidbytOutput(
                total_miles="15.50",
                last_updated="2023-01-01T12:00:00",
                source_count=1,
                display_message=""
            )
        
        with pytest.raises(ValueError, match="Display message cannot be empty"):
            TidbytOutput(
                total_miles="15.50",
                last_updated="2023-01-01T12:00:00",
                source_count=1,
                display_message="   "  # Only whitespace
            )
    
    def test_to_json(self):
        """Test converting TidbytOutput to JSON string."""
        output = TidbytOutput(
            total_miles="15.50",
            last_updated="2023-01-01T12:00:00",
            source_count=2,
            display_message="15.50 miles from peloton, strava"
        )
        
        json_str = output.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["total_miles"] == "15.50"
        assert parsed["last_updated"] == "2023-01-01T12:00:00"
        assert parsed["source_count"] == 2
        assert parsed["display_message"] == "15.50 miles from peloton, strava"
        assert "generated_at" in parsed
    
    def test_to_dict(self):
        """Test converting TidbytOutput to dictionary."""
        output = TidbytOutput(
            total_miles="15.50",
            last_updated="2023-01-01T12:00:00",
            source_count=2,
            display_message="15.50 miles from peloton, strava"
        )
        
        output_dict = output.to_dict()
        
        assert output_dict["total_miles"] == "15.50"
        assert output_dict["last_updated"] == "2023-01-01T12:00:00"
        assert output_dict["source_count"] == 2
        assert output_dict["display_message"] == "15.50 miles from peloton, strava"
        assert "generated_at" in output_dict
    
    def test_from_aggregated_data(self):
        """Test creating TidbytOutput from AggregatedData."""
        # Create sample workouts
        workouts = [
            Workout(
                id="1",
                source="peloton",
                date=datetime(2023, 1, 1),
                duration_minutes=30,
                distance_miles=5.0,
                workout_type="cycling"
            ),
            Workout(
                id="2",
                source="strava",
                date=datetime(2023, 1, 2),
                duration_minutes=45,
                distance_miles=7.5,
                workout_type="ride"
            )
        ]
        
        aggregated = AggregatedData(
            total_miles=12.5,
            workout_count=2,
            last_updated=datetime(2023, 1, 2, 15, 30, 0),
            sources=["peloton", "strava"],
            period_start=datetime(2023, 1, 1),
            period_end=datetime(2023, 1, 31),
            workouts=workouts
        )
        
        output = TidbytOutput.from_aggregated_data(aggregated)
        
        assert output.total_miles == "12.50"
        assert output.source_count == 2
        assert "12.50 miles from peloton, strava" in output.display_message
        assert "2023-01-02T15:30:00" in output.last_updated
    
    def test_create_fallback(self):
        """Test creating fallback TidbytOutput."""
        fallback = TidbytOutput.create_fallback()
        
        assert fallback.total_miles == "0.00"
        assert fallback.source_count == 0
        assert fallback.display_message == "No data available"
        
        # Test with custom message
        custom_fallback = TidbytOutput.create_fallback("API unavailable")
        assert custom_fallback.display_message == "API unavailable"
    
    def test_valid_iso_formats(self):
        """Test various valid ISO datetime formats."""
        valid_formats = [
            "2023-01-01T12:00:00",
            "2023-01-01T12:00:00.000",
            "2023-01-01T12:00:00Z",
            "2023-01-01T12:00:00.000Z",
            "2023-01-01T12:00:00+00:00",
            "2023-01-01T12:00:00.000+00:00"
        ]
        
        for date_format in valid_formats:
            output = TidbytOutput(
                total_miles="10.00",
                last_updated=date_format,
                source_count=1,
                display_message="Test message"
            )
            assert output.last_updated == date_format