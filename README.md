# Runicorn

**English** | [简体中文](README_zh.md)

[![PyPI version](https://img.shields.io/pypi/v/runicorn)](https://pypi.org/project/runicorn/)
[![Python Versions](https://img.shields.io/pypi/pyversions/runicorn)](https://pypi.org/project/runicorn/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<p align="center">
  <img src="docs/picture/icon.jpg" alt="Runicorn logo" width="360" />
</p>

Local, open-source experiment tracking and visualization. 100% offline. Professional ML experiment management; a modern self-hosted alternative to W&B.

## ✨ What's New in v0.3.0

- 🎯 **Universal Best Metric System** - Track any metric as primary indicator
- 🗑️ **Soft Delete & Recycle Bin** - Safe experiment management with restore capability  
- 🛡️ **Smart Status Detection** - Automatic detection of crashed/interrupted experiments
- 🎨 **Modern Settings Interface** - Tabbed settings with comprehensive customization
- 📱 **Responsive Design** - Perfect display on any screen size
- 🌍 **Full Internationalization** - Complete Chinese/English support
- 📊 **Enhanced Experiment Management** - Tagging, search, batch operations
- 🔧 **Advanced Features** - Environment tracking, multiple export formats, anomaly detection

## Core Features

- **Package**: `runicorn` - Universal Python SDK for any ML framework
- **Viewer**: Web interface with real-time charts and experiment comparison
- **Remote Sync**: Live SSH mirroring from Linux servers  
- **Desktop App**: Native Windows application with auto-backend
- **GPU Monitoring**: Real-time GPU telemetry if `nvidia-smi` available


<p align="center">
  <img src="docs/picture/p1.png" alt="Runicorn demo 1" width="98%" />
  <br/>
  <img src="docs/picture/p2.png" alt="Runicorn demo 2" width="98%" />
  <br/>
  <img src="docs/picture/p3.png" alt="Runicorn demo 3" width="98%" />
  <br/>
  <span style="color:#888; font-size: 12px;">UI overview</span>
  
</p>

Features
--------

### 🏠 **Local & Secure**
- 100% local; data stays on your machine
- Zero telemetry; complete privacy
- Offline-capable after installation

### 🎯 **Smart Experiment Tracking**
- **Universal Best Metric** - Set any metric as primary indicator with auto-tracking
- **Intelligent Status Detection** - Automatic detection of crashed/interrupted experiments
- **Soft Delete & Recycle Bin** - Safe experiment management with restore capability
- **Environment Capture** - Automatic Git, dependencies, and system info tracking

### 📊 **Advanced Visualization**
- **Multi-run Comparison** - Overlay multiple experiments on single charts
- **Responsive Charts** - Adaptive layouts for any screen size
- **Real-time Updates** - Live logs and GPU monitoring via WebSocket
- **Multiple Export Formats** - CSV, Excel, TensorBoard, Markdown reports

### 🎨 **Modern Interface**
- **Tabbed Settings** - Comprehensive customization with live preview
- **Multi-language Support** - Full Chinese/English internationalization
- **Glass Morphism UI** - Beautiful modern design with customizable themes
- **Smart Layouts** - Automatic responsive design


Installation
------------
Requires Python 3.8+ (Windows/Linux). The desktop app is currently Windows-only; the CLI/Viewer work on both Windows and Linux.

```bash
pip install -U runicorn
```

Quick start
-----------------

### Start the viewer

```bash
runicorn viewer
# or custom params
runicorn viewer --host 127.0.0.1 --port 8000
# Open http://127.0.0.1:8000
```

Recommended: if you have Runicorn Desktop installed, just double-click to launch.

### Set the local storage root

- In Desktop app UI: top-right gear → Settings → Data Directory → Save Data Directory.

- Via CLI:

```bash
runicorn config --set-user-root "E:\\RunicornData"
runicorn config --show
```

The setting is written to `%APPDATA%\Runicorn\config.json` and can be edited directly.

### Usage example

```python
import runicorn as rn
import math, random

# Initialize experiment with automatic environment capture
run = rn.init(project="demo", name="exp1", capture_env=True)

# Set primary metric for automatic best value tracking
rn.set_primary_metric("accuracy", mode="max")  # or mode="min" for loss

stages = ["warmup", "train", "eval"]
for i in range(1, 101):
    stage = stages[min((i - 1) // 33, len(stages) - 1)]
    
    # Simulate training metrics
    loss = max(0.02, 2.0 * math.exp(-0.02 * i) + random.uniform(-0.02, 0.02))
    accuracy = min(95.0, 60 + i * 0.3 + random.uniform(-2, 2))
    
    # Log metrics - best accuracy will be automatically tracked
    rn.log({
        "loss": round(loss, 4),
        "accuracy": round(accuracy, 2),
        "learning_rate": 0.001 * (0.95 ** i)
    }, stage=stage)

# Summary metrics
rn.summary({
    "final_accuracy": 92.1,
    "total_epochs": 100,
    "notes": "Baseline model with improved architecture"
})

rn.finish()  # Best metric automatically saved
```

### Advanced features

```python
# Exception handling (automatic)
try:
    # Your training code
    train_model()
    rn.finish("finished")
except Exception as e:
    rn.finish("failed")  # Status correctly updated

# Environment tracking
run = rn.init(project="research", name="experiment_v2", capture_env=True)
# Automatically captures: Git info, dependencies, system specs

# Monitoring and alerts (optional)
if hasattr(rn, 'MetricMonitor'):
    monitor = rn.MetricMonitor()
    # Automatic detection of NaN/Inf values and training issues

# Data export (optional)
if hasattr(rn, 'MetricsExporter'):
    exporter = rn.MetricsExporter(run.run_dir)
    exporter.to_excel("results.xlsx", include_charts=True)
    exporter.generate_report("report.md", format="markdown")
```

Optional: explicitly override the storage root

```python
run = rn.init(project="demo", name="exp1", storage="E:\\RunicornData")
```

Storage root precedence (high → low):

1. `runicorn.init(storage=...)`
2. Environment variable `RUNICORN_DIR`
3. Per-user config `user_root_dir` (set via `runicorn config` or web UI)


Remote
----------------------
Mirror runs from a remote Linux server to your local storage over SSH in real time.

- Open the top navigation "Remote" page
- Steps:
  1) Connect: enter `host`, `port` (default 22), `username`; optionally enter `password` or `private key` content/path.
  2) Browse remote directories and select the correct level:
     - For v0.2.0 and above: we recommend selecting the per-user root directory.
  3) Click "Sync this directory". A "Sync Task" appears below, and the "Runs" page refreshes immediately.

Tips & troubleshooting
- If no runs appear, check:
  - Mirror task: GET `/api/ssh/mirror/list` should show `alive: true` with increasing counters.
  - Local storage root: GET `/api/config` to inspect the `storage` path; verify the expected hierarchy is created.
  - Credentials are only used for this session and are not persisted; SSH is handled by Paramiko.

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

Privacy & Offline
-----------------
- No telemetry. The viewer only reads local files (JSON/JSONL and media).
- Bundled UI allows using the viewer without Node.js at runtime.

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

Community
---------
- See `CONTRIBUTING.md` for dev setup, style, and release flow.
- See `SECURITY.md` for private vulnerability reporting.
- See `CHANGELOG.md` for version history.

AI
---
This project is mainly developed by OpenAI's GPT-5.
