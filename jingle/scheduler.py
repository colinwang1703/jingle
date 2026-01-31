"""
Task scheduler for Jingle.
Manages timed music playback with support for cron-like scheduling.
"""

import logging
import schedule
import threading
import time
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class MusicScheduler:
    """
    Lightweight scheduler for timed music playback.
    Uses the schedule library for efficient task scheduling.
    """
    
    def __init__(self, player=None):
        """
        Initialize MusicScheduler.
        
        Args:
            player: AudioPlayer instance
        """
        self.player = player
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._jobs: List[schedule.Job] = []
        self._event_handlers: Dict[str, List[Callable]] = {}
        
    def add_schedule(self, time_spec: str, music_file: str, **kwargs):
        """
        Add a scheduled playback task.
        
        Args:
            time_spec: Time specification (e.g., "10:30", "every 2 hours")
            music_file: Music file to play
            **kwargs: Additional arguments passed to player.play()
        """
        try:
            # Parse time specification
            parts = time_spec.strip().lower().split()
            
            if len(parts) == 1 and ':' in parts[0]:
                # Simple time format: "HH:MM"
                job = schedule.every().day.at(parts[0]).do(
                    self._play_task, music_file, **kwargs
                )
            elif parts[0] == "every":
                # Interval format: "every X hours/minutes/seconds"
                if len(parts) < 3:
                    logger.error(f"Invalid time specification: {time_spec}")
                    return
                
                interval = int(parts[1])
                unit = parts[2].rstrip('s')  # Remove plural 's'
                
                if unit == "hour":
                    job = schedule.every(interval).hours.do(
                        self._play_task, music_file, **kwargs
                    )
                elif unit == "minute":
                    job = schedule.every(interval).minutes.do(
                        self._play_task, music_file, **kwargs
                    )
                elif unit == "second":
                    job = schedule.every(interval).seconds.do(
                        self._play_task, music_file, **kwargs
                    )
                else:
                    logger.error(f"Unsupported time unit: {unit}")
                    return
            else:
                logger.error(f"Unsupported time specification: {time_spec}")
                return
            
            self._jobs.append(job)
            logger.info(f"Scheduled: {music_file} at {time_spec}")
            
        except Exception as e:
            logger.error(f"Error adding schedule: {e}")
    
    def _play_task(self, music_file: str, **kwargs):
        """Internal task to play music."""
        if self.player:
            logger.info(f"Scheduled playback: {music_file}")
            self.player.play(music_file, **kwargs)
        else:
            logger.warning("No player instance available")
    
    def add_event_handler(self, event_name: str, handler: Callable):
        """
        Add an event handler for custom triggers.
        
        Args:
            event_name: Name of the event
            handler: Callable to handle the event
        """
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        
        self._event_handlers[event_name].append(handler)
        logger.info(f"Added event handler for: {event_name}")
    
    def trigger_event(self, event_name: str, *args, **kwargs):
        """
        Trigger a custom event.
        
        Args:
            event_name: Name of the event to trigger
            *args, **kwargs: Arguments passed to event handlers
        """
        if event_name in self._event_handlers:
            logger.info(f"Triggering event: {event_name}")
            for handler in self._event_handlers[event_name]:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
        else:
            logger.warning(f"No handlers for event: {event_name}")
    
    def start(self, check_interval: float = 1.0):
        """
        Start the scheduler in a background thread.
        
        Args:
            check_interval: Interval in seconds to check for pending tasks
        """
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._run_scheduler,
            args=(check_interval,),
            daemon=True
        )
        self._thread.start()
        logger.info("Scheduler started")
    
    def _run_scheduler(self, check_interval: float):
        """Internal method to run the scheduler loop."""
        while self._running:
            try:
                schedule.run_pending()
                time.sleep(check_interval)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
    
    def stop(self):
        """Stop the scheduler."""
        if not self._running:
            return
        
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        
        logger.info("Scheduler stopped")
    
    def clear_schedules(self):
        """Clear all scheduled tasks."""
        schedule.clear()
        self._jobs.clear()
        logger.info("All schedules cleared")
    
    def get_schedules(self) -> List[Dict[str, Any]]:
        """
        Get list of all scheduled tasks.
        
        Returns:
            List of schedule information dictionaries
        """
        schedules = []
        for job in schedule.get_jobs():
            schedules.append({
                'next_run': str(job.next_run),
                'interval': str(job.interval) if job.interval else None,
                'unit': job.unit,
                'at_time': str(job.at_time) if job.at_time else None
            })
        return schedules
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running
