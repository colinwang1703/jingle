#!/usr/bin/env python3
"""
Advanced example demonstrating event-driven playback.
"""

import time
import random
from jingle import AudioPlayer, MusicScheduler


def main():
    print("Jingle - Event-Driven Example")
    print("=" * 50)
    
    # Create player and scheduler
    player = AudioPlayer(music_dir="./music", volume=0.7)
    scheduler = MusicScheduler(player=player)
    
    # Define event handlers
    def on_sensor_trigger():
        """Simulate sensor-triggered playback."""
        print("[EVENT] Sensor triggered - playing alert")
        player.play("alert.mp3")
    
    def on_network_request(music_file):
        """Simulate API-triggered playback."""
        print(f"[EVENT] Network request - playing {music_file}")
        player.play(music_file, fade_in=1.0)
    
    def on_custom_event():
        """Custom event handler."""
        print("[EVENT] Custom event triggered")
        player.play("chime.mp3")
    
    # Register event handlers
    scheduler.add_event_handler("sensor_trigger", on_sensor_trigger)
    scheduler.add_event_handler("network_request", on_network_request)
    scheduler.add_event_handler("custom_event", on_custom_event)
    
    print("\nEvent handlers registered:")
    print("  - sensor_trigger")
    print("  - network_request")
    print("  - custom_event")
    
    # Start scheduler
    scheduler.start()
    
    # Simulate random events
    print("\nSimulating random events (press Ctrl+C to stop)...\n")
    
    try:
        event_count = 0
        while event_count < 10:  # Simulate 10 events
            time.sleep(3)  # Wait between events
            
            # Randomly trigger events
            event_type = random.choice(["sensor", "network", "custom"])
            
            if event_type == "sensor":
                scheduler.trigger_event("sensor_trigger")
            elif event_type == "network":
                music = random.choice(["morning.mp3", "afternoon.mp3", "evening.mp3"])
                scheduler.trigger_event("network_request", music)
            else:
                scheduler.trigger_event("custom_event")
            
            event_count += 1
        
        print("\nEvent simulation complete!")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    finally:
        print("Cleaning up...")
        scheduler.stop()
        player.cleanup()
        print("Goodbye!")


if __name__ == '__main__':
    main()
