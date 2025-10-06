"""
Strava API client for fetching cycling statistics and workout data.
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import requests

logger = logging.getLogger(__name__)

class StravaRateLimitError(Exception):
    """Raised when Strava API rate limit is exceeded."""
    pass

class StravaAuthenticationError(Exception):
    """Raised when Strava authentication fails."""
    pass

class StravaClient:
    """Client for interacting with Strava API to fetch cycling statistics."""
    
    # Strava API rate limits
    RATE_LIMIT_15MIN = 100  # 100 requests per 15 minutes
    RATE_LIMIT_DAILY = 1000  # 1000 requests per day
    
    def __init__(self, client_id: str, client_secret: str, refresh_token: str, 
                 athlete_id: str, api_timeout: int = 30):
        """
        Initialize Strava client with OAuth2 credentials.
        
        Args:
            client_id: Strava API client ID
            client_secret: Strava API client secret
            refresh_token: OAuth2 refresh token
            athlete_id: Strava athlete ID
            api_timeout: Request timeout in seconds
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.athlete_id = athlete_id
        self.api_timeout = api_timeout
        
        # OAuth2 tokens
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[int] = None
        
        # Rate limiting tracking
        self._request_times: List[float] = []
        self._daily_requests = 0
        self._daily_reset_time = time.time() + 86400  # 24 hours from now
        
        # API endpoints
        self.base_url = "https://www.strava.com/api/v3"
        self.token_url = "https://www.strava.com/oauth/token"
        
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self) -> None:
        """Setup HTTP session with required headers."""
        self.session.headers.update({
            'User-Agent': 'Miles-Aggregator/1.0',
            'Accept': 'application/json',
        })
    
    async def authenticate(self) -> bool:
        """
        Authenticate with Strava API using refresh token.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Check if we already have a valid access token
            if self._is_token_valid():
                logger.info("Using existing valid Strava access token")
                return True
            
            # Refresh the access token
            success = await self._refresh_access_token()
            if success:
                logger.info("Strava authentication successful")
                return True
            else:
                logger.error("Strava authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"Strava authentication error: {e}")
            return False
    
    def _is_token_valid(self) -> bool:
        """Check if current access token is still valid."""
        if not self.access_token or not self.token_expires_at:
            return False
        
        # Add 5 minute buffer before expiration
        return time.time() < (self.token_expires_at - 300)
    
    async def _refresh_access_token(self) -> bool:
        """
        Refresh OAuth2 access token using refresh token.
        
        Returns:
            True if token refresh successful, False otherwise
        """
        try:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': self.refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = self.session.post(
                self.token_url,
                data=data,
                timeout=self.api_timeout
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                self.token_expires_at = token_data['expires_at']
                
                # Update session headers with new token
                self.session.headers['Authorization'] = f'Bearer {self.access_token}'
                
                logger.debug("Access token refreshed successfully")
                return True
            else:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Token refresh request failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return False
    
    async def get_athlete_stats(self) -> Dict[str, Any]:
        """
        Retrieve athlete cycling statistics from Strava.
        
        Returns:
            Dictionary containing athlete cycling statistics
        """
        try:
            # Ensure we're authenticated
            if not await self.authenticate():
                raise StravaAuthenticationError("Failed to authenticate with Strava")
            
            # Check rate limits before making request
            await self._handle_rate_limiting()
            
            # Make API request
            url = f"{self.base_url}/athletes/{self.athlete_id}/stats"
            response = await self._make_request('GET', url)
            
            if response.status_code == 200:
                stats_data = response.json()
                cycling_stats = self._extract_cycling_stats(stats_data)
                logger.info(f"Retrieved Strava cycling stats for athlete {self.athlete_id}")
                return cycling_stats
            else:
                logger.error(f"Failed to fetch athlete stats: {response.status_code} - {response.text}")
                return {}
                
        except StravaRateLimitError:
            logger.error("Strava rate limit exceeded")
            raise
        except StravaAuthenticationError:
            logger.error("Strava authentication failed")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Strava athlete stats: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing Strava athlete stats: {e}")
            raise
    
    def _extract_cycling_stats(self, stats_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract cycling-specific statistics from Strava athlete stats.
        
        Args:
            stats_data: Raw athlete stats from Strava API
            
        Returns:
            Dictionary with cycling statistics
        """
        try:
            # Extract cycling data from different time periods
            cycling_stats = {
                'ytd_ride_totals': stats_data.get('ytd_ride_totals', {}),
                'all_ride_totals': stats_data.get('all_ride_totals', {}),
                'recent_ride_totals': stats_data.get('recent_ride_totals', {}),
            }
            
            # Calculate current year distance in miles
            ytd_distance_meters = cycling_stats['ytd_ride_totals'].get('distance', 0)
            ytd_distance_miles = self._meters_to_miles(ytd_distance_meters)
            
            # Add computed fields
            cycling_stats['ytd_distance_miles'] = round(ytd_distance_miles, 2)
            cycling_stats['ytd_ride_count'] = cycling_stats['ytd_ride_totals'].get('count', 0)
            cycling_stats['ytd_moving_time_hours'] = round(
                cycling_stats['ytd_ride_totals'].get('moving_time', 0) / 3600, 1
            )
            
            # All-time totals
            all_distance_meters = cycling_stats['all_ride_totals'].get('distance', 0)
            all_distance_miles = self._meters_to_miles(all_distance_meters)
            cycling_stats['all_time_distance_miles'] = round(all_distance_miles, 2)
            cycling_stats['all_time_ride_count'] = cycling_stats['all_ride_totals'].get('count', 0)
            
            logger.debug(f"Extracted cycling stats: YTD {ytd_distance_miles:.2f} miles, "
                        f"All-time {all_distance_miles:.2f} miles")
            
            return cycling_stats
            
        except Exception as e:
            logger.error(f"Error extracting cycling stats: {e}")
            return {
                'ytd_distance_miles': 0.0,
                'ytd_ride_count': 0,
                'ytd_moving_time_hours': 0.0,
                'all_time_distance_miles': 0.0,
                'all_time_ride_count': 0,
                'ytd_ride_totals': {},
                'all_ride_totals': {},
                'recent_ride_totals': {},
            }
    
    def _meters_to_miles(self, meters: float) -> float:
        """Convert meters to miles."""
        return meters * 0.000621371
    
    async def _handle_rate_limiting(self) -> None:
        """
        Handle Strava API rate limiting with appropriate delays.
        
        Raises:
            StravaRateLimitError: If rate limits are exceeded
        """
        current_time = time.time()
        
        # Reset daily counter if needed
        if current_time > self._daily_reset_time:
            self._daily_requests = 0
            self._daily_reset_time = current_time + 86400
        
        # Check daily limit
        if self._daily_requests >= self.RATE_LIMIT_DAILY:
            raise StravaRateLimitError("Daily rate limit exceeded")
        
        # Clean old request times (older than 15 minutes)
        cutoff_time = current_time - 900  # 15 minutes
        self._request_times = [t for t in self._request_times if t > cutoff_time]
        
        # Check 15-minute limit
        if len(self._request_times) >= self.RATE_LIMIT_15MIN:
            # Calculate wait time until oldest request is 15 minutes old
            oldest_request = min(self._request_times)
            wait_time = 900 - (current_time - oldest_request)
            
            if wait_time > 0:
                logger.warning(f"Rate limit approaching, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
        
        # Record this request
        self._request_times.append(current_time)
        self._daily_requests += 1
    
    async def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make HTTP request with retry logic and error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            Response object
            
        Raises:
            StravaRateLimitError: If rate limit is exceeded
            StravaAuthenticationError: If authentication fails
        """
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Set timeout if not provided
                kwargs.setdefault('timeout', self.api_timeout)
                
                response = self.session.request(method, url, **kwargs)
                
                # Handle rate limiting
                if response.status_code == 429:
                    # Check rate limit headers
                    rate_limit_15min = response.headers.get('X-RateLimit-Limit', '100,1000').split(',')[0]
                    rate_limit_usage_15min = response.headers.get('X-RateLimit-Usage', '0,0').split(',')[0]
                    
                    logger.warning(f"Rate limit hit: {rate_limit_usage_15min}/{rate_limit_15min} requests")
                    
                    if attempt < max_retries - 1:
                        # Exponential backoff with jitter
                        delay = base_delay * (2 ** attempt) + (time.time() % 1)
                        logger.info(f"Rate limited, retrying in {delay:.1f} seconds")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise StravaRateLimitError("Rate limit exceeded, max retries reached")
                
                # Handle authentication errors
                if response.status_code == 401:
                    logger.warning("Access token expired, attempting refresh")
                    if await self._refresh_access_token():
                        # Retry with new token
                        if attempt < max_retries - 1:
                            continue
                    raise StravaAuthenticationError("Authentication failed")
                
                # Handle other client errors
                if 400 <= response.status_code < 500:
                    logger.error(f"Client error {response.status_code}: {response.text}")
                    return response
                
                # Handle server errors with retry
                if response.status_code >= 500:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Server error {response.status_code}, retrying in {delay:.1f} seconds")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"Server error {response.status_code}: {response.text}")
                        return response
                
                # Success
                return response
                
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Request timeout, retrying in {delay:.1f} seconds")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("Request timeout, max retries reached")
                    raise
            
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Request failed: {e}, retrying in {delay:.1f} seconds")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    raise
        
        # This should never be reached, but just in case
        raise Exception("Unexpected error in request retry logic")
    
    def get_current_year_distance(self) -> float:
        """
        Get current year cycling distance in miles.
        This is a convenience method that requires athlete stats to be fetched first.
        
        Returns:
            Current year distance in miles
        """
        # This method would typically be called after get_athlete_stats()
        # For now, it's a placeholder that would use cached stats
        logger.warning("get_current_year_distance() requires athlete stats to be fetched first")
        return 0.0
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current configuration.
        
        Returns:
            Dictionary with configuration details
        """
        return {
            'client_id': self.client_id,
            'athlete_id': self.athlete_id,
            'base_url': self.base_url,
            'api_timeout': self.api_timeout,
            'has_access_token': bool(self.access_token),
            'token_valid': self._is_token_valid(),
            'daily_requests': self._daily_requests,
            'rate_limit_15min_usage': len(self._request_times),
        }