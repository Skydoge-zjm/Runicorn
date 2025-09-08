# Runicorn

[English](README.md) | [简体中文](README_zh.md)

[![PyPI version](https://img.shields.io/pypi/v/runicorn)](https://pypi.org/project/runicorn/)
[![Python Versions](https://img.shields.io/pypi/pyversions/runicorn)](https://pypi.org/project/runicorn/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<p align="center">
  <img src="docs/picture/icon.jpg" alt="Runicorn logo" width="120" />
</p>

Local, open-source experiment tracking and visualization. 100% local. A lightweight, self-hosted alternative to W&B.

- Package/Library name: runicorn
- Default storage root: user-level folder (configurable), falls back to `./.runicorn`
- Viewer: read-only, serves metrics/logs/media from local storage
- GPU telemetry: optional panel (reads nvidia-smi if available)

<p align="center">
  <img src="https://github.com/Skydoge-zjm/Runicorn/blob/main/docs/picture/p1.png" alt="Runicorn demo 1" width="49%" />
  <img src="https://github.com/Skydoge-zjm/Runicorn/blob/main/docs/picture/p2.png" alt="Runicorn demo 2" width="49%" />
  <br/>
  <img src="https://github.com/Skydoge-zjm/Runicorn/blob/main/docs/picture/p3.png" alt="Runicorn demo 3" width="49%" />
  <img src="https://github.com/Skydoge-zjm/Runicorn/blob/main/docs/picture/p4.png" alt="Runicorn demo 4" width="49%" />
  <br/>
  <span style="color:#888; font-size: 12px;">Screenshots of Runicorn UI (Runs list, Run detail, Metrics overlay, GPU panel)</span>
  
</p>

Features
--------
- 100% local, self-hosted. No external services. Data stays under your user-level root by default.
- Read-only viewer built on FastAPI; zero impact on your training loop.
- Prebuilt web UI bundled in wheel; offline-friendly after install.
- Step/time metrics with stage separators; live logs via WebSocket.
- Optional GPU telemetry panel if `nvidia-smi` is available.
- Global per-user storage with project/name hierarchy.
- Compare multiple runs of the same experiment on a single chart (multi-run overlay).


Installation
------------
Requires Windows, Python 3.8+.

```bash
pip install -U runicorn
# Optional image helpers (Pillow, NumPy, Matplotlib)
pip install -U "runicorn[images]"
```

Quick start
-----------------

```python
import runicorn as rn
import math, random

run = rn.init(project="demo", name="exp1")

stages = ["warmup", "train"]
total_steps = 100
seg = max(1, total_steps // len(stages))
for i in range(1, total_steps + 1):
    stage = stages[min((i - 1) // seg, len(stages) - 1)]
    loss = max(0.02, 2.0 * math.exp(-0.02 * i) + random.uniform(-0.02, 0.02))
    rn.log({"loss": round(loss, 4)}, stage=stage)

rn.summary(update={"best_val_acc_top1": 77.3})
rn.finish()
```

 
Viewer
------------
Start the local, read-only viewer and open the UI:

```bash
runicorn viewer
# or
runicorn viewer --storage ./.runicorn --host 127.0.0.1 --port 8000
# Then open http://127.0.0.1:8000
```
 
Desktop app (Windows)
---------------------
- Install from GitHub Releases (recommended for end users), or build locally.
- Build locally (creates an NSIS installer):

  ```powershell
  # From repo root
  powershell -ExecutionPolicy Bypass -File .\desktop\tauri\build_release.ps1 -Bundles nsis
  # Installer output:
  # desktop/tauri/src-tauri/target/release/bundle/nsis/Runicorn Desktop_<version>_x64-setup.exe
  ```

- After installation, launch "Runicorn Desktop".
  - First run: open the gear icon (top-right) → Settings → Data Directory, choose a writable path (e.g., `D:\RunicornData`), then Save.
  - The desktop app auto-starts a local backend and opens the UI.

Configuration
-------------
- Per-user storage root can be set via UI or CLI:

  - In Desktop app UI: gear icon → Settings → Data Directory (persisted to `%APPDATA%\Runicorn\config.json`).

  - Via CLI (global, reused by all projects):
  
  ```bash
  # Set a persistent per-user root used across all projects
  runicorn config --set-user-root "E:\\RunicornData"
  # Inspect current config
  runicorn config --show
```

- Precedence for resolving storage root:
  1. `runicorn.init(storage=...)`
  2. Environment variable `RUNICORN_DIR`
  3. Per-user config `user_root_dir` (set via `runicorn config`)
  4. Project-local `./.runicorn`

- Live logs are tailed from `logs.txt` via WebSocket at `/api/runs/{run_id}/logs/ws`.
 
Privacy & Offline
------------------
- No telemetry. The viewer only reads local files (JSON/JSONL and media).
- Default storage root is your per-user folder if configured, otherwise falls back to `./.runicorn`.
- Bundled UI allows using the viewer without Node.js at runtime.
 
Roadmap
-------
- Advanced filtering/search in the UI.
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
user_root_dir/
  <project>/
    <name>/
      runs/
        <run_id>/
          meta.json
          status.json
          summary.json
          events.jsonl
          logs.txt
          media/
```

Legacy layout is also supported for backward compatibility:

```
./.runicorn/
  runs/
    <run_id>/
      ...
```
 
Notes
-----
- GPU telemetry is shown if `nvidia-smi` is available.
- Windows compatible.


AI 
----
This project is mainly developed by OpenAI's GPT-5.