# Jingle 🎵

A lightweight timed music playback system designed for resource-constrained devices like Raspberry Pi Zero.

## Features

- **Minimal Resource Usage**: Optimized for low-spec hardware, preventing crashes and lag
- **Flexible Configuration**: Support for YAML/JSON config files and environment variables
- **Hot-Reload**: Update configuration without restarting the service
- **Extensible Scheduling**: Time-based and event-driven triggers
- **Modular Design**: Clean separation of concerns for easy maintenance and extension

## Installation

### Prerequisites

- Python 3.7 or higher
- SDL2 libraries (for pygame audio backend)

On Raspberry Pi/Debian-based systems:
```bash
sudo apt-get update
sudo apt-get install python3-pip python3-dev libsdl2-mixer-2.0-0 libsdl2-2.0-0
```

### Install Jingle

```bash
# Clone the repository
git clone https://github.com/colinwang1703/jingle.git
cd jingle

# Install dependencies
pip3 install -r requirements.txt

# Or install as a package
pip3 install -e .
```

## Quick Start

1. Create a music directory and add your audio files:
```bash
mkdir music
# Copy your music files to the music directory
```

2. Configure your playback schedule by editing `config/jingle.yaml`:
```yaml
player:
  music_dir: "./music"
  volume: 0.7

schedules:
  - time: "08:00"
    music: "morning.mp3"
    options:
      fade_in: 2.0
  
  - time: "every 2 hours"
    music: "reminder.mp3"
```

3. Run Jingle:
```bash
# Using the installed command
jingle -c config/jingle.yaml

# Or run directly
python3 -m jingle.main -c config/jingle.yaml
```

## Configuration

### Configuration File Format

Jingle supports both YAML and JSON configuration files.

**YAML Example** (`config/jingle.yaml`):
```yaml
player:
  music_dir: "./music"
  volume: 0.7

schedules:
  # Play at specific time (24-hour format)
  - time: "08:00"
    music: "morning.mp3"
    options:
      fade_in: 2.0
      loops: 0
  
  # Play at intervals
  - time: "every 30 minutes"
    music: "chime.mp3"
```

**JSON Example** (`config/jingle.json`):
```json
{
  "player": {
    "music_dir": "./music",
    "volume": 0.7
  },
  "schedules": [
    {
      "time": "08:00",
      "music": "morning.mp3",
      "options": {
        "fade_in": 2.0
      }
    }
  ]
}
```

### Schedule Time Formats

- **Specific time**: `"08:00"`, `"13:30"` (24-hour format)
- **Intervals**: 
  - `"every 30 minutes"`
  - `"every 2 hours"`
  - `"every 10 seconds"`

### Playback Options

- `fade_in`: Fade-in duration in seconds (default: 0)
- `fade_out`: Fade-out duration in seconds (default: 0)
- `loops`: Number of times to loop (-1 for infinite, 0 for once, default: 0)

### Environment Variable Overrides

- `JINGLE_VOLUME`: Override volume setting (0.0 to 1.0)
- `JINGLE_MUSIC_DIR`: Override music directory path

Example:
```bash
JINGLE_VOLUME=0.5 JINGLE_MUSIC_DIR=/home/pi/music jingle -c config/jingle.yaml
```

## Command Line Options

```bash
jingle [OPTIONS]

Options:
  -c, --config PATH         Path to configuration file (default: config/jingle.yaml)
  --no-hot-reload          Disable configuration hot-reload
  --reload-interval FLOAT  Hot-reload check interval in seconds (default: 5.0)
  -v, --verbose            Enable verbose logging
  -h, --help               Show help message
```

## Architecture

Jingle is designed with a modular architecture:

- **ConfigManager** (`jingle/config.py`): Handles configuration loading, hot-reload, and environment variable overrides
- **AudioPlayer** (`jingle/player.py`): Lightweight audio playback using pygame.mixer
- **MusicScheduler** (`jingle/scheduler.py`): Manages scheduled and event-driven playback
- **JingleApp** (`jingle/main.py`): Main application orchestrating all components

## Advanced Usage

### Programmatic Usage

```python
from jingle import ConfigManager, AudioPlayer, MusicScheduler

# Initialize components
config = ConfigManager('config/jingle.yaml')
player = AudioPlayer(music_dir='./music', volume=0.7)
scheduler = MusicScheduler(player=player)

# Add schedules
scheduler.add_schedule("09:00", "morning.mp3", fade_in=2.0)
scheduler.add_schedule("every 1 hour", "reminder.mp3")

# Start scheduler
scheduler.start()

# Add event handlers for custom triggers
def on_sensor_trigger():
    player.play("alert.mp3")

scheduler.add_event_handler("sensor_trigger", on_sensor_trigger)

# Trigger events
scheduler.trigger_event("sensor_trigger")
```

### Running as a System Service

Create a systemd service file (`/etc/systemd/system/jingle.service`):

```ini
[Unit]
Description=Jingle Music Player
After=sound.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/jingle
ExecStart=/usr/bin/python3 -m jingle.main -c /home/pi/jingle/config/jingle.yaml
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable jingle.service
sudo systemctl start jingle.service
```

## Supported Audio Formats

- MP3 (.mp3)
- WAV (.wav)
- OGG (.ogg)
- FLAC (.flac)
- M4A (.m4a)
- AAC (.aac)

## Performance Considerations

Jingle is optimized for resource-constrained devices:

- Uses pygame.mixer with reduced buffer size (512 bytes) for minimal latency
- Lower sample rate (22050 Hz) to reduce CPU usage
- Efficient scheduling with minimal overhead
- Hot-reload checks only every 5 seconds by default
- Thread-safe operations with minimal locking

## Troubleshooting

### No Sound Output

1. Check that SDL2 audio libraries are installed
2. Verify audio device is working: `speaker-test -t wav`
3. Check volume levels: `alsamixer`
4. Ensure music files are in the correct directory

### High CPU Usage

1. Reduce hot-reload frequency: `jingle -c config.yaml --reload-interval 10`
2. Use MP3 format instead of FLAC for smaller files
3. Avoid very long audio files if using loops

### Config Not Reloading

1. Ensure file modification time is updated when editing
2. Check file permissions
3. Watch logs for reload messages: `jingle -c config.yaml -v`

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## License

MIT License - see LICENSE file for details.

## Author

Colin Wang

## Acknowledgments

- Built with [pygame](https://www.pygame.org/) for audio playback
- Uses [schedule](https://github.com/dbader/schedule) for task scheduling
- Inspired by the need for simple, reliable music scheduling on embedded devices