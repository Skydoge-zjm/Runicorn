[English](QUICK_REFERENCE.md) | [简体中文](../zh/QUICK_REFERENCE.md)

---

# Runicorn API Quick Reference

**Version**: v0.5.4  
**Base URL**: `http://127.0.0.1:23300/api`

---

## Quick Start (30 seconds)

```bash
# 1. Start Runicorn
runicorn viewer

# 2. Test API
curl http://127.0.0.1:23300/api/health

# 3. List experiments
curl http://127.0.0.1:23300/api/runs
```

---

## Most Used Endpoints

### Experiments

```bash
# List all runs
GET /api/runs

# Get run details
GET /api/runs/{run_id}

# Get metrics (step-based)
GET /api/runs/{run_id}/metrics_step

# Delete runs (soft)
POST /api/runs/soft-delete
Body: {"run_ids": ["run1", "run2"]}
```

### Artifacts

```bash
# List artifacts
GET /api/artifacts?type=model

# Get versions
GET /api/artifacts/{name}/versions

# Get version details
GET /api/artifacts/{name}/v{version}

# Get lineage graph
GET /api/artifacts/{name}/v{version}/lineage
```

### V2 API (High Performance)

```bash
# Advanced query
GET /api/v2/experiments?project=demo&status=finished&page=1&per_page=50

# Fast metrics
GET /api/v2/experiments/{id}/metrics/fast?downsample=1000
```

### Configuration

```bash
# Get config
GET /api/config

# Set storage root
POST /api/config/user_root_dir
Body: {"path": "E:\\RunicornData"}
```

### Remote Viewer API 🆕

```bash
# Connect to remote server
POST /api/remote/connect
Body: {"host": "gpu-server.com", "port": 22, "username": "user", "password": null, "private_key": null, "private_key_path": "~/.ssh/id_rsa", "passphrase": null, "use_agent": true}

# List Python environments
GET /api/remote/conda-envs?connection_id=user@gpu-server.com:22

# Start Remote Viewer
POST /api/remote/viewer/start
Body: {"host": "gpu-server.com", "port": 22, "username": "user", "password": null, "private_key": null, "private_key_path": "~/.ssh/id_rsa", "passphrase": null, "use_agent": true, "remote_root": "/data/experiments", "local_port": null, "remote_port": null, "conda_env": null}

# Get Viewer status
GET /api/remote/viewer/status/{session_id}

# List SSH sessions
GET /api/remote/sessions

# Disconnect
POST /api/remote/disconnect
Body: {"host": "gpu-server.com", "port": 22, "username": "user"}
```

---

## Response Formats

### Success Response

```json
{
  "ok": true,
  "data": { ... },
  "message": "Operation successful"
}
```

### Error Response

```json
{
  "detail": "Error description"
}
```

---

## Common Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 400 | Bad Request | Check parameters |
| 404 | Not Found | Verify resource exists |
| 429 | Rate Limited | Wait and retry |
| 500 | Server Error | Check logs, retry |

---

## Rate Limits

| Endpoint Type | Limit |
|---------------|-------|
| Standard | 60/min |
| V2 Queries | 100/min |
| SSH Connect | 5/min |
| Batch Delete | 10/min |

**Headers**:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 15
```

---

## Python Quick Examples

### List and Filter

```python
import requests

# Get all finished runs
runs = requests.get('http://127.0.0.1:23300/api/runs').json()
finished = [r for r in runs if r['status'] == 'finished']
```

### Get Metrics and Plot

```python
import requests
import matplotlib.pyplot as plt

metrics = requests.get(f'http://127.0.0.1:23300/api/runs/{run_id}/metrics_step').json()

steps = [row['global_step'] for row in metrics['rows']]
loss = [row['loss'] for row in metrics['rows']]

plt.plot(steps, loss)
plt.show()
```

### Stream Logs

```python
import asyncio
import websockets

async def stream_logs(run_id):
    uri = f"ws://127.0.0.1:23300/api/runs/{run_id}/logs/ws"
    async with websockets.connect(uri) as ws:
        while True:
            print(await ws.recv())

asyncio.run(stream_logs("20250114_153045_a1b2c3"))
```

---

## JavaScript Quick Examples

### Fetch Runs

```javascript
const response = await fetch('http://127.0.0.1:23300/api/runs')
const runs = await response.json()

runs.forEach(run => {
  console.log(`${run.id}: ${run.status}`)
})
```

### WebSocket Logs

```javascript
const ws = new WebSocket('ws://127.0.0.1:23300/api/runs/{run_id}/logs/ws')

ws.onmessage = (event) => {
  console.log(event.data)
}
```

---

## Data Types

### Run ID Format

```
YYYYMMDD_HHMMSS_XXXXXX

Examples:
- 20250114_153045_a1b2c3
- 20241225_090000_xyz789
```

### Timestamps

All timestamps are **Unix timestamps** (seconds since epoch):

```python
import time
from datetime import datetime

# Current timestamp
ts = time.time()  # 1704067200.5

# Convert to datetime
dt = datetime.fromtimestamp(ts)  # 2025-10-14 15:30:45

# Convert from datetime
ts = dt.timestamp()  # 1704067200.5
```

### File Sizes

All sizes in **bytes**:

```python
# Convert bytes to human-readable
def format_bytes(bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024

# 102400000 bytes → "97.66 MB"
```

---

## Environment Variables

```bash
# API base URL (for development)
export VITE_API_BASE="http://localhost:23300/api"

# Storage root
export RUNICORN_DIR="E:\\RunicornData"

# Disable modern storage (testing)
export RUNICORN_DISABLE_MODERN_STORAGE=1
```

---

## Troubleshooting

### API Not Responding

```bash
# Check if viewer is running
curl http://127.0.0.1:23300/api/health

# Start viewer if not running
runicorn viewer --host 127.0.0.1 --port 23300
```

### CORS Errors (from browser)

The API allows CORS from all origins. If you still get CORS errors:

```javascript
// Add mode: 'cors' explicitly
fetch('http://127.0.0.1:23300/api/runs', {
  mode: 'cors',
  headers: {
    'Content-Type': 'application/json'
  }
})
```

### Large Response Timeouts

```python
import requests

# Increase timeout for large datasets
response = requests.get(
    'http://127.0.0.1:23300/api/runs',
    timeout=60  # 60 seconds
)
```

---

## Full Documentation

For detailed API documentation, see:

- **[README.md](./README.md)** - API overview and getting started
- **[runs_api.md](./runs_api.md)** - Experiment management
- **[artifacts_api.md](./artifacts_api.md)** - Model version control
- **[v2_api.md](./v2_api.md)** - High-performance queries
- **[metrics_api.md](./metrics_api.md)** - Metrics and logs
- **[config_api.md](./config_api.md)** - Configuration
- **[remote_api.md](./remote_api.md)** - Remote Viewer API 🆕

---

**Interactive API Docs**: `http://127.0.0.1:23300/docs` (FastAPI auto-generated)

---

**Last Updated**: 2025-10-25

