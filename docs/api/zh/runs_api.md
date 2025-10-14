[English](../en/runs_api.md) | [简体中文](runs_api.md)

---

# Runs API - 实验管理

**模块**: Runs API  
**基础路径**: `/api/runs`  
**版本**: v1.0  
**描述**: 创建、读取、更新和管理实验运行，支持软删除和恢复功能。

---

## 端点概览

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/runs` | 列出所有实验运行 |
| GET | `/runs/{run_id}` | 获取详细运行信息 |
| POST | `/runs/soft-delete` | 软删除运行（移至回收站）|
| GET | `/recycle-bin` | 列出已删除的运行 |
| POST | `/recycle-bin/restore` | 从回收站恢复运行 |
| POST | `/recycle-bin/empty` | 永久删除回收站中的所有运行 |

---

## 列出运行

获取所有实验运行及基本元数据的列表。

### 请求

```http
GET /api/runs
```

**查询参数**: 无

### 响应

**状态码**: `200 OK`

**响应体**:
```json
[
  {
    "id": "20250114_153045_a1b2c3",
    "run_dir": "E:\\RunicornData\\image_classification\\resnet_baseline\\runs\\20250114_153045_a1b2c3",
    "created_time": 1704067200.5,
    "status": "finished",
    "pid": 12345,
    "best_metric_value": 0.9542,
    "best_metric_name": "accuracy",
    "project": "image_classification",
    "name": "resnet_baseline",
    "artifacts_created_count": 2,
    "artifacts_used_count": 1
  },
  {
    "id": "20250114_120000_d4e5f6",
    "run_dir": "E:\\RunicornData\\nlp\\bert_finetune\\runs\\20250114_120000_d4e5f6",
    "created_time": 1704053400.2,
    "status": "running",
    "pid": 23456,
    "best_metric_value": null,
    "best_metric_name": null,
    "project": "nlp",
    "name": "bert_finetune",
    "artifacts_created_count": 0,
    "artifacts_used_count": 0
  }
]
```

### 响应字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | string | 唯一运行标识符（格式：YYYYMMDD_HHMMSS_XXXXXX）|
| `run_dir` | string | 运行目录的绝对路径 |
| `created_time` | number | 运行创建的 Unix 时间戳 |
| `status` | string | 运行状态：`running`、`finished`、`failed`、`interrupted` |
| `pid` | number\|null | 进程 ID（进程结束后为 null）|
| `best_metric_value` | number\|null | 最佳指标值（如果配置了主要指标）|
| `best_metric_name` | string\|null | 主要指标的名称 |
| `project` | string | 项目名称 |
| `name` | string | 实验名称 |
| `artifacts_created_count` | number | 此运行创建的 artifacts 数量 |
| `artifacts_used_count` | number | 此运行使用的 artifacts 数量 |

### 示例

**cURL**:
```bash
curl http://127.0.0.1:23300/api/runs
```

**Python**:
```python
import requests

response = requests.get('http://127.0.0.1:23300/api/runs')
runs = response.json()

for run in runs:
    print(f"{run['id']}: {run['status']} - {run['best_metric_name']}={run['best_metric_value']}")
```

**JavaScript**:
```javascript
fetch('http://127.0.0.1:23300/api/runs')
  .then(res => res.json())
  .then(runs => {
    runs.forEach(run => {
      console.log(`${run.id}: ${run.status}`)
    })
  })
```

---

## 获取运行详情

检索特定运行的详细信息。

### 请求

```http
GET /api/runs/{run_id}
```

**路径参数**:
| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `run_id` | string | 是 | 运行标识符（格式：YYYYMMDD_HHMMSS_XXXXXX）|

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "id": "20250114_153045_a1b2c3",
  "status": "finished",
  "pid": 12345,
  "run_dir": "E:\\RunicornData\\image_classification\\resnet_baseline\\runs\\20250114_153045_a1b2c3",
  "project": "image_classification",
  "name": "resnet_baseline",
  "logs": "E:\\RunicornData\\image_classification\\resnet_baseline\\runs\\20250114_153045_a1b2c3\\logs.txt",
  "metrics": "E:\\RunicornData\\image_classification\\resnet_baseline\\runs\\20250114_153045_a1b2c3\\events.jsonl",
  "metrics_step": "E:\\RunicornData\\image_classification\\resnet_baseline\\runs\\20250114_153045_a1b2c3\\events.jsonl",
  "artifacts_created_count": 2,
  "artifacts_used_count": 1
}
```

### 错误响应

**404 未找到**:
```json
{
  "detail": "Run not found"
}
```

### 示例

**cURL**:
```bash
curl http://127.0.0.1:23300/api/runs/20250114_153045_a1b2c3
```

**Python**:
```python
import requests

run_id = "20250114_153045_a1b2c3"
response = requests.get(f'http://127.0.0.1:23300/api/runs/{run_id}')

if response.status_code == 200:
    detail = response.json()
    print(f"Run {detail['id']}")
    print(f"Status: {detail['status']}")
    print(f"Project: {detail['project']}/{detail['name']}")
elif response.status_code == 404:
    print("Run not found")
```

---

## 软删除运行

将运行移至回收站（软删除），不会永久删除数据。

### 请求

```http
POST /api/runs/soft-delete
Content-Type: application/json
```

**请求体**:
```json
{
  "run_ids": [
    "20250114_153045_a1b2c3",
    "20250114_120000_d4e5f6"
  ]
}
```

### 请求体 Schema

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `run_ids` | array[string] | 是 | 要删除的运行 ID 列表（最多 100 个）|

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "deleted_count": 2,
  "results": {
    "20250114_153045_a1b2c3": {
      "success": true
    },
    "20250114_120000_d4e5f6": {
      "success": true
    }
  },
  "message": "Soft deleted 2 of 2 runs"
}
```

### 错误响应

**400 Bad Request** (无效输入):
```json
{
  "detail": "run_ids is required and must be a list"
}
```

**400 Bad Request** (超过批量大小):
```json
{
  "detail": "Cannot delete more than 100 runs at once"
}
```

**400 Bad Request** (无效的 run_id 格式):
```json
{
  "detail": "Invalid run_id format: abc123"
}
```

### 示例

**cURL**:
```bash
curl -X POST http://127.0.0.1:23300/api/runs/soft-delete \
  -H "Content-Type: application/json" \
  -d '{
    "run_ids": ["20250114_153045_a1b2c3", "20250114_120000_d4e5f6"]
  }'
```

**Python**:
```python
import requests

run_ids = ["20250114_153045_a1b2c3", "20250114_120000_d4e5f6"]

response = requests.post(
    'http://127.0.0.1:23300/api/runs/soft-delete',
    json={"run_ids": run_ids}
)

result = response.json()
print(f"已删除 {result['deleted_count']} 个运行")

# 检查各个结果
for run_id, status in result['results'].items():
    if status['success']:
        print(f"✓ 已删除 {run_id}")
    else:
        print(f"✗ 删除失败 {run_id}: {status.get('error')}")
```

---

## 列出已删除的运行

获取回收站中的所有运行。

### 请求

```http
GET /api/recycle-bin
```

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "deleted_runs": [
    {
      "id": "20250114_153045_a1b2c3",
      "project": "image_classification",
      "name": "resnet_baseline",
      "created_time": 1704067200.5,
      "deleted_at": 1704070800.2,
      "delete_reason": "user_deleted",
      "original_status": "finished",
      "run_dir": "E:\\RunicornData\\image_classification\\resnet_baseline\\runs\\20250114_153045_a1b2c3"
    }
  ]
}
```

### 响应字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | string | 运行标识符 |
| `project` | string | 项目名称 |
| `name` | string | 实验名称 |
| `created_time` | number | 原始创建时间戳 |
| `deleted_at` | number | 删除时间戳 |
| `delete_reason` | string | 删除原因 |
| `original_status` | string | 删除前的状态 |
| `run_dir` | string | 运行目录路径 |

---

## 恢复运行

从回收站恢复运行。

### 请求

```http
POST /api/recycle-bin/restore
Content-Type: application/json
```

**请求体**:
```json
{
  "run_ids": [
    "20250114_153045_a1b2c3"
  ]
}
```

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "restored_count": 1,
  "results": {
    "20250114_153045_a1b2c3": {
      "success": true
    }
  },
  "message": "Restored 1 of 1 runs"
}
```

### 示例

**Python**:
```python
import requests

run_ids = ["20250114_153045_a1b2c3"]

response = requests.post(
    'http://127.0.0.1:23300/api/recycle-bin/restore',
    json={"run_ids": run_ids}
)

result = response.json()
print(f"已恢复 {result['restored_count']} 个运行")
```

---

## 清空回收站

永久删除回收站中的所有运行。

### 请求

```http
POST /api/recycle-bin/empty
Content-Type: application/json
```

**请求体**:
```json
{
  "confirm": true
}
```

### 请求体 Schema

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `confirm` | boolean | 是 | 必须为 `true` 才能继续永久删除 |

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "permanently_deleted": 15,
  "message": "Permanently deleted 15 runs"
}
```

### 错误响应

**400 Bad Request** (缺少确认):
```json
{
  "detail": "Must set confirm=true to permanently delete"
}
```

### 示例

**cURL**:
```bash
curl -X POST http://127.0.0.1:23300/api/recycle-bin/empty \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}'
```

**Python** (带确认提示):
```python
import requests

# 询问用户确认
confirm = input("永久删除回收站中的所有运行？ (yes/no): ")

if confirm.lower() == 'yes':
    response = requests.post(
        'http://127.0.0.1:23300/api/recycle-bin/empty',
        json={"confirm": True}
    )
    
    result = response.json()
    print(result['message'])
else:
    print("操作已取消")
```

---

## 数据模型

### RunListItem

```typescript
interface RunListItem {
  id: string                        // Run ID
  run_dir: string | null            // 运行目录路径
  created_time: number | null       // Unix 时间戳
  status: "running" | "finished" | "failed" | "interrupted"
  pid: number | null                // 进程 ID
  best_metric_value: number | null  // 最佳指标值
  best_metric_name: string | null   // 主要指标名称
  project: string | null            // 项目名称
  name: string | null               // 实验名称
  artifacts_created_count: number   // 创建的 artifacts 数量
  artifacts_used_count: number      // 使用的 artifacts 数量
}
```

### DeletedRun

```typescript
interface DeletedRun {
  id: string              // Run ID
  project: string         // 项目名称
  name: string            // 实验名称
  created_time: number    // 原始创建时间戳
  deleted_at: number      // 删除时间戳
  delete_reason: string   // 删除原因
  original_status: string // 删除前的状态
  run_dir: string         // 运行目录路径
}
```

---

## 最佳实践

### 批量操作

删除或恢复多个运行时：

```python
# ✅ 好: 批量操作（高效）
run_ids = ["run1", "run2", "run3", ..., "run100"]  # 最多 100 个
requests.post('/api/runs/soft-delete', json={"run_ids": run_ids})

# ❌ 差: 单个操作（慢）
for run_id in run_ids:
    requests.post('/api/runs/soft-delete', json={"run_ids": [run_id]})
```

### 处理大结果集

```python
import requests

# 获取所有运行
all_runs = requests.get('http://127.0.0.1:23300/api/runs').json()

# V1 API 客户端过滤
running_runs = [r for r in all_runs if r['status'] == 'running']

# 推荐: 使用 V2 API 进行服务端过滤
# 查看 docs/api/zh/v2_api.md
```

### 状态管理

**自动状态检测**: 当进程不再活动时，API 会自动更新标记为 `running` 的运行状态。

```python
# API 检查 PID 是否仍然存活
# 如果不存活，状态自动更新为 "failed"
# 退出原因: "process_not_found"

# 后台任务: 每 30 秒运行一次
# 按需: 列出状态为 "running" 的运行时
```

---

## 错误码

| 状态码 | 场景 | 操作 |
|--------|------|------|
| `400` | 无效的 run_id 格式 | 检查 ID 格式：YYYYMMDD_HHMMSS_XXXXXX |
| `400` | 批量大小 > 100 | 拆分为多个批次 |
| `400` | 缺少 run_ids | 在请求体中包含 run_ids 数组 |
| `404` | 运行未找到 | 通过 GET /runs 验证 run_id 存在 |
| `500` | 服务器错误 | 检查服务器日志，重试请求 |

---

## 速率限制

- **GET /runs**: 每分钟 100 个请求
- **POST /runs/soft-delete**: 每分钟 20 个请求
- **POST /recycle-bin/empty**: 每分钟 5 个请求

---

## 注意事项

### 软删除 vs 永久删除

**软删除**（回收站）:
- 在运行目录中创建 `.deleted` 标记文件
- 运行从主列表中隐藏
- 所有数据保持完整
- 可以随时恢复

**永久删除**:
- 物理删除运行目录
- **不可逆** - 所有数据丢失
- 仅通过 `/recycle-bin/empty` 可用

### 文件结构

软删除后，运行目录包含：
```
runs/20250114_153045_a1b2c3/
├── meta.json
├── status.json
├── events.jsonl
├── logs.txt
└── .deleted        ← 软删除标记
    {
      "deleted_at": 1704070800.2,
      "reason": "user_deleted",
      "original_status": "finished"
    }
```

---

## 相关 API

- **Metrics API**: 获取运行指标数据 - [metrics_api.md](./metrics_api.md)
- **V2 Experiments API**: 高性能查询 - [v2_api.md](./v2_api.md)
- **Artifacts API**: 管理运行 artifacts - [artifacts_api.md](./artifacts_api.md)

---

**最后更新**: 2025-10-14


