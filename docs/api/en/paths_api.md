[English](paths_api.md) | [简体中文](../zh/paths_api.md)

---

# Path Hierarchy API Reference

> **Version**: v0.6.0  
> **Last Updated**: 2025-01-XX  
> **Base URL**: `http://127.0.0.1:23300/api`

---

## 📖 Table of Contents

- [Overview](#overview)
- [Path Naming](#path-naming)
- [Endpoints](#endpoints)
  - [GET /api/paths](#get-apipaths)
  - [GET /api/paths/tree](#get-apipathstree)
  - [GET /api/paths/runs](#get-apipathsruns)
  - [POST /api/paths/soft-delete](#post-apipathssoft-delete)
  - [GET /api/paths/export](#get-apipathsexport)
- [Legacy Compatibility](#legacy-compatibility)
- [Examples](#examples)

---

## Overview

The Path Hierarchy API provides flexible experiment organization using path-based naming. Instead of the fixed `project/name` structure, you can now use arbitrary depth paths like `cv/detection/yolo/ablation`.

### Key Features

- **Flexible Depth**: Organize experiments with any number of levels
- **Tree Navigation**: VSCode-style hierarchical browsing
- **Batch Operations**: Delete or export entire path subtrees
- **Statistics**: Run counts per path for UI badges
- **Legacy Compatible**: Old `project/name` APIs still work

### Path Structure

```
<storage_root>/runs/
├── cv/
│   ├── detection/
│   │   └── yolo/
│   │       ├── 20250114_153045_a1b2c3/
│   │       └── 20250114_160000_b8c4d2/
│   └── classification/
│       └── resnet/
│           └── 20250114_170000_c9e5f3/
└── nlp/
    └── bert/
        └── 20250114_180000_d0f6g4/
```

---

## Path Naming

### SDK Usage

```python
import runicorn

# Flexible path depth
run = runicorn.init(path="cv/detection/yolo/ablation_lr")
run = runicorn.init(path="nlp/bert/finetune")
run = runicorn.init(path="thesis/chapter3")

# Optional alias for easy identification
run = runicorn.init(path="cv/yolo", alias="best-v2")
```

### Path Rules

| Rule | Description |
|------|-------------|
| Characters | `a-z A-Z 0-9 _ - /` only |
| No traversal | `..` not allowed |
| Max length | 200 characters |
| Separator | Always `/` (converted to OS separator for storage) |
| Default | `"default"` if not specified |
| Root | `"/"` or `""` for root level |

### Examples

```python
# Valid paths
"cv/yolo"
"nlp/bert/finetune"
"thesis/chapter3/experiment1"
"my-project/test_run"

# Invalid paths
"cv/../secrets"     # Contains ..
"path/with spaces"  # Contains space
"path\\windows"     # Use / not \
```

---

## Endpoints

### GET /api/paths

List all unique experiment paths with optional statistics.

#### Request

**URL**: `GET /api/paths`

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_stats` | boolean | `false` | Include run count statistics per path |

#### Response

**Without stats** (`include_stats=false`):
```json
{
  "paths": [
    "cv/detection/yolo",
    "cv/classification/resnet",
    "nlp/bert"
  ],
  "tree": {
    "cv": {
      "detection": {
        "yolo": {}
      },
      "classification": {
        "resnet": {}
      }
    },
    "nlp": {
      "bert": {}
    }
  }
}
```

**With stats** (`include_stats=true`):
```json
{
  "paths": ["cv", "cv/detection", "cv/detection/yolo", "nlp", "nlp/bert"],
  "tree": {
    "cv": {
      "detection": {
        "yolo": {}
      }
    },
    "nlp": {
      "bert": {}
    }
  },
  "stats": {
    "cv": {"total": 15, "running": 2, "finished": 12, "failed": 1},
    "cv/detection": {"total": 10, "running": 1, "finished": 8, "failed": 1},
    "cv/detection/yolo": {"total": 8, "running": 1, "finished": 6, "failed": 1},
    "nlp": {"total": 5, "running": 0, "finished": 5, "failed": 0},
    "nlp/bert": {"total": 5, "running": 0, "finished": 5, "failed": 0}
  }
}
```

#### Examples

**cURL**:
```bash
# Basic list
curl http://localhost:23300/api/paths

# With statistics
curl "http://localhost:23300/api/paths?include_stats=true"
```

**Python**:
```python
import requests

# Get paths with stats
response = requests.get(
    "http://localhost:23300/api/paths",
    params={"include_stats": True}
)
data = response.json()

for path, stats in data["stats"].items():
    print(f"{path}: {stats['total']} runs ({stats['running']} running)")
```

---

### GET /api/paths/tree

Get only the tree structure (without path list or stats).

#### Request

**URL**: `GET /api/paths/tree`

#### Response

```json
{
  "tree": {
    "cv": {
      "detection": {
        "yolo": {}
      },
      "classification": {
        "resnet": {}
      }
    },
    "nlp": {
      "bert": {}
    }
  }
}
```

#### Example

```bash
curl http://localhost:23300/api/paths/tree
```

---

### GET /api/paths/runs

List runs filtered by path prefix.

#### Request

**URL**: `GET /api/paths/runs`

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string | `null` | Path prefix to filter by |
| `exact` | boolean | `false` | If true, match exact path only |

#### Response

```json
[
  {
    "id": "20250114_153045_a1b2c3",
    "run_dir": "/data/runicorn/runs/cv/yolo/20250114_153045_a1b2c3",
    "created_time": 1705234245.5,
    "status": "finished",
    "pid": null,
    "best_metric_value": 0.95,
    "best_metric_name": "accuracy",
    "path": "cv/yolo",
    "alias": "best-v2"
  },
  {
    "id": "20250114_160000_b8c4d2",
    "run_dir": "/data/runicorn/runs/cv/yolo/ablation/20250114_160000_b8c4d2",
    "created_time": 1705236000.0,
    "status": "running",
    "pid": 12345,
    "best_metric_value": null,
    "best_metric_name": null,
    "path": "cv/yolo/ablation",
    "alias": null
  }
]
```

#### Examples

**cURL**:
```bash
# All runs under cv/yolo (including cv/yolo/ablation, etc.)
curl "http://localhost:23300/api/paths/runs?path=cv/yolo"

# Only runs with exact path cv/yolo
curl "http://localhost:23300/api/paths/runs?path=cv/yolo&exact=true"

# All runs (no filter)
curl "http://localhost:23300/api/paths/runs"
```

**Python**:
```python
import requests

# Get runs under a path
response = requests.get(
    "http://localhost:23300/api/paths/runs",
    params={"path": "cv/detection", "exact": False}
)
runs = response.json()

for run in runs:
    print(f"{run['id']}: {run['status']} ({run['path']})")
```

---

### POST /api/paths/soft-delete

Soft delete all runs under a path (move to recycle bin).

#### Request

**URL**: `POST /api/paths/soft-delete`

**Headers**:
```
Content-Type: application/json
```

**Body**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | string | ✅ | Path prefix to match |
| `exact` | boolean | ❌ | If true, only match exact path (default: false) |

#### Response

```json
{
  "path": "cv/yolo/old_experiments",
  "deleted_count": 5,
  "errors": null,
  "message": "Moved 5 runs to recycle bin"
}
```

**With errors**:
```json
{
  "path": "cv/yolo",
  "deleted_count": 3,
  "errors": [
    "Failed to delete 20250114_153045_a1b2c3",
    "Error deleting 20250114_160000_b8c4d2: Permission denied"
  ],
  "message": "Moved 3 runs to recycle bin"
}
```

#### Examples

**cURL**:
```bash
# Delete all runs under cv/yolo (including subpaths)
curl -X POST http://localhost:23300/api/paths/soft-delete \
  -H "Content-Type: application/json" \
  -d '{"path": "cv/yolo"}'

# Delete only runs with exact path cv/yolo
curl -X POST http://localhost:23300/api/paths/soft-delete \
  -H "Content-Type: application/json" \
  -d '{"path": "cv/yolo", "exact": true}'
```

**Python**:
```python
import requests

response = requests.post(
    "http://localhost:23300/api/paths/soft-delete",
    json={"path": "old_experiments", "exact": False}
)
result = response.json()
print(f"Deleted {result['deleted_count']} runs")
```

---

### GET /api/paths/export

Export all runs under a path as JSON or ZIP.

#### Request

**URL**: `GET /api/paths/export`

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string | **required** | Path prefix to export |
| `exact` | boolean | `false` | If true, only match exact path |
| `format` | string | `"json"` | Export format: `json` or `zip` |

#### Response

**JSON format** (`format=json`):
```json
{
  "path": "cv/yolo",
  "exact": false,
  "total_runs": 3,
  "runs": [
    {
      "run_id": "20250114_153045_a1b2c3",
      "path": "cv/yolo",
      "alias": "best-v2",
      "status": "finished",
      "created_time": 1705234245.5,
      "summary": {
        "best_metric_value": 0.95,
        "best_metric_name": "accuracy"
      },
      "meta": {
        "python": "3.11.0",
        "platform": "Linux 5.15.0",
        "hostname": "gpu-server"
      }
    }
  ]
}
```

**ZIP format** (`format=zip`):
- Returns a downloadable ZIP file
- Contains `index.json` with metadata
- Contains full run directories with all files

#### Examples

**cURL**:
```bash
# Export as JSON
curl "http://localhost:23300/api/paths/export?path=cv/yolo&format=json"

# Export as ZIP (download)
curl -o export.zip "http://localhost:23300/api/paths/export?path=cv/yolo&format=zip"
```

**Python**:
```python
import requests

# JSON export
response = requests.get(
    "http://localhost:23300/api/paths/export",
    params={"path": "cv/yolo", "format": "json"}
)
data = response.json()
print(f"Exported {data['total_runs']} runs")

# ZIP export
response = requests.get(
    "http://localhost:23300/api/paths/export",
    params={"path": "cv/yolo", "format": "zip"}
)
with open("export.zip", "wb") as f:
    f.write(response.content)
```

---

## Legacy Compatibility

The old `project/name` API endpoints still work for backward compatibility.

### GET /api/projects

List top-level path segments (first segment of each path).

```bash
curl http://localhost:23300/api/projects
```

**Response**:
```json
{
  "projects": ["cv", "nlp", "default"]
}
```

### GET /api/projects/{project}/names

List second-level path segments for a given first segment.

```bash
curl http://localhost:23300/api/projects/cv/names
```

**Response**:
```json
{
  "names": ["detection", "classification"]
}
```

### GET /api/projects/{project}/names/{name}/runs

List runs for a given `project/name` combination.

```bash
curl http://localhost:23300/api/projects/cv/names/detection/runs
```

**Response**:
```json
[
  {
    "run_id": "20250114_153045_a1b2c3",
    "path": "cv/detection/yolo",
    "alias": null,
    "status": "finished",
    "start_time": 1705234245.5
  }
]
```

---

## Examples

### Building a Path Tree UI

```python
import requests

def build_tree_ui():
    response = requests.get(
        "http://localhost:23300/api/paths",
        params={"include_stats": True}
    )
    data = response.json()
    
    def render_tree(tree, stats, indent=0):
        for name, children in tree.items():
            # Build full path for stats lookup
            path = name  # Simplified; real impl needs full path tracking
            stat = stats.get(path, {})
            count = stat.get("total", 0)
            running = stat.get("running", 0)
            
            prefix = "  " * indent
            badge = f" ({running} running)" if running > 0 else ""
            print(f"{prefix}📁 {name} [{count}]{badge}")
            
            if children:
                render_tree(children, stats, indent + 1)
    
    render_tree(data["tree"], data.get("stats", {}))

build_tree_ui()
```

**Output**:
```
📁 cv [15] (2 running)
  📁 detection [10] (1 running)
    📁 yolo [8] (1 running)
  📁 classification [5]
    📁 resnet [5]
📁 nlp [5]
  📁 bert [5]
```

### Batch Cleanup Script

```python
import requests
from datetime import datetime, timedelta

def cleanup_old_experiments(days_old=30):
    """Delete experiments older than N days."""
    
    # Get all paths
    response = requests.get("http://localhost:23300/api/paths")
    paths = response.json()["paths"]
    
    cutoff = datetime.now() - timedelta(days=days_old)
    cutoff_ts = cutoff.timestamp()
    
    for path in paths:
        # Get runs for this path
        response = requests.get(
            "http://localhost:23300/api/paths/runs",
            params={"path": path, "exact": True}
        )
        runs = response.json()
        
        # Check if all runs are old
        old_runs = [r for r in runs if r["created_time"] < cutoff_ts]
        
        if len(old_runs) == len(runs) and runs:
            print(f"Deleting {len(runs)} old runs from {path}")
            requests.post(
                "http://localhost:23300/api/paths/soft-delete",
                json={"path": path, "exact": True}
            )

cleanup_old_experiments(days_old=30)
```

---

## Error Handling

### Common Errors

| Status | Error | Cause |
|--------|-------|-------|
| 400 | `path is required` | Missing path parameter |
| 400 | `Unsupported format: xyz` | Invalid export format |
| 404 | `No runs found for this path` | ZIP export with no matching runs |
| 500 | `Failed to create zip: ...` | ZIP creation error |

### Error Response Format

```json
{
  "detail": "path is required"
}
```

---

## Related Documentation

- **[Runs API](./runs_api.md)** - Individual run management
- **[API Index](./API_INDEX.md)** - Complete API reference
- **[Quick Reference](./QUICK_REFERENCE.md)** - API quick reference

---

**Author**: Runicorn Development Team  
**Version**: v0.6.0  
**Last Updated**: 2025-01-XX

**[Back to API Index](API_INDEX.md)**
