#!/usr/bin/env python3
"""
铃声播放系统入口点
"""

import logging
import argparse
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.scheduler import BellScheduler
from app.settings import CONFIG_FILE, LOG_FILE

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
    parser = argparse.ArgumentParser(description='铃声播放调度器')
    parser.add_argument('config', nargs='?', default=str(CONFIG_FILE),
                       help=f'配置文件路径 (默认: {CONFIG_FILE})')
    parser.add_argument('--create-sample', action='store_true',
                       help='创建示例配置文件并退出')
    
    args = parser.parse_args()
    
    if args.create_sample:
        create_sample_config()
        return
    
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {config_path}")
        print("使用 --create-sample 参数创建示例配置文件")
        return
    
    # 创建调度器并运行
    scheduler = BellScheduler(config_path)
    scheduler.run()

if __name__ == "__main__":
    main()
