# Jingle Configuration v1.0 Specification

## Overview
Jingle Configuration v1.0 provides a flexible, human-readable YAML format for defining audio scheduling systems. This specification is designed for maximum flexibility while maintaining clarity and ease of use.

## Version Declaration
All v1.0 configuration files MUST begin with a version declaration:
```yaml
version: "1.0"
```

## Global Configuration
The `config` section contains global settings applicable to all schedules unless overridden:
```yaml
config:
  music_dir: "./audio"         # Base directory for audio files (required)
  default_volume: 0.8          # Default volume (0.0 to 1.0, optional)
  fade_in_duration: 2.0        # Default fade-in duration in seconds (optional)
  fade_out_duration: 2.0       # Default fade-out duration in seconds (optional)
```

### Configuration Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `music_dir` | string | Yes | - | Base directory containing audio files |
| `default_volume` | float | No | 0.8 | Default playback volume (0.0 to 1.0) |
| `fade_in_duration` | float | No | 0.0 | Default fade-in duration in seconds |
| `fade_out_duration` | float | No | 0.0 | Default fade-out duration in seconds |

## Schedule Definitions
Each schedule is a named entry under the `schedules` section. Schedules support multiple time expression formats to accommodate different use cases.

### Basic Schedule Structure
```yaml
schedules:
  schedule_name:
    description: "Optional human-readable description"
    # Time specification (one of the formats below)
    # Playback mode specification
```

## Time Specification Formats
Jingle supports four complementary time specification formats. Each schedule MUST use exactly one format.

### Format 1: Simple Time Points
Ideal for scenarios like school bells with many fixed time points on the same days.

**Structure:**
```yaml
schedule_name:
  description: "Optional description"
  days: ["weekday"]  # Day specification
  times: ["08:00", "08:45", "09:00"]  # Time points
  mode:
    # Playback mode configuration
```

**Example:**
```yaml
class_bells:
  description: "School bells - Weekdays"
  days: ["weekday"]
  times: ["08:00", "08:45", "09:00", "09:45", "10:00", "10:45"]
  mode:
    type: "random"
    playlist: ["bell.mp3"]
    play_count: 1
```

### Format 2: Time Range with Interval
Suitable for hourly chimes or regular reminders within a time window.

**Structure:**
```yaml
schedule_name:
  description: "Optional description"
  days: ["weekday"]  # Day specification
  time_range:
    start: "09:00"    # Start time (HH:MM)
    end: "18:00"      # End time (HH:MM)
    interval: 60      # Minutes between playbacks
  mode:
    # Playback mode configuration
```

**Example:**
```yaml
hourly_reminders:
  description: "Hourly chimes during office hours"
  days: ["weekday"]
  time_range:
    start: "09:00"
    end: "18:00"
    interval: 60
  mode:
    type: "random"
    playlist: ["chime.mp3"]
    play_count: 1
    volume: 0.6
```

### Format 3: Complex Time Groups
Allows different time points for different days of the week.

**Structure:**
```yaml
schedule_name:
  description: "Optional description"
  times:
    - days: ["monday", "wednesday", "friday"]
      points: ["07:30", "08:00", "16:30"]
    - days: ["tuesday", "thursday"]
      points: ["08:00", "17:00"]
  mode:
    # Playback mode configuration
```

**Example:**
```yaml
weekly_program:
  description: "Different times on different days"
  times:
    - days: ["monday", "wednesday"]
      points: ["07:00", "12:00", "19:00"]
    - days: ["tuesday", "thursday"]
      points: ["08:00", "13:00", "20:00"]
    - days: ["friday"]
      points: ["09:00", "17:00"]
    - days: ["weekend"]
      points: ["10:00", "15:00"]
  mode:
    type: "random"
    playlist: ["background_music"]
    play_count: 2
```

### Format 4: Compact Schedule Strings
For advanced users who prefer a compact, text-based format.

**Structure:**
```yaml
schedule_name:
  description: "Optional description"
  schedule:
    - "weekday 08:00"
    - "saturday,sunday 10:00"
    - "monday,wednesday,friday 16:00"
  mode:
    # Playback mode configuration
```

**Example:**
```yaml
quick_setup:
  description: "Using compact schedule strings"
  schedule:
    - "monday,wednesday,friday 08:00"
    - "tuesday,thursday 09:00"
    - "saturday 10:00"
    - "sunday 11:00"
  mode:
    type: "random"
    playlist: ["morning_bells"]
    play_count: 1
```

## Day Specifications
All time formats support flexible day specifications:

| Value | Meaning | Examples |
|-------|---------|----------|
| `weekday` | Monday through Friday | `days: "weekday"` |
| `weekend` | Saturday and Sunday | `days: ["weekend"]` |
| `all` | Every day of the week | `days: "all"` |
| Day names | Specific days | `days: ["monday", "wednesday"]` |
| Ranges | Day ranges (inclusive) | `days: "monday-friday"` |
| Mixed arrays | Any combination | `days: ["monday", "wednesday-friday", "weekend"]` |

**Valid day names:** monday, tuesday, wednesday, thursday, friday, saturday, sunday

**Examples:**
```yaml
# Single shortcut
days: "weekday"

# Multiple specific days
days: ["monday", "wednesday", "friday"]

# Day range
days: "monday-friday"

# Mixed specification
days: ["monday", "wednesday-friday", "weekend"]

# Multiple shortcuts
days: ["weekday", "saturday"]
```

## Playback Modes

### Random Play Mode
Plays a specified number of tracks randomly selected from a playlist.

**Structure:**
```yaml
mode:
  type: "random"
  playlist: ["track1.mp3", "track2.mp3", "track3.mp3"]  # Direct file list
  play_count: 3           # Number of tracks to play (1 for single track)
  # Optional overrides:
  volume: 0.9             # Override default volume
  fade_in: 3.0            # Override fade-in duration
  fade_out: 3.0           # Override fade-out duration
```

**Mode Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Must be "random" |
| `playlist` | array | Yes | List of audio files or playlist references |
| `play_count` | integer | Yes | Number of tracks to play (minimum 1) |
| `volume` | float | No | Override default volume (0.0 to 1.0) |
| `fade_in` | float | No | Override fade-in duration (seconds) |
| `fade_out` | float | No | Override fade-out duration (seconds) |

**Playlist References:**
Instead of listing files directly, you can reference globally defined playlists:
```yaml
mode:
  type: "random"
  playlist: ["morning_bells"]    # Reference to playlist name
  play_count: 1
```

## Global Playlists (Optional)
Define reusable playlists that can be referenced by multiple schedules:

```yaml
playlists:
  morning_bells:
    - "bell_gentle.mp3"
    - "bell_bright.mp3"
    - "bell_chime.mp3"
  
  background_music:
    - "ambient_1.mp3"
    - "ambient_2.mp3"
    - "piano_soft.mp3"
  
  single_track:  # Even single tracks can be defined as playlists
    - "special_event.mp3"
```

## Complete Example
```yaml
# Jingle Configuration v1.0
# Complete example demonstrating all formats

version: "1.0"

config:
  music_dir: "./sounds"
  default_volume: 0.8
  fade_in_duration: 2.0
  fade_out_duration: 2.0

schedules:
  # Format 1: Simple time points for school bells
  school_bells:
    description: "Elementary school daily bells"
    days: ["weekday"]
    times: ["08:30", "09:15", "10:00", "10:45", "11:30", "12:15"]
    mode:
      type: "random"
      playlist: ["school_bells"]
      play_count: 1

  # Format 2: Time range for office reminders
  office_reminders:
    description: "Hourly reminders during work hours"
    days: ["weekday"]
    time_range:
      start: "09:00"
      end: "18:00"
      interval: 60
    mode:
      type: "random"
      playlist: ["reminder_soft.mp3"]
      play_count: 1
      volume: 0.6

  # Format 3: Complex schedule for varied weekly timetable
  weekly_program:
    description: "Different times on different days"
    times:
      - days: ["monday", "wednesday"]
        points: ["07:00", "12:00", "19:00"]
      - days: ["tuesday", "thursday"]
        points: ["08:00", "13:00", "20:00"]
      - days: ["friday"]
        points: ["09:00", "17:00"]
      - days: ["weekend"]
        points: ["10:00", "15:00"]
    mode:
      type: "random"
      playlist: ["background_music"]
      play_count: 2
      fade_in: 5.0

  # Format 4: Compact strings for quick configuration
  quick_setup:
    description: "Using compact schedule strings"
    schedule:
      - "monday,wednesday,friday 08:00"
      - "tuesday,thursday 09:00"
      - "saturday 10:00"
    mode:
      type: "random"
      playlist: ["weekend_mix"]
      play_count: 3

playlists:
  school_bells:
    - "bell_short.mp3"
    - "bell_medium.mp3"
    - "bell_long.mp3"
  
  background_music:
    - "ambient_calm.mp3"
    - "jazz_soft.mp3"
    - "classical_light.mp3"
  
  weekend_mix:
    - "relaxing_1.mp3"
    - "upbeat_2.mp3"
    - "chill_3.mp3"
```

## Environment Variable Overrides
Configuration values can be overridden using environment variables:

| Variable | Overrides | Example |
|----------|-----------|---------|
| `JINGLE_VOLUME` | `config.default_volume` | `JINGLE_VOLUME=0.5 jingle -c config.yaml` |
| `JINGLE_MUSIC_DIR` | `config.music_dir` | `JINGLE_MUSIC_DIR=/music jingle -c config.yaml` |

## Implementation Notes

### Time Format
- All times use 24-hour format (HH:MM)
- Examples: "08:00", "13:45", "23:59"

### File Paths
- Audio file paths are relative to `music_dir` unless specified as absolute paths
- Forward slashes (/) work on all platforms
- Examples: "music.mp3", "subfolder/song.mp3", "/absolute/path/to/file.mp3"

### Playlist Behavior
- If `play_count` equals playlist size, all tracks play in random order
- If `play_count` is less than playlist size, random tracks are selected without replacement
- If `play_count` is greater than playlist size, all tracks play in random order

### Schedule Execution
- When multiple schedules are configured for the same time, all will be triggered
- Each schedule executes independently in its own context
- Overlapping schedules may play audio simultaneously

### Validation
- Configuration is validated at load time
- Invalid configurations will prevent the application from starting
- Validation errors provide specific messages about what needs to be fixed

## Error Handling

### Common Validation Errors

**Missing required field:**
```
ConfigError: config.music_dir is required in configuration v1.0
```

**Invalid day specification:**
```
ConfigError: Schedule 'my_schedule': invalid day 'funday'
```

**Empty playlist:**
```
ConfigError: Schedule 'my_schedule': mode.playlist cannot be empty
```

**Invalid time format:**
```
ConfigError: Schedule 'my_schedule': must specify one time format
```

## Migration from Legacy Format

If you have an existing Jingle configuration, here's how to migrate to v1.0:

### Legacy Format:
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

### V1.0 Format:
```yaml
version: "1.0"

config:
  music_dir: "./music"
  default_volume: 0.7

schedules:
  morning_music:
    days: "all"
    times: ["08:00"]
    mode:
      type: "random"
      playlist: ["morning.mp3"]
      play_count: 1
      fade_in: 2.0
  
  # Note: Interval schedules need to be converted to time ranges
  # "every 2 hours" becomes a time range with 120-minute intervals
  hourly_reminder:
    days: "all"
    time_range:
      start: "00:00"
      end: "22:00"
      interval: 120
    mode:
      type: "random"
      playlist: ["reminder.mp3"]
      play_count: 1
```

## Best Practices

### 1. Use Descriptive Schedule Names
```yaml
schedules:
  morning_wake_up_bells:  # Good: descriptive
    # ...
  
  schedule1:  # Bad: not descriptive
    # ...
```

### 2. Organize with Global Playlists
```yaml
# Good: reusable playlists
playlists:
  morning_bells:
    - "bell1.mp3"
    - "bell2.mp3"

schedules:
  morning_schedule:
    mode:
      playlist: ["morning_bells"]
```

### 3. Add Descriptions
```yaml
schedules:
  complex_schedule:
    description: "Plays different music on weekdays vs weekends"
    # ...
```

### 4. Use Appropriate Time Format
- Format 1: Dense schedules with same times every day
- Format 2: Regular intervals
- Format 3: Different times on different days
- Format 4: Quick setups and prototypes

### 5. Test Configuration
```bash
# Validate configuration without running
jingle -c config/jingle_v1.yaml --validate
```

## Troubleshooting

### Configuration Won't Load
- Check YAML syntax (indentation, colons, quotes)
- Ensure version is "1.0" (string, not number)
- Verify all required fields are present

### Schedule Not Triggering
- Verify time format is HH:MM (24-hour)
- Check day specification is valid
- Ensure audio files exist in music_dir

### Audio Not Playing
- Check file paths relative to music_dir
- Verify audio file format is supported (mp3, wav, ogg, flac, m4a, aac)
- Check volume settings (not set to 0.0)

## Further Resources
- See `config/jingle_v1.yaml` for a complete working example
- Check the README.md for installation and usage instructions
- Visit the GitHub repository for the latest updates
