"""
API Service Manager for coordinating data collection from multiple fitness platforms.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from clients.peloton_client import PelotonClient
from clients.strava_client import StravaClient, StravaRateLimitError, StravaAuthenticationError

logger = logging.getLogger(__name__)

class APIManagerError(Exception):
    """Base exception for API Manager errors."""
    pass

class APIManager:
    """
    Manages data collection from multiple fitness API sources with error handling,
    retry logic, and graceful degradation when individual APIs fail.
    """
    
    def __init__(self, peloton_client: Optional[PelotonClient] = None, 
                 strava_client: Optional[StravaClient] = None,
                 default_timeout: int = 30,
                 max_retries: int = 3,
                 base_retry_delay: float = 1.0):
        """
        Initialize API Manager with client instances.
        
        Args:
            peloton_client: Configured Peloton API client
            strava_client: Configured Strava API client
            default_timeout: Default timeout for API requests in seconds
            max_retries: Maximum number of retry attempts for transient failures
            base_retry_delay: Base delay for exponential backoff in seconds
        """
        self.peloton_client = peloton_client
        self.strava_client = strava_client
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.base_retry_delay = base_retry_delay
        
        # Track API availability and errors
        self.api_status = {
            'peloton': {'available': True, 'last_error': None, 'error_count': 0},
            'strava': {'available': True, 'last_error': None, 'error_count': 0}
        }
        
        # Results storage
        self.last_results = {
            'peloton_data': None,
            'strava_data': None,
            'fetch_timestamp': None,
            'successful_sources': [],
            'failed_sources': []
        }
    
    async def fetch_all_data(self, start_date: Optional[datetime] = None, 
                           end_date: Optional[datetime] = None,
                           force_refresh: bool = False) -> Dict[str, Any]:
        """
        Fetch data from all configured API sources sequentially.
        
        Args:
            start_date: Start date for data collection (defaults to current year start)
            end_date: End date for data collection (defaults to now)
            force_refresh: Force refresh even if recent data exists
            
        Returns:
            Dictionary containing aggregated data from all sources
            
        Raises:
            APIManagerError: If all API sources fail
        """
        logger.info("Starting data collection from all API sources")
        
        # Set default date range if not provided
        if not start_date:
            current_year = datetime.now().year
            start_date = datetime(current_year, 1, 1, tzinfo=timezone.utc)
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        # Initialize results
        results = {
            'peloton_data': None,
            'strava_data': None,
            'fetch_timestamp': datetime.now(timezone.utc),
            'successful_sources': [],
            'failed_sources': [],
            'date_range': {
                'start_date': start_date,
                'end_date': end_date
            }
        }
        
        # Fetch from Peloton (sequential, not parallel to respect rate limits)
        if self.peloton_client:
            peloton_data = await self._fetch_peloton_data(start_date, end_date)
            if peloton_data is not None:
                results['peloton_data'] = peloton_data
                results['successful_sources'].append('peloton')
                logger.info("Successfully fetched Peloton data")
            else:
                results['failed_sources'].append('peloton')
                logger.warning("Failed to fetch Peloton data")
        else:
            logger.info("Peloton client not configured, skipping")
        
        # Fetch from Strava (sequential to avoid rate limiting issues)
        if self.strava_client:
            strava_data = await self._fetch_strava_data()
            if strava_data is not None:
                results['strava_data'] = strava_data
                results['successful_sources'].append('strava')
                logger.info("Successfully fetched Strava data")
            else:
                results['failed_sources'].append('strava')
                logger.warning("Failed to fetch Strava data")
        else:
            logger.info("Strava client not configured, skipping")
        
        # Check if we got any data
        if not results['successful_sources']:
            error_msg = "All API sources failed to provide data"
            logger.error(error_msg)
            raise APIManagerError(error_msg)
        
        # Store results for future reference
        self.last_results = results
        
        logger.info(f"Data collection complete. Successful sources: {results['successful_sources']}, "
                   f"Failed sources: {results['failed_sources']}")
        
        return results
    
    async def _fetch_peloton_data(self, start_date: datetime, end_date: datetime) -> Optional[Dict[str, Any]]:
        """
        Fetch data from Peloton API with retry logic and error handling.
        
        Args:
            start_date: Start date for workout data
            end_date: End date for workout data
            
        Returns:
            Peloton data dictionary or None if failed
        """
        source = 'peloton'
        
        for attempt in range(self.max_retries + 1):
            start_time = time.time()
            try:
                logger.debug(f"Attempting Peloton data fetch (attempt {attempt + 1}/{self.max_retries + 1})")
                
                # Apply timeout to the entire operation
                peloton_data = await asyncio.wait_for(
                    self._peloton_fetch_operation(start_date, end_date),
                    timeout=self.default_timeout
                )
                
                # Log successful API call with timing
                elapsed_time = time.time() - start_time
                logger.info(f"Peloton API call successful in {elapsed_time:.2f}s")
                
                # Mark as successful
                self.api_status[source]['available'] = True
                self.api_status[source]['last_error'] = None
                self.api_status[source]['error_count'] = 0
                
                return peloton_data
                
            except asyncio.TimeoutError:
                error_msg = f"Peloton API request timed out after {self.default_timeout} seconds"
                logger.warning(f"{error_msg} (attempt {attempt + 1})")
                self._handle_api_error(source, error_msg)
                
                if attempt < self.max_retries:
                    await self._exponential_backoff(attempt)
                    continue
                
            except Exception as e:
                error_msg = f"Peloton API error: {str(e)}"
                logger.warning(f"{error_msg} (attempt {attempt + 1})")
                self._handle_api_error(source, error_msg)
                
                # Don't retry on authentication errors
                if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                    logger.error("Peloton authentication failed, not retrying")
                    break
                
                if attempt < self.max_retries:
                    await self._exponential_backoff(attempt)
                    continue
        
        # All attempts failed
        self.api_status[source]['available'] = False
        logger.error(f"Peloton data fetch failed after {self.max_retries + 1} attempts")
        return None
    
    async def _peloton_fetch_operation(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Perform the actual Peloton data fetch operation.
        
        Args:
            start_date: Start date for workout data
            end_date: End date for workout data
            
        Returns:
            Dictionary containing Peloton workout data and summary
        """
        # Authenticate first
        auth_success = await self.peloton_client.authenticate()
        if not auth_success:
            raise Exception("Peloton authentication failed")
        
        # Fetch cycling workouts
        workouts = await self.peloton_client.get_cycling_workouts(start_date, end_date)
        
        # Calculate summary statistics
        total_distance = self.peloton_client.summarize_current_year_distance(workouts)
        
        return {
            'workouts': workouts,
            'total_distance_miles': total_distance,
            'workout_count': len(workouts),
            'source': 'peloton',
            'fetch_time': datetime.now(timezone.utc).isoformat()
        }
    
    async def _fetch_strava_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch data from Strava API with retry logic and error handling.
        
        Returns:
            Strava data dictionary or None if failed
        """
        source = 'strava'
        
        for attempt in range(self.max_retries + 1):
            start_time = time.time()
            try:
                logger.debug(f"Attempting Strava data fetch (attempt {attempt + 1}/{self.max_retries + 1})")
                
                # Apply timeout to the entire operation
                strava_data = await asyncio.wait_for(
                    self._strava_fetch_operation(),
                    timeout=self.default_timeout
                )
                
                # Log successful API call with timing
                elapsed_time = time.time() - start_time
                logger.info(f"Strava API call successful in {elapsed_time:.2f}s")
                
                # Mark as successful
                self.api_status[source]['available'] = True
                self.api_status[source]['last_error'] = None
                self.api_status[source]['error_count'] = 0
                
                return strava_data
                
            except asyncio.TimeoutError:
                error_msg = f"Strava API request timed out after {self.default_timeout} seconds"
                logger.warning(f"{error_msg} (attempt {attempt + 1})")
                self._handle_api_error(source, error_msg)
                
                if attempt < self.max_retries:
                    await self._exponential_backoff(attempt)
                    continue
                
            except StravaRateLimitError as e:
                error_msg = f"Strava rate limit exceeded: {str(e)}"
                logger.warning(f"{error_msg} (attempt {attempt + 1})")
                self._handle_api_error(source, error_msg)
                
                # For rate limit errors, use longer backoff
                if attempt < self.max_retries:
                    backoff_time = self.base_retry_delay * (3 ** attempt)  # More aggressive backoff
                    logger.info(f"Rate limited, waiting {backoff_time:.1f} seconds before retry")
                    await asyncio.sleep(backoff_time)
                    continue
                
            except StravaAuthenticationError as e:
                error_msg = f"Strava authentication failed: {str(e)}"
                logger.error(error_msg)
                self._handle_api_error(source, error_msg)
                # Don't retry authentication errors
                break
                
            except Exception as e:
                error_msg = f"Strava API error: {str(e)}"
                logger.warning(f"{error_msg} (attempt {attempt + 1})")
                self._handle_api_error(source, error_msg)
                
                if attempt < self.max_retries:
                    await self._exponential_backoff(attempt)
                    continue
        
        # All attempts failed
        self.api_status[source]['available'] = False
        logger.error(f"Strava data fetch failed after {self.max_retries + 1} attempts")
        return None
    
    async def _strava_fetch_operation(self) -> Dict[str, Any]:
        """
        Perform the actual Strava data fetch operation.
        
        Returns:
            Dictionary containing Strava athlete statistics
        """
        # Authenticate first
        auth_success = await self.strava_client.authenticate()
        if not auth_success:
            raise StravaAuthenticationError("Strava authentication failed")
        
        # Fetch athlete statistics
        athlete_stats = await self.strava_client.get_athlete_stats()
        
        return {
            'athlete_stats': athlete_stats,
            'total_distance_miles': athlete_stats.get('ytd_distance_miles', 0.0),
            'workout_count': athlete_stats.get('ytd_ride_count', 0),
            'source': 'strava',
            'fetch_time': datetime.now(timezone.utc).isoformat()
        }
    
    async def _exponential_backoff(self, attempt: int) -> None:
        """
        Implement exponential backoff with jitter for retry delays.
        
        Args:
            attempt: Current attempt number (0-based)
        """
        # Calculate delay with exponential backoff and jitter
        delay = self.base_retry_delay * (2 ** attempt)
        jitter = (time.time() % 1) * 0.5  # Add up to 0.5 seconds of jitter
        total_delay = delay + jitter
        
        logger.debug(f"Waiting {total_delay:.2f} seconds before retry")
        await asyncio.sleep(total_delay)
    
    def _handle_api_error(self, source: str, error_message: str) -> None:
        """
        Handle API errors by updating status and logging.
        
        Args:
            source: API source name ('peloton' or 'strava')
            error_message: Error message to log and store
        """
        if source in self.api_status:
            self.api_status[source]['last_error'] = error_message
            self.api_status[source]['error_count'] += 1
            
            # Log error with context
            logger.warning(f"API error for {source}: {error_message} "
                          f"(total errors: {self.api_status[source]['error_count']})")
    
    def get_api_status(self) -> Dict[str, Any]:
        """
        Get current status of all API sources.
        
        Returns:
            Dictionary with status information for each API source
        """
        return {
            'api_status': self.api_status.copy(),
            'last_fetch': self.last_results.get('fetch_timestamp'),
            'successful_sources': self.last_results.get('successful_sources', []),
            'failed_sources': self.last_results.get('failed_sources', []),
            'configured_clients': {
                'peloton': self.peloton_client is not None,
                'strava': self.strava_client is not None
            }
        }
    
    def has_recent_data(self, max_age_minutes: int = 60) -> bool:
        """
        Check if we have recent data that might not need refreshing.
        
        Args:
            max_age_minutes: Maximum age of data in minutes to consider recent
            
        Returns:
            True if recent data exists, False otherwise
        """
        if not self.last_results.get('fetch_timestamp'):
            return False
        
        fetch_time = self.last_results['fetch_timestamp']
        if isinstance(fetch_time, str):
            fetch_time = datetime.fromisoformat(fetch_time.replace('Z', '+00:00'))
        
        age_minutes = (datetime.now(timezone.utc) - fetch_time).total_seconds() / 60
        return age_minutes <= max_age_minutes
    
    def get_last_successful_data(self) -> Optional[Dict[str, Any]]:
        """
        Get the last successfully fetched data.
        
        Returns:
            Last successful data or None if no data available
        """
        if self.last_results.get('successful_sources'):
            return self.last_results
        return None
    
    async def test_connectivity(self) -> Dict[str, bool]:
        """
        Test connectivity to all configured API sources.
        
        Returns:
            Dictionary with connectivity test results for each source
        """
        results = {}
        
        if self.peloton_client:
            try:
                logger.info("Testing Peloton connectivity...")
                auth_result = await asyncio.wait_for(
                    self.peloton_client.authenticate(),
                    timeout=self.default_timeout
                )
                results['peloton'] = auth_result
                logger.info(f"Peloton connectivity test: {'PASS' if auth_result else 'FAIL'}")
            except Exception as e:
                logger.error(f"Peloton connectivity test failed: {e}")
                results['peloton'] = False
        
        if self.strava_client:
            try:
                logger.info("Testing Strava connectivity...")
                auth_result = await asyncio.wait_for(
                    self.strava_client.authenticate(),
                    timeout=self.default_timeout
                )
                results['strava'] = auth_result
                logger.info(f"Strava connectivity test: {'PASS' if auth_result else 'FAIL'}")
            except Exception as e:
                logger.error(f"Strava connectivity test failed: {e}")
                results['strava'] = False
        
        return results