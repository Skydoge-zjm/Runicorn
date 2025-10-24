[English](../en/QUICK_REFERENCE.md) | [简体中文](QUICK_REFERENCE.md)

---

# Runicorn API 快速参考

**版本**: v0.4.1  
**基础 URL**: `http://127.0.0.1:23300/api`

---

## 🐍 Python API Client (推荐)

**最简单的方式**：使用 Python 客户端

```python
import runicorn.api as api

# 连接
with api.connect() as client:
    # 列出实验
    experiments = client.list_experiments(project="vision")
    
    # 获取指标
    metrics = client.get_metrics(experiments[0]["id"])
    
    # Artifacts
    artifacts = client.artifacts.list_artifacts(type="model")
```

**文档**: [python_client_api.md](./python_client_api.md)

---

## 🌐 REST API 快速开始 (30秒)

```bash
# 1. 启动 Runicorn
runicorn viewer

# 2. 测试 API
curl http://127.0.0.1:23300/api/health

# 3. 列出实验
curl http://127.0.0.1:23300/api/runs
```

---

## 最常用端点

### 实验管理

```bash
# 列出所有运行
GET /api/runs

# 获取运行详情
GET /api/runs/{run_id}

# 获取指标（基于步骤）
GET /api/runs/{run_id}/metrics_step

# 删除运行（软删除）
POST /api/runs/soft-delete
Body: {"run_ids": ["run1", "run2"]}
```

### Manifest-Based Sync 🚀

```bash
# 生成 manifest（服务器端）
runicorn generate-manifest --verbose

# 生成活跃 manifest（最近 1 小时）
runicorn generate-manifest --active

# 指定实验目录
runicorn generate-manifest --root /data/experiments

# 查看 manifest 统计
jq '.statistics' .runicorn/full_manifest.json

# Python SDK - 服务端
from runicorn.manifest import ManifestGenerator, ManifestType
generator = ManifestGenerator(Path("/data/experiments"))
manifest, path = generator.generate(ManifestType.FULL)

# Python SDK - 客户端（自动集成）
from runicorn.remote_storage import MetadataSyncService
service = MetadataSyncService(..., use_manifest_sync=True)
service.sync_all()  # 自动使用 manifest，失败时回退
```

### Artifacts

```bash
# 列出 artifacts
GET /api/artifacts?type=model

# 获取版本
GET /api/artifacts/{name}/versions

# 获取版本详情
GET /api/artifacts/{name}/v{version}

# 获取血缘图
GET /api/artifacts/{name}/v{version}/lineage
```

### V2 API (高性能)

```bash
# 高级查询
GET /api/v2/experiments?project=demo&status=finished&page=1&per_page=50

# 快速指标
GET /api/v2/experiments/{id}/metrics/fast?downsample=1000
```

### 配置

```bash
# 获取配置
GET /api/config

# 设置存储根目录
POST /api/config/user_root_dir
Body: {"path": "E:\\RunicornData"}
```

### 远程同步

```bash
# 连接 SSH
POST /api/unified/connect
Body: {"host": "192.168.1.100", "username": "user", "password": "secret"}

# 配置智能同步
POST /api/unified/configure_mode
Body: {"mode": "smart", "remote_root": "/data/runicorn"}

# 检查状态
GET /api/unified/status
```

---

## 响应格式

### 成功响应

```json
{
  "ok": true,
  "data": { ... },
  "message": "操作成功"
}
```

### 错误响应

```json
{
  "detail": "错误描述"
}
```

---

## 常用状态码

| 代码 | 含义 | 操作 |
|------|------|------|
| 200 | 成功 | 处理响应 |
| 400 | 请求错误 | 检查参数 |
| 404 | 未找到 | 验证资源存在 |
| 429 | 速率限制 | 等待后重试 |
| 500 | 服务器错误 | 检查日志，重试 |

---

## 速率限制

| 端点类型 | 限制 |
|---------|------|
| 标准 | 60/分钟 |
| V2 查询 | 100/分钟 |
| SSH 连接 | 5/分钟 |
| 批量删除 | 10/分钟 |

**响应头**:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 15
```

---

## Python 快速示例

### 列出和过滤

```python
import requests

# 获取所有已完成的运行
runs = requests.get('http://127.0.0.1:23300/api/runs').json()
finished = [r for r in runs if r['status'] == 'finished']
```

### 获取指标并绘图

```python
import requests
import matplotlib.pyplot as plt

metrics = requests.get(f'http://127.0.0.1:23300/api/runs/{run_id}/metrics_step').json()

steps = [row['global_step'] for row in metrics['rows']]
loss = [row['loss'] for row in metrics['rows']]

plt.plot(steps, loss)
plt.show()
```

### 流式日志

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

## JavaScript 快速示例

### 获取运行

```javascript
const response = await fetch('http://127.0.0.1:23300/api/runs')
const runs = await response.json()

runs.forEach(run => {
  console.log(`${run.id}: ${run.status}`)
})
```

### WebSocket 日志

```javascript
const ws = new WebSocket('ws://127.0.0.1:23300/api/runs/{run_id}/logs/ws')

ws.onmessage = (event) => {
  console.log(event.data)
}
```

---

## 数据类型

### Run ID 格式

```
YYYYMMDD_HHMMSS_XXXXXX

示例:
- 20250114_153045_a1b2c3
- 20241225_090000_xyz789
```

### 时间戳

所有时间戳都是 **Unix 时间戳**（自纪元以来的秒数）：

```python
import time
from datetime import datetime

# 当前时间戳
ts = time.time()  # 1704067200.5

# 转换为 datetime
dt = datetime.fromtimestamp(ts)  # 2025-10-14 15:30:45

# 从 datetime 转换
ts = dt.timestamp()  # 1704067200.5
```

### 文件大小

所有大小以**字节**为单位：

```python
# 将字节转换为可读格式
def format_bytes(bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024

# 102400000 bytes → "97.66 MB"
```

---

## 环境变量

```bash
# API 基础 URL（用于开发）
export VITE_API_BASE="http://localhost:23300/api"

# 存储根目录
export RUNICORN_DIR="E:\\RunicornData"

# 禁用现代存储（测试）
export RUNICORN_DISABLE_MODERN_STORAGE=1
```

---

## 故障排查

### API 无响应

```bash
# 检查 viewer 是否运行
curl http://127.0.0.1:23300/api/health

# 如果未运行则启动 viewer
runicorn viewer --host 127.0.0.1 --port 23300
```

### CORS 错误（来自浏览器）

API 允许来自所有来源的 CORS。如果仍然出现 CORS 错误：

```javascript
// 显式添加 mode: 'cors'
fetch('http://127.0.0.1:23300/api/runs', {
  mode: 'cors',
  headers: {
    'Content-Type': 'application/json'
  }
})
```

### 大响应超时

```python
import requests

# 对于大数据集增加超时时间
response = requests.get(
    'http://127.0.0.1:23300/api/runs',
    timeout=60  # 60 秒
)
```

---

## 完整文档

详细 API 文档请参阅：

- **[README.md](./README.md)** - API 概览和快速开始
- **[runs_api.md](./runs_api.md)** - 实验管理
- **[artifacts_api.md](./artifacts_api.md)** - 模型版本控制
- **[v2_api.md](./v2_api.md)** - 高性能查询
- **[metrics_api.md](./metrics_api.md)** - 指标和日志
- **[config_api.md](./config_api.md)** - 配置
- **[ssh_api.md](./ssh_api.md)** - 远程同步
- **[manifest_api.md](./manifest_api.md)** - Manifest-based 同步 🚀

---

**交互式 API 文档**: `http://127.0.0.1:23300/docs` (FastAPI 自动生成)

---

**最后更新**: 2025-10-14


