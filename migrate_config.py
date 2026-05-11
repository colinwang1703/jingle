#!/usr/bin/env python3
import argparse
from pathlib import Path

from app.core.versioned_config import VersionedConfigStore
from app.settings import CONFIG_FILE, MEDIA_DIR


def main():
    parser = argparse.ArgumentParser(description="将 legacy bells.conf 迁移到 v1 JSON 配置")
    parser.add_argument(
        "-c",
        "--config",
        default=str(CONFIG_FILE),
        help=f"配置文件路径 (默认: {CONFIG_FILE})",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="不创建 .legacy.bak 备份",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    store = VersionedConfigStore(config_path, MEDIA_DIR)
    payload = store.migrate_legacy_config(create_backup=not args.no_backup)
    print(f"迁移完成: {config_path}")
    print(f"version: {payload.get('version')}")
    print(f"entries: {len(payload.get('entries', []))}")
    if not args.no_backup:
        print(f"backup: {config_path.with_suffix('.legacy.bak')}")


if __name__ == "__main__":
    main()
