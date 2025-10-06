"""
Unit tests for CacheManager class.

Tests cache operations, expiration handling, directory management,
and cleanup utilities according to requirements 3.1-3.4.
"""

import json
import os
import tempfile
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, mock_open
from freezegun import freeze_time

from utils.cache_manager import CacheManager


class TestCacheManager:
    """Test suite for CacheManager functionality."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def cache_manager(self, temp_cache_dir):
        """Create CacheManager instance with temporary directory."""
        return CacheManager(cache_dir=temp_cache_dir)
    
    @pytest.fixture
    def sample_data(self):
        """Sample data for testing cache operations."""
        return {
            "total_miles": 150.5,
            "workouts": [
                {"id": "1", "miles": 75.2, "source": "peloton"},
                {"id": "2", "miles": 75.3, "source": "strava"}
            ],
            "last_updated": "2024-01-15T10:30:00"
        }
    
    def test_cache_manager_initialization(self, temp_cache_dir):
        """Test CacheManager initialization and directory creation."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        
        assert cache_manager.cache_dir == Path(temp_cache_dir)
        assert Path(temp_cache_dir).exists()
        assert Path(temp_cache_dir).is_dir()
    
    def test_cache_manager_creates_missing_directory(self):
        """Test that CacheManager creates cache directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_dir = Path(temp_dir) / "cache" / "subdir"
            
            cache_manager = CacheManager(cache_dir=str(non_existent_dir))
            
            assert non_existent_dir.exists()
            assert non_existent_dir.is_dir()
    
    def test_store_and_retrieve_data(self, cache_manager, sample_data):
        """Test storing and retrieving cached data."""
        key = "test_data"
        
        # Store data
        cache_manager.store_data(key, sample_data)
        
        # Retrieve data
        retrieved_data = cache_manager.get_cached_data(key)
        
        assert retrieved_data == sample_data
    
    def test_cache_miss_returns_none(self, cache_manager):
        """Test that cache miss returns None."""
        result = cache_manager.get_cached_data("non_existent_key")
        assert result is None
    
    def test_cache_file_creation(self, cache_manager, sample_data):
        """Test that cache files are created with correct structure."""
        key = "test_file_creation"
        cache_manager.store_data(key, sample_data)
        
        cache_file = cache_manager._get_cache_file_path(key)
        assert cache_file.exists()
        
        with open(cache_file, 'r') as f:
            cache_entry = json.load(f)
        
        assert 'timestamp' in cache_entry
        assert 'data' in cache_entry
        assert cache_entry['data'] == sample_data
        
        # Verify timestamp format
        datetime.fromisoformat(cache_entry['timestamp'])
    
    @freeze_time("2024-01-15 10:00:00")
    def test_cache_expiration_24_hours(self, cache_manager, sample_data):
        """Test 24-hour cache expiration logic."""
        key = "expiration_test"
        
        # Store data at frozen time
        cache_manager.store_data(key, sample_data)
        
        # Check validity immediately
        assert cache_manager.is_cache_valid(key) is True
        
        # Move forward 23 hours - should still be valid
        with freeze_time("2024-01-16 09:00:00"):
            assert cache_manager.is_cache_valid(key) is True
            assert cache_manager.get_cached_data(key) == sample_data
        
        # Move forward 25 hours - should be expired
        with freeze_time("2024-01-16 11:00:00"):
            assert cache_manager.is_cache_valid(key) is False
            assert cache_manager.get_cached_data(key) is None
    
    def test_custom_expiration_time(self, cache_manager, sample_data):
        """Test custom cache expiration time."""
        key = "custom_expiration"
        
        with freeze_time("2024-01-15 10:00:00"):
            cache_manager.store_data(key, sample_data)
        
        # Test with 1-hour expiration
        with freeze_time("2024-01-15 10:30:00"):
            assert cache_manager.is_cache_valid(key, max_age_hours=1) is True
        
        with freeze_time("2024-01-15 11:30:00"):
            assert cache_manager.is_cache_valid(key, max_age_hours=1) is False
    
    def test_clear_specific_cache(self, cache_manager, sample_data):
        """Test clearing specific cache entry."""
        key1 = "data1"
        key2 = "data2"
        
        cache_manager.store_data(key1, sample_data)
        cache_manager.store_data(key2, sample_data)
        
        # Verify both exist
        assert cache_manager.get_cached_data(key1) is not None
        assert cache_manager.get_cached_data(key2) is not None
        
        # Clear only key1
        cache_manager.clear_cache(key1)
        
        # Verify key1 is cleared, key2 remains
        assert cache_manager.get_cached_data(key1) is None
        assert cache_manager.get_cached_data(key2) is not None
    
    def test_clear_all_cache(self, cache_manager, sample_data):
        """Test clearing all cached data."""
        keys = ["data1", "data2", "data3"]
        
        # Store multiple entries
        for key in keys:
            cache_manager.store_data(key, sample_data)
        
        # Verify all exist
        for key in keys:
            assert cache_manager.get_cached_data(key) is not None
        
        # Clear all cache
        cache_manager.clear_cache()
        
        # Verify all are cleared
        for key in keys:
            assert cache_manager.get_cached_data(key) is None
    
    def test_key_sanitization(self, cache_manager, sample_data):
        """Test that cache keys are sanitized for filesystem safety."""
        unsafe_key = "test/key:with*unsafe?chars"
        
        cache_manager.store_data(unsafe_key, sample_data)
        retrieved_data = cache_manager.get_cached_data(unsafe_key)
        
        assert retrieved_data == sample_data
        
        # Check that file was created with sanitized name
        cache_file = cache_manager._get_cache_file_path(unsafe_key)
        assert cache_file.exists()
        # Sanitized name should only contain safe characters
        assert all(c.isalnum() or c in ('-', '_', '.') for c in cache_file.stem)
    
    def test_invalid_cache_file_handling(self, cache_manager):
        """Test handling of corrupted or invalid cache files."""
        key = "invalid_cache"
        cache_file = cache_manager._get_cache_file_path(key)
        
        # Create invalid JSON file
        with open(cache_file, 'w') as f:
            f.write("invalid json content")
        
        # Should return None and remove invalid file
        result = cache_manager.get_cached_data(key)
        assert result is None
        assert not cache_file.exists()
    
    def test_missing_timestamp_handling(self, cache_manager):
        """Test handling of cache files missing timestamp."""
        key = "missing_timestamp"
        cache_file = cache_manager._get_cache_file_path(key)
        
        # Create cache file without timestamp
        invalid_entry = {"data": {"test": "value"}}
        with open(cache_file, 'w') as f:
            json.dump(invalid_entry, f)
        
        # Should return None and remove invalid file
        result = cache_manager.get_cached_data(key)
        assert result is None
        assert not cache_file.exists()
    
    def test_cache_stats(self, cache_manager, sample_data):
        """Test cache statistics functionality."""
        # Initially empty
        stats = cache_manager.get_cache_stats()
        assert stats['total_files'] == 0
        assert stats['valid_files'] == 0
        assert stats['expired_files'] == 0
        
        # Add some cache entries
        with freeze_time("2024-01-15 10:00:00"):
            cache_manager.store_data("valid1", sample_data)
            cache_manager.store_data("valid2", sample_data)
        
        # Add expired entry
        with freeze_time("2024-01-14 10:00:00"):
            cache_manager.store_data("expired1", sample_data)
        
        # Check stats from current time
        with freeze_time("2024-01-15 12:00:00"):
            stats = cache_manager.get_cache_stats()
            assert stats['total_files'] == 3
            assert stats['valid_files'] == 2
            assert stats['expired_files'] == 1
            assert stats['total_size_bytes'] > 0
    
    def test_cleanup_expired_cache(self, cache_manager, sample_data):
        """Test cleanup of expired cache files."""
        # Create valid and expired entries
        with freeze_time("2024-01-15 10:00:00"):
            cache_manager.store_data("valid1", sample_data)
            cache_manager.store_data("valid2", sample_data)
        
        with freeze_time("2024-01-14 08:00:00"):
            cache_manager.store_data("expired1", sample_data)
            cache_manager.store_data("expired2", sample_data)
        
        # Verify all files exist
        assert len(list(cache_manager.cache_dir.glob("*.json"))) == 4
        
        # Cleanup from current time and verify valid entries still exist
        with freeze_time("2024-01-15 12:00:00"):
            removed_count = cache_manager.cleanup_expired_cache()
            
            assert removed_count == 2
            assert len(list(cache_manager.cache_dir.glob("*.json"))) == 2
            
            # Verify valid entries still exist (within same time context)
            assert cache_manager.get_cached_data("valid1") is not None
            assert cache_manager.get_cached_data("valid2") is not None
    
    def test_force_refresh_bypass(self, cache_manager, sample_data):
        """Test force refresh functionality by clearing cache."""
        key = "force_refresh_test"
        
        # Store data
        cache_manager.store_data(key, sample_data)
        assert cache_manager.get_cached_data(key) is not None
        
        # Simulate force refresh by clearing cache
        cache_manager.clear_cache(key)
        assert cache_manager.get_cached_data(key) is None
    
    def test_concurrent_cache_operations(self, cache_manager, sample_data):
        """Test cache operations with multiple keys simultaneously."""
        keys_data = {
            f"concurrent_{i}": {**sample_data, "id": i}
            for i in range(10)
        }
        
        # Store all data
        for key, data in keys_data.items():
            cache_manager.store_data(key, data)
        
        # Retrieve and verify all data
        for key, expected_data in keys_data.items():
            retrieved_data = cache_manager.get_cached_data(key)
            assert retrieved_data == expected_data
    
    def test_cache_directory_permissions_error(self, temp_cache_dir):
        """Test handling of cache directory creation errors."""
        # Create a file where we want to create directory
        blocked_path = Path(temp_cache_dir) / "blocked"
        blocked_path.touch()
        
        # Try to create cache manager with blocked path
        with pytest.raises(OSError):
            CacheManager(cache_dir=str(blocked_path / "cache"))
    
    def test_storage_error_handling(self, cache_manager):
        """Test handling of storage errors."""
        key = "storage_error_test"
        
        # Mock file operations to raise OSError
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = OSError("Disk full")
            
            with pytest.raises(OSError):
                cache_manager.store_data(key, {"test": "data"})