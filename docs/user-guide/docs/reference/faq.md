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

- **Python**: 3.10 or higher
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

run = rn.init(path="demo")              # Line 1: Initialize
run.log({"loss": 0.1}, step=1)          # Line 2: Log metrics
run.finish()                            # Line 3: Finish
```

### Can I use Runicorn with TensorFlow?

Yes! Runicorn is framework-agnostic:

```python
import runicorn as rn
import tensorflow as tf

run = rn.init(path="tf_demo")

# Your TensorFlow code
model = tf.keras.Sequential([...])
model.compile(...)

for epoch in range(10):
    history = model.fit(x_train, y_train)
    
    # Log TensorFlow metrics
    run.log({
        "loss": history.history['loss'][0],
        "accuracy": history.history['accuracy'][0]
    }, step=epoch)

run.finish()
```

### Can I use Runicorn with scikit-learn?

Yes!

```python
import runicorn as rn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

run = rn.init(path="sklearn_demo")

# Train model
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Evaluate and log
accuracy = accuracy_score(y_test, model.predict(X_test))
run.log({"accuracy": accuracy})

run.summary({"model": "RandomForest", "final_accuracy": accuracy})
run.finish()
```

### How do I use console capture? <span class="rn-badge">v0.6.0</span>

```python
import runicorn as rn

run = rn.init(path="demo", capture_console=True)
print("Training started...")  # Captured to logs.txt
run.finish()
```

Control tqdm capture with `tqdm_mode`: `"smart"` (default, final state only), `"all"`, or `"none"`.

See [Enhanced Logging Guide](../getting-started/enhanced-logging.md) for Python logging handler integration.

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

## Assets & Storage

### What is the Assets System?

The Assets System <span class="rn-badge">v0.6.0</span> provides SHA256 content-addressed storage for workspace snapshots and files, with automatic deduplication (50-90% space savings).

### How do I snapshot my workspace code?

```python
import runicorn as rn

run = rn.init(path="demo", snapshot_code=True)
# Training code...
run.finish()
# Workspace snapshot saved automatically
```

See [Assets System Guide](../getting-started/assets-system.md) for manual snapshots and blob storage.

### How much storage does Runicorn use?

Runicorn uses **SHA256 content deduplication** — identical files are stored only once.

Typical savings:

- **50–70%** for regular projects
- **80–90%** for projects with many checkpoints

```
Example: 10 experiments × 500MB = 5GB → Deduplicated: ~1GB
```

---

## Remote Viewer <span class="rn-badge">v0.5.0+</span>

### How do I view experiments on a remote server?

**v0.5.0** introduces **Remote Viewer** — a VSCode-style remote access feature:

**Step 1**: Start local viewer
```bash
runicorn viewer
```

**Step 2**: Open web UI → **Remote** page

**Step 3**: Enter SSH credentials:
- Host: `gpu-server.lab.com`
- Username: `your_username`
- Password or SSH key

**Step 4**: Select Python environment with Runicorn installed

**Step 5**: Click **Start Viewer** → Done!

!!! tip "No File Sync Needed"
    Remote Viewer runs directly on your server. Data never leaves the remote machine — only the UI is tunneled to your browser. Latency < 100ms!

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
    path="training",
    storage="/data/runicorn"  # Consistent storage path
)

# Training code...
run.log({"loss": 0.1})
run.finish()
```

### What's the difference between Remote Viewer and File Sync?

| Feature | Remote Viewer (v0.5.0+) | File Sync (deprecated) |
|---------|------------------------|------------------------|
| **Data Location** | Stays on server | Copied to local |
| **Initial Wait** | None (instant) | Minutes to hours |
| **Bandwidth** | Low (UI only) | High (all files) |
| **Privacy** | Data never leaves server | Data copied locally |
| **Real-time** | ✅ Yes | ⚠️ Delayed |

### Can I connect to multiple remote servers?

Yes! The Remote page supports multiple concurrent connections. Each connection can have its own Viewer instance.

---

## Performance

### Why is listing experiments slow?

If you have 1000+ experiments, use the **V2 API** for 100x faster queries.

**Check your query performance**:
- Open browser DevTools → Network tab
- Look at API call times
- If `/api/runs` takes >5s, you need V2

**Solution**: Frontend automatically uses V2 API when available.

### How do I handle experiments with 100k+ data points? <span class="rn-badge">v0.5.2+</span>

Use **LTTB downsampling**:

1. Go to **Settings** → **Charts**
2. Set **Max Data Points** (default: 2000)
3. Charts will automatically downsample while preserving visual accuracy

```bash
# API also supports explicit downsampling
GET /api/runs/{run_id}/metrics_step?downsample=2000
```

### Why are charts loading faster in v0.5.3?

v0.5.3 introduces several optimizations:

- **Lazy loading** — Charts only render when visible
- **Memo optimization** — Fewer unnecessary re-renders
- **Incremental cache** — Backend parses only new data

See [Performance Tips](../ui/performance.md) for details.

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
    run = rn.init(path="distributed_training")
    
    # Log from master process
    run.log({"train_loss": loss})
    
    # Finish on master process
    run.finish()
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

run = rn.init(path="notebook_demo")

# Your notebook code
# ...

run.log({"accuracy": 0.95})
run.finish()

print(f"View results: http://127.0.0.1:23300/runs/{run.id}")
```

### Does Runicorn work with GPU training?

Yes! Runicorn can monitor GPU usage in real-time (requires `nvidia-smi`).

GPU monitoring is automatic—just train your model and check the GPU panel in the web UI.

---

## Data & Privacy

### Can I export my data?

```bash
# Export metrics (CSV)
runicorn export-data --run-id <ID> --format csv --output metrics.csv

# Export metrics (Excel with charts)
runicorn export-data --run-id <ID> --format excel --output report.xlsx
```

### Can I delete experiments?

**Web UI** — Select experiments → Delete → Recycle Bin (recoverable). Empty Recycle Bin for permanent deletion.

**CLI** — Permanent deletion:
```bash
runicorn delete --run-id 20260115_100000_abc123 --dry-run   # Preview
runicorn delete --run-id 20260115_100000_abc123 --force      # Delete
```

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
1. Is Python 3.10+ installed? `python --version`
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

**Cleanup options**:
1. Delete old runs: `runicorn delete --run-id <ID> --force`
2. Empty recycle bin in Web UI
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
rn_run = rn.init(path="demo")
wandb.init(project="demo")

# Log to both
metrics = {"loss": 0.1, "accuracy": 0.95}
rn_run.log(metrics)
wandb.log(metrics)

# Finish both
rn_run.finish()
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

See the API documentation for details (visit `http://127.0.0.1:23300/docs` after starting viewer).

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

- [Python SDK Overview](../sdk/overview.md) — Programming guide
- [CLI Overview](../cli/overview.md) — Command-line usage
- [GitHub Discussions](https://github.com/Skydoge-zjm/Runicorn/discussions) — Ask the community
- [Report bugs](https://github.com/Skydoge-zjm/Runicorn/issues) — Issue tracker
