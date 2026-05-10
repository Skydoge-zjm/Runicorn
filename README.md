# Runicorn

**English** | [简体中文](README_zh.md)

[![PyPI version](https://img.shields.io/pypi/v/runicorn)](https://pypi.org/project/runicorn/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<p align="center">
  <img src="docs/assets/icon.jpg" alt="Runicorn logo" width="300" />
</p>

**Local, open-source ML experiment tracking.** 100% offline, zero telemetry. A modern self-hosted alternative to W&B.

---

## ✨ Highlights

| Feature | Description |
|---------|-------------|
| 🏠 **100% Local** | Your data never leaves your machine |
| 📊 **Real-time Visualization** | Live metrics, logs, and GPU monitoring |
| 📦 **Assets & Snapshots** | Workspace snapshots plus dataset/config/pretrained references |
| 🌐 **Remote Viewer** | Access remote GPU servers via SSH (like VSCode Remote) |
| 🖥️ **Desktop App** | Native Windows app with auto-backend |

<table>
  <tr>
    <td><img src="docs/assets/p1.png" alt="Experiments" width="100%" /></td>
    <td><img src="docs/assets/p2.png" alt="Detail" width="100%" /></td>
  </tr>
</table>

---

## 🚀 Quick Start

```bash
pip install runicorn
runicorn viewer  # Open http://127.0.0.1:23300
```

```python
import runicorn as rn

run = rn.init(path="my_project/exp_1", alias="baseline")

for epoch in range(100):
    loss = train_one_epoch()
    run.log({"loss": loss}, step=epoch + 1)

run.finish()
```

---

## 🎯 Who It's For

**Good fit**

- You train locally or on your own servers and want experiment tracking without SaaS lock-in
- You need metrics, logs, assets, and code context in one place
- You regularly jump between a local workstation and remote GPU machines

**Not a good fit**

- You need a hosted collaboration platform, team permissions, or cloud dashboards out of the box
- You only want a minimal CSV logger and do not care about browsing runs later
- Your workflow depends on a managed online ecosystem rather than local or self-controlled infrastructure

---

## ✅ Recommended Workflow

1. Add `runicorn.init(...)` to your training entrypoint and log metrics during training
2. Open `runicorn viewer` locally to inspect runs, compare metrics, and review logs/assets
3. Save snapshots or references for config, datasets, and pretrained inputs when the run matters
4. Use the `Remote` page when training happens on a GPU server, so you can inspect the remote run without copying files back first

---

## 🔍 Why Use It

| Workflow | Common friction | Runicorn |
|---|---|---|
| Manual local folders + scripts | Metrics, logs, configs, and outputs drift apart | Keeps run history, summary, logs, and assets tied to one run |
| Remote SSH + tail + ad-hoc plotting | Slow to inspect, hard to compare, easy to lose context | Remote Viewer gives a structured UI over SSH without a sync-first loop |
| Hosted experiment tracker | Requires internet/service trust and external storage | Stays local, offline, and under your storage boundary |

---

## 📦 Assets & Workspace Snapshots

```python
from pathlib import Path

snapshot = rn.snapshot_workspace(Path.cwd(), Path("workspace_snapshot.zip"))

print(snapshot["archive_path"])
print(snapshot["file_count"])
```

Use `run.log_config(...)`, `run.log_dataset(...)`, and `run.log_pretrained(...)` inside a run to attach reusable training context without relying on the removed `Artifact` API.

---

## 🌐 Remote Viewer

Access remote GPU servers without file sync:

```bash
runicorn viewer  # → Click "Remote" → SSH credentials → Done!
```

| | Old Sync (v0.4) | Remote Viewer (v0.5+) |
|---|---|---|
| **Wait** | Minutes~Hours | Seconds |
| **Storage** | Required | Zero |
| **Real-time** | ❌ | ✅ |

---

## 📚 Documentation

| Resource | Link |
|----------|------|
| User Guide | [docs/user-guide/](docs/user-guide/) |
| API Reference | [docs/api/](docs/api/) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |

---

## 🆕 v0.7.1 (Latest)

- 🛡️ **Reliability Hardening** — Tighter API/documentation alignment, clearer remote API boundaries, and stronger legacy-path cleanup
- 🔐 **Security Tightening** — Safer handling around legacy XOR credential migration and saved-credential compatibility
- ✅ **Test & CI Coverage** — Expanded smoke and baseline coverage, with more consistent frontend and desktop validation
- 🖥️ **Desktop Build Hardening** — Reproducible build controls, layered build configuration, and stronger sidecar packaging workflow
- 📚 **Release Cleanup** — Current-version docs and release metadata aligned to the shipped API surface

---

## License

MIT — see [LICENSE](LICENSE)

---

**Version**: v0.7.1 | **Last Updated**: 2026-05-10
