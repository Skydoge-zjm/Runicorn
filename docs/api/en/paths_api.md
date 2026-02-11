[English](paths_api.md) | [简体中文](../zh/paths_api.md)

---

# Path Hierarchy API

**Version**: v0.6.0  
**Router**: `projects.py` (exported as `projects_router`)  
**Prefix**: `/api`

Flexible path-based experiment organization with tree navigation, batch operations, and export.

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/paths` | List all unique paths (with optional stats) |
| GET | `/api/paths/tree` | Get path tree structure |
| GET | `/api/paths/runs` | List runs filtered by path |
| POST | `/api/paths/soft-delete` | Batch soft delete runs by path |
| GET | `/api/paths/export` | Export runs by path (JSON or ZIP) |

### Legacy Compatibility

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List top-level path segments |
| GET | `/api/projects/{project}/names` | List second-level segments |
| GET | `/api/projects/{project}/names/{name}/runs` | List runs under project/name |

---

## GET /api/paths

List all unique experiment paths.

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_stats` | bool | `false` | Include run count statistics per path |

**Response** (without stats):
```json
{
  "paths": ["cv/resnet", "cv/yolo", "nlp/bert"],
  "tree": {
    "cv": {
      "resnet": {},
      "yolo": {}
    },
    "nlp": {
      "bert": {}
    }
  }
}
```

**Response** (with `include_stats=true`):
```json
{
  "paths": ["cv", "cv/resnet", "cv/yolo"],
  "tree": { ... },
  "stats": {
    "cv": {"total": 15, "running": 2, "finished": 12, "failed": 1},
    "cv/resnet": {"total": 8, "running": 1, "finished": 7, "failed": 0},
    "cv/yolo": {"total": 7, "running": 1, "finished": 5, "failed": 1}
  }
}
```

> **Note**: When `include_stats=true`, ancestor paths are automatically included with aggregated statistics.

---

## GET /api/paths/tree

Get the path tree structure only.

**Response**:
```json
{
  "tree": {
    "cv": {
      "resnet": {},
      "yolo": {}
    },
    "nlp": {
      "bert": {}
    }
  }
}
```

---

## GET /api/paths/runs

List runs filtered by path prefix or exact match.

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string | `null` | Path prefix to filter by (e.g., `cv/yolo`) |
| `exact` | bool | `false` | If true, match exact path only |

**Response**: Array of `RunListItem`:
```json
[
  {
    "id": "20250114_153045_a1b2c3",
    "run_dir": "/data/runicorn/...",
    "created_time": 1736870400.0,
    "status": "finished",
    "pid": null,
    "best_metric_value": 0.95,
    "best_metric_name": "accuracy",
    "path": "cv/yolo",
    "alias": "yolov8-baseline"
  }
]
```

**Examples**:
```bash
# All runs under cv/
GET /api/paths/runs?path=cv

# Only runs with exact path cv/yolo
GET /api/paths/runs?path=cv/yolo&exact=true

# All runs (no filter)
GET /api/paths/runs
```

---

## POST /api/paths/soft-delete

Batch soft delete all runs under a path (move to recycle bin).

**Request Body**:
```json
{
  "path": "old_experiments",
  "exact": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | string | Yes | Path prefix to match |
| `exact` | bool | No (default: false) | If true, only match exact path |

**Response**:
```json
{
  "path": "old_experiments",
  "deleted_count": 12,
  "errors": null,
  "message": "Moved 12 runs to recycle bin"
}
```

---

## GET /api/paths/export

Export all runs under a path as JSON metadata or a ZIP archive.

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string | **required** | Path prefix to match |
| `exact` | bool | `false` | If true, match exact path only |
| `format` | string | `json` | Export format: `json` or `zip` |

**Response** (`format=json`):
```json
{
  "path": "cv/yolo",
  "exact": false,
  "total_runs": 5,
  "runs": [
    {
      "run_id": "20250114_153045_a1b2c3",
      "path": "cv/yolo",
      "alias": "yolov8-baseline",
      "status": "finished",
      "created_time": 1736870400.0,
      "summary": { "best_metric_value": 0.95 },
      "meta": { ... }
    }
  ]
}
```

**Response** (`format=zip`): Binary ZIP file download containing:
- `index.json` — metadata index of all exported runs
- `{run_id}/` — full run directory contents for each run

**Examples**:
```bash
# Export metadata as JSON
GET /api/paths/export?path=cv/yolo&format=json

# Download full data as ZIP
GET /api/paths/export?path=cv/yolo&format=zip
```

---

## Legacy Endpoints

These endpoints provide backward compatibility by mapping the old project/name hierarchy to the new path-based system.

### GET /api/projects

Returns top-level path segments as "projects".

```json
{"projects": ["cv", "nlp", "rl"]}
```

### GET /api/projects/{project}/names

Returns second-level path segments under a project.

```json
{"names": ["resnet", "yolo", "vit"]}
```

### GET /api/projects/{project}/names/{name}/runs

Returns runs matching the path prefix `{project}/{name}`.

```json
[
  {
    "run_id": "20250114_153045_a1b2c3",
    "path": "cv/yolo",
    "alias": "yolov8-baseline",
    "status": "finished",
    "start_time": 1736870400.0
  }
]
```

---

**[Back to API Index](./API_INDEX.md)** | **[Back to Main](../../README.md)**
