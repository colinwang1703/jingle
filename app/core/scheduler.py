import datetime
import logging
import secrets
import threading
import os
from typing import Optional, Dict
from pathlib import Path
from app.settings import CONFIG_FILE, MEDIA_DIR
from app.core.player import BellPlayer
from app.core.parser import BellParser
try:
    from app.version import VERSION
except ImportError:
    VERSION = "Unknown"

logger = logging.getLogger(__name__)

class BellScheduler:
    """
    铃声调度器
    负责协调配置解析、时间检查和音频播放。
    """
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = Path(config_file)
        self.player = BellPlayer(MEDIA_DIR)
        self.parser = BellParser(self.config_file, MEDIA_DIR)
        self.bell_entries = []
        self.stop_event = threading.Event()
        self.last_modified = 0
        self.last_music_dir_modified = 0

    def load_config(self) -> bool:
        """加载配置文件，支持检测变更"""
        if not self.config_file.exists():
             logger.error(f"配置文件不存在: {self.config_file}")
             return False

        # 检查文件修改时间
        current_modified = os.path.getmtime(self.config_file)
        current_music_modified = 0
        if MEDIA_DIR.exists():
            current_music_modified = os.path.getmtime(MEDIA_DIR)

        if current_modified <= self.last_modified and current_music_modified <= self.last_music_dir_modified:
            return True

        logger.info("重新加载配置...")
        self.last_modified = current_modified
        self.last_music_dir_modified = current_music_modified
        
        self.bell_entries = self.parser.parse()
        logger.info(f"成功加载 {len(self.bell_entries)} 个铃声配置")
        return True

    def should_play_now(self) -> Optional[Dict]:
        """检查当前时间是否需要播放铃声"""
        now = datetime.datetime.now()
        current_time = (now.hour, now.minute)
        today = now.isoweekday()

        for entry in self.bell_entries:
            # 检查周几
            if entry.get('days') is not None and today not in entry['days']:
                continue
            
            # 检查时间点
            for time_info in entry['times']:
                if time_info['time'] == current_time and not time_info['disabled']:
                    return entry
        return None

    def run(self):
        """主循环：每分钟检查一次"""
        logger.info(f"铃声调度器开始运行 (v{VERSION})")
        last_checked_minute = -1

        try:
            while not self.stop_event.is_set():
                now = datetime.datetime.now()
                # 只有当分钟变化时才进行检查
                if now.minute != last_checked_minute:
                    last_checked_minute = now.minute
                    self.load_config()
                    
                    bell = self.should_play_now()
                    if bell:
                        # 随机选择一首
                        chosen = secrets.choice(bell.get('filenames', []))
                        logger.info(f"触发播放: {chosen} (第{bell['line_num']}行)")
                        self.player.play(chosen, bell.get('duration', 0))
                
                # 休眠1秒，避免CPU空转，同时保持响应
                self.stop_event.wait(1)
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在退出...")
        except Exception as e:
            logger.error(f"主循环发生错误: {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        """优雅关闭"""
        self.stop_event.set()
        self.player.quit()
        logger.info("铃声调度器已停止")
