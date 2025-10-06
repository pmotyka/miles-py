# Miles Aggregator

A Python application for aggregating cycling workout data from multiple fitness platforms including Peloton and Strava.

## Features

- 🚴 Fetch cycling workout data from Peloton API
- 🏃 Retrieve cycling statistics from Strava API
- 📊 Calculate year-to-date distance totals across platforms
- 🌍 Timezone-aware timestamp handling
- 📈 Workout statistics and averages
- 🔐 OAuth2 and session-based authentication
- ⚡ Rate limiting and retry logic for API reliability
- 🔄 Automatic token refresh for Strava OAuth2

## Quick Start

```bash
# Complete setup (installs dependencies and creates .env template)
make dev-setup

# Run demo with mock data (no credentials needed)
make demo

# Edit .env with your Peloton credentials, then:
make run
```

## Manual Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure credentials:**
   - Copy `.env.example` to `.env`
   - Update with your Peloton credentials (see instructions below)

3. **Run the application:**
   ```bash
   python3 main.py
   ```

## Getting Credentials

### Peloton Credentials

To use Peloton data, you need to extract your session credentials from your browser:

1. **Log into Peloton** in your web browser at https://members.onepeloton.com/
2. **Open Developer Tools** (F12 or right-click → Inspect)
3. **Go to Application/Storage tab** → Cookies → https://members.onepeloton.com
4. **Find these cookie values:**
   - `peloton_session_id` → Use as `PELOTON_SESSION_ID`
   - `user_id` → Use as `PELOTON_USER_ID`

### Strava Credentials

To use Strava data, you need to create a Strava API application:

1. **Create a Strava App** at https://www.strava.com/settings/api
2. **Get your credentials:**
   - Client ID → Use as `STRAVA_CLIENT_ID`
   - Client Secret → Use as `STRAVA_CLIENT_SECRET`
3. **Get a refresh token** using OAuth2 flow (see Strava API documentation)
4. **Find your athlete ID** from your Strava profile URL or API

## Configuration

Update your `.env` file with the extracted values:

```env
# Peloton Configuration
PELOTON_USER_ID=your_actual_user_id
PELOTON_SESSION_ID=your_actual_session_id

# Strava Configuration
STRAVA_CLIENT_ID=your_strava_client_id
STRAVA_CLIENT_SECRET=your_strava_client_secret
STRAVA_REFRESH_TOKEN=your_strava_refresh_token
STRAVA_ATHLETE_ID=your_strava_athlete_id

# General Configuration
TIMEZONE=America/New_York
API_TIMEOUT=30
```

## Example Output

```
🚴 Miles Aggregator - Multi-Platform Cycling Data
==================================================
📡 Initializing clients...
   Peloton client for user: 12345678...
   Strava client for athlete: 87654321...

🔐 Testing authentication...
✅ Peloton authentication successful!
✅ Strava authentication successful!

📅 Fetching cycling data for 2025...
🏃 Found 15 Peloton cycling workouts
🚴 Retrieved Strava cycling statistics

📊 Data Sources Summary:
------------------------------
Peloton Workouts: 15 rides, 245.80 miles
Strava Statistics: 42 rides, 1,250.50 miles YTD

🎯 Combined Year-to-Date Totals:
--------------------------------
Total Workouts: 57 rides
Total Distance: 1,496.30 miles
Peloton Contribution: 16.4%
Strava Contribution: 83.6%

📈 Platform Breakdown:
----------------------
Peloton:
  - Avg Distance: 16.39 miles per ride
  - Total Calories: 6,750
  - Total Duration: 11.3 hours

Strava:
  - YTD Distance: 1,250.50 miles
  - YTD Rides: 42
  - YTD Moving Time: 65.2 hours

✅ Data aggregation completed successfully!
```

## Development

### Available Commands

```bash
# Show all available commands
make help

# Run tests
make test
make test-cov  # with coverage

# Run demos and examples
make demo      # mock data demo
make examples  # usage examples
make run       # real application

# Code quality
make format    # format code
make lint      # lint code
make type-check # type checking
make check     # run all quality checks
```

### Manual Commands

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=clients --cov-report=term-missing

# Run specific test file
python3 -m pytest tests/unit/test_peloton_client.py -v
```

## Project Structure

```
├── clients/
│   ├── __init__.py
│   ├── peloton_client.py      # Peloton API client
│   └── strava_client.py       # Strava API client
├── models/
│   ├── __init__.py
│   ├── workout.py             # Workout data model
│   ├── aggregated_data.py     # Aggregated data model
│   ├── tidbyt_output.py       # Tidbyt display model
│   └── validation_utils.py    # Data validation utilities
├── tests/
│   ├── unit/
│   │   ├── test_peloton_client.py
│   │   ├── test_strava_client.py
│   │   ├── test_workout.py
│   │   ├── test_aggregated_data.py
│   │   └── test_config.py
│   └── fixtures/
│       ├── peloton_response.csv
│       └── peloton_response.json
├── utils/
│   └── logging_config.py      # Logging configuration
├── config.py                  # Configuration management
├── main.py                    # Entry point
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
└── .env.example              # Configuration template
```

## Security Notes

- Never commit your `.env` file with real credentials
- Session IDs expire periodically - you'll need to refresh them
- Keep your credentials secure and don't share them

## Troubleshooting

### Authentication Issues

**Peloton:**
- Verify your session hasn't expired by logging into Peloton web
- Double-check the cookie values are copied correctly
- Ensure no extra spaces in your `.env` file

**Strava:**
- Verify your refresh token is valid and hasn't been revoked
- Check that your Strava app has the correct permissions
- Ensure your client ID and secret are correct

### No Data Found
- Check that you have cycling workouts/activities in the current year
- Verify your timezone setting matches your location
- For Strava, ensure your activities are marked as "Ride" type

### Network Issues
- Check your internet connection
- APIs may be temporarily unavailable
- Rate limiting applies - the app handles this automatically
- Strava has strict rate limits (100 requests per 15 minutes, 1000 per day)