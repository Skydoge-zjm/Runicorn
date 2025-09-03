# Runicorn
 
[![PyPI version](https://img.shields.io/pypi/v/runicorn)](https://pypi.org/project/runicorn/)
[![Python Versions](https://img.shields.io/pypi/pyversions/runicorn)](https://pypi.org/project/runicorn/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
 
Local, open-source experiment tracking and visualization. 100% local. A lightweight, self-hosted alternative to W&B.
 
- Package/Library name: runicorn
- Default storage path: ./.runicorn
- Viewer: read-only, serves metrics/logs/media from local storage
- GPU telemetry: optional panel (reads nvidia-smi if available)
 
![](https://github.com/Skydoge-zjm/Runicorn/blob/main/docs/picture/p1.png)
![](https://github.com/Skydoge-zjm/Runicorn/blob/main/docs/picture/p2.png)

Features
--------
- 100% local, self-hosted. No external services. Data stays under `./.runicorn/` by default.
- Read-only viewer built on FastAPI; zero impact on your training loop.
- Prebuilt web UI bundled in wheel; offline-friendly after install.
- Step/time metrics with stage separators; live logs via WebSocket.
- Optional GPU telemetry panel if `nvidia-smi` is available.


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

run = rn.init(project="demo")

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
 
Configuration
-------------
- Environment variable `RUNICORN_DIR` overrides the default storage root (`./.runicorn`).
- Or pass `--storage` to the CLI or `storage=` to `runicorn.init()`.
- Live logs are tailed from `logs.txt` via WebSocket at `/api/runs/{run_id}/logs/ws`.
 
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
