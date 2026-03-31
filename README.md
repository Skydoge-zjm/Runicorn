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

## 🆕 v0.7.0 (Latest)

- 🌐 **Remote Viewer Hardening** — Saved connections, health monitoring, reconnect states, and OpenSSH password support
- 🎨 **Web UI Productization** — Cleaner navigation, better compare flow, ZIP import/export preview, and unified recycle bin
- 📈 **Logs & Monitoring** — Virtualized logs, stronger dark-mode consistency, and backend-collected GPU telemetry history
- 🔌 **Logging Compatibility** — Better support for ImageNet meters, TensorBoard, and tensorboardX
- 🖥️ **Desktop Improvements** — Native remote-session windows in the current desktop workflow

---

## License

MIT — see [LICENSE](LICENSE)

---

**Version**: v0.7.0 | **Last Updated**: 2026-03-28
