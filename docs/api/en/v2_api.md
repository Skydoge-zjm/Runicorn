[English](v2_api.md) | [简体中文](../zh/v2_api.md)

---

# V2 API - High-Performance Queries

**Module**: V2 API (Next-Generation)  
**Base Path**: `/api/v2`  
**Version**: v2.0  
**Backend**: SQLite with optimized indexes  
**Performance**: 50-500x faster than V1 API

---

## Overview

The V2 API provides high-performance experiment queries using SQLite backend instead of file system scanning.

### V1 vs V2 Comparison

| Feature | V1 API | V2 API | Improvement |
|---------|--------|--------|-------------|
| **List 1000 experiments** | 5-10 seconds | 50-100 ms | **100x faster** |
| **Complex filtering** | Not supported | Supported | ✓ |
| **Pagination** | Client-side | Server-side | ✓ |
| **Search** | Not supported | Full-text search | ✓ |
| **Sorting** | Client-side | Server-side (indexed) | ✓ |

### When to Use V2

✅ **Use V2 API when**:
- You have 1000+ experiments
- You need advanced filtering
- Performance is critical
- You need server-side pagination

⚠️ **Use V1 API when**:
- You need backward compatibility
- You're working with legacy systems
- You prefer file-based queries

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v2/experiments` | List experiments with advanced filtering |
| GET | `/v2/experiments/{exp_id}` | Get experiment detail with metrics summary |
| GET | `/v2/experiments/{exp_id}/metrics/fast` | High-performance metrics retrieval |
| POST | `/v2/experiments/batch-delete` | Batch soft delete (up to 1000) |
| GET | `/v2/analytics/summary` | Aggregated analytics |

---

## List Experiments

Advanced experiment listing with server-side filtering, pagination, and sorting.

### Request

```http
GET /api/v2/experiments?{query_params}
```

### Query Parameters

#### Filtering Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `project` | string | Filter by project name | `image_classification` |
| `name` | string | Filter by experiment name | `resnet_baseline` |
| `status` | string | Filter by status (comma-separated) | `finished,failed` |
| `tags` | string | Filter by tags (comma-separated) | `baseline,production` |
| `search` | string | Full-text search in project/name/description | `resnet` |
| `created_after` | number | Unix timestamp (inclusive) | `1704067200` |
| `created_before` | number | Unix timestamp (inclusive) | `1704153600` |
| `best_metric_min` | number | Minimum best metric value | `0.9` |
| `best_metric_max` | number | Maximum best metric value | `1.0` |
| `include_deleted` | boolean | Include soft-deleted experiments | `false` |

#### Pagination Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | number | 1 | Page number (1-based) |
| `per_page` | number | 50 | Results per page (1-1000) |

#### Sorting Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `order_by` | string | `created_at` | Sort field: `created_at`, `updated_at`, `best_metric_value`, `status` |
| `order_desc` | boolean | true | Sort descending (true) or ascending (false) |

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "experiments": [
    {
      "id": "20250114_153045_a1b2c3",
      "project": "image_classification",
      "name": "resnet_baseline",
      "status": "finished",
      "created_at": 1704067200.0,
      "best_metric_name": "accuracy",
      "best_metric_value": 0.9542,
      "pid": 12345,
      "run_dir": "E:\\RunicornData\\..."
    }
  ],
  "total": 237,
  "page": 1,
  "per_page": 50,
  "has_next": true,
  "has_prev": false,
  "query_time_ms": 12.34
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `experiments` | array | List of experiment objects |
| `total` | number | Total number of matching experiments |
| `page` | number | Current page number |
| `per_page` | number | Results per page |
| `has_next` | boolean | Whether there's a next page |
| `has_prev` | boolean | Whether there's a previous page |
| `query_time_ms` | number | Query execution time in milliseconds |

### Examples

**Example 1**: Get finished experiments from last week
```bash
curl "http://127.0.0.1:23300/api/v2/experiments?\
status=finished&\
created_after=1703980800&\
page=1&\
per_page=20&\
order_by=created_at&\
order_desc=true"
```

**Example 2**: Search for "baseline" experiments with high accuracy
```python
import requests

response = requests.get('http://127.0.0.1:23300/api/v2/experiments', params={
    'search': 'baseline',
    'best_metric_min': 0.9,
    'status': 'finished',
    'page': 1,
    'per_page': 50,
    'order_by': 'best_metric_value',
    'order_desc': True
})

data = response.json()

print(f"Found {data['total']} experiments")
print(f"Query time: {data['query_time_ms']} ms")

for exp in data['experiments']:
    print(f"{exp['id']}: {exp['best_metric_name']}={exp['best_metric_value']:.4f}")
```

**Example 3**: Pagination
```python
import requests

def get_all_experiments(project=None, per_page=100):
    """Fetch all experiments with pagination"""
    experiments = []
    page = 1
    
    while True:
        response = requests.get('http://127.0.0.1:23300/api/v2/experiments', params={
            'project': project,
            'page': page,
            'per_page': per_page
        })
        
        data = response.json()
        experiments.extend(data['experiments'])
        
        if not data['has_next']:
            break
        
        page += 1
    
    return experiments

# Usage
all_exps = get_all_experiments(project="image_classification")
print(f"Total: {len(all_exps)} experiments")
```

---

## Get Experiment Detail

Get detailed experiment information with metrics summary.

### Request

```http
GET /api/v2/experiments/{exp_id}
```

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `exp_id` | string | Yes | Experiment ID |

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "experiment": {
    "id": "20250114_153045_a1b2c3",
    "project": "image_classification",
    "name": "resnet_baseline",
    "status": "finished",
    "created_at": 1704067200.0,
    "ended_at": 1704070800.0,
    "best_metric_value": 0.9542,
    "best_metric_name": "accuracy",
    "run_dir": "E:\\RunicornData\\..."
  },
  "metrics_summary": {
    "total_data_points": 1000,
    "available_metrics": ["loss", "accuracy", "learning_rate"],
    "step_range": {
      "min": 1,
      "max": 1000
    }
  },
  "environment_available": true,
  "file_count": 15
}
```

---

## Fast Metrics Retrieval

High-performance metrics query with advanced filtering and downsampling.

### Request

```http
GET /api/v2/experiments/{exp_id}/metrics/fast?{params}
```

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `exp_id` | string | Yes | Experiment ID |

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metric_names` | string | No | Specific metrics (comma-separated) |
| `step_range` | string | No | Step range filter (format: "min:max") |
| `downsample` | number | No | Downsample to N points |

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "columns": ["global_step", "loss", "accuracy"],
  "rows": [
    {
      "global_step": 1,
      "loss": 2.3025,
      "accuracy": 0.1234
    },
    {
      "global_step": 10,
      "loss": 0.8543,
      "accuracy": 0.7821
    }
  ],
  "query_time_ms": 8.45,
  "total_points": 100,
  "applied_filters": {
    "metrics": ["loss", "accuracy"],
    "step_range": null,
    "downsampled": false
  }
}
```

### Examples

**Example 1**: Get specific metrics
```bash
curl "http://127.0.0.1:23300/api/v2/experiments/20250114_153045_a1b2c3/metrics/fast?\
metric_names=loss,accuracy"
```

**Example 2**: Filter by step range
```python
import requests

response = requests.get(
    'http://127.0.0.1:23300/api/v2/experiments/20250114_153045_a1b2c3/metrics/fast',
    params={
        'metric_names': 'loss,accuracy',
        'step_range': '100:500',  # Steps 100 to 500
    }
)

data = response.json()
print(f"Query time: {data['query_time_ms']} ms")
print(f"Data points: {data['total_points']}")
```

**Example 3**: Downsample for visualization
```python
import requests
import matplotlib.pyplot as plt

# Get metrics with downsampling
response = requests.get(
    'http://127.0.0.1:23300/api/v2/experiments/20250114_153045_a1b2c3/metrics/fast',
    params={
        'metric_names': 'accuracy',
        'downsample': 100  # Reduce to 100 points
    }
)

data = response.json()

# Extract data
steps = [row['global_step'] for row in data['rows']]
accuracy = [row['accuracy'] for row in data['rows']]

# Plot
plt.plot(steps, accuracy)
plt.xlabel('Step')
plt.ylabel('Accuracy')
plt.title('Training Accuracy')
plt.show()
```

---

## Batch Delete

High-performance batch soft delete operation (up to 1000 experiments).

### Request

```http
POST /api/v2/experiments/batch-delete
Content-Type: application/json
```

**Request Body**:
```json
{
  "exp_ids": [
    "20250114_153045_a1b2c3",
    "20250114_120000_d4e5f6"
  ],
  "reason": "cleanup_old_experiments"
}
```

### Request Body Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `exp_ids` | array[string] | Yes | List of experiment IDs (max 1000) |
| `reason` | string | No | Deletion reason (default: "user_batch_delete") |

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "deleted": 2,
  "failed": 0,
  "results": {
    "20250114_153045_a1b2c3": true,
    "20250114_120000_d4e5f6": true
  }
}
```

### Error Responses

**400 Bad Request** (too many experiments):
```json
{
  "detail": "Cannot delete more than 1000 experiments at once"
}
```

---

## Performance Metrics

### Benchmarks

Tested on: Windows 10, SSD, 10,000 experiments

| Operation | V1 API | V2 API | Speedup |
|-----------|--------|--------|---------|
| List all | 5.2 s | 52 ms | 100x |
| Filter by project | 5.8 s | 45 ms | 129x |
| Filter by status | 6.1 s | 38 ms | 161x |
| Sort by metric | 7.3 s | 68 ms | 107x |
| Complex query (4 filters) | 8.5 s | 85 ms | 100x |
| Pagination (page 2) | 5.2 s | 18 ms | 289x |

### Query Time Tracking

Every V2 API response includes `query_time_ms` for performance monitoring:

```python
import requests
import statistics

query_times = []

for i in range(10):
    response = requests.get('http://127.0.0.1:23300/api/v2/experiments', params={
        'page': i + 1,
        'per_page': 50
    })
    
    data = response.json()
    query_times.append(data['query_time_ms'])

print(f"Average query time: {statistics.mean(query_times):.2f} ms")
print(f"P95: {statistics.quantiles(query_times, n=20)[18]:.2f} ms")
```

---

## Migration Guide

### Migrating from V1 to V2

**V1 Code** (slow):
```javascript
// Old way: Client-side filtering
const response = await fetch('/api/runs')
const allRuns = await response.json()

// Filter client-side
const finishedRuns = allRuns.filter(r => r.status === 'finished')
const sorted = finishedRuns.sort((a, b) => b.created_time - a.created_time)
const page1 = sorted.slice(0, 50)
```

**V2 Code** (fast):
```javascript
// New way: Server-side everything
const response = await fetch('/api/v2/experiments?' + new URLSearchParams({
  status: 'finished',
  order_by: 'created_at',
  order_desc: 'true',
  page: '1',
  per_page: '50'
}))

const data = await response.json()
const experiments = data.experiments  // Already filtered, sorted, paginated
```

### Feature Mapping

| V1 Feature | V2 Equivalent | Notes |
|------------|---------------|-------|
| `GET /runs` | `GET /v2/experiments` | Add `page` and `per_page` params |
| Client filtering | `?project=X&status=Y` | Server-side filters |
| Client sorting | `?order_by=X&order_desc=true` | Server-side sorting |
| N/A | `?search=text` | New: full-text search |
| `GET /runs/{id}` | `GET /v2/experiments/{id}` | Enhanced response |

---

## Advanced Query Examples

### Example 1: Complex Multi-Filter Query

```python
import requests
from datetime import datetime, timedelta

# Find finished experiments from last 7 days with accuracy > 0.9
one_week_ago = (datetime.now() - timedelta(days=7)).timestamp()

response = requests.get('http://127.0.0.1:23300/api/v2/experiments', params={
    'status': 'finished',
    'created_after': one_week_ago,
    'best_metric_min': 0.9,
    'order_by': 'best_metric_value',
    'order_desc': True,
    'page': 1,
    'per_page': 20
})

data = response.json()

print(f"Found {data['total']} experiments (showing {len(data['experiments'])})")
print(f"Query time: {data['query_time_ms']} ms")

for exp in data['experiments']:
    print(f"{exp['name']}: {exp['best_metric_value']:.4f}")
```

### Example 2: Efficient Pagination UI

```javascript
// React component with V2 pagination
import { useState, useEffect } from 'react'

function ExperimentList() {
  const [experiments, setExperiments] = useState([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const perPage = 50
  
  useEffect(() => {
    async function fetchData() {
      const response = await fetch(`/api/v2/experiments?page=${page}&per_page=${perPage}`)
      const data = await response.json()
      
      setExperiments(data.experiments)
      setTotal(data.total)
      
      // Show query performance
      console.log(`Query time: ${data.query_time_ms} ms`)
    }
    
    fetchData()
  }, [page])
  
  return (
    <div>
      <h2>Experiments ({total} total)</h2>
      
      {experiments.map(exp => (
        <div key={exp.id}>{exp.name}</div>
      ))}
      
      {/* Pagination controls */}
      <button 
        onClick={() => setPage(p => p - 1)} 
        disabled={page === 1}
      >
        Previous
      </button>
      
      <span>Page {page} of {Math.ceil(total / perPage)}</span>
      
      <button 
        onClick={() => setPage(p => p + 1)} 
        disabled={page * perPage >= total}
      >
        Next
      </button>
    </div>
  )
}
```

### Example 3: Real-time Search

```python
import requests
import time

def search_experiments(query_text, debounce_ms=300):
    """Search with debouncing"""
    time.sleep(debounce_ms / 1000)
    
    response = requests.get('http://127.0.0.1:23300/api/v2/experiments', params={
        'search': query_text,
        'page': 1,
        'per_page': 10
    })
    
    data = response.json()
    
    print(f"Search '{query_text}': {data['total']} results ({data['query_time_ms']} ms)")
    
    return data['experiments']

# Usage
results = search_experiments("resnet")
```

---

## SQL Query Insights

### Query Construction

The V2 API translates parameters to optimized SQL:

**API Request**:
```
GET /api/v2/experiments?
  project=image_classification&
  status=finished,failed&
  created_after=1704067200&
  best_metric_min=0.9&
  order_by=best_metric_value&
  order_desc=true&
  page=2&
  per_page=50
```

**Generated SQL** (simplified):
```sql
SELECT * FROM experiments
WHERE project = 'image_classification'
  AND status IN ('finished', 'failed')
  AND created_at >= 1704067200
  AND best_metric_value >= 0.9
  AND deleted_at IS NULL
ORDER BY best_metric_value DESC
LIMIT 50 OFFSET 50;
```

### Index Usage

The V2 API leverages these indexes for fast queries:

```sql
-- Project filter
CREATE INDEX idx_experiments_project ON experiments(project);

-- Status filter
CREATE INDEX idx_experiments_status ON experiments(status);

-- Time range
CREATE INDEX idx_experiments_created_at ON experiments(created_at);

-- Best metric
CREATE INDEX idx_experiments_best_metric 
ON experiments(best_metric_name, best_metric_value);

-- Soft delete
CREATE INDEX idx_experiments_deleted_at ON experiments(deleted_at);
```

---

## Error Handling

### Standard Errors

**400 Bad Request**:
```json
{
  "detail": "Invalid step_range format, use 'min:max'"
}
```

**404 Not Found**:
```json
{
  "detail": "Experiment 20250114_999999_zzz999 not found"
}
```

**500 Internal Server Error**:
```json
{
  "detail": "Database query failed: timeout"
}
```

### Handling Errors

```python
import requests

try:
    response = requests.get(
        'http://127.0.0.1:23300/api/v2/experiments',
        params={'page': 1, 'per_page': 50},
        timeout=10
    )
    
    response.raise_for_status()  # Raise exception for 4xx/5xx
    
    data = response.json()
    
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 400:
        print(f"Bad request: {e.response.json()['detail']}")
    elif e.response.status_code == 404:
        print("Experiment not found")
    elif e.response.status_code == 500:
        print("Server error, please try again later")
    else:
        print(f"HTTP error: {e}")
        
except requests.exceptions.Timeout:
    print("Request timeout, server may be busy")
    
except requests.exceptions.RequestException as e:
    print(f"Network error: {e}")
```

---

## Rate Limits

V2 API has higher rate limits due to better performance:

| Endpoint | Limit | Window |
|----------|-------|--------|
| `GET /v2/experiments` | 100 requests | 60 seconds |
| `GET /v2/experiments/{id}` | 200 requests | 60 seconds |
| `GET /v2/experiments/{id}/metrics/fast` | 100 requests | 60 seconds |
| `POST /v2/experiments/batch-delete` | 10 requests | 60 seconds |

---

## Best Practices

### 1. Use Server-Side Filtering

```python
# ✅ Good: Server-side filtering (fast)
response = requests.get('/api/v2/experiments', params={
    'project': 'my_project',
    'status': 'finished'
})

# ❌ Bad: Client-side filtering (slow)
all_runs = requests.get('/api/runs').json()
filtered = [r for r in all_runs if r['project'] == 'my_project' and r['status'] == 'finished']
```

### 2. Use Pagination

```python
# ✅ Good: Paginated requests
for page in range(1, 11):
    data = requests.get('/api/v2/experiments', params={'page': page, 'per_page': 100}).json()
    process(data['experiments'])

# ❌ Bad: Load all at once
all_data = requests.get('/api/runs').json()  # May timeout with 10,000+ experiments
```

### 3. Monitor Query Performance

```python
import requests

response = requests.get('/api/v2/experiments', params={'page': 1, 'per_page': 50})
data = response.json()

# Log slow queries
if data['query_time_ms'] > 100:
    print(f"⚠️ Slow query: {data['query_time_ms']} ms")
    print(f"Consider adding indexes or optimizing filters")
```

---

## Related APIs

- **Runs API (V1)**: Backward compatible - [runs_api.md](./runs_api.md)
- **Metrics API**: Detailed metrics queries - [metrics_api.md](./metrics_api.md)

---

**Last Updated**: 2025-10-14

