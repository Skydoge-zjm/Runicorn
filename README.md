# Runicorn
 
[![PyPI version](https://img.shields.io/pypi/v/runicorn)](https://pypi.org/project/runicorn/)
[![Python Versions](https://img.shields.io/pypi/pyversions/runicorn)](https://pypi.org/project/runicorn/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
 
Local, open-source experiment tracking and visualization. 100% local. A lightweight, self-hosted alternative to W&B.
 
- Package/Library name: runicorn
- Default storage path: ./.runicorn
- Viewer: read-only, serves metrics/logs/media from local storage
- GPU telemetry: optional panel (reads nvidia-smi if available)
 
Features
--------
- 100% local, self-hosted. No external services. Data stays under `./.runicorn/` by default.
- Read-only viewer built on FastAPI; zero impact on your training loop.
- Prebuilt web UI bundled in wheel; offline-friendly after install.
- Metrics tables for epochs and steps; live logs via WebSocket.
- Optional GPU telemetry panel if `nvidia-smi` is available.
 
Quick start (SDK)
-----------------
```python
import runicorn as rn

run = rn.init(project="demo")
for epoch in range(3):
    rn.log({"epoch": epoch, "train_loss": 1.0/(epoch+1)})
# Or rn.log(key=value, epoch=epoch)

rn.summary(update={"best_val_acc_top1": 77.3})
rn.finish()
```
 
Launch viewer
-------------
```
runicorn viewer --storage ./.runicorn --host 127.0.0.1 --port 8000
```
Open http://127.0.0.1:8000
 
Frontend (dev)
--------------
For local frontend development with live-reload and API proxy:
```
./run_dev.ps1 -PythonExe "python"
```
Then open http://127.0.0.1:5173. The frontend proxies `/api/*` to `http://127.0.0.1:8000`.
 
See `web/README.md` for manual steps.
 
Installation
------------
Requires Python 3.8+.
 
```bash
pip install -U runicorn
# Optional image helpers (Pillow, NumPy, Matplotlib)
pip install -U "runicorn[images]"
```
 
CLI (Viewer)
------------
Start the local, read-only viewer and open the UI:
 
```bash
runicorn viewer --storage ./.runicorn --host 127.0.0.1 --port 8000
# Then open http://127.0.0.1:8000
```
 
Generate a demo run (no server required)
----------------------------------------
```bash
python examples/create_test_run.py --epochs 5 --steps 20 --sleep 0.05
```
This writes a run under `./.runicorn/runs/<run_id>/` which the viewer can display.
 
Configuration
-------------
- Environment variable `RUNICORN_DIR` overrides the default storage root (`./.runicorn`).
- Or pass `--storage` to the CLI or `storage=` to `runicorn.init()`.
- Live logs are tailed from `logs.txt` via WebSocket at `/api/runs/{run_id}/logs/ws`.
 
Troubleshooting
---------------
- UI not loading when running from source: ensure the prebuilt frontend exists at `src/runicorn/webui/` (installed wheels already bundle it). Use `./run_dev.ps1` for dev, or run the publish script to build the frontend before packaging.
- GPU panel not visible: `nvidia-smi` must be available in PATH (Windows paths are auto-detected if installed).
- Empty runs list: first create data with the demo script above or instrument your training with the SDK.
 
Privacy & Offline
------------------
- No telemetry. The viewer only reads local files (JSON/JSONL and media).
- Default storage root is `./.runicorn` (configurable via `RUNICORN_DIR` or `--storage`).
- Bundled UI allows using the viewer without Node.js at runtime.
 
Roadmap
-------
- Compare runs and filter/search.
- Artifact browser and media gallery improvements.
- CSV export and API pagination.
- Optional remote storage adapters (e.g., S3/MinIO) while keeping the viewer read-only.
 
Community
---------
- See `CONTRIBUTING.md` for dev setup, style, and release flow.
- See `SECURITY.md` for private vulnerability reporting.
- See `CHANGELOG.md` for version history.
 
Storage layout
--------------
```
.runicorn/
  runs/
    <run_id>/
      meta.json
      status.json
      summary.json
      events.jsonl
      media/
```

Notes
-----
- GPU telemetry is shown if `nvidia-smi` is available.
- Windows compatible.
