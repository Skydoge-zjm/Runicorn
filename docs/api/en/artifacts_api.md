[English](artifacts_api.md) | [简体中文](../zh/artifacts_api.md)

---

# Artifacts API - Model Version Control

**Module**: Artifacts API  
**Base Path**: `/api/artifacts`  
**Version**: v1.0  
**Description**: Version control for ML models, datasets, and other assets with deduplication and lineage tracking.

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/artifacts` | List all artifacts |
| GET | `/artifacts/{name}/versions` | List versions of an artifact |
| GET | `/artifacts/{name}/v{version}` | Get artifact version details |
| GET | `/artifacts/{name}/v{version}/files` | List files in artifact version |
| GET | `/artifacts/{name}/v{version}/lineage` | Get artifact lineage graph |
| GET | `/artifacts/stats` | Get storage statistics |
| DELETE | `/artifacts/{name}/v{version}` | Delete artifact version |

---

## List Artifacts

Get a list of all artifacts with optional type filter.

### Request

```http
GET /api/artifacts?type={type}
```

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | No | Filter by type: `model`, `dataset`, `config`, `code`, `custom` |

### Response

**Status Code**: `200 OK`

**Response Body**:
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

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Artifact name (unique within type) |
| `type` | string | Artifact type |
| `num_versions` | number | Total number of versions |
| `latest_version` | number | Latest version number |
| `size_bytes` | number | Total size of latest version in bytes |
| `created_at` | number | First version creation timestamp |
| `updated_at` | number | Last version creation timestamp |
| `aliases` | object | Map of alias → version number |

### Example

**cURL**:
```bash
# List all artifacts
curl http://127.0.0.1:23300/api/artifacts

# List only models
curl http://127.0.0.1:23300/api/artifacts?type=model
```

**Python**:
```python
import requests

# Get all models
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

## List Artifact Versions

Get version history for a specific artifact.

### Request

```http
GET /api/artifacts/{name}/versions?type={type}
```

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Artifact name |

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | No | Artifact type hint (improves performance) |

### Response

**Status Code**: `200 OK`

**Response Body**:
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

### Example

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
    print(f"  Created: {v['created_at']}")
    print(f"  Size: {v['size_bytes'] / 1024 / 1024:.2f} MB")
    print(f"  Run: {v['created_by_run']}")
```

---

## Get Artifact Detail

Get detailed metadata for a specific artifact version.

### Request

```http
GET /api/artifacts/{name}/v{version}?type={type}
```

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Artifact name |
| `version` | number | Yes | Version number |

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | No | Artifact type hint |

### Response

**Status Code**: `200 OK`

**Response Body**:
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

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Artifact name |
| `type` | string | Artifact type |
| `version` | number | Version number |
| `created_at` | number | Creation timestamp |
| `created_by_run` | string | Run ID that created this version |
| `size_bytes` | number | Total size in bytes |
| `num_files` | number | Number of files |
| `num_references` | number | Number of external references |
| `status` | string | `ready`, `deleted`, `corrupted` |
| `metadata` | object | User-defined metadata |
| `description` | string | Text description |
| `tags` | array[string] | Tags for categorization |
| `aliases` | array[string] | Version aliases |
| `manifest_digest` | string | SHA256 hash of manifest |

---

## List Artifact Files

Get file listing for an artifact version.

### Request

```http
GET /api/artifacts/{name}/v{version}/files?type={type}
```

### Response

**Status Code**: `200 OK`

**Response Body**:
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

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `path` | string | Relative path within artifact |
| `size` | number | File size in bytes |
| `digest` | string | Content hash (format: `sha256:...`) |
| `modified_at` | number | File modification timestamp |
| `absolute_path` | string\|null | Absolute path (null for remote storage) |
| `is_remote` | boolean | Whether file is on remote server |

---

## Get Artifact Lineage

Retrieve lineage graph showing dependencies.

### Request

```http
GET /api/artifacts/{name}/v{version}/lineage?type={type}&max_depth={depth}
```

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Artifact name |
| `version` | number | Yes | Version number |

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `type` | string | No | - | Artifact type hint |
| `max_depth` | number | No | 3 | Maximum traversal depth |

### Response

**Status Code**: `200 OK`

**Response Body**:
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

### Lineage Graph Structure

**Node Types**:
- `artifact`: Artifact versions (models, datasets)
- `run`: Experiment runs

**Edge Types**:
- `uses`: Run uses artifact as input
- `produces`: Run produces artifact as output

### Example

**Python** (visualize with NetworkX):
```python
import requests
import networkx as nx
import matplotlib.pyplot as plt

# Get lineage
response = requests.get(
    'http://127.0.0.1:23300/api/artifacts/resnet50-model/v3/lineage',
    params={'type': 'model', 'max_depth': 3}
)

data = response.json()

# Build graph
G = nx.DiGraph()

for node in data['nodes']:
    G.add_node(node['node_id'], **node)

for edge in data['edges']:
    G.add_edge(edge['source'], edge['target'], type=edge['edge_type'])

# Visualize
nx.draw(G, with_labels=True, node_color='lightblue', node_size=3000)
plt.show()
```

---

## Get Storage Statistics

Get artifact storage statistics including deduplication metrics.

### Request

```http
GET /api/artifacts/stats
```

### Response

**Status Code**: `200 OK`

**Response Body**:
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

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `total_artifacts` | number | Total number of unique artifacts |
| `total_versions` | number | Total number of versions across all artifacts |
| `total_size_bytes` | number | Total logical size (without deduplication) |
| `dedup_enabled` | boolean | Whether deduplication is enabled |
| `dedup_pool_size_bytes` | number | Actual physical size (with deduplication) |
| `space_saved_bytes` | number | Space saved by deduplication |
| `dedup_ratio` | number | Deduplication ratio (0-1, higher is better) |
| `by_type` | object | Statistics by artifact type |

### Example

**Python**:
```python
import requests

response = requests.get('http://127.0.0.1:23300/api/artifacts/stats')
stats = response.json()

total_gb = stats['total_size_bytes'] / (1024**3)
saved_gb = stats['space_saved_bytes'] / (1024**3)
ratio = stats['dedup_ratio'] * 100

print(f"Total artifacts: {stats['total_artifacts']}")
print(f"Total size: {total_gb:.2f} GB")
print(f"Space saved: {saved_gb:.2f} GB ({ratio:.1f}%)")

# By type
for atype, data in stats['by_type'].items():
    print(f"\n{atype.capitalize()}:")
    print(f"  Count: {data['count']}")
    print(f"  Versions: {data['versions']}")
    print(f"  Size: {data['size_bytes'] / (1024**3):.2f} GB")
```

---

## Delete Artifact Version

Delete a specific artifact version.

### Request

```http
DELETE /api/artifacts/{name}/v{version}?type={type}&permanent={permanent}
```

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Artifact name |
| `version` | number | Yes | Version number to delete |

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `type` | string | No | - | Artifact type hint |
| `permanent` | boolean | No | false | If true, permanently delete; if false, soft delete |

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "success": true,
  "message": "Soft deleted resnet50-model:v2 locally"
}
```

### Error Responses

**404 Not Found**:
```json
{
  "detail": "Artifact not found: resnet50-model"
}
```

**404 Not Found** (version):
```json
{
  "detail": "Version not found: resnet50-model:v999"
}
```

### Example

**Python** (soft delete):
```python
import requests

# Soft delete version 2
response = requests.delete(
    'http://127.0.0.1:23300/api/artifacts/resnet50-model/v2',
    params={'type': 'model', 'permanent': False}
)

result = response.json()
print(result['message'])  # "Soft deleted resnet50-model:v2 locally"
```

**Python** (permanent delete with confirmation):
```python
import requests

artifact_name = "old-model"
version = 1

confirm = input(f"Permanently delete {artifact_name}:v{version}? (yes/no): ")

if confirm.lower() == 'yes':
    response = requests.delete(
        f'http://127.0.0.1:23300/api/artifacts/{artifact_name}/v{version}',
        params={'type': 'model', 'permanent': True}
    )
    
    if response.status_code == 200:
        print("✓ Permanently deleted")
    else:
        print(f"✗ Error: {response.json()['detail']}")
else:
    print("Cancelled")
```

---

## Working with Artifacts

### Complete Workflow Example

**Python SDK** (creating artifacts):
```python
import runicorn as rn
import torch

# Step 1: Train model
run = rn.init(project="image_classification", name="resnet_training")

# ... training code ...
torch.save(model.state_dict(), "model.pth")

# Step 2: Create artifact
artifact = rn.Artifact("resnet50-model", type="model")
artifact.add_file("model.pth")
artifact.add_metadata({
    "architecture": "ResNet50",
    "val_accuracy": 0.9542,
    "epochs": 100,
    "optimizer": "AdamW"
})
artifact.add_tags("baseline", "production-ready")

# Step 3: Save with version control
version = run.log_artifact(artifact)
print(f"Saved as v{version}")

run.finish()
```

**API Client** (querying artifacts):
```python
import requests

BASE_URL = "http://127.0.0.1:23300/api"

# List all models
models = requests.get(f"{BASE_URL}/artifacts", params={"type": "model"}).json()

# Get latest model
model = models[0]  # Sorted by updated_at desc
print(f"Latest: {model['name']} v{model['latest_version']}")

# Get version details
detail = requests.get(
    f"{BASE_URL}/artifacts/{model['name']}/v{model['latest_version']}",
    params={"type": "model"}
).json()

print(f"Accuracy: {detail['metadata']['val_accuracy']}")
print(f"Created by: {detail['created_by_run']}")

# Get lineage
lineage = requests.get(
    f"{BASE_URL}/artifacts/{model['name']}/v{model['latest_version']}/lineage",
    params={"type": "model", "max_depth": 3}
).json()

print(f"Dependencies: {len(lineage['nodes'])} nodes, {len(lineage['edges'])} edges")
```

---

## Version Aliases

### Understanding Aliases

Aliases provide semantic versioning:

```
resnet50-model:v1  ← old version
resnet50-model:v2  ← production ← alias points here
resnet50-model:v3  ← latest ← alias points here
```

### Using Aliases (Python SDK)

```python
import runicorn as rn

run = rn.init(project="inference")

# Load using alias (recommended)
artifact = run.use_artifact("resnet50-model:latest")

# Load using version number (specific)
artifact = run.use_artifact("resnet50-model:v2")

# Download files
model_path = artifact.download()
print(f"Model downloaded to: {model_path}")

run.finish()
```

### Managing Aliases (API)

> 🔔 **Note**: Alias management is currently done through the UI or CLI. API endpoints for alias management are planned for future versions.

**CLI Example**:
```bash
# CLI support coming soon
runicorn artifacts alias set resnet50-model v2 production
```

---

## Deduplication

### How It Works

Artifacts use **content-based deduplication**:

1. **Hash Calculation**: SHA256 hash computed for each file
2. **Dedup Pool**: Files stored in `.dedup/` directory by hash
3. **Hard Links**: Multiple versions link to same physical file
4. **Space Savings**: 50-90% storage reduction typical

### Deduplication Example

```
Scenario: 100 model checkpoints, same architecture, different weights

Without dedup:
100 files × 1 GB each = 100 GB

With dedup:
- Shared layers (80% of model): 800 MB × 1 = 800 MB
- Unique weights (20% of model): 200 MB × 100 = 20 GB
Total: ~21 GB (79% savings)
```

### Checking Dedup Effectiveness

```python
import requests

stats = requests.get('http://127.0.0.1:23300/api/artifacts/stats').json()

if stats['dedup_enabled']:
    total_gb = stats['total_size_bytes'] / (1024**3)
    actual_gb = stats['dedup_pool_size_bytes'] / (1024**3)
    saved_gb = stats['space_saved_bytes'] / (1024**3)
    ratio = stats['dedup_ratio'] * 100
    
    print(f"Logical size: {total_gb:.2f} GB")
    print(f"Physical size: {actual_gb:.2f} GB")
    print(f"Space saved: {saved_gb:.2f} GB ({ratio:.1f}%)")
else:
    print("Deduplication is disabled")
```

---

## Data Models

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
  aliases: Record<string, number>  // alias → version
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
  metadata: Record<string, any>  // User-defined
  description: string
  tags: string[]
  aliases: string[]
  manifest_digest: string
}
```

---

## Best Practices

### Artifact Naming

```python
# ✅ Good names
"resnet50-imagenet"       # model-dataset
"bert-base-finetuned"     # base-model + status
"cifar10-augmented-v2"    # dataset + processing
"config-baseline"         # type + purpose

# ❌ Bad names
"model"                   # Too generic
"data123"                 # Meaningless
"final_final"             # Use versions instead
```

### Metadata Best Practices

```python
# ✅ Rich metadata
artifact.add_metadata({
    # Architecture
    "architecture": "ResNet50",
    "num_parameters": 25000000,
    
    # Training config
    "optimizer": "AdamW",
    "learning_rate": 0.001,
    "batch_size": 256,
    "epochs": 100,
    
    # Performance
    "train_accuracy": 0.98,
    "val_accuracy": 0.95,
    "test_accuracy": 0.94,
    
    # Data
    "dataset": "ImageNet",
    "dataset_size": 1281167,
    
    # Misc
    "training_time_hours": 72,
    "hardware": "8x V100"
})

# ❌ Sparse metadata
artifact.add_metadata({"acc": 0.95})  # Not informative
```

---

## Related APIs

- **Runs API**: Manage experiment runs - [runs_api.md](./runs_api.md)
- **V2 API**: High-performance queries - [v2_api.md](./v2_api.md)
- **Python SDK**: See main [README.md](../../README.md)

---

**Last Updated**: 2025-10-14

