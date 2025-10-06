"""
Integration tests for CacheManager with the Miles Aggregator application.

Tests cache integration with real file system operations and
validates cache behavior in application context.
"""

import json
import tempfile
import pytest
from datetime import datetime, timedelta
from pathlib import Path

from utils.cache_manager import CacheManager


class TestCacheIntegration:
    """Integration tests for CacheManager functionality."""
    
    def test_cache_integration_with_real_filesystem(self):
        """Test CacheManager with real filesystem operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            # Simulate real application data
            workout_data = {
                "peloton_data": [
                    {
                        "id": "peloton_123",
                        "distance": 25.5,
                        "duration": 45,
                        "date": "2024-01-15T10:30:00Z"
                    }
                ],
                "strava_data": {
                    "ytd_ride_totals": {
                        "distance": 1500000,  # meters
                        "count": 50
                    }
                },
                "aggregated_miles": 956.25,
                "last_updated": datetime.now().isoformat()
            }
            
            # Test complete cache workflow
            cache_key = "workout_data_2024_01_15"
            
            # 1. Initial cache miss
            assert cache_manager.get_cached_data(cache_key) is None
            
            # 2. Store data
            cache_manager.store_data(cache_key, workout_data)
            
            # 3. Cache hit
            cached_data = cache_manager.get_cached_data(cache_key)
            assert cached_data == workout_data
            
            # 4. Verify cache file structure
            cache_file = cache_manager._get_cache_file_path(cache_key)
            assert cache_file.exists()
            
            with open(cache_file, 'r') as f:
                cache_entry = json.load(f)
            
            assert 'timestamp' in cache_entry
            assert 'data' in cache_entry
            assert cache_entry['data'] == workout_data
    
    def test_cache_with_multiple_data_sources(self):
        """Test caching data from multiple API sources."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            # Separate cache entries for different data sources
            peloton_data = {
                "workouts": [{"id": "p1", "miles": 15.5}],
                "source": "peloton"
            }
            
            strava_data = {
                "stats": {"ytd_ride_totals": {"distance": 500000}},
                "source": "strava"
            }
            
            # Store data from different sources
            cache_manager.store_data("peloton_cache", peloton_data)
            cache_manager.store_data("strava_cache", strava_data)
            
            # Verify both can be retrieved independently
            assert cache_manager.get_cached_data("peloton_cache") == peloton_data
            assert cache_manager.get_cached_data("strava_cache") == strava_data
            
            # Verify cache stats
            stats = cache_manager.get_cache_stats()
            assert stats['total_files'] == 2
            assert stats['valid_files'] == 2
    
    def test_cache_directory_management(self):
        """Test cache directory creation and management."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test nested cache directory creation
            nested_cache_dir = Path(temp_dir) / "app_cache" / "miles_aggregator"
            cache_manager = CacheManager(cache_dir=str(nested_cache_dir))
            
            # Verify directory was created
            assert nested_cache_dir.exists()
            assert nested_cache_dir.is_dir()
            
            # Test cache operations in nested directory
            test_data = {"test": "nested_cache"}
            cache_manager.store_data("nested_test", test_data)
            
            assert cache_manager.get_cached_data("nested_test") == test_data
    
    def test_cache_cleanup_workflow(self):
        """Test complete cache cleanup workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            # Create multiple cache entries
            for i in range(5):
                cache_manager.store_data(f"data_{i}", {"value": i})
            
            # Verify all created
            stats = cache_manager.get_cache_stats()
            assert stats['total_files'] == 5
            
            # Clear specific entries
            cache_manager.clear_cache("data_0")
            cache_manager.clear_cache("data_1")
            
            stats = cache_manager.get_cache_stats()
            assert stats['total_files'] == 3
            
            # Clear all remaining
            cache_manager.clear_cache()
            
            stats = cache_manager.get_cache_stats()
            assert stats['total_files'] == 0
    
    def test_cache_with_application_like_keys(self):
        """Test cache with realistic application cache keys."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            # Test various key formats that might be used in the application
            test_cases = [
                ("daily_workout_data", {"date": "2024-01-15"}),
                ("peloton_api_response_user_123", {"user_id": "123"}),
                ("strava_athlete_stats_456", {"athlete_id": "456"}),
                ("aggregated_miles_2024_01", {"month": "2024-01"}),
                ("tidbyt_output_latest", {"format": "json"})
            ]
            
            # Store all test data
            for key, data in test_cases:
                cache_manager.store_data(key, data)
            
            # Verify all can be retrieved
            for key, expected_data in test_cases:
                cached_data = cache_manager.get_cached_data(key)
                assert cached_data == expected_data
            
            # Verify cache statistics
            stats = cache_manager.get_cache_stats()
            assert stats['total_files'] == len(test_cases)
            assert stats['valid_files'] == len(test_cases)
            assert stats['expired_files'] == 0