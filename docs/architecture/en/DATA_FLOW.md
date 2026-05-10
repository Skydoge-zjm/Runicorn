[English](DATA_FLOW.md) | [简体中文](../zh/DATA_FLOW.md)

---

# Data Flow Architecture

**Document Type**: Architecture
**Purpose**: Document how data flows through the Runicorn system

---

## Experiment Lifecycle Flow

```mermaid
sequenceDiagram
    participant User
    participant SDK
    participant FileSystem
    participant SQLite
    participant WebUI

    User->>SDK: rn.init(path, alias)
    SDK->>FileSystem: Create run directory
    SDK->>FileSystem: Write meta.json, status.json
    SDK->>SQLite: INSERT INTO experiments

    loop Training
        User->>SDK: run.log({loss: 0.1})
        SDK->>FileSystem: Append to events.jsonl
        SDK->>SQLite: INSERT INTO metrics
    end

    User->>SDK: run.finish()
    SDK->>FileSystem: Update summary.json
    SDK->>SQLite: UPDATE experiments SET status='finished'

    User->>WebUI: View experiment
    WebUI->>SQLite: SELECT * FROM experiments
    SQLite-->>WebUI: Fast metadata
    WebUI->>FileSystem: Read events.jsonl
    FileSystem-->>WebUI: Chart data
```

---

## Metrics Logging Pipeline

### Step-by-Step Flow

**1. User logs metrics**:
```python
run.log({"loss": 0.5, "accuracy": 0.9}, step=100)
```

**2. SDK processes**:
```python
# Add metadata
payload = {
    "loss": 0.5,
    "accuracy": 0.9,
    "global_step": 100,
    "time": current_timestamp
}

# Write to file (V1 compatibility)
events_file.append(json.dumps(payload))

# Write to SQLite (V2 performance)
for metric_name, value in payload.items():
    metrics_table.insert(exp_id, metric_name, value, step)
```

**3. Web UI retrieves**:
```python
# V1: Parse JSONL file
metrics = parse_jsonl(events_file)

# V2: Query SQLite (100x faster)
metrics = SELECT * FROM metrics WHERE experiment_id = ? ORDER BY step
```

---

## Run Asset Recording Flow

### Sequence

```
1. User calls `run.log_config()`, `run.log_dataset()`, `run.log_pretrained()`
   or `snapshot_workspace()`
   ↓
2. SDK normalizes metadata and decides whether to archive content
   ↓
3. For saved files/directories:
   - Compute fingerprint / SHA256
   - Reuse existing blob or manifest when possible
   - Copy or link into `archive/`
   ↓
4. Update `assets.json` in the run directory
   ↓
5. Sync SQLite `assets` + `run_assets` records when modern storage is enabled
   ↓
6. Viewer surfaces the result via `/api/runs/{run_id}/assets`
```

### Deduplication Decision Tree

```
File or directory to archive
    ↓
Compute fingerprint / SHA256
    ↓
Check: matching blob / manifest already archived?
    ├─ Yes → Reuse existing archive entry
    │         (No duplicate write)
    └─ No  → Store under `archive/blobs` or `archive/manifests`
              ↓
              Record `archive_path` in `assets.json`
              ↓
              Link run ↔ asset in SQLite when available
```

---

## Remote Synchronization Flow

### Smart Mode (Metadata Only)

```
┌─────────────┐         SSH/SFTP        ┌──────────────┐
│ Local       │ ◄──────────────────────►│ Remote       │
│ Machine     │                          │ Server       │
└─────────────┘                          └──────────────┘

Step 1: Connect via SSH
Local ──[SSH Auth]──► Remote
      ◄──[Connected]──

Step 2: List remote structure
Local ──[SFTP ls]──────► Remote
      ◄──[Dir listing]──

Step 3: Sync metadata (JSON files only)
Local ──[SFTP get *.json]──► Remote
      ◄──[200MB metadata]───

Step 4: Cache locally
Local: Save to ~/.runicorn_remote_cache/
       ├── metadata/
       └── index.db

Step 5: User queries (from cache, instant)
User → WebUI → Cache → Display (no network)

Step 6: Download files on-demand
User clicks "Download"
   ↓
Local ──[SFTP get model.pth]──► Remote
      ◄──[8GB file transfer]───
   ↓
Saved to cache/downloads/
```

---

## WebSocket Log Streaming

### Real-time Flow

```
Training Process          Backend              Frontend
      │                      │                     │
      │ Write to logs.txt    │                     │
      ├──────────────────────►                     │
      │                      │                     │
      │                      │ tail -f logs.txt    │
      │                      ├─────────────────────► WebSocket
      │                      │                     │ connection
      │                      │ New line event      │
      │                      ├─────────────────────►
      │                      │                     │ Display
      │                      │                     │ in UI
```

### Implementation

**Backend** (FastAPI WebSocket):
```python
@app.websocket("/runs/{run_id}/logs/ws")
async def logs_websocket(websocket, run_id):
    await websocket.accept()

    log_file = get_log_path(run_id)

    with open(log_file) as f:
        # Send existing logs
        for line in f:
            await websocket.send_text(line)

        # Tail new lines
        while True:
            line = f.readline()
            if line:
                await websocket.send_text(line)
            else:
                await asyncio.sleep(0.1)
```

**Frontend** (React):
```javascript
const ws = new WebSocket('ws://localhost:23300/api/runs/{id}/logs/ws')

ws.onmessage = (event) => {
    setLogs(prev => [...prev, event.data])
}
```

---

## Asset Inspection & Download Flow

### Loading and Using

```
1. User opens Run Detail or Assets page
   ↓
2. Frontend requests `/api/runs/{run_id}/assets`
   ↓
3. Backend reads `assets.json` (and asset index when needed)
   ↓
4. UI groups code / config / dataset / pretrained / output entries
   ↓
5. User previews or downloads a selected entry
   ↓
6. Frontend calls `/api/runs/{run_id}/assets/download?path=...`
   ↓
7. Backend validates the absolute path against the run directory / linked archives
   ↓
8. File or ZIP response is streamed back to the browser
```

### Shared-Asset Reference Checks

```
Recycle Bin preview:
GET /api/runs/{run_id}/assets/refs
    ↓
Response:
{
  "orphaned_assets": [
    {"asset_id": "...", "asset_type": "dataset", "ref_count": 1}
  ],
  "shared_assets": [
    {"asset_id": "...", "asset_type": "pretrained", "ref_count": 3}
  ]
}
    ↓
Recycle bin UI shows what permanent delete would remove vs keep
```

---

## Query Optimization Flow

### V1 API (File Scanning)

```
GET /api/runs
    ↓
Scan directories
    ├─ project1/
    │  └─ name1/runs/* (100 runs)
    ├─ project2/
    │  └─ name2/runs/* (500 runs)
    ↓
Read JSON files (3-4 per run)
    ↓
Parse and aggregate
    ↓
Return after 5-10 seconds
```

### Current SQLite-Backed Listing Flow

```
GET /api/paths/runs?path=X&exact=false
    ↓
Read active runs from SQLite-backed experiments table
    ↓
SELECT * FROM experiments
WHERE deleted_at IS NULL
ORDER BY created_at DESC
    ↓
Filter rows by path prefix
    ↓
Return in 50-100ms for typical datasets
```

---

## Caching Strategy

### Metrics Caching

```
First Request:
User → API → Parse events.jsonl → Cache result → Return
                      (300ms)

Subsequent Requests (within 60s):
User → API → Check cache → Return cached
                  (5ms, 60x faster)

Cache Invalidation:
- TTL: 60 seconds
- Or: When new metrics logged
```

### Connection Pooling

```
Request 1 → Get connection from pool → Execute → Return to pool
Request 2 → Reuse connection → Execute → Return to pool
...
Request 10 → All reuse 10 pooled connections

Benefits:
- No connection setup overhead
- Thread-safe access
- Automatic cleanup
```

---

## Error Propagation

### From Storage to User

```
Storage Layer Error
    ↓
Business Logic catches
    ↓
Maps to HTTP status
    ↓
API returns JSON error
    ↓
Frontend displays user-friendly message
```

**Example**:
```python
# Storage
raise FileNotFoundError("Run directory not found")

# Business Logic
except FileNotFoundError:
    raise HTTPException(404, "Run not found")

# API Response
{"detail": "Run not found"}

# Frontend
message.error("实验未找到")
```

---

## Remote Viewer Data Flow

### Connection Establishment Flow

```
User (Browser)
    ↓
Click "Connect to Remote Server"
    ↓
Local Viewer API
    ↓
Connection Manager: Establish SSH connection
    ├─ Password / SSH key authentication
    ├─ Keep-alive setup
    └─ Add to connection pool
    ↓
Environment Detector: Scan remote environments
    ├─ Execute: conda env list
    ├─ Execute: which python
    ├─ For each env: import runicorn
    └─ Return compatible environment list
    ↓
Return connection status and environment list to frontend
```

### Remote Viewer Startup Flow

```
User selects environment
    ↓
POST /api/remote/viewer/start
    ↓
Viewer Launcher: Build startup command
    ↓
Execute via SSH:
    source /path/to/env/bin/activate && \
    runicorn viewer --host 127.0.0.1 --port 23300 --no-open-browser &
    ↓
Get process PID
    ↓
Tunnel Manager: Create SSH tunnel
    ├─ Remote: 127.0.0.1:23300
    └─ Local: 127.0.0.1:8081
    ↓
Health Checker: Verify Viewer startup
    ├─ Test connection: socket.connect(('127.0.0.1', 8081))
    └─ HTTP check: GET http://localhost:8081/api/health
    ↓
Return Viewer URL: http://localhost:8081
    ↓
Frontend auto-opens new tab
```

### Data Access Flow

```
Browser request
    ↓
http://localhost:8081/api/runs
    ↓
Local SSH tunnel
    ↓
Forward to remote: 127.0.0.1:23300
    ↓
Remote Viewer instance (FastAPI)
    ↓
Read remote data storage
    ├─ runicorn.db (SQLite)
    └─ ~/RunicornData/project/name/runs/
    ↓
Return JSON response
    ↓
Return through SSH tunnel
    ↓
Browser receives and renders
```

### Real-time Log Streaming (Remote)

```
Browser establishes WebSocket
    ↓
ws://localhost:8081/api/runs/{id}/logs/ws
    ↓
Local SSH tunnel (WebSocket upgrade)
    ↓
Forward to remote Viewer
    ↓
Remote Viewer reads log file
    ├─ tail -f /path/to/logs.txt
    └─ Continuous streaming
    ↓
Stream back through SSH tunnel
    ↓
Browser displays logs in real-time
```

### Health Check Flow

```
Timer (every 30 seconds)
    ↓
Health Checker performs checks
    ├─ 1. Connection check
    │   └─ SSH: echo "ping"
    ├─ 2. Viewer check
    │   └─ HTTP: GET http://localhost:8081/api/health
    └─ 3. Tunnel check
        └─ socket.connect(('127.0.0.1', 8081))
    ↓
If any check fails:
    ├─ Attempt auto-recovery
    │   ├─ SSH disconnected: Reconnect (max 3 attempts)
    │   ├─ Viewer crashed: Notify user
    │   └─ Tunnel broken: Rebuild tunnel
    └─ Update health status
    ↓
Frontend displays connection status indicator
```

### Disconnect Cleanup Flow

```
User clicks disconnect / closes tab
    ↓
POST /api/remote/viewer/stop
{"session_id": "{session_id}"}
    ↓
If no sessions remain on that SSH connection:
POST /api/remote/disconnect
{"host": "...", "port": 22, "username": "..."}
    ↓
Cleanup steps:
    ├─ 1. Tunnel Manager: Close SSH tunnel
    │   └─ Stop forwarding thread
    ├─ 2. Viewer Launcher: Stop remote Viewer
    │   ├─ Via SSH: kill {pid}
    │   └─ Delete log file
    └─ 3. Connection Manager: Close SSH connection
        └─ Remove from connection pool
    ↓
Return cleanup status
    ↓
Frontend updates UI, removes connection
```

---

**Related**: [COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md) | [STORAGE_DESIGN.md](STORAGE_DESIGN.md) | [REMOTE_VIEWER_ARCHITECTURE.md](REMOTE_VIEWER_ARCHITECTURE.md)

**Back to**: [Architecture Index](README.md)

