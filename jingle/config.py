"""
Configuration management module for Jingle.
Supports YAML, JSON, and environment variables with hot-reload capability.
"""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from threading import RLock

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages configuration loading and hot-reload for the music player.
    Supports YAML, JSON files and environment variable overrides.
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
                
                # Apply environment variable overrides
                self._apply_env_overrides()
                
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        
        return self.config
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to configuration."""
        # Check for common environment variable overrides
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
