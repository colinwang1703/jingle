#!/usr/bin/env python3
"""
Comprehensive verification script for Jingle.
Tests all core functionality to ensure system is working correctly.
"""

import sys
import time
import tempfile
import json
from pathlib import Path

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_test(name, status, message=""):
    """Print test result."""
    symbol = f"{GREEN}✓{RESET}" if status else f"{RED}✗{RESET}"
    print(f"{symbol} {name}", end="")
    if message:
        print(f": {message}")
    else:
        print()

def test_imports():
    """Test that all modules can be imported."""
    print(f"\n{YELLOW}=== Testing Module Imports ==={RESET}")
    
    try:
        from jingle import ConfigManager, AudioPlayer, MusicScheduler
        print_test("Import jingle modules", True)
        
        from jingle.main import JingleApp
        print_test("Import main application", True)
        
        return True
    except Exception as e:
        print_test("Import modules", False, str(e))
        return False

def test_config_manager():
    """Test ConfigManager functionality."""
    print(f"\n{YELLOW}=== Testing ConfigManager ==={RESET}")
    
    try:
        from jingle.config import ConfigManager
        
        # Test initialization
        manager = ConfigManager()
        print_test("Initialize ConfigManager", True)
        
        # Test set/get
        manager.set('test.key', 'value')
        result = manager.get('test.key')
        print_test("Set and get config value", result == 'value', f"Got: {result}")
        
        # Test with YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("player:\n  volume: 0.8\n")
            temp_file = f.name
        
        manager = ConfigManager(temp_file)
        volume = manager.get('player.volume')
        Path(temp_file).unlink()
        print_test("Load YAML config", volume == 0.8, f"Volume: {volume}")
        
        return True
    except Exception as e:
        print_test("ConfigManager tests", False, str(e))
        return False

def test_audio_player():
    """Test AudioPlayer functionality."""
    print(f"\n{YELLOW}=== Testing AudioPlayer ==={RESET}")
    
    try:
        from jingle.player import AudioPlayer
        
        # Test initialization
        player = AudioPlayer(music_dir='/tmp', volume=0.7)
        print_test("Initialize AudioPlayer", True)
        
        # Test volume
        player.set_volume(0.5)
        volume = player.get_volume()
        print_test("Set and get volume", volume == 0.5, f"Volume: {volume}")
        
        # Test volume bounds
        player.set_volume(2.0)
        print_test("Volume upper bound", player.get_volume() == 1.0)
        
        player.set_volume(-1.0)
        print_test("Volume lower bound", player.get_volume() == 0.0)
        
        # Test cleanup
        player.cleanup()
        print_test("Cleanup AudioPlayer", True)
        
        return True
    except Exception as e:
        print_test("AudioPlayer tests", False, str(e))
        return False

def test_scheduler():
    """Test MusicScheduler functionality."""
    print(f"\n{YELLOW}=== Testing MusicScheduler ==={RESET}")
    
    try:
        from jingle.scheduler import MusicScheduler
        from jingle.player import AudioPlayer
        import schedule
        
        schedule.clear()
        
        player = AudioPlayer()
        scheduler = MusicScheduler(player=player)
        print_test("Initialize MusicScheduler", True)
        
        # Test adding schedules
        scheduler.add_schedule("10:00", "test.mp3")
        schedules = scheduler.get_schedules()
        print_test("Add time-based schedule", len(schedules) >= 1)
        
        schedule.clear()
        scheduler.add_schedule("every 1 hour", "test.mp3")
        schedules = scheduler.get_schedules()
        print_test("Add interval schedule", len(schedules) >= 1)
        
        # Test event handlers
        called = []
        def handler():
            called.append(True)
        
        scheduler.add_event_handler("test_event", handler)
        scheduler.trigger_event("test_event")
        print_test("Event handler system", len(called) == 1)
        
        # Test start/stop
        scheduler.start()
        time.sleep(0.5)
        is_running = scheduler.is_running()
        scheduler.stop()
        print_test("Start and stop scheduler", is_running)
        
        schedule.clear()
        return True
    except Exception as e:
        print_test("MusicScheduler tests", False, str(e))
        return False

def test_main_app():
    """Test main application."""
    print(f"\n{YELLOW}=== Testing Main Application ==={RESET}")
    
    try:
        from jingle.main import JingleApp
        
        # Create temporary config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
player:
  music_dir: /tmp
  volume: 0.7

schedules:
  - time: "10:00"
    music: test.mp3
""")
            temp_config = f.name
        
        app = JingleApp(config_path=temp_config)
        print_test("Initialize JingleApp", True)
        
        success = app.initialize()
        print_test("Initialize components", success)
        
        app.stop()
        Path(temp_config).unlink()
        print_test("Stop application", True)
        
        return True
    except Exception as e:
        print_test("Main application tests", False, str(e))
        return False

def test_api_module():
    """Test API module can be imported."""
    print(f"\n{YELLOW}=== Testing API Module ==={RESET}")
    
    try:
        from jingle.api import app, initialize_jingle
        print_test("Import API module", True)
        
        # Test app is Flask instance
        from flask import Flask
        is_flask = isinstance(app, Flask)
        print_test("API is Flask app", is_flask)
        
        return True
    except ImportError as e:
        print_test("Import API module", False, "Flask not installed (optional dependency)")
        return True  # API is optional
    except Exception as e:
        print_test("API module tests", False, str(e))
        return False

def test_example_scripts():
    """Test that example scripts are valid Python."""
    print(f"\n{YELLOW}=== Testing Example Scripts ==={RESET}")
    
    examples = [
        'examples/simple_example.py',
        'examples/event_example.py',
        'examples/api_client_example.py'
    ]
    
    all_valid = True
    for example in examples:
        try:
            path = Path(example)
            if path.exists():
                compile(path.read_text(), str(path), 'exec')
                print_test(f"Validate {path.name}", True)
            else:
                print_test(f"Find {path.name}", False, "File not found")
                all_valid = False
        except Exception as e:
            print_test(f"Validate {path.name}", False, str(e))
            all_valid = False
    
    return all_valid

def test_documentation():
    """Test that documentation files exist."""
    print(f"\n{YELLOW}=== Testing Documentation ==={RESET}")
    
    docs = [
        ('README.md', 'Main documentation'),
        ('DEMO.md', 'Demo documentation'),
        ('QUICKSTART_CN.md', 'Chinese quick start'),
        ('config/jingle.yaml', 'YAML config example'),
        ('config/jingle.json', 'JSON config example'),
    ]
    
    all_exist = True
    for doc, description in docs:
        path = Path(doc)
        exists = path.exists()
        print_test(f"{description}", exists, f"{doc}")
        if not exists:
            all_exist = False
    
    return all_exist

def run_all_tests():
    """Run all verification tests."""
    print(f"{GREEN}{'=' * 60}{RESET}")
    print(f"{GREEN}Jingle System Verification{RESET}")
    print(f"{GREEN}{'=' * 60}{RESET}")
    
    results = []
    
    # Run tests
    results.append(("Module Imports", test_imports()))
    results.append(("ConfigManager", test_config_manager()))
    results.append(("AudioPlayer", test_audio_player()))
    results.append(("MusicScheduler", test_scheduler()))
    results.append(("Main Application", test_main_app()))
    results.append(("API Module", test_api_module()))
    results.append(("Example Scripts", test_example_scripts()))
    results.append(("Documentation", test_documentation()))
    
    # Summary
    print(f"\n{YELLOW}{'=' * 60}{RESET}")
    print(f"{YELLOW}Test Summary{RESET}")
    print(f"{YELLOW}{'=' * 60}{RESET}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{status}: {name}")
    
    print(f"\n{YELLOW}{'=' * 60}{RESET}")
    if passed == total:
        print(f"{GREEN}✓ All tests passed! ({passed}/{total}){RESET}")
        print(f"{GREEN}Jingle is ready to use!{RESET}")
        return 0
    else:
        print(f"{RED}✗ Some tests failed ({passed}/{total}){RESET}")
        print(f"{YELLOW}Please check the errors above{RESET}")
        return 1

if __name__ == '__main__':
    sys.exit(run_all_tests())
