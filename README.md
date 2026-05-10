# Runicorn

**English** | [简体中文](README_zh.md)

[![PyPI version](https://img.shields.io/pypi/v/runicorn)](https://pypi.org/project/runicorn/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<p align="center">
  <img src="docs/assets/icon.jpg" alt="Runicorn logo" width="280" />
</p>

**Local-first experiment tracking for teams and individuals who keep ML runs on their own machines or GPU servers.**

Runicorn combines a Python SDK, Web UI, Remote Viewer, and optional Windows desktop build into one workflow. It is designed for people who want experiment tracking without pushing runs into a SaaS platform, mirroring remote run folders back to a laptop, or rewriting an existing training stack from scratch.

If your experiments run on remote Linux boxes, Runicorn can start a lightweight Viewer on the remote machine and tunnel it over SSH, so you inspect runs directly where they live.

[Documentation Site](https://skydoge-zjm.github.io/Runicorn/)

<p align="center">
  <img src="docs/user-guide/docs/assets/main_page/experiment_list.png" alt="Runicorn experiments view" width="100%" />
</p>

---

## Why Runicorn

- **Data stays under your control**: runs, logs, assets, and settings remain on storage you control
- **Remote Viewer without file sync**: inspect remote GPU-server experiments over SSH instead of copying run folders back first
- **Low-friction adoption**: start with `rn.init(...)` and `run.log(...)`, while keeping compatibility with `print()`, Python `logging`, torchvision `MetricLogger`, ImageNet meters, TensorBoard, and tensorboardX
- **Real experiment context**: store config metadata, dataset references, pretrained references, code snapshots, and archived outputs alongside scalar metrics
- **Rich local UI**: path tree, compare mode, assets repository, recycle bin, import/export, GPU telemetry, and remote session management

---

## Who It's For

**Good fit**

- You train locally or on your own servers and want experiment tracking without SaaS lock-in
- You often switch between a local workstation and remote GPU machines
- You want metrics, logs, code context, and experiment assets tied to the same run
- You already have training code and want an incremental adoption path instead of a large rewrite

**Not a good fit**

- You need a hosted collaboration platform, cloud dashboards, or team permissions out of the box
- You only want a minimal CSV logger and do not care about browsing runs later
- Your workflow depends on a managed online ecosystem rather than local or self-controlled infrastructure

---

## Quick Start

Install Runicorn:

```bash
pip install -U runicorn
```

Log your first run:

```python
import runicorn as rn

run = rn.init(
    path="cv/resnet50/baseline",
    alias="trial-01",
    capture_console=True,
)

for epoch in range(1, 11):
    train_loss = 1.0 / epoch
    val_acc = 0.70 + epoch * 0.02
    run.log({"train_loss": train_loss, "val_acc": val_acc})

run.summary({"notes": "first stable run"})
run.finish()
```

Open the viewer:

```bash
runicorn viewer
```

Then visit [http://127.0.0.1:23300](http://127.0.0.1:23300).

---

## What Makes It Different

| Workflow | Common friction | Runicorn |
|---|---|---|
| Manual local folders + scripts | Metrics, logs, configs, and outputs drift apart | Keeps run history, summary, logs, and assets tied to one run |
| Remote SSH + tail + ad-hoc plotting | Slow to inspect, hard to compare, easy to lose context | Remote Viewer gives a structured UI over SSH without a sync-first loop |
| Hosted experiment tracker | Requires internet/service trust and external storage | Keeps experiment data local and under your storage boundary |

---

## Remote Viewer

Runicorn is strongest when training happens on remote GPU servers.

With Remote Viewer, you can connect over SSH, choose the remote Python environment, start a remote Viewer session, and inspect remote runs through your local browser or desktop app.

No local mirror. No manual sync step. No waiting for large run folders to copy.

```bash
runicorn viewer
# Open the Remote page -> connect over SSH -> choose environment -> start session
```

| | Old sync-heavy workflow | Remote Viewer |
|---|---|---|
| Wait time | Minutes to hours | Seconds |
| Local storage copy | Required | Not required |
| Experiment inspection | Delayed | Direct over SSH |

---

## Logging Compatibility

Runicorn is built to fit into training code that already exists.

If your loop already uses torchvision-style metric logging, you can often start by replacing one import:

```python
from runicorn.log_compat.torchvision import MetricLogger as MetricLogger
```

Runicorn also provides compatibility helpers for:

- `runicorn.log_compat.imagenet`
- `runicorn.log_compat.tensorboard`
- `runicorn.log_compat.tensorboardX`

You can also capture `print()` output and Python `logging`, but the main value here is structured metric compatibility that turns existing training signals into real experiment curves.

---

## Assets and Run Context

Runicorn does not stop at scalar metrics. You can also record the surrounding context that makes runs understandable later:

- config metadata
- dataset references
- pretrained model references
- code snapshots
- archived output files
- cross-run asset browsing and preview

Use `run.log_config(...)`, `run.log_dataset(...)`, and `run.log_pretrained(...)` inside a run to attach reusable training context directly to the experiment record.

---

## Documentation

- [Quick Start](docs/user-guide/docs/getting-started/quickstart.md)
- [Remote Viewer Guide](docs/user-guide/docs/getting-started/remote-viewer.md)
- [Python SDK Overview](docs/user-guide/docs/sdk/overview.md)
- [Web UI Overview](docs/user-guide/docs/ui/overview.md)
- [CLI Overview](docs/user-guide/docs/cli/overview.md)
- [Changelog](CHANGELOG.md)

---

## License

MIT. See [LICENSE](LICENSE).
