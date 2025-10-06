#!/usr/bin/env python3
"""
Entry point for the Miles Aggregator application.
"""
import argparse
import asyncio
import sys
from datetime import datetime, timezone

from config import get_config, ConfigError
from utils.logging_config import setup_logging
from clients.peloton_client import PelotonClient
from clients.strava_client import StravaClient, StravaAuthenticationError, StravaRateLimitError


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Miles Aggregator - Collect and aggregate cycling data')
    parser.add_argument(
        '--force-refresh',
        action='store_true',
        help='Force refresh data from APIs, bypassing cache'
    )
    return parser.parse_args()

async def main(force_refresh: bool = False):
    """Main entry point for the application."""
    logger = None
    
    try:
        # Set up logging
        logger = setup_logging()
        logger.info("🚴 Miles Aggregator starting up")
        logger.info(f"Force refresh: {force_refresh}")
        
        # Validate configuration
        logger.info("Validating configuration...")
        config = get_config()
        logger.info("✅ Configuration validated successfully")
        
        # Initialize clients
        logger.info("📡 Initializing clients...")
        
        # Initialize Peloton client
        logger.info("   Initializing Peloton client...")
        peloton_client = PelotonClient()
        peloton_config = peloton_client.get_config_summary()
        logger.info(f"   Peloton User ID: {peloton_config['user_id']}")
        
        # Initialize Strava client
        logger.info("   Initializing Strava client...")
        strava_client = StravaClient(
            client_id=config.strava_client_id,
            client_secret=config.strava_client_secret,
            refresh_token=config.strava_refresh_token,
            athlete_id=config.strava_athlete_id,
            api_timeout=config.api_timeout
        )
        strava_config = strava_client.get_config_summary()
        logger.info(f"   Strava Athlete ID: {strava_config['athlete_id']}")
        
    except ConfigError as e:
        if logger:
            logger.error(f"Configuration error: {e}")
        else:
            print(f"❌ Configuration error: {e}")
        return 1
    except ValueError as e:
        if logger:
            logger.error(f"Client initialization error: {e}")
        else:
            print(f"❌ Error: Missing credentials! {e}")
        return 1
    
    try:
        # Test authentication for both clients
        logger.info("🔐 Testing authentication...")
        
        # Authenticate Peloton
        logger.info("   Testing Peloton authentication...")
        peloton_auth_success = await peloton_client.authenticate()
        if not peloton_auth_success:
            logger.warning("⚠️  Peloton authentication failed! Peloton data will be unavailable.")
        else:
            logger.info("✅ Peloton authentication successful!")
        
        # Authenticate Strava
        logger.info("   Testing Strava authentication...")
        strava_auth_success = await strava_client.authenticate()
        if not strava_auth_success:
            logger.warning("⚠️  Strava authentication failed! Strava data will be unavailable.")
        else:
            logger.info("✅ Strava authentication successful!")
        
        # Check if at least one client is authenticated
        if not peloton_auth_success and not strava_auth_success:
            logger.error("❌ No clients authenticated! Please check your credentials.")
            return 1
        
        # Get current year date range
        current_year = datetime.now().year
        start_date = datetime(current_year, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(current_year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        
        logger.info(f"📅 Fetching cycling data for {current_year}...")
        
        # Initialize totals
        total_distance = 0.0
        total_workouts = 0
        total_calories = 0
        total_duration = 0.0
        
        # Fetch Peloton data if authenticated
        peloton_workouts = []
        peloton_distance = 0.0
        if peloton_auth_success:
            try:
                logger.info("   Fetching Peloton workouts...")
                peloton_workouts = await peloton_client.get_cycling_workouts(start_date, end_date)
                peloton_distance = peloton_client.summarize_current_year_distance(peloton_workouts)
                
                peloton_calories = sum(workout.get('calories', 0) for workout in peloton_workouts)
                peloton_duration = sum(workout.get('duration', 0) for workout in peloton_workouts)
                
                logger.info(f"🏃 Found {len(peloton_workouts)} Peloton cycling workouts")
                logger.info(f"   Peloton YTD: {peloton_distance:.2f} miles")
                
                # Add to totals
                total_distance += peloton_distance
                total_workouts += len(peloton_workouts)
                total_calories += peloton_calories
                total_duration += peloton_duration
                
            except Exception as e:
                logger.error(f"❌ Error fetching Peloton data: {e}")
        
        # Fetch Strava data if authenticated
        strava_stats = {}
        strava_distance = 0.0
        if strava_auth_success:
            try:
                logger.info("   Fetching Strava statistics...")
                strava_stats = await strava_client.get_athlete_stats()
                strava_distance = strava_stats.get('ytd_distance_miles', 0.0)
                strava_ride_count = strava_stats.get('ytd_ride_count', 0)
                strava_moving_time = strava_stats.get('ytd_moving_time_hours', 0.0)
                
                logger.info(f"🚴 Retrieved Strava cycling statistics")
                logger.info(f"   Strava YTD: {strava_distance:.2f} miles, {strava_ride_count} rides")
                
                # Add to totals
                total_distance += strava_distance
                total_workouts += strava_ride_count
                
            except StravaRateLimitError:
                logger.error("❌ Strava rate limit exceeded. Please try again later.")
            except StravaAuthenticationError:
                logger.error("❌ Strava authentication failed during data fetch.")
            except Exception as e:
                logger.error(f"❌ Error fetching Strava data: {e}")
        
        # Display results
        logger.info("")
        logger.info("📊 Data Sources Summary:")
        logger.info("=" * 50)
        
        if peloton_auth_success:
            logger.info(f"Peloton: {len(peloton_workouts)} workouts, {peloton_distance:.2f} miles")
        
        if strava_auth_success and strava_stats:
            strava_ride_count = strava_stats.get('ytd_ride_count', 0)
            logger.info(f"Strava: {strava_ride_count} rides, {strava_distance:.2f} miles YTD")
        
        logger.info("")
        logger.info("🎯 Combined Year-to-Date Totals:")
        logger.info("=" * 50)
        logger.info(f"Total Distance: {total_distance:.2f} miles")
        logger.info(f"Total Workouts/Rides: {total_workouts}")
        
        if total_calories > 0:
            logger.info(f"Total Calories (Peloton): {total_calories:,}")
        
        if total_duration > 0:
            logger.info(f"Total Duration (Peloton): {total_duration:.1f} minutes ({total_duration/60:.1f} hours)")
        
        # Show platform breakdown if both are available
        if peloton_auth_success and strava_auth_success and total_distance > 0:
            peloton_percentage = (peloton_distance / total_distance) * 100
            strava_percentage = (strava_distance / total_distance) * 100
            
            logger.info("")
            logger.info("📈 Platform Breakdown:")
            logger.info("=" * 50)
            logger.info(f"Peloton: {peloton_percentage:.1f}% ({peloton_distance:.2f} miles)")
            logger.info(f"Strava: {strava_percentage:.1f}% ({strava_distance:.2f} miles)")
        
        if total_distance == 0:
            logger.info("ℹ️  No cycling data found for the current year.")
        
        logger.info("")
        logger.info("✅ Data aggregation completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Unexpected error occurred: {e}")
        logger.error("Please check your network connection and credentials.")
        return 1


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    # Run the main function
    try:
        exit_code = asyncio.run(main(force_refresh=args.force_refresh))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)