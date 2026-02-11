[English](ASSETS_GUIDE.md) | [简体中文](../zh/ASSETS_GUIDE.md)

---

# Assets System Guide

> **Version**: v0.6.0  
> **Feature**: SHA256 Content-Addressed Storage, Workspace Snapshots, Deduplication

---

## 📋 Overview

Runicorn v0.6.0 introduces a new **Assets System** that provides efficient, deduplicated storage for experiment files. This system replaces the old artifacts module with a modern content-addressed storage (CAS) architecture.

### Key Features

- **SHA256 Content-Addressed Storage**: Files are stored by their content hash, enabling automatic deduplication
- **Workspace Snapshots**: Capture your entire codebase at experiment time
- **Blob Store**: Efficient storage with 50-90% space savings for similar files
- **Manifest-Based Restore**: Reconstruct any snapshot from its manifest
- **Orphan Cleanup**: Automatic cleanup of unreferenced blobs

### How Deduplication Works

```
Traditional Storage:
  run_001/code.zip  →  100 MB
  run_002/code.zip  →  100 MB  (99% identical)
  run_003/code.zip  →  100 MB  (99% identical)
  Total: 300 MB

Content-Addressed Storage:
  blobs/a4/a47eb79...  →  100 MB  (shared content)
  blobs/3f/3f8c2a1...  →  1 MB    (unique changes)
  manifests/run_001.json  →  points to blobs
  manifests/run_002.json  →  points to blobs
  manifests/run_003.json  →  points to blobs
  Total: ~101 MB (66% savings)
```

---

## 🚀 Quick Start

### Creating Workspace Snapshots

Capture your code at experiment time:

```python
import runicorn as rn
from runicorn import snapshot_workspace
from pathlib import Path

# Initialize run
run = rn.init(path="training/resnet")

# Snapshot current workspace
result = snapshot_workspace(
    root=Path("."),
    out_zip=run.run_dir / "code_snapshot.zip",
)

print(f"Captured {result['file_count']} files ({result['total_bytes']} bytes)")

# Continue with training...
run.log({"loss": 0.5})
run.finish()
```

### Using Blob Storage

Store files with automatic deduplication:

```python
from runicorn.assets.blob_store import store_blob, get_blob_path, get_blob_stats
from pathlib import Path

# Define blob storage root
blob_root = Path("~/.runicorn/archive/blobs").expanduser()

# Store a file (returns SHA256 hash)
sha256 = store_blob(Path("model.pth"), blob_root)
print(f"Stored with hash: {sha256}")

# Store same file again - no duplicate created
sha256_again = store_blob(Path("model.pth"), blob_root)
assert sha256 == sha256_again  # Same hash, no new storage

# Get blob path for retrieval
blob_path = get_blob_path(sha256, blob_root)
print(f"Blob stored at: {blob_path}")

# Check storage statistics
stats = get_blob_stats(blob_root)
print(f"Total blobs: {stats['blob_count']}")
print(f"Total size: {stats['total_size_bytes']} bytes")
```

---

## 📚 Features

### Workspace Snapshots

The `snapshot_workspace()` function creates a compressed archive of your project, respecting `.rnignore` patterns.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `root` | `Path` | Required | Workspace root directory |
| `out_zip` | `Path` | Required | Output zip file path |
| `ignore_file` | `str` | `".rnignore"` | Ignore file name |
| `extra_excludes` | `List[str]` | `None` | Additional exclude patterns |
| `max_total_bytes` | `int` | `500MB` | Maximum snapshot size |
| `max_files` | `int` | `200,000` | Maximum file count |
| `force_snapshot` | `bool` | `False` | Bypass size limits |

#### Return Value

```python
{
    "workspace_root": "/path/to/workspace",
    "archive_path": "/path/to/snapshot.zip",
    "format": "zip",
    "file_count": 150,
    "total_bytes": 1048576,
}
```

### .rnignore Support

Create a `.rnignore` file in your project root to exclude files from snapshots:

```gitignore
# .rnignore - Similar to .gitignore syntax

# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/

# Virtual environments
venv/
.venv/
env/

# Data and models (usually too large)
data/
datasets/
*.pth
*.ckpt
*.h5

# IDE
.idea/
.vscode/
*.swp

# Build artifacts
dist/
build/
*.egg-info/

# Logs and outputs
logs/
outputs/
*.log
```

If no `.rnignore` exists, Runicorn creates a default one with common exclusions.

### Fingerprint Calculation

Files are identified by their SHA256 hash:

```python
from runicorn.assets.fingerprint import sha256_file
from pathlib import Path

# Calculate file fingerprint
fingerprint = sha256_file(Path("model.pth"))
print(f"SHA256: {fingerprint}")
# Output: SHA256: a47eb79188cdc67a601ebf32...
```

### Blob Store

The blob store provides content-addressed storage:

```python
from runicorn.assets.blob_store import (
    store_blob,
    get_blob_path,
    blob_exists,
    read_blob,
    get_blob_stats,
)
```

#### Storage Structure

```
archive/
├── blobs/
│   ├── a4/
│   │   └── a47eb79188cdc67a601ebf32...  # File content
│   ├── 3f/
│   │   └── 3f8c2a1b9e4d7f...
│   └── ...
└── manifests/
    ├── run_001.json  # Points to blobs
    └── run_002.json
```

### Manifest-Based Restore

Restore files from a manifest:

```python
from runicorn.assets.restore import (
    load_manifest,
    restore_from_manifest,
    export_manifest_to_zip,
    get_file_from_manifest,
)
from pathlib import Path

# Load manifest
manifest = load_manifest(Path("archive/manifests/run_001.json"))
print(f"Files in manifest: {len(manifest['files'])}")

# Restore to directory
result = restore_from_manifest(
    manifest_path=Path("archive/manifests/run_001.json"),
    blob_root=Path("archive/blobs"),
    target_dir=Path("restored_code"),
    overwrite=False,
)
print(f"Restored {result['restored_count']} files")

# Export to zip
result = export_manifest_to_zip(
    manifest_path=Path("archive/manifests/run_001.json"),
    blob_root=Path("archive/blobs"),
    zip_path=Path("export.zip"),
)
print(f"Exported {result['exported_count']} files to {result['zip_path']}")

# Get single file
blob_path = get_file_from_manifest(
    manifest_path=Path("archive/manifests/run_001.json"),
    blob_root=Path("archive/blobs"),
    rel_path="train.py",
)
print(f"train.py stored at: {blob_path}")
```

---

## 📖 API Reference

### snapshot_workspace()

```python
from runicorn import snapshot_workspace

result = snapshot_workspace(
    root: Path,
    out_zip: Path,
    *,
    ignore_file: str = ".rnignore",
    extra_excludes: Optional[List[str]] = None,
    max_total_bytes: int = 500 * 1024 * 1024,
    max_files: int = 200_000,
    force_snapshot: bool = False,
) -> Dict[str, Any]
```

### store_blob()

```python
from runicorn.assets.blob_store import store_blob

sha256 = store_blob(
    src_path: Path,
    blob_root: Path,
) -> str
```

Stores a file in the blob store. Returns SHA256 hash. If file already exists (same hash), no duplicate is created.

### get_blob_path()

```python
from runicorn.assets.blob_store import get_blob_path

path = get_blob_path(
    sha256: str,
    blob_root: Path,
) -> Path
```

Returns the storage path for a blob by its hash.

### restore_from_manifest()

```python
from runicorn.assets.restore import restore_from_manifest

result = restore_from_manifest(
    manifest_path: Path,
    blob_root: Path,
    target_dir: Path,
    *,
    overwrite: bool = False,
) -> Dict[str, Any]
```

Restores files from a manifest to a target directory.

### export_manifest_to_zip()

```python
from runicorn.assets.restore import export_manifest_to_zip

result = export_manifest_to_zip(
    manifest_path: Path,
    blob_root: Path,
    zip_path: Path,
) -> Dict[str, Any]
```

Exports a manifest-based archive to a zip file.

---

## 🧹 Cleanup

### delete_run_completely()

Permanently delete a run and all its orphaned assets:

```python
from runicorn.assets.cleanup import delete_run_completely
from pathlib import Path

# Preview what would be deleted (dry run)
result = delete_run_completely(
    run_id="20250115_103015_abc123",
    storage_root=Path("~/.runicorn").expanduser(),
    dry_run=True,
)
print(f"Would delete {result['blobs_deleted']} blobs")
print(f"Would free {result['bytes_freed']} bytes")

# Actually delete
result = delete_run_completely(
    run_id="20250115_103015_abc123",
    storage_root=Path("~/.runicorn").expanduser(),
    dry_run=False,
)
print(f"Deleted {result['blobs_deleted']} blobs")
print(f"Freed {result['bytes_freed']} bytes")
```

#### Return Value

```python
{
    "success": True,
    "run_id": "20250115_103015_abc123",
    "run_dir_deleted": True,
    "orphaned_assets": [...],  # Assets only used by this run
    "kept_assets": [...],      # Assets shared with other runs
    "blobs_deleted": 15,
    "manifests_deleted": 2,
    "outputs_deleted": 5,
    "bytes_freed": 104857600,
    "errors": [],
}
```

### cleanup_orphaned_blobs()

Scan for and remove orphaned blobs not referenced by any manifest:

```python
from runicorn.assets.cleanup import cleanup_orphaned_blobs
from pathlib import Path

# Preview orphaned blobs
result = cleanup_orphaned_blobs(
    storage_root=Path("~/.runicorn").expanduser(),
    dry_run=True,
)
print(f"Found {result['orphaned_blobs']} orphaned blobs")
print(f"Would free {result['bytes_freed']} bytes")

# Clean up
result = cleanup_orphaned_blobs(
    storage_root=Path("~/.runicorn").expanduser(),
    dry_run=False,
)
print(f"Cleaned {result['orphaned_blobs']} orphaned blobs")
```

---

## 🔄 Migration from v0.5.x

### What Changed

| v0.5.x (Artifacts) | v0.6.0 (Assets) |
|-------------------|-----------------|
| `rn.Artifact()` class | `snapshot_workspace()` function |
| `run.log_artifact()` | Automatic with `snapshot_workspace()` |
| `run.use_artifact()` | `restore_from_manifest()` |
| Version-based storage | Content-addressed storage |
| Manual deduplication | Automatic SHA256 deduplication |

### Migration Steps

1. **Update imports**:
   ```python
   # Old
   from runicorn import Artifact
   
   # New
   from runicorn import snapshot_workspace
   from runicorn.assets.restore import restore_from_manifest
   ```

2. **Update snapshot code**:
   ```python
   # Old
   artifact = rn.Artifact("code", type="code")
   artifact.add_dir(".")
   run.log_artifact(artifact)
   
   # New
   from runicorn import snapshot_workspace
   snapshot_workspace(
       root=Path("."),
       out_zip=run.run_dir / "code_snapshot.zip",
   )
   ```

3. **Update restore code**:
   ```python
   # Old
   artifact = run.use_artifact("code:v1")
   path = artifact.download()
   
   # New
   from runicorn.assets.restore import restore_from_manifest
   result = restore_from_manifest(
       manifest_path=Path("archive/manifests/run_001.json"),
       blob_root=Path("archive/blobs"),
       target_dir=Path("restored"),
   )
   ```

### Existing Data

Existing v0.5.x artifacts in `artifacts/` directory remain accessible. The new assets system uses a separate `archive/` directory structure.

---

## 💡 Best Practices

### 1. Configure .rnignore Early

Create `.rnignore` before your first experiment to avoid capturing unnecessary files:

```gitignore
# Essential exclusions
__pycache__/
*.pyc
venv/
.git/
data/
*.pth
*.ckpt
```

### 2. Use Snapshots for Reproducibility

Always snapshot your code when starting important experiments:

```python
run = rn.init(path="important_experiment")

# Snapshot immediately after init
snapshot_workspace(
    root=Path("."),
    out_zip=run.run_dir / "code.zip",
)

# Now train...
```

### 3. Monitor Storage Usage

Periodically check blob store statistics:

```python
from runicorn.assets.blob_store import get_blob_stats
from pathlib import Path

stats = get_blob_stats(Path("~/.runicorn/archive/blobs").expanduser())
print(f"Blobs: {stats['blob_count']}")
print(f"Size: {stats['total_size_bytes'] / 1024 / 1024:.1f} MB")
```

### 4. Clean Up Old Runs

Remove old runs to free space:

```python
from runicorn.assets.cleanup import delete_run_completely

# Delete old runs (shared blobs are preserved)
for run_id in old_run_ids:
    delete_run_completely(run_id, storage_root)
```

---

## 🔧 Troubleshooting

### Issue: Snapshot too large

**Cause**: Large data files or models included

**Solution**: Update `.rnignore`:
```gitignore
# Add to .rnignore
data/
datasets/
*.pth
*.ckpt
*.h5
checkpoints/
```

Or use `extra_excludes`:
```python
snapshot_workspace(
    root=Path("."),
    out_zip=out_path,
    extra_excludes=["large_folder/", "*.bin"],
)
```

### Issue: Too many files

**Cause**: Node modules, virtual environments, or cache directories

**Solution**: Ensure these are in `.rnignore`:
```gitignore
node_modules/
venv/
.venv/
__pycache__/
.pytest_cache/
```

### Issue: Missing blobs during restore

**Cause**: Blobs were deleted or corrupted

**Solution**: Check the result for missing blobs:
```python
result = restore_from_manifest(...)
if "missing_blobs" in result:
    print(f"Missing: {result['missing_blobs']}")
```

### Issue: Disk space not freed after deletion

**Cause**: Blobs are shared with other runs

**Solution**: Use `cleanup_orphaned_blobs()` after deleting multiple runs:
```python
# Delete runs first
for run_id in runs_to_delete:
    delete_run_completely(run_id, storage_root)

# Then clean orphaned blobs
cleanup_orphaned_blobs(storage_root)
```

---

## 📊 Storage Structure

```
<storage_root>/
├── archive/
│   ├── blobs/                    # Content-addressed storage
│   │   ├── a4/
│   │   │   └── a47eb79188...     # File content (named by SHA256)
│   │   └── 3f/
│   │       └── 3f8c2a1b9e...
│   ├── manifests/                # File manifests
│   │   ├── run_001.json
│   │   └── run_002.json
│   └── outputs/                  # Rolling outputs
│       └── rolling/
│           └── <run_id>/
└── <project>/
    └── <experiment>/
        └── runs/
            └── <run_id>/
                ├── code_snapshot.zip  # Workspace snapshot
                └── ...
```

---

**[Back to Guides](README.md)** | **[Back to Main](../../README.md)**
