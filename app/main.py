#!/usr/bin/env python3
"""
铃声播放系统
从配置文件读取铃声计划，定时检查并播放铃声
"""

import argparse
import datetime
import time
import logging
import os
import re
import random
import pygame
import threading
from typing import List, Dict, Tuple, Optional
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bell_scheduler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BellScheduler:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.bell_entries: List[Dict] = []
        self.current_playing: Optional[str] = None
        self.stop_event = threading.Event()
        self.last_modified = 0
        self.pygame_initialized = False
        
        # 初始化pygame mixer
        self._init_audio()
        
    def _init_audio(self):
        """初始化音频系统"""
        try:
            pygame.mixer.init()
            self.pygame_initialized = True
            logger.info("音频系统初始化成功")
        except Exception as e:
            logger.error(f"音频系统初始化失败: {e}")
            self.pygame_initialized = False
    
    def parse_time(self, time_str: str) -> Optional[Tuple[int, int]]:
        """
        解析时间字符串，支持格式: HH:MM 或 H:MM
        返回 (小时, 分钟) 元组，解析失败返回None
        """
        time_str = time_str.strip()
        
        # 检查是否被禁用（以-开头）
        if time_str.startswith('-'):
            time_str = time_str[1:].strip()
        
        # 匹配时间格式
        time_pattern = r'^(\d{1,2}):(\d{2})$'
        match = re.match(time_pattern, time_str)
        
        if not match:
            logger.warning(f"时间格式错误: {time_str}")
            return None
            
        try:
            hour = int(match.group(1))
            minute = int(match.group(2))
            
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return (hour, minute)
            else:
                logger.warning(f"时间超出范围: {hour}:{minute:02d}")
                return None
                
        except ValueError as e:
            logger.warning(f"时间解析错误 {time_str}: {e}")
            return None
    
    def parse_duration(self, duration_str: str) -> Optional[int]:
        """
        解析持续时间字符串，格式: MM:SS 或 M:SS
        返回总秒数，解析失败返回None
        """
        duration_str = duration_str.strip()
        duration_pattern = r'^(\d{1,2}):(\d{2})$'
        match = re.match(duration_pattern, duration_str)
        
        if not match:
            logger.warning(f"持续时间格式错误: {duration_str}")
            return None
            
        try:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            
            if minutes >= 0 and 0 <= seconds <= 59:
                return minutes * 60 + seconds
            else:
                logger.warning(f"持续时间超出范围: {duration_str}")
                return None
                
        except ValueError as e:
            logger.warning(f"持续时间解析错误 {duration_str}: {e}")
            return None
    
    def load_config(self) -> bool:
        """
        加载配置文件
        返回是否成功加载
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(self.config_file):
                logger.error(f"配置文件不存在: {self.config_file}")
                return False
            
            # 检查文件是否被修改
            current_modified = os.path.getmtime(self.config_file)
            if current_modified <= self.last_modified:
                return True  # 文件未修改，不需要重新加载
            
            self.last_modified = current_modified
            
            # 清空现有条目
            self.bell_entries.clear()

            # 读取配置文件
            with open(self.config_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            def split_fields(line: str) -> List[str]:
                """
                按逗号分割，但忽略方括号 [] 和圆括号 () 内的逗号。
                返回已strip的字段列表。
                """
                parts: List[str] = []
                cur = []
                depth_square = 0
                depth_round = 0
                for ch in line:
                    if ch == '[':
                        depth_square += 1
                    elif ch == ']':
                        if depth_square > 0:
                            depth_square -= 1
                    elif ch == '(':
                        depth_round += 1
                    elif ch == ')':
                        if depth_round > 0:
                            depth_round -= 1

                    if ch == ',' and depth_square == 0 and depth_round == 0:
                        parts.append(''.join(cur).strip())
                        cur = []
                    else:
                        cur.append(ch)

                if cur:
                    parts.append(''.join(cur).strip())

                return [p for p in parts if p != '']

            # 解析每一行
            for line_num, raw_line in enumerate(lines, 1):
                line = raw_line.strip()

                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue

                parts = split_fields(line)

                # 现在最少需要文件(或列表) 和 一个时间点 => 至少2个字段
                if len(parts) < 2:
                    logger.warning(f"第{line_num}行格式错误，至少需要文件和时间: {line}")
                    continue

                # 可选：行首是周几 (1-7) 列表，例如 (1,5,7)
                days = None
                idx = 0
                if parts[0].startswith('(') and ')' in parts[0]:
                    m = re.match(r'^\(([^)]+)\)\s*(.*)$', parts[0])
                    if m:
                        days_raw = m.group(1)
                        rest = m.group(2).strip()
                        # days_raw 可能包含逗号分隔的数字
                        try:
                            days = [int(d.strip()) for d in days_raw.split(',') if d.strip()]
                        except ValueError:
                            logger.warning(f"第{line_num}行: 周几字段解析错误: {parts[0]}")
                            days = None

                        if rest:
                            # 例如 (1,2)[a.mp3, b.mp3] 连在一起的情况
                            parts[0] = rest
                        else:
                            # 跳到下一个字段作为文件字段
                            idx = 1

                # 如果第一项仍是括号外的周几（独立字段）
                if idx == 0 and parts[0].startswith('(') and parts[0].endswith(')'):
                    days_raw = parts[0][1:-1]
                    try:
                        days = [int(d.strip()) for d in days_raw.split(',') if d.strip()]
                        idx = 1
                    except ValueError:
                        logger.warning(f"第{line_num}行: 周几字段解析错误: {parts[0]}")
                        days = None

                # 解析文件字段（单个文件或方括号列表）
                file_field = parts[idx]
                filenames: List[str] = []
                if file_field.startswith('[') and file_field.endswith(']'):
                    inner = file_field[1:-1]
                    # 允许方括号内用逗号分隔
                    filenames = [fn.strip() for fn in inner.split(',') if fn.strip()]
                else:
                    filenames = [file_field]

                idx += 1

                # 向后兼容：如果下一字段是持续时间（MM:SS），并且之后还有时间点，则当作旧格式
                duration = 0
                if idx < len(parts) and re.match(r'^\d{1,2}:\d{2}$', parts[idx]) and (idx + 1) < len(parts):
                    dur = self.parse_duration(parts[idx])
                    if dur is None:
                        logger.warning(f"第{line_num}行: 持续时间解析失败: {parts[idx]}")
                        continue
                    duration = dur
                    idx += 1

                # 解析时间点（剩下的字段）
                times = []
                for time_str in parts[idx:]:
                    if not time_str:
                        continue
                    # disabled 标记以 - 开头
                    disabled = time_str.strip().startswith('-')
                    # 去掉前导的 - 便于解析
                    check_str = time_str.strip()[1:].strip() if disabled else time_str.strip()
                    time_point = self.parse_time(check_str)
                    if time_point is not None:
                        times.append({'time': time_point, 'disabled': disabled})

                if not times:
                    logger.warning(f"第{line_num}行: 没有有效的时间点")
                    continue

                # 检查文件是否存在（如果文件不存在只发警告）
                for fn in filenames:
                    if not os.path.exists(fn):
                        logger.warning(f"第{line_num}行: 音频文件不存在: {fn}")

                # 添加到条目列表，统一使用 filenames 列表
                self.bell_entries.append({
                    'filenames': filenames,
                    'duration': duration,
                    'times': times,
                    'days': days,  # None 表示每天
                    'line_num': line_num
                })
            
            logger.info(f"成功加载 {len(self.bell_entries)} 个铃声配置")
            return True
            
        except Exception as e:
            logger.error(f"加载配置文件时发生错误: {e}")
            return False
    
    def should_play_now(self) -> Optional[Dict]:
        """
        检查当前时间是否有需要播放的铃声
        返回需要播放的铃声配置，如果没有则返回None
        """
        now = datetime.datetime.now()
        current_time = (now.hour, now.minute)
        
        today = datetime.datetime.now().isoweekday()  # 1=Mon .. 7=Sun
        for entry in self.bell_entries:
            # 检查周几限制
            if entry.get('days') is not None:
                if today not in entry['days']:
                    continue

            for time_info in entry['times']:
                if time_info['time'] == current_time and not time_info['disabled']:
                    return entry
        
        return None
    
    def play_audio(self, filename: str, duration: int):
        """
        播放音频文件
        """
        if not self.pygame_initialized:
            logger.error("音频系统未初始化，无法播放")
            return
        
        try:
            # 停止当前播放
            self.stop_audio()
            
            # 确定文件路径
            file_path = Path(filename)
            if not file_path.is_absolute():
                # 假设 music 目录在项目根目录下的 music 子目录
                # config_file 应该是 absolute path
                project_root = Path(self.config_file).parent.parent
                media_dir = project_root / 'music'
                potential_path = media_dir / filename
                if potential_path.exists():
                    file_path = potential_path
            
            # 检查文件是否存在
            if not file_path.exists():
                logger.error(f"音频文件不存在: {file_path}")
                return
            
            logger.info(f"开始播放: {file_path}")
            self.current_playing = str(file_path)
            
            # 加载并播放音频
            pygame.mixer.music.load(str(file_path))
            pygame.mixer.music.play()
            
            # 设置定时停止（如果指定了持续时间）
            if duration > 0:
                def stop_after_delay():
                    time.sleep(duration)
                    if self.current_playing == str(file_path):  # 确保还是同一个文件
                        self.stop_audio()
                
                stop_thread = threading.Thread(target=stop_after_delay)
                stop_thread.daemon = True
                stop_thread.start()
                
        except Exception as e:
            logger.error(f"播放音频时发生错误: {e}")
            self.current_playing = None
    
    def stop_audio(self):
        """停止当前播放的音频"""
        if self.pygame_initialized and pygame.mixer.music.get_busy():
            try:
                pygame.mixer.music.stop()
                if self.current_playing:
                    logger.info(f"停止播放: {self.current_playing}")
                self.current_playing = None
            except Exception as e:
                logger.error(f"停止音频时发生错误: {e}")
    
    def run(self):
        """主运行循环"""
        logger.info("铃声调度器开始运行")
        
        last_checked_minute = -1
        
        try:
            while not self.stop_event.is_set():
                now = datetime.datetime.now()
                
                # 每分钟检查一次（避免重复检查同一分钟）
                if now.minute != last_checked_minute:
                    last_checked_minute = now.minute
                    
                    # 重新加载配置（如果文件有修改）
                    self.load_config()
                    
                    # 检查是否需要播放铃声
                    bell_to_play = self.should_play_now()
                    if bell_to_play:
                        # 从 filenames 列表中随机选择一个文件
                        chosen = random.choice(bell_to_play.get('filenames', []))
                        logger.info(f"触发播放: {chosen} (第{bell_to_play['line_num']}行)")
                        self.play_audio(chosen, bell_to_play.get('duration', 0))
                
                # 等待一段时间再检查
                self.stop_event.wait(10)  # 每10秒检查一次停止事件
                
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在退出...")
        except Exception as e:
            logger.error(f"主循环发生错误: {e}")
        finally:
            self.stop_audio()
            if self.pygame_initialized:
                pygame.mixer.quit()
            logger.info("铃声调度器已停止")
    
    def shutdown(self):
        """停止调度器"""
        self.stop_event.set()

def create_sample_config():
    """创建示例配置文件"""
    sample_content = """# 新铃声配置文件格式:
# 支持行首可选的周几，例如 (1,5,7) 表示周一、周五和周日播放（1=周一,7=周日）
# 音频文件可以是单个文件或方括号内的列表，方括号内逗号分隔表示随机选择一首播放
# 旧格式向后兼容：如果第二字段是持续时长 MM:SS 且后面还有时间点，将被当作持续时长
# 时间前加 - 表示禁用该时间点

# 示例用法:
# (1,5,7) [class_bell.mp3, class_bell_alt.mp3], 08:00, 12:00
# [break_bell.mp3], 10:00
# bed_up_bell.mp3, 07:50
# 3.mp3, 00:45, -08:30, 15:00  # 兼容旧格式：持续30秒，08:30 被禁用
"""
    
    with open('bells.conf', 'w', encoding='utf-8') as f:
        f.write(sample_content)
    print("已创建示例配置文件: bells.conf")

def main():
    # 默认配置文件路径：../config/bells.conf
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_config = os.path.join(base_dir, 'config', 'bells.conf')

    parser = argparse.ArgumentParser(description='铃声播放调度器')
    parser.add_argument('config', nargs='?', default=default_config,
                       help=f'配置文件路径 (默认: {default_config})')
    parser.add_argument('--create-sample', action='store_true',
                       help='创建示例配置文件并退出')
    
    args = parser.parse_args()
    
    if args.create_sample:
        create_sample_config()
        return
    
    # 检查配置文件是否存在
    if not os.path.exists(args.config):
        print(f"配置文件不存在: {args.config}")
        print("使用 --create-sample 参数创建示例配置文件")
        return
    
    # 创建调度器并运行
    scheduler = BellScheduler(args.config)
    
    try:
        scheduler.run()
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
    finally:
        scheduler.shutdown()

if __name__ == "__main__":
    main()