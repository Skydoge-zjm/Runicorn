# Frequently Asked Questions

Common questions and answers about Runicorn.

---

## General

### What is Runicorn?

Runicorn is a local, open-source experiment tracking and model versioning platform for machine learning. It provides tools to track experiments, manage model versions, and visualize results—all running on your own machine.

### Is Runicorn really free?

Yes! Runicorn is 100% free and open-source under the MIT license. No hidden costs, no premium tiers, no usage limits.

### Do I need to create an account?

No. Runicorn runs entirely on your local machine. No account, no registration, no cloud service required.

### Does Runicorn send data to external servers?

No. Runicorn has **zero telemetry**. All data stays on your machine.

### Can I use Runicorn offline?

Yes! After installation, Runicorn works completely offline.

---

## Installation & Setup

### What are the system requirements?

- **Python**: 3.8 or higher
- **OS**: Windows 10+, Linux (any), macOS 10.14+
- **RAM**: 2 GB minimum, 4 GB recommended
- **Disk**: 100 MB for software + storage for experiments

### How do I install Runicorn?

```bash
pip install -U runicorn
```

### Can I use Runicorn with conda?

Yes! Runicorn works in conda environments:

```bash
conda create -n ml python=3.10
conda activate ml
pip install runicorn
```

### Where does Runicorn store data?

By default, data is stored in:

1. User-configured path (recommended): Set via `runicorn config --set-user-root "PATH"`
2. Environment variable `RUNICORN_DIR`
3. Current directory `./.runicorn/`

### How do I change the storage location?

**Method 1** (Web UI):
1. Open viewer: `runicorn viewer`
2. Click ⚙️ Settings → Data Directory
3. Enter path and click Save

**Method 2** (CLI):
```bash
runicorn config --set-user-root "E:\RunicornData"
```

---

## Usage

### Do I need to modify my training code?

Minimal changes required:

```python
# Add 4 lines to your code:
import runicorn as rn

run = rn.init(project="demo")           # Line 1: Initialize
rn.log({"loss": 0.1}, step=1)           # Line 2: Log metrics
rn.finish()                             # Line 3: Finish
```

### Can I use Runicorn with TensorFlow?

Yes! Runicorn is framework-agnostic:

```python
import runicorn as rn
import tensorflow as tf

run = rn.init(project="tf_demo")

# Your TensorFlow code
model = tf.keras.Sequential([...])
model.compile(...)

for epoch in range(10):
    history = model.fit(x_train, y_train)
    
    # Log TensorFlow metrics
    rn.log({
        "loss": history.history['loss'][0],
        "accuracy": history.history['accuracy'][0]
    }, step=epoch)

rn.finish()
```

### Can I use Runicorn with scikit-learn?

Yes!

```python
import runicorn as rn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

run = rn.init(project="sklearn_demo")

# Train model
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Evaluate and log
accuracy = accuracy_score(y_test, model.predict(X_test))
rn.log({"accuracy": accuracy})

rn.summary({"model": "RandomForest", "final_accuracy": accuracy})
rn.finish()
```

### How do I view my experiments?

Start the web viewer:

```bash
runicorn viewer
```

Then open [http://127.0.0.1:23300](http://127.0.0.1:23300) in your browser.

### Can I access the viewer from another computer?

Yes, bind to all interfaces:

```bash
runicorn viewer --host 0.0.0.0 --port 8000
```

Then access from other computers: `http://YOUR_IP:8000`

!!! warning "Security Warning"
    Only do this on trusted networks! The API has no authentication.

---

## Artifacts & Model Versioning

### What are Artifacts?

Artifacts are versioned ML assets (models, datasets, configs). Think of it as **Git for machine learning files**.

### How do I save a model as an artifact?

```python
import runicorn as rn

run = rn.init(project="demo")

# Save your model file
torch.save(model.state_dict(), "model.pth")

# Create artifact
artifact = rn.Artifact("my-model", type="model")
artifact.add_file("model.pth")
artifact.add_metadata({"accuracy": 0.95})

# Save with version control
version = run.log_artifact(artifact)  # Returns v1, v2, v3...
print(f"Model saved as v{version}")

rn.finish()
```

### How do I load a saved model?

```python
import runicorn as rn

run = rn.init(project="inference")

# Load artifact
artifact = run.use_artifact("my-model:latest")  # Or "my-model:v3"
model_path = artifact.download()

# Load model
import torch
state_dict = torch.load(model_path / "model.pth")
model.load_state_dict(state_dict)

rn.finish()
```

### How much storage does Runicorn use?

Runicorn uses **content deduplication** to save 50-90% storage:

- **Without dedup**: 100 model checkpoints × 1 GB = 100 GB
- **With dedup**: ~10-20 GB (similar models share common layers)

Check your stats:

```bash
runicorn artifacts --action stats
```

### Can I delete old artifact versions?

Yes:

**Soft delete** (reversible):
```bash
runicorn artifacts --action delete --name old-model --version 1
```

**Permanent delete**:
```bash
runicorn artifacts --action delete --name old-model --version 1 --permanent
```

---

## Remote Sync

### How do I sync from a remote server?

**Step 1**: Start viewer
```bash
runicorn viewer
```

**Step 2**: Open web UI and go to "Remote" page

**Step 3**: Enter SSH credentials:
- Host: `192.168.1.100`
- Username: `your_username`
- Password or SSH key

**Step 4**: Browse remote directories and click "Configure Smart Mode"

**Step 5**: Experiments sync automatically!

### Do I need to install Runicorn on the remote server?

Yes, install Runicorn on the remote server where you train models:

```bash
# On remote server
pip install runicorn
```

Then use Runicorn SDK in your training scripts:

```python
import runicorn as rn

run = rn.init(
    project="training",
    storage="/data/runicorn"  # Shared storage path
)

# Training code...
rn.log({"loss": 0.1})
rn.finish()
```

### What's the difference between Smart Mode and Mirror Mode?

**Smart Mode** (recommended):
- Syncs metadata only
- Downloads files on-demand
- Fast, low bandwidth

**Mirror Mode**:
- Syncs all files
- Real-time updates (2-second interval)
- Higher bandwidth usage

---

## Performance

### Why is listing experiments slow?

If you have 1000+ experiments, use the **V2 API** for 100x faster queries.

**Check your query performance**:
- Open browser DevTools → Network tab
- Look at API call times
- If `/api/runs` takes >5s, you need V2

**Solution**: Frontend automatically uses V2 API when available.

### How many experiments can Runicorn handle?

Tested with:
- ✅ **10,000 experiments**: Excellent performance
- ✅ **100,000 experiments**: Good performance (use V2 API)
- ⚠️ **1,000,000 experiments**: Possible but may require optimization

### Does Runicorn support distributed training?

Yes! Use Runicorn in your distributed training script:

```python
import runicorn as rn
import torch.distributed as dist

# Initialize experiment on rank 0 only
if dist.get_rank() == 0:
    run = rn.init(project="distributed_training")
    
    # Log from master process
    rn.log({"train_loss": loss})
    
    # Finish on master process
    rn.finish()
```

---

## Compatibility

### Which ML frameworks does Runicorn support?

Runicorn is **framework-agnostic**. Works with:

- ✅ PyTorch
- ✅ TensorFlow / Keras
- ✅ JAX
- ✅ scikit-learn
- ✅ XGBoost, LightGBM
- ✅ Hugging Face Transformers
- ✅ FastAI
- ✅ Any Python-based framework

### Can I use Runicorn with Jupyter Notebooks?

Yes!

```python
# In Jupyter cell
import runicorn as rn

run = rn.init(project="notebook_demo")

# Your notebook code
# ...

rn.log({"accuracy": 0.95})
rn.finish()

print(f"View results: http://127.0.0.1:23300/runs/{run.id}")
```

### Does Runicorn work with GPU training?

Yes! Runicorn can monitor GPU usage in real-time (requires `nvidia-smi`).

GPU monitoring is automatic—just train your model and check the GPU panel in the web UI.

---

## Data & Privacy

### Can I export my data?

Yes, multiple export formats:

```bash
# Export experiments (full data)
runicorn export --project demo --out demo.tar.gz

# Export metrics only (CSV)
runicorn export-data --run-id <ID> --format csv --output metrics.csv

# Export metrics (Excel with charts)
runicorn export-data --run-id <ID> --format excel --output report.xlsx
```

### Can I delete experiments?

Yes, with **soft delete** (recycle bin):

**Web UI**:
1. Select experiments
2. Click "Delete" button
3. Experiments move to Recycle Bin
4. Restore from Recycle Bin if needed

**CLI**:
```bash
# Soft delete via API requires custom script
# Or use Web UI for deletion
```

**Permanent deletion**:
- Empty Recycle Bin in Web UI
- Or manually delete run directories

### How do I backup my data?

**Method 1**: Export to archive
```bash
runicorn export --out backup_$(date +%Y%m%d).tar.gz
```

**Method 2**: Copy storage directory
```bash
# Stop viewer first
cp -r $RUNICORN_DIR /path/to/backup/
```

**Method 3**: Version control (Git LFS)
```bash
cd $RUNICORN_DIR
git init
git lfs track "*.pth" "*.h5"
git add .
git commit -m "Backup"
```

---

## Troubleshooting

### Viewer won't start

**Check**:
1. Is Python 3.8+ installed? `python --version`
2. Is Runicorn installed? `pip list | grep runicorn`
3. Is port 23300 available? Try: `runicorn viewer --port 8080`

### Experiments don't appear in viewer

**Check**:
1. Correct storage root? `runicorn config --show`
2. Experiments in correct location? Check directory structure
3. Try refresh button in web UI

### Database locked (Windows)

If you see "database is locked" errors:

```bash
# Stop viewer
# Wait 5 seconds
# Restart viewer
runicorn viewer
```

**Prevention**: Always stop viewer gracefully (Ctrl+C)

### Out of disk space

Check artifact storage stats:

```bash
runicorn artifacts --action stats
```

**Cleanup options**:
1. Delete old artifact versions
2. Empty recycle bin
3. Export and archive old experiments

---

## Migration & Integration

### Can I migrate from TensorBoard?

There's no automatic migration, but you can:

1. Keep using TensorBoard for old experiments
2. Start using Runicorn for new experiments
3. Gradually migrate important experiments manually

### Can I use both Runicorn and W&B?

Yes! Use both:

```python
import runicorn as rn
import wandb

# Initialize both
rn_run = rn.init(project="demo")
wandb.init(project="demo")

# Log to both
metrics = {"loss": 0.1, "accuracy": 0.95}
rn.log(metrics)
wandb.log(metrics)

# Finish both
rn.finish()
wandb.finish()
```

### Can I export to TensorBoard format?

The Python SDK includes an exporter:

```python
from runicorn import MetricsExporter

exporter = MetricsExporter(run.run_dir)

# Export to TensorBoard-compatible format (planned feature)
# Currently supported: CSV, Excel, Markdown
exporter.to_csv("metrics.csv")
```

---

## Advanced

### Can I customize the web UI?

Yes, through Settings (⚙️ icon):

- Theme (light/dark/auto)
- Accent color
- Background (gradient/image/solid)
- Chart height and animations
- And more...

All settings persist in browser localStorage.

### Can I access Runicorn from Python scripts?

Yes! Use the REST API:

```python
import requests

# List experiments
response = requests.get('http://127.0.0.1:23300/api/runs')
experiments = response.json()

for exp in experiments:
    print(f"{exp['id']}: {exp['status']}")
```

See [API Documentation](../../api/README.md) for details.

### Can I run multiple viewers?

Yes, on different ports:

```bash
# Terminal 1
runicorn viewer --storage "E:\Project1" --port 23300

# Terminal 2
runicorn viewer --storage "E:\Project2" --port 23301
```

---

## Still Have Questions?

- 📖 Check [Glossary](glossary.md) for terminology
- 🔧 See [Troubleshooting Guide](../guides/troubleshooting.md)
- 💬 Ask on [GitHub Discussions](https://github.com/yourusername/runicorn/discussions)
- 🐛 [Report bugs](https://github.com/yourusername/runicorn/issues)

---

<div align="center">
  <p><strong>Can't find your answer?</strong></p>
  <p><a href="https://github.com/yourusername/runicorn/discussions">Ask the Community →</a></p>
</div>

