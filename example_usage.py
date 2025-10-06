#!/usr/bin/env python3
"""
Example usage of the Peloton client in different scenarios.
"""
import asyncio
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

from clients.peloton_client import PelotonClient


async def example_basic_usage():
    """Basic usage example."""
    print("📚 Example 1: Basic Usage")
    print("-" * 30)
    
    # Load credentials
    load_dotenv()
    
    try:
        # Initialize client (loads from environment variables)
        client = PelotonClient()
    except ValueError:
        print("❌ Missing credentials - using demo mode")
        client = PelotonClient("demo_user", "demo_session", "America/New_York")
    
    # Get current year workouts
    current_year = datetime.now().year
    start_date = datetime(current_year, 1, 1, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)
    
    try:
        # Test authentication first
        if await client.authenticate():
            workouts = await client.get_cycling_workouts(start_date, end_date)
            distance = client.summarize_current_year_distance(workouts)
            print(f"✅ Found {len(workouts)} workouts, total distance: {distance:.2f} miles")
        else:
            print("❌ Authentication failed")
    except Exception as e:
        print(f"❌ Error: {e}")


async def example_date_range_query():
    """Example of querying specific date ranges."""
    print("\n📚 Example 2: Date Range Query")
    print("-" * 35)
    
    load_dotenv()
    
    try:
        client = PelotonClient()
    except ValueError:
        print("❌ Missing credentials - using demo mode")
        client = PelotonClient("demo_user", "demo_session")
    
    # Get last 30 days
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=30)
    
    try:
        if await client.authenticate():
            workouts = await client.get_cycling_workouts(start_date, end_date)
            
            if workouts:
                total_distance = sum(w.get('distance', 0) for w in workouts)
                total_calories = sum(w.get('calories', 0) for w in workouts)
                
                print(f"📅 Last 30 days:")
                print(f"   Workouts: {len(workouts)}")
                print(f"   Distance: {total_distance:.2f} miles")
                print(f"   Calories: {total_calories:,}")
            else:
                print("📅 No workouts found in the last 30 days")
        else:
            print("❌ Authentication failed")
    except Exception as e:
        print(f"❌ Error: {e}")


async def example_workout_analysis():
    """Example of analyzing workout patterns."""
    print("\n📚 Example 3: Workout Analysis")
    print("-" * 33)
    
    load_dotenv()
    
    try:
        client = PelotonClient()
    except ValueError:
        print("❌ Missing credentials - using demo mode")
        client = PelotonClient("demo_user", "demo_session")
    
    # Get current year workouts
    current_year = datetime.now().year
    start_date = datetime(current_year, 1, 1, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)
    
    try:
        if await client.authenticate():
            workouts = await client.get_cycling_workouts(start_date, end_date)
            
            if workouts:
                # Analyze workout types
                workout_types = {}
                monthly_stats = {}
                
                for workout in workouts:
                    # Count by type
                    workout_type = workout.get('type', 'Unknown')
                    workout_types[workout_type] = workout_types.get(workout_type, 0) + 1
                    
                    # Monthly breakdown
                    try:
                        workout_date = client._parse_timestamp(workout['created_at'])
                        month_key = workout_date.strftime('%Y-%m')
                        
                        if month_key not in monthly_stats:
                            monthly_stats[month_key] = {'count': 0, 'distance': 0}
                        
                        monthly_stats[month_key]['count'] += 1
                        monthly_stats[month_key]['distance'] += workout.get('distance', 0)
                    except:
                        continue
                
                print("🏋️ Workout Types:")
                for workout_type, count in workout_types.items():
                    print(f"   {workout_type}: {count} workouts")
                
                print("\n📊 Monthly Breakdown:")
                for month, stats in sorted(monthly_stats.items()):
                    print(f"   {month}: {stats['count']} workouts, {stats['distance']:.1f} miles")
            else:
                print("📊 No workouts found for analysis")
        else:
            print("❌ Authentication failed")
    except Exception as e:
        print(f"❌ Error: {e}")


def example_error_handling():
    """Example of proper error handling."""
    print("\n📚 Example 4: Error Handling")
    print("-" * 31)
    
    async def safe_peloton_call():
        try:
            # Initialize with potentially invalid credentials
            client = PelotonClient("invalid_user", "invalid_session")
            
            # Always test authentication first
            if not await client.authenticate():
                print("⚠️  Authentication failed - check credentials")
                return None
            
            # Proceed with API calls
            current_year = datetime.now().year
            start_date = datetime(current_year, 1, 1, tzinfo=timezone.utc)
            end_date = datetime.now(timezone.utc)
            
            workouts = await client.get_cycling_workouts(start_date, end_date)
            return workouts
            
        except Exception as e:
            print(f"❌ API Error: {e}")
            print("💡 Possible causes:")
            print("   - Network connectivity issues")
            print("   - Peloton API temporarily unavailable")
            print("   - Session expired (re-login to Peloton)")
            return None
    
    # Run the safe call
    asyncio.create_task(safe_peloton_call())
    print("✅ Error handling example completed")


async def main():
    """Run all examples."""
    print("🚴 Peloton Client Usage Examples")
    print("=" * 40)
    
    await example_basic_usage()
    await example_date_range_query()
    await example_workout_analysis()
    example_error_handling()
    
    print("\n" + "=" * 40)
    print("📖 For more examples, see:")
    print("   - main.py (full application)")
    print("   - demo.py (mock data demo)")
    print("   - tests/unit/test_peloton_client.py (test cases)")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Examples interrupted!")
    except Exception as e:
        print(f"❌ Example error: {e}")