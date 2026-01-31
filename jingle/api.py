"""
Simple REST API for dynamically controlling Jingle.
Allows remote control and configuration updates without restart.
"""

from flask import Flask, jsonify, request
import logging
from threading import Thread
from jingle import ConfigManager, AudioPlayer, MusicScheduler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Global state
config_manager = None
player = None
scheduler = None


def initialize_jingle(config_path='config/jingle.yaml'):
    """Initialize Jingle components."""
    global config_manager, player, scheduler
    
    config_manager = ConfigManager(config_path)
    
    music_dir = config_manager.get('player.music_dir', './music')
    volume = config_manager.get('player.volume', 0.7)
    
    player = AudioPlayer(music_dir=music_dir, volume=volume)
    scheduler = MusicScheduler(player=player)
    
    # Load schedules from config
    schedules = config_manager.get('schedules', [])
    for sched in schedules:
        time_spec = sched.get('time')
        music_file = sched.get('music')
        options = sched.get('options', {})
        
        if time_spec and music_file:
            scheduler.add_schedule(time_spec, music_file, **options)
    
    scheduler.start()
    logger.info("Jingle API initialized")


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current status."""
    return jsonify({
        'status': 'running',
        'scheduler_running': scheduler.is_running() if scheduler else False,
        'current_volume': player.get_volume() if player else 0.0,
        'music_dir': config_manager.get('player.music_dir') if config_manager else None
    })


@app.route('/api/play', methods=['POST'])
def play_music():
    """Play a music file immediately."""
    if not player:
        return jsonify({'error': 'Player not initialized'}), 500
    
    data = request.get_json()
    music_file = data.get('music')
    fade_in = data.get('fade_in', 0.0)
    loops = data.get('loops', 0)
    
    if not music_file:
        return jsonify({'error': 'Missing music parameter'}), 400
    
    success = player.play(music_file, loops=loops, fade_in=fade_in)
    
    if success:
        return jsonify({'success': True, 'message': f'Playing {music_file}'})
    else:
        return jsonify({'error': 'Failed to play music'}), 500


@app.route('/api/stop', methods=['POST'])
def stop_music():
    """Stop current playback."""
    if not player:
        return jsonify({'error': 'Player not initialized'}), 500
    
    data = request.get_json() or {}
    fade_out = data.get('fade_out', 0.0)
    
    player.stop(fade_out=fade_out)
    return jsonify({'success': True, 'message': 'Playback stopped'})


@app.route('/api/pause', methods=['POST'])
def pause_music():
    """Pause current playback."""
    if not player:
        return jsonify({'error': 'Player not initialized'}), 500
    
    player.pause()
    return jsonify({'success': True, 'message': 'Playback paused'})


@app.route('/api/resume', methods=['POST'])
def resume_music():
    """Resume paused playback."""
    if not player:
        return jsonify({'error': 'Player not initialized'}), 500
    
    player.unpause()
    return jsonify({'success': True, 'message': 'Playback resumed'})


@app.route('/api/volume', methods=['GET', 'POST'])
def volume():
    """Get or set volume."""
    if not player:
        return jsonify({'error': 'Player not initialized'}), 500
    
    if request.method == 'GET':
        return jsonify({'volume': player.get_volume()})
    
    else:  # POST
        data = request.get_json()
        new_volume = data.get('volume')
        
        if new_volume is None:
            return jsonify({'error': 'Missing volume parameter'}), 400
        
        try:
            new_volume = float(new_volume)
            player.set_volume(new_volume)
            return jsonify({'success': True, 'volume': player.get_volume()})
        except ValueError:
            return jsonify({'error': 'Invalid volume value'}), 400


@app.route('/api/schedules', methods=['GET'])
def get_schedules():
    """Get all scheduled tasks."""
    if not scheduler:
        return jsonify({'error': 'Scheduler not initialized'}), 500
    
    schedules = scheduler.get_schedules()
    return jsonify({'schedules': schedules})


@app.route('/api/schedules', methods=['POST'])
def add_schedule():
    """Add a new schedule."""
    if not scheduler:
        return jsonify({'error': 'Scheduler not initialized'}), 500
    
    data = request.get_json()
    time_spec = data.get('time')
    music_file = data.get('music')
    options = data.get('options', {})
    
    if not time_spec or not music_file:
        return jsonify({'error': 'Missing time or music parameter'}), 400
    
    scheduler.add_schedule(time_spec, music_file, **options)
    return jsonify({'success': True, 'message': 'Schedule added'})


@app.route('/api/schedules', methods=['DELETE'])
def clear_schedules():
    """Clear all schedules."""
    if not scheduler:
        return jsonify({'error': 'Scheduler not initialized'}), 500
    
    scheduler.clear_schedules()
    return jsonify({'success': True, 'message': 'All schedules cleared'})


@app.route('/api/music/list', methods=['GET'])
def list_music():
    """List available music files."""
    if not player:
        return jsonify({'error': 'Player not initialized'}), 500
    
    files = player.get_music_files()
    return jsonify({'music_files': files})


@app.route('/api/event', methods=['POST'])
def trigger_event():
    """Trigger a custom event."""
    if not scheduler:
        return jsonify({'error': 'Scheduler not initialized'}), 500
    
    data = request.get_json()
    event_name = data.get('event')
    
    if not event_name:
        return jsonify({'error': 'Missing event parameter'}), 400
    
    scheduler.trigger_event(event_name)
    return jsonify({'success': True, 'message': f'Event {event_name} triggered'})


def main():
    """Run the API server."""
    import argparse
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description='Jingle REST API Server')
    parser.add_argument(
        '-c', '--config',
        type=str,
        default=None,
        help='Path to configuration file (default: config/jingle.yaml if exists, else no config)'
    )
    parser.add_argument(
        '-H', '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=5000,
        help='Port to bind to (default: 5000)'
    )
    
    args = parser.parse_args()
    
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
    
    # Initialize Jingle
    initialize_jingle(config_path)
    
    # Run Flask app
    logger.info(f"Starting Jingle API server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == '__main__':
    main()
