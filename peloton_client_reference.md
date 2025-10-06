# 🚴 Peloton Client - Complete Method Reference

## Overview
The `PelotonClient` class provides a comprehensive interface for interacting with Peloton's API to fetch and analyze cycling workout data.

## 📋 Public Methods (Main API)

### 1. `__init__()` - Constructor
**Purpose:** Initialize the Peloton client with authentication credentials

```python
# Load from environment variables (.env file)
client = PelotonClient()

# Or provide credentials explicitly
client = PelotonClient(
    user_id="your_user_id",
    session_id="your_session_id",
    timezone_str="America/New_York",
    api_base="https://api.onepeloton.com/api/user/",
    platform="web",
    api_path="/workout_history_csv?timezone=",
    output_file="my_workouts.csv"
)
```

**Parameters:**
- `user_id` (Optional[str]): Peloton user ID from browser cookies
- `session_id` (Optional[str]): Peloton session ID from browser cookies
- `timezone_str` (Optional[str]): Timezone for timestamp conversion
- `api_base` (Optional[str]): Base API URL
- `platform` (Optional[str]): Platform identifier (web/mobile)
- `api_path` (Optional[str]): API path for CSV export
- `output_file` (Optional[str]): Default output filename

**Environment Variables:**
- `PELOTON_USER_ID`
- `PELOTON_SESSION_ID`
- `PELOTON_TIMEZONE`
- `PELOTON_API_BASE`
- `PELOTON_PLATFORM`
- `PELOTON_API_PATH`
- `PELOTON_OUTPUT_FILE`

---

### 2. `authenticate()` - Verify Authentication
**Purpose:** Test if the provided credentials are valid

```python
# Test authentication
is_authenticated = await client.authenticate()
if is_authenticated:
    print("✅ Authentication successful!")
else:
    print("❌ Authentication failed!")
```

**Returns:** `bool` - True if authentication successful, False otherwise

**Use Cases:**
- Validate credentials before making API calls
- Check if session has expired
- Troubleshoot connection issues

---

### 3. `get_cycling_workouts()` - Fetch Workout Data
**Purpose:** Retrieve cycling workout data for a specified date range

```python
from datetime import datetime, timezone

# Get current year workouts
current_year = datetime.now().year
start_date = datetime(current_year, 1, 1, tzinfo=timezone.utc)
end_date = datetime.now(timezone.utc)

workouts = await client.get_cycling_workouts(start_date, end_date)
print(f"Found {len(workouts)} cycling workouts")

# Get last 30 days
from datetime import timedelta
end_date = datetime.now(timezone.utc)
start_date = end_date - timedelta(days=30)
recent_workouts = await client.get_cycling_workouts(start_date, end_date)
```

**Parameters:**
- `start_date` (datetime): Start date for workout data
- `end_date` (datetime): End date for workout data

**Returns:** `List[Dict[str, Any]]` - List of cycling workout dictionaries

**Workout Dictionary Structure:**
```python
{
    'id': 'workout_123',
    'created_at': datetime_object,
    'type': 'Cycling',
    'title': '30 Min HIIT Ride',
    'duration': 30.0,  # minutes
    'distance': 12.5,  # miles
    'calories': 350,
    'avg_heart_rate': 145
}
```

**Features:**
- Tries CSV export first (more efficient)
- Falls back to JSON API if CSV fails
- Filters for cycling-related workouts only
- Applies timezone conversion
- Handles various timestamp formats

---

### 4. `summarize_current_year_distance()` - Calculate Year Distance
**Purpose:** Calculate total cycling distance for the current year

```python
# Get workouts and calculate year total
workouts = await client.get_cycling_workouts(start_date, end_date)
total_distance = client.summarize_current_year_distance(workouts)
print(f"Total cycling distance this year: {total_distance:.2f} miles")

# You can also use it with any workout list
specific_workouts = [workout for workout in workouts if 'HIIT' in workout.get('title', '')]
hiit_distance = client.summarize_current_year_distance(specific_workouts)
```

**Parameters:**
- `workouts` (List[Dict[str, Any]]): List of workout dictionaries

**Returns:** `float` - Total distance in miles for current year

**Features:**
- Filters workouts by current year automatically
- Handles invalid/missing distance data gracefully
- Returns rounded result (2 decimal places)

---

### 5. `save_workouts_to_csv()` - Export to CSV
**Purpose:** Save workout data to a CSV file

```python
# Save to default file (from PELOTON_OUTPUT_FILE)
workouts = await client.get_cycling_workouts(start_date, end_date)
saved_path = client.save_workouts_to_csv(workouts)
print(f"Workouts saved to: {saved_path}")

# Save to specific file
custom_path = client.save_workouts_to_csv(workouts, "my_custom_workouts.csv")

# Save filtered workouts
recent_workouts = [w for w in workouts if w.get('distance', 0) > 10]
client.save_workouts_to_csv(recent_workouts, "long_rides.csv")
```

**Parameters:**
- `workouts` (List[Dict[str, Any]]): List of workout dictionaries
- `filename` (Optional[str]): Output filename (uses default if not provided)

**Returns:** `str` - Path to saved file

**Features:**
- Uses CSV headers from workout dictionary keys
- Handles empty workout lists gracefully
- Creates file with UTF-8 encoding
- Overwrites existing files

---

### 6. `get_config_summary()` - View Configuration
**Purpose:** Get a summary of current client configuration

```python
# View current configuration
config = client.get_config_summary()
print("Current Configuration:")
for key, value in config.items():
    print(f"  {key}: {value}")

# Check specific settings
print(f"Timezone: {config['timezone']}")
print(f"API Base: {config['api_base']}")
print(f"Output File: {config['output_file']}")
```

**Returns:** `Dict[str, Any]` - Configuration dictionary

**Configuration Keys:**
- `user_id`: Masked user ID (first 8 chars + "...")
- `session_id`: Masked session ID (first 8 chars + "...")
- `timezone`: Configured timezone
- `api_base`: Base API URL
- `platform`: Platform identifier
- `api_path`: CSV export API path
- `output_file`: Default output filename
- `base_url`: Constructed base URL

**Use Cases:**
- Debug configuration issues
- Verify environment variable loading
- Display current settings to user

---

## 🔧 Private Methods (Internal Use)

These methods are used internally by the public methods:

- `_setup_session()`: Configure HTTP session with headers and cookies
- `_build_csv_export_url()`: Construct CSV export URL
- `_get_workouts_json_api()`: Fallback JSON API method
- `_parse_csv_response()`: Parse CSV response data
- `_parse_json_response()`: Parse JSON response data
- `_filter_cycling_workouts()`: Filter for cycling workouts in date range
- `_apply_timezone()`: Convert timestamps to configured timezone
- `_parse_timestamp()`: Parse various timestamp formats
- `_parse_duration()`: Parse duration strings to float minutes
- `_parse_distance()`: Parse distance strings to float miles
- `_parse_int()`: Parse strings to integers with fallback

---

## 🚀 Complete Usage Example

```python
import asyncio
from datetime import datetime, timezone, timedelta
from clients.peloton_client import PelotonClient

async def main():
    # Initialize client (loads from .env)
    client = PelotonClient()
    
    # Check configuration
    config = client.get_config_summary()
    print(f"Using timezone: {config['timezone']}")
    
    # Verify authentication
    if not await client.authenticate():
        print("Authentication failed!")
        return
    
    # Get current year workouts
    current_year = datetime.now().year
    start_date = datetime(current_year, 1, 1, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)
    
    workouts = await client.get_cycling_workouts(start_date, end_date)
    print(f"Found {len(workouts)} workouts")
    
    # Calculate statistics
    total_distance = client.summarize_current_year_distance(workouts)
    total_calories = sum(w.get('calories', 0) for w in workouts)
    
    print(f"Total distance: {total_distance:.2f} miles")
    print(f"Total calories: {total_calories:,}")
    
    # Save to CSV
    saved_file = client.save_workouts_to_csv(workouts)
    print(f"Data saved to: {saved_file}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🛠️ Error Handling

The client includes comprehensive error handling:

```python
try:
    client = PelotonClient()
except ValueError as e:
    print(f"Configuration error: {e}")

try:
    workouts = await client.get_cycling_workouts(start_date, end_date)
except requests.exceptions.RequestException as e:
    print(f"Network error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

Common error scenarios:
- Missing credentials (ValueError)
- Network connectivity issues (RequestException)
- Invalid date ranges
- API rate limiting
- Session expiration