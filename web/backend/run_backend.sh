#!/usr/bin/env bash
set -euo pipefail

# Simple script to run the read-only viewer backend for development on Linux.
# Usage: PORT=8000 ./run_backend.sh

PORT=${PORT:-8000}
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)

export PYTHONUTF8=1
export PYTHONIOENCODING='utf-8:backslashreplace'
python3 -m pip install -r "$SCRIPT_DIR/requirements.txt"
export PYTHONPATH="$ROOT_DIR/src:${PYTHONPATH:-}"
cd "$ROOT_DIR"
exec python3 -X utf8 -m uvicorn runicorn.viewer:create_app --factory --reload --host 127.0.0.1 --port "$PORT"
