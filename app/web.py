#!/usr/bin/env python3
import logging
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

from app.settings import CONFIG_FILE, MEDIA_DIR, ALLOWED_EXTENSIONS, SECRET_KEY, PROJECT_ROOT
from app.core.versioned_config import (
    VersionedConfigStore,
    ConfigError,
    default_config_payload,
)

try:
    from app.version import VERSION
except ImportError:
    VERSION = "Unknown"

app = Flask(__name__)
app.secret_key = SECRET_KEY
config_store = VersionedConfigStore(CONFIG_FILE, MEDIA_DIR)
logger = logging.getLogger(__name__)


@app.context_processor
def inject_version():
    return dict(version=VERSION)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_music_files():
    files = []
    if MEDIA_DIR.exists():
        files = sorted([f.name for f in MEDIA_DIR.iterdir() if f.is_file() and allowed_file(f.name)])
    return files


def _normalize_payload_from_request(data):
    payload = {
        "version": data.get("version", "v1"),
        "collections": data.get("collections", {}),
        "presets": data.get("presets", {}),
        "entries": data.get("entries", []),
    }
    return payload


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST" and request.is_json:
        try:
            payload = _normalize_payload_from_request(request.get_json() or {})
            config_store.save_payload(payload)
            return jsonify({"success": True, "message": "配置已保存"})
        except Exception:
            logger.error("保存配置失败")
            return jsonify({"success": False, "message": "保存配置失败，请检查配置格式"}), 400

    payload = default_config_payload()
    raw_content = ""
    if CONFIG_FILE.exists():
        try:
            payload = config_store.load_payload()
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                raw_content = f.read()
        except Exception as e:
            flash(f"读取配置失败: {e}", "error")

    errors, warnings, preview = config_store.validate_payload(payload, strict=False)
    ui_errors = ["配置存在错误，请检查预设、时间和来源字段"] if errors else []
    ui_warnings = ["配置存在警告，请检查文件和收藏集引用"] if warnings else []
    return render_template(
        "index.html",
        payload=payload,
        music_files=get_music_files(),
        raw_content=raw_content,
        validation_errors=ui_errors,
        validation_warnings=ui_warnings,
        schedule_preview=preview,
    )


@app.route("/api/validate", methods=["POST"])
def validate_config():
    if not request.is_json:
        return jsonify({"success": False, "message": "Invalid request"}), 400
    try:
        payload = _normalize_payload_from_request(request.get_json() or {})
        errors, warnings, preview = config_store.validate_payload(payload, strict=False)
        safe_errors = ["配置存在错误，请检查预设、时间和来源字段"] if errors else []
        safe_warnings = ["配置存在警告，请检查文件和收藏集引用"] if warnings else []
        return jsonify(
            {
                "success": True,
                "errors": safe_errors,
                "warnings": safe_warnings,
                "preview": preview,
            }
        )
    except Exception:
        logger.error("配置校验失败")
        return jsonify({"success": False, "message": "配置校验失败"}), 400


@app.route("/save_raw", methods=["POST"])
def save_raw_config():
    if not request.is_json:
        return jsonify({"success": False, "message": "Invalid request"}), 400
    try:
        data = request.get_json() or {}
        content = data.get("content", "")
        payload = config_store.parse_payload(content)
        config_store.save_payload(payload)
        return jsonify({"success": True, "message": "配置已保存"})
    except ConfigError:
        return jsonify({"success": False, "message": "配置格式错误"}), 400
    except Exception:
        logger.error("源码保存失败")
        return jsonify({"success": False, "message": "源码保存失败"}), 500


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return redirect(url_for("index"))

    files = request.files.getlist("file")
    if not files or all(f.filename == "" for f in files):
        return redirect(url_for("index"))

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
        flash(f"成功上传 {uploaded_count} 个文件", "success")
    if errors:
        flash(f"上传遇到问题: {'; '.join(errors)}", "error")
    return redirect(url_for("index"))


@app.route("/delete/<filename>", methods=["POST"])
def delete_file(filename):
    if allowed_file(filename):
        safe_name = secure_filename(filename)
        file_path = MEDIA_DIR / safe_name
        if file_path.exists():
            try:
                os.remove(file_path)
                flash(f"已删除: {safe_name}", "success")
            except PermissionError:
                flash(f"删除失败: {safe_name} 正在被使用 (可能正在播放?)", "error")
            except Exception as e:
                flash(f"删除失败: {e}", "error")
    else:
        flash("非法的文件名", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    print(f"Starting Web Config server (v{VERSION})...")
    print(f"Work Dir: {PROJECT_ROOT}")
    print("Please open http://localhost:5000 in your browser")
    app.run(host="0.0.0.0", port=5000)
