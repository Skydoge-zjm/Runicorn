# Runicorn User Guide

<div align="center">
  <img src="assets/logo.png" alt="Runicorn Logo" width="200">
  <h3>🦄 Local ML Experiment Tracking & Model Versioning</h3>
  <p><strong>v0.6.0</strong> • 100% Offline • Privacy-First • Self-Hosted</p>
  
  <p>
    <a href="https://pypi.org/project/runicorn/"><img src="https://img.shields.io/pypi/v/runicorn?color=blue&label=PyPI" alt="PyPI"></a>
    <a href="https://github.com/Skydoge-zjm/Runicorn"><img src="https://img.shields.io/github/stars/Skydoge-zjm/Runicorn?style=social" alt="GitHub"></a>
  </p>
</div>

---

## ✨ What's New in v0.6.0

<div class="grid cards" markdown>

-   :material-package-variant:{ .lg .middle } __New Assets System (v0.6.0)__

    ---

    SHA256 content-addressed storage with 50-90% deduplication. Workspace snapshots and blob storage.

-   :material-text-box-outline:{ .lg .middle } __Enhanced Logging (v0.6.0)__

    ---

    Console capture, Python logging handler, MetricLogger compatibility, smart tqdm filtering.

-   :material-file-tree:{ .lg .middle } __Path-based Hierarchy (v0.6.0)__

    ---

    VSCode-style PathTreePanel navigation with batch operations and export.

-   :material-compare:{ .lg .middle } __Inline Compare View (v0.6.0)__

    ---

    Multi-run metric comparison with ECharts, common metrics detection.

</div>

---

## What is Runicorn?

**Runicorn** is a local, open-source experiment tracking and visualization platform designed for machine learning researchers and engineers. Think of it as a **self-hosted alternative to Weights & Biases** that runs entirely on your computer.

### Key Features

- 🏠 **100% Local** - All data stays on your machine, complete privacy
- 📦 **Model Versioning** - Git-like version control for ML models and datasets
- 📊 **Beautiful Visualization** - Interactive charts with EMA smoothing and comparison
- 🌐 **Remote Viewer** - VSCode-style remote access via SSH tunnel (v0.5.0+)
- ⚡ **High Performance** - LTTB downsampling, incremental caching (v0.5.2+)
- 💻 **Cross-Platform** - Python SDK + Web UI + Desktop App (Windows)

---

## Quick Links

<div class="grid cards" markdown>

-   :material-clock-fast:{ .lg .middle } __Quick Start__

    ---

    Get up and running in 5 minutes

    [:octicons-arrow-right-24: Quick Start](getting-started/quickstart.md)

-   :material-code-braces:{ .lg .middle } __Python SDK__

    ---

    Track experiments with simple Python API

    [:octicons-arrow-right-24: SDK Guide](sdk/overview.md)

-   :material-console:{ .lg .middle } __CLI Reference__

    ---

    Command-line tools and utilities

    [:octicons-arrow-right-24: CLI Docs](cli/overview.md)

-   :material-web:{ .lg .middle } __Web Interface__

    ---

    Explore the web viewer and UI features

    [:octicons-arrow-right-24: CLI Guide](cli/overview.md)

</div>

---

## Who is Runicorn For?

### ML Researchers

Track experiments, compare hyperparameters, and manage model versions without sending data to external services.

**Use cases**: Academic research, private datasets, air-gapped environments

### ML Engineers

Production model management with version control, lineage tracking, and deployment workflows.

**Use cases**: Model registry, A/B testing, production deployment

### Data Scientists

Organize exploratory experiments, visualize results, and export findings for reports.

**Use cases**: Data analysis, experiment documentation, stakeholder reporting

### Teams

Collaborate locally or sync from shared servers while keeping full control of your data.

**Use cases**: Lab servers, on-premise infrastructure, team collaboration

---

## Why Choose Runicorn?

### vs. Weights & Biases

| Feature | W&B | Runicorn |
|---------|-----|----------|
| **Privacy** | Cloud-based | 100% local |
| **Cost** | $50+/user/month | Free & open-source |
| **Offline** | Requires internet | Fully offline |
| **Data ownership** | Stored on W&B servers | You own all data |
| **Setup** | Account required | `pip install` |
| **Versioning** | ✓ | ✓ (Artifacts system) |
| **Visualization** | ✓✓✓ | ✓✓ |
| **Team features** | ✓✓✓ | ✓ (via remote sync) |

### vs. TensorBoard

| Feature | TensorBoard | Runicorn |
|---------|-------------|----------|
| **UI** | Basic | Modern (Ant Design) |
| **Experiment comparison** | Limited | Full multi-run overlay |
| **Model versioning** | ✗ | ✓ (Built-in) |
| **Status tracking** | ✗ | ✓ (Auto-detect crashes) |
| **Remote sync** | ✗ | ✓ (SSH mirror) |
| **Storage** | Event files | Hybrid (SQLite + files) |

### vs. MLflow

| Feature | MLflow | Runicorn |
|---------|--------|----------|
| **Setup complexity** | Medium | Low |
| **Performance** | Good | Excellent (10-500x faster queries) |
| **Model registry** | ✓ | ✓ (Artifacts) |
| **Deployment** | ✓✓✓ | ✓ |
| **Windows support** | Limited | Native |
| **Deduplication** | ✗ | ✓ (50-90% space saving) |

---

## Installation

```bash
pip install -U runicorn
```

**Requirements**: Python 3.8+

**Supported Platforms**: Windows, Linux, macOS

---

## 30-Second Demo

```python
import runicorn as rn
import random

# Initialize experiment
run = rn.init(project="demo", name="my_first_run")

# Set primary metric
run.set_primary_metric("accuracy", mode="max")

# Training loop
for step in range(1, 101):
    loss = 2.0 * (0.95 ** step) + random.uniform(-0.01, 0.01)
    acc = min(0.99, 0.5 + step * 0.005 + random.uniform(-0.02, 0.02))
    
    # Log metrics
    run.log({
        "loss": round(loss, 4),
        "accuracy": round(acc, 4)
    }, step=step)

# Finish
run.finish()
print(f"✓ Experiment saved: {run.id}")
```

**Then view results**:
```bash
runicorn viewer
# Open http://127.0.0.1:23300
```

---

## Next Steps

!!! tip "Recommended Learning Path"

    1. **[Quick Start Guide](getting-started/quickstart.md)** - Set up Runicorn in 5 minutes
    2. **[Python SDK Overview](sdk/overview.md)** - Learn the core functions
    3. **[Image Classification Tutorial](tutorials/image-classification.md)** - Complete example
    4. **[FAQ](reference/faq.md)** - Frequently asked questions

---

## Features Showcase

### Experiment Tracking

```python
import runicorn as rn

run = rn.init(project="image_classification", name="resnet50_baseline")

for epoch in range(100):
    # Your training code
    train_loss = train_one_epoch(model, train_loader)
    val_acc = validate(model, val_loader)
    
    # Log metrics
    run.log({
        "train_loss": train_loss,
        "val_accuracy": val_acc,
        "learning_rate": optimizer.param_groups[0]['lr']
    }, step=epoch)

run.finish()
```

### Model Versioning

```python
import runicorn as rn

run = rn.init(project="production")

# Save model as versioned artifact
artifact = rn.Artifact("production-model", type="model")
artifact.add_file("model.pth")
artifact.add_metadata({"accuracy": 0.95, "f1_score": 0.93})

version = run.log_artifact(artifact)  # → v1, v2, v3...
print(f"Model saved as v{version}")

run.finish()

# Later: Load the model
run2 = rn.init(project="inference")
model_artifact = run2.use_artifact("production-model:latest")
model_path = model_artifact.download()
```

### Remote Viewer (v0.5.0+) 🌐

Train on remote GPU servers, view results locally in real-time with **zero file sync**:

```python
# On remote server (Linux)
import runicorn as rn

run = rn.init(
    project="training",
    storage="/data/runicorn"
)

# Training code...
run.log({"loss": 0.1})
run.finish()
```

**On your local machine**:

1. Open Web UI → **Remote** page
2. Enter SSH credentials (host, username, key/password)
3. Select Python environment with Runicorn installed
4. Click **Start Viewer** → Remote Viewer launches on server
5. View experiments instantly via SSH tunnel!

!!! tip "VSCode Remote-style Architecture"
    Unlike file sync, Remote Viewer runs directly on your remote server. Data never leaves the server — only the UI is tunneled to your local browser. Latency < 100ms!

---

## Community & Support

- 📖 **Documentation**: You're reading it!
- 💬 **Issues**: [GitHub Issues](https://github.com/yourusername/runicorn/issues)
- 🔒 **Security**: [Report vulnerabilities](https://github.com/yourusername/runicorn/security)
- 🤝 **Contributing**: [Contribution Guide](https://github.com/yourusername/runicorn/blob/main/CONTRIBUTING.md)

---

## License

Runicorn is open-source software licensed under the **MIT License**.

---

<div align="center">
  <p>Made with ❤️ by the Runicorn Team</p>
  <p><a href="getting-started/quickstart.md">Get Started →</a></p>
</div>

