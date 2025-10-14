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

**相关文档**: [COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md) | [FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md)

**返回**: [架构索引](README.md)
