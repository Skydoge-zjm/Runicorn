[English](QUICKSTART.md) | [简体中文](../zh/QUICKSTART.md)

---

# Runicorn Quick Start Guide

> **Version**: v0.6.0

Get started with Runicorn in 5 minutes.

---

## 📦 Installation

```bash
pip install runicorn
```

**Requirements**: Python 3.10+

---

## 🚀 Basic Usage

### 1. Experiment Tracking

```python
import runicorn as rn

# Initialize experiment with console capture (v0.6.0)
run = rn.init(
    path="my_project/experiment_1",
    capture_console=True,  # Capture print output to logs.txt
)

# All print output is automatically captured
print("Starting training...")

# Log metrics
for epoch in range(10):
    loss = 1.0 / (1 + epoch)
    accuracy = 0.5 + epoch * 0.05
    
    print(f"Epoch {epoch}: loss={loss:.4f}, acc={accuracy:.2f}")
    
    run.log({
        "loss": loss,
        "accuracy": accuracy
    }, step=epoch)

# Finish
run.finish()
print(f"Experiment ID: {run.id}")
```

### 2. Start Viewer

```bash
runicorn viewer
```

Open browser: [http://127.0.0.1:23300](http://127.0.0.1:23300)

---

## 📊 View Results

In the web interface:

- **Experiments List**: See all your runs with path-based hierarchy navigation
- **Experiment Detail**: Click to view charts and logs
- **Metrics Charts**: Interactive training curves with inline comparison
- **Real-time Logs**: Live log streaming with ANSI color support
- **Path Tree Navigation**: VSCode-style folder navigation (v0.6.0)

---

## 📝 Enhanced Logging (v0.6.0 New Feature)

Automatically capture all console output without code changes:

```python
import runicorn as rn
from tqdm import tqdm

# Enable console capture
run = rn.init(path="training", capture_console=True, tqdm_mode="smart")

print("Starting training...")

# tqdm progress bars are handled intelligently
for batch in tqdm(dataloader, desc="Training"):
    loss = train_step(batch)
    run.log({"loss": loss})

run.finish()
```

**Features**:
- ✅ Automatic `print()` capture to `logs.txt`
- ✅ Smart tqdm handling (no log bloat)
- ✅ Python logging integration via `run.get_logging_handler()`
- ✅ MetricLogger compatibility for CV projects

**Complete Guide**: [Enhanced Logging Guide](ENHANCED_LOGGING_GUIDE.md)

---

## 📦 Assets System (v0.6.0 New Feature)

Efficient workspace snapshots with SHA256 deduplication:

```python
import runicorn as rn
from runicorn import snapshot_workspace
from pathlib import Path

run = rn.init(path="training")

# Snapshot your code for reproducibility
result = snapshot_workspace(
    root=Path("."),
    out_zip=run.run_dir / "code_snapshot.zip",
)
print(f"Captured {result['file_count']} files")

# Train...
run.finish()
```

**Features**:
- ✅ SHA256 content-addressed storage
- ✅ 50-90% storage savings via deduplication
- ✅ `.rnignore` support (like `.gitignore`)
- ✅ Manifest-based restore

**Complete Guide**: [Assets Guide](ASSETS_GUIDE.md)

---

---

## 🌐 Remote Viewer (v0.5.0 New Feature)

Train on remote server, view locally in real-time - **No data sync needed**!

### 5-Minute Quick Start

#### Step 1: Ensure Runicorn is Installed on Remote Server

```bash
# SSH login to remote server
ssh user@gpu-server.com

# Install Runicorn
pip install runicorn
```

#### Step 2: Start Local Viewer

```bash
runicorn viewer
```

#### Step 3: Connect to Remote Server

1. Click **"Remote"** menu in browser
2. Fill in SSH connection info:
   - Host: `gpu-server.com`
   - User: `your-username`
   - Auth: SSH key or password
3. Click **"Connect to Server"**

#### Step 4: Select Python Environment

System auto-detects remote environments, select one with Runicorn installed.

#### Step 5: Start Remote Viewer

Click **"Start Remote Viewer"**, automatically opens new tab to access remote data!

**Advantages**:
- ✅ Real-time access, latency < 100ms
- ✅ Zero local storage usage
- ✅ Connection startup in seconds

**Complete Guide**: [Remote Viewer User Guide](REMOTE_VIEWER_GUIDE.md)

---

## ⚙️ Configuration

### Set Storage Location

```bash
runicorn config --set-user-root "E:\RunicornData"
```

Or in Web UI: Settings (⚙️) → Data Directory

---

## 📚 Learn More

### v0.6.0 New Features
- **[Enhanced Logging Guide](ENHANCED_LOGGING_GUIDE.md)** - Console capture, Python logging integration
- **[Assets Guide](ASSETS_GUIDE.md)** - SHA256 deduplication, workspace snapshots

### Core Features
- **[Remote Viewer Guide](REMOTE_VIEWER_GUIDE.md)** - Real-time remote server access
- **[Demo Examples](DEMO_EXAMPLES_GUIDE.md)** - Example code walkthrough

### Migration
- **[Migration Guide](MIGRATION_GUIDE_v0.4_to_v0.5.md)** - Upgrade from 0.4.x to 0.5.0

---

**[Back to Guides](README.md)** | **[Back to Main](../../README.md)**

