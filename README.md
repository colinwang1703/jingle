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

### REST API for Remote Control

Jingle includes a REST API for remote control and dynamic configuration:

**Install API dependencies:**
```bash
pip3 install -r requirements-api.txt
```

**Start the API server:**
```bash
# Start API server
python3 -m jingle.api -c config/jingle.yaml -H 0.0.0.0 -p 5000

# Or with custom settings
python3 -m jingle.api --host 0.0.0.0 --port 8080 --config config/jingle.yaml
```

**API Endpoints:**

- `GET /api/status` - Get current status
- `POST /api/play` - Play music immediately
  ```json
  {"music": "song.mp3", "fade_in": 1.0, "loops": 0}
  ```
- `POST /api/stop` - Stop playback
  ```json
  {"fade_out": 1.0}
  ```
- `POST /api/pause` - Pause playback
- `POST /api/resume` - Resume playback
- `GET /api/volume` - Get current volume
- `POST /api/volume` - Set volume
  ```json
  {"volume": 0.8}
  ```
- `GET /api/schedules` - Get all schedules
- `POST /api/schedules` - Add new schedule
  ```json
  {"time": "every 1 hour", "music": "chime.mp3", "options": {"fade_in": 0.5}}
  ```
- `DELETE /api/schedules` - Clear all schedules
- `GET /api/music/list` - List available music files
- `POST /api/event` - Trigger custom event
  ```json
  {"event": "sensor_trigger"}
  ```

**Example API usage (with curl):**
```bash
# Play music
curl -X POST http://localhost:5000/api/play \
  -H "Content-Type: application/json" \
  -d '{"music": "morning.mp3", "fade_in": 2.0}'

# Set volume
curl -X POST http://localhost:5000/api/volume \
  -H "Content-Type: application/json" \
  -d '{"volume": 0.5}'

# Add schedule
curl -X POST http://localhost:5000/api/schedules \
  -H "Content-Type: application/json" \
  -d '{"time": "every 30 minutes", "music": "chime.mp3"}'

# Get status
curl http://localhost:5000/api/status
```

**Python API client example:**
```python
import requests

# Play music
response = requests.post('http://localhost:5000/api/play',
    json={'music': 'morning.mp3', 'fade_in': 2.0})
print(response.json())

# Set volume
response = requests.post('http://localhost:5000/api/volume',
    json={'volume': 0.8})
print(response.json())
```

See `examples/api_client_example.py` for a complete example.

### Running as a System Service

**Basic Service** (without API):

Create a systemd service file (`/etc/systemd/system/jingle.service`):

```ini
[Unit]
Description=Jingle Music Player Service
After=sound.target network.target
Wants=sound.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/jingle
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 -m jingle.main -c /home/pi/jingle/config/jingle.yaml
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**API Service** (with REST API):

Create a systemd service file (`/etc/systemd/system/jingle-api.service`):

```ini
[Unit]
Description=Jingle API Server
After=sound.target network.target
Wants=sound.target network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/jingle
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 -m jingle.api -c /home/pi/jingle/config/jingle.yaml -H 0.0.0.0 -p 5000
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
# Copy service file
sudo cp examples/jingle.service /etc/systemd/system/

# Or for API version
sudo cp examples/jingle-api.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable jingle.service

# Start service
sudo systemctl start jingle.service

# Check status
sudo systemctl status jingle.service

# View logs
sudo journalctl -u jingle.service -f
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