# Web Layer

This `web/` directory contains the polished web UI for Runicorn.
- Backend: Read-only FastAPI viewer, see `src/runicorn/viewer.py`.
- Frontend: React + Vite + Ant Design + ECharts, see `web/frontend/`.

## What's New (0.2.0)

- Per-user storage root with project/name hierarchy.
- Project/Name filters on the runs list page.
- Compare multiple runs from the same experiment on a single chart (overlay).

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

## Per-user Storage Root (CLI)

Set once and reuse across projects:

```powershell
runicorn config --set-user-root "E:\\RunicornData"
runicorn config --show
```

Storage resolution precedence:
1. `runicorn.init(storage=...)`
2. Env `RUNICORN_DIR`
3. Per-user config `user_root_dir`
4. Local `./.runicorn`

## Notes
- Default storage root is the per-user folder if configured; otherwise falls back to `./.runicorn`.
- New hierarchy (0.2.0+): `user_root_dir/<project>/<name>/runs/<run_id>/...`.
- Legacy layout `./.runicorn/runs/<run_id>/` is still supported by the viewer.
- UI is read-only: no train start/stop actions from the web.
