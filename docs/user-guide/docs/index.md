---
title: Runicorn User Guide
description: User guide for Runicorn 0.7.2.
hide:
  - toc
---

<div class="rn-hero">
  <img src="assets/logo.png" alt="Runicorn">
  <h1>Runicorn</h1>
  <p class="rn-tagline">
    Local-first experiment tracking for machine learning.<br>
    Python SDK, Web UI, Remote Viewer, and desktop workflow in one tool.
  </p>
  <div class="rn-install-inline">
    <code>pip install -U runicorn</code>
  </div>
  <p class="rn-install-meta">Python 3.10+ | Windows / Linux / macOS</p>
  <p class="rn-badges">
    <a href="https://pypi.org/project/runicorn/"><img src="https://img.shields.io/pypi/v/runicorn?color=blue&label=PyPI" alt="PyPI"></a>
    <a href="https://github.com/Skydoge-zjm/Runicorn"><img src="https://img.shields.io/github/stars/Skydoge-zjm/Runicorn?style=social" alt="GitHub"></a>
  </p>
</div>

<div class="rn-screenshot">
  <img src="assets/main_page/experiment_list.png" alt="Runicorn Web UI">
</div>

## What Runicorn is good at

<div class="rn-features">
  <div class="rn-feat">
    <strong>100% Local</strong>
    <span>Runs, logs, assets, and settings stay in your own storage directory.</span>
  </div>
  <div class="rn-feat">
    <strong>Python-first Tracking</strong>
    <span>Log metrics, text, images, datasets, pretrained weights, and code snapshots.</span>
  </div>
  <div class="rn-feat">
    <strong>Modern Web UI</strong>
    <span>Path tree navigation, compare mode, recycle bin, ZIP import/export, and theme presets.</span>
  </div>
  <div class="rn-feat">
    <strong>Remote Viewer</strong>
    <span>SSH-based remote access with saved connections, host key confirmation, and health monitoring.</span>
  </div>
  <div class="rn-feat">
    <strong>Logging Compatibility</strong>
    <span>Works with Python logging, torchvision MetricLogger, ImageNet meters, TensorBoard, and tensorboardX.</span>
  </div>
  <div class="rn-feat">
    <strong>Desktop Option</strong>
    <span>The current desktop build can open native windows for remote sessions on top of the same local viewer stack.</span>
  </div>
</div>

---

## Start here

<div class="rn-grid">
  <div class="rn-card">
    <h3>Quick Start</h3>
    <p>Install Runicorn, choose a storage root, create a first run, and open the viewer.</p>
    <a class="rn-card-link" href="getting-started/quickstart/">Open guide -></a>
  </div>
  <div class="rn-card">
    <h3>Remote Viewer</h3>
    <p>Connect to remote GPU servers with the current three-step wizard and OpenSSH-first workflow.</p>
    <a class="rn-card-link" href="getting-started/remote-viewer/">Open guide -></a>
  </div>
  <div class="rn-card">
    <h3>Web UI</h3>
    <p>Learn the current page structure: experiments, assets, performance, remote sessions, and settings.</p>
    <a class="rn-card-link" href="ui/overview/">Open guide -></a>
  </div>
  <div class="rn-card">
    <h3>SDK and CLI</h3>
    <p>Go deeper into run lifecycle, asset tracking, compatibility helpers, and daily command-line workflows.</p>
    <a class="rn-card-link" href="sdk/overview/">Open guide -></a>
  </div>
</div>

---

## What changed after 0.6.0

- Remote Viewer became much more resilient: host key confirmation, faster environment probing, health monitoring, reconnect states, idle shutdown, and OpenSSH password support.
- The Web UI moved toward a more productized layout: professional defaults, cleaner navigation, compare deep links, ZIP import/export preview, and a unified recycle-bin flow.
- Logs and monitoring improved: virtualized log rendering, GPU history playback, and better chart/theme consistency.
- Logging compatibility expanded beyond the original `MetricLogger` support to include ImageNet-style meters, TensorBoard, and tensorboardX patterns.
- The desktop build now supports native remote-session windows instead of sending every session to an external browser.

---

## Recommended path

1. [Quick Start](getting-started/quickstart.md)
2. [Installation & Storage](getting-started/installation-and-storage.md)
3. [Remote Viewer](getting-started/remote-viewer.md)
4. [Web UI Overview](ui/overview.md)
5. [Python SDK Overview](sdk/overview.md)
6. [CLI Overview](cli/overview.md)

---

## Community

[GitHub Issues](https://github.com/Skydoge-zjm/Runicorn/issues) |
[Contributing](https://github.com/Skydoge-zjm/Runicorn/blob/main/CONTRIBUTING.md) |
[Security](https://github.com/Skydoge-zjm/Runicorn/security)

Runicorn is open-source under the **MIT License**.

<div class="rn-cta">
  <a href="getting-started/quickstart/">Get Started</a>
</div>
