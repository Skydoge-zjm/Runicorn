#!/usr/bin/env bash
set -euo pipefail

# Simple Linux dev helper: start viewer backend and Vite frontend.
# Usage:
#   BACKEND_PORT=8000 FRONTEND_PORT=5173 ./run_dev.sh
# Requires: python3, pip, node, npm

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-5173}

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# --- Backend ---
export PYTHONUTF8=1
export PYTHONIOENCODING='utf-8:backslashreplace'
python3 -m pip install -r "$ROOT_DIR/web/backend/requirements.txt"
# Ensure src-based imports
export PYTHONPATH="$ROOT_DIR/src:${PYTHONPATH:-}"
(
  cd "$ROOT_DIR"
  exec python3 -X utf8 -m uvicorn runicorn.viewer:create_app --factory --host 127.0.0.1 --port "$BACKEND_PORT" --reload
) &
BACKEND_PID=$!

echo "[run_dev.sh] Backend PID=$BACKEND_PID at http://127.0.0.1:$BACKEND_PORT"

# Wait a bit for backend to start
sleep 2

# --- Frontend ---
(
  cd "$ROOT_DIR/web/frontend"
  if [[ ! -d node_modules ]]; then
    npm install
  fi
  exec npm run dev -- --port "$FRONTEND_PORT" --host 127.0.0.1
) &
FRONTEND_PID=$!

echo "[run_dev.sh] Frontend PID=$FRONTEND_PID at http://127.0.0.1:$FRONTEND_PORT"

echo "[run_dev.sh] Press Ctrl+C to stop both."
wait
