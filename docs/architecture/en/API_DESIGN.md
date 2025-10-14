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
- Artifacts (`/artifacts`)
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

## V1 vs V2 API Design

### V1 API (File-Based)

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

### V2 API (SQLite-Based)

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
@router.get("/v2/experiments")
async def list_experiments_v2(
    project: str = None,
    status: str = None,
    page: int = 1,
    per_page: int = 50
):
    query = QueryParams(
        project=project,
        status=status.split(',') if status else None,
        limit=per_page,
        offset=(page - 1) * per_page
    )
    
    # Single SQL query with indexes
    experiments = await storage.list_experiments(query)
    total = await storage.count_experiments(query)
    
    return {
        "experiments": experiments,
        "total": total,
        "page": page,
        "has_next": (page * per_page) < total
    }
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

### Pagination

**Standard pattern**:
```python
@router.get("/v2/experiments")
async def list_experiments(
    page: int = 1,
    per_page: int = 50
):
    offset = (page - 1) * per_page
    
    experiments = await db.query(
        "SELECT * FROM experiments LIMIT ? OFFSET ?",
        (per_page, offset)
    )
    
    total = await db.count("experiments")
    
    return {
        "experiments": experiments,
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_next": offset + len(experiments) < total,
        "has_prev": page > 1
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

**Related**: [COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md) | [FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md)

**Back to**: [Architecture Index](README.md)

