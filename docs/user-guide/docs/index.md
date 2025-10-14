# Runicorn User Guide

<div align="center">
  <img src="assets/logo.png" alt="Runicorn Logo" width="200">
  <p><strong>Local ML Experiment Tracking & Model Versioning</strong></p>
  <p>100% Offline • Privacy-First • Self-Hosted</p>
</div>

---

## What is Runicorn?

**Runicorn** is a local, open-source experiment tracking and visualization platform designed for machine learning researchers and engineers. Think of it as a **self-hosted alternative to Weights & Biases** that runs entirely on your computer.

### Key Features

- 🏠 **100% Local** - All data stays on your machine, complete privacy
- 📦 **Model Versioning** - Git-like version control for ML models and datasets
- 📊 **Beautiful Visualization** - Interactive charts and experiment comparison
- 🔄 **Remote Sync** - Mirror experiments from remote training servers via SSH
- 💻 **Cross-Platform** - Python SDK + Web UI + Desktop App (Windows)
- ⚡ **High Performance** - SQLite backend, handles 10,000+ experiments

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

    [:octicons-arrow-right-24: UI Guide](ui/overview.md)

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
rn.set_primary_metric("accuracy", mode="max")

# Training loop
for step in range(1, 101):
    loss = 2.0 * (0.95 ** step) + random.uniform(-0.01, 0.01)
    acc = min(0.99, 0.5 + step * 0.005 + random.uniform(-0.02, 0.02))
    
    # Log metrics
    rn.log({
        "loss": round(loss, 4),
        "accuracy": round(acc, 4)
    }, step=step)

# Finish
rn.finish()
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
    2. **[Your First Experiment](getting-started/first-experiment.md)** - Track a real ML experiment
    3. **[Python SDK Overview](sdk/overview.md)** - Learn the core functions
    4. **[Model Versioning Tutorial](tutorials/model-versioning.md)** - Version control for models

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
    rn.log({
        "train_loss": train_loss,
        "val_accuracy": val_acc,
        "learning_rate": optimizer.param_groups[0]['lr']
    }, step=epoch)

rn.finish()
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

rn.finish()

# Later: Load the model
run2 = rn.init(project="inference")
model_artifact = run2.use_artifact("production-model:latest")
model_path = model_artifact.download()
```

### Remote Synchronization

Train on a powerful remote server, view results locally in real-time:

```python
# On remote server (Linux)
import runicorn as rn

run = rn.init(
    project="training",
    storage="/data/runicorn"  # Shared storage
)

# Training code...
rn.log({"loss": 0.1})
rn.finish()
```

**On your local machine**: Use the Web UI to connect via SSH and sync experiments automatically. No need to copy files manually!

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

