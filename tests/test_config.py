"""
Tests for ConfigManager.
"""

import os
import json
import yaml
import tempfile
import time
from pathlib import Path
import pytest

from jingle.config import ConfigManager, ConfigError


class TestConfigManager:
    """Test cases for ConfigManager."""
    
    def test_init_without_config(self):
        """Test initialization without config file."""
        manager = ConfigManager()
        assert manager.config == {}
    
    def test_load_yaml_config(self):
        """Test loading YAML configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                'player': {'volume': 0.8, 'music_dir': '/music'},
                'schedules': [{'time': '10:00', 'music': 'test.mp3'}]
            }, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            assert manager.get('player.volume') == 0.8
            assert manager.get('player.music_dir') == '/music'
            assert len(manager.get('schedules', [])) == 1
        finally:
            os.unlink(config_path)
    
    def test_load_json_config(self):
        """Test loading JSON configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                'player': {'volume': 0.6},
                'schedules': []
            }, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            assert manager.get('player.volume') == 0.6
        finally:
            os.unlink(config_path)
    
    def test_get_with_default(self):
        """Test get with default value."""
        manager = ConfigManager()
        assert manager.get('nonexistent', 'default') == 'default'
        assert manager.get('nested.key', 42) == 42
    
    def test_set_value(self):
        """Test setting configuration value."""
        manager = ConfigManager()
        manager.set('player.volume', 0.9)
        assert manager.get('player.volume') == 0.9
        
        manager.set('nested.deep.value', 'test')
        assert manager.get('nested.deep.value') == 'test'
    
    def test_environment_override(self):
        """Test environment variable override."""
        os.environ['JINGLE_VOLUME'] = '0.5'
        os.environ['JINGLE_MUSIC_DIR'] = '/test/music'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'player': {'volume': 0.8}}, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            # Environment variable should override config file
            assert manager.get('player.volume') == 0.5
            assert manager.get('player.music_dir') == '/test/music'
        finally:
            os.unlink(config_path)
            del os.environ['JINGLE_VOLUME']
            del os.environ['JINGLE_MUSIC_DIR']
    
    def test_hot_reload(self):
        """Test configuration hot-reload."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'player': {'volume': 0.7}}, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            assert manager.get('player.volume') == 0.7
            
            # Modify config file
            time.sleep(0.1)  # Ensure file mtime changes
            with open(config_path, 'w') as f:
                yaml.dump({'player': {'volume': 0.9}}, f)
            
            # Check reload
            assert manager.check_reload() == True
            assert manager.get('player.volume') == 0.9
            
            # Second check should return False (no change)
            assert manager.check_reload() == False
        finally:
            os.unlink(config_path)
    
    def test_get_all(self):
        """Test getting entire configuration."""
        manager = ConfigManager()
        manager.set('key1', 'value1')
        manager.set('key2', 'value2')
        
        config = manager.get_all()
        assert 'key1' in config
        assert 'key2' in config
        assert config['key1'] == 'value1'
    
    def test_v1_config_valid(self):
        """Test loading valid v1.0 configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                'version': '1.0',
                'config': {
                    'music_dir': '/music',
                    'default_volume': 0.8,
                    'fade_in_duration': 2.0,
                    'fade_out_duration': 2.0
                },
                'schedules': {
                    'test_schedule': {
                        'days': ['weekday'],
                        'times': ['08:00', '12:00'],
                        'mode': {
                            'type': 'random',
                            'playlist': ['test.mp3'],
                            'play_count': 1
                        }
                    }
                }
            }, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            assert manager.get('version') == '1.0'
            assert manager.get('config.music_dir') == '/music'
            assert manager.get('config.default_volume') == 0.8
        finally:
            os.unlink(config_path)
    
    def test_v1_config_missing_version(self):
        """Test that missing version declaration still loads (legacy format)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                'config': {
                    'music_dir': '/music'
                }
            }, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            # Should load without error (treated as legacy format)
            assert manager.get('config.music_dir') == '/music'
        finally:
            os.unlink(config_path)
    
    def test_v1_config_invalid_version(self):
        """Test error on invalid version."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                'version': '2.0',
                'config': {
                    'music_dir': '/music'
                }
            }, f)
            config_path = f.name
        
        try:
            with pytest.raises(ConfigError):
                manager = ConfigManager(config_path)
        finally:
            os.unlink(config_path)
    
    def test_v1_config_missing_music_dir(self):
        """Test error when music_dir is missing in v1.0."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                'version': '1.0',
                'config': {
                    'default_volume': 0.8
                }
            }, f)
            config_path = f.name
        
        try:
            with pytest.raises(ConfigError):
                manager = ConfigManager(config_path)
        finally:
            os.unlink(config_path)
    
    def test_v1_config_invalid_schedule(self):
        """Test error on invalid schedule format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                'version': '1.0',
                'config': {
                    'music_dir': '/music'
                },
                'schedules': {
                    'test_schedule': {
                        'days': ['weekday'],
                        'times': ['08:00'],
                        # Missing mode section
                    }
                }
            }, f)
            config_path = f.name
        
        try:
            with pytest.raises(ConfigError):
                manager = ConfigManager(config_path)
        finally:
            os.unlink(config_path)
    
    def test_v1_config_empty_playlist(self):
        """Test error on empty playlist."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                'version': '1.0',
                'config': {
                    'music_dir': '/music'
                },
                'schedules': {
                    'test_schedule': {
                        'days': ['weekday'],
                        'times': ['08:00'],
                        'mode': {
                            'type': 'random',
                            'playlist': [],  # Empty playlist
                            'play_count': 1
                        }
                    }
                }
            }, f)
            config_path = f.name
        
        try:
            with pytest.raises(ConfigError):
                manager = ConfigManager(config_path)
        finally:
            os.unlink(config_path)
    
    def test_v1_config_invalid_day(self):
        """Test error on invalid day specification."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                'version': '1.0',
                'config': {
                    'music_dir': '/music'
                },
                'schedules': {
                    'test_schedule': {
                        'days': ['invalidday'],
                        'times': ['08:00'],
                        'mode': {
                            'type': 'random',
                            'playlist': ['test.mp3'],
                            'play_count': 1
                        }
                    }
                }
            }, f)
            config_path = f.name
        
        try:
            with pytest.raises(ConfigError):
                manager = ConfigManager(config_path)
        finally:
            os.unlink(config_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
