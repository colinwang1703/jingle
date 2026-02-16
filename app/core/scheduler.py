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
        """检查当前时间是否需要播放铃声，优先匹配单点时间"""
        now = datetime.datetime.now()
        current_time = (now.hour, now.minute)
        today = now.isoweekday()

        range_entry = None

        for entry in self.bell_entries:
            # 检查周几
            if entry.get('days') is not None and today not in entry['days']:
                continue
            
            # 检查时间点
            for time_info in entry['times']:
                if time_info['time'] == current_time and not time_info['disabled']:
                    # 创建副本以避免修改原始配置
                    matched_entry = entry.copy()
                    
                    is_range = time_info.get('is_range', False)
                    if time_info.get('duration'):
                        matched_entry['duration'] = time_info['duration']
                    matched_entry['is_range'] = is_range
                    
                    if is_range:
                        # 暂时保存时间段任务
                        range_entry = matched_entry
                    else:
                        # 找到单点任务，立即返回（优先级最高）
                        return matched_entry
        
        # 如果没有单点任务，但有时间段任务，则返回时间段任务
        return range_entry

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
                        # 如果是时间段模式 (is_range=True)，我们需要不断播放
                        # 否则只播放一次
                        is_range = bell.get('is_range', False)
                        duration = bell.get('duration', 0)
                        
                        filenames = bell.get('filenames', [])
                        if not filenames: continue

                        if is_range:
                            logger.info(f"触发时间段播放: {duration}秒 (第{bell['line_num']}行)")
                            
                            # 记录开始时间
                            start_time = time.time()
                            range_filenames = bell.get('filenames', [])
                            
                            def play_next():
                                # 检查是否超时
                                elapsed = time.time() - start_time
                                remaining = duration - elapsed
                                
                                if remaining <= 0:
                                    logger.info("时间段结束，停止播放")
                                    return # 结束循环
                                
                                # 随机选择下一首
                                next_file = secrets.choice(range_filenames)
                                logger.info(f"时间段播放下一首: {next_file} (剩余 {int(remaining)}秒)")
                                
                                # 播放，但不设置 duration (让它自然播完或者被外部 stop 终止)
                                # 关键点：我们不传递 remaining 给 play 的 duration 参数
                                # 因为我们希望"把最后一首曲子放完再停"，而不是硬切断
                                # 除非 remaining 已经耗尽，上面的 check 会阻止开始新的一首
                                # 注意：这里 self.player.play 需要支持回调，我们刚才修改了 player.py
                                self.player.play(next_file, duration=0, next_track_callback=play_next)

                            # 启动第一首
                            play_next()
                            
                        else:
                            # 随机选择一首
                            chosen = secrets.choice(filenames)
                            logger.info(f"触发播放: {chosen} (第{bell['line_num']}行)")
                            # 确保清除可能存在的回调，以免影响单曲循环
                            self.player.play(chosen, duration, next_track_callback=None)
                
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
