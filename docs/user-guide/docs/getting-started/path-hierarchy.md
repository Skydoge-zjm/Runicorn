# Path-based Hierarchy Guide

**New in v0.6.0** - Flexible experiment organization using path-based hierarchy.

---

## Overview

In v0.6.0, Runicorn replaces the old `project/name` parameters with a single, flexible `path` parameter. This provides:

- **Unlimited nesting** — Organize experiments at any depth
- **VSCode-style navigation** — PathTreePanel in the Web UI
- **Backward compatible** — Old single-level paths still work

---

## Quick Start

```python
import runicorn as rn

# Simple path (like old project name)
run = rn.init(path="demo")

# Two-level path (like old project/name)
run = rn.init(path="cv/resnet50")

# Deep hierarchy
run = rn.init(path="cv/detection/yolo/ablation")

# Root path (no hierarchy)
run = rn.init(path="/")

# Default path (when None is passed)
run = rn.init()  # path defaults to "default"
```

---

## Path Rules

### Valid Characters

Paths can contain:
- Letters (a-z, A-Z)
- Numbers (0-9)
- Underscores (`_`)
- Hyphens (`-`)
- Forward slashes (`/`) as separators

### Validation

```python
# ✅ Valid paths
rn.init(path="cv/resnet50")
rn.init(path="nlp/bert-base/finetuning")
rn.init(path="experiment_001")
rn.init(path="team-A/project-1/run-v2")

# ❌ Invalid paths (will raise ValueError)
rn.init(path="my experiment")      # Spaces not allowed
rn.init(path="path/../escape")     # ".." not allowed
rn.init(path="special@chars!")     # Special characters not allowed
```

### Normalization

- Backslashes are converted to forward slashes: `cv\yolo` → `cv/yolo`
- Leading/trailing slashes are stripped: `/cv/yolo/` → `cv/yolo`
- `"/"` or `""` maps to root path
- `None` defaults to `"default"`
- Maximum length: 200 characters

---

## Directory Structure

Paths map directly to filesystem directories under the storage root:

```
storage_root/
├── runs/
│   ├── cv/
│   │   ├── detection/
│   │   │   └── yolo/
│   │   │       ├── 20260115_100000_abc123/  # run directory
│   │   │       └── 20260115_110000_def456/
│   │   └── classification/
│   │       └── resnet50/
│   │           └── 20260115_120000_789abc/
│   └── nlp/
│       └── bert/
│           └── 20260115_130000_xyz789/
└── archive/
    └── ...
```

---

## Web UI: PathTreePanel

The PathTreePanel provides a VSCode-style tree navigation in the experiments list:

### Features

- **Collapsible tree** — Expand/collapse path nodes
- **Run counts** — See how many runs exist at each level
- **Click to filter** — Click a node to show only runs under that path
- **Batch operations** — Export or soft-delete all runs under a path

### API Endpoints

The following REST API endpoints support path-based querying:

- `GET /api/paths` — List all paths with run statistics
- `GET /api/paths/tree` — Get hierarchical tree structure
- `GET /api/paths/runs?path=cv/detection` — List runs under a specific path
- `POST /api/paths/soft-delete` — Batch soft-delete runs by path
- `POST /api/paths/export` — Batch export runs by path

---

## Migration from project/name

### Before (v0.5.x)

```python
import runicorn as rn

# Old API: separate project and name
run = rn.init(project="image_classification", name="resnet50_v1")
```

### After (v0.6.0)

```python
import runicorn as rn

# New API: single path parameter
run = rn.init(path="image_classification/resnet50_v1")

# Or use deeper hierarchy
run = rn.init(path="cv/classification/resnet50/v1")
```

### Mapping Guide

| Old (v0.5.x) | New (v0.6.0) |
|---------------|--------------|
| `project="demo"` | `path="demo"` |
| `project="cv", name="resnet"` | `path="cv/resnet"` |
| `project="nlp", name="bert_ft"` | `path="nlp/bert_ft"` |

### Alias Support

For user-friendly names, use the `alias` parameter:

```python
run = rn.init(
    path="cv/detection/yolo/ablation",
    alias="best-yolo-v2"
)
# run.id = "20260115_100000_abc123" (auto-generated)
# run.alias = "best-yolo-v2" (human-readable)
```

---

## Best Practices

!!! tip "Organize by Task → Model → Variant"
    
    Use a consistent hierarchy:
    
    ```python
    rn.init(path="cv/detection/yolo")
    rn.init(path="cv/detection/faster-rcnn")
    rn.init(path="cv/classification/resnet50")
    rn.init(path="nlp/sentiment/bert-base")
    ```

!!! tip "Use Aliases for Important Runs"
    
    ```python
    run = rn.init(path="cv/detection/yolo", alias="production-v3")
    ```

!!! warning "Path Length Limit"
    
    Paths are limited to 200 characters. Keep paths concise.

---

## Next Steps

- [Python SDK Overview](../sdk/overview.md) — Full API reference
- [Web UI Overview](../ui/overview.md) — Explore the PathTreePanel
- [Quick Start](quickstart.md) — Get started with Runicorn

---

<div align="center">
  <p><a href="../sdk/overview.md">Explore the Python SDK →</a></p>
</div>
