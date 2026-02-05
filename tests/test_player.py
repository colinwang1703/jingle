"""
Tests for AudioPlayer.
"""

import os
import tempfile
from pathlib import Path
import pytest
import pygame

from jingle.player import AudioPlayer


class TestAudioPlayer:
    """Test cases for AudioPlayer."""
    
    def test_init(self):
        """Test player initialization."""
        player = AudioPlayer(music_dir="/tmp", volume=0.5)
        assert player.music_dir == "/tmp"
        assert player.get_volume() == 0.5
    
    def test_audio_initialization_parameters(self):
        """Test that pygame mixer is initialized with correct parameters.
        
        Uses standard 44.1kHz sampling rate and 4096 buffer size for:
        - Better audio quality (CD standard)
        - Improved stability on embedded/resource-constrained devices
        - Reduced buffer underruns
        """
        # Save original SDL_AUDIODRIVER if it exists
        original_driver = os.environ.get('SDL_AUDIODRIVER')
        
        # Use dummy audio driver for testing environments without audio devices
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
        
        try:
            # Initialize player which initializes pygame mixer
            player = AudioPlayer()
            
            # Verify initialization succeeded
            assert player._initialized
            
            # Get mixer settings (requires pygame mixer to be initialized)
            mixer_freq = pygame.mixer.get_init()[0]
            
            # Verify frequency is 44100 Hz (CD quality standard)
            assert mixer_freq == 44100, f"Expected frequency 44100 Hz, got {mixer_freq} Hz"
        finally:
            # Restore original value or remove if it didn't exist
            if original_driver is not None:
                os.environ['SDL_AUDIODRIVER'] = original_driver
            elif 'SDL_AUDIODRIVER' in os.environ:
                del os.environ['SDL_AUDIODRIVER']
    
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
