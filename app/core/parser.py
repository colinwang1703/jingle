import os
import re
import glob
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class BellParser:
    """
    配置解析器类
    负责解析 bells.conf 配置文件，将其转换为结构化的数据。
    """
    def __init__(self, config_file: Path, media_dir: Path):
        self.config_file = config_file
        self.media_dir = media_dir

    def parse(self) -> List[Dict]:
        """
        解析配置文件，返回结构化的铃声条目列表
        :return: 包含铃声配置的字典列表
        """
        if not self.config_file.exists():
            logger.error(f"配置文件不存在: {self.config_file}")
            return []

        entries = []
        with open(self.config_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line_num, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue

            try:
                entry = self._parse_line(line, line_num)
                if entry:
                    entries.append(entry)
            except Exception as e:
                logger.error(f"第{line_num}行解析错误: {e}")

        return entries

    def _parse_line(self, line: str, line_num: int) -> Optional[Dict]:
        """解析单行配置"""
        parts = self._split_fields(line)
        if len(parts) < 2:
            logger.warning(f"第{line_num}行格式错误，至少需要文件和时间: {line}")
            return None

        days = None
        idx = 0
        
        # 解析周几
        # Case 1: (1,2) [files]...
        if parts[0].startswith('(') and ')' in parts[0]:
            m = re.match(r'^\(([^)]+)\)\s*(.*)$', parts[0])
            if m:
                days_raw = m.group(1)
                rest = m.group(2).strip()
                try:
                    days = [int(d.strip()) for d in days_raw.split(',') if d.strip()]
                except ValueError:
                    logger.warning(f"第{line_num}行: 周几字段解析错误: {parts[0]}")
                    return None

                if rest:
                    parts[0] = rest
                else:
                    idx = 1

        # Case 2: (1,2), [files]... (separated by comma)
        if idx == 0 and parts[0].startswith('(') and parts[0].endswith(')'):
            days_raw = parts[0][1:-1]
            try:
                days = [int(d.strip()) for d in days_raw.split(',') if d.strip()]
                idx = 1
            except ValueError:
                logger.warning(f"第{line_num}行: 周几字段解析错误: {parts[0]}")
                return None

        # 解析文件名
        file_field = parts[idx]
        filenames = self._resolve_filenames(file_field, line_num)
        if not filenames:
             return None
        
        idx += 1

        # 解析持续时间 (可选)
        duration = 0
        if idx < len(parts) and re.match(r'^\d{1,2}:\d{2}$', parts[idx]) and (idx + 1) < len(parts):
            dur = self._parse_duration(parts[idx])
            if dur is not None:
                duration = dur
                idx += 1
            else:
                logger.warning(f"第{line_num}行: 持续时间解析失败: {parts[idx]}")

        # 解析时间点
        times = []
        for time_str in parts[idx:]:
            if not time_str: continue
            disabled = time_str.strip().startswith('-')
            check_str = time_str.strip()[1:].strip() if disabled else time_str.strip()
            
            time_point = self._parse_time(check_str)
            if time_point:
                times.append({'time': time_point, 'disabled': disabled})
            else:
                 logger.warning(f"第{line_num}行: 时间格式错误 {time_str}")

        if not times:
            logger.warning(f"第{line_num}行: 没有有效的时间点")
            return None

        return {
            'filenames': filenames,
            'duration': duration,
            'times': times,
            'days': days,
            'line_num': line_num
        }

    def _resolve_filenames(self, file_field: str, line_num: int) -> List[str]:
        """解析并展开文件名（支持列表和通配符）"""
        raw_filenames = []
        if file_field.startswith('[') and file_field.endswith(']'):
            inner = file_field[1:-1]
            raw_filenames = [fn.strip() for fn in inner.split(',') if fn.strip()]
        else:
            raw_filenames = [file_field]

        filenames = []
        for fn in raw_filenames:
            if '*' in fn or '?' in fn:
                try:
                    pattern = str(self.media_dir / fn)
                    matched_paths = glob.glob(pattern)
                    if matched_paths:
                        for p in matched_paths:
                            filenames.append(os.path.basename(p))
                    else:
                        logger.warning(f"第{line_num}行: 通配符未匹配到任何文件: {fn}")
                        filenames.append(fn)
                except Exception as e:
                    logger.warning(f"第{line_num}行: 通配符解析错误 {fn}: {e}")
                    filenames.append(fn)
            else:
                filenames.append(fn)

        # 检查文件存在性 (去重)
        final_filenames = list(set(filenames))
        for fn in final_filenames:
             if not (self.media_dir / fn).exists() and not Path(fn).exists():
                 logger.warning(f"第{line_num}行: 音频文件不存在: {fn}")
        
        return final_filenames

    def _split_fields(self, line: str) -> List[str]:
        """按逗号分割字段，但忽略括号内的逗号"""
        parts = []
        cur = []
        depth_square = 0
        depth_round = 0
        for ch in line:
            if ch == '[': depth_square += 1
            elif ch == ']': depth_square = max(0, depth_square - 1)
            elif ch == '(': depth_round += 1
            elif ch == ')': depth_round = max(0, depth_round - 1)

            if ch == ',' and depth_square == 0 and depth_round == 0:
                parts.append(''.join(cur).strip())
                cur = []
            else:
                cur.append(ch)
        if cur: parts.append(''.join(cur).strip())
        return [p for p in parts if p != '']

    def _parse_time(self, time_str: str) -> Optional[Tuple[int, int]]:
        """解析时间 HH:MM"""
        match = re.match(r'^(\d{1,2}):(\d{2})$', time_str)
        if match:
            h, m = int(match.group(1)), int(match.group(2))
            if 0 <= h <= 23 and 0 <= m <= 59:
                return (h, m)
        return None

    def _parse_duration(self, duration_str: str) -> Optional[int]:
        """解析持续时间 MM:SS -> 秒"""
        match = re.match(r'^(\d{1,2}):(\d{2})$', duration_str)
        if match:
            m, s = int(match.group(1)), int(match.group(2))
            return m * 60 + s
        return None
