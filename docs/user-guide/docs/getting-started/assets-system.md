# Assets System Guide

**New in v0.6.0** - SHA256 content-addressed storage with automatic deduplication.

---

## Overview

Runicorn's Assets System provides:

1. **Workspace Snapshots** - Capture your entire workspace state as a zip archive
2. **Blob Storage** - Store individual files with SHA256 content-addressing
3. **Automatic Deduplication** - Identical files are stored only once (50-90% space savings)
4. **Restore Capability** - Recreate workspace from manifests

<figure markdown>
  ![Asset Code Preview](../assets/asset_code_preview.png)
  <figcaption>Browse and preview code snapshots in the Web UI</figcaption>
</figure>

---

## Quick Start

### Automatic Code Snapshot (Recommended)

The simplest way to snapshot your workspace is via `rn.init()`:

```python
import runicorn as rn

# Enable automatic code snapshot
run = rn.init(path="cv/resnet50/baseline", snapshot_code=True)

# Training code...
run.log({"loss": 0.1}, step=1)

run.finish()
# Code snapshot saved as code_snapshot.zip in run directory
```

This automatically:

- Reads `.rnignore` to exclude unwanted files
- Creates a zip archive of your workspace
- Archives it to content-addressed storage
- Records metadata in `assets.json`

### Manual Snapshot

For more control, use `rn.snapshot_workspace()` directly:

```python
import runicorn as rn
from pathlib import Path

run = rn.init(path="demo/snapshot_test")

# Snapshot workspace to a zip file
result = rn.snapshot_workspace(
    root=Path("."),                      # Workspace root directory
    out_zip=Path(run.run_dir) / "my_snapshot.zip"  # Output zip path
)

print(f"Snapshot created: {result['file_count']} files, {result['total_bytes']} bytes")

run.finish()
```

### Store Individual Files (Blob Store)

For advanced use, store individual files in the content-addressed blob store:

```python
from pathlib import Path
from runicorn.assets import store_blob, get_blob_path, blob_exists

# Define your blob store root (typically inside storage directory)
blob_root = Path(".runicorn/blobs")

# Store a file — returns its SHA256 hash
sha256 = store_blob(Path("model.pth"), blob_root)
print(f"Stored as blob: {sha256}")

# Check if a blob exists
print(f"Blob exists: {blob_exists(sha256, blob_root)}")

# Get the storage path of a blob
blob_path = get_blob_path(sha256, blob_root)
print(f"Blob location: {blob_path}")
```

### Restore from Manifest

Recreate a workspace from a manifest file:

```python
from pathlib import Path
from runicorn.assets import restore_from_manifest

result = restore_from_manifest(
    manifest_path=Path(".runicorn/runs/demo/20260115_100000_abc123/assets.json"),
    blob_root=Path(".runicorn/blobs"),
    target_dir=Path("./restored_workspace"),
    overwrite=False
)

print(f"Restored {result['restored_count']} files ({result['total_bytes']} bytes)")
```

---

## .rnignore File

Control which files are included in snapshots using `.rnignore` (similar to `.gitignore`):

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

When no `.rnignore` exists, `snapshot_workspace()` automatically creates a default one with common exclusion patterns.

---

## Complete Example

Here's a complete training script with workspace snapshots:

```python
import runicorn as rn
import torch
import yaml

# Initialize with automatic code snapshot
run = rn.init(
    path="image_classification/resnet50",
    snapshot_code=True,          # Snapshot workspace code
    force_snapshot=False         # Fail if workspace is too large
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

# Training
model = torch.nn.Sequential(
    torch.nn.Linear(784, 128),
    torch.nn.ReLU(),
    torch.nn.Linear(128, 10)
)

for epoch in range(100):
    loss = train_one_epoch(model)
    run.log({"loss": loss}, step=epoch)

# Save model
torch.save(model.state_dict(), "model.pth")

# Save summary
run.summary({
    "final_loss": loss,
    "total_epochs": 100,
})

run.finish()
print(f"✓ Experiment completed: {run.id}")
# Code snapshot was automatically saved during init
```

---

## Deduplication

The blob store automatically deduplicates files based on SHA256 content hashing:

```python
from pathlib import Path
from runicorn.assets import store_blob

blob_root = Path(".runicorn/blobs")

# Store same file content twice
sha1 = store_blob(Path("config_v1.yaml"), blob_root)
sha2 = store_blob(Path("config_copy.yaml"), blob_root)  # Same content

# Same content → same hash → stored only once
assert sha1 == sha2
print(f"SHA256: {sha1}")
print("File stored only once on disk (deduplication)")
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

!!! tip "Tip: Use snapshot_code=True"
    
    The easiest way to snapshot is through `rn.init()`:
    
    ```python
    run = rn.init(path="experiment", snapshot_code=True)
    # Snapshot happens automatically — no extra code needed
    ```

!!! tip "Tip: Force Snapshot for Large Workspaces"
    
    By default, snapshots fail if the workspace exceeds 500 MB or 200,000 files.
    Use `force_snapshot=True` to override:
    
    ```python
    run = rn.init(path="large_project", snapshot_code=True, force_snapshot=True)
    ```

!!! warning "Large Files"
    
    For very large files (>1GB), consider:
    
    - Using `.rnignore` to exclude them from snapshots
    - Storing only checksums instead of full files
    - Using external storage (S3, NFS) and storing paths

---

## API Reference

### `snapshot_workspace()`

Capture workspace state as a zip archive.

**Signature**:
```python
from runicorn import snapshot_workspace

def snapshot_workspace(
    root: Path,
    out_zip: Path,
    *,
    ignore_file: str = ".rnignore",
    extra_excludes: list[str] | None = None,
    max_total_bytes: int = 500 * 1024 * 1024,  # 500 MB
    max_files: int = 200_000,
    force_snapshot: bool = False,
) -> dict
```

**Parameters**:

- `root` — Root directory to snapshot
- `out_zip` — Path for output zip archive
- `ignore_file` — Name of ignore file (default: `.rnignore`)
- `extra_excludes` — Additional glob patterns to exclude
- `max_total_bytes` — Maximum total size (default: 500 MB)
- `max_files` — Maximum number of files (default: 200,000)
- `force_snapshot` — Skip size/count limits if `True`

**Returns**: Dictionary with `workspace_root`, `archive_path`, `format`, `file_count`, `total_bytes`

### `store_blob()`

Store a file in content-addressed blob storage.

**Signature**:
```python
from runicorn.assets import store_blob

def store_blob(src_path: Path, blob_root: Path) -> str
```

**Parameters**:

- `src_path` — Path to the source file
- `blob_root` — Root directory of the blob store

**Returns**: SHA256 hash string (blob ID)

### `get_blob_path()`

Get the storage path for a blob by its SHA256 hash.

**Signature**:
```python
from runicorn.assets import get_blob_path

def get_blob_path(sha256: str, blob_root: Path) -> Path
```

**Parameters**:

- `sha256` — SHA256 hash of the blob
- `blob_root` — Root directory of the blob store

**Returns**: `Path` to the blob file

### `restore_from_manifest()`

Restore a directory from a manifest file.

**Signature**:
```python
from runicorn.assets import restore_from_manifest

def restore_from_manifest(
    manifest_path: Path,
    blob_root: Path,
    target_dir: Path,
    *,
    overwrite: bool = False,
) -> dict
```

**Parameters**:

- `manifest_path` — Path to the manifest JSON file
- `blob_root` — Root directory of the blob store
- `target_dir` — Directory to restore files into
- `overwrite` — Overwrite existing files if `True`

**Returns**: Dictionary with `restored_count`, `total_bytes`, `target_dir`

---

## Troubleshooting

### Snapshot too large?

If you see `"code snapshot too large"`:

1. **Add a `.rnignore` file** to exclude large directories:
    ```gitignore
    data/
    *.csv
    *.h5
    *.pth
    ```
2. **Use `force_snapshot=True`** to skip limits:
    ```python
    run = rn.init(path="demo", snapshot_code=True, force_snapshot=True)
    ```

### Deduplication not working?

Check that file content is actually identical:
```python
from runicorn.assets.fingerprint import sha256_file
from pathlib import Path

hash1 = sha256_file(Path("file1.txt"))
hash2 = sha256_file(Path("file2.txt"))
print(f"Same content: {hash1 == hash2}")
```

### Restore failed?

Check that manifest and blob store paths are correct:
```python
from pathlib import Path

manifest = Path(".runicorn/runs/demo/20260115_100000_abc123/assets.json")
blob_root = Path(".runicorn/blobs")

print(f"Manifest exists: {manifest.exists()}")
print(f"Blob root exists: {blob_root.exists()}")
```

---

## Migration from v0.5.x

If you're upgrading from v0.5.x:

**Before (v0.5.x)**:
```python
import runicorn as rn

run = rn.init(path="demo")

# Manual file copying
import shutil
shutil.copy("config.yaml", f".runicorn/runs/{run.id}/")

run.finish()
```

**After (v0.6.0)**:
```python
import runicorn as rn

# Automatic snapshot with deduplication
run = rn.init(path="demo", snapshot_code=True)

# Everything is captured automatically
run.finish()
```

---

## Next Steps

- [Enhanced Logging Guide](enhanced-logging.md) - Learn about console capture
- [Python SDK Overview](../sdk/overview.md) - Learn all SDK functions
- [FAQ](../reference/faq.md) - Common questions

---

<div class="rn-page-nav">
  <a href="../sdk/overview.md">Back to SDK Overview →</a>
</div>
