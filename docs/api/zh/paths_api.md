[English](../en/paths_api.md) | [简体中文](paths_api.md)

---

# 路径层级 API 参考文档

> **版本**: v0.6.0  
> **最后更新**: 2025-01-XX  
> **Base URL**: `http://127.0.0.1:23300/api`

---

## 📖 目录

- [概述](#概述)
- [路径命名](#路径命名)
- [端点](#端点)
  - [GET /api/paths](#get-apipaths)
  - [GET /api/paths/tree](#get-apipathstree)
  - [GET /api/paths/runs](#get-apipathsruns)
  - [POST /api/paths/soft-delete](#post-apipathssoft-delete)
  - [GET /api/paths/export](#get-apipathsexport)
- [旧版兼容](#旧版兼容)
- [示例](#示例)

---

## 概述

路径层级 API 提供基于路径命名的灵活实验组织方式。不再使用固定的 `project/name` 结构，现在可以使用任意深度的路径，如 `cv/detection/yolo/ablation`。

### 主要特性

- **灵活深度**: 使用任意层级组织实验
- **树形导航**: VSCode 风格的层级浏览
- **批量操作**: 删除或导出整个路径子树
- **统计信息**: 每个路径的运行计数，用于 UI 徽章
- **旧版兼容**: 旧的 `project/name` API 仍然可用

### 路径结构

```
<storage_root>/runs/
├── cv/
│   ├── detection/
│   │   └── yolo/
│   │       ├── 20250114_153045_a1b2c3/
│   │       └── 20250114_160000_b8c4d2/
│   └── classification/
│       └── resnet/
│           └── 20250114_170000_c9e5f3/
└── nlp/
    └── bert/
        └── 20250114_180000_d0f6g4/
```

---

## 路径命名

### SDK 用法

```python
import runicorn

# 灵活的路径深度
run = runicorn.init(path="cv/detection/yolo/ablation_lr")
run = runicorn.init(path="nlp/bert/finetune")
run = runicorn.init(path="thesis/chapter3")

# 可选的别名，便于识别
run = runicorn.init(path="cv/yolo", alias="best-v2")
```

### 路径规则

| 规则 | 描述 |
|------|------|
| 字符 | 仅允许 `a-z A-Z 0-9 _ - /` |
| 禁止遍历 | 不允许 `..` |
| 最大长度 | 200 字符 |
| 分隔符 | 始终使用 `/`（存储时转换为操作系统分隔符） |
| 默认值 | 未指定时为 `"default"` |
| 根路径 | `"/"` 或 `""` 表示根级别 |

### 示例

```python
# 有效路径
"cv/yolo"
"nlp/bert/finetune"
"thesis/chapter3/experiment1"
"my-project/test_run"

# 无效路径
"cv/../secrets"     # 包含 ..
"path/with spaces"  # 包含空格
"path\\windows"     # 使用 / 而不是 \
```

---

## 端点

### GET /api/paths

列出所有唯一的实验路径，可选包含统计信息。

#### 请求

**URL**: `GET /api/paths`

**查询参数**:

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `include_stats` | boolean | `false` | 包含每个路径的运行计数统计 |

#### 响应

**不含统计** (`include_stats=false`):
```json
{
  "paths": [
    "cv/detection/yolo",
    "cv/classification/resnet",
    "nlp/bert"
  ],
  "tree": {
    "cv": {
      "detection": {
        "yolo": {}
      },
      "classification": {
        "resnet": {}
      }
    },
    "nlp": {
      "bert": {}
    }
  }
}
```

**含统计** (`include_stats=true`):
```json
{
  "paths": ["cv", "cv/detection", "cv/detection/yolo", "nlp", "nlp/bert"],
  "tree": {
    "cv": {
      "detection": {
        "yolo": {}
      }
    },
    "nlp": {
      "bert": {}
    }
  },
  "stats": {
    "cv": {"total": 15, "running": 2, "finished": 12, "failed": 1},
    "cv/detection": {"total": 10, "running": 1, "finished": 8, "failed": 1},
    "cv/detection/yolo": {"total": 8, "running": 1, "finished": 6, "failed": 1},
    "nlp": {"total": 5, "running": 0, "finished": 5, "failed": 0},
    "nlp/bert": {"total": 5, "running": 0, "finished": 5, "failed": 0}
  }
}
```

#### 示例

**cURL**:
```bash
# 基本列表
curl http://localhost:23300/api/paths

# 含统计信息
curl "http://localhost:23300/api/paths?include_stats=true"
```

**Python**:
```python
import requests

# 获取带统计的路径
response = requests.get(
    "http://localhost:23300/api/paths",
    params={"include_stats": True}
)
data = response.json()

for path, stats in data["stats"].items():
    print(f"{path}: {stats['total']} 个运行 ({stats['running']} 运行中)")
```

---

### GET /api/paths/tree

仅获取树结构（不含路径列表或统计）。

#### 请求

**URL**: `GET /api/paths/tree`

#### 响应

```json
{
  "tree": {
    "cv": {
      "detection": {
        "yolo": {}
      },
      "classification": {
        "resnet": {}
      }
    },
    "nlp": {
      "bert": {}
    }
  }
}
```

#### 示例

```bash
curl http://localhost:23300/api/paths/tree
```

---

### GET /api/paths/runs

按路径前缀过滤列出运行。

#### 请求

**URL**: `GET /api/paths/runs`

**查询参数**:

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `path` | string | `null` | 要过滤的路径前缀 |
| `exact` | boolean | `false` | 如果为 true，仅匹配精确路径 |

#### 响应

```json
[
  {
    "id": "20250114_153045_a1b2c3",
    "run_dir": "/data/runicorn/runs/cv/yolo/20250114_153045_a1b2c3",
    "created_time": 1705234245.5,
    "status": "finished",
    "pid": null,
    "best_metric_value": 0.95,
    "best_metric_name": "accuracy",
    "path": "cv/yolo",
    "alias": "best-v2"
  },
  {
    "id": "20250114_160000_b8c4d2",
    "run_dir": "/data/runicorn/runs/cv/yolo/ablation/20250114_160000_b8c4d2",
    "created_time": 1705236000.0,
    "status": "running",
    "pid": 12345,
    "best_metric_value": null,
    "best_metric_name": null,
    "path": "cv/yolo/ablation",
    "alias": null
  }
]
```

#### 示例

**cURL**:
```bash
# cv/yolo 下的所有运行（包括 cv/yolo/ablation 等）
curl "http://localhost:23300/api/paths/runs?path=cv/yolo"

# 仅精确路径为 cv/yolo 的运行
curl "http://localhost:23300/api/paths/runs?path=cv/yolo&exact=true"

# 所有运行（无过滤）
curl "http://localhost:23300/api/paths/runs"
```

**Python**:
```python
import requests

# 获取某路径下的运行
response = requests.get(
    "http://localhost:23300/api/paths/runs",
    params={"path": "cv/detection", "exact": False}
)
runs = response.json()

for run in runs:
    print(f"{run['id']}: {run['status']} ({run['path']})")
```

---

### POST /api/paths/soft-delete

软删除某路径下的所有运行（移至回收站）。

#### 请求

**URL**: `POST /api/paths/soft-delete`

**Headers**:
```
Content-Type: application/json
```

**Body**:

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `path` | string | ✅ | 要匹配的路径前缀 |
| `exact` | boolean | ❌ | 如果为 true，仅匹配精确路径（默认: false） |

#### 响应

```json
{
  "path": "cv/yolo/old_experiments",
  "deleted_count": 5,
  "errors": null,
  "message": "Moved 5 runs to recycle bin"
}
```

**有错误时**:
```json
{
  "path": "cv/yolo",
  "deleted_count": 3,
  "errors": [
    "Failed to delete 20250114_153045_a1b2c3",
    "Error deleting 20250114_160000_b8c4d2: Permission denied"
  ],
  "message": "Moved 3 runs to recycle bin"
}
```

#### 示例

**cURL**:
```bash
# 删除 cv/yolo 下的所有运行（包括子路径）
curl -X POST http://localhost:23300/api/paths/soft-delete \
  -H "Content-Type: application/json" \
  -d '{"path": "cv/yolo"}'

# 仅删除精确路径为 cv/yolo 的运行
curl -X POST http://localhost:23300/api/paths/soft-delete \
  -H "Content-Type: application/json" \
  -d '{"path": "cv/yolo", "exact": true}'
```

**Python**:
```python
import requests

response = requests.post(
    "http://localhost:23300/api/paths/soft-delete",
    json={"path": "old_experiments", "exact": False}
)
result = response.json()
print(f"已删除 {result['deleted_count']} 个运行")
```

---

### GET /api/paths/export

将某路径下的所有运行导出为 JSON 或 ZIP。

#### 请求

**URL**: `GET /api/paths/export`

**查询参数**:

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `path` | string | **必需** | 要导出的路径前缀 |
| `exact` | boolean | `false` | 如果为 true，仅匹配精确路径 |
| `format` | string | `"json"` | 导出格式: `json` 或 `zip` |

#### 响应

**JSON 格式** (`format=json`):
```json
{
  "path": "cv/yolo",
  "exact": false,
  "total_runs": 3,
  "runs": [
    {
      "run_id": "20250114_153045_a1b2c3",
      "path": "cv/yolo",
      "alias": "best-v2",
      "status": "finished",
      "created_time": 1705234245.5,
      "summary": {
        "best_metric_value": 0.95,
        "best_metric_name": "accuracy"
      },
      "meta": {
        "python": "3.11.0",
        "platform": "Linux 5.15.0",
        "hostname": "gpu-server"
      }
    }
  ]
}
```

**ZIP 格式** (`format=zip`):
- 返回可下载的 ZIP 文件
- 包含带元数据的 `index.json`
- 包含完整的运行目录及所有文件

#### 示例

**cURL**:
```bash
# 导出为 JSON
curl "http://localhost:23300/api/paths/export?path=cv/yolo&format=json"

# 导出为 ZIP（下载）
curl -o export.zip "http://localhost:23300/api/paths/export?path=cv/yolo&format=zip"
```

**Python**:
```python
import requests

# JSON 导出
response = requests.get(
    "http://localhost:23300/api/paths/export",
    params={"path": "cv/yolo", "format": "json"}
)
data = response.json()
print(f"已导出 {data['total_runs']} 个运行")

# ZIP 导出
response = requests.get(
    "http://localhost:23300/api/paths/export",
    params={"path": "cv/yolo", "format": "zip"}
)
with open("export.zip", "wb") as f:
    f.write(response.content)
```

---

## 旧版兼容

旧的 `project/name` API 端点仍然可用以保持向后兼容。

### GET /api/projects

列出顶级路径段（每个路径的第一段）。

```bash
curl http://localhost:23300/api/projects
```

**响应**:
```json
{
  "projects": ["cv", "nlp", "default"]
}
```

### GET /api/projects/{project}/names

列出给定第一段的第二级路径段。

```bash
curl http://localhost:23300/api/projects/cv/names
```

**响应**:
```json
{
  "names": ["detection", "classification"]
}
```

### GET /api/projects/{project}/names/{name}/runs

列出给定 `project/name` 组合的运行。

```bash
curl http://localhost:23300/api/projects/cv/names/detection/runs
```

**响应**:
```json
[
  {
    "run_id": "20250114_153045_a1b2c3",
    "path": "cv/detection/yolo",
    "alias": null,
    "status": "finished",
    "start_time": 1705234245.5
  }
]
```

---

## 示例

### 构建路径树 UI

```python
import requests

def build_tree_ui():
    response = requests.get(
        "http://localhost:23300/api/paths",
        params={"include_stats": True}
    )
    data = response.json()
    
    def render_tree(tree, stats, indent=0):
        for name, children in tree.items():
            # 构建完整路径用于统计查找
            path = name  # 简化版；实际实现需要完整路径跟踪
            stat = stats.get(path, {})
            count = stat.get("total", 0)
            running = stat.get("running", 0)
            
            prefix = "  " * indent
            badge = f" ({running} 运行中)" if running > 0 else ""
            print(f"{prefix}📁 {name} [{count}]{badge}")
            
            if children:
                render_tree(children, stats, indent + 1)
    
    render_tree(data["tree"], data.get("stats", {}))

build_tree_ui()
```

**输出**:
```
📁 cv [15] (2 运行中)
  📁 detection [10] (1 运行中)
    📁 yolo [8] (1 运行中)
  📁 classification [5]
    📁 resnet [5]
📁 nlp [5]
  📁 bert [5]
```

### 批量清理脚本

```python
import requests
from datetime import datetime, timedelta

def cleanup_old_experiments(days_old=30):
    """删除超过 N 天的实验。"""
    
    # 获取所有路径
    response = requests.get("http://localhost:23300/api/paths")
    paths = response.json()["paths"]
    
    cutoff = datetime.now() - timedelta(days=days_old)
    cutoff_ts = cutoff.timestamp()
    
    for path in paths:
        # 获取此路径的运行
        response = requests.get(
            "http://localhost:23300/api/paths/runs",
            params={"path": path, "exact": True}
        )
        runs = response.json()
        
        # 检查是否所有运行都是旧的
        old_runs = [r for r in runs if r["created_time"] < cutoff_ts]
        
        if len(old_runs) == len(runs) and runs:
            print(f"正在删除 {path} 中的 {len(runs)} 个旧运行")
            requests.post(
                "http://localhost:23300/api/paths/soft-delete",
                json={"path": path, "exact": True}
            )

cleanup_old_experiments(days_old=30)
```

---

## 错误处理

### 常见错误

| 状态码 | 错误 | 原因 |
|--------|------|------|
| 400 | `path is required` | 缺少 path 参数 |
| 400 | `Unsupported format: xyz` | 无效的导出格式 |
| 404 | `No runs found for this path` | ZIP 导出时没有匹配的运行 |
| 500 | `Failed to create zip: ...` | ZIP 创建错误 |

### 错误响应格式

```json
{
  "detail": "path is required"
}
```

---

## 相关文档

- **[Runs API](./runs_api.md)** - 单个运行管理
- **[API 索引](./API_INDEX.md)** - 完整 API 参考
- **[快速参考](./QUICK_REFERENCE.md)** - API 快速参考

---

**作者**: Runicorn Development Team  
**版本**: v0.6.0  
**最后更新**: 2025-01-XX

**[返回 API 索引](API_INDEX.md)**
