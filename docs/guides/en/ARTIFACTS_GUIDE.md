[English](ARTIFACTS_GUIDE.md) | [简体中文](../zh/ARTIFACTS_GUIDE.md)

---

# Runicorn Artifacts User Guide

> **Version**: v0.3.1+  
> **Feature**: Model and Dataset Version Control

---

## 📦 What are Artifacts?

Artifacts are Runicorn's version control system for managing machine learning assets, including:
- **Models** - PyTorch, TensorFlow, ONNX model files
- **Datasets** - Training/validation/test data
- **Configs** - Model configurations, hyperparameter files
- **Code** - Training scripts, custom code
- **Custom** - Any other files

---

## 🚀 Quick Start

### 1. Save Model

```python
import runicorn as rn

# Train model
run = rn.init(project="image_classification", name="resnet50_v1")

# ... training code ...
# torch.save(model.state_dict(), "model.pth")

# Create artifact
model = rn.Artifact("resnet50-model", type="model")
model.add_file("model.pth")
model.add_metadata({
    "architecture": "ResNet50",
    "val_acc": 0.95,
    "epochs": 100
})

# Save (automatic version control)
version = run.log_artifact(model)  # → v1
print(f"Saved model: resnet50-model:v{version}")

rn.finish()
```

### 2. Use Model

```python
import runicorn as rn

# Inference run
run = rn.init(project="inference")

# Load latest version
artifact = run.use_artifact("resnet50-model:latest")
model_path = artifact.download()

# Use model
# model.load_state_dict(torch.load(model_path / "model.pth"))

rn.finish()
```

---

## 📚 Complete Features

### Adding Files

```python
artifact = rn.Artifact("my-model", type="model")

# Add single file
artifact.add_file("model.pth")

# Add with rename
artifact.add_file("checkpoint.pth", name="model.pth")

# Add entire directory
artifact.add_dir("checkpoints/")

# Add directory with exclusions
artifact.add_dir("checkpoints/", exclude_patterns=["*.log", "*.tmp"])
```

### Adding Metadata

```python
artifact = rn.Artifact("my-model", type="model")
artifact.add_file("model.pth")

# Add metadata (any JSON data)
artifact.add_metadata({
    "architecture": "ResNet50",
    "val_acc": 0.95,
    "val_loss": 0.23,
    "epochs": 100,
    "optimizer": "Adam",
    "learning_rate": 0.001,
    "batch_size": 64,
    "notes": "Best model from hyperparameter sweep"
})

# Add tags
artifact.add_tags("production", "resnet", "imagenet")

run.log_artifact(artifact)
```

### External References (Large Datasets)

```python
# For very large datasets, don't copy, just record reference
dataset = rn.Artifact("imagenet-full", type="dataset")
dataset.add_reference(
    uri="s3://my-bucket/imagenet-full",
    checksum="sha256:abc123...",
    size=150_000_000_000  # 150 GB
)
dataset.add_metadata({
    "num_samples": 1_281_167,
    "num_classes": 1000
})

run.log_artifact(dataset)
```

---

## 🔍 Query and Usage

### Use Specific Version

```python
# Use latest version
artifact = run.use_artifact("my-model:latest")

# Use specific version number
artifact = run.use_artifact("my-model:v3")

# Use alias (if set)
artifact = run.use_artifact("my-model:production")
```

### Download Files

```python
# Download to temp directory
artifact = run.use_artifact("my-model:latest")
model_dir = artifact.download()  # Returns temp directory path
model_file = model_dir / "model.pth"

# Download to specific directory
model_dir = artifact.download(target_dir="./models")
```

### Get Metadata

```python
artifact = run.use_artifact("my-model:latest")

# Get metadata object
metadata = artifact.get_metadata()
print(f"Accuracy: {metadata.metadata['val_acc']}")
print(f"Created: {metadata.created_at}")
print(f"Size: {metadata.size_bytes} bytes")

# Get file manifest
manifest = artifact.get_manifest()
print(f"Files: {manifest.total_files}")
for file in manifest.files:
    print(f"  {file.path} ({file.size} bytes)")
```

---

## 🔗 Lineage Tracking

Runicorn automatically tracks dependencies between artifacts:

```python
# Run 1: Prepare dataset
run1 = rn.init(project="training", name="data_prep")
dataset = rn.Artifact("my-dataset", type="dataset")
dataset.add_dir("data/")
run1.log_artifact(dataset)  # → my-dataset:v1
rn.finish()

# Run 2: Train model using dataset
run2 = rn.init(project="training", name="model_train")
dataset = run2.use_artifact("my-dataset:v1")  # Automatically recorded
# Training...
model = rn.Artifact("my-model", type="model")
model.add_file("model.pth")
run2.log_artifact(model)  # → my-model:v1
rn.finish()

# System automatically records lineage:
# my-dataset:v1 → run2 → my-model:v1
```

View complete lineage graph in Web UI.

---

## 🖥️ Web UI Features

### Artifacts Page

Visit `http://127.0.0.1:23300/artifacts` to:

1. **Browse all artifacts**
   - Filter by type (models, datasets, etc.)
   - Search artifact names
   - View statistics

2. **View version history**
   - List all versions
   - Version comparison
   - Creation time and creator

3. **File management**
   - View included files
   - File sizes and hashes
   - External references

4. **Lineage visualization**
   - Graphical dependency display
   - Upstream dependencies (inputs)
   - Downstream usage (outputs)

---

## 💻 CLI Commands

### List All Artifacts

```bash
$ runicorn artifacts --action list
Found 5 artifact(s):

Name                           Type       Versions   Size            Latest    
-------------------------------------------------------------------------------------
resnet50-model                 model      3          98.23 MB   v3
bert-base-finetuned            model      2          420.15 MB  v2
imagenet-subset                dataset    1          5120.00 MB v1
```

### View Version History

```bash
$ runicorn artifacts --action versions --name resnet50-model
Versions for resnet50-model:

Version    Created                   Size            Files    Run
------------------------------------------------------------------------------------------
v1         2025-09-01 10:30:15       97.50 MB   1        20250901_103015_abc123
v2         2025-09-15 14:22:33       98.00 MB   1        20250915_142233_def456
v3         2025-09-30 16:45:12       98.23 MB   1        20250930_164512_ghi789
```

### View Detailed Information

```bash
$ runicorn artifacts --action info --name resnet50-model --version 3
Artifact: resnet50-model:v3
============================================================
Type:         model
Status:       ready
Created:      2025-09-30 16:45:12
Created by:   20250930_164512_ghi789
Size:         98.23 MB
Files:        1
Aliases:      latest, production

Metadata:
  architecture: ResNet50
  val_acc: 0.95
  epochs: 100
  optimizer: AdamW

Files (1):
  model.pth (98.2 MB)
```

### View Storage Statistics

```bash
$ runicorn artifacts --action stats
Artifact Storage Statistics
============================================================
Total Artifacts:  5
Total Versions:   12
Total Size:       6.8 GB
Dedup Enabled:    True

Deduplication Stats:
  Pool Size:      5.2 GB
  Space Saved:    1.6 GB
  Dedup Ratio:    23.5%

By Type:
  Model      3 artifacts, 8 versions, 1.2 GB
  Dataset    2 artifacts, 4 versions, 5.6 GB
```

### Delete Version

```bash
# Soft delete (recoverable)
$ runicorn artifacts --action delete --name old-model --version 1
Delete old-model:v1? [y/N] y
✅ Soft deleted old-model:v1

# Permanent delete
$ runicorn artifacts --action delete --name old-model --version 1 --permanent
```

---

## 🎯 Best Practices

### 1. Naming Conventions

```python
# Good naming
rn.Artifact("resnet50-imagenet", type="model")
rn.Artifact("mnist-augmented", type="dataset")
rn.Artifact("training-config", type="config")

# Avoid
rn.Artifact("model", type="model")  # Too generic
rn.Artifact("final_final_v2", type="model")  # Confusing
```

### 2. Metadata Standards

```python
# Typical model metadata
model.add_metadata({
    "architecture": "ResNet50",
    "val_acc": 0.95,
    "val_loss": 0.23,
    "epochs": 100,
    "optimizer": "Adam",
    "learning_rate": 0.001,
    "batch_size": 64,
    "dataset": "imagenet-subset:v2",  # Link to dataset
    "framework": "pytorch",
    "framework_version": "2.0.0"
})

# Typical dataset metadata
dataset.add_metadata({
    "num_samples": 50000,
    "num_classes": 10,
    "split_ratio": "0.8/0.2",
    "preprocessing": "normalize + augmentation",
    "augmentation": "flip + crop + color_jitter"
})
```

### 3. Version Management Strategy

```python
# Development phase: Frequent saves
run = rn.init(project="dev", name="experiment_123")
model = rn.Artifact("dev-model", type="model")
model.add_file("checkpoint.pth")
run.log_artifact(model)  # v1, v2, v3, ...

# Production phase: Use aliases
# TODO: Alias feature to be implemented
# artifact.alias("production")  # Mark production version
```

### 4. Large File Optimization

```python
# For very large datasets (>10 GB)
dataset = rn.Artifact("huge-dataset", type="dataset")

# Method 1: External reference (no download)
dataset.add_reference("s3://bucket/data", checksum="sha256:...")

# Method 2: Chunked upload (future feature)
# dataset.add_dir("data/", chunk_size="1GB")
```

---

## 🔍 Troubleshooting

### Issue 1: "Artifacts system is not available"

**Cause**: Artifacts module not loaded properly

**Solution**:
```bash
# Check Python path
python -c "import runicorn.artifacts; print('OK')"

# Reinstall
pip install --upgrade runicorn
```

### Issue 2: FileNotFoundError

**Cause**: File path doesn't exist

**Solution**:
```python
# Use absolute path
from pathlib import Path
model_path = Path("model.pth").resolve()
artifact.add_file(str(model_path))
```

### Issue 3: Low Disk Space

**Cause**: Multiple versions consuming space

**Solution**:
```bash
# View statistics
$ runicorn artifacts --action stats

# Delete old versions
$ runicorn artifacts --action delete --name old-model --version 1 --permanent

# Cleanup orphaned dedup files (future feature)
# $ runicorn artifacts --action cleanup-dedup
```

---

## 📊 Web UI Usage

### Access Artifacts Page

1. Start viewer: `runicorn viewer`
2. Open browser: `http://127.0.0.1:23300`
3. Click "Artifacts" in top menu

### Features

#### Artifacts List
- View all saved models and datasets
- Statistics cards showing totals, size, dedup savings
- Filter by type
- Search functionality

#### Artifact Details
- **Info tab**: Basic info, metadata, tags
- **Files tab**: File list, external references
- **Version History tab**: All version history
- **Lineage tab**: Dependency graph

#### Version Comparison (future feature)
- Compare two versions
- View metadata changes
- View file changes

---

## 🔗 Lineage Tracking Example

### Complete Workflow

```python
# Step 1: Prepare dataset
run_data = rn.init(project="ml_pipeline", name="data_prep")
dataset = rn.Artifact("processed-data", type="dataset")
dataset.add_dir("processed_data/")
dataset.add_metadata({"num_samples": 10000})
run_data.log_artifact(dataset)  # → processed-data:v1
rn.finish()

# Step 2: Train model
run_train = rn.init(project="ml_pipeline", name="training")
dataset = run_train.use_artifact("processed-data:v1")  # Auto-tracked
data_path = dataset.download()

# Training...
model = rn.Artifact("trained-model", type="model")
model.add_file("model.pth")
model.add_metadata({"trained_with": "processed-data:v1"})
run_train.log_artifact(model)  # → trained-model:v1
rn.finish()

# Step 3: Model evaluation
run_eval = rn.init(project="ml_pipeline", name="evaluation")
model = run_eval.use_artifact("trained-model:v1")  # Auto-tracked
# Evaluation...
rn.finish()

# Lineage (automatically generated):
# processed-data:v1 → run_train → trained-model:v1 → run_eval
```

### View Lineage Graph in Web UI

1. Go to Artifacts page
2. Click `trained-model`
3. Switch to "Lineage" tab
4. Click "Load Lineage Graph"
5. View graphical dependencies

---

## 💾 Storage Structure

```
user_root_dir/
├── artifacts/                          # Artifacts root
│   ├── models/                         # Model type
│   │   └── resnet50-model/             # Artifact name
│   │       ├── versions.json           # Version index
│   │       ├── v1/                     # Version 1
│   │       │   ├── files/              # Actual files
│   │       │   │   └── model.pth
│   │       │   ├── metadata.json       # Version metadata
│   │       │   └── manifest.json       # File manifest
│   │       ├── v2/                     # Version 2
│   │       └── v3/                     # Version 3
│   ├── datasets/                       # Dataset type
│   │   └── imagenet-subset/
│   │       └── ...
│   └── .dedup/                         # Dedup storage pool
│       └── a1/
│           └── a1b2c3d4.../            # Stored by hash
├── <project>/
│   └── <name>/
│       └── runs/
│           └── <run_id>/
│               ├── artifacts_used.json     # Artifacts used by this run
│               └── artifacts_created.json  # Artifacts created by this run
```

---

## ⚡ Performance Optimization

### Content Deduplication

Runicorn automatically deduplicates identical file content:

```
Scenario: Save 10 model versions, 1 GB each, 10% actual changes

Without dedup: 10 GB disk usage
With dedup:    ~1.5 GB disk usage
Savings:       85%
```

### Hard Links

Identical content files use hard links, zero extra space:

```
v1/files/model.pth  ─┐
v2/files/model.pth  ─┼─> .dedup/a1b2c3.../  (actual file)
v3/files/model.pth  ─┘

Three versions, only one copy on disk
```

---

## 📖 More Examples

See complete examples:
- `examples/test_artifacts.py` - Complete workflow demo
- Quick Start Guide in Web UI

---

## 🔮 Future Features (Planned)

- [ ] Alias management (production, staging, etc.)
- [ ] Version comparison tool
- [ ] Incremental upload (only transfer changes)
- [ ] Compressed storage
- [ ] Cloud integration (optional S3/OSS sync)
- [ ] Artifact search
- [ ] Artifact export/import

---

## 📝 Summary

Runicorn Artifacts provides:
- ✅ **Fully local** version control
- ✅ **Automatic deduplication** saves space
- ✅ **Lineage tracking** ensures reproducibility
- ✅ **Simple API** easy to use
- ✅ **Zero cost** forever free

Suitable for:
- Projects requiring model version management
- Research needing dataset version control
- Production deployments requiring complete lineage tracking
- Privacy-sensitive scenarios

---

**Documentation Updated**: 2025-09-30  
**Related Docs**: [README](../README.md), [Architecture](../../reference/en/ARCHITECTURE.md)

