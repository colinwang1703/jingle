import os
from pathlib import Path

# Base directories
APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
CONFIG_DIR = PROJECT_ROOT / 'config'
MEDIA_DIR = PROJECT_ROOT / 'music'

# Files
CONFIG_FILE = CONFIG_DIR / 'bells.conf'
LOG_FILE = PROJECT_ROOT / 'bell_scheduler.log'

# Configuration
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac'}
SECRET_KEY = 'jingle_bell_secret_key'
