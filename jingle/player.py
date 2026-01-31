"""
Audio playback engine for Jingle.
Uses pygame.mixer for lightweight, efficient audio playback.
"""

import os
import logging
import threading
from pathlib import Path
from typing import Optional, List
import pygame

logger = logging.getLogger(__name__)


class AudioPlayer:
    """
    Lightweight audio player using pygame.mixer.
    Optimized for resource-constrained devices.
    """
    
    def __init__(self, music_dir: Optional[str] = None, volume: float = 0.7):
        """
        Initialize AudioPlayer.
        
        Args:
            music_dir: Directory containing music files
            volume: Initial volume (0.0 to 1.0)
        """
        self.music_dir = music_dir or os.getcwd()
        self._volume = max(0.0, min(1.0, volume))
        self._is_playing = False
        self._lock = threading.RLock()
        self._initialized = False
        
        # Initialize pygame mixer with low buffer for minimal latency
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self._initialized = True
            pygame.mixer.music.set_volume(self._volume)
            logger.info("Audio player initialized")
        except Exception as e:
            logger.error(f"Failed to initialize audio player: {e}")
    
    def play(self, filename: str, loops: int = 0, fade_in: float = 0.0) -> bool:
        """
        Play a music file.
        
        Args:
            filename: Name of the music file (relative to music_dir)
            loops: Number of times to loop (-1 for infinite, 0 for once)
            fade_in: Fade-in duration in seconds
            
        Returns:
            True if playback started successfully, False otherwise
        """
        if not self._initialized:
            logger.error("Audio player not initialized")
            return False
        
        with self._lock:
            try:
                # Resolve file path
                if os.path.isabs(filename):
                    filepath = Path(filename)
                else:
                    filepath = Path(self.music_dir) / filename
                
                if not filepath.exists():
                    logger.error(f"Music file not found: {filepath}")
                    return False
                
                # Stop current playback if any
                if self._is_playing:
                    self.stop()
                
                # Load and play music
                pygame.mixer.music.load(str(filepath))
                
                if fade_in > 0:
                    pygame.mixer.music.play(loops=loops, fade_ms=int(fade_in * 1000))
                else:
                    pygame.mixer.music.play(loops=loops)
                
                self._is_playing = True
                logger.info(f"Playing: {filepath.name}")
                return True
                
            except Exception as e:
                logger.error(f"Error playing music: {e}")
                return False
    
    def stop(self, fade_out: float = 0.0):
        """
        Stop current playback.
        
        Args:
            fade_out: Fade-out duration in seconds
        """
        if not self._initialized:
            return
        
        with self._lock:
            try:
                if fade_out > 0:
                    pygame.mixer.music.fadeout(int(fade_out * 1000))
                else:
                    pygame.mixer.music.stop()
                
                self._is_playing = False
                logger.info("Playback stopped")
            except Exception as e:
                logger.error(f"Error stopping playback: {e}")
    
    def pause(self):
        """Pause current playback."""
        if not self._initialized:
            return
        
        with self._lock:
            try:
                pygame.mixer.music.pause()
                logger.info("Playback paused")
            except Exception as e:
                logger.error(f"Error pausing playback: {e}")
    
    def unpause(self):
        """Resume paused playback."""
        if not self._initialized:
            return
        
        with self._lock:
            try:
                pygame.mixer.music.unpause()
                logger.info("Playback resumed")
            except Exception as e:
                logger.error(f"Error resuming playback: {e}")
    
    def set_volume(self, volume: float):
        """
        Set playback volume.
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        with self._lock:
            self._volume = max(0.0, min(1.0, volume))
            
            if not self._initialized:
                return
            
            try:
                pygame.mixer.music.set_volume(self._volume)
                logger.debug(f"Volume set to {self._volume}")
            except Exception as e:
                logger.error(f"Error setting volume: {e}")
    
    def get_volume(self) -> float:
        """Get current volume level."""
        return self._volume
    
    def is_playing(self) -> bool:
        """Check if music is currently playing."""
        if not self._initialized:
            return False
        
        with self._lock:
            try:
                return pygame.mixer.music.get_busy()
            except Exception as e:
                logger.error(f"Error checking playback status: {e}")
                return False
    
    def get_music_files(self, extensions: Optional[List[str]] = None) -> List[str]:
        """
        Get list of music files in music directory.
        
        Args:
            extensions: List of file extensions to filter (e.g., ['.mp3', '.wav'])
                       If None, uses common audio formats
        
        Returns:
            List of music file paths relative to music_dir
        """
        if extensions is None:
            extensions = ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac']
        
        music_files = []
        music_path = Path(self.music_dir)
        
        if not music_path.exists():
            logger.warning(f"Music directory not found: {music_path}")
            return music_files
        
        try:
            for ext in extensions:
                music_files.extend([
                    str(f.relative_to(music_path))
                    for f in music_path.rglob(f'*{ext}')
                ])
            
            music_files.sort()
            logger.info(f"Found {len(music_files)} music files")
        except Exception as e:
            logger.error(f"Error scanning music directory: {e}")
        
        return music_files
    
    def cleanup(self):
        """Clean up resources."""
        with self._lock:
            if self._initialized:
                try:
                    pygame.mixer.music.stop()
                    pygame.mixer.quit()
                    self._initialized = False
                    logger.info("Audio player cleaned up")
                except Exception as e:
                    logger.error(f"Error during cleanup: {e}")
