#!/usr/bin/env python3
"""
Demo script showing Peloton client functionality with mock data.
This runs without requiring real Peloton credentials.
"""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from clients.peloton_client import PelotonClient


async def demo_with_mock_data():
    """Demonstrate Peloton client functionality with mock data."""
    print("🚴 Miles Aggregator - Demo with Mock Data")
    print("=" * 50)
    
    # Initialize client with dummy credentials
    client = PelotonClient("demo_user", "demo_session", "America/New_York")
    
    # Mock workout data
    mock_workouts = [
        {
            'id': 'workout_1',
            'created_at': '2025-01-15T10:00:00Z',
            'type': 'Cycling',
            'title': '30 Min HIIT Ride',
            'distance': 12.5,
            'calories': 350,
            'duration': 30.0,
            'avg_heart_rate': 145
        },
        {
            'id': 'workout_2',
            'created_at': '2025-01-10T09:30:00Z',
            'type': 'Cycling',
            'title': '45 Min Power Zone Ride',
            'distance': 18.2,
            'calories': 480,
            'duration': 45.0,
            'avg_heart_rate': 152
        },
        {
            'id': 'workout_3',
            'created_at': '2025-01-05T08:00:00Z',
            'type': 'Bike Bootcamp',
            'title': '60 Min Bike Bootcamp',
            'distance': 25.0,
            'calories': 650,
            'duration': 60.0,
            'avg_heart_rate': 155
        },
        {
            'id': 'workout_4',
            'created_at': '2025-01-01T07:00:00Z',
            'type': 'Cycling',
            'title': '20 Min Recovery Ride',
            'distance': 8.3,
            'calories': 180,
            'duration': 20.0,
            'avg_heart_rate': 125
        }
    ]
    
    print("📡 Initializing Peloton client (demo mode)...")
    print("🔐 Simulating authentication...")
    print("✅ Authentication successful! (mocked)")
    
    current_year = datetime.now().year
    print(f"📅 Fetching cycling workouts for {current_year}... (mocked)")
    
    # Simulate the client methods
    workouts = mock_workouts
    print(f"🏃 Found {len(workouts)} cycling workouts")
    print()
    
    if workouts:
        # Display workout summary
        print("📊 Workout Summary:")
        print("-" * 30)
        
        total_workouts = len(workouts)
        total_distance = 0.0
        total_calories = 0
        total_duration = 0.0
        
        for i, workout in enumerate(workouts, 1):
            distance = workout.get('distance', 0)
            calories = workout.get('calories', 0)
            duration = workout.get('duration', 0)
            created_at = workout.get('created_at', 'Unknown')
            
            total_distance += distance
            total_calories += calories
            total_duration += duration
            
            print(f"{i}. {workout.get('type', 'Unknown')} - {distance:.1f} mi, "
                  f"{calories} cal, {duration:.0f} min")
            print(f"   Title: {workout.get('title', 'Unknown')}")
            print(f"   Date: {created_at}")
            print()
        
        # Calculate current year distance using client method
        current_year_distance = client.summarize_current_year_distance(workouts)
        
        print("🎯 Year-to-Date Totals:")
        print("-" * 25)
        print(f"Total Workouts: {total_workouts}")
        print(f"Total Distance: {current_year_distance:.2f} miles")
        print(f"Total Calories: {total_calories:,}")
        print(f"Total Duration: {total_duration:.1f} minutes ({total_duration/60:.1f} hours)")
        
        if total_workouts > 0:
            avg_distance = current_year_distance / total_workouts
            avg_calories = total_calories / total_workouts
            avg_duration = total_duration / total_workouts
            
            print()
            print("📈 Averages per Workout:")
            print("-" * 25)
            print(f"Avg Distance: {avg_distance:.2f} miles")
            print(f"Avg Calories: {avg_calories:.0f}")
            print(f"Avg Duration: {avg_duration:.1f} minutes")
    
    print()
    print("✅ Demo completed successfully!")
    print()
    print("💡 To use with real data:")
    print("   1. Set up your .env file with Peloton credentials")
    print("   2. Run: python main.py")


def demo_csv_parsing():
    """Demonstrate CSV parsing functionality."""
    print("\n🔧 CSV Parsing Demo:")
    print("-" * 20)
    
    client = PelotonClient("demo_user", "demo_session")
    
    # Sample CSV data
    csv_data = """Workout Timestamp,Fitness Discipline,Class Timestamp,Length (minutes),Distance (mi),Calories Burned,Avg Heart Rate (bpm)
1640995200,Cycling,2022-01-01 10:00:00,30,12.5,350,145
1641081600,Cycling,2022-01-02 11:00:00,45,18.2,480,152"""
    
    workouts = client._parse_csv_response(csv_data)
    
    print(f"Parsed {len(workouts)} workouts from CSV:")
    for workout in workouts:
        print(f"  - {workout['type']}: {workout['distance']} mi, {workout['calories']} cal")


def demo_json_parsing():
    """Demonstrate JSON parsing functionality."""
    print("\n🔧 JSON Parsing Demo:")
    print("-" * 21)
    
    client = PelotonClient("demo_user", "demo_session")
    
    # Sample JSON data
    json_data = {
        "data": [
            {
                "id": "workout_123",
                "created_at": 1640995200,
                "fitness_discipline": "cycling",
                "title": "30 Min HIIT Ride",
                "total_work": 1800,
                "distance": 20116.8,  # meters
                "calories": 350,
                "avg_heart_rate": 145
            }
        ]
    }
    
    workouts = client._parse_json_response(json_data)
    
    print(f"Parsed {len(workouts)} workouts from JSON:")
    for workout in workouts:
        print(f"  - {workout['type']}: {workout['distance']:.1f} mi, {workout['calories']} cal")


if __name__ == "__main__":
    try:
        asyncio.run(demo_with_mock_data())
        demo_csv_parsing()
        demo_json_parsing()
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted!")
    except Exception as e:
        print(f"❌ Demo error: {e}")