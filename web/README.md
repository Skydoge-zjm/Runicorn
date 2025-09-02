# Web Layer

This `web/` directory contains the polished web UI for Runicorn.
- Backend: Read-only FastAPI viewer, see `src/runicorn/viewer.py`.
- Frontend: React + Vite + Ant Design + ECharts, see `web/frontend/`.
## Quick Start (Windows PowerShell)

- One-click dev (recommended):
  ```powershell
  ./run_dev.ps1 -PythonExe "E:\Anaconda\envs\pytorch\python.exe"
  ```

- Manual start (equivalent):
  1) Backend deps (in project root):
  ```powershell
  python -m pip install -r web/backend/requirements.txt
  ```
  2) Start read-only viewer backend with UTF-8 enforced:
  ```powershell
  # Option A: via uvicorn factory
  $env:PYTHONPATH = "$PWD/src;$env:PYTHONPATH"
  python -X utf8 -m uvicorn runicorn.viewer:create_app --factory --reload --host 127.0.0.1 --port 8000

  # Option B: via CLI
  python -m runicorn.cli viewer --host 127.0.0.1 --port 8000 --reload
  ```
  3) Frontend deps + start:
  ```powershell
  cd web/frontend
  npm install
  npm run dev -- --host 127.0.0.1 --port 5173
  ```

Open http://127.0.0.1:5173. The frontend proxies `/api/*` to `http://127.0.0.1:8000` during development.

## Notes
- Default storage root is `./.runicorn` (configurable via `RUNICORN_DIR` or `--storage`).
- Each run lives under `.runicorn/runs/<run_id>/` with files: `meta.json`, `status.json`, `summary.json`, `events.jsonl`, `logs.txt`, `media/`.
- UI is read-only: no train start/stop actions from the web.
