from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

import uvicorn

from .viewer import create_app


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="runicorn", description="Runicorn CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_viewer = sub.add_parser("viewer", help="Start the local read-only viewer API")
    p_viewer.add_argument("--storage", default=os.environ.get("RUNICORN_DIR") or "./.runicorn", help="Storage root directory (default: ./.runicorn)")
    p_viewer.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    p_viewer.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    p_viewer.add_argument("--reload", action="store_true", help="Enable auto-reload (dev only)")

    args = parser.parse_args(argv)

    if args.cmd == "viewer":
        # uvicorn can serve factory via --factory style; do it programmatically here
        app = lambda: create_app(storage=args.storage)  # noqa: E731
        uvicorn.run(app, host=args.host, port=args.port, reload=bool(args.reload), factory=True)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
