"""
Configuration management module for Jingle.
Supports YAML, JSON, and environment variables with hot-reload capability.
Configuration v1.0 specification compliant.
"""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from threading import RLock

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Configuration validation error."""
    pass


class ConfigManager:
    """
    Manages configuration loading and hot-reload for the music player.
    Supports YAML, JSON files and environment variable overrides.
    Implements Configuration v1.0 specification.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize ConfigManager.
        
        Args:
            config_path: Path to configuration file (YAML or JSON)
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._lock = RLock()
        self._last_modified = 0
        
        if config_path:
            self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Configuration dictionary
        
        Raises:
            ConfigError: If configuration is invalid
        """
        with self._lock:
            if not self.config_path:
                logger.warning("No config path specified")
                return self.config
            
            config_file = Path(self.config_path)
            if not config_file.exists():
                logger.error(f"Config file not found: {self.config_path}")
                return self.config
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    if config_file.suffix in ['.yaml', '.yml']:
                        self.config = yaml.safe_load(f) or {}
                    elif config_file.suffix == '.json':
                        self.config = json.load(f)
                    else:
                        logger.error(f"Unsupported config format: {config_file.suffix}")
                        return self.config
                
                self._last_modified = config_file.stat().st_mtime
                logger.info(f"Configuration loaded from {self.config_path}")
                
                # Validate configuration if version is specified
                if 'version' in self.config:
                    self._validate_config_v1()
                
                # Apply environment variable overrides
                self._apply_env_overrides()
                
            except ConfigError as e:
                logger.error(f"Configuration validation error: {e}")
                raise
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        
        return self.config
    
    def _validate_config_v1(self):
        """
        Validate configuration v1.0 format.
        
        Raises:
            ConfigError: If configuration is invalid
        """
        # Check version
        version = self.config.get('version')
        if version != "1.0":
            raise ConfigError(f"Unsupported configuration version: {version}. Expected '1.0'")
        
        # Validate config section if present
        if 'config' in self.config:
            config_section = self.config['config']
            if 'music_dir' not in config_section:
                raise ConfigError("config.music_dir is required in configuration v1.0")
            
            # Validate optional numeric fields
            for field in ['default_volume', 'fade_in_duration', 'fade_out_duration']:
                if field in config_section:
                    value = config_section[field]
                    if not isinstance(value, (int, float)):
                        raise ConfigError(f"config.{field} must be a number")
                    if field == 'default_volume' and not (0.0 <= value <= 1.0):
                        raise ConfigError(f"config.default_volume must be between 0.0 and 1.0")
        
        # Validate schedules section
        if 'schedules' in self.config:
            schedules = self.config['schedules']
            if not isinstance(schedules, dict):
                raise ConfigError("schedules must be a dictionary")
            
            for name, schedule in schedules.items():
                self._validate_schedule(name, schedule)
        
        # Validate playlists section if present
        if 'playlists' in self.config:
            playlists = self.config['playlists']
            if not isinstance(playlists, dict):
                raise ConfigError("playlists must be a dictionary")
            
            for name, playlist in playlists.items():
                if not isinstance(playlist, list):
                    raise ConfigError(f"playlist '{name}' must be a list")
                if len(playlist) == 0:
                    raise ConfigError(f"playlist '{name}' cannot be empty")
    
    def _validate_schedule(self, name: str, schedule: Dict[str, Any]):
        """
        Validate a single schedule entry.
        
        Args:
            name: Schedule name
            schedule: Schedule configuration
            
        Raises:
            ConfigError: If schedule is invalid
        """
        if not isinstance(schedule, dict):
            raise ConfigError(f"Schedule '{name}' must be a dictionary")
        
        # Check that exactly one time format is used
        time_formats = ['times', 'time_range', 'schedule']
        used_formats = [fmt for fmt in time_formats if fmt in schedule]
        
        # Special case: 'times' can be either simple list or complex list
        if 'times' in schedule:
            times_value = schedule['times']
            if isinstance(times_value, list):
                if len(times_value) > 0 and isinstance(times_value[0], dict):
                    # Format 3: Complex time groups
                    for time_group in times_value:
                        if 'days' not in time_group or 'points' not in time_group:
                            raise ConfigError(f"Schedule '{name}': complex time groups must have 'days' and 'points'")
                        self._validate_days(time_group['days'], name)
                        if not isinstance(time_group['points'], list):
                            raise ConfigError(f"Schedule '{name}': 'points' must be a list")
                elif len(times_value) > 0 and isinstance(times_value[0], str):
                    # Format 1: Simple time points
                    if 'days' not in schedule:
                        raise ConfigError(f"Schedule '{name}': Format 1 requires 'days' field")
                    self._validate_days(schedule['days'], name)
                else:
                    raise ConfigError(f"Schedule '{name}': 'times' must be a non-empty list")
        
        elif 'time_range' in schedule:
            # Format 2: Time range with interval
            time_range = schedule['time_range']
            if not isinstance(time_range, dict):
                raise ConfigError(f"Schedule '{name}': 'time_range' must be a dictionary")
            if 'start' not in time_range or 'end' not in time_range or 'interval' not in time_range:
                raise ConfigError(f"Schedule '{name}': time_range must have 'start', 'end', and 'interval'")
            if 'days' not in schedule:
                raise ConfigError(f"Schedule '{name}': Format 2 requires 'days' field")
            self._validate_days(schedule['days'], name)
        
        elif 'schedule' in schedule:
            # Format 4: Compact schedule strings
            schedule_strings = schedule['schedule']
            if not isinstance(schedule_strings, list):
                raise ConfigError(f"Schedule '{name}': 'schedule' must be a list")
            if len(schedule_strings) == 0:
                raise ConfigError(f"Schedule '{name}': 'schedule' cannot be empty")
        
        else:
            raise ConfigError(f"Schedule '{name}': must specify one time format (times, time_range, or schedule)")
        
        # Validate mode section
        if 'mode' not in schedule:
            raise ConfigError(f"Schedule '{name}': 'mode' section is required")
        
        mode = schedule['mode']
        if not isinstance(mode, dict):
            raise ConfigError(f"Schedule '{name}': 'mode' must be a dictionary")
        
        if 'type' not in mode:
            raise ConfigError(f"Schedule '{name}': mode.type is required")
        
        if mode['type'] != 'random':
            raise ConfigError(f"Schedule '{name}': only 'random' mode type is supported")
        
        if 'playlist' not in mode:
            raise ConfigError(f"Schedule '{name}': mode.playlist is required")
        
        if not isinstance(mode['playlist'], list):
            raise ConfigError(f"Schedule '{name}': mode.playlist must be a list")
        
        if len(mode['playlist']) == 0:
            raise ConfigError(f"Schedule '{name}': mode.playlist cannot be empty")
        
        if 'play_count' not in mode:
            raise ConfigError(f"Schedule '{name}': mode.play_count is required")
        
        if not isinstance(mode['play_count'], int) or mode['play_count'] < 1:
            raise ConfigError(f"Schedule '{name}': mode.play_count must be a positive integer")
    
    def _validate_days(self, days: Union[str, List[str]], schedule_name: str):
        """
        Validate day specification.
        
        Args:
            days: Day specification
            schedule_name: Schedule name for error messages
            
        Raises:
            ConfigError: If days specification is invalid
        """
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        valid_shortcuts = ['weekday', 'weekend', 'all']
        
        if isinstance(days, str):
            days = [days]
        
        if not isinstance(days, list):
            raise ConfigError(f"Schedule '{schedule_name}': 'days' must be a string or list")
        
        for day_spec in days:
            if not isinstance(day_spec, str):
                raise ConfigError(f"Schedule '{schedule_name}': day specification must be a string")
            
            day_spec = day_spec.lower()
            
            # Check if it's a shortcut
            if day_spec in valid_shortcuts:
                continue
            
            # Check if it's a range
            if '-' in day_spec:
                parts = day_spec.split('-')
                if len(parts) != 2:
                    raise ConfigError(f"Schedule '{schedule_name}': invalid day range '{day_spec}'")
                if parts[0] not in valid_days or parts[1] not in valid_days:
                    raise ConfigError(f"Schedule '{schedule_name}': invalid day range '{day_spec}'")
                continue
            
            # Check if it's a comma-separated list (for Format 4)
            if ',' in day_spec:
                for day in day_spec.split(','):
                    day = day.strip()
                    if day not in valid_days and day not in valid_shortcuts:
                        raise ConfigError(f"Schedule '{schedule_name}': invalid day '{day}'")
                continue
            
            # Check if it's a single valid day
            if day_spec not in valid_days:
                raise ConfigError(f"Schedule '{schedule_name}': invalid day '{day_spec}'")
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to configuration."""
        # For v1.0 config, override the config section
        if 'version' in self.config and self.config['version'] == "1.0":
            if 'JINGLE_VOLUME' in os.environ:
                try:
                    self.config.setdefault('config', {})['default_volume'] = float(os.environ['JINGLE_VOLUME'])
                except ValueError:
                    logger.error("Invalid JINGLE_VOLUME value")
            
            if 'JINGLE_MUSIC_DIR' in os.environ:
                self.config.setdefault('config', {})['music_dir'] = os.environ['JINGLE_MUSIC_DIR']
        else:
            # Legacy format
            if 'JINGLE_VOLUME' in os.environ:
                try:
                    self.config.setdefault('player', {})['volume'] = float(os.environ['JINGLE_VOLUME'])
                except ValueError:
                    logger.error("Invalid JINGLE_VOLUME value")
            
            if 'JINGLE_MUSIC_DIR' in os.environ:
                self.config.setdefault('player', {})['music_dir'] = os.environ['JINGLE_MUSIC_DIR']
    
    def check_reload(self) -> bool:
        """
        Check if config file has been modified and reload if needed.
        
        Returns:
            True if config was reloaded, False otherwise
        """
        with self._lock:
            if not self.config_path:
                return False
            
            config_file = Path(self.config_path)
            if not config_file.exists():
                return False
            
            current_mtime = config_file.stat().st_mtime
            if current_mtime > self._last_modified:
                logger.info("Config file changed, reloading...")
                self.load_config()
                return True
        
        return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'player.volume')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        with self._lock:
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                    if value is None:
                        return default
                else:
                    return default
            
            return value if value is not None else default
    
    def set(self, key: str, value: Any):
        """
        Set configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        with self._lock:
            keys = key.split('.')
            config = self.config
            
            for k in keys[:-1]:
                config = config.setdefault(k, {})
            
            config[keys[-1]] = value
    
    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration dictionary."""
        with self._lock:
            return self.config.copy()
