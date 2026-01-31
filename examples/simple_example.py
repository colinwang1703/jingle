#!/usr/bin/env python3
"""
Simple example demonstrating basic Jingle usage.
"""

import time
from jingle import ConfigManager, AudioPlayer, MusicScheduler


def main():
    print("Jingle - Simple Example")
    print("=" * 50)
    
    # Create a simple player
    player = AudioPlayer(music_dir="./music", volume=0.7)
    
    # Create scheduler
    scheduler = MusicScheduler(player=player)
    
    # Add some schedules (using short intervals for demo)
    print("\nAdding schedules:")
    scheduler.add_schedule("every 10 seconds", "morning.mp3")
    print("  - Play morning.mp3 every 10 seconds")
    
    scheduler.add_schedule("every 15 seconds", "afternoon.mp3", fade_in=1.0)
    print("  - Play afternoon.mp3 every 15 seconds with fade-in")
    
    # Start scheduler
    scheduler.start()
    print("\nScheduler started. Playing music...")
    print("Press Ctrl+C to stop\n")
    
    try:
        # Let it run
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping...")
        scheduler.stop()
        player.cleanup()
        print("Goodbye!")


if __name__ == '__main__':
    main()
