#!/usr/bin/env python3
"""
Start Remote Viewer in Remote Mode

Simulates starting a remote viewer on WSL server.
"""
import os
import sys
import subprocess
from pathlib import Path


def start_remote_viewer(
    root_dir: str = "~/runicorn_test_data",
    port: int = 8080,
    host: str = "127.0.0.1"
):
    """Start remote viewer in remote mode."""
    root = Path(root_dir).expanduser()
    
    if not root.exists():
        print(f"❌ Error: Data directory not found: {root}")
        print(f"Run 'python tests/server/setup_test_data.py' first")
        sys.exit(1)
    
    print(f"🚀 Starting Remote Viewer")
    print(f"   Root: {root}")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Mode: Remote")
    print()
    
    # Start viewer
    cmd = [
        sys.executable,
        "-m", "runicorn", "viewer",
        "--storage", str(root),
        "--host", host,
        "--port", str(port),
        "--remote-mode",
        "--log-level", "INFO"
    ]
    
    print(f"Command: {' '.join(cmd)}")
    print(f"\n{'='*60}")
    print(f"Remote Viewer starting on {host}:{port}")
    print(f"Press Ctrl+C to stop")
    print(f"{'='*60}\n")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\n✋ Remote Viewer stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Start Remote Viewer in remote mode")
    parser.add_argument(
        "--root",
        default="~/runicorn_test_data",
        help="Root directory (default: ~/runicorn_test_data)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind (default: 8080)"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind (default: 127.0.0.1)"
    )
    
    args = parser.parse_args()
    start_remote_viewer(args.root, args.port, args.host)
