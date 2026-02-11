# Runicorn v0.6.0 Release Notes

> **Release Date**: 2026-01  
> **Version**: v0.6.0  
> **Author**: Runicorn Development Team

[English](RELEASE_NOTES_v0.6.0.md) | [简体中文](../zh/RELEASE_NOTES_v0.6.0.md)

---

## 🚀 Major Updates

Runicorn v0.6.0 is a feature-rich release that introduces several major improvements:

| Feature | Description |
|---------|-------------|
| **New Assets System** | SHA256 content-addressed storage with automatic deduplication |
| **Enhanced Logging** | Console capture, tqdm smart filtering, MetricLogger compatibility |
| **Path-based Hierarchy** | VSCode-style tree navigation for experiments |
| **Inline Compare View** | Multi-run metric comparison directly in experiment list |
| **New SSH Backend** | Multi-backend fallback architecture (OpenSSH → AsyncSSH → Paramiko) |
| **Frontend Improvements** | ANSI color support, line numbers, and search in logs |

---

## ✨ New Features

### 1. Assets System

The new Assets system replaces the old artifacts module with a modern, SHA256 content-addressed storage architecture.

#### Key Features

- **SHA256 Deduplication**: Identical files are stored only once, saving 50-90% storage
- **Workspace Snapshots**: Capture your entire codebase with `.rnignore` support
- **Blob Store**: Efficient content-addressed storage for all assets
- **Manifest-based Restore**: Restore any snapshot to its original state

#### Quick Start

```python
import runicorn as rn

# Initialize with code snapshot
run = rn.init(
    path="cv/yolo/experiment",
    snapshot_code=True,  # Automatically snapshot workspace
)

# Or manually snapshot workspace
from runicorn import snapshot_workspace

snapshot = snapshot_workspace(
    root=Path("./my_project"),
    out_zip=Path("./snapshot.zip"),
)
print(f"Captured {snapshot['file_count']} files, {snapshot['total_bytes']} bytes")
```

#### Storage Structure

```
<storage_root>/
├── archive/
│   ├── code/           # Code snapshots (SHA256 deduplicated)
│   ├── datasets/       # Dataset archives
│   └── outputs/        # Model outputs
└── runs/<path>/<run_id>/
    ├── assets.json     # Asset manifest
    └── code_snapshot.zip
```

#### API Reference

| Function | Description |
|----------|-------------|
| `snapshot_workspace(root, out_zip)` | Create a ZIP snapshot of workspace |
| `archive_file(path, archive_dir)` | Archive a file with SHA256 deduplication |
| `archive_dir(path, archive_dir)` | Archive a directory |
| `restore_from_manifest(manifest, target)` | Restore from asset manifest |

---

### 2. Enhanced Logging System

The new logging system provides seamless integration with your existing code - no modifications required.

#### Console Capture

Automatically capture all `print()` and logging output:

```python
import runicorn as rn

# Enable console capture
run = rn.init(
    path="training/bert",
    capture_console=True,  # Capture stdout/stderr
    tqdm_mode="smart",     # Smart tqdm filtering
)

# Your existing code works unchanged
print("Starting training...")
print(f"Epoch 1: loss={0.5:.4f}, acc={0.85:.2f}")

# All output is captured to logs.txt and viewable in Web UI
```

#### tqdm Handling Modes

| Mode | Behavior |
|------|----------|
| `"smart"` | Only keep final progress bar state (recommended) |
| `"all"` | Capture all progress updates |
| `"none"` | Disable tqdm capture |

#### Python Logging Integration

```python
import logging
import runicorn as rn

run = rn.init(path="experiment", capture_console=True)

# Get a logging handler that writes to Runicorn
logger = logging.getLogger(__name__)
logger.addHandler(run.get_logging_handler(level=logging.INFO))

logger.info("This goes to logs.txt")
logger.warning("Warnings are captured too")
```

#### MetricLogger Compatibility

Drop-in replacement for torchvision's MetricLogger:

```python
# Before (torchvision)
# from torchvision.references.detection.utils import MetricLogger

# After (Runicorn - just change the import!)
from runicorn.log_compat.torchvision import MetricLogger

metric_logger = MetricLogger(delimiter="  ")
for data in metric_logger.log_every(dataloader, 10, header="Train"):
    loss = model(data)
    metric_logger.update(loss=loss.item(), lr=optimizer.param_groups[0]['lr'])
    # Metrics are automatically logged to Runicorn!
```

**Features**:
- Pure Python implementation (works without PyTorch)
- Optional PyTorch acceleration when available
- Automatic metric logging via `run.log()`
- Distributed training support via `synchronize_between_processes()`

---

### 3. Path-based Hierarchy

Replace the rigid `project/name` structure with flexible path-based organization.

#### VSCode-style Navigation

The new `PathTreePanel` provides intuitive tree navigation:

```
┌─────────────────┬──────────────────────────────────────────┐
│  Path Tree      │  Runs Table                              │
│  ┌───────────┐  │  ┌────────────────────────────────────┐  │
│  │ 📁 cv     │  │  │ Path    │ Status │ Created │ ...  │  │
│  │  └ 📁 yolo│  │  ├────────────────────────────────────┤  │
│  │    └ 📁 v1│  │  │ cv/yolo │ ✓      │ 2025... │      │  │
│  │ 📁 nlp    │  │  │ cv/yolo │ ✓      │ 2025... │      │  │
│  │  └ 📁 bert│  │  └────────────────────────────────────┘  │
│  └───────────┘  │                                          │
└─────────────────┴──────────────────────────────────────────┘
```

#### SDK Usage

```python
import runicorn as rn

# Flexible path structure - any depth you want
run = rn.init(path="cv/detection/yolo/ablation_lr")
run = rn.init(path="nlp/bert/finetune")
run = rn.init(path="thesis/chapter3/experiment1")

# Optional alias for easy identification
run = rn.init(path="cv/yolo", alias="best-v2")
```

#### New API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/paths` | List all paths with optional statistics |
| `GET /api/paths/tree` | Get hierarchical tree structure |
| `GET /api/paths/runs?path=cv/yolo` | Filter runs by path prefix |
| `POST /api/paths/soft-delete` | Batch soft-delete runs by path |
| `GET /api/paths/export` | Batch export runs by path |

#### Features

- **Run Count Badges**: See how many runs are in each path
- **Search & Filter**: Quickly find paths
- **Right-click Menu**: Batch delete, export operations
- **Keyboard Navigation**: Arrow keys, Enter to select
- **Collapsible Panel**: Save screen space when needed

---

### 4. Inline Compare View

Compare multiple experiments directly in the experiment list page.

#### How It Works

1. Select 2+ runs in the experiment table
2. Click "Compare" button
3. View side-by-side metric charts instantly

```
┌─────────────────┬──────────────────────────────────────────┐
│  Selected Runs  │  [← Back]           Common Metrics: 3   │
│  ┌───────────┐  ├──────────────────────────────────────────┤
│  │ ● run_1   │  │  ┌─────────────┐  ┌─────────────┐       │
│  │   cv/yolo │  │  │    loss     │  │  accuracy   │       │
│  ├───────────┤  │  └─────────────┘  └─────────────┘       │
│  │ ● run_2   │  │  ┌─────────────┐                        │
│  │   cv/yolo │  │  │   f1_score  │                        │
│  └───────────┘  │  └─────────────┘                        │
└─────────────────┴──────────────────────────────────────────┘
```

#### Features

- **Common Metrics Detection**: Automatically shows metrics shared by 2+ runs
- **Color-coded Runs**: Left panel colors match chart lines
- **ECharts Linking**: Synchronized tooltip and zoom across charts
- **Visibility Toggle**: Show/hide individual runs or metrics
- **Auto-refresh**: Running experiments update in real-time

---

### 5. New SSH Backend Architecture

A complete rewrite of the SSH tunneling layer for improved reliability and compatibility.

#### Multi-Backend Fallback Chain

```
┌─────────────────────────────────────────────────────────────┐
│                     AutoBackend                              │
├─────────────────────────────────────────────────────────────┤
│  Connection: Always Paramiko (SSHConnection)                │
├─────────────────────────────────────────────────────────────┤
│  Tunneling Fallback Chain:                                  │
│                                                             │
│  1. OpenSSHTunnel (preferred)                               │
│     └─ Uses system OpenSSH client                           │
│     └─ Best compatibility with SSH agents                   │
│     └─ Requires: ssh, ssh-keyscan in PATH                   │
│                    ↓ (if unavailable)                       │
│  2. AsyncSSHTunnel                                          │
│     └─ Pure Python async implementation                     │
│     └─ Good performance                                     │
│                    ↓ (if unavailable)                       │
│  3. SSHTunnel (Paramiko)                                    │
│     └─ Final fallback                                       │
│     └─ Always available                                     │
└─────────────────────────────────────────────────────────────┘
```

#### Security Features

- **Strict Host Key Checking**: All backends enforce host key verification
- **Runicorn-managed known_hosts**: Separate from system known_hosts
- **409 Confirmation Protocol**: UI prompts for unknown/changed host keys
- **BatchMode**: No interactive password prompts (use keys!)

#### Configuration

```bash
# Optional: Specify custom SSH path
export RUNICORN_SSH_PATH=/usr/local/bin/ssh

# The backend is auto-detected - no configuration needed!
```

---

### 6. Frontend Improvements

#### LogsViewer Enhancements

The log viewer has been significantly improved:

| Feature | Description |
|---------|-------------|
| **ANSI Colors** | Full support for colored terminal output |
| **Line Numbers** | Easy reference and navigation |
| **Search** | Find text in logs with highlighting |
| **Auto-scroll** | Follow mode for live logs |
| **Virtual Scrolling** | Handle 100k+ lines smoothly |

#### Example ANSI Output

```python
# Your colored output is preserved!
print("\033[32m✓ Training complete\033[0m")
print("\033[31m✗ Validation failed\033[0m")
print("\033[33m⚠ Warning: learning rate too high\033[0m")
```

---

## 💥 Breaking Changes

### API Changes

| Old API | New API | Notes |
|---------|---------|-------|
| `project` parameter | `path` parameter | Use path-based hierarchy |
| `name` parameter | `path` parameter | Combine into single path |
| `/api/projects` | `/api/paths` | New endpoint structure |
| `/api/projects/{p}/names` | `/api/paths/tree` | Tree structure |

### Module Changes

| Removed | Replacement |
|---------|-------------|
| `artifacts/` module | `assets/` module |
| Old `project/name` fields | `path` field |

### SDK Parameter Changes

```python
# Old (v0.5.x)
run = rn.init(project="cv", name="yolo")

# New (v0.6.0)
run = rn.init(path="cv/yolo")
```

---

## 🐛 Bug Fixes

- **Fixed**: WebSocket connection stability in Remote Viewer
- **Fixed**: Memory leak in long-running metric logging
- **Fixed**: tqdm output causing log file bloat
- **Fixed**: SSH tunnel reconnection issues
- **Fixed**: Path traversal vulnerability in file operations
- **Fixed**: Race condition in concurrent metric writes

---

## 📚 Documentation Updates

### New Documentation

- **[Enhanced Logging Guide](../../guides/en/ENHANCED_LOGGING_GUIDE.md)** - Console capture and MetricLogger
- **[Assets Guide](../../guides/en/ASSETS_GUIDE.md)** - New asset system usage
- **[SSH Backend Architecture](../../architecture/en/SSH_BACKEND_ARCHITECTURE.md)** - Technical details
- **[Paths API Reference](../../api/en/paths_api.md)** - New API endpoints
- **[Logging API Reference](../../api/en/logging_api.md)** - Logging integration

### Updated Documentation

- **Quick Start Guide** - Updated for new features
- **API Index** - New endpoints added
- **System Overview** - New module architecture

---

## ⚠️ Known Limitations

### Console Capture

- Capture starts after `rn.init()` - early prints may be missed
- Some C extensions may bypass Python stdout
- Interactive prompts (input()) may behave unexpectedly

### Path Hierarchy

- Maximum path length: 200 characters
- Allowed characters: `a-z A-Z 0-9 _ - /`
- No `..` in paths (security)

### SSH Backend

- OpenSSH backend requires `ssh` and `ssh-keyscan` in PATH
- Password authentication not supported with OpenSSH tunnel
- Windows: OpenSSH may not be available by default

---

## 🔄 Migration Guide

### From v0.5.x to v0.6.0

#### 1. Update SDK Calls

```python
# Before (v0.5.x)
run = rn.init(project="my_project", name="experiment_1")

# After (v0.6.0)
run = rn.init(path="my_project/experiment_1")
```

#### 2. Enable New Features (Optional)

```python
# Add console capture
run = rn.init(
    path="my_project/experiment",
    capture_console=True,
    tqdm_mode="smart",
)

# Add code snapshot
run = rn.init(
    path="my_project/experiment",
    snapshot_code=True,
)
```

#### 3. Update MetricLogger (If Used)

```python
# Change import
# from utils import MetricLogger
from runicorn.log_compat.torchvision import MetricLogger

# Rest of code unchanged!
```

#### 4. Database Migration

The database schema is automatically migrated on first run. Existing data is preserved:
- `project` + `name` → `path` (concatenated with `/`)
- All metrics and assets remain intact

---

## 📥 Downloads

### PyPI

```bash
pip install -U runicorn
```

### With Image Support

```bash
pip install -U "runicorn[images]"
```

### GitHub Releases

- [v0.6.0 Source Code](https://github.com/Skydoge-zjm/runicorn/archive/v0.6.0.tar.gz)
- [Windows Desktop App](https://github.com/Skydoge-zjm/runicorn/releases/v0.6.0)

---

## 🙏 Acknowledgments

Thanks to all contributors and users who provided feedback for v0.6.0!

**Key Contributors**:
- Enhanced logging system design inspired by W&B and Neptune research
- Path hierarchy inspired by VSCode file explorer
- SSH backend improvements based on community feedback

---

**Author**: Runicorn Development Team  
**Version**: v0.6.0  
**Release Date**: 2026-01

**[View Full CHANGELOG](../../CHANGELOG.md)** | **[Back to Documentation](../../README.md)**
