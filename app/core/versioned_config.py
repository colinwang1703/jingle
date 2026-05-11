import glob
import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.core.parser import BellParser

SUPPORTED_VERSION = "v1"


class ConfigError(ValueError):
    pass


def default_config_payload() -> Dict:
    return {
        "version": SUPPORTED_VERSION,
        "collections": {},
        "presets": {},
        "entries": [],
    }


class VersionedConfigStore:
    def __init__(self, config_file: Path, media_dir: Path):
        self.config_file = Path(config_file)
        self.media_dir = Path(media_dir)

    def load_payload(self) -> Dict:
        if not self.config_file.exists():
            raise ConfigError(f"配置文件不存在: {self.config_file}")
        with open(self.config_file, "r", encoding="utf-8") as f:
            content = f.read()
        return self.parse_payload(content)

    def parse_payload(self, content: str) -> Dict:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ConfigError(
                "配置必须为带版本标记的 JSON 格式，请先迁移为 v1。"
            ) from exc
        normalized = self._normalize_payload(payload)
        errors, _, _ = self.validate_payload(normalized, strict=False)
        if errors:
            raise ConfigError("; ".join(errors))
        return normalized

    def save_payload(self, payload: Dict):
        normalized = self._normalize_payload(payload)
        errors, _, _ = self.validate_payload(normalized, strict=False)
        if errors:
            raise ConfigError("; ".join(errors))
        content = json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True)
        tmp_file = self.config_file.with_suffix(".tmp")
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(content + "\n")
        os.replace(tmp_file, self.config_file)

    def validate_payload(self, payload: Dict, strict: bool = False):
        errors: List[str] = []
        warnings: List[str] = []
        preview: Dict[str, List[str]] = {str(day): [] for day in range(1, 8)}

        if payload.get("version") != SUPPORTED_VERSION:
            errors.append(f"仅支持配置版本 {SUPPORTED_VERSION}")
            return errors, warnings, preview

        collections = payload.get("collections", {})
        presets = payload.get("presets", {})
        entries = payload.get("entries", [])

        expanded_collections: Dict[str, List[str]] = {}
        for name, sources in collections.items():
            expanded = self._resolve_sources(sources, collections, strict, warnings, f"收藏集 {name}")
            if not expanded:
                msg = f"收藏集 {name} 没有可用音乐源"
                if strict:
                    errors.append(msg)
                else:
                    warnings.append(msg)
            expanded_collections[name] = expanded

        for idx, entry in enumerate(entries, 1):
            line_label = f"条目#{idx}"
            preset_name = entry.get("preset")
            preset = None
            if preset_name:
                preset = presets.get(preset_name)
                if preset is None:
                    errors.append(f"{line_label} 引用了不存在的预设: {preset_name}")
                    continue

            days = self._entry_days(entry, preset)
            try:
                self._validate_days(days)
            except ConfigError as exc:
                errors.append(f"{line_label}: {exc}")
                continue

            time_tokens = self._entry_times(entry, preset)
            if not time_tokens:
                errors.append(f"{line_label} 缺少时间配置（直接时间或预设）")
                continue

            parsed_times = []
            for token in time_tokens:
                try:
                    parsed_times.extend(self._expand_time_token(token, preset))
                except ConfigError as exc:
                    errors.append(f"{line_label}: {exc}")

            sources = entry.get("sources", [])
            if not isinstance(sources, list) or len(sources) == 0:
                errors.append(f"{line_label} 缺少 sources")
                continue
            resolved_files = self._resolve_sources(
                sources,
                collections,
                strict,
                warnings,
                line_label,
                expanded_collections=expanded_collections,
            )
            if not resolved_files:
                msg = f"{line_label} 没有可播放的音乐文件"
                if strict:
                    errors.append(msg)
                else:
                    warnings.append(msg)
                continue

            if not errors:
                for t in parsed_times:
                    if t["disabled"]:
                        continue
                    hh, mm = t["time"]
                    if t.get("is_range"):
                        preview_token = f"{hh:02d}:{mm:02d}-{self._range_end_text(t)}"
                    else:
                        preview_token = f"{hh:02d}:{mm:02d}"
                    for day in self._days_to_iter(days):
                        preview[str(day)].append(preview_token)

        for day in preview:
            preview[day] = sorted(set(preview[day]))
        return errors, warnings, preview

    def load_runtime_entries(self, strict: bool = False) -> List[Dict]:
        payload = self.load_payload()
        errors, warnings, _ = self.validate_payload(payload, strict=strict)
        if errors:
            raise ConfigError("; ".join(errors))

        runtime_entries: List[Dict] = []
        collections = payload.get("collections", {})
        presets = payload.get("presets", {})
        for idx, entry in enumerate(payload.get("entries", []), 1):
            preset = presets.get(entry.get("preset")) if entry.get("preset") else None
            parsed_times = []
            for token in self._entry_times(entry, preset):
                parsed_times.extend(self._expand_time_token(token, preset))
            resolved_files = self._resolve_sources(
                entry.get("sources", []),
                collections,
                strict=False,
                warnings=warnings,
                context=f"条目#{idx}",
            )
            runtime_entries.append(
                {
                    "filenames": resolved_files,
                    "duration": 0,
                    "times": parsed_times,
                    "days": self._entry_days(entry, preset),
                    "line_num": idx,
                }
            )
        return runtime_entries

    def migrate_legacy_config(self, create_backup: bool = True) -> Dict:
        parser = BellParser(self.config_file, self.media_dir)
        legacy_entries = parser.parse()
        payload = default_config_payload()
        for entry in legacy_entries:
            payload["entries"].append(
                {
                    "preset": "",
                    "days": entry.get("days") or [],
                    "times": [self._time_info_to_token(t) for t in entry.get("times", [])],
                    "sources": list(entry.get("filenames", [])),
                }
            )

        if create_backup:
            backup = self.config_file.with_suffix(".legacy.bak")
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as src:
                    legacy_content = src.read()
                with open(backup, "w", encoding="utf-8") as dst:
                    dst.write(legacy_content)

        self.save_payload(payload)
        return payload

    def _normalize_payload(self, payload: Dict) -> Dict:
        if not isinstance(payload, dict):
            raise ConfigError("配置根节点必须是对象")
        normalized = deepcopy(payload)
        if "version" not in normalized:
            raise ConfigError("配置缺少 version 字段")
        if normalized["version"] != SUPPORTED_VERSION:
            raise ConfigError(f"仅支持配置版本 {SUPPORTED_VERSION}")
        normalized.setdefault("collections", {})
        normalized.setdefault("presets", {})
        normalized.setdefault("entries", [])
        if not isinstance(normalized["collections"], dict):
            raise ConfigError("collections 必须是对象")
        if not isinstance(normalized["presets"], dict):
            raise ConfigError("presets 必须是对象")
        if not isinstance(normalized["entries"], list):
            raise ConfigError("entries 必须是数组")
        return normalized

    def _entry_days(self, entry: Dict, preset: Optional[Dict]) -> Optional[List[int]]:
        if isinstance(entry.get("days"), list) and len(entry["days"]) > 0:
            return sorted(set(int(d) for d in entry["days"]))
        if preset and isinstance(preset.get("days"), list) and len(preset["days"]) > 0:
            return sorted(set(int(d) for d in preset["days"]))
        return None

    def _entry_times(self, entry: Dict, preset: Optional[Dict]) -> List[str]:
        times = entry.get("times", [])
        if isinstance(times, list) and len(times) > 0:
            return [str(t).strip() for t in times if str(t).strip()]
        if preset:
            mode = preset.get("mode", "times")
            if mode == "times":
                return [str(t).strip() for t in preset.get("times", []) if str(t).strip()]
            if mode == "all_day":
                return ["@all_day"]
        return []

    def _resolve_sources(
        self,
        sources: List[str],
        collections: Dict[str, List[str]],
        strict: bool,
        warnings: List[str],
        context: str,
        expanded_collections: Optional[Dict[str, List[str]]] = None,
    ) -> List[str]:
        resolved: List[str] = []
        for source in sources:
            if not isinstance(source, str):
                continue
            token = source.strip()
            if not token:
                continue
            if token.startswith("@"):
                collection_name = token[1:]
                if expanded_collections and collection_name in expanded_collections:
                    coll_files = expanded_collections[collection_name]
                else:
                    coll_sources = collections.get(collection_name)
                    if coll_sources is None:
                        msg = f"{context} 引用了不存在的收藏集: {collection_name}"
                        if strict:
                            raise ConfigError(msg)
                        warnings.append(msg)
                        continue
                    coll_files = self._resolve_sources(coll_sources, collections, strict, warnings, f"收藏集 {collection_name}")
                resolved.extend(coll_files)
                continue

            if "*" in token or "?" in token:
                matched = glob.glob(str(self.media_dir / token))
                if matched:
                    resolved.extend([Path(p).name for p in matched])
                else:
                    warnings.append(f"{context} 通配符未匹配到文件: {token}")
                continue

            path = self.media_dir / token
            if not path.exists():
                warnings.append(f"{context} 文件不存在: {token}")
            resolved.append(token)
        # keep order, remove duplicates
        uniq = []
        seen = set()
        for item in resolved:
            if item not in seen:
                uniq.append(item)
                seen.add(item)
        return uniq

    def _expand_time_token(self, token: str, preset: Optional[Dict]) -> List[Dict]:
        token = str(token).strip()
        if not token:
            return []
        disabled = token.startswith("-")
        core = token[1:].strip() if disabled else token
        if core == "@all_day":
            if not preset or preset.get("mode") != "all_day":
                raise ConfigError("@all_day 只能在 all_day 预设中使用")
            return self._build_all_day_times(preset)

        m = re.match(r"^(\d{1,2}:\d{2})-(\d{1,2}:\d{2})$", core)
        if m:
            start = self._parse_clock(m.group(1))
            end = self._parse_clock(m.group(2))
            start_min = start[0] * 60 + start[1]
            end_min = end[0] * 60 + end[1]
            if end_min < start_min:
                end_min += 24 * 60
            return [
                {
                    "time": start,
                    "disabled": disabled,
                    "duration": (end_min - start_min) * 60,
                    "is_range": True,
                }
            ]

        point = self._parse_clock(core)
        return [{"time": point, "disabled": disabled, "duration": None, "is_range": False}]

    def _build_all_day_times(self, preset: Dict) -> List[Dict]:
        interval = int(preset.get("interval_minutes", 60))
        if interval <= 0 or interval > 24 * 60:
            raise ConfigError("all_day.interval_minutes 必须在 1-1440")
        start = self._parse_clock(str(preset.get("start", "00:00")))
        end = self._parse_clock(str(preset.get("end", "23:59")))
        start_min = start[0] * 60 + start[1]
        end_min = end[0] * 60 + end[1]
        if end_min < start_min:
            end_min += 24 * 60

        times = []
        current = start_min
        while current <= end_min:
            h = (current // 60) % 24
            m = current % 60
            times.append({"time": (h, m), "disabled": False, "duration": None, "is_range": False})
            current += interval
        return times

    def _parse_clock(self, value: str) -> Tuple[int, int]:
        m = re.match(r"^(\d{1,2}):(\d{2})$", value.strip())
        if not m:
            raise ConfigError(f"非法时间格式: {value}")
        h = int(m.group(1))
        minute = int(m.group(2))
        if not (0 <= h <= 23 and 0 <= minute <= 59):
            raise ConfigError(f"时间超出范围: {value}")
        return h, minute

    def _validate_days(self, days: Optional[List[int]]):
        if days is None:
            return
        for d in days:
            if int(d) < 1 or int(d) > 7:
                raise ConfigError(f"非法星期值: {d}")

    def _days_to_iter(self, days: Optional[List[int]]):
        if days is None:
            return range(1, 8)
        return days

    def _range_end_text(self, time_info: Dict) -> str:
        start_h, start_m = time_info["time"]
        duration = int(time_info.get("duration") or 0)
        end_total = (start_h * 60 + start_m + duration // 60) % (24 * 60)
        return f"{end_total // 60:02d}:{end_total % 60:02d}"

    def _time_info_to_token(self, time_info: Dict) -> str:
        hh, mm = time_info["time"]
        prefix = "-" if time_info.get("disabled") else ""
        if time_info.get("is_range"):
            end = self._range_end_text(time_info)
            return f"{prefix}{hh:02d}:{mm:02d}-{end}"
        return f"{prefix}{hh:02d}:{mm:02d}"
