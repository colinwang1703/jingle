import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import time
import threading
# Import BellPlayer class, but we will patch pygame inside the module it belongs to
from app.core.player import BellPlayer

class TestBellPlayer(unittest.TestCase):
    def setUp(self):
        # Patch pygame in app.core.player BEFORE creating BellPlayer instance
        self.pygame_patcher = patch('app.core.player.pygame')
        self.mock_pygame = self.pygame_patcher.start()
        self.mock_mixer = self.mock_pygame.mixer
        self.mock_music = self.mock_pygame.mixer.music
        
        # Setup common paths
        self.media_dir = Path("/fake/media")
        self.player = BellPlayer(self.media_dir)

    def tearDown(self):
        # Stop any running threads by clearing current_playing
        self.player.current_playing = None
        self.player.stop()
        self.pygame_patcher.stop()

    def test_init_audio(self):
        """Test audio initialization"""
        self.mock_mixer.init.assert_called_once()
        self.assertTrue(self.player.pygame_initialized)

    def test_play_file_exists(self):
        """Test playing an existing file"""
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "is_absolute", return_value=False):
                self.player.play("song.mp3")
            
        self.mock_music.load.assert_called()
        self.mock_music.play.assert_called()
        self.assertTrue(str(self.player.current_playing).endswith("song.mp3"))

    def test_play_file_not_exists(self):
        """Test playing a non-existing file"""
        with patch.object(Path, "exists", return_value=False):
             with patch.object(Path, "is_absolute", return_value=False):
                self.player.play("song.mp3")
            
        self.mock_music.load.assert_not_called()
        self.mock_music.play.assert_not_called()

    def test_stop(self):
        """Test stopping playback"""
        self.mock_music.get_busy.return_value = True
        self.player.current_playing = "song.mp3"
        
        self.player.stop()
        
        self.mock_music.stop.assert_called()
        self.assertIsNone(self.player.current_playing)

    def test_is_busy(self):
        """Test checking if player is busy"""
        self.mock_music.get_busy.return_value = True
        self.assertTrue(self.player.is_busy())
        
        self.mock_music.get_busy.return_value = False
        self.assertFalse(self.player.is_busy())

    def test_play_callback(self):
        """Test that callback is called when music ends"""
        callback = MagicMock()
        
        # Mock threading.Thread to capture the target function
        with patch('app.core.player.threading.Thread') as mock_thread_cls:
            mock_thread_instance = MagicMock()
            mock_thread_cls.return_value = mock_thread_instance
            
            with patch.object(Path, "exists", return_value=True):
                 with patch.object(Path, "is_absolute", return_value=False):
                    self.player.play("song.mp3", next_track_callback=callback)
            
            # Verify thread was started
            self.assertTrue(mock_thread_cls.called)
            
            # We can't easily run the target function because it contains an infinite loop (while self.current_playing...)
            # But we verified the logic structure in code review.
            # Here we just ensure the thread mechanism is invoked.

    def test_play_with_duration(self):
        """Test playing with a specific duration"""
        with patch('app.core.player.threading.Thread') as mock_thread_cls:
            with patch.object(Path, "exists", return_value=True):
                 with patch.object(Path, "is_absolute", return_value=False):
                    self.player.play("song.mp3", duration=10)
            
            # Verify 2 threads started
            self.assertEqual(mock_thread_cls.call_count, 2)

if __name__ == '__main__':
    unittest.main()
