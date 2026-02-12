#!/usr/bin/env python3
"""
配置检查与试运行工具
用于检查 bells.conf 的语法错误、时间重叠，以及模拟日程。
"""

import argparse
import sys
import os
import logging
from pathlib import Path
from collections import defaultdict

# 添加当前目录到 sys.path 以便导入 app 模块
sys.path.append(os.getcwd())

try:
    from app.main import BellScheduler
except ImportError as e:
    print(f"错误: 无法导入 app.main。\n详细错误信息: {e}")
    print("提示: 如果使用了 sudo，请确保指向虚拟环境的 python，例如: sudo .venv/bin/python configure.py")
    sys.exit(1)

# 配置日志，避免 app.main 的日志干扰太多，但保留错误信息
# 注意：app.main 导入时已经配置了 logging.basicConfig
# 我们获取 logger 并根据需要调整
scheduler_logger = logging.getLogger('app.main')

def get_day_name(day_idx):
    days = {
        1: "周一 (Monday)",
        2: "周二 (Tuesday)",
        3: "周三 (Wednesday)",
        4: "周四 (Thursday)",
        5: "周五 (Friday)",
        6: "周六 (Saturday)",
        7: "周日 (Sunday)"
    }
    return days.get(day_idx, f"Day {day_idx}")

def check_config(config_path):
    """
    检查配置文件
    1. 语法错误 (通过 load_config)
    2. 时间重叠警告 (< 5分钟)
    """
    print(f"正在检查配置文件: {config_path}")
    
    scheduler = BellScheduler(config_path)
    # load_config 会打印日志，我们暂时不屏蔽，这样用户可以看到具体的解析错误
    success = scheduler.load_config()
    
    if not success:
        print("\n❌ 配置文件加载失败！请检查上述错误日志。")
        return False

    print("✅ 语法检查通过。")
    print("正在检查时间线重叠...")

    # 展开所有事件
    # events format: (day_idx, time_in_minutes, line_num, filenames)
    all_events = []
    
    for entry in scheduler.bell_entries:
        days = entry.get('days')
        if days is None:
            days = range(1, 8) # 1-7
        
        for day in days:
            for time_info in entry['times']:
                if time_info['disabled']:
                    continue
                
                h, m = time_info['time']
                time_in_mins = h * 60 + m
                all_events.append({
                    'day': day,
                    'time_mins': time_in_mins,
                    'time_str': f"{h:02d}:{m:02d}",
                    'line': entry['line_num'],
                    'files': entry['filenames']
                })

    # 按天和时间排序
    all_events.sort(key=lambda x: (x['day'], x['time_mins']))

    warning_count = 0
    
    # 检查重叠
    for i in range(len(all_events) - 1):
        curr = all_events[i]
        next_event = all_events[i+1]
        
        # 只检查同一天的
        if curr['day'] == next_event['day']:
            diff = next_event['time_mins'] - curr['time_mins']
            if diff < 5:
                print(f"⚠️  WARNING: 时间重叠 < 5分钟 ({get_day_name(curr['day'])})")
                print(f"    - {curr['time_str']} (第{curr['line']}行): {curr['files']}")
                print(f"    - {next_event['time_str']} (第{next_event['line']}行): {next_event['files']}")
                print(f"    间隔仅 {diff} 分钟\n")
                warning_count += 1

    if warning_count == 0:
        print("✅ 未发现时间线重叠问题。")
    else:
        print(f"⚠️  发现 {warning_count} 个潜在的时间重叠问题。")
    
    return True

def dry_run(config_path, target_day=None):
    """
    试运行/模拟日程
    """
    scheduler = BellScheduler(config_path)
    # 减少日志输出，只显示结果
    scheduler_logger.setLevel(logging.ERROR)
    
    if not scheduler.load_config():
        print("❌ 配置文件加载失败")
        return

    # 收集事件
    daily_schedule = defaultdict(list)
    
    for entry in scheduler.bell_entries:
        days = entry.get('days')
        if days is None:
            days = range(1, 8)
            
        for day in days:
            # 如果指定了 target_day 且不匹配，则跳过
            if target_day is not None and day != target_day:
                continue
                
            for time_info in entry['times']:
                # 即使是 disabled 的也显示吗？通常 dry-run 显示实际会播放的。
                # 这里只显示启用的
                if time_info['disabled']:
                    continue
                    
                h, m = time_info['time']
                daily_schedule[day].append({
                    'time': f"{h:02d}:{m:02d}",
                    'time_val': h * 60 + m,
                    'files': entry['filenames'],
                    'line': entry['line_num'],
                    'duration': entry.get('duration', 0)
                })

    # 输出
    days_to_show = sorted(daily_schedule.keys())
    if not days_to_show:
        if target_day:
            print(f"📅 {get_day_name(target_day)}: 没有安排任何铃声。")
        else:
            print("📅 整周都没有安排铃声。")
        return

    for day in days_to_show:
        print(f"\n📅 {get_day_name(day)}")
        print("-" * 50)
        events = sorted(daily_schedule[day], key=lambda x: x['time_val'])
        
        for evt in events:
            files_str = ", ".join(evt['files'])
            dur_str = f" (持续 {evt['duration']}秒)" if evt['duration'] > 0 else ""
            print(f"  🕒 {evt['time']} | 🎵 {files_str}{dur_str}")
        print("-" * 50)

def main():
    # 默认配置文件路径
    base_dir = Path(__file__).resolve().parent
    default_config = base_dir / 'config' / 'bells.conf'

    parser = argparse.ArgumentParser(description='Jingle 配置检查与试运行工具')
    parser.add_argument('-c', '--config', default=str(default_config),
                        help=f'配置文件路径 (默认: {default_config})')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-t', '--test', action='store_true',
                       help='检查配置文件语法和时间重叠')
    group.add_argument('-d', '--dry-run', nargs='?', const=0, type=int, metavar='DAY',
                       help='试运行。不带参数运行整周，带数字(1-7)运行指定的一天 (1=周一)')

    args = parser.parse_args()
    
    config_path = Path(args.config).resolve()
    if not config_path.exists():
        print(f"❌ 错误: 配置文件不存在: {config_path}")
        sys.exit(1)

    if args.test:
        check_config(str(config_path))
    
    elif args.dry_run is not None:
        # args.dry_run 是 0 (const) 如果没有提供参数，或者具体的数字
        day = args.dry_run
        if day == 0:
            # 整周
            print(f"🚀 模拟整周日程 (配置文件: {config_path.name})")
            dry_run(str(config_path))
        else:
            if 1 <= day <= 7:
                print(f"🚀 模拟 {get_day_name(day)} 日程 (配置文件: {config_path.name})")
                dry_run(str(config_path), target_day=day)
            else:
                print("❌ 错误: 天数必须在 1-7 之间 (1=周一, 7=周日)")
                sys.exit(1)

if __name__ == "__main__":
    main()
