"""
Tests for MusicScheduler.
"""

import time
import pytest
import schedule

from jingle.scheduler import MusicScheduler
from jingle.player import AudioPlayer


class TestMusicScheduler:
    """Test cases for MusicScheduler."""
    
    def setup_method(self):
        """Clear schedules before each test."""
        schedule.clear()
    
    def teardown_method(self):
        """Clear schedules after each test."""
        schedule.clear()
    
    def test_init(self):
        """Test scheduler initialization."""
        player = AudioPlayer()
        scheduler = MusicScheduler(player)
        assert scheduler.player == player
        assert scheduler.is_running() == False
    
    def test_add_schedule_time(self):
        """Test adding time-based schedule."""
        scheduler = MusicScheduler()
        scheduler.add_schedule("10:30", "test.mp3")
        schedules = scheduler.get_schedules()
        assert len(schedules) == 1  # Verify schedule was added
    
    def test_add_schedule_interval(self):
        """Test adding interval-based schedule."""
        scheduler = MusicScheduler()
        scheduler.add_schedule("every 1 hour", "test.mp3")
        schedules = scheduler.get_schedules()
        assert len(schedules) == 1  # Verify schedule was added
    
    def test_add_event_handler(self):
        """Test adding event handler."""
        scheduler = MusicScheduler()
        
        called = []
        def handler():
            called.append(True)
        
        scheduler.add_event_handler("test_event", handler)
        scheduler.trigger_event("test_event")
        
        assert len(called) == 1
    
    def test_trigger_multiple_handlers(self):
        """Test triggering multiple handlers for same event."""
        scheduler = MusicScheduler()
        
        call_count = []
        def handler1():
            call_count.append(1)
        
        def handler2():
            call_count.append(2)
        
        scheduler.add_event_handler("test", handler1)
        scheduler.add_event_handler("test", handler2)
        scheduler.trigger_event("test")
        
        assert len(call_count) == 2
        assert 1 in call_count
        assert 2 in call_count
    
    def test_start_stop(self):
        """Test starting and stopping scheduler."""
        scheduler = MusicScheduler()
        scheduler.start()
        assert scheduler.is_running() == True
        
        scheduler.stop()
        time.sleep(0.5)  # Give thread time to stop
        assert scheduler.is_running() == False
    
    def test_clear_schedules(self):
        """Test clearing all schedules."""
        scheduler = MusicScheduler()
        scheduler.add_schedule("10:00", "test.mp3")
        scheduler.add_schedule("11:00", "test2.mp3")
        
        scheduler.clear_schedules()
        schedules = scheduler.get_schedules()
        assert len(schedules) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
