"""
Tests for MusicScheduler with Configuration v1.0.
"""

import pytest
import schedule
from jingle.scheduler import MusicScheduler
from jingle.player import AudioPlayer


class TestMusicSchedulerV1:
    """Test cases for MusicScheduler with Configuration v1.0."""
    
    def setup_method(self):
        """Setup for each test."""
        schedule.clear()
        self.player = AudioPlayer(music_dir='/tmp', volume=0.7)
    
    def teardown_method(self):
        """Cleanup after each test."""
        schedule.clear()
        if self.player:
            self.player.cleanup()
    
    def test_expand_days_weekday(self):
        """Test expanding 'weekday' shortcut."""
        config = {}
        scheduler = MusicScheduler(player=self.player, config=config)
        
        expanded = scheduler._expand_days('weekday')
        assert len(expanded) == 5
        assert 'monday' in expanded
        assert 'friday' in expanded
        assert 'saturday' not in expanded
    
    def test_expand_days_weekend(self):
        """Test expanding 'weekend' shortcut."""
        config = {}
        scheduler = MusicScheduler(player=self.player, config=config)
        
        expanded = scheduler._expand_days('weekend')
        assert len(expanded) == 2
        assert 'saturday' in expanded
        assert 'sunday' in expanded
    
    def test_expand_days_all(self):
        """Test expanding 'all' shortcut."""
        config = {}
        scheduler = MusicScheduler(player=self.player, config=config)
        
        expanded = scheduler._expand_days('all')
        assert len(expanded) == 7
    
    def test_expand_days_range(self):
        """Test expanding day range."""
        config = {}
        scheduler = MusicScheduler(player=self.player, config=config)
        
        expanded = scheduler._expand_days('monday-friday')
        assert len(expanded) == 5
        assert expanded[0] == 'monday'
        assert expanded[-1] == 'friday'
    
    def test_expand_days_list(self):
        """Test expanding list of days."""
        config = {}
        scheduler = MusicScheduler(player=self.player, config=config)
        
        expanded = scheduler._expand_days(['monday', 'wednesday', 'friday'])
        assert len(expanded) == 3
        assert 'monday' in expanded
        assert 'wednesday' in expanded
        assert 'friday' in expanded
    
    def test_generate_time_points(self):
        """Test generating time points from range."""
        config = {}
        scheduler = MusicScheduler(player=self.player, config=config)
        
        time_points = scheduler._generate_time_points('09:00', '12:00', 60)
        assert len(time_points) == 4  # 09:00, 10:00, 11:00, 12:00
        assert '09:00' in time_points
        assert '12:00' in time_points
    
    def test_generate_time_points_30min(self):
        """Test generating time points with 30-minute interval."""
        config = {}
        scheduler = MusicScheduler(player=self.player, config=config)
        
        time_points = scheduler._generate_time_points('08:00', '09:00', 30)
        assert len(time_points) == 3  # 08:00, 08:30, 09:00
        assert '08:30' in time_points
    
    def test_resolve_playlist_direct_files(self):
        """Test resolving playlist with direct file references."""
        config = {}
        scheduler = MusicScheduler(player=self.player, config=config)
        
        playlist_spec = ['song1.mp3', 'song2.mp3', 'song3.mp3']
        resolved = scheduler._resolve_playlist(playlist_spec)
        assert len(resolved) == 3
        assert 'song1.mp3' in resolved
    
    def test_resolve_playlist_with_references(self):
        """Test resolving playlist with global playlist references."""
        config = {
            'playlists': {
                'morning_bells': ['bell1.mp3', 'bell2.mp3'],
                'evening_bells': ['bell3.mp3']
            }
        }
        scheduler = MusicScheduler(player=self.player, config=config)
        
        playlist_spec = ['morning_bells']
        resolved = scheduler._resolve_playlist(playlist_spec)
        assert len(resolved) == 2
        assert 'bell1.mp3' in resolved
        assert 'bell2.mp3' in resolved
    
    def test_resolve_playlist_mixed(self):
        """Test resolving playlist with mixed references and direct files."""
        config = {
            'playlists': {
                'bells': ['bell1.mp3', 'bell2.mp3']
            }
        }
        scheduler = MusicScheduler(player=self.player, config=config)
        
        playlist_spec = ['bells', 'direct.mp3']
        resolved = scheduler._resolve_playlist(playlist_spec)
        assert len(resolved) == 3
        assert 'bell1.mp3' in resolved
        assert 'direct.mp3' in resolved
    
    def test_select_tracks_single(self):
        """Test selecting single track from playlist."""
        config = {}
        scheduler = MusicScheduler(player=self.player, config=config)
        
        playlist = ['song1.mp3', 'song2.mp3', 'song3.mp3']
        selected = scheduler._select_tracks(playlist, 1)
        assert len(selected) == 1
        assert selected[0] in playlist
    
    def test_select_tracks_multiple(self):
        """Test selecting multiple tracks from playlist."""
        config = {}
        scheduler = MusicScheduler(player=self.player, config=config)
        
        playlist = ['song1.mp3', 'song2.mp3', 'song3.mp3', 'song4.mp3', 'song5.mp3']
        selected = scheduler._select_tracks(playlist, 3)
        assert len(selected) == 3
        # All selected should be in original playlist
        for track in selected:
            assert track in playlist
        # No duplicates
        assert len(selected) == len(set(selected))
    
    def test_select_tracks_all(self):
        """Test selecting all tracks from playlist."""
        config = {}
        scheduler = MusicScheduler(player=self.player, config=config)
        
        playlist = ['song1.mp3', 'song2.mp3', 'song3.mp3']
        selected = scheduler._select_tracks(playlist, 5)
        # Should return all tracks when count > playlist size
        assert len(selected) == 3
        for track in playlist:
            assert track in selected
    
    def test_add_simple_time_points(self):
        """Test adding schedule with Format 1 (simple time points)."""
        config = {}
        scheduler = MusicScheduler(player=self.player, config=config)
        
        schedule_config = {
            'days': ['monday', 'wednesday'],
            'times': ['08:00', '12:00'],
            'mode': {
                'type': 'random',
                'playlist': ['test.mp3'],
                'play_count': 1
            }
        }
        
        scheduler.add_schedule_v1('test_schedule', schedule_config)
        
        # Should create 4 jobs (2 days × 2 times)
        jobs = schedule.get_jobs()
        assert len(jobs) == 4
    
    def test_add_time_range(self):
        """Test adding schedule with Format 2 (time range)."""
        config = {}
        scheduler = MusicScheduler(player=self.player, config=config)
        
        schedule_config = {
            'days': ['weekday'],
            'time_range': {
                'start': '09:00',
                'end': '11:00',
                'interval': 60
            },
            'mode': {
                'type': 'random',
                'playlist': ['test.mp3'],
                'play_count': 1
            }
        }
        
        scheduler.add_schedule_v1('test_schedule', schedule_config)
        
        # Should create 15 jobs (5 weekdays × 3 time points)
        jobs = schedule.get_jobs()
        assert len(jobs) == 15
    
    def test_add_complex_time_groups(self):
        """Test adding schedule with Format 3 (complex time groups)."""
        config = {}
        scheduler = MusicScheduler(player=self.player, config=config)
        
        schedule_config = {
            'times': [
                {
                    'days': ['monday', 'wednesday'],
                    'points': ['08:00', '12:00']
                },
                {
                    'days': ['friday'],
                    'points': ['09:00']
                }
            ],
            'mode': {
                'type': 'random',
                'playlist': ['test.mp3'],
                'play_count': 1
            }
        }
        
        scheduler.add_schedule_v1('test_schedule', schedule_config)
        
        # Should create 5 jobs (2 days × 2 times + 1 day × 1 time)
        jobs = schedule.get_jobs()
        assert len(jobs) == 5
    
    def test_add_compact_schedules(self):
        """Test adding schedule with Format 4 (compact strings)."""
        config = {}
        scheduler = MusicScheduler(player=self.player, config=config)
        
        schedule_config = {
            'schedule': [
                'monday,wednesday 08:00',
                'friday 09:00'
            ],
            'mode': {
                'type': 'random',
                'playlist': ['test.mp3'],
                'play_count': 1
            }
        }
        
        scheduler.add_schedule_v1('test_schedule', schedule_config)
        
        # Should create 3 jobs (2 days for first string + 1 day for second)
        jobs = schedule.get_jobs()
        assert len(jobs) == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
