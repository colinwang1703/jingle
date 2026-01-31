"""
Jingle - A lightweight timed music playback system for resource-constrained devices.
"""

__version__ = "0.1.0"
__author__ = "Colin Wang"

from .player import AudioPlayer
from .scheduler import MusicScheduler
from .config import ConfigManager

__all__ = ['AudioPlayer', 'MusicScheduler', 'ConfigManager']
