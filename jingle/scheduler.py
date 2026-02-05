"""
Task scheduler for Jingle.
Manages timed music playback with support for cron-like scheduling.
Configuration v1.0 compliant with support for multiple time formats.
"""

import logging
import schedule
import threading
import time
import random
from typing import Callable, Dict, Any, Optional, List, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MusicScheduler:
    """
    Lightweight scheduler for timed music playback.
    Uses the schedule library for efficient task scheduling.
    Supports Configuration v1.0 with multiple time specification formats.
    """
    
    def __init__(self, player=None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize MusicScheduler.
        
        Args:
            player: AudioPlayer instance
            config: Optional configuration dictionary for v1.0 format
        """
        self.player = player
        self.config = config or {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._jobs: List[schedule.Job] = []
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._playlists: Dict[str, List[str]] = {}
        
        # Load playlists from config if available
        if 'playlists' in self.config:
            self._playlists = self.config['playlists']
        
    def add_schedule_v1(self, schedule_name: str, schedule_config: Dict[str, Any]):
        """
        Add a schedule using Configuration v1.0 format.
        
        Args:
            schedule_name: Name of the schedule
            schedule_config: Schedule configuration dictionary
        """
        try:
            # Determine which time format is being used
            if 'times' in schedule_config:
                times_value = schedule_config['times']
                if isinstance(times_value, list) and len(times_value) > 0:
                    if isinstance(times_value[0], dict):
                        # Format 3: Complex time groups
                        self._add_complex_time_groups(schedule_name, schedule_config)
                    else:
                        # Format 1: Simple time points
                        self._add_simple_time_points(schedule_name, schedule_config)
            elif 'time_range' in schedule_config:
                # Format 2: Time range with interval
                self._add_time_range(schedule_name, schedule_config)
            elif 'schedule' in schedule_config:
                # Format 4: Compact schedule strings
                self._add_compact_schedules(schedule_name, schedule_config)
            else:
                logger.error(f"Schedule '{schedule_name}': no recognized time format")
        
        except Exception as e:
            logger.error(f"Error adding schedule '{schedule_name}': {e}")
    
    def _add_simple_time_points(self, schedule_name: str, schedule_config: Dict[str, Any]):
        """
        Add schedules using Format 1: Simple time points.
        
        Args:
            schedule_name: Name of the schedule
            schedule_config: Schedule configuration
        """
        days = schedule_config['days']
        times = schedule_config['times']
        mode = schedule_config['mode']
        
        # Expand days
        expanded_days = self._expand_days(days)
        
        # Add a schedule for each time on each day
        for day in expanded_days:
            for time_point in times:
                self._schedule_playback(day, time_point, mode, schedule_name)
    
    def _add_time_range(self, schedule_name: str, schedule_config: Dict[str, Any]):
        """
        Add schedules using Format 2: Time range with interval.
        
        Args:
            schedule_name: Name of the schedule
            schedule_config: Schedule configuration
        """
        days = schedule_config['days']
        time_range = schedule_config['time_range']
        mode = schedule_config['mode']
        
        start = time_range['start']
        end = time_range['end']
        interval = time_range['interval']  # in minutes
        
        # Generate time points within the range
        time_points = self._generate_time_points(start, end, interval)
        
        # Expand days
        expanded_days = self._expand_days(days)
        
        # Add a schedule for each time on each day
        for day in expanded_days:
            for time_point in time_points:
                self._schedule_playback(day, time_point, mode, schedule_name)
    
    def _add_complex_time_groups(self, schedule_name: str, schedule_config: Dict[str, Any]):
        """
        Add schedules using Format 3: Complex time groups.
        
        Args:
            schedule_name: Name of the schedule
            schedule_config: Schedule configuration
        """
        times_groups = schedule_config['times']
        mode = schedule_config['mode']
        
        for time_group in times_groups:
            days = time_group['days']
            points = time_group['points']
            
            expanded_days = self._expand_days(days)
            
            for day in expanded_days:
                for time_point in points:
                    self._schedule_playback(day, time_point, mode, schedule_name)
    
    def _add_compact_schedules(self, schedule_name: str, schedule_config: Dict[str, Any]):
        """
        Add schedules using Format 4: Compact schedule strings.
        
        Args:
            schedule_name: Name of the schedule
            schedule_config: Schedule configuration
        """
        schedule_strings = schedule_config['schedule']
        mode = schedule_config['mode']
        
        for schedule_str in schedule_strings:
            # Parse format: "monday,wednesday 08:00" or "weekday 08:00"
            parts = schedule_str.strip().split()
            if len(parts) != 2:
                logger.error(f"Invalid schedule string: '{schedule_str}'")
                continue
            
            days_str, time_point = parts
            
            # Handle comma-separated days
            if ',' in days_str:
                days = [d.strip() for d in days_str.split(',')]
            else:
                days = [days_str]
            
            expanded_days = self._expand_days(days)
            
            for day in expanded_days:
                self._schedule_playback(day, time_point, mode, schedule_name)
    
    def _expand_days(self, days: Union[str, List[str]]) -> List[str]:
        """
        Expand day specifications into individual day names.
        
        Args:
            days: Day specification (string or list)
            
        Returns:
            List of day names (monday, tuesday, etc.)
        """
        if isinstance(days, str):
            days = [days]
        
        expanded = []
        
        for day_spec in days:
            day_spec = day_spec.lower().strip()
            
            if day_spec == 'weekday':
                expanded.extend(['monday', 'tuesday', 'wednesday', 'thursday', 'friday'])
            elif day_spec == 'weekend':
                expanded.extend(['saturday', 'sunday'])
            elif day_spec == 'all':
                expanded.extend(['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'])
            elif '-' in day_spec:
                # Handle day ranges
                expanded.extend(self._expand_day_range(day_spec))
            else:
                # Single day or comma-separated (already split)
                expanded.append(day_spec)
        
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for day in expanded:
            if day not in seen:
                seen.add(day)
                result.append(day)
        
        return result
    
    def _expand_day_range(self, day_range: str) -> List[str]:
        """
        Expand a day range like 'monday-friday' into individual days.
        
        Args:
            day_range: Day range string
            
        Returns:
            List of day names
        """
        days_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        parts = day_range.split('-')
        if len(parts) != 2:
            return []
        
        start_day = parts[0].strip()
        end_day = parts[1].strip()
        
        try:
            start_idx = days_order.index(start_day)
            end_idx = days_order.index(end_day)
            
            if start_idx <= end_idx:
                return days_order[start_idx:end_idx + 1]
            else:
                # Wrap around (e.g., friday-monday)
                return days_order[start_idx:] + days_order[:end_idx + 1]
        except ValueError:
            logger.error(f"Invalid day range: {day_range}")
            return []
    
    def _generate_time_points(self, start: str, end: str, interval_minutes: int) -> List[str]:
        """
        Generate time points within a range at specified intervals.
        
        Args:
            start: Start time (HH:MM)
            end: End time (HH:MM)
            interval_minutes: Interval in minutes
            
        Returns:
            List of time strings (HH:MM)
        """
        # Parse start and end times
        start_time = datetime.strptime(start, "%H:%M")
        end_time = datetime.strptime(end, "%H:%M")
        
        time_points = []
        current_time = start_time
        
        while current_time <= end_time:
            time_points.append(current_time.strftime("%H:%M"))
            current_time += timedelta(minutes=interval_minutes)
        
        return time_points
    
    def _schedule_playback(self, day: str, time_point: str, mode: Dict[str, Any], schedule_name: str):
        """
        Schedule a playback task for a specific day and time.
        
        Args:
            day: Day name (monday, tuesday, etc.)
            time_point: Time in HH:MM format
            mode: Mode configuration with playlist and options
            schedule_name: Name of the schedule
        """
        # Get schedule method for the day
        day_map = {
            'monday': schedule.every().monday,
            'tuesday': schedule.every().tuesday,
            'wednesday': schedule.every().wednesday,
            'thursday': schedule.every().thursday,
            'friday': schedule.every().friday,
            'saturday': schedule.every().saturday,
            'sunday': schedule.every().sunday,
        }
        
        if day not in day_map:
            logger.error(f"Invalid day: {day}")
            return
        
        try:
            job = day_map[day].at(time_point).do(
                self._play_task_v1, mode, schedule_name
            )
            self._jobs.append(job)
            logger.info(f"Scheduled '{schedule_name}' on {day} at {time_point}")
        except Exception as e:
            logger.error(f"Error scheduling playback: {e}")
    
    def _play_task_v1(self, mode: Dict[str, Any], schedule_name: str):
        """
        Execute playback task for Configuration v1.0.
        
        Args:
            mode: Mode configuration
            schedule_name: Name of the schedule
        """
        if not self.player:
            logger.warning("No player instance available")
            return
        
        try:
            # Get playlist
            playlist_spec = mode['playlist']
            play_count = mode.get('play_count', 1)
            
            # Resolve playlist
            resolved_playlist = self._resolve_playlist(playlist_spec)
            
            if not resolved_playlist:
                logger.error(f"Empty playlist for schedule '{schedule_name}'")
                return
            
            # Select tracks to play
            tracks_to_play = self._select_tracks(resolved_playlist, play_count)
            
            # Get playback options
            volume = mode.get('volume')
            fade_in = mode.get('fade_in', 0.0)
            fade_out = mode.get('fade_out', 0.0)
            
            # Play tracks
            logger.info(f"Playing {len(tracks_to_play)} track(s) from schedule '{schedule_name}'")
            
            for i, track in enumerate(tracks_to_play):
                # Set volume if specified
                if volume is not None and i == 0:
                    self.player.set_volume(volume)
                
                # Play the track
                kwargs = {}
                if fade_in > 0 and i == 0:
                    kwargs['fade_in'] = fade_in
                
                self.player.play(track, **kwargs)
                
                # Wait for playback to complete (except for last track with fade out)
                if i < len(tracks_to_play) - 1 or fade_out == 0:
                    while self.player.is_playing():
                        time.sleep(0.1)
                else:
                    # For last track with fade out, wait then fade
                    while self.player.is_playing():
                        time.sleep(0.1)
                    
                    if fade_out > 0:
                        self.player.stop(fade_out=fade_out)
        
        except Exception as e:
            logger.error(f"Error in playback task: {e}")
    
    def _resolve_playlist(self, playlist_spec: List[str]) -> List[str]:
        """
        Resolve playlist specification to actual file list.
        
        Args:
            playlist_spec: Playlist specification (list of files or playlist names)
            
        Returns:
            List of music files
        """
        resolved = []
        
        for item in playlist_spec:
            # Check if it's a reference to a global playlist
            if item in self._playlists:
                resolved.extend(self._playlists[item])
            else:
                # It's a direct file reference
                resolved.append(item)
        
        return resolved
    
    def _select_tracks(self, playlist: List[str], count: int) -> List[str]:
        """
        Select tracks from playlist based on play count.
        
        Args:
            playlist: List of available tracks
            count: Number of tracks to select
            
        Returns:
            List of selected tracks
        """
        if count >= len(playlist):
            # Return all tracks in random order
            tracks = playlist.copy()
            random.shuffle(tracks)
            return tracks
        else:
            # Select random tracks without replacement
            return random.sample(playlist, count)
    
    def add_schedule(self, time_spec: str, music_file: str, **kwargs):
        """
        Add a scheduled playback task (legacy format).
        
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
                
                try:
                    interval = int(parts[1])
                except ValueError:
                    logger.error(f"Invalid interval value: '{parts[1]}' in time specification: {time_spec}")
                    return
                
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
