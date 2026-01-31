"""
Tests for AudioPlayer.
"""

import os
import tempfile
from pathlib import Path
import pytest

from jingle.player import AudioPlayer


class TestAudioPlayer:
    """Test cases for AudioPlayer."""
    
    def test_init(self):
        """Test player initialization."""
        player = AudioPlayer(music_dir="/tmp", volume=0.5)
        assert player.music_dir == "/tmp"
        assert player.get_volume() == 0.5
    
    def test_volume_bounds(self):
        """Test volume is bounded between 0.0 and 1.0."""
        player = AudioPlayer(volume=1.5)
        assert player.get_volume() == 1.0
        
        player2 = AudioPlayer(volume=-0.5)
        assert player2.get_volume() == 0.0
    
    def test_set_volume(self):
        """Test setting volume."""
        player = AudioPlayer()
        player.set_volume(0.8)
        assert player.get_volume() == 0.8
        
        # Test bounds
        player.set_volume(2.0)
        assert player.get_volume() == 1.0
        
        player.set_volume(-1.0)
        assert player.get_volume() == 0.0
    
    def test_get_music_files(self):
        """Test getting music files from directory."""
        # Create temporary directory with test files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test music files
            Path(tmpdir, "test1.mp3").touch()
            Path(tmpdir, "test2.wav").touch()
            Path(tmpdir, "test3.ogg").touch()
            Path(tmpdir, "not_music.txt").touch()
            
            player = AudioPlayer(music_dir=tmpdir)
            files = player.get_music_files()
            
            assert len(files) == 3
            assert "test1.mp3" in files
            assert "test2.wav" in files
            assert "test3.ogg" in files
            assert "not_music.txt" not in files
    
    def test_play_nonexistent_file(self):
        """Test playing non-existent file returns False."""
        player = AudioPlayer()
        result = player.play("nonexistent_file.mp3")
        assert result == False
    
    def test_is_playing_initial_state(self):
        """Test initial playing state."""
        player = AudioPlayer()
        # Initially should not be playing
        assert player.is_playing() == False
    
    def test_cleanup(self):
        """Test cleanup doesn't raise exceptions."""
        player = AudioPlayer()
        player.cleanup()
        # Should not raise any exception


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
