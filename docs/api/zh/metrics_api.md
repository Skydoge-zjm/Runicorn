[English](../en/metrics_api.md) | [简体中文](metrics_api.md)

---

# Metrics API - 训练指标查询

**模块**: Metrics API  
**基础路径**: `/api/runs/{run_id}`  
**版本**: v1.0  
**描述**: 查询训练指标、进度和通过 HTTP 和 WebSocket 获取实时日志。

---

## 端点概览

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/runs/{run_id}/metrics` | 获取按时间戳聚合的指标 |
| GET | `/runs/{run_id}/metrics_step` | 获取按步骤聚合的指标 |
| WS | `/runs/{run_id}/logs/ws` | 通过 WebSocket 实时日志流 |

---

## 获取指标（基于时间）

检索按时间戳聚合的指标。

### 请求

```http
GET /api/runs/{run_id}/metrics
```

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "columns": ["time", "loss", "accuracy", "learning_rate"],
  "rows": [
    {
      "time": 0.0,
      "loss": 2.3025,
      "accuracy": 0.1234,
      "learning_rate": 0.001
    }
  ]
}
```

---

## 获取步骤指标

检索按训练步骤聚合的指标（推荐用于 ML）。

### 请求

```http
GET /api/runs/{run_id}/metrics_step
```

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "columns": ["global_step", "loss", "accuracy", "stage"],
  "rows": [
    {
      "global_step": 1,
      "loss": 2.3025,
      "accuracy": 0.1234,
      "stage": "warmup"
    }
  ]
}
```

---

## 实时日志流

通过 WebSocket 流式传输训练日志。

### 连接

```
ws://127.0.0.1:23300/api/runs/{run_id}/logs/ws
```

### 示例

**Python**:
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

**JavaScript**:
```javascript
const ws = new WebSocket('ws://127.0.0.1:23300/api/runs/{run_id}/logs/ws')

ws.onmessage = (event) => {
  console.log(event.data)
}
```

---

## 相关 API

- **Runs API**: 获取运行信息 - [runs_api.md](runs_api.md)
- **V2 API**: 高性能指标查询 - [v2_api.md](v2_api.md)

---

**最后更新**: 2025-10-14

