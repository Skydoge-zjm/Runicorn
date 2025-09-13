# Runicorn

[English](README.md) | [简体中文](README_zh.md)

[![PyPI version](https://img.shields.io/pypi/v/runicorn)](https://pypi.org/project/runicorn/)
[![Python Versions](https://img.shields.io/pypi/pyversions/runicorn)](https://pypi.org/project/runicorn/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<p align="center">
  <img src="docs/picture/icon.jpg" alt="Runicorn logo" width="360" />
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
  <img src="https://github.com/Skydoge-zjm/Runicorn/blob/main/docs/picture/p5.png" alt="Runicorn demo 5" width="98%" />
  <br/>
  <span style="color:#888; font-size: 12px;">Screenshots of Runicorn UI </span>
  
</p>

Features
--------
- 100% local, self-hosted. No external services. Data stays under your user-level root by default.
- Read-only viewer built on FastAPI; zero impact on your training loop.
- Prebuilt web UI bundled in wheel; offline-friendly after install.
- Step/time metrics with stage separators; live logs via WebSocket.
- Optional GPU telemetry panel if `nvidia-smi` is available.
- Global per-user storage with project/name hierarchy.
- Remote SSH live sync to mirror runs from a Linux server to your local storage.
- Compare multiple runs of the same experiment on a single chart (multi-run overlay).


Installation
------------
Requires Python 3.8+ (Windows/Linux). The desktop app is currently Windows-only; the CLI/Viewer work on both Windows and Linux.

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

Note: To use the web uploader for offline import (drag-and-drop .zip/.tar.gz in the UI), install the optional dependency:

```bash
pip install python-multipart
```
 
Remote (SSH live sync)
----------------------
Mirror runs from a remote Linux server to your local storage over SSH in real time.

- Open the UI and go to the top menu: `Remote` (or visit `/remote`).
- Steps:
  1) Connect: enter `host`, `port` (default 22), `username`; optionally provide a password or a private key (content or path).
  2) Browse remote directories and select the correct level:
     - New layout: select `<project>/<name>/runs`
     - Legacy layout: select `runs`
     - Avoid selecting a specific `<run_id>` directory.
  3) Click "Sync this directory". The task will appear under "Sync Tasks" and the "Runs" page refreshes immediately.

Tips & troubleshooting
- If no runs appear, verify:
  - The mirror task exists: GET `/api/ssh/mirror/list` shows an `alive: true` task with increasing counters.
  - The local storage root: GET `/api/config` and inspect the `storage` path. Check that runs are being created under the expected layout.
  - Directory level: ensure you selected `.../runs` (not a specific run folder).
  - Credentials are only used for the session and are not persisted. SSH is handled by Paramiko.

Desktop app (Windows)
---------------------
- Install from GitHub Releases (recommended for end users), or build locally.
- Prerequisites: Node.js 18+; Rust & Cargo (stable); Python 3.8+; NSIS (for installer packaging).
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

Linux development helper
------------------------
For local development on Linux, you can use the helper script:

```bash
chmod +x ./run_dev.sh
BACKEND_PORT=8000 FRONTEND_PORT=5173 ./run_dev.sh
```

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
 
Offline workflow (headless Linux server ➜ local PC)
--------------------------------------------------
When training on an offline, headless Linux server, and you want to visualize on your own PC:

1) On the Linux server (while or after training with `runicorn` SDK):
   - Ensure runs are written under your chosen storage root (see precedence below).
   - Export runs into a portable archive using the CLI:

   ```bash
   # Export all runs (new + legacy layouts) under the resolved storage root
   python3 -m runicorn.cli export --out /tmp/runicorn_export_$(date +%s).tar.gz

   # Or export a subset by project/name and/or run id
   python3 -m runicorn.cli export --project demo --name exp1 --out /tmp/exp1_runs.tar.gz
   python3 -m runicorn.cli export --run-id abc123 --run-id def456 --out /tmp/some_runs.tar.gz
   ```

   Transfer the archive to your PC via scp/USB.

2) On your PC (Windows or Linux):
   - Start the viewer:

   ```bash
   runicorn viewer
   # open http://127.0.0.1:8000
   ```

   - Open the UI (gear icon ➜ Settings) and use the "Offline Import" uploader to drop the `.tar.gz` or `.zip` archive. The runs will be extracted into the active storage root. (Requires `python-multipart`; install with `pip install python-multipart`.)

   - Alternatively, import via CLI without opening the UI:

   ```bash
   # Import into the configured storage root (or override with --storage)
   python -m runicorn.cli import --archive /path/to/exported_runs.tar.gz
   ```

Privacy & Offline
------------------
- No telemetry. The viewer only reads local files (JSON/JSONL and media).
- Default storage root is your per-user folder if configured, otherwise falls back to `./.runicorn`.
- Bundled UI allows using the viewer without Node.js at runtime.

Storage resolution precedence
-----------------------------
1. `runicorn.init(storage=...)`
2. Environment variable `RUNICORN_DIR`
3. Per-user config `user_root_dir` (set via `runicorn config`)
4. Project-local `./.runicorn`

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