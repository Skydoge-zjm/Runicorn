[English](runs_api.md) | [简体中文](../zh/runs_api.md)

---

# Runs API - Experiment Management

**Module**: Runs API  
**Base Path**: `/api/runs`  
**Version**: v1.0  
**Description**: Create, read, update, and manage experiment runs with soft delete and restore capabilities.

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/runs` | List all experiment runs |
| GET | `/runs/{run_id}` | Get detailed run information |
| POST | `/runs/soft-delete` | Soft delete runs (move to recycle bin) |
| GET | `/recycle-bin` | List deleted runs |
| POST | `/recycle-bin/restore` | Restore runs from recycle bin |
| POST | `/recycle-bin/empty` | Permanently delete all runs in recycle bin |

---

## List Runs

Get a list of all experiment runs with basic metadata.

### Request

```http
GET /api/runs
```

**Query Parameters**: None

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
[
  {
    "id": "20250114_153045_a1b2c3",
    "run_dir": "E:\\RunicornData\\image_classification\\resnet_baseline\\runs\\20250114_153045_a1b2c3",
    "created_time": 1704067200.5,
    "status": "finished",
    "pid": 12345,
    "best_metric_value": 0.9542,
    "best_metric_name": "accuracy",
    "project": "image_classification",
    "name": "resnet_baseline",
    "artifacts_created_count": 2,
    "artifacts_used_count": 1
  },
  {
    "id": "20250114_120000_d4e5f6",
    "run_dir": "E:\\RunicornData\\nlp\\bert_finetune\\runs\\20250114_120000_d4e5f6",
    "created_time": 1704053400.2,
    "status": "running",
    "pid": 23456,
    "best_metric_value": null,
    "best_metric_name": null,
    "project": "nlp",
    "name": "bert_finetune",
    "artifacts_created_count": 0,
    "artifacts_used_count": 0
  }
]
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique run identifier (format: YYYYMMDD_HHMMSS_XXXXXX) |
| `run_dir` | string | Absolute path to run directory |
| `created_time` | number | Unix timestamp of run creation |
| `status` | string | Run status: `running`, `finished`, `failed`, `interrupted` |
| `pid` | number\|null | Process ID (null if process ended) |
| `best_metric_value` | number\|null | Best metric value (if primary metric configured) |
| `best_metric_name` | string\|null | Name of the primary metric |
| `project` | string | Project name |
| `name` | string | Experiment name |
| `artifacts_created_count` | number | Number of artifacts created by this run |
| `artifacts_used_count` | number | Number of artifacts used by this run |

### Example

**cURL**:
```bash
curl http://127.0.0.1:23300/api/runs
```

**Python**:
```python
import requests

response = requests.get('http://127.0.0.1:23300/api/runs')
runs = response.json()

for run in runs:
    print(f"{run['id']}: {run['status']} - {run['best_metric_name']}={run['best_metric_value']}")
```

**JavaScript**:
```javascript
fetch('http://127.0.0.1:23300/api/runs')
  .then(res => res.json())
  .then(runs => {
    runs.forEach(run => {
      console.log(`${run.id}: ${run.status}`)
    })
  })
```

---

## Get Run Detail

Retrieve detailed information for a specific run.

### Request

```http
GET /api/runs/{run_id}
```

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `run_id` | string | Yes | Run identifier (format: YYYYMMDD_HHMMSS_XXXXXX) |

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "id": "20250114_153045_a1b2c3",
  "status": "finished",
  "pid": 12345,
  "run_dir": "E:\\RunicornData\\image_classification\\resnet_baseline\\runs\\20250114_153045_a1b2c3",
  "project": "image_classification",
  "name": "resnet_baseline",
  "logs": "E:\\RunicornData\\image_classification\\resnet_baseline\\runs\\20250114_153045_a1b2c3\\logs.txt",
  "metrics": "E:\\RunicornData\\image_classification\\resnet_baseline\\runs\\20250114_153045_a1b2c3\\events.jsonl",
  "metrics_step": "E:\\RunicornData\\image_classification\\resnet_baseline\\runs\\20250114_153045_a1b2c3\\events.jsonl",
  "artifacts_created_count": 2,
  "artifacts_used_count": 1
}
```

### Error Responses

**404 Not Found**:
```json
{
  "detail": "Run not found"
}
```

### Example

**cURL**:
```bash
curl http://127.0.0.1:23300/api/runs/20250114_153045_a1b2c3
```

**Python**:
```python
import requests

run_id = "20250114_153045_a1b2c3"
response = requests.get(f'http://127.0.0.1:23300/api/runs/{run_id}')

if response.status_code == 200:
    detail = response.json()
    print(f"Run {detail['id']}")
    print(f"Status: {detail['status']}")
    print(f"Project: {detail['project']}/{detail['name']}")
elif response.status_code == 404:
    print("Run not found")
```

---

## Soft Delete Runs

Move runs to recycle bin (soft delete) without permanently removing data.

### Request

```http
POST /api/runs/soft-delete
Content-Type: application/json
```

**Request Body**:
```json
{
  "run_ids": [
    "20250114_153045_a1b2c3",
    "20250114_120000_d4e5f6"
  ]
}
```

### Request Body Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `run_ids` | array[string] | Yes | List of run IDs to delete (max 100) |

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "deleted_count": 2,
  "results": {
    "20250114_153045_a1b2c3": {
      "success": true
    },
    "20250114_120000_d4e5f6": {
      "success": true
    }
  },
  "message": "Soft deleted 2 of 2 runs"
}
```

### Error Responses

**400 Bad Request** (invalid input):
```json
{
  "detail": "run_ids is required and must be a list"
}
```

**400 Bad Request** (batch size exceeded):
```json
{
  "detail": "Cannot delete more than 100 runs at once"
}
```

**400 Bad Request** (invalid run_id format):
```json
{
  "detail": "Invalid run_id format: abc123"
}
```

### Example

**cURL**:
```bash
curl -X POST http://127.0.0.1:23300/api/runs/soft-delete \
  -H "Content-Type: application/json" \
  -d '{
    "run_ids": ["20250114_153045_a1b2c3", "20250114_120000_d4e5f6"]
  }'
```

**Python**:
```python
import requests

run_ids = ["20250114_153045_a1b2c3", "20250114_120000_d4e5f6"]

response = requests.post(
    'http://127.0.0.1:23300/api/runs/soft-delete',
    json={"run_ids": run_ids}
)

result = response.json()
print(f"Deleted {result['deleted_count']} runs")

# Check individual results
for run_id, status in result['results'].items():
    if status['success']:
        print(f"✓ Deleted {run_id}")
    else:
        print(f"✗ Failed to delete {run_id}: {status.get('error')}")
```

---

## List Deleted Runs

Get all runs in the recycle bin.

### Request

```http
GET /api/recycle-bin
```

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "deleted_runs": [
    {
      "id": "20250114_153045_a1b2c3",
      "project": "image_classification",
      "name": "resnet_baseline",
      "created_time": 1704067200.5,
      "deleted_at": 1704070800.2,
      "delete_reason": "user_deleted",
      "original_status": "finished",
      "run_dir": "E:\\RunicornData\\image_classification\\resnet_baseline\\runs\\20250114_153045_a1b2c3"
    }
  ]
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Run identifier |
| `project` | string | Project name |
| `name` | string | Experiment name |
| `created_time` | number | Original creation timestamp |
| `deleted_at` | number | Deletion timestamp |
| `delete_reason` | string | Reason for deletion |
| `original_status` | string | Status before deletion |
| `run_dir` | string | Path to run directory |

---

## Restore Runs

Restore runs from recycle bin.

### Request

```http
POST /api/recycle-bin/restore
Content-Type: application/json
```

**Request Body**:
```json
{
  "run_ids": [
    "20250114_153045_a1b2c3"
  ]
}
```

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "restored_count": 1,
  "results": {
    "20250114_153045_a1b2c3": {
      "success": true
    }
  },
  "message": "Restored 1 of 1 runs"
}
```

### Example

**Python**:
```python
import requests

run_ids = ["20250114_153045_a1b2c3"]

response = requests.post(
    'http://127.0.0.1:23300/api/recycle-bin/restore',
    json={"run_ids": run_ids}
)

result = response.json()
print(f"Restored {result['restored_count']} runs")
```

---

## Empty Recycle Bin

Permanently delete all runs in recycle bin.

### Request

```http
POST /api/recycle-bin/empty
Content-Type: application/json
```

**Request Body**:
```json
{
  "confirm": true
}
```

### Request Body Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `confirm` | boolean | Yes | Must be `true` to proceed with permanent deletion |

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "permanently_deleted": 15,
  "message": "Permanently deleted 15 runs"
}
```

### Error Responses

**400 Bad Request** (missing confirmation):
```json
{
  "detail": "Must set confirm=true to permanently delete"
}
```

### Example

**cURL**:
```bash
curl -X POST http://127.0.0.1:23300/api/recycle-bin/empty \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}'
```

**Python** (with confirmation prompt):
```python
import requests

# Ask user for confirmation
confirm = input("Permanently delete all runs in recycle bin? (yes/no): ")

if confirm.lower() == 'yes':
    response = requests.post(
        'http://127.0.0.1:23300/api/recycle-bin/empty',
        json={"confirm": True}
    )
    
    result = response.json()
    print(result['message'])
else:
    print("Operation cancelled")
```

---

## Data Models

### RunListItem

```typescript
interface RunListItem {
  id: string                        // Run ID
  run_dir: string | null            // Path to run directory
  created_time: number | null       // Unix timestamp
  status: "running" | "finished" | "failed" | "interrupted"
  pid: number | null                // Process ID
  best_metric_value: number | null  // Best metric value
  best_metric_name: string | null   // Primary metric name
  project: string | null            // Project name
  name: string | null               // Experiment name
  artifacts_created_count: number   // Number of artifacts created
  artifacts_used_count: number      // Number of artifacts used
}
```

### DeletedRun

```typescript
interface DeletedRun {
  id: string              // Run ID
  project: string         // Project name
  name: string            // Experiment name
  created_time: number    // Original creation timestamp
  deleted_at: number      // Deletion timestamp
  delete_reason: string   // Deletion reason
  original_status: string // Status before deletion
  run_dir: string         // Path to run directory
}
```

---

## Best Practices

### Batch Operations

When deleting or restoring multiple runs:

```python
# ✅ Good: Batch operation (efficient)
run_ids = ["run1", "run2", "run3", ..., "run100"]  # Up to 100
requests.post('/api/runs/soft-delete', json={"run_ids": run_ids})

# ❌ Bad: Individual operations (slow)
for run_id in run_ids:
    requests.post('/api/runs/soft-delete', json={"run_ids": [run_id]})
```

### Handling Large Result Sets

```python
import requests

# Get all runs
all_runs = requests.get('http://127.0.0.1:23300/api/runs').json()

# Filter client-side for V1 API
running_runs = [r for r in all_runs if r['status'] == 'running']

# Recommendation: Use V2 API for server-side filtering
# See docs/api/v2_api.md
```

### Status Management

**Automatic Status Detection**: The API automatically updates the status of runs marked as `running` when the process is no longer active.

```python
# The API checks if PID is still alive
# If not, status is automatically updated to "failed"
# with exit_reason: "process_not_found"

# Background task: Runs every 30 seconds
# On-demand: When listing runs with status="running"
```

---

## Error Codes

| Status Code | Scenario | Action |
|-------------|----------|--------|
| `400` | Invalid run_id format | Check ID format: YYYYMMDD_HHMMSS_XXXXXX |
| `400` | Batch size > 100 | Split into multiple batches |
| `400` | Missing run_ids | Include run_ids array in request body |
| `404` | Run not found | Verify run_id exists via GET /runs |
| `500` | Server error | Check server logs, retry request |

---

## Rate Limits

- **GET /runs**: 100 requests per minute
- **POST /runs/soft-delete**: 20 requests per minute
- **POST /recycle-bin/empty**: 5 requests per minute

---

## Notes

### Soft Delete vs Permanent Delete

**Soft Delete** (Recycle Bin):
- Creates `.deleted` marker file in run directory
- Run is hidden from main list
- All data remains intact
- Can be restored at any time

**Permanent Delete**:
- Physically removes run directory
- **Irreversible** - all data is lost
- Only available via `/recycle-bin/empty`

### File Structure

After soft delete, run directory contains:
```
runs/20250114_153045_a1b2c3/
├── meta.json
├── status.json
├── events.jsonl
├── logs.txt
└── .deleted        ← Soft delete marker
    {
      "deleted_at": 1704070800.2,
      "reason": "user_deleted",
      "original_status": "finished"
    }
```

---

## Related APIs

- **Metrics API**: Get run metrics data - [metrics_api.md](./metrics_api.md)
- **V2 Experiments API**: High-performance queries - [v2_api.md](./v2_api.md)
- **Artifacts API**: Manage run artifacts - [artifacts_api.md](./artifacts_api.md)

---

**Last Updated**: 2025-10-14

