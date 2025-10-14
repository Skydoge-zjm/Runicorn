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
    
    rn.log({
        "loss": loss,
        "accuracy": accuracy
    }, step=epoch)

# Finish
rn.finish()
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
rn.finish()
```

### Load Model

```python
import runicorn as rn

run = rn.init(project="inference")

# Load model
artifact = run.use_artifact("my-model:latest")
model_path = artifact.download()

# Use model...
rn.finish()
```

---

## 🔄 Remote Sync

Train on remote server, view locally in real-time.

**In Web UI**:
1. Go to "Remote" page
2. Enter SSH credentials
3. Click "Configure Smart Mode"
4. Experiments sync automatically!

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
- **[Remote Storage Guide](REMOTE_STORAGE_USER_GUIDE.md)** - Remote sync setup
- **[Demo Examples](DEMO_EXAMPLES_GUIDE.md)** - Example code walkthrough

---

**[Back to Guides](README.md)** | **[Back to Main](../../README.md)**

