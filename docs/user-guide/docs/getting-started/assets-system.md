# Assets System Guide

**New in v0.6.0** - SHA256 content-addressed storage with automatic deduplication.

---

## Overview

Runicorn's Assets System provides:

1. **Workspace Snapshots** - Capture your entire workspace state
2. **Blob Storage** - Store individual files with deduplication
3. **Content Addressing** - SHA256-based storage (50-90% space savings)
4. **Restore Capability** - Recreate workspace from snapshots

---

## Quick Start

### Snapshot Your Workspace

Capture your entire workspace:

```python
import runicorn as rn

run = rn.init(project="demo")

# Snapshot workspace
manifest = rn.snapshot_workspace(
    run_id=run.id,
    include_patterns=["*.py", "*.yaml", "config/*"],
    exclude_patterns=["*.pyc", "__pycache__", ".git"]
)

print(f"Snapshot created: {len(manifest['files'])} files")

run.finish()
```

### Store Individual Files

Store specific files as blobs:

```python
import runicorn as rn

run = rn.init(project="demo")

# Store a file
blob_id = run.store_blob("model.pth")
print(f"Stored as blob: {blob_id}")

# Get blob path
blob_path = run.get_blob_path(blob_id)
print(f"Blob location: {blob_path}")

run.finish()
```

### Restore from Snapshot

Recreate workspace from a snapshot:

```python
import runicorn as rn

# Restore workspace
rn.restore_from_manifest(
    manifest_path=".runicorn/runs/20260115_100000_abc123/assets.json",
    target_dir="./restored_workspace"
)

print("Workspace restored successfully")
```

---

## .rnignore File

Control which files are included in snapshots using `.rnignore`:

**Create `.rnignore` in your project root**:
```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
.pytest_cache/

# Data
data/
*.csv
*.h5

# Models (large files)
*.pth
*.ckpt
*.safetensors

# IDE
.vscode/
.idea/
*.swp

# Git
.git/
.gitignore
```

**Usage**:
```python
import runicorn as rn

run = rn.init(project="demo")

# .rnignore is automatically respected
manifest = rn.snapshot_workspace(run_id=run.id)
# Files matching .rnignore patterns are excluded

run.finish()
```

---

## Complete Example

Here's a complete example with workspace snapshots:

```python
import runicorn as rn
import torch
import yaml

# Initialize
run = rn.init(
    project="image_classification",
    name="resnet50_experiment"
)

# Save configuration
config = {
    "model": "ResNet50",
    "epochs": 100,
    "batch_size": 32,
    "learning_rate": 0.001
}

with open("config.yaml", "w") as f:
    yaml.dump(config, f)

# Snapshot workspace before training
print("Creating pre-training snapshot...")
pre_manifest = rn.snapshot_workspace(
    run_id=run.id,
    include_patterns=["*.py", "*.yaml", "requirements.txt"],
    exclude_patterns=["*.pyc", "__pycache__"]
)

print(f"Snapshot: {len(pre_manifest['files'])} files")

# Training
model = torch.nn.Sequential(
    torch.nn.Linear(784, 128),
    torch.nn.ReLU(),
    torch.nn.Linear(128, 10)
)

for epoch in range(100):
    # Training code
    loss = train_one_epoch(model)
    run.log({"loss": loss}, step=epoch)

# Save model
torch.save(model.state_dict(), "model.pth")

# Store model as blob
print("Storing model...")
model_blob_id = run.store_blob("model.pth")
print(f"Model stored as: {model_blob_id}")

# Snapshot workspace after training
print("Creating post-training snapshot...")
post_manifest = rn.snapshot_workspace(
    run_id=run.id,
    include_patterns=["*.py", "*.yaml", "model.pth"],
    exclude_patterns=["*.pyc"]
)

# Save blob IDs to summary
run.summary({
    "model_blob_id": model_blob_id,
    "pre_training_files": len(pre_manifest['files']),
    "post_training_files": len(post_manifest['files'])
})

run.finish()
print(f"✓ Experiment completed: {run.id}")
```

---

## Deduplication

The Assets System automatically deduplicates files:

```python
import runicorn as rn

run1 = rn.init(project="demo", name="exp1")
run2 = rn.init(project="demo", name="exp2")

# Store same file twice
blob_id1 = run1.store_blob("config.yaml")
blob_id2 = run2.store_blob("config.yaml")

# Same content = same blob ID
assert blob_id1 == blob_id2

print(f"Blob ID: {blob_id1}")
print("File stored only once (deduplication)")

run1.finish()
run2.finish()
```

**Storage savings**:
- Typical projects: 50-70% space savings
- Projects with many checkpoints: 80-90% savings

---

## Best Practices

!!! tip "Tip: Use .rnignore"
    
    Always create a `.rnignore` file to exclude unnecessary files:
    
    ```gitignore
    __pycache__/
    *.pyc
    data/
    .git/
    ```

!!! tip "Tip: Snapshot at Key Points"
    
    Create snapshots at important milestones:
    
    ```python
    # Before training
    rn.snapshot_workspace(run_id=run.id)
    
    # After training
    train_model()
    rn.snapshot_workspace(run_id=run.id)
    
    # After evaluation
    evaluate_model()
    rn.snapshot_workspace(run_id=run.id)
    ```

!!! warning "Large Files"
    
    For very large files (>1GB), consider:
    
    - Using `.rnignore` to exclude them
    - Storing only checksums instead of full files
    - Using external storage (S3, NFS) and storing paths

---

## API Reference

### `snapshot_workspace()`

Capture workspace state.

**Signature**:
```python
def snapshot_workspace(
    run_id: str,
    workspace_root: str = ".",
    include_patterns: list[str] = None,
    exclude_patterns: list[str] = None
) -> dict
```

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | str | Run ID to associate snapshot with |
| `workspace_root` | str | Root directory to snapshot |
| `include_patterns` | list[str] | Glob patterns to include |
| `exclude_patterns` | list[str] | Glob patterns to exclude |

**Returns**: Manifest dictionary with file metadata

### `store_blob()`

Store a file as a blob.

**Signature**:
```python
def store_blob(file_path: str) -> str
```

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | str | Path to file to store |

**Returns**: Blob ID (SHA256 hash)

### `get_blob_path()`

Get path to a stored blob.

**Signature**:
```python
def get_blob_path(blob_id: str) -> str
```

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `blob_id` | str | Blob ID (SHA256 hash) |

**Returns**: Absolute path to blob file

### `restore_from_manifest()`

Restore workspace from snapshot.

**Signature**:
```python
def restore_from_manifest(
    manifest_path: str,
    target_dir: str = "."
) -> None
```

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `manifest_path` | str | Path to assets.json manifest |
| `target_dir` | str | Directory to restore to |

---

## Troubleshooting

### Snapshot too large?

**Use .rnignore to exclude files**:
```gitignore
data/
*.csv
*.h5
*.pth
```

### Deduplication not working?

**Check file content is identical**:
```python
import hashlib

def get_hash(file_path):
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

# Files must have identical content
hash1 = get_hash("file1.txt")
hash2 = get_hash("file2.txt")
print(f"Same content: {hash1 == hash2}")
```

### Restore failed?

**Check manifest path is correct**:
```python
import os

manifest_path = ".runicorn/runs/20260115_100000_abc123/assets.json"
print(f"Manifest exists: {os.path.exists(manifest_path)}")
```

---

## Migration from v0.5.x

If you're upgrading from v0.5.x:

**Before (v0.5.x)**:
```python
import runicorn as rn

run = rn.init(project="demo")

# Manual file copying
import shutil
shutil.copy("config.yaml", f".runicorn/runs/{run.id}/")

run.finish()
```

**After (v0.6.0)**:
```python
import runicorn as rn

run = rn.init(project="demo")

# Automatic snapshot with deduplication
manifest = rn.snapshot_workspace(run_id=run.id)

run.finish()
```

---

## Next Steps

- [Enhanced Logging Guide](enhanced-logging.md) - Learn about console capture
- [Python SDK Overview](../sdk/overview.md) - Learn all SDK functions
- [FAQ](../reference/faq.md) - Common questions

---

<div align="center">
  <p><a href="../sdk/overview.md">Back to SDK Overview →</a></p>
</div>
