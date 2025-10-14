[English](../en/artifacts_api.md) | [简体中文](artifacts_api.md)

---

# Artifacts API - 模型版本控制

**模块**: Artifacts API  
**基础路径**: `/api/artifacts`  
**版本**: v1.0  
**描述**: ML 模型、数据集和其他资产的版本控制，支持去重和血缘追踪。

---

## 端点概览

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/artifacts` | 列出所有 artifacts |
| GET | `/artifacts/{name}/versions` | 列出 artifact 的版本 |
| GET | `/artifacts/{name}/v{version}` | 获取 artifact 版本详情 |
| GET | `/artifacts/{name}/v{version}/files` | 列出 artifact 版本中的文件 |
| GET | `/artifacts/{name}/v{version}/lineage` | 获取 artifact 血缘图 |
| GET | `/artifacts/stats` | 获取存储统计信息 |
| DELETE | `/artifacts/{name}/v{version}` | 删除 artifact 版本 |

---

## 列出 Artifacts

获取所有 artifacts 的列表，可选类型过滤。

### 请求

```http
GET /api/artifacts?type={type}
```

**查询参数**:
| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `type` | string | 否 | 按类型过滤：`model`、`dataset`、`config`、`code`、`custom` |

### 响应

**状态码**: `200 OK`

**响应体**:
```json
[
  {
    "name": "resnet50-model",
    "type": "model",
    "num_versions": 3,
    "latest_version": 3,
    "size_bytes": 102400000,
    "created_at": 1704067200.0,
    "updated_at": 1704153600.0,
    "aliases": {
      "latest": 3,
      "production": 2
    }
  },
  {
    "name": "cifar10-dataset",
    "type": "dataset",
    "num_versions": 2,
    "latest_version": 2,
    "size_bytes": 524288000,
    "created_at": 1704024000.0,
    "updated_at": 1704110400.0,
    "aliases": {
      "latest": 2
    }
  }
]
```

### 响应字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `name` | string | Artifact 名称（在类型内唯一）|
| `type` | string | Artifact 类型 |
| `num_versions` | number | 总版本数 |
| `latest_version` | number | 最新版本号 |
| `size_bytes` | number | 最新版本的总大小（字节）|
| `created_at` | number | 第一个版本创建时间戳 |
| `updated_at` | number | 最后一个版本创建时间戳 |
| `aliases` | object | 别名 → 版本号映射 |

### 示例

**cURL**:
```bash
# 列出所有 artifacts
curl http://127.0.0.1:23300/api/artifacts

# 只列出模型
curl http://127.0.0.1:23300/api/artifacts?type=model
```

**Python**:
```python
import requests

# 获取所有模型
response = requests.get(
    'http://127.0.0.1:23300/api/artifacts',
    params={'type': 'model'}
)

artifacts = response.json()

for artifact in artifacts:
    size_mb = artifact['size_bytes'] / (1024 * 1024)
    print(f"{artifact['name']} v{artifact['latest_version']}: {size_mb:.2f} MB")
```

---

## 列出 Artifact 版本

获取特定 artifact 的版本历史。

### 请求

```http
GET /api/artifacts/{name}/versions?type={type}
```

**路径参数**:
| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `name` | string | 是 | Artifact 名称 |

**查询参数**:
| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `type` | string | 否 | Artifact 类型提示（提高性能）|

### 响应

**状态码**: `200 OK`

**响应体**:
```json
[
  {
    "version": 1,
    "created_at": 1704067200.0,
    "created_by_run": "20250114_120000_abc123",
    "size_bytes": 102400000,
    "num_files": 1,
    "status": "ready",
    "aliases": []
  },
  {
    "version": 2,
    "created_at": 1704110400.0,
    "created_by_run": "20250114_150000_def456",
    "size_bytes": 102400000,
    "num_files": 1,
    "status": "ready",
    "aliases": ["production"]
  },
  {
    "version": 3,
    "created_at": 1704153600.0,
    "created_by_run": "20250114_180000_ghi789",
    "size_bytes": 102400000,
    "num_files": 1,
    "status": "ready",
    "aliases": ["latest"]
  }
]
```

### 示例

**Python**:
```python
import requests

response = requests.get(
    'http://127.0.0.1:23300/api/artifacts/resnet50-model/versions',
    params={'type': 'model'}
)

versions = response.json()

for v in versions:
    aliases_str = ', '.join(v['aliases']) if v['aliases'] else 'none'
    print(f"v{v['version']}: {aliases_str}")
    print(f"  创建时间: {v['created_at']}")
    print(f"  大小: {v['size_bytes'] / 1024 / 1024:.2f} MB")
    print(f"  运行: {v['created_by_run']}")
```

---

## 获取 Artifact 详情

获取特定 artifact 版本的详细元数据。

### 请求

```http
GET /api/artifacts/{name}/v{version}?type={type}
```

**路径参数**:
| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `name` | string | 是 | Artifact 名称 |
| `version` | number | 是 | 版本号 |

**查询参数**:
| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `type` | string | 否 | Artifact 类型提示 |

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "name": "resnet50-model",
  "type": "model",
  "version": 3,
  "created_at": 1704153600.0,
  "updated_at": 1704153600.0,
  "created_by_run": "20250114_180000_ghi789",
  "created_by_user": null,
  "size_bytes": 102400000,
  "num_files": 1,
  "num_references": 0,
  "status": "ready",
  "metadata": {
    "architecture": "ResNet50",
    "num_parameters": 25000000,
    "val_accuracy": 0.9542,
    "optimizer": "AdamW",
    "learning_rate": 0.001
  },
  "description": "ResNet50 trained on ImageNet",
  "tags": ["baseline", "v3"],
  "aliases": ["latest"],
  "manifest_digest": "sha256:abc123..."
}
```

### 响应字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `name` | string | Artifact 名称 |
| `type` | string | Artifact 类型 |
| `version` | number | 版本号 |
| `created_at` | number | 创建时间戳 |
| `created_by_run` | string | 创建此版本的运行 ID |
| `size_bytes` | number | 总大小（字节）|
| `num_files` | number | 文件数量 |
| `num_references` | number | 外部引用数量 |
| `status` | string | `ready`、`deleted`、`corrupted` |
| `metadata` | object | 用户定义的元数据 |
| `description` | string | 文本描述 |
| `tags` | array[string] | 用于分类的标签 |
| `aliases` | array[string] | 版本别名 |
| `manifest_digest` | string | 清单的 SHA256 哈希 |

---

## 列出 Artifact 文件

获取 artifact 版本的文件列表。

### 请求

```http
GET /api/artifacts/{name}/v{version}/files?type={type}
```

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "artifact": "resnet50-model:v3",
  "files": [
    {
      "path": "model.pth",
      "size": 102400000,
      "digest": "sha256:abc123...",
      "modified_at": 1704153600.0,
      "absolute_path": "E:\\RunicornData\\artifacts\\model\\resnet50-model\\v3\\files\\model.pth",
      "is_remote": false
    }
  ],
  "references": [],
  "total_size": 102400000,
  "total_files": 1,
  "total_references": 0,
  "is_remote": false
}
```

### 响应字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `path` | string | artifact 内的相对路径 |
| `size` | number | 文件大小（字节）|
| `digest` | string | 内容哈希（格式：`sha256:...`）|
| `modified_at` | number | 文件修改时间戳 |
| `absolute_path` | string\|null | 绝对路径（远程存储为 null）|
| `is_remote` | boolean | 文件是否在远程服务器上 |

---

## 获取 Artifact 血缘

检索显示依赖关系的血缘图。

### 请求

```http
GET /api/artifacts/{name}/v{version}/lineage?type={type}&max_depth={depth}
```

**路径参数**:
| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `name` | string | 是 | Artifact 名称 |
| `version` | number | 是 | 版本号 |

**查询参数**:
| 参数 | 类型 | 必需 | 默认值 | 描述 |
|------|------|------|---------|------|
| `type` | string | 否 | - | Artifact 类型提示 |
| `max_depth` | number | 否 | 3 | 最大遍历深度 |

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "root_artifact": "resnet50-model:v3",
  "nodes": [
    {
      "node_type": "artifact",
      "node_id": "resnet50-model:v3",
      "label": "resnet50-model v3",
      "metadata": {
        "type": "model",
        "size": 102400000
      }
    },
    {
      "node_type": "run",
      "node_id": "20250114_180000_ghi789",
      "label": "Training Run",
      "metadata": {
        "project": "image_classification",
        "name": "resnet_baseline"
      }
    },
    {
      "node_type": "artifact",
      "node_id": "cifar10-dataset:v1",
      "label": "cifar10-dataset v1",
      "metadata": {
        "type": "dataset",
        "size": 524288000
      }
    }
  ],
  "edges": [
    {
      "source": "cifar10-dataset:v1",
      "target": "20250114_180000_ghi789",
      "edge_type": "uses"
    },
    {
      "source": "20250114_180000_ghi789",
      "target": "resnet50-model:v3",
      "edge_type": "produces"
    }
  ]
}
```

### 血缘图结构

**节点类型**:
- `artifact`: Artifact 版本（模型、数据集）
- `run`: 实验运行

**边类型**:
- `uses`: 运行使用 artifact 作为输入
- `produces`: 运行产生 artifact 作为输出

### 示例

**Python** (使用 NetworkX 可视化):
```python
import requests
import networkx as nx
import matplotlib.pyplot as plt

# 获取血缘
response = requests.get(
    'http://127.0.0.1:23300/api/artifacts/resnet50-model/v3/lineage',
    params={'type': 'model', 'max_depth': 3}
)

data = response.json()

# 构建图
G = nx.DiGraph()

for node in data['nodes']:
    G.add_node(node['node_id'], **node)

for edge in data['edges']:
    G.add_edge(edge['source'], edge['target'], type=edge['edge_type'])

# 可视化
nx.draw(G, with_labels=True, node_color='lightblue', node_size=3000)
plt.show()
```

---

## 获取存储统计

获取 artifact 存储统计信息，包括去重指标。

### 请求

```http
GET /api/artifacts/stats
```

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "total_artifacts": 25,
  "total_versions": 87,
  "total_size_bytes": 5368709120,
  "total_files": 143,
  "dedup_enabled": true,
  "dedup_pool_size_bytes": 536870912,
  "space_saved_bytes": 4831838208,
  "dedup_ratio": 0.9,
  "by_type": {
    "model": {
      "count": 15,
      "versions": 52,
      "size_bytes": 4294967296
    },
    "dataset": {
      "count": 8,
      "versions": 28,
      "size_bytes": 1073741824
    },
    "config": {
      "count": 2,
      "versions": 7,
      "size_bytes": 1048576
    }
  }
}
```

### 响应字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `total_artifacts` | number | 唯一 artifacts 总数 |
| `total_versions` | number | 所有 artifacts 的总版本数 |
| `total_size_bytes` | number | 总逻辑大小（不含去重）|
| `dedup_enabled` | boolean | 是否启用去重 |
| `dedup_pool_size_bytes` | number | 实际物理大小（含去重）|
| `space_saved_bytes` | number | 去重节省的空间 |
| `dedup_ratio` | number | 去重率（0-1，越高越好）|
| `by_type` | object | 按 artifact 类型的统计 |

### 示例

**Python**:
```python
import requests

response = requests.get('http://127.0.0.1:23300/api/artifacts/stats')
stats = response.json()

total_gb = stats['total_size_bytes'] / (1024**3)
saved_gb = stats['space_saved_bytes'] / (1024**3)
ratio = stats['dedup_ratio'] * 100

print(f"Total artifacts: {stats['total_artifacts']}")
print(f"总大小: {total_gb:.2f} GB")
print(f"节省空间: {saved_gb:.2f} GB ({ratio:.1f}%)")

# 按类型
for atype, data in stats['by_type'].items():
    print(f"\n{atype.capitalize()}:")
    print(f"  数量: {data['count']}")
    print(f"  版本: {data['versions']}")
    print(f"  大小: {data['size_bytes'] / (1024**3):.2f} GB")
```

---

## 删除 Artifact 版本

删除特定的 artifact 版本。

### 请求

```http
DELETE /api/artifacts/{name}/v{version}?type={type}&permanent={permanent}
```

**路径参数**:
| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `name` | string | 是 | Artifact 名称 |
| `version` | number | 是 | 要删除的版本号 |

**查询参数**:
| 参数 | 类型 | 必需 | 默认值 | 描述 |
|------|------|------|---------|------|
| `type` | string | 否 | - | Artifact 类型提示 |
| `permanent` | boolean | 否 | false | 如为 true 则永久删除；为 false 则软删除 |

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "success": true,
  "message": "Soft deleted resnet50-model:v2 locally"
}
```

### 错误响应

**404 未找到**:
```json
{
  "detail": "Artifact not found: resnet50-model"
}
```

**404 未找到**（版本）:
```json
{
  "detail": "Version not found: resnet50-model:v999"
}
```

### 示例

**Python** (软删除):
```python
import requests

# 软删除版本 2
response = requests.delete(
    'http://127.0.0.1:23300/api/artifacts/resnet50-model/v2',
    params={'type': 'model', 'permanent': False}
)

result = response.json()
print(result['message'])  # "Soft deleted resnet50-model:v2 locally"
```

**Python** (永久删除并确认):
```python
import requests

artifact_name = "old-model"
version = 1

confirm = input(f"永久删除 {artifact_name}:v{version}? (yes/no): ")

if confirm.lower() == 'yes':
    response = requests.delete(
        f'http://127.0.0.1:23300/api/artifacts/{artifact_name}/v{version}',
        params={'type': 'model', 'permanent': True}
    )
    
    if response.status_code == 200:
        print("✓ 已永久删除")
    else:
        print(f"✗ 错误: {response.json()['detail']}")
else:
    print("已取消")
```

---

## 使用 Artifacts

### 完整工作流示例

**Python SDK** (创建 artifacts):
```python
import runicorn as rn
import torch

# 步骤 1: 训练模型
run = rn.init(project="image_classification", name="resnet_training")

# ... 训练代码 ...
torch.save(model.state_dict(), "model.pth")

# 步骤 2: 创建 artifact
artifact = rn.Artifact("resnet50-model", type="model")
artifact.add_file("model.pth")
artifact.add_metadata({
    "architecture": "ResNet50",
    "val_accuracy": 0.9542,
    "epochs": 100,
    "optimizer": "AdamW"
})
artifact.add_tags("baseline", "production-ready")

# 步骤 3: 保存并进行版本控制
version = run.log_artifact(artifact)
print(f"保存为 v{version}")

rn.finish()
```

**API 客户端** (查询 artifacts):
```python
import requests

BASE_URL = "http://127.0.0.1:23300/api"

# 列出所有模型
models = requests.get(f"{BASE_URL}/artifacts", params={"type": "model"}).json()

# 获取最新模型
model = models[0]  # 按 updated_at 降序排序
print(f"最新: {model['name']} v{model['latest_version']}")

# 获取版本详情
detail = requests.get(
    f"{BASE_URL}/artifacts/{model['name']}/v{model['latest_version']}",
    params={"type": "model"}
).json()

print(f"准确率: {detail['metadata']['val_accuracy']}")
print(f"创建者: {detail['created_by_run']}")

# 获取血缘
lineage = requests.get(
    f"{BASE_URL}/artifacts/{model['name']}/v{model['latest_version']}/lineage",
    params={"type": "model", "max_depth": 3}
).json()

print(f"依赖: {len(lineage['nodes'])} 个节点, {len(lineage['edges'])} 条边")
```

---

## 版本别名

### 理解别名

别名提供语义化版本控制：

```
resnet50-model:v1  ← 旧版本
resnet50-model:v2  ← production ← 别名指向这里
resnet50-model:v3  ← latest ← 别名指向这里
```

### 使用别名（Python SDK）

```python
import runicorn as rn

run = rn.init(project="inference")

# 使用别名加载（推荐）
artifact = run.use_artifact("resnet50-model:latest")

# 使用版本号加载（指定）
artifact = run.use_artifact("resnet50-model:v2")

# 下载文件
model_path = artifact.download()
print(f"模型已下载到: {model_path}")

rn.finish()
```

### 管理别名（API）

> 🔔 **注意**: 别名管理目前通过 UI 或 CLI 完成。计划在未来版本中提供别名管理的 API 端点。

**CLI 示例**:
```bash
# CLI 支持即将推出
runicorn artifacts alias set resnet50-model v2 production
```

---

## 去重

### 工作原理

Artifacts 使用**基于内容的去重**：

1. **哈希计算**: 为每个文件计算 SHA256 哈希
2. **去重池**: 文件按哈希存储在 `.dedup/` 目录中
3. **硬链接**: 多个版本链接到同一物理文件
4. **空间节省**: 典型情况下减少 50-90% 存储

### 去重示例

```
场景: 100 个模型检查点，相同架构，不同权重

不去重:
100 个文件 × 每个 1 GB = 100 GB

去重:
- 共享层（模型的 80%）: 800 MB × 1 = 800 MB
- 独特权重（模型的 20%）: 200 MB × 100 = 20 GB
总计: ~21 GB（节省 79%）
```

### 检查去重效果

```python
import requests

stats = requests.get('http://127.0.0.1:23300/api/artifacts/stats').json()

if stats['dedup_enabled']:
    total_gb = stats['total_size_bytes'] / (1024**3)
    actual_gb = stats['dedup_pool_size_bytes'] / (1024**3)
    saved_gb = stats['space_saved_bytes'] / (1024**3)
    ratio = stats['dedup_ratio'] * 100
    
    print(f"逻辑大小: {total_gb:.2f} GB")
    print(f"物理大小: {actual_gb:.2f} GB")
    print(f"节省空间: {saved_gb:.2f} GB ({ratio:.1f}%)")
else:
    print("去重已禁用")
```

---

## 数据模型

### Artifact

```typescript
interface Artifact {
  name: string
  type: "model" | "dataset" | "config" | "code" | "custom"
  num_versions: number
  latest_version: number
  size_bytes: number
  created_at: number
  updated_at: number
  aliases: Record<string, number>  // 别名 → 版本
}
```

### ArtifactVersion

```typescript
interface ArtifactVersion {
  version: number
  created_at: number
  created_by_run: string
  size_bytes: number
  num_files: number
  status: "ready" | "deleted" | "corrupted"
  aliases: string[]
}
```

### ArtifactMetadata

```typescript
interface ArtifactMetadata {
  name: string
  type: string
  version: number
  created_at: number
  updated_at: number
  created_by_run: string
  created_by_user: string | null
  size_bytes: number
  num_files: number
  num_references: number
  status: string
  metadata: Record<string, any>  // 用户定义
  description: string
  tags: string[]
  aliases: string[]
  manifest_digest: string
}
```

---

## 最佳实践

### Artifact 命名

```python
# ✅ 好的命名
"resnet50-imagenet"       # 模型-数据集
"bert-base-finetuned"     # 基础模型 + 状态
"cifar10-augmented-v2"    # 数据集 + 处理
"config-baseline"         # 类型 + 用途

# ❌ 不好的命名
"model"                   # 太通用
"data123"                 # 无意义
"final_final"             # 应使用版本
```

### 元数据最佳实践

```python
# ✅ 丰富的元数据
artifact.add_metadata({
    # 架构
    "architecture": "ResNet50",
    "num_parameters": 25000000,
    
    # 训练配置
    "optimizer": "AdamW",
    "learning_rate": 0.001,
    "batch_size": 256,
    "epochs": 100,
    
    # 性能
    "train_accuracy": 0.98,
    "val_accuracy": 0.95,
    "test_accuracy": 0.94,
    
    # 数据
    "dataset": "ImageNet",
    "dataset_size": 1281167,
    
    # 其他
    "training_time_hours": 72,
    "hardware": "8x V100"
})

# ❌ 稀疏的元数据
artifact.add_metadata({"acc": 0.95})  # 信息不足
```

---

## 相关 API

- **Runs API**: 管理实验运行 - [runs_api.md](./runs_api.md)
- **V2 API**: 高性能查询 - [v2_api.md](./v2_api.md)
- **Python SDK**: 查看主 [README.md](../../README.md)

---

**最后更新**: 2025-10-14


