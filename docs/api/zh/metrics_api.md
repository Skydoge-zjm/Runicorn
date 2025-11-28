[English](../en/metrics_api.md) | [简体中文](metrics_api.md)

---

# Metrics API - 训练指标查询

**模块**: Metrics API  
**基础路径**: `/api/runs/{run_id}`  
**版本**: v1.1  
**描述**: 查询训练指标、进度和通过 HTTP 和 WebSocket 获取实时日志。

---

## 端点概览

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/runs/{run_id}/metrics` | 获取按时间戳聚合的指标（支持降采样） |
| GET | `/runs/{run_id}/metrics_step` | 获取按步骤聚合的指标（支持降采样） |
| GET | `/metrics/cache/stats` | 获取缓存统计信息 |
| WS | `/runs/{run_id}/logs/ws` | 通过 WebSocket 实时日志流 |

---

## 获取指标（基于时间）

检索按时间戳聚合的指标。

### 请求

```http
GET /api/runs/{run_id}/metrics?downsample=2000
```

**查询参数**:
| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `downsample` | integer | 否 | 目标数据点数量（100-50000）。使用 LTTB 算法进行智能降采样。 |

### 响应

**状态码**: `200 OK`

**响应头**:
| 头部 | 描述 |
|------|------|
| `X-Row-Count` | 响应中的行数 |
| `X-Total-Count` | 降采样前的总行数 |
| `X-Last-Step` | 数据中最后一个步骤号 |

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
  ],
  "total": 100000,
  "sampled": 2000
}
```

---

## 获取步骤指标

检索按训练步骤聚合的指标（推荐用于 ML）。

### 请求

```http
GET /api/runs/{run_id}/metrics_step?downsample=2000
```

**查询参数**:
| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `downsample` | integer | 否 | 目标数据点数量（100-50000）。使用 LTTB 算法进行智能降采样。 |

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
  ],
  "total": 100000,
  "sampled": 2000
}
```

---

## 缓存统计

获取增量缓存的性能统计信息。

### 请求

```http
GET /api/metrics/cache/stats
```

### 响应

```json
{
  "size": 15,
  "max_size": 100,
  "hits": 1250,
  "misses": 45,
  "incremental_updates": 320,
  "hit_rate": 0.77,
  "incremental_rate": 0.20
}
```

**字段说明**:
| 字段 | 描述 |
|------|------|
| `size` | 当前缓存条目数 |
| `max_size` | 最大缓存容量 |
| `hits` | 缓存命中次数 |
| `misses` | 缓存未命中次数 |
| `incremental_updates` | 增量更新次数 |
| `hit_rate` | 缓存命中率 |
| `incremental_rate` | 增量更新率 |

---

## 性能优化

### LTTB 降采样

对于大型数据集（10万+数据点），使用 `downsample` 参数：

```python
import requests

run_id = "long_training_run"

# 使用降采样减少响应大小
response = requests.get(
    f'http://127.0.0.1:23300/api/runs/{run_id}/metrics_step',
    params={'downsample': 2000}
)

data = response.json()
print(f"总数据点: {data['total']}, 采样后: {data['sampled']}")
```

**LTTB (Largest Triangle Three Buckets) 算法特点**：
- 保留数据的峰值和谷值
- 保持图表的视觉保真度
- O(n) 时间复杂度
- 适用于任何数值型指标

### 增量缓存

API 使用增量缓存系统优化持续增长的文件：

| 场景 | 性能 |
|------|------|
| 文件未变化 | O(1) 立即返回缓存 |
| 文件增长（新数据追加） | O(n) 仅读取新数据并合并 |
| 文件截断/重置 | O(N) 完整重新解析 |

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

**最后更新**: 2025-11-28

