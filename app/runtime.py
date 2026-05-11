#!/usr/bin/env python3
import argparse

from app.main import main as scheduler_main
from app.web import app


def main():
    parser = argparse.ArgumentParser(description="Jingle runtime launcher")
    parser.add_argument(
        "process",
        choices=["scheduler", "config-web"],
        help="启动的独立进程类型",
    )
    parser.add_argument("--host", default="0.0.0.0", help="web host")
    parser.add_argument("--port", type=int, default=5000, help="web port")
    args = parser.parse_args()

    if args.process == "scheduler":
        scheduler_main()
    else:
        app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
