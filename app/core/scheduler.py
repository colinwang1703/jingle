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
        """检查当前时间是否需要播放铃声，优先匹配单点时间，其次匹配时间段"""
        now = datetime.datetime.now()
        current_time = (now.hour, now.minute)
        today = now.isoweekday()

        range_entry = None

        for entry in self.bell_entries:
            # 检查周几
            if entry.get('days') is not None and today not in entry['days']:
                continue
            
            for time_info in entry['times']:
                if time_info['disabled']: continue

                # 1. 优先检查单点时间（保持不变，优先级最高）
                if time_info['time'] == current_time:
                    matched_entry = entry.copy()
                    is_range = time_info.get('is_range', False)
                    if time_info.get('duration'):
                        matched_entry['duration'] = time_info['duration']
                    matched_entry['is_range'] = is_range
                    return matched_entry

                # 2. 检查是否在时间段内 (新增逻辑)
                if time_info.get('is_range', False):
                    start_h, start_m = time_info['time']
                    duration = time_info['duration']
                    
                    # 构建当天的开始和结束时间
                    start_dt = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
                    end_dt = start_dt + datetime.timedelta(seconds=duration)
                    
                    # 检查当前时间是否在范围内
                    if start_dt <= now < end_dt:
                        matched_entry = entry.copy()
                        matched_entry['duration'] = duration
                        matched_entry['is_range'] = True
                        matched_entry['range_start_dt'] = start_dt  # 记录开始时间用于计算剩余时长
                        range_entry = matched_entry

        # 如果没有单点任务，返回匹配到的时间段任务
        return range_entry

    def run(self):
        """主循环：每分钟检查一次"""
        logger.info(f"铃声调度器开始运行 (v{VERSION})")
        last_checked_minute = -1
        self.current_range_signature = None  # 用于记录当前正在播放的时间段任务签名

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
                            # 生成任务签名 (行号 + 开始时间)，用于识别是否是同一个任务
                            signature = (bell['line_num'], bell.get('range_start_dt'))
                            
                            if self.player.is_busy():
                                if self.current_range_signature == signature:
                                    # 已经在播放这个时间段的音乐了，跳过，不做任何操作
                                    continue
                                else:
                                    # 播放器忙，但不是这个任务（可能是插播的铃声正在响）
                                    # 我们选择等待插播铃声结束，不强制打断
                                    continue
                            
                            # 播放器空闲，或者之前的任务已结束 -> 启动/恢复背景音乐
                            self.current_range_signature = signature
                            
                            # 计算剩余时长
                            start_dt = bell.get('range_start_dt')
                            total_duration = bell.get('duration', 0)
                            elapsed = (now - start_dt).total_seconds()
                            remaining = max(0, total_duration - elapsed)
                            
                            if remaining > 0:
                                logger.info(f"恢复/启动背景音乐，剩余时长: {int(remaining)}秒")
                                
                                # 记录开始时间 (相对于当前时刻)
                                start_time = time.time()
                                range_filenames = bell.get('filenames', [])
                                
                                def play_next():
                                    # 检查是否超时
                                    current_elapsed = time.time() - start_time
                                    current_remaining = remaining - current_elapsed
                                    
                                    if current_remaining <= 0:
                                        logger.info("时间段结束，停止播放")
                                        self.current_range_signature = None
                                        return # 结束循环
                                    
                                    # 随机选择下一首
                                    next_file = secrets.choice(range_filenames)
                                    logger.info(f"时间段播放下一首: {next_file} (剩余 {int(current_remaining)}秒)")
                                    
                                    # 播放，但不设置 duration (让它自然播完或者被外部 stop 终止)
                                    # 关键点：我们不传递 remaining 给 play 的 duration 参数
                                    # 因为我们希望"把最后一首曲子放完再停"，而不是硬切断
                                    # 除非 remaining 已经耗尽，上面的 check 会阻止开始新的一首
                                    # 注意：这里 self.player.play 需要支持回调，我们刚才修改了 player.py
                                    self.player.play(next_file, duration=0, next_track_callback=play_next)

                                # 启动第一首
                                play_next()
                            
                        else:
                            # 单点铃声 (高优先级)
                            # 清除背景音乐签名，标记背景音乐被打断
                            self.current_range_signature = None 
                            
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
