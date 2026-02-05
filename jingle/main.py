"""
Main application for Jingle - Timed Music Playback System.
"""

import os
import sys
import signal
import logging
import argparse
import time
from pathlib import Path
from typing import Optional

from jingle.config import ConfigManager
from jingle.player import AudioPlayer
from jingle.scheduler import MusicScheduler


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class JingleApp:
    """Main application class for Jingle."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Jingle application.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_manager = ConfigManager(config_path)
        self.player: Optional[AudioPlayer] = None
        self.scheduler: Optional[MusicScheduler] = None
        self._running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Shutdown signal received")
        self.stop()
    
    def initialize(self):
        """Initialize application components."""
        try:
            config_all = self.config_manager.get_all()
            
            # Check if using v1.0 configuration format
            is_v1 = config_all.get('version') == "1.0"
            
            if is_v1:
                # Configuration v1.0 format
                config_section = config_all.get('config', {})
                music_dir = config_section.get('music_dir', os.getcwd())
                volume = config_section.get('default_volume', 0.8)
                
                self.player = AudioPlayer(music_dir=music_dir, volume=volume)
                
                # Initialize scheduler with full config for v1.0
                self.scheduler = MusicScheduler(player=self.player, config=config_all)
                
                # Load schedules from v1.0 format
                schedules = config_all.get('schedules', {})
                if isinstance(schedules, dict):
                    for schedule_name, schedule_config in schedules.items():
                        self.scheduler.add_schedule_v1(schedule_name, schedule_config)
                else:
                    logger.warning("Schedules should be a dictionary in v1.0 format")
            else:
                # Legacy format
                music_dir = self.config_manager.get('player.music_dir', os.getcwd())
                volume = self.config_manager.get('player.volume', 0.7)
                
                self.player = AudioPlayer(music_dir=music_dir, volume=volume)
                
                # Initialize scheduler
                self.scheduler = MusicScheduler(player=self.player)
                
                # Load schedules from legacy format
                schedules = self.config_manager.get('schedules', [])
                for sched in schedules:
                    time_spec = sched.get('time')
                    music_file = sched.get('music')
                    options = sched.get('options', {})
                    
                    if time_spec and music_file:
                        self.scheduler.add_schedule(time_spec, music_file, **options)
            
            logger.info("Application initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            return False
    
    def run(self, hot_reload: bool = True, reload_interval: float = 5.0):
        """
        Run the application.
        
        Args:
            hot_reload: Enable configuration hot-reload
            reload_interval: Interval in seconds to check for config changes
        """
        if not self.initialize():
            logger.error("Initialization failed, exiting")
            return
        
        self._running = True
        
        # Start scheduler
        if self.scheduler:
            self.scheduler.start()
        
        logger.info("Jingle is running. Press Ctrl+C to stop.")
        
        # Main loop with optional hot-reload
        try:
            while self._running:
                if hot_reload:
                    if self.config_manager.check_reload():
                        logger.info("Configuration reloaded, updating schedules...")
                        self._reload_schedules()
                
                time.sleep(reload_interval)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.stop()
    
    def _reload_schedules(self):
        """Reload schedules from updated configuration."""
        if not self.scheduler:
            return
        
        try:
            # Clear existing schedules
            self.scheduler.clear_schedules()
            
            config_all = self.config_manager.get_all()
            is_v1 = config_all.get('version') == "1.0"
            
            if is_v1:
                # Update player settings from v1.0 config
                config_section = config_all.get('config', {})
                volume = config_section.get('default_volume', 0.8)
                if self.player:
                    self.player.set_volume(volume)
                
                # Update playlists
                self.scheduler._playlists = config_all.get('playlists', {})
                
                # Reload schedules from v1.0 format
                schedules = config_all.get('schedules', {})
                if isinstance(schedules, dict):
                    for schedule_name, schedule_config in schedules.items():
                        self.scheduler.add_schedule_v1(schedule_name, schedule_config)
            else:
                # Legacy format
                volume = self.config_manager.get('player.volume', 0.7)
                if self.player:
                    self.player.set_volume(volume)
                
                # Reload schedules from legacy format
                schedules = self.config_manager.get('schedules', [])
                for sched in schedules:
                    time_spec = sched.get('time')
                    music_file = sched.get('music')
                    options = sched.get('options', {})
                    
                    if time_spec and music_file:
                        self.scheduler.add_schedule(time_spec, music_file, **options)
            
            logger.info("Schedules reloaded successfully")
            
        except Exception as e:
            logger.error(f"Error reloading schedules: {e}")
    
    def stop(self):
        """Stop the application."""
        logger.info("Stopping Jingle...")
        self._running = False
        
        if self.scheduler:
            self.scheduler.stop()
        
        if self.player:
            self.player.cleanup()
        
        logger.info("Jingle stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Jingle - Lightweight timed music playback system'
    )
    parser.add_argument(
        '-c', '--config',
        type=str,
        default=None,
        help='Path to configuration file (default: config/jingle.yaml if exists, else no config)'
    )
    parser.add_argument(
        '--no-hot-reload',
        action='store_true',
        help='Disable configuration hot-reload'
    )
    parser.add_argument(
        '--reload-interval',
        type=float,
        default=5.0,
        help='Hot-reload check interval in seconds (default: 5.0)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Determine config path
    config_path = args.config
    if config_path is None:
        # Try default path if it exists
        default_path = Path('config/jingle.yaml')
        if default_path.exists():
            config_path = str(default_path)
            logger.info(f"Using default config: {config_path}")
        else:
            logger.warning("No config file specified and default not found. Running with minimal config.")
    
    # Create and run application
    app = JingleApp(config_path=config_path)
    app.run(
        hot_reload=not args.no_hot_reload,
        reload_interval=args.reload_interval
    )


if __name__ == '__main__':
    main()
