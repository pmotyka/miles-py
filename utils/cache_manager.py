"""
Cache management system for Miles Aggregator application.

Provides file-based JSON caching with 24-hour expiration logic,
force refresh bypass functionality, and cache directory management.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CacheManager:
    """
    File-based cache manager with JSON storage and expiration logic.
    
    Supports 24-hour cache expiration, force refresh bypass, and
    automatic cache directory management and cleanup.
    """
    
    def __init__(self, cache_dir: str = ".cache"):
        """
        Initialize cache manager with specified cache directory.
        
        Args:
            cache_dir: Directory path for cache storage (default: ".cache")
        """
        self.cache_dir = Path(cache_dir)
        self._ensure_cache_directory()
        logger.debug(f"CacheManager initialized with cache_dir: {self.cache_dir}")
    
    def _ensure_cache_directory(self) -> None:
        """Create cache directory if it doesn't exist."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Cache directory ensured: {self.cache_dir}")
        except OSError as e:
            logger.error(f"Failed to create cache directory {self.cache_dir}: {e}")
            raise
    
    def _get_cache_file_path(self, key: str) -> Path:
        """
        Get the file path for a cache key.
        
        Args:
            key: Cache key identifier
            
        Returns:
            Path object for the cache file
        """
        # Sanitize key for filesystem safety
        safe_key = "".join(c for c in key if c.isalnum() or c in ('-', '_', '.'))
        return self.cache_dir / f"{safe_key}.json"
    
    def get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached data if valid and not expired.
        
        Args:
            key: Cache key identifier
            
        Returns:
            Cached data dictionary if valid, None otherwise
        """
        cache_file = self._get_cache_file_path(key)
        
        if not cache_file.exists():
            logger.debug(f"Cache miss: file not found for key '{key}'")
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_entry = json.load(f)
            
            # Validate cache entry structure
            if not isinstance(cache_entry, dict) or 'timestamp' not in cache_entry or 'data' not in cache_entry:
                logger.warning(f"Invalid cache entry structure for key '{key}', removing")
                self._remove_cache_file(cache_file)
                return None
            
            # Check if cache is still valid (24 hours by default)
            if self.is_cache_valid(key):
                logger.info(f"Cache hit: returning cached data for key '{key}'")
                return cache_entry['data']
            else:
                logger.info(f"Cache expired for key '{key}', removing")
                self._remove_cache_file(cache_file)
                return None
                
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read cache file for key '{key}': {e}")
            self._remove_cache_file(cache_file)
            return None
    
    def store_data(self, key: str, data: Dict[str, Any]) -> None:
        """
        Store data in cache with current timestamp.
        
        Args:
            key: Cache key identifier
            data: Data to cache
        """
        cache_file = self._get_cache_file_path(key)
        
        cache_entry = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Data cached successfully for key '{key}'")
            logger.debug(f"Cache file written: {cache_file}")
            
        except (OSError, TypeError) as e:
            logger.error(f"Failed to store cache data for key '{key}': {e}")
            raise
    
    def is_cache_valid(self, key: str, max_age_hours: int = 24) -> bool:
        """
        Check if cached data is still valid based on age.
        
        Args:
            key: Cache key identifier
            max_age_hours: Maximum age in hours (default: 24)
            
        Returns:
            True if cache is valid, False otherwise
        """
        cache_file = self._get_cache_file_path(key)
        
        if not cache_file.exists():
            return False
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_entry = json.load(f)
            
            if 'timestamp' not in cache_entry:
                return False
            
            cache_time = datetime.fromisoformat(cache_entry['timestamp'])
            expiry_time = cache_time + timedelta(hours=max_age_hours)
            is_valid = datetime.now() < expiry_time
            
            logger.debug(f"Cache validity check for key '{key}': {is_valid} "
                        f"(cached: {cache_time}, expires: {expiry_time})")
            
            return is_valid
            
        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.warning(f"Failed to validate cache for key '{key}': {e}")
            return False
    
    def clear_cache(self, key: Optional[str] = None) -> None:
        """
        Clear specific cache entry or all cached data.
        
        Args:
            key: Specific cache key to clear, or None to clear all
        """
        if key is not None:
            # Clear specific cache entry
            cache_file = self._get_cache_file_path(key)
            if cache_file.exists():
                self._remove_cache_file(cache_file)
                logger.info(f"Cleared cache for key '{key}'")
            else:
                logger.debug(f"No cache file found for key '{key}'")
        else:
            # Clear all cache files
            cleared_count = 0
            try:
                for cache_file in self.cache_dir.glob("*.json"):
                    self._remove_cache_file(cache_file)
                    cleared_count += 1
                
                logger.info(f"Cleared all cache data ({cleared_count} files)")
                
            except OSError as e:
                logger.error(f"Failed to clear cache directory: {e}")
                raise
    
    def _remove_cache_file(self, cache_file: Path) -> None:
        """
        Safely remove a cache file.
        
        Args:
            cache_file: Path to cache file to remove
        """
        try:
            cache_file.unlink()
            logger.debug(f"Removed cache file: {cache_file}")
        except OSError as e:
            logger.warning(f"Failed to remove cache file {cache_file}: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about cached data.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = {
            'cache_dir': str(self.cache_dir),
            'total_files': 0,
            'valid_files': 0,
            'expired_files': 0,
            'invalid_files': 0,
            'total_size_bytes': 0
        }
        
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                stats['total_files'] += 1
                stats['total_size_bytes'] += cache_file.stat().st_size
                
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_entry = json.load(f)
                    
                    if 'timestamp' not in cache_entry:
                        stats['invalid_files'] += 1
                        continue
                    
                    cache_time = datetime.fromisoformat(cache_entry['timestamp'])
                    expiry_time = cache_time + timedelta(hours=24)
                    
                    if datetime.now() < expiry_time:
                        stats['valid_files'] += 1
                    else:
                        stats['expired_files'] += 1
                        
                except (json.JSONDecodeError, ValueError, OSError):
                    stats['invalid_files'] += 1
                    
        except OSError as e:
            logger.error(f"Failed to get cache stats: {e}")
        
        return stats
    
    def cleanup_expired_cache(self) -> int:
        """
        Remove all expired cache files.
        
        Returns:
            Number of files removed
        """
        removed_count = 0
        
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_entry = json.load(f)
                    
                    if 'timestamp' not in cache_entry:
                        self._remove_cache_file(cache_file)
                        removed_count += 1
                        continue
                    
                    cache_time = datetime.fromisoformat(cache_entry['timestamp'])
                    expiry_time = cache_time + timedelta(hours=24)
                    
                    if datetime.now() >= expiry_time:
                        self._remove_cache_file(cache_file)
                        removed_count += 1
                        
                except (json.JSONDecodeError, ValueError, OSError):
                    # Remove invalid cache files
                    self._remove_cache_file(cache_file)
                    removed_count += 1
                    
        except OSError as e:
            logger.error(f"Failed to cleanup expired cache: {e}")
            raise
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} expired cache files")
        
        return removed_count