[English](../en/API_DESIGN.md) | [简体中文](API_DESIGN.md)

---

# API 层架构

**文档类型**: 架构  
**目的**: Runicorn API 层的设计原则和模式

---

## API 设计原则

### 1. RESTful 资源建模

**资源**:
- 实验（`/runs`）
- Artifacts（`/artifacts`）
- 指标（`/runs/{id}/metrics`）
- 配置（`/config`）

**标准 HTTP 方法**:
- `GET`: 检索
- `POST`: 创建或操作
- `DELETE`: 删除
- `PUT/PATCH`: 更新（最少使用）

---

### 2. 分层架构

```
路由（API 端点）
    ↓ 委托给
服务（业务逻辑）
    ↓ 使用
存储（数据访问）
```

**优势**:
- 可测试: 为路由测试模拟服务
- 可复用: 服务被多个路由使用
- 清晰: 关注点分离

---

### 3. 全面 Async/Await

**原因**: FastAPI 是 ASGI，从异步 I/O 中受益

```python
# 所有路由都是异步的
@router.get("/runs")
async def list_runs(request: Request):
    # 异步文件操作
    async with aiofiles.open(path) as f:
        content = await f.read()
    
    # 异步数据库查询
    experiments = await storage.list_experiments()
    
    return experiments
```

---

## V1 vs V2 API 设计

### V1 API（基于文件）

**设计**:
- 直接文件系统访问
- 简单，直接
- 不需要数据库

**特征**:
- ✅ 向后兼容
- ✅ 人类可读（可以检查文件）
- ⚠️ 大数据集慢（O(n) 扫描）

---

### V2 API（基于 SQLite）

**设计**:
- 带索引的数据库查询
- 高级过滤、分页、搜索
- 针对性能优化

**特征**:
- ✅ 快 100 倍
- ✅ 服务端过滤/排序
- ✅ 分页支持
- ⚠️ 需要现代存储

---

## 错误处理策略

### HTTP 状态码映射

```python
# 存储层
raise FileNotFoundError("Run not found")

# API 层
try:
    result = service.get_run(run_id)
except FileNotFoundError:
    raise HTTPException(status_code=404, detail="Run not found")
except PermissionError:
    raise HTTPException(status_code=403, detail="Permission denied")
except Exception as e:
    logger.error(f"意外错误: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

---

## 速率限制架构

### 中间件模式

```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 检查速率限制
        if not limiter.is_allowed(endpoint, client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)}
            )
        
        # 处理请求
        response = await call_next(request)
        
        # 添加速率限制头部
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
```

---

## WebSocket 设计

### 连接管理

```python
@app.websocket("/runs/{run_id}/logs/ws")
async def logs_websocket(websocket: WebSocket, run_id: str):
    await websocket.accept()
    
    try:
        # 流式日志
        async for line in tail_file(log_path):
            await websocket.send_text(line)
    
    except WebSocketDisconnect:
        logger.info(f"客户端断开连接: {run_id}")
    
    finally:
        # 清理资源
        await cleanup()
```

---

## Remote API 设计（v0.5.0）

### 资源层次

```
/api/remote/
├── connections           # 连接管理
│   ├── POST /connect     # 建立连接
│   ├── GET /connections  # 列出所有连接
│   └── DELETE /{id}      # 断开连接
│
├── environments          # 环境检测
│   ├── GET /             # 列出环境
│   ├── POST /detect      # 重新检测
│   └── GET /config       # 获取配置
│
└── viewer/               # Viewer 管理
    ├── POST /start       # 启动 Viewer
    ├── POST /stop        # 停止 Viewer
    ├── GET /status       # 获取状态
    └── GET /logs         # 获取日志
```

### RESTful 设计模式

**1. 连接作为资源**:
```python
# 创建连接
POST /api/remote/connect
→ 返回: {"connection_id": "conn_123", ...}

# 查询连接
GET /api/remote/connections/{connection_id}

# 删除连接（断开）
DELETE /api/remote/connections/{connection_id}
```

**2. 子资源嵌套**:
```python
# Viewer 是连接的子资源
POST /api/remote/viewer/start
{
  "connection_id": "conn_123",  # 关联到父资源
  "env_name": "pytorch-env"
}
```

### 异步操作设计

**长时间操作**（如启动 Viewer）:
```python
@router.post("/viewer/start")
async def start_viewer(request: StartViewerRequest):
    # 1. 立即返回接受状态
    task_id = uuid.uuid4().hex
    
    # 2. 后台异步执行
    background_tasks.add_task(
        _start_viewer_task,
        connection_id=request.connection_id,
        env_name=request.env_name,
        task_id=task_id
    )
    
    # 3. 返回任务 ID 供轮询
    return {
        "status": "starting",
        "task_id": task_id,
        "estimated_time_ms": 5000
    }

# 客户端轮询状态
GET /api/remote/viewer/status?connection_id={id}
→ {"status": "running", "viewer_url": "http://localhost:8081"}
```

### 错误处理（Remote 特定）

```python
# Remote 特定错误码
class RemoteErrorCode(str, Enum):
    SSH_AUTH_FAILED = "ssh_auth_failed"
    CONNECTION_TIMEOUT = "connection_timeout"
    ENVIRONMENT_NOT_FOUND = "environment_not_found"
    VIEWER_START_FAILED = "viewer_start_failed"
    TUNNEL_FAILED = "tunnel_failed"

# 标准错误响应
{
  "error": "ssh_auth_failed",
  "message": "SSH authentication failed",
  "details": "Permission denied (publickey)",
  "retry_after": null,  # 如果可重试，秒数
  "suggestions": [
    "Check SSH key path",
    "Verify username and host"
  ]
}
```

### 健康检查设计

**分层健康检查**:
```python
GET /api/remote/health?connection_id={id}

返回:
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

### 安全设计考虑

**1. SSH 凭据处理**:
```python
# 永不存储明文密码
@router.post("/connect")
async def connect(request: ConnectRequest):
    # 密码仅在内存中，立即使用后丢弃
    ssh_client = paramiko.SSHClient()
    ssh_client.connect(
        hostname=request.host,
        username=request.username,
        password=request.password  # 用后即焚
    )
    
    # 存储连接对象，不存储凭据
    connection_manager.add(connection_id, ssh_client)
```

**2. 端口隔离**:
```python
# 远程 Viewer 只监听 127.0.0.1，不对外暴露
viewer_cmd = (
    f"runicorn viewer "
    f"--host 127.0.0.1 "  # 仅本地
    f"--port {remote_port} "
    f"--no-open-browser"
)
```

---

**相关文档**: [COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md) | [FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md) | [REMOTE_VIEWER_ARCHITECTURE.md](REMOTE_VIEWER_ARCHITECTURE.md)

**返回**: [架构索引](README.md)
