[English](QUICKSTART.md) | [简体中文](../zh/QUICKSTART.md)

---

# Runicorn Quick Start Guide

Get started with Runicorn in 5 minutes.

---

## 📦 Installation

```bash
pip install runicorn
```

**Requirements**: Python 3.8+

---

## 🚀 Basic Usage

### 1. Experiment Tracking

```python
import runicorn as rn

# Initialize experiment
run = rn.init(project="my_project", name="experiment_1")

# Log metrics
for epoch in range(10):
    loss = 1.0 / (1 + epoch)
    accuracy = 0.5 + epoch * 0.05
    
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

- **Experiments List**: See all your runs
- **Experiment Detail**: Click to view charts and logs
- **Metrics Charts**: Interactive training curves
- **Real-time Logs**: Live log streaming

---

## 💾 Model Versioning

### Save Model

```python
import runicorn as rn

run = rn.init(project="training")

# After training
# torch.save(model.state_dict(), "model.pth")

# Save as versioned artifact
artifact = rn.Artifact("my-model", type="model")
artifact.add_file("model.pth")
artifact.add_metadata({"accuracy": 0.95})

version = run.log_artifact(artifact)  # v1, v2, v3...
run.finish()
```

### Load Model

```python
import runicorn as rn

run = rn.init(project="inference")

# Load model
artifact = run.use_artifact("my-model:latest")
model_path = artifact.download()

# Use model...
run.finish()
```

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

- **[Artifacts Guide](ARTIFACTS_GUIDE.md)** - Model version control
- **[Remote Viewer Guide](REMOTE_VIEWER_GUIDE.md)** - Real-time remote server access
- **[Demo Examples](DEMO_EXAMPLES_GUIDE.md)** - Example code walkthrough
- **[Migration Guide](MIGRATION_GUIDE_v0.4_to_v0.5.md)** - Upgrade from 0.4.x to 0.5.0

---

**[Back to Guides](README.md)** | **[Back to Main](../../README.md)**

