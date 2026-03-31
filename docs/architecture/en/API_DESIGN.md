[English](API_DESIGN.md) | [简体中文](../zh/API_DESIGN.md)

---

# API Layer Architecture

**Document Type**: Architecture
**Purpose**: Design principles and patterns for the Runicorn API layer

---

## API Design Principles

### 1. RESTful Resource Modeling

**Resources**:
- Experiments (`/runs`)
- Run assets (`/runs/{id}/assets`)
- Metrics (`/runs/{id}/metrics`)
- Configuration (`/config`)

**Standard HTTP methods**:
- `GET`: Retrieve
- `POST`: Create or action
- `DELETE`: Remove
- `PUT/PATCH`: Update (minimal use)

---

### 2. Layered Architecture

```
Routes (API endpoints)
    ↓ delegates to
Services (business logic)
    ↓ uses
Storage (data access)
```

**Benefits**:
- Testable: Mock services for route tests
- Reusable: Services used by multiple routes
- Clean: Separation of concerns

---

### 3. Async/Await Throughout

**Why**: FastAPI is ASGI, benefits from async I/O

```python
# All routes are async
@router.get("/runs")
async def list_runs(request: Request):
    # Async file operations
    async with aiofiles.open(path) as f:
        content = await f.read()

    # Async database queries
    experiments = await storage.list_experiments()

    return experiments
```

---

## File-Scan Fallback vs SQLite-Backed Fast Path

Earlier drafts called this split "V1" vs "V2". In the current codebase these are
implementation modes behind the same public routes (`/runs`, `/paths/runs`,
`/runs/{run_id}`), not separate route namespaces.

### File-Scan Fallback

**Design**:
- Direct file system access
- Simple, straightforward
- No database required

**Characteristics**:
- ✅ Backward compatible
- ✅ Human-readable (can inspect files)
- ⚠️ Slow for large datasets (O(n) scans)

**Example**:
```python
@router.get("/runs")
async def list_runs_v1(request: Request):
    runs = []
    # Scan directories
    for entry in iter_all_runs(storage_root):
        # Read JSON files
        meta = read_json(entry.dir / "meta.json")
        status = read_json(entry.dir / "status.json")
        runs.append(RunListItem(...))
    return runs
```

---

### SQLite-Backed Fast Path

**Design**:
- Database queries with indexes
- Advanced filtering, pagination, search
- Optimized for performance

**Characteristics**:
- ✅ 100x faster
- ✅ Server-side filtering/sorting
- ✅ Pagination support
- ⚠️ Requires modern storage

**Example**:
```python
@router.get("/runs")
async def list_runs(request: Request):
    backend = get_backend(request)

    if backend is not None:
        db_rows = list_runs_from_db(backend)
        if db_rows is not None:
            return [RunListItem(**row) for row in db_rows]

    # Fall back to file scanning only when SQLite is unavailable.
    items = []
    for entry in iter_all_runs(request.app.state.storage_root):
        ...
    return items
```

---

## Error Handling Strategy

### HTTP Status Code Mapping

```python
# Storage layer
raise FileNotFoundError("Run not found")

# API layer
try:
    result = service.get_run(run_id)
except FileNotFoundError:
    raise HTTPException(status_code=404, detail="Run not found")
except PermissionError:
    raise HTTPException(status_code=403, detail="Permission denied")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

### Consistent Error Format

```json
{
  "detail": "Human-readable error message"
}
```

**Optional** (for complex errors):
```json
{
  "detail": "Error message",
  "error_code": "INVALID_RUN_ID",
  "context": {
    "run_id": "abc123",
    "expected_format": "YYYYMMDD_HHMMSS_XXXXXX"
  }
}
```

---

## Rate Limiting Architecture

### Middleware Pattern

```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Check rate limit
        if not limiter.is_allowed(endpoint, client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)}
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
```

### Sliding Window Algorithm

```python
class SlidingWindowLimiter:
    def __init__(max_requests, window_seconds):
        self.requests = {}  # {client_ip: [timestamps]}

    def is_allowed(client_ip):
        now = time.time()

        # Remove old timestamps
        self.requests[client_ip] = [
            ts for ts in self.requests.get(client_ip, [])
            if now - ts < window_seconds
        ]

        # Check limit
        if len(self.requests[client_ip]) >= max_requests:
            return False

        # Record request
        self.requests[client_ip].append(now)
        return True
```

---

## Input Validation

### Three-Layer Protection

**Layer 1: Format validation**
```python
def validate_run_id(run_id: str) -> bool:
    pattern = r'^[0-9]{8}_[0-9]{6}_[a-f0-9]{6}$'
    return bool(re.match(pattern, run_id))
```

**Layer 2: Semantic validation**
```python
def validate_batch_size(size: int, max_size: int = 100) -> bool:
    return isinstance(size, int) and 0 < size <= max_size
```

**Layer 3: Path traversal prevention**
```python
def validate_path(path: str, base_dir: Path) -> bool:
    if '..' in path:
        return False

    full_path = (base_dir / path).resolve()
    base_resolved = base_dir.resolve()

    # Ensure path is within base_dir
    return str(full_path).startswith(str(base_resolved))
```

---

## Response Optimization

### Windowed Query Pattern

**Standard pattern**:
```python
def query_runs_window(backend, limit: int = 50, offset: int = 0):
    query = QueryParams(limit=limit, offset=offset)
    runs = backend.list_experiments(query)
    total = backend.count_experiments(QueryParams())

    return {
        "runs": runs,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_next": offset + len(runs) < total,
        "has_prev": offset > 0
    }
```

### Field Selection (Future)

```python
# Allow clients to request specific fields
GET /api/runs?fields=id,status,project

# Returns only requested fields, smaller response
```

---

## WebSocket Design

### Connection Management

```python
@app.websocket("/runs/{run_id}/logs/ws")
async def logs_websocket(websocket: WebSocket, run_id: str):
    await websocket.accept()

    try:
        # Stream logs
        async for line in tail_file(log_path):
            await websocket.send_text(line)

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {run_id}")

    finally:
        # Cleanup resources
        await cleanup()
```

### Auto-Reconnect (Client-Side)

```javascript
function connectWebSocket(url, onReconnect) {
    let ws = new WebSocket(url)
    let reconnectDelay = 1000  // Start with 1s

    ws.onclose = () => {
        console.log(`Reconnecting in ${reconnectDelay}ms...`)
        setTimeout(() => {
            reconnectDelay = Math.min(reconnectDelay * 1.5, 10000)  // Max 10s
            connectWebSocket(url, onReconnect)
        }, reconnectDelay)
    }

    ws.onopen = () => {
        reconnectDelay = 1000  // Reset on successful connect
        if (onReconnect) onReconnect()
    }

    return ws
}
```

---

## Remote API Design

### Resource Hierarchy

```
/api/remote/
├── connections           # Connection management
│   ├── POST /connect     # Establish connection
│   ├── GET /connections  # List all connections
│   └── DELETE /{id}      # Disconnect
│
├── environments          # Environment detection
│   ├── GET /             # List environments
│   ├── POST /detect      # Re-detect
│   └── GET /config       # Get config
│
└── viewer/               # Viewer management
    ├── POST /start       # Start Viewer
    ├── POST /stop        # Stop Viewer
    ├── GET /status       # Get status
    └── GET /logs         # Get logs
```

### RESTful Design Patterns

**1. Connection as Resource**:
```python
# Create connection
POST /api/remote/connect
→ Returns: {"connection_id": "conn_123", ...}

# Query connection
GET /api/remote/connections/{connection_id}

# Delete connection (disconnect)
DELETE /api/remote/connections/{connection_id}
```

**2. Sub-resource Nesting**:
```python
# Viewer is sub-resource of connection
POST /api/remote/viewer/start
{
  "connection_id": "conn_123",  # Links to parent resource
  "env_name": "pytorch-env"
}
```

### Async Operation Design

**Long-running operations** (like starting Viewer):
```python
@router.post("/viewer/start")
async def start_viewer(request: StartViewerRequest):
    # 1. Immediately return accepted status
    task_id = uuid.uuid4().hex

    # 2. Execute asynchronously in background
    background_tasks.add_task(
        _start_viewer_task,
        connection_id=request.connection_id,
        env_name=request.env_name,
        task_id=task_id
    )

    # 3. Return task ID for polling
    return {
        "status": "starting",
        "task_id": task_id,
        "estimated_time_ms": 5000
    }

# Client polls status
GET /api/remote/viewer/status?connection_id={id}
→ {"status": "running", "viewer_url": "http://localhost:8081"}
```

### Error Handling (Remote-specific)

```python
# Remote-specific error codes
class RemoteErrorCode(str, Enum):
    SSH_AUTH_FAILED = "ssh_auth_failed"
    CONNECTION_TIMEOUT = "connection_timeout"
    ENVIRONMENT_NOT_FOUND = "environment_not_found"
    VIEWER_START_FAILED = "viewer_start_failed"
    TUNNEL_FAILED = "tunnel_failed"

# Standard error response
{
  "error": "ssh_auth_failed",
  "message": "SSH authentication failed",
  "details": "Permission denied (publickey)",
  "retry_after": null,  # Seconds if retryable
  "suggestions": [
    "Check SSH key path",
    "Verify username and host"
  ]
}
```

### Health Check Design

**Layered health checks**:
```python
GET /api/remote/health?connection_id={id}

Returns:
{
  "is_healthy": true,
  "checks": {
    "ssh_connection": {
      "status": "healthy",
      "latency_ms": 45.3,
      "last_check": "2025-10-25T10:30:00Z"
    },
    "viewer_process": {
      "status": "healthy",
      "pid": 12345,
      "uptime_seconds": 3600
    },
    "ssh_tunnel": {
      "status": "healthy",
      "local_port": 8081,
      "remote_port": 23300,
      "bytes_transferred": 1048576
    }
  }
}
```

### Security Design Considerations

**1. SSH Credential Handling**:
```python
# Never store plaintext passwords
@router.post("/connect")
async def connect(request: ConnectRequest):
    # Password only in memory, discard immediately after use
    ssh_client = paramiko.SSHClient()
    ssh_client.connect(
        hostname=request.host,
        username=request.username,
        password=request.password  # Burn after reading
    )

    # Store connection object, not credentials
    connection_manager.add(connection_id, ssh_client)
```

**2. Port Isolation**:
```python
# Remote Viewer only listens on 127.0.0.1, not exposed
viewer_cmd = (
    f"runicorn viewer "
    f"--host 127.0.0.1 "  # Localhost only
    f"--port {remote_port} "
    f"--no-open-browser"
)
```

---

**Related**: [COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md) | [FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md) | [REMOTE_VIEWER_ARCHITECTURE.md](REMOTE_VIEWER_ARCHITECTURE.md)

**Back to**: [Architecture Index](README.md)

