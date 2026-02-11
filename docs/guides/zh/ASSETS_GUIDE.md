[English](../en/ASSETS_GUIDE.md) | [简体中文](ASSETS_GUIDE.md)

---

# 资产系统指南

> **版本**: v0.6.0  
> **功能**: SHA256 内容寻址存储、工作区快照、去重

---

## 📋 概述

Runicorn v0.6.0 引入了新的**资产系统**，为实验文件提供高效的去重存储。该系统用现代的内容寻址存储（CAS）架构替代了旧的 artifacts 模块。

### 核心特性

- **SHA256 内容寻址存储**: 文件按内容哈希存储，实现自动去重
- **工作区快照**: 在实验时捕获整个代码库
- **Blob 存储**: 对相似文件节省 50-90% 的存储空间
- **基于清单的恢复**: 从清单重建任何快照
- **孤立清理**: 自动清理未引用的 blob

### 去重原理

```
传统存储:
  run_001/code.zip  →  100 MB
  run_002/code.zip  →  100 MB  (99% 相同)
  run_003/code.zip  →  100 MB  (99% 相同)
  总计: 300 MB

内容寻址存储:
  blobs/a4/a47eb79...  →  100 MB  (共享内容)
  blobs/3f/3f8c2a1...  →  1 MB    (独特变更)
  manifests/run_001.json  →  指向 blobs
  manifests/run_002.json  →  指向 blobs
  manifests/run_003.json  →  指向 blobs
  总计: ~101 MB (节省 66%)
```

---

## 🚀 快速入门

### 创建工作区快照

在实验时捕获代码：

```python
import runicorn as rn
from runicorn import snapshot_workspace
from pathlib import Path

# 初始化运行
run = rn.init(path="training/resnet")

# 快照当前工作区
result = snapshot_workspace(
    root=Path("."),
    out_zip=run.run_dir / "code_snapshot.zip",
)

print(f"捕获了 {result['file_count']} 个文件 ({result['total_bytes']} 字节)")

# 继续训练...
run.log({"loss": 0.5})
run.finish()
```

### 使用 Blob 存储

存储文件并自动去重：

```python
from runicorn.assets.blob_store import store_blob, get_blob_path, get_blob_stats
from pathlib import Path

# 定义 blob 存储根目录
blob_root = Path("~/.runicorn/archive/blobs").expanduser()

# 存储文件（返回 SHA256 哈希）
sha256 = store_blob(Path("model.pth"), blob_root)
print(f"存储哈希: {sha256}")

# 再次存储相同文件 - 不会创建副本
sha256_again = store_blob(Path("model.pth"), blob_root)
assert sha256 == sha256_again  # 相同哈希，无新存储

# 获取 blob 路径用于检索
blob_path = get_blob_path(sha256, blob_root)
print(f"Blob 存储于: {blob_path}")

# 检查存储统计
stats = get_blob_stats(blob_root)
print(f"总 blob 数: {stats['blob_count']}")
print(f"总大小: {stats['total_size_bytes']} 字节")
```

---

## 📚 功能详解

### 工作区快照

`snapshot_workspace()` 函数创建项目的压缩归档，遵循 `.rnignore` 模式。

#### 参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `root` | `Path` | 必需 | 工作区根目录 |
| `out_zip` | `Path` | 必需 | 输出 zip 文件路径 |
| `ignore_file` | `str` | `".rnignore"` | 忽略文件名 |
| `extra_excludes` | `List[str]` | `None` | 额外排除模式 |
| `max_total_bytes` | `int` | `500MB` | 最大快照大小 |
| `max_files` | `int` | `200,000` | 最大文件数 |
| `force_snapshot` | `bool` | `False` | 绕过大小限制 |

#### 返回值

```python
{
    "workspace_root": "/path/to/workspace",
    "archive_path": "/path/to/snapshot.zip",
    "format": "zip",
    "file_count": 150,
    "total_bytes": 1048576,
}
```

### .rnignore 支持

在项目根目录创建 `.rnignore` 文件以排除快照中的文件：

```gitignore
# .rnignore - 类似 .gitignore 语法

# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/

# 虚拟环境
venv/
.venv/
env/

# 数据和模型（通常太大）
data/
datasets/
*.pth
*.ckpt
*.h5

# IDE
.idea/
.vscode/
*.swp

# 构建产物
dist/
build/
*.egg-info/

# 日志和输出
logs/
outputs/
*.log
```

如果不存在 `.rnignore`，Runicorn 会创建一个包含常见排除项的默认文件。

### 指纹计算

文件通过 SHA256 哈希标识：

```python
from runicorn.assets.fingerprint import sha256_file
from pathlib import Path

# 计算文件指纹
fingerprint = sha256_file(Path("model.pth"))
print(f"SHA256: {fingerprint}")
# 输出: SHA256: a47eb79188cdc67a601ebf32...
```

### Blob 存储

Blob 存储提供内容寻址存储：

```python
from runicorn.assets.blob_store import (
    store_blob,
    get_blob_path,
    blob_exists,
    read_blob,
    get_blob_stats,
)
```

#### 存储结构

```
archive/
├── blobs/
│   ├── a4/
│   │   └── a47eb79188cdc67a601ebf32...  # 文件内容
│   ├── 3f/
│   │   └── 3f8c2a1b9e4d7f...
│   └── ...
└── manifests/
    ├── run_001.json  # 指向 blobs
    └── run_002.json
```

### 基于清单的恢复

从清单恢复文件：

```python
from runicorn.assets.restore import (
    load_manifest,
    restore_from_manifest,
    export_manifest_to_zip,
    get_file_from_manifest,
)
from pathlib import Path

# 加载清单
manifest = load_manifest(Path("archive/manifests/run_001.json"))
print(f"清单中的文件: {len(manifest['files'])}")

# 恢复到目录
result = restore_from_manifest(
    manifest_path=Path("archive/manifests/run_001.json"),
    blob_root=Path("archive/blobs"),
    target_dir=Path("restored_code"),
    overwrite=False,
)
print(f"恢复了 {result['restored_count']} 个文件")

# 导出为 zip
result = export_manifest_to_zip(
    manifest_path=Path("archive/manifests/run_001.json"),
    blob_root=Path("archive/blobs"),
    zip_path=Path("export.zip"),
)
print(f"导出了 {result['exported_count']} 个文件到 {result['zip_path']}")

# 获取单个文件
blob_path = get_file_from_manifest(
    manifest_path=Path("archive/manifests/run_001.json"),
    blob_root=Path("archive/blobs"),
    rel_path="train.py",
)
print(f"train.py 存储于: {blob_path}")
```

---

## 📖 API 参考

### snapshot_workspace()

```python
from runicorn import snapshot_workspace

result = snapshot_workspace(
    root: Path,
    out_zip: Path,
    *,
    ignore_file: str = ".rnignore",
    extra_excludes: Optional[List[str]] = None,
    max_total_bytes: int = 500 * 1024 * 1024,
    max_files: int = 200_000,
    force_snapshot: bool = False,
) -> Dict[str, Any]
```

### store_blob()

```python
from runicorn.assets.blob_store import store_blob

sha256 = store_blob(
    src_path: Path,
    blob_root: Path,
) -> str
```

将文件存储到 blob 存储。返回 SHA256 哈希。如果文件已存在（相同哈希），不会创建副本。

### get_blob_path()

```python
from runicorn.assets.blob_store import get_blob_path

path = get_blob_path(
    sha256: str,
    blob_root: Path,
) -> Path
```

根据哈希返回 blob 的存储路径。

### restore_from_manifest()

```python
from runicorn.assets.restore import restore_from_manifest

result = restore_from_manifest(
    manifest_path: Path,
    blob_root: Path,
    target_dir: Path,
    *,
    overwrite: bool = False,
) -> Dict[str, Any]
```

从清单恢复文件到目标目录。

### export_manifest_to_zip()

```python
from runicorn.assets.restore import export_manifest_to_zip

result = export_manifest_to_zip(
    manifest_path: Path,
    blob_root: Path,
    zip_path: Path,
) -> Dict[str, Any]
```

将基于清单的归档导出为 zip 文件。

---

## 🧹 清理

### delete_run_completely()

永久删除运行及其所有孤立资产：

```python
from runicorn.assets.cleanup import delete_run_completely
from pathlib import Path

# 预览将被删除的内容（干运行）
result = delete_run_completely(
    run_id="20250115_103015_abc123",
    storage_root=Path("~/.runicorn").expanduser(),
    dry_run=True,
)
print(f"将删除 {result['blobs_deleted']} 个 blob")
print(f"将释放 {result['bytes_freed']} 字节")

# 实际删除
result = delete_run_completely(
    run_id="20250115_103015_abc123",
    storage_root=Path("~/.runicorn").expanduser(),
    dry_run=False,
)
print(f"删除了 {result['blobs_deleted']} 个 blob")
print(f"释放了 {result['bytes_freed']} 字节")
```

#### 返回值

```python
{
    "success": True,
    "run_id": "20250115_103015_abc123",
    "run_dir_deleted": True,
    "orphaned_assets": [...],  # 仅被此运行使用的资产
    "kept_assets": [...],      # 与其他运行共享的资产
    "blobs_deleted": 15,
    "manifests_deleted": 2,
    "outputs_deleted": 5,
    "bytes_freed": 104857600,
    "errors": [],
}
```

### cleanup_orphaned_blobs()

扫描并删除未被任何清单引用的孤立 blob：

```python
from runicorn.assets.cleanup import cleanup_orphaned_blobs
from pathlib import Path

# 预览孤立 blob
result = cleanup_orphaned_blobs(
    storage_root=Path("~/.runicorn").expanduser(),
    dry_run=True,
)
print(f"发现 {result['orphaned_blobs']} 个孤立 blob")
print(f"将释放 {result['bytes_freed']} 字节")

# 清理
result = cleanup_orphaned_blobs(
    storage_root=Path("~/.runicorn").expanduser(),
    dry_run=False,
)
print(f"清理了 {result['orphaned_blobs']} 个孤立 blob")
```

---

## 🔄 从 v0.5.x 迁移

### 变更内容

| v0.5.x (Artifacts) | v0.6.0 (Assets) |
|-------------------|-----------------|
| `rn.Artifact()` 类 | `snapshot_workspace()` 函数 |
| `run.log_artifact()` | 使用 `snapshot_workspace()` 自动完成 |
| `run.use_artifact()` | `restore_from_manifest()` |
| 基于版本的存储 | 内容寻址存储 |
| 手动去重 | 自动 SHA256 去重 |

### 迁移步骤

1. **更新导入**：
   ```python
   # 旧
   from runicorn import Artifact
   
   # 新
   from runicorn import snapshot_workspace
   from runicorn.assets.restore import restore_from_manifest
   ```

2. **更新快照代码**：
   ```python
   # 旧
   artifact = rn.Artifact("code", type="code")
   artifact.add_dir(".")
   run.log_artifact(artifact)
   
   # 新
   from runicorn import snapshot_workspace
   snapshot_workspace(
       root=Path("."),
       out_zip=run.run_dir / "code_snapshot.zip",
   )
   ```

3. **更新恢复代码**：
   ```python
   # 旧
   artifact = run.use_artifact("code:v1")
   path = artifact.download()
   
   # 新
   from runicorn.assets.restore import restore_from_manifest
   result = restore_from_manifest(
       manifest_path=Path("archive/manifests/run_001.json"),
       blob_root=Path("archive/blobs"),
       target_dir=Path("restored"),
   )
   ```

### 现有数据

`artifacts/` 目录中的现有 v0.5.x artifacts 仍然可访问。新的资产系统使用单独的 `archive/` 目录结构。

---

## 💡 最佳实践

### 1. 尽早配置 .rnignore

在第一次实验之前创建 `.rnignore`，避免捕获不必要的文件：

```gitignore
# 必要排除项
__pycache__/
*.pyc
venv/
.git/
data/
*.pth
*.ckpt
```

### 2. 使用快照确保可复现性

在开始重要实验时始终快照代码：

```python
run = rn.init(path="important_experiment")

# 在 init 后立即快照
snapshot_workspace(
    root=Path("."),
    out_zip=run.run_dir / "code.zip",
)

# 然后训练...
```

### 3. 监控存储使用

定期检查 blob 存储统计：

```python
from runicorn.assets.blob_store import get_blob_stats
from pathlib import Path

stats = get_blob_stats(Path("~/.runicorn/archive/blobs").expanduser())
print(f"Blob 数: {stats['blob_count']}")
print(f"大小: {stats['total_size_bytes'] / 1024 / 1024:.1f} MB")
```

### 4. 清理旧运行

删除旧运行以释放空间：

```python
from runicorn.assets.cleanup import delete_run_completely

# 删除旧运行（共享 blob 会保留）
for run_id in old_run_ids:
    delete_run_completely(run_id, storage_root)
```

---

## 🔧 故障排除

### 问题：快照太大

**原因**: 包含了大型数据文件或模型

**解决方案**: 更新 `.rnignore`：
```gitignore
# 添加到 .rnignore
data/
datasets/
*.pth
*.ckpt
*.h5
checkpoints/
```

或使用 `extra_excludes`：
```python
snapshot_workspace(
    root=Path("."),
    out_zip=out_path,
    extra_excludes=["large_folder/", "*.bin"],
)
```

### 问题：文件太多

**原因**: Node modules、虚拟环境或缓存目录

**解决方案**: 确保这些在 `.rnignore` 中：
```gitignore
node_modules/
venv/
.venv/
__pycache__/
.pytest_cache/
```

### 问题：恢复时缺少 blob

**原因**: Blob 被删除或损坏

**解决方案**: 检查结果中的缺失 blob：
```python
result = restore_from_manifest(...)
if "missing_blobs" in result:
    print(f"缺失: {result['missing_blobs']}")
```

### 问题：删除后磁盘空间未释放

**原因**: Blob 与其他运行共享

**解决方案**: 删除多个运行后使用 `cleanup_orphaned_blobs()`：
```python
# 先删除运行
for run_id in runs_to_delete:
    delete_run_completely(run_id, storage_root)

# 然后清理孤立 blob
cleanup_orphaned_blobs(storage_root)
```

---

## 📊 存储结构

```
<storage_root>/
├── archive/
│   ├── blobs/                    # 内容寻址存储
│   │   ├── a4/
│   │   │   └── a47eb79188...     # 文件内容（以 SHA256 命名）
│   │   └── 3f/
│   │       └── 3f8c2a1b9e...
│   ├── manifests/                # 文件清单
│   │   ├── run_001.json
│   │   └── run_002.json
│   └── outputs/                  # 滚动输出
│       └── rolling/
│           └── <run_id>/
└── <project>/
    └── <experiment>/
        └── runs/
            └── <run_id>/
                ├── code_snapshot.zip  # 工作区快照
                └── ...
```

---

**[返回指南](README.md)** | **[返回主页](../../README.md)**
