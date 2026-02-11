[English](../en/paths_api.md) | [简体中文](paths_api.md)

---

# 路径层级 API

**版本**: v0.6.0  
**路由文件**: `projects.py`（导出为 `projects_router`）  
**前缀**: `/api`

灵活的基于路径的实验组织，支持树形导航、批量操作和导出。

---

## 端点概览

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/paths` | 列出所有唯一路径（可选包含统计） |
| GET | `/api/paths/tree` | 获取路径树结构 |
| GET | `/api/paths/runs` | 按路径过滤列出运行 |
| POST | `/api/paths/soft-delete` | 按路径批量软删除运行 |
| GET | `/api/paths/export` | 按路径导出运行（JSON 或 ZIP） |

### 旧版兼容

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/projects` | 列出顶层路径段 |
| GET | `/api/projects/{project}/names` | 列出第二层路径段 |
| GET | `/api/projects/{project}/names/{name}/runs` | 列出 project/name 下的运行 |

---

## GET /api/paths

列出所有唯一的实验路径。

**查询参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `include_stats` | bool | `false` | 包含每个路径的运行统计信息 |

**响应**（不含统计）：
```json
{
  "paths": ["cv/resnet", "cv/yolo", "nlp/bert"],
  "tree": {
    "cv": {
      "resnet": {},
      "yolo": {}
    },
    "nlp": {
      "bert": {}
    }
  }
}
```

**响应**（`include_stats=true`）：
```json
{
  "paths": ["cv", "cv/resnet", "cv/yolo"],
  "tree": { ... },
  "stats": {
    "cv": {"total": 15, "running": 2, "finished": 12, "failed": 1},
    "cv/resnet": {"total": 8, "running": 1, "finished": 7, "failed": 0},
    "cv/yolo": {"total": 7, "running": 1, "finished": 5, "failed": 1}
  }
}
```

> **注意**：当 `include_stats=true` 时，祖先路径会自动包含聚合统计。

---

## GET /api/paths/tree

仅获取路径树结构。

**响应**：
```json
{
  "tree": {
    "cv": {
      "resnet": {},
      "yolo": {}
    },
    "nlp": {
      "bert": {}
    }
  }
}
```

---

## GET /api/paths/runs

按路径前缀或精确匹配列出运行。

**查询参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `path` | string | `null` | 用于过滤的路径前缀（如 `cv/yolo`） |
| `exact` | bool | `false` | 为 true 时仅精确匹配路径 |

**响应**：`RunListItem` 数组：
```json
[
  {
    "id": "20250114_153045_a1b2c3",
    "run_dir": "/data/runicorn/...",
    "created_time": 1736870400.0,
    "status": "finished",
    "pid": null,
    "best_metric_value": 0.95,
    "best_metric_name": "accuracy",
    "path": "cv/yolo",
    "alias": "yolov8-baseline"
  }
]
```

**示例**：
```bash
# cv/ 下的所有运行
GET /api/paths/runs?path=cv

# 仅精确匹配 cv/yolo 的运行
GET /api/paths/runs?path=cv/yolo&exact=true

# 所有运行（无过滤）
GET /api/paths/runs
```

---

## POST /api/paths/soft-delete

按路径批量软删除所有运行（移入回收站）。

**请求体**：
```json
{
  "path": "old_experiments",
  "exact": false
}
```

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `path` | string | 是 | 要匹配的路径前缀 |
| `exact` | bool | 否（默认 false） | 为 true 时仅精确匹配路径 |

**响应**：
```json
{
  "path": "old_experiments",
  "deleted_count": 12,
  "errors": null,
  "message": "Moved 12 runs to recycle bin"
}
```

---

## GET /api/paths/export

将某路径下所有运行导出为 JSON 元数据或 ZIP 归档。

**查询参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `path` | string | **必填** | 要匹配的路径前缀 |
| `exact` | bool | `false` | 为 true 时仅精确匹配路径 |
| `format` | string | `json` | 导出格式：`json` 或 `zip` |

**响应**（`format=json`）：
```json
{
  "path": "cv/yolo",
  "exact": false,
  "total_runs": 5,
  "runs": [
    {
      "run_id": "20250114_153045_a1b2c3",
      "path": "cv/yolo",
      "alias": "yolov8-baseline",
      "status": "finished",
      "created_time": 1736870400.0,
      "summary": { "best_metric_value": 0.95 },
      "meta": { ... }
    }
  ]
}
```

**响应**（`format=zip`）：二进制 ZIP 文件下载，包含：
- `index.json` — 所有导出运行的元数据索引
- `{run_id}/` — 每个运行的完整目录内容

**示例**：
```bash
# 导出元数据为 JSON
GET /api/paths/export?path=cv/yolo&format=json

# 下载完整数据为 ZIP
GET /api/paths/export?path=cv/yolo&format=zip
```

---

## 旧版端点

这些端点通过将旧的 project/name 层级映射到新的基于路径的系统来提供向后兼容。

### GET /api/projects

返回顶层路径段作为"项目"。

```json
{"projects": ["cv", "nlp", "rl"]}
```

### GET /api/projects/{project}/names

返回项目下的第二层路径段。

```json
{"names": ["resnet", "yolo", "vit"]}
```

### GET /api/projects/{project}/names/{name}/runs

返回匹配路径前缀 `{project}/{name}` 的运行。

```json
[
  {
    "run_id": "20250114_153045_a1b2c3",
    "path": "cv/yolo",
    "alias": "yolov8-baseline",
    "status": "finished",
    "start_time": 1736870400.0
  }
]
```

---

**[返回 API 索引](./API_INDEX.md)** | **[返回主页](../../README.md)**
