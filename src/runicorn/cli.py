from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

import uvicorn

from .viewer import create_app
from .config import get_config_file_path, load_user_config, set_user_root_dir


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="runicorn", description="Runicorn CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_viewer = sub.add_parser("viewer", help="Start the local read-only viewer API")
    p_viewer.add_argument("--storage", default=os.environ.get("RUNICORN_DIR") or None, help="Storage root directory; if omitted, uses global config or legacy ./.runicorn")
    p_viewer.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    p_viewer.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    p_viewer.add_argument("--reload", action="store_true", help="Enable auto-reload (dev only)")

    p_cfg = sub.add_parser("config", help="Manage Runicorn user configuration")
    p_cfg.add_argument("--show", action="store_true", help="Show current configuration")
    p_cfg.add_argument("--set-user-root", dest="user_root", help="Set the per-user root directory for all projects")

    args = parser.parse_args(argv)

    if args.cmd == "viewer":
        # uvicorn can serve factory via --factory style; do it programmatically here
        app = lambda: create_app(storage=args.storage)  # noqa: E731
        uvicorn.run(app, host=args.host, port=args.port, reload=bool(args.reload), factory=True)
        return 0

    if args.cmd == "config":
        did = False
        if getattr(args, "user_root", None):
            p = set_user_root_dir(args.user_root)
            print(f"Set user_root_dir to: {p}")
            did = True
        if getattr(args, "show", False) or not did:
            cfg_file = get_config_file_path()
            cfg = load_user_config()
            print("Runicorn user config:")
            print(f"  File          : {cfg_file}")
            print(f"  user_root_dir : {cfg.get('user_root_dir') or '(not set)'}")
            if not cfg.get('user_root_dir'):
                print("\nTip: Set it via:\n  runicorn config --set-user-root <ABSOLUTE_PATH>")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
