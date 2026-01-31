#!/usr/bin/env python3
"""
Example demonstrating how to use the Jingle REST API.
This script shows various API operations.
"""

import requests
import time
import json

# API base URL
BASE_URL = "http://localhost:5000/api"


def print_section(title):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def get_status():
    """Get current status."""
    response = requests.get(f"{BASE_URL}/status")
    print(f"Status: {json.dumps(response.json(), indent=2)}")


def play_music(music_file, fade_in=0.0):
    """Play a music file."""
    response = requests.post(
        f"{BASE_URL}/play",
        json={'music': music_file, 'fade_in': fade_in}
    )
    print(f"Play response: {response.json()}")


def stop_music(fade_out=0.0):
    """Stop playback."""
    response = requests.post(
        f"{BASE_URL}/stop",
        json={'fade_out': fade_out}
    )
    print(f"Stop response: {response.json()}")


def set_volume(volume):
    """Set volume level."""
    response = requests.post(
        f"{BASE_URL}/volume",
        json={'volume': volume}
    )
    print(f"Set volume response: {response.json()}")


def get_volume():
    """Get current volume."""
    response = requests.get(f"{BASE_URL}/volume")
    print(f"Current volume: {response.json()}")


def list_music_files():
    """List available music files."""
    response = requests.get(f"{BASE_URL}/music/list")
    files = response.json().get('music_files', [])
    print(f"Available music files ({len(files)}):")
    for f in files:
        print(f"  - {f}")


def add_schedule(time_spec, music_file, **options):
    """Add a new schedule."""
    response = requests.post(
        f"{BASE_URL}/schedules",
        json={'time': time_spec, 'music': music_file, 'options': options}
    )
    print(f"Add schedule response: {response.json()}")


def get_schedules():
    """Get all schedules."""
    response = requests.get(f"{BASE_URL}/schedules")
    schedules = response.json().get('schedules', [])
    print(f"Active schedules ({len(schedules)}):")
    for s in schedules:
        print(f"  - Next run: {s.get('next_run')}, Interval: {s.get('interval')}, Unit: {s.get('unit')}")


def trigger_event(event_name):
    """Trigger a custom event."""
    response = requests.post(
        f"{BASE_URL}/event",
        json={'event': event_name}
    )
    print(f"Trigger event response: {response.json()}")


def main():
    """Run API examples."""
    print("Jingle API Example")
    print("Make sure the Jingle API server is running:")
    print("  python3 -m jingle.api -c config/jingle.yaml")
    
    try:
        # 1. Get status
        print_section("1. Get Status")
        get_status()
        
        # 2. List music files
        print_section("2. List Music Files")
        list_music_files()
        
        # 3. Volume control
        print_section("3. Volume Control")
        get_volume()
        set_volume(0.5)
        get_volume()
        
        # 4. Play music
        print_section("4. Play Music")
        play_music("morning.mp3", fade_in=1.0)
        time.sleep(3)
        
        # 5. Pause and resume
        print_section("5. Pause and Resume")
        response = requests.post(f"{BASE_URL}/pause")
        print(f"Pause: {response.json()}")
        time.sleep(2)
        
        response = requests.post(f"{BASE_URL}/resume")
        print(f"Resume: {response.json()}")
        time.sleep(2)
        
        # 6. Stop music
        print_section("6. Stop Music")
        stop_music(fade_out=1.0)
        
        # 7. Schedule management
        print_section("7. Schedule Management")
        get_schedules()
        add_schedule("every 30 seconds", "chime.mp3", fade_in=0.5)
        get_schedules()
        
        # 8. Trigger custom event
        print_section("8. Trigger Custom Event")
        trigger_event("sensor_trigger")
        
        print_section("Example Complete!")
        print("\nAPI is working correctly!")
        
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to Jingle API server.")
        print("Please start the server first:")
        print("  python3 -m jingle.api -c config/jingle.yaml")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == '__main__':
    main()
