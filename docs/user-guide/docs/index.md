---
title: Runicorn — Local ML Experiment Tracking
description: Open-source, self-hosted experiment tracking and visualization platform for machine learning. A privacy-first alternative to W&B.
hide:
  - toc
---

<div class="rn-hero">
  <img src="assets/logo.png" alt="Runicorn">
  <h1>Runicorn</h1>
  <p class="rn-tagline">
    Open-source experiment tracking for machine learning.<br>
    Self-hosted, privacy-first, runs entirely on your machine.
  </p>
  <div class="rn-install-inline">
    <code>pip install -U runicorn</code>
  </div>
  <p class="rn-install-meta">Python 3.10+ · Windows / Linux / macOS</p>
  <p class="rn-badges">
    <a href="https://pypi.org/project/runicorn/"><img src="https://img.shields.io/pypi/v/runicorn?color=blue&label=PyPI" alt="PyPI"></a>
    <a href="https://github.com/Skydoge-zjm/Runicorn"><img src="https://img.shields.io/github/stars/Skydoge-zjm/Runicorn?style=social" alt="GitHub"></a>
  </p>
</div>

<div class="rn-screenshot">
  <img src="assets/hero-screenshot.png" alt="Runicorn Web UI">
</div>

---

## Key Features

<div class="rn-features">
  <div class="rn-feat">
    <strong>100% Local</strong>
    <span>All data stays on your machine. Complete privacy by design.</span>
  </div>
  <div class="rn-feat">
    <strong>Assets &amp; Versioning</strong>
    <span>SHA256 content-addressed storage with workspace snapshots.</span>
  </div>
  <div class="rn-feat">
    <strong>Rich Visualization</strong>
    <span>Interactive charts, EMA smoothing, inline run comparison.</span>
  </div>
  <div class="rn-feat">
    <strong>Remote Viewer</strong>
    <span>VSCode-style remote access via SSH tunnel.</span>
  </div>
  <div class="rn-feat">
    <strong>High Performance</strong>
    <span>LTTB downsampling and incremental caching.</span>
  </div>
  <div class="rn-feat">
    <strong>Cross-Platform</strong>
    <span>Python SDK, Web UI, and Desktop App.</span>
  </div>
</div>

---

## Quick Start

```python
import runicorn as rn

run = rn.init(path="demo/quickstart")

for step in range(1, 101):
    run.log({"loss": 2.0 * (0.95 ** step), "acc": 0.5 + step * 0.005}, step=step)

run.finish()
```

```bash
runicorn viewer    # → http://127.0.0.1:23300
```

---

## What's New in v0.6.0

<div class="rn-grid">
  <div class="rn-card">
    <h3>Assets System</h3>
    <p>SHA256 content-addressed storage with 50–90% deduplication. Workspace snapshots and blob storage.</p>
    <a class="rn-card-link" href="getting-started/assets-system/">Learn more →</a>
  </div>
  <div class="rn-card">
    <h3>Enhanced Logging</h3>
    <p>Console capture, Python logging handler, MetricLogger compatibility, smart tqdm filtering.</p>
    <a class="rn-card-link" href="getting-started/enhanced-logging/">Learn more →</a>
  </div>
  <div class="rn-card">
    <h3>Path-based Hierarchy</h3>
    <p>Flexible <code>path</code> parameter replaces project/name. VSCode-style tree navigation.</p>
    <a class="rn-card-link" href="getting-started/path-hierarchy/">Learn more →</a>
  </div>
  <div class="rn-card">
    <h3>Inline Compare</h3>
    <p>Multi-run metric comparison with ECharts and common metrics auto-detection.</p>
    <a class="rn-card-link" href="ui/overview/">Learn more →</a>
  </div>
</div>

---

!!! tip "Recommended Learning Path"

    1. **[Quick Start](getting-started/quickstart.md)** — Install and run your first experiment
    2. **[Path Hierarchy](getting-started/path-hierarchy.md)** — Organize experiments
    3. **[Python SDK](sdk/overview.md)** — Core API reference
    4. **[Tutorial](tutorials/image-classification.md)** — End-to-end image classification example
    5. **[FAQ](reference/faq.md)** — Common questions

---

## Community

[GitHub Issues](https://github.com/Skydoge-zjm/Runicorn/issues) ·
[Contributing](https://github.com/Skydoge-zjm/Runicorn/blob/main/CONTRIBUTING.md) ·
[Security](https://github.com/Skydoge-zjm/Runicorn/security)

Runicorn is open-source under the **MIT License**.

<div class="rn-cta">
  <a href="getting-started/quickstart/">Get Started</a>
</div>
