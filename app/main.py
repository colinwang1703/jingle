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
    sample_content = """{
  "version": "v1",
  "collections": {
    "class_bells": [
      "class_bell.mp3",
      "class_bell_alt.mp3"
    ]
  },
  "presets": {
    "every_hour": {
      "mode": "all_day",
      "days": [],
      "start": "08:00",
      "end": "18:00",
      "interval_minutes": 60
    }
  },
  "entries": [
    {
      "preset": "every_hour",
      "days": [],
      "times": [],
      "sources": [
        "@class_bells"
      ]
    }
  ]
}
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
