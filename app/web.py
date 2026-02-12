#!/usr/bin/env python3
import os
import re
from pathlib import Path
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'jingle_bell_secret_key'

# 使用 Pathlib 优化路径处理
APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
CONFIG_FILE = PROJECT_ROOT / 'config' / 'bells.conf'
MEDIA_DIR = PROJECT_ROOT / 'music'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg'}

class ConfigParser:
    """Helper class to parse and stringify bells.conf format"""
    
    @staticmethod
    def parse(content: str) -> list:
        entries = []
        lines = content.splitlines()
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            entry = {
                'id': line_num, # Use line index as temporary ID
                'days': [],
                'filenames': [],
                'times': [],
                'duration': None
            }
            
            # 1. Parse Days: (1,2,3)
            days_match = re.match(r'^\(([\d,\s]+)\)\s*(.*)', line)
            rest = line
            if days_match:
                days_str = days_match.group(1)
                entry['days'] = [int(d.strip()) for d in days_str.split(',') if d.strip()]
                rest = days_match.group(2)
            
            # 2. Parse Filenames: [a.mp3, b.mp3] or single.mp3
            # Need to be careful about splitting by comma
            # Strategy: Extract filenames part first
            
            # Check for list format [ ... ]
            files_match = re.match(r'^\[(.*?)\]\s*,\s*(.*)', rest)
            if files_match:
                files_str = files_match.group(1)
                entry['filenames'] = [f.strip() for f in files_str.split(',') if f.strip()]
                rest = files_match.group(2)
            else:
                # Single file, split by first comma
                parts = rest.split(',', 1)
                entry['filenames'] = [parts[0].strip()]
                if len(parts) > 1:
                    rest = parts[1]
                else:
                    rest = ""
            
            # 3. Parse Duration (optional MM:SS) and Times
            time_parts = [t.strip() for t in rest.split(',') if t.strip()]
            
            for part in time_parts:
                # Check if it looks like duration (MM:SS) vs time (HH:MM)
                # Actually in main.py, it distinguishes based on position or format?
                # main.py logic: if first part matches MM:SS AND there are more parts, it's duration.
                # Here we simplify: if we haven't found duration and it looks like MM:SS, treat as duration?
                # But time is also HH:MM. 
                # Let's strictly follow main.py logic:
                # If we encounter a part, if it's the first one and followed by others, check if it's duration.
                # However, users might mix.
                # Let's assume HH:MM is time. If user sets duration, it's rare.
                # For this UI, let's treat all HH:MM as time points for now to simplify.
                # If there's a need for duration control, we can add it later.
                # Wait, main.py logic:
                # duration = 0
                # if idx < len(parts) and re.match(r'^\d{1,2}:\d{2}$', parts[idx]) and (idx + 1) < len(parts):
                #    duration = parse...
                # So if there are at least 2 items left, check the first one.
                # Since we don't have easy way to distinguish 05:00 (duration) vs 05:00 (5am),
                # We will just treat everything as times in this UI version for simplicity,
                # unless we see a clear pattern.
                # To be safe, let's just parse all as times.
                
                entry['times'].append(part)
                
            entries.append(entry)
        return entries

    @staticmethod
    def stringify(entries: list) -> str:
        lines = []
        for entry in entries:
            parts = []
            
            # 1. Days
            if entry.get('days') and len(entry['days']) > 0:
                # sort days
                sorted_days = sorted([int(d) for d in entry['days']])
                days_str = ",".join(str(d) for d in sorted_days)
                parts.append(f"({days_str})")
            
            # 2. Filenames
            filenames = entry.get('filenames', [])
            if not filenames:
                continue # Skip invalid entry
            
            if len(filenames) > 1:
                f_str = "[" + ", ".join(filenames) + "]"
                # If there were days, we need to join with nothing or space? 
                # config format: (1,2)file.mp3 or (1,2) [a.mp3]
                # main.py splits by comma but ignores brackets.
                # So: (1,2)[a,b], 08:00
                if parts:
                     parts[0] += f_str
                else:
                     parts.append(f_str)
            else:
                if parts:
                    parts[0] += filenames[0]
                else:
                    parts.append(filenames[0])
            
            # 3. Times
            times = entry.get('times', [])
            if times:
                parts.append(", ".join(times))
            
            # Join all with comma
            # Note: The first part (Days+Files) is one chunk, then comma, then times
            lines.append(", ".join(parts))
            
        return "\n\n".join(lines)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_music_files():
    files = []
    if MEDIA_DIR.exists():
        # sort by name
        files = sorted([f.name for f in MEDIA_DIR.iterdir() if f.is_file() and allowed_file(f.name)])
    return files

@app.route('/', methods=['GET', 'POST'])
def index():
    saved = False
    
    # API: Save Config (JSON)
    if request.method == 'POST' and request.is_json:
        try:
            data = request.get_json()
            entries = data.get('entries', [])
            content = ConfigParser.stringify(entries)
            
            # 原子写入
            tmp_file = CONFIG_FILE.with_suffix('.tmp')
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            with open(tmp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            os.replace(tmp_file, CONFIG_FILE)
            return jsonify({'success': True, 'message': '配置已保存'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # Read Config
    content = ""
    entries = []
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            entries = ConfigParser.parse(content)
        except Exception as e:
            flash(f"读取配置失败: {e}", 'error')

    music_files = get_music_files()
    
    # Pass data as JSON string for Vue to pick up
    return render_template('index.html', 
                         entries=entries, 
                         music_files=music_files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('index'))
    
    files = request.files.getlist('file')
    if not files or all(f.filename == '' for f in files):
        return redirect(url_for('index'))
    
    uploaded_count = 0
    errors = []
    
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            try:
                file.save(MEDIA_DIR / filename)
                uploaded_count += 1
            except Exception as e:
                errors.append(f"{filename}: {e}")
        elif file.filename:
             errors.append(f"{file.filename}: 不支持的文件类型")
            
    if uploaded_count > 0:
        flash(f'成功上传 {uploaded_count} 个文件', 'success')
        
    if errors:
        flash(f'上传遇到问题: {"; ".join(errors)}', 'error')
        
    return redirect(url_for('index'))

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    if allowed_file(filename):
        safe_name = secure_filename(filename)
        file_path = MEDIA_DIR / safe_name
        
        if file_path.exists():
            try:
                os.remove(file_path)
                flash(f'已删除: {safe_name}', 'success')
            except PermissionError:
                flash(f'删除失败: {safe_name} 正在被使用 (可能正在播放?)', 'error')
            except Exception as e:
                flash(f'删除失败: {e}', 'error')
    else:
        flash('非法的文件名', 'error')
                
    return redirect(url_for('index'))

if __name__ == '__main__':
    print(f"Starting Web Config server...")
    print(f"Work Dir: {PROJECT_ROOT}")
    print(f"Please open http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000)
