import logging
import threading
import time
import pygame
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class BellPlayer:
    """
    音频播放器类
    封装了 Pygame 的音频播放功能，支持播放、停止以及定时停止。
    """
    def __init__(self, media_dir: Path):
        self.media_dir = media_dir
        self.current_playing: Optional[str] = None
        self.pygame_initialized = False
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

    def play(self, filename: str, duration: int = 0, next_track_callback=None):
        """
        播放音频文件
        :param filename: 文件名或绝对路径
        :param duration: 持续时间（秒），0 表示播放完整文件
        :param next_track_callback: 播放结束后调用的回调函数（用于循环播放）
        """
        if not self.pygame_initialized:
            logger.error("音频系统未初始化，无法播放")
            return

        try:
            # 停止当前播放
            self.stop()

            # 确定文件路径
            file_path = Path(filename)
            if not file_path.is_absolute():
                potential_path = self.media_dir / filename
                if potential_path.exists():
                    file_path = potential_path

            # 检查文件是否存在
            if not file_path.exists():
                logger.error(f"音频文件不存在: {file_path}")
                if next_track_callback:
                    next_track_callback()
                return

            logger.info(f"开始播放: {file_path}")
            self.current_playing = str(file_path)

            # 加载并播放音频
            pygame.mixer.music.load(str(file_path))
            pygame.mixer.music.play()
            
            # 设置音乐结束事件
            pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)
            
            # 监听音乐结束事件
            def check_music_end():
                while self.current_playing == str(file_path):
                    for event in pygame.event.get():
                        if event.type == pygame.USEREVENT + 1:
                            if next_track_callback:
                                next_track_callback()
                            return
                    time.sleep(0.1)

            threading.Thread(target=check_music_end, daemon=True).start()

            # 设置定时停止（如果指定了持续时间）
            if duration > 0:
                self._schedule_stop(duration, str(file_path))

        except Exception as e:
            logger.error(f"播放音频时发生错误: {e}")
            self.current_playing = None

    def _schedule_stop(self, duration: int, file_path_str: str):
        """安排在指定时间后停止播放"""
        def stop_after_delay():
            time.sleep(duration)
            if self.current_playing == file_path_str:  # 确保还是同一个文件
                self.stop()

        stop_thread = threading.Thread(target=stop_after_delay)
        stop_thread.daemon = True
        stop_thread.start()

    def stop(self):
        """停止当前播放的音频"""
        if self.pygame_initialized and pygame.mixer.music.get_busy():
            try:
                pygame.mixer.music.stop()
                if self.current_playing:
                    logger.info(f"停止播放: {self.current_playing}")
                self.current_playing = None
            except Exception as e:
                logger.error(f"停止音频时发生错误: {e}")
    
    def is_busy(self) -> bool:
        """检查播放器是否正在忙碌"""
        return self.pygame_initialized and pygame.mixer.music.get_busy()

    def quit(self):
        """退出音频系统，释放资源"""
        self.stop()
        if self.pygame_initialized:
            pygame.mixer.quit()
