#!/usr/bin/env python3
import os
import shutil
from pathlib import Path
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'jingle_bell_secret_key'

# 使用 Pathlib 优化路径处理
APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
CONFIG_FILE = PROJECT_ROOT / 'config' / 'bells.conf'
MEDIA_DIR = PROJECT_ROOT / 'music'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg'}

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
    content = ""
    
    if request.method == 'POST' and 'content' in request.form:
        content = request.form.get('content')
        if content:
            content = content.replace('\r\n', '\n')
            try:
                # 原子写入：写入临时文件后重命名
                tmp_file = CONFIG_FILE.with_suffix('.tmp')
                # Ensure config dir exists
                CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
                
                with open(tmp_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Windows 下 replace 可能失败如果目标存在，但在 Python 3.3+ os.replace 应该是原子的且覆盖
                # 不过为了安全，也可以用 shutil.move
                os.replace(tmp_file, CONFIG_FILE)
                saved = True
                flash('配置保存成功！', 'success')
            except Exception as e:
                flash(f"保存失败: {e}", 'error')
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            flash(f"读取配置失败: {e}", 'error')
    else:
        content = "# 配置文件不存在，保存后将自动创建"

    music_files = get_music_files()
    return render_template('index.html', content=content, saved=saved, music_files=music_files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            file.save(MEDIA_DIR / filename)
            flash(f'成功上传: {filename}', 'success')
        except Exception as e:
            flash(f'上传失败: {e}', 'error')
        
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
