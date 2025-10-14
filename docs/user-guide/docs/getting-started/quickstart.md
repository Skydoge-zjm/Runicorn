# Quick Start

Get Runicorn up and running in 5 minutes!

---

## Installation

### Step 1: Install Runicorn

```bash
pip install -U runicorn
```

**Requirements**: Python 3.8 or higher

??? tip "Using conda?"
    ```bash
    conda create -n runicorn python=3.10
    conda activate runicorn
    pip install runicorn
    ```

### Step 2: Verify Installation

```bash
runicorn --version
```

You should see: `runicorn 0.4.0` (or later)

---

## Your First Experiment

### Step 1: Create a Simple Experiment

Create a file `demo.py`:

```python
import runicorn as rn
import random
import time

# Initialize experiment
run = rn.init(project="quickstart", name="demo_experiment")
print(f"✓ Created experiment: {run.id}")

# Set primary metric (optional)
rn.set_primary_metric("accuracy", mode="max")

# Training loop
for step in range(1, 51):
    # Simulate training
    loss = 2.0 * (0.9 ** step) + random.uniform(-0.05, 0.05)
    accuracy = min(0.98, 0.5 + step * 0.01 + random.uniform(-0.02, 0.02))
    
    # Log metrics
    rn.log({
        "loss": round(loss, 4),
        "accuracy": round(accuracy, 4),
        "learning_rate": 0.001
    }, step=step)
    
    # Simulate time passing
    time.sleep(0.1)
    
    # Print progress
    if step % 10 == 0:
        print(f"Step {step}/50: loss={loss:.4f}, acc={accuracy:.4f}")

# Save summary
rn.summary({
    "final_accuracy": 0.95,
    "total_steps": 50,
    "notes": "Demo experiment from quickstart guide"
})

# Finish experiment
rn.finish()
print("✓ Experiment completed!")
```

### Step 2: Run the Experiment

```bash
python demo.py
```

**Expected output**:
```
✓ Created experiment: 20250114_153045_a1b2c3
Step 10/50: loss=0.6974, acc=0.6234
Step 20/50: loss=0.2433, acc=0.7156
Step 30/50: loss=0.0849, acc=0.8089
Step 40/50: loss=0.0296, acc=0.8945
Step 50/50: loss=0.0103, acc=0.9567
✓ Experiment completed!
```

### Step 3: View Results

Start the web viewer:

```bash
runicorn viewer
```

**Open your browser**: [http://127.0.0.1:23300](http://127.0.0.1:23300)

You should see your experiment in the list!

---

## Explore the Web Interface

### 1. Experiments Page

<figure markdown>
  ![Experiments Page](../assets/screenshots/experiments-page.png)
  <figcaption>View all your experiments in one place</figcaption>
</figure>

**Features**:
- 📋 List all experiments
- 🔍 Filter by project/status
- 📊 View best metrics
- 🗑️ Soft delete (recycle bin)

### 2. Experiment Detail

Click on any experiment to see:

- 📈 **Interactive Charts** - Training curves with zoom/pan
- 📝 **Real-time Logs** - Live log streaming
- 🖼️ **Images** - Logged images and visualizations
- 💾 **Artifacts** - Associated models and datasets

### 3. Artifacts Page

<figure markdown>
  ![Artifacts Page](../assets/screenshots/artifacts-page.png)
  <figcaption>Manage model versions with Git-like workflow</figcaption>
</figure>

**Features**:
- 📦 List all models and datasets
- 🔄 Version history
- 🌳 Dependency graph (lineage)
- 💾 Storage statistics

---

## Configure Storage

### Set Storage Location

!!! warning "Important First Step"
    The first time you run Runicorn, configure where to store your data.

**Option 1: Web UI**

1. Click the ⚙️ Settings icon (top-right)
2. Go to "Data Directory" tab
3. Enter path: `E:\RunicornData` (or your preferred location)
4. Click "Save Data Directory"

**Option 2: Command Line**

```bash
runicorn config --set-user-root "E:\RunicornData"
```

**Option 3: Code**

```python
import runicorn as rn

run = rn.init(
    project="demo",
    storage="E:\\RunicornData"  # Explicit path
)
```

### Storage Priority

Runicorn determines storage location in this order:

1. `rn.init(storage="...")` - Highest priority
2. Environment variable `RUNICORN_DIR`
3. User config (set via UI/CLI)
4. `./runicorn/` in current directory - Lowest priority

---

## What's Next?

### Learn the Basics

- [📚 Your First Real Experiment](first-experiment.md) - Track a real ML model
- [⚙️ Configuration Guide](configuration.md) - Customize Runicorn
- [📖 Python SDK Overview](../sdk/overview.md) - Learn all SDK functions

### Advanced Features

- [📦 Model Versioning](../tutorials/model-versioning.md) - Version control for models
- [🔄 Remote Sync](../guides/sync-remote.md) - Connect to training servers
- [📊 Experiment Comparison](../guides/compare-experiments.md) - Compare multiple runs

### Tutorials

- [🖼️ Image Classification](../tutorials/image-classification.md) - Complete PyTorch example
- [💬 NLP Fine-tuning](../tutorials/nlp-finetuning.md) - BERT fine-tuning with artifacts
- [🎮 Multi-GPU Training](../tutorials/multi-gpu.md) - Distributed training tracking

---

## Getting Help

!!! question "Need help?"

    - 📖 Search this documentation
    - ❓ Check [FAQ](../reference/faq.md)
    - 🐛 [Report issues](https://github.com/yourusername/runicorn/issues)
    - 💬 Ask in [GitHub Discussions](https://github.com/yourusername/runicorn/discussions)

---

## System Requirements

| Component | Requirement |
|-----------|-------------|
| **Python** | 3.8, 3.9, 3.10, 3.11, 3.12, 3.13 |
| **OS** | Windows 10+, Linux (any), macOS 10.14+ |
| **RAM** | 2 GB minimum, 4 GB recommended |
| **Disk** | 100 MB for software + storage for your experiments |
| **GPU** | Optional (for GPU monitoring, requires `nvidia-smi`) |

---

<div align="center">
  <p><strong>Ready to dive deeper?</strong></p>
  <p><a href="first-experiment.md">Create Your First Real Experiment →</a></p>
</div>

