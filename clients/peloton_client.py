"""
Peloton API client for fetching cycling workout data.
"""
import csv
import io
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import requests
import pytz

logger = logging.getLogger(__name__)

class PelotonClient:
    """Client for interacting with Peloton API to fetch cycling workout data."""
    
    def __init__(self, user_id: Optional[str] = None, session_id: Optional[str] = None, 
                 timezone_str: Optional[str] = None, api_base: Optional[str] = None,
                 platform: Optional[str] = None, api_path: Optional[str] = None,
                 output_file: Optional[str] = None):
        """
        Initialize Peloton client with authentication credentials.
        
        Args:
            user_id: Peloton user ID from browser cookies (or from env PELOTON_USER_ID)
            session_id: Peloton session ID from browser cookies (or from env PELOTON_SESSION_ID)
            timezone_str: Timezone string for timestamp conversion (or from env PELOTON_TIMEZONE)
            api_base: Base API URL (or from env PELOTON_API_BASE)
            platform: Platform identifier (or from env PELOTON_PLATFORM)
            api_path: API path for CSV export (or from env PELOTON_API_PATH)
            output_file: Output filename (or from env PELOTON_OUTPUT_FILE)
        """
        # Load from environment variables if not provided
        self.user_id = user_id or os.getenv('PELOTON_USER_ID')
        self.session_id = session_id or os.getenv('PELOTON_SESSION_ID')
        self.peloton_timezone = timezone_str or os.getenv('PELOTON_TIMEZONE', 'UTC')
        self.api_base = api_base or os.getenv('PELOTON_API_BASE', 'https://api.onepeloton.com/api/user/')
        self.platform = platform or os.getenv('PELOTON_PLATFORM', 'web')
        self.api_path = api_path or os.getenv('PELOTON_API_PATH', '/workout_history_csv?timezone=')
        self.output_file = output_file or os.getenv('PELOTON_OUTPUT_FILE', 'activities.csv')
        
        # Set up timezone
        self.timezone = pytz.timezone(self.peloton_timezone)
        
        # Construct base URL - remove trailing slash from api_base if present
        self.base_url = self.api_base.rstrip('/')
        if not self.base_url.startswith('http'):
            self.base_url = f"https://api.onepeloton.com/{self.base_url}"
        
        # Validate required credentials
        if not self.user_id or not self.session_id:
            raise ValueError("PELOTON_USER_ID and PELOTON_SESSION_ID must be provided")
        
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self) -> None:
        """Setup HTTP session with required headers and cookies."""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/csv,application/json,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://members.onepeloton.com/',
        })
        
        # Set authentication cookies
        self.session.cookies.set('peloton_session_id', self.session_id)
        self.session.cookies.set('user_id', self.user_id)
    
    async def authenticate(self) -> bool:
        """
        Verify authentication with Peloton API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Test authentication by making a simple API call
            # Construct URL based on whether base_url already includes the user path
            if self.base_url.endswith('/user') or self.base_url.endswith('/user/'):
                auth_url = f"{self.base_url.rstrip('/')}/{self.user_id}"
            else:
                auth_url = f"{self.base_url}/api/user/{self.user_id}"
            
            response = self.session.get(auth_url, timeout=30)
            
            if response.status_code == 200:
                logger.info("Peloton authentication successful")
                return True
            else:
                logger.error(f"Peloton authentication failed: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Peloton authentication error: {e}")
            return False
    
    async def get_cycling_workouts(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Retrieve cycling workout data for the specified date range.
        
        Args:
            start_date: Start date for workout data
            end_date: End date for workout data
            
        Returns:
            List of cycling workout dictionaries
        """
        try:
            # Convert dates to timestamps
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())
            
            # Try CSV export endpoint first (more efficient for bulk data)
            try:
                csv_url = self._build_csv_export_url()
                response = self.session.get(csv_url, timeout=30)
                response.raise_for_status()
                
                if response.headers.get('content-type', '').startswith('text/csv'):
                    workouts = self._parse_csv_response(response.text)
                    logger.info(f"Retrieved workouts via CSV export: {len(workouts)} total")
                else:
                    # Fallback to JSON API if CSV doesn't return CSV
                    workouts = await self._get_workouts_json_api(start_timestamp, end_timestamp)
            except Exception as csv_error:
                logger.warning(f"CSV export failed: {csv_error}, falling back to JSON API")
                workouts = await self._get_workouts_json_api(start_timestamp, end_timestamp)
            
            # Filter for cycling workouts in date range
            cycling_workouts = self._filter_cycling_workouts(
                workouts, start_timestamp, end_timestamp
            )
            
            logger.info(f"Retrieved {len(cycling_workouts)} cycling workouts from Peloton")
            return cycling_workouts
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Peloton workouts: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing Peloton workout data: {e}")
            raise
    
    def _build_csv_export_url(self) -> str:
        """
        Build the CSV export URL using environment variables.
        
        Returns:
            Complete CSV export URL
        """
        # Construct the CSV export URL
        if self.base_url.endswith('/user') or self.base_url.endswith('/user/'):
            # Base URL already includes user path
            base = self.base_url.rstrip('/')
            if not base.endswith(self.user_id):
                base = f"{base}/{self.user_id}"
        else:
            # Need to add user path
            base = f"{self.base_url.rstrip('/')}/api/user/{self.user_id}"
        
        # Add the API path and timezone
        csv_url = f"{base}{self.api_path}{self.peloton_timezone}"
        
        logger.debug(f"CSV export URL: {csv_url}")
        return csv_url
    
    async def _get_workouts_json_api(self, start_timestamp: int, end_timestamp: int) -> List[Dict[str, Any]]:
        """
        Fallback method to get workouts via JSON API.
        
        Args:
            start_timestamp: Start timestamp for filtering
            end_timestamp: End timestamp for filtering
            
        Returns:
            List of workout dictionaries
        """
        # Construct JSON API URL
        if self.base_url.endswith('/user') or self.base_url.endswith('/user/'):
            base = self.base_url.rstrip('/')
            if not base.endswith(self.user_id):
                base = f"{base}/{self.user_id}"
            url = f"{base}/workouts"
        else:
            url = f"{self.base_url.rstrip('/')}/api/user/{self.user_id}/workouts"
        
        params = {
            'joins': 'ride,ride.instructor',
            'limit': 1000,  # Large limit to get all workouts
            'page': 0,
            'sort_by': '-created'
        }
        
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        # Handle JSON response
        data = response.json()
        workouts = self._parse_json_response(data)
        
        logger.info(f"Retrieved workouts via JSON API: {len(workouts)} total")
        return workouts
    
    def _parse_csv_response(self, csv_content: str) -> List[Dict[str, Any]]:
        """
        Parse CSV response from Peloton API.
        
        Args:
            csv_content: Raw CSV content string
            
        Returns:
            List of workout dictionaries
        """
        workouts = []
        
        try:
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            
            for row in csv_reader:
                workout = {
                    'id': row.get('Workout Timestamp', ''),
                    'created_at': row.get('Workout Timestamp', ''),
                    'type': row.get('Fitness Discipline', ''),
                    'title': row.get('Class Timestamp', ''),
                    'duration': self._parse_duration(row.get('Length (minutes)', '0')),
                    'distance': self._parse_distance(row.get('Distance (mi)', '0')),
                    'calories': self._parse_int(row.get('Calories Burned', '0')),
                    'avg_heart_rate': self._parse_int(row.get('Avg Heart Rate (bpm)', '0')),
                }
                workouts.append(workout)
                
        except Exception as e:
            logger.error(f"Error parsing CSV response: {e}")
            raise
        
        return workouts
    
    def _parse_json_response(self, json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse JSON response from Peloton API.
        
        Args:
            json_data: JSON response data
            
        Returns:
            List of workout dictionaries
        """
        workouts = []
        
        try:
            workout_data = json_data.get('data', [])
            
            for workout in workout_data:
                parsed_workout = {
                    'id': workout.get('id', ''),
                    'created_at': workout.get('created_at', ''),
                    'type': workout.get('fitness_discipline', ''),
                    'title': workout.get('title', ''),
                    'duration': workout.get('total_work', 0) / 60,  # Convert to minutes
                    'distance': workout.get('distance', 0) * 0.000621371,  # Convert meters to miles
                    'calories': workout.get('calories', 0),
                    'avg_heart_rate': workout.get('avg_heart_rate', 0),
                }
                workouts.append(parsed_workout)
                
        except Exception as e:
            logger.error(f"Error parsing JSON response: {e}")
            raise
        
        return workouts
    
    def _filter_cycling_workouts(self, workouts: List[Dict[str, Any]], 
                                start_timestamp: int, end_timestamp: int) -> List[Dict[str, Any]]:
        """
        Filter workouts for cycling activities within date range.
        
        Args:
            workouts: List of all workouts
            start_timestamp: Start timestamp for filtering
            end_timestamp: End timestamp for filtering
            
        Returns:
            Filtered list of cycling workouts
        """
        cycling_workouts = []
        
        for workout in workouts:
            try:
                # Convert workout timestamp
                workout_time = self._parse_timestamp(workout['created_at'])
                workout_timestamp = int(workout_time.timestamp())
                
                # Check if it's a cycling workout and within date range
                workout_type = workout.get('type', '').lower()
                is_cycling = any(keyword in workout_type for keyword in ['cycling', 'bike', 'spin'])
                
                if (is_cycling and 
                    start_timestamp <= workout_timestamp <= end_timestamp and
                    workout.get('distance', 0) > 0):
                    
                    # Apply timezone conversion
                    workout['created_at'] = self._apply_timezone(workout['created_at'])
                    cycling_workouts.append(workout)
                    
            except Exception as e:
                logger.warning(f"Error processing workout {workout.get('id', 'unknown')}: {e}")
                continue
        
        return cycling_workouts
    
    def _apply_timezone(self, timestamp_input) -> datetime:
        """
        Convert timestamp to configured timezone.
        
        Args:
            timestamp_input: Timestamp string or datetime object to convert
            
        Returns:
            Timezone-aware datetime object
        """
        try:
            # If it's already a datetime object, just convert timezone
            if isinstance(timestamp_input, datetime):
                if timestamp_input.tzinfo is None:
                    # Assume UTC if no timezone info
                    timestamp_input = timestamp_input.replace(tzinfo=timezone.utc)
                return timestamp_input.astimezone(self.timezone)
            
            # Parse timestamp (handle various formats)
            if isinstance(timestamp_input, (int, float)):
                dt = datetime.fromtimestamp(timestamp_input, tz=timezone.utc)
            else:
                # Handle Peloton CSV format: "2019-09-07 20:03 (MDT)"
                if '(' in timestamp_input and ')' in timestamp_input:
                    # Extract just the date/time part before the timezone
                    date_part = timestamp_input.split('(')[0].strip()
                    try:
                        # Parse the date/time part
                        dt = datetime.strptime(date_part, '%Y-%m-%d %H:%M')
                        # Return as UTC (we'll handle timezone conversion later)
                        dt = dt.replace(tzinfo=timezone.utc)
                    except ValueError:
                        # If parsing fails, return a very old date
                        return datetime(1970, 1, 1, tzinfo=timezone.utc)
                else:
                    # Try parsing ISO format first
                    try:
                        dt = datetime.fromisoformat(timestamp_input.replace('Z', '+00:00'))
                    except ValueError:
                        try:
                            # Fallback to timestamp parsing
                            timestamp = float(timestamp_input)
                            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        except (ValueError, TypeError):
                            # If all parsing fails, return a very old date
                            return datetime(1970, 1, 1, tzinfo=timezone.utc)
            
            # Convert to configured timezone
            return dt.astimezone(self.timezone)
            
        except Exception:
            # Silently return a very old date for unparseable timestamps
            return datetime(1970, 1, 1, tzinfo=timezone.utc)
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string to datetime object."""
        try:
            if isinstance(timestamp_str, (int, float)):
                return datetime.fromtimestamp(timestamp_str, tz=timezone.utc)
            else:
                # Handle Peloton CSV format: "2019-09-07 20:03 (MDT)"
                if '(' in timestamp_str and ')' in timestamp_str:
                    # Extract just the date/time part before the timezone
                    date_part = timestamp_str.split('(')[0].strip()
                    try:
                        # Parse the date/time part
                        dt = datetime.strptime(date_part, '%Y-%m-%d %H:%M')
                        # Return as UTC (we'll handle timezone conversion later)
                        return dt.replace(tzinfo=timezone.utc)
                    except ValueError:
                        pass
                
                # Try ISO format
                try:
                    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except ValueError:
                    # Try as Unix timestamp
                    timestamp = float(timestamp_str)
                    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except Exception:
            # Silently return a very old date so it gets filtered out
            return datetime(1970, 1, 1, tzinfo=timezone.utc)
    
    def _parse_duration(self, duration_str: str) -> float:
        """Parse duration string to float minutes."""
        try:
            return float(duration_str)
        except (ValueError, TypeError):
            return 0.0
    
    def _parse_distance(self, distance_str: str) -> float:
        """Parse distance string to float miles."""
        try:
            return float(distance_str)
        except (ValueError, TypeError):
            return 0.0
    
    def _parse_int(self, value_str: str) -> int:
        """Parse string to integer."""
        try:
            return int(float(value_str))
        except (ValueError, TypeError):
            return 0
    
    def summarize_current_year_distance(self, workouts: List[Dict[str, Any]]) -> float:
        """
        Calculate total cycling distance for the current year.
        
        Args:
            workouts: List of workout dictionaries
            
        Returns:
            Total distance in miles for current year
        """
        current_year = datetime.now().year
        total_distance = 0.0
        
        for workout in workouts:
            try:
                # Handle both datetime objects and strings
                created_at = workout['created_at']
                if isinstance(created_at, datetime):
                    workout_date = created_at
                else:
                    workout_date = self._parse_timestamp(created_at)
                
                if workout_date.year == current_year:
                    distance = workout.get('distance', 0)
                    if isinstance(distance, (int, float)) and distance > 0:
                        total_distance += distance
            except Exception as e:
                logger.warning(f"Error processing workout distance: {e}")
                continue
        
        logger.info(f"Total Peloton cycling distance for {current_year}: {total_distance:.2f} miles")
        return round(total_distance, 2)
    
    def save_workouts_to_csv(self, workouts: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """
        Save workouts to CSV file.
        
        Args:
            workouts: List of workout dictionaries
            filename: Output filename (uses PELOTON_OUTPUT_FILE if not provided)
            
        Returns:
            Path to saved file
        """
        output_file = filename or self.output_file
        
        if not workouts:
            logger.warning("No workouts to save")
            return output_file
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                # Use keys from first workout as fieldnames
                fieldnames = workouts[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for workout in workouts:
                    writer.writerow(workout)
            
            logger.info(f"Saved {len(workouts)} workouts to {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Failed to save workouts to CSV: {e}")
            raise
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current configuration.
        
        Returns:
            Dictionary with configuration details
        """
        return {
            'user_id': self.user_id[:8] + '...' if self.user_id else None,
            'session_id': self.session_id[:8] + '...' if self.session_id else None,
            'timezone': self.peloton_timezone,
            'api_base': self.api_base,
            'platform': self.platform,
            'api_path': self.api_path,
            'output_file': self.output_file,
            'base_url': self.base_url
        }   
 
    def save_workouts_to_csv(self, workouts: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """
        Save workouts to CSV file.
        
        Args:
            workouts: List of workout dictionaries
            filename: Output filename (uses PELOTON_OUTPUT_FILE if not provided)
            
        Returns:
            Path to saved file
        """
        output_file = filename or self.output_file
        
        if not workouts:
            logger.warning("No workouts to save")
            return output_file
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                # Use keys from first workout as fieldnames
                fieldnames = workouts[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for workout in workouts:
                    writer.writerow(workout)
            
            logger.info(f"Saved {len(workouts)} workouts to {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Failed to save workouts to CSV: {e}")
            raise
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current configuration.
        
        Returns:
            Dictionary with configuration details
        """
        return {
            'user_id': self.user_id[:8] + '...' if self.user_id else None,
            'session_id': self.session_id[:8] + '...' if self.session_id else None,
            'timezone': self.peloton_timezone,
            'api_base': self.api_base,
            'platform': self.platform,
            'api_path': self.api_path,
            'output_file': self.output_file,
            'base_url': self.base_url
        }