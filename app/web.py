#!/usr/bin/env python3
import os
import re
from pathlib import Path
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

# 尝试导入版本号
try:
    from app.version import VERSION
except ImportError:
    try:
        import version
        VERSION = version.VERSION
    except ImportError:
        VERSION = "Unknown"

app = Flask(__name__)
app.secret_key = 'jingle_bell_secret_key'

# 注入版本号到模板
@app.context_processor
def inject_version():
    return dict(version=VERSION)

# 使用 Pathlib 优化路径处理
APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
CONFIG_FILE = PROJECT_ROOT / 'config' / 'bells.conf'
MEDIA_DIR = PROJECT_ROOT / 'music'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac'}

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
                if not parts[0].strip():
                     raise ValueError(f"第 {line_num+1} 行格式错误：缺少文件名")
                entry['filenames'] = [parts[0].strip()]
                if len(parts) > 1:
                    rest = parts[1]
                else:
                    rest = ""
            
            # 3. Parse Duration (optional MM:SS) and Times
            time_parts = [t.strip() for t in rest.split(',') if t.strip()]
            
            if not time_parts:
                 raise ValueError(f"第 {line_num+1} 行格式错误：缺少时间点")

            for part in time_parts:
                # Check format HH:MM or MM:SS or -HH:MM
                # Allow disabled times starting with -
                check_part = part[1:] if part.startswith('-') else part
                if not re.match(r'^\d{1,2}:\d{2}$', check_part):
                     raise ValueError(f"第 {line_num+1} 行时间格式错误：{part}")

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
                         music_files=music_files,
                         raw_content=content)

@app.route('/save_raw', methods=['POST'])
def save_raw_config():
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Invalid request'}), 400
        
    try:
        data = request.get_json()
        content = data.get('content', '')
        
        # 简单的语法检查：尝试解析
        # 如果解析过程中发现严重格式问题，ConfigParser可能会报错
        # 但目前的ConfigParser比较宽容，主要跳过错误行
        # 我们可以检查解析后的条目数量是否合理（可选）
        ConfigParser.parse(content)
        
        # 原子写入
        tmp_file = CONFIG_FILE.with_suffix('.tmp')
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(tmp_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        os.replace(tmp_file, CONFIG_FILE)
        return jsonify({'success': True, 'message': '配置已保存'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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
    print(f"Starting Web Config server (v{VERSION})...")
    print(f"Work Dir: {PROJECT_ROOT}")
    print(f"Please open http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000)
