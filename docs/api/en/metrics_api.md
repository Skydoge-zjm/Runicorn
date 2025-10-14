[English](metrics_api.md) | [简体中文](../zh/metrics_api.md)

---

# Metrics API - Training Metrics Queries

**Module**: Metrics API  
**Base Path**: `/api/runs/{run_id}`  
**Version**: v1.0  
**Description**: Query training metrics, progress, and real-time logs via HTTP and WebSocket.

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/runs/{run_id}/metrics` | Get metrics aggregated by timestamp |
| GET | `/runs/{run_id}/metrics_step` | Get metrics aggregated by step |
| GET | `/runs/{run_id}/progress` | Get training progress (deprecated) |
| WS | `/runs/{run_id}/logs/ws` | Real-time log streaming via WebSocket |

---

## Get Metrics (Time-based)

Retrieve metrics aggregated by timestamp.

### Request

```http
GET /api/runs/{run_id}/metrics
```

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `run_id` | string | Yes | Run identifier |

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "columns": ["time", "loss", "accuracy", "learning_rate"],
  "rows": [
    {
      "time": 0.0,
      "loss": 2.3025,
      "accuracy": 0.1234,
      "learning_rate": 0.001
    },
    {
      "time": 1.5,
      "loss": 1.8543,
      "accuracy": 0.3567,
      "learning_rate": 0.001
    },
    {
      "time": 3.2,
      "loss": 1.2134,
      "accuracy": 0.6789,
      "learning_rate": 0.001
    }
  ]
}
```

### Response Format

| Field | Type | Description |
|-------|------|-------------|
| `columns` | array[string] | Metric names |
| `rows` | array[object] | Metric data points |

**Row Structure**:
- `time`: Relative time in seconds (normalized to start from 0)
- Other fields: Metric values

### Example

**Python** (plot metrics):
```python
import requests
import matplotlib.pyplot as plt

run_id = "20250114_153045_a1b2c3"
response = requests.get(f'http://127.0.0.1:23300/api/runs/{run_id}/metrics')
data = response.json()

# Extract data
time_values = [row['time'] for row in data['rows']]
loss_values = [row['loss'] for row in data['rows']]
acc_values = [row['accuracy'] for row in data['rows']]

# Plot
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

ax1.plot(time_values, loss_values)
ax1.set_ylabel('Loss')
ax1.set_title('Training Loss')

ax2.plot(time_values, acc_values)
ax2.set_xlabel('Time (seconds)')
ax2.set_ylabel('Accuracy')
ax2.set_title('Training Accuracy')

plt.tight_layout()
plt.show()
```

---

## Get Step Metrics

Retrieve metrics aggregated by training step (recommended for ML).

### Request

```http
GET /api/runs/{run_id}/metrics_step
```

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `run_id` | string | Yes | Run identifier |

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "columns": ["global_step", "loss", "accuracy", "learning_rate", "stage"],
  "rows": [
    {
      "global_step": 1,
      "loss": 2.3025,
      "accuracy": 0.1234,
      "learning_rate": 0.001,
      "stage": "warmup"
    },
    {
      "global_step": 10,
      "loss": 1.8543,
      "accuracy": 0.3567,
      "learning_rate": 0.001,
      "stage": "warmup"
    },
    {
      "global_step": 50,
      "loss": 0.8432,
      "accuracy": 0.7821,
      "learning_rate": 0.001,
      "stage": "train"
    }
  ]
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `global_step` | number | Training step number |
| `stage` | string | Training stage: `warmup`, `train`, `eval`, etc. |
| Other fields | number | Metric values |

### Example

**Python** (step-based analysis):
```python
import requests
import pandas as pd

run_id = "20250114_153045_a1b2c3"
response = requests.get(f'http://127.0.0.1:23300/api/runs/{run_id}/metrics_step')
data = response.json()

# Convert to DataFrame for analysis
df = pd.DataFrame(data['rows'])

# Analyze by stage
for stage in df['stage'].unique():
    stage_data = df[df['stage'] == stage]
    
    print(f"\nStage: {stage}")
    print(f"  Steps: {stage_data['global_step'].min()} - {stage_data['global_step'].max()}")
    print(f"  Final loss: {stage_data['loss'].iloc[-1]:.4f}")
    print(f"  Final accuracy: {stage_data['accuracy'].iloc[-1]:.4f}")

# Find best accuracy
best_idx = df['accuracy'].idxmax()
best_row = df.loc[best_idx]

print(f"\nBest accuracy: {best_row['accuracy']:.4f} at step {best_row['global_step']}")
```

---

## Real-time Log Streaming

Stream training logs in real-time via WebSocket.

### Connection

```
ws://127.0.0.1:23300/api/runs/{run_id}/logs/ws
```

**Protocol**: WebSocket  
**Format**: Plain text (one line per message)

### Message Flow

```
Client → Server: (WebSocket connection established)
Server → Client: "12:34:56 | Starting training..."
Server → Client: "12:34:57 | Epoch 1/100"
Server → Client: "12:34:58 | Batch 1/1000, loss=2.30"
...
```

### Example

**Python** (websockets library):
```python
import asyncio
import websockets

async def stream_logs(run_id):
    """Stream logs in real-time"""
    
    uri = f"ws://127.0.0.1:23300/api/runs/{run_id}/logs/ws"
    
    async with websockets.connect(uri) as websocket:
        print(f"Connected to {run_id} logs\n")
        
        try:
            while True:
                message = await websocket.recv()
                print(message)
                
        except websockets.exceptions.ConnectionClosed:
            print("\nConnection closed")

# Usage
run_id = "20250114_153045_a1b2c3"
asyncio.run(stream_logs(run_id))
```

**JavaScript** (browser):
```javascript
function streamLogs(runId) {
  const ws = new WebSocket(`ws://127.0.0.1:23300/api/runs/${runId}/logs/ws`)
  
  ws.onopen = () => {
    console.log('Connected to log stream')
  }
  
  ws.onmessage = (event) => {
    // Append log line to UI
    const logLine = event.data
    console.log(logLine)
    
    // Or update DOM
    const logContainer = document.getElementById('logs')
    const line = document.createElement('div')
    line.textContent = logLine
    logContainer.appendChild(line)
    
    // Auto-scroll
    logContainer.scrollTop = logContainer.scrollHeight
  }
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
  }
  
  ws.onclose = () => {
    console.log('Disconnected from log stream')
    
    // Auto-reconnect with exponential backoff
    setTimeout(() => streamLogs(runId), 5000)
  }
  
  return ws
}

// Usage
const ws = streamLogs("20250114_153045_a1b2c3")

// Close when done
// ws.close()
```

**Python** (simple with websocket-client):
```python
from websocket import create_connection

run_id = "20250114_153045_a1b2c3"
ws = create_connection(f"ws://127.0.0.1:23300/api/runs/{run_id}/logs/ws")

print(f"Streaming logs for {run_id}...\n")

try:
    while True:
        message = ws.recv()
        print(message)
except KeyboardInterrupt:
    print("\nStopped")
finally:
    ws.close()
```

---

## Metrics Data Format

### Events JSONL File

Metrics are stored in `events.jsonl` (JSON Lines format):

```jsonl
{"ts": 1704067200.0, "type": "metrics", "data": {"global_step": 1, "time": 0.0, "loss": 2.30, "accuracy": 0.12}}
{"ts": 1704067201.5, "type": "metrics", "data": {"global_step": 2, "time": 1.5, "loss": 1.85, "accuracy": 0.35}}
{"ts": 1704067203.2, "type": "image", "data": {"key": "prediction", "path": "media/123_abc_prediction.png", "step": 10}}
```

### Metric Types

**Type: metrics**:
```json
{
  "ts": 1704067200.0,
  "type": "metrics",
  "data": {
    "global_step": 100,
    "time": 45.2,
    "loss": 0.234,
    "accuracy": 0.95,
    "stage": "train"
  }
}
```

**Type: image**:
```json
{
  "ts": 1704067200.0,
  "type": "image",
  "data": {
    "key": "prediction_sample",
    "path": "media/1704067200000_abc123_prediction.png",
    "step": 100,
    "caption": "Model prediction on validation set"
  }
}
```

---

## Advanced Usage

### Metric Aggregation

**Group by stage**:
```python
import requests
from collections import defaultdict

run_id = "20250114_153045_a1b2c3"
response = requests.get(f'http://127.0.0.1:23300/api/runs/{run_id}/metrics_step')
data = response.json()

# Group metrics by stage
by_stage = defaultdict(list)

for row in data['rows']:
    stage = row.get('stage', 'default')
    by_stage[stage].append(row)

# Analyze each stage
for stage, rows in by_stage.items():
    losses = [r['loss'] for r in rows if 'loss' in r]
    
    print(f"\nStage: {stage}")
    print(f"  Steps: {len(rows)}")
    print(f"  Avg loss: {sum(losses)/len(losses):.4f}")
    print(f"  Final loss: {losses[-1]:.4f}")
```

### Metric Export

**Export to CSV**:
```python
import requests
import csv

run_id = "20250114_153045_a1b2c3"
response = requests.get(f'http://127.0.0.1:23300/api/runs/{run_id}/metrics_step')
data = response.json()

# Write to CSV
with open(f'{run_id}_metrics.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=data['columns'])
    writer.writeheader()
    writer.writerows(data['rows'])

print(f"Metrics exported to {run_id}_metrics.csv")
```

**Export to Excel** (using pandas):
```python
import requests
import pandas as pd

run_id = "20250114_153045_a1b2c3"
response = requests.get(f'http://127.0.0.1:23300/api/runs/{run_id}/metrics_step')
data = response.json()

# Convert to DataFrame
df = pd.DataFrame(data['rows'])

# Export to Excel with multiple sheets
with pd.ExcelWriter(f'{run_id}_metrics.xlsx') as writer:
    # All metrics
    df.to_excel(writer, sheet_name='All Metrics', index=False)
    
    # By stage
    if 'stage' in df.columns:
        for stage in df['stage'].unique():
            stage_df = df[df['stage'] == stage]
            stage_df.to_excel(writer, sheet_name=stage, index=False)

print(f"Metrics exported to {run_id}_metrics.xlsx")
```

---

## WebSocket Log Filtering

### Filter tqdm Progress Bars

tqdm progress bars can clutter logs when redirected to file. The frontend automatically filters them.

**tqdm output example**:
```
 45%|███████████▍            | 45/100 [00:12<00:15,  3.45it/s]
 46%|███████████▌            | 46/100 [00:12<00:14,  3.46it/s]
```

**Python client** (with filtering):
```python
import asyncio
import websockets
import re

def is_tqdm_line(text):
    """Detect tqdm progress bar"""
    if re.search(r'\d{1,3}%\|', text):
        return True
    if re.search(r'it\/(s|sec)', text, re.IGNORECASE):
        return True
    if re.search(r'ETA|elapsed', text, re.IGNORECASE):
        return True
    return False

async def stream_logs_filtered(run_id, filter_tqdm=True):
    uri = f"ws://127.0.0.1:23300/api/runs/{run_id}/logs/ws"
    
    async with websockets.connect(uri) as ws:
        while True:
            message = await ws.recv()
            
            if filter_tqdm and is_tqdm_line(message):
                continue  # Skip tqdm lines
            
            print(message)

# Usage
asyncio.run(stream_logs_filtered("20250114_153045_a1b2c3"))
```

---

## Data Models

### MetricsResponse

```typescript
interface MetricsResponse {
  columns: string[]                    // Metric names
  rows: Array<Record<string, number>>  // Data points
}
```

### MetricRow (Step-based)

```typescript
interface MetricRow {
  global_step: number      // Required: training step
  time?: number            // Optional: timestamp
  stage?: string           // Optional: training stage
  [key: string]: number    // Other metrics
}
```

---

## Performance Considerations

### Large Metrics Files

For experiments with 100,000+ data points:

```python
import requests

run_id = "long_training_run"

# This may be slow and return large response
response = requests.get(f'http://127.0.0.1:23300/api/runs/{run_id}/metrics_step')

# Better: Use V2 API with downsampling
response = requests.get(
    f'http://127.0.0.1:23300/api/v2/experiments/{run_id}/metrics/fast',
    params={'downsample': 1000}  # Reduce to 1000 points
)
```

### Caching

The API caches metrics for 60 seconds:

```python
import requests
import time

run_id = "20250114_153045_a1b2c3"

# First request: Reads from file
start = time.time()
response1 = requests.get(f'http://127.0.0.1:23300/api/runs/{run_id}/metrics_step')
time1 = time.time() - start
print(f"First request: {time1:.3f}s")

# Second request: Cached
start = time.time()
response2 = requests.get(f'http://127.0.0.1:23300/api/runs/{run_id}/metrics_step')
time2 = time.time() - start
print(f"Second request: {time2:.3f}s (cached)")

# Typical results:
# First request: 0.345s
# Second request: 0.012s (29x faster)
```

---

## Best Practices

### 1. Use Step-based Metrics for ML

```python
# ✅ Recommended: Step-based (consistent x-axis)
GET /runs/{run_id}/metrics_step

# X-axis: global_step (1, 2, 3, ...)
# Pros: Consistent, easy to compare across runs

# ⚠️ Alternative: Time-based (for wall-clock analysis)
GET /runs/{run_id}/metrics

# X-axis: time (0.0, 1.5, 3.2, ...)
# Pros: Shows real-time performance
```

### 2. Handle Missing Values

```python
import requests

response = requests.get('http://127.0.0.1:23300/api/runs/{run_id}/metrics_step')
data = response.json()

# Some metrics may not be logged at every step
for row in data['rows']:
    loss = row.get('loss', None)
    accuracy = row.get('accuracy', None)
    
    if loss is not None:
        print(f"Step {row['global_step']}: loss={loss:.4f}")
    
    # Or use default value
    lr = row.get('learning_rate', 0.001)
```

### 3. Monitor Training in Real-time

```python
import asyncio
import websockets
import re

async def monitor_training(run_id):
    """Monitor training and extract key metrics"""
    
    uri = f"ws://127.0.0.1:23300/api/runs/{run_id}/logs/ws"
    
    async with websockets.connect(uri) as ws:
        while True:
            line = await ws.recv()
            
            # Extract metrics from logs
            # Example: "Epoch 5/100, loss=0.234, acc=0.95"
            match = re.search(r'Epoch (\d+)/(\d+), loss=([\d.]+), acc=([\d.]+)', line)
            
            if match:
                epoch, total, loss, acc = match.groups()
                print(f"Epoch {epoch}/{total}: loss={loss}, acc={acc}")
                
                # Check for early stopping
                if float(acc) > 0.98:
                    print("🎉 Target accuracy reached!")
                    break

# Usage
asyncio.run(monitor_training("20250114_153045_a1b2c3"))
```

---

## Error Handling

**404 Not Found**:
```json
{
  "detail": "Run not found: 20250114_999999_zzz999"
}
```

**500 Internal Server Error** (corrupted metrics file):
```json
{
  "detail": "Failed to parse metrics file"
}
```

### Handling Errors

```python
import requests

def get_metrics_safe(run_id):
    """Get metrics with error handling"""
    try:
        response = requests.get(
            f'http://127.0.0.1:23300/api/runs/{run_id}/metrics_step',
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"Run {run_id} not found")
            return None
        else:
            print(f"Error {response.status_code}: {response.json()['detail']}")
            return None
            
    except requests.exceptions.Timeout:
        print("Request timeout - metrics file may be very large")
        
        # Retry with V2 API and downsampling
        print("Retrying with V2 API...")
        response = requests.get(
            f'http://127.0.0.1:23300/api/v2/experiments/{run_id}/metrics/fast',
            params={'downsample': 1000}
        )
        return response.json()
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

# Usage
metrics = get_metrics_safe("20250114_153045_a1b2c3")
```

---

## Integration Examples

### TensorBoard Integration

```python
import requests
from torch.utils.tensorboard import SummaryWriter

run_id = "20250114_153045_a1b2c3"

# Get metrics from Runicorn
response = requests.get(f'http://127.0.0.1:23300/api/runs/{run_id}/metrics_step')
data = response.json()

# Write to TensorBoard
writer = SummaryWriter(f'tensorboard_logs/{run_id}')

for row in data['rows']:
    step = row['global_step']
    
    for metric_name, value in row.items():
        if metric_name not in ['global_step', 'time', 'stage']:
            writer.add_scalar(metric_name, value, step)

writer.close()
print(f"Exported to TensorBoard: tensorboard --logdir tensorboard_logs")
```

### Weights & Biases Migration

```python
import requests
import wandb

run_id = "20250114_153045_a1b2c3"

# Initialize W&B
wandb.init(project="migrated_from_runicorn", name=run_id)

# Get Runicorn metrics
response = requests.get(f'http://127.0.0.1:23300/api/runs/{run_id}/metrics_step')
data = response.json()

# Log to W&B
for row in data['rows']:
    step = row['global_step']
    metrics = {k: v for k, v in row.items() if k not in ['global_step', 'time', 'stage']}
    
    wandb.log(metrics, step=step)

wandb.finish()
print("Migration to W&B completed")
```

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `GET /runs/{run_id}/metrics` | 60 requests | 60 seconds |
| `GET /runs/{run_id}/metrics_step` | 60 requests | 60 seconds |
| WebSocket connections | 10 concurrent | Per IP |

---

## Related APIs

- **Runs API**: Get run information - [runs_api.md](./runs_api.md)
- **V2 API**: High-performance metrics queries - [v2_api.md](./v2_api.md)

---

**Last Updated**: 2025-10-14

