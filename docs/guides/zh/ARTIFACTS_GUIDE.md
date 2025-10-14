[English](../en/ARTIFACTS_GUIDE.md) | [简体中文](ARTIFACTS_GUIDE.md)

---

# Runicorn Artifacts 使用指南

> **版本**: v0.3.1+  
> **功能**: 模型与数据集版本控制

---

## 📦 什么是 Artifacts？

Artifacts（工件）是 Runicorn 的版本控制系统，用于管理机器学习资产，包括：
- **模型** (models) - PyTorch、TensorFlow、ONNX等模型文件
- **数据集** (datasets) - 训练/验证/测试数据
- **配置** (configs) - 模型配置、超参数文件
- **代码** (code) - 训练脚本、自定义代码
- **自定义** (custom) - 任何其他文件

---

## 🚀 快速开始

### 1. 保存模型

```python
import runicorn as rn

# 训练模型
run = rn.init(project="image_classification", name="resnet50_v1")

# ... 训练代码 ...
# torch.save(model.state_dict(), "model.pth")

# 创建 artifact
model = rn.Artifact("resnet50-model", type="model")
model.add_file("model.pth")
model.add_metadata({
    "architecture": "ResNet50",
    "val_acc": 0.95,
    "epochs": 100
})

# 保存（自动版本控制）
version = run.log_artifact(model)  # → v1
print(f"Saved model: resnet50-model:v{version}")

rn.finish()
```

### 2. 使用模型

```python
import runicorn as rn

# 推理run
run = rn.init(project="inference")

# 加载最新版本
artifact = run.use_artifact("resnet50-model:latest")
model_path = artifact.download()

# 使用模型
# model.load_state_dict(torch.load(model_path / "model.pth"))

rn.finish()
```

---

## 📚 完整功能

### 添加文件

```python
artifact = rn.Artifact("my-model", type="model")

# 添加单个文件
artifact.add_file("model.pth")

# 添加时重命名
artifact.add_file("checkpoint.pth", name="model.pth")

# 添加整个目录
artifact.add_dir("checkpoints/")

# 添加目录并排除文件
artifact.add_dir("checkpoints/", exclude_patterns=["*.log", "*.tmp"])
```

### 添加元数据

```python
artifact = rn.Artifact("my-model", type="model")
artifact.add_file("model.pth")

# 添加元数据（任意 JSON 数据）
artifact.add_metadata({
    "architecture": "ResNet50",
    "val_acc": 0.95,
    "val_loss": 0.23,
    "epochs": 100,
    "optimizer": "Adam",
    "learning_rate": 0.001,
    "batch_size": 64,
    "notes": "Best model from hyperparameter sweep"
})

# 添加标签
artifact.add_tags("production", "resnet", "imagenet")

run.log_artifact(artifact)
```

### 外部引用（大数据集）

```python
# 对于超大数据集，不实际复制，只记录引用
dataset = rn.Artifact("imagenet-full", type="dataset")
dataset.add_reference(
    uri="s3://my-bucket/imagenet-full",
    checksum="sha256:abc123...",
    size=150_000_000_000  # 150 GB
)
dataset.add_metadata({
    "num_samples": 1_281_167,
    "num_classes": 1000
})

run.log_artifact(dataset)
```

---

## 🔍 查询和使用

### 使用特定版本

```python
# 使用最新版本
artifact = run.use_artifact("my-model:latest")

# 使用特定版本号
artifact = run.use_artifact("my-model:v3")

# 使用别名（如果设置了）
artifact = run.use_artifact("my-model:production")
```

### 下载文件

```python
# 下载到临时目录
artifact = run.use_artifact("my-model:latest")
model_dir = artifact.download()  # 返回临时目录路径
model_file = model_dir / "model.pth"

# 下载到指定目录
model_dir = artifact.download(target_dir="./models")
```

### 获取元数据

```python
artifact = run.use_artifact("my-model:latest")

# 获取元数据对象
metadata = artifact.get_metadata()
print(f"Accuracy: {metadata.metadata['val_acc']}")
print(f"Created: {metadata.created_at}")
print(f"Size: {metadata.size_bytes} bytes")

# 获取文件清单
manifest = artifact.get_manifest()
print(f"Files: {manifest.total_files}")
for file in manifest.files:
    print(f"  {file.path} ({file.size} bytes)")
```

---

## 🔗 血缘追踪

Runicorn 自动追踪 artifact 之间的依赖关系：

```python
# Run 1: 准备数据集
run1 = rn.init(project="training", name="data_prep")
dataset = rn.Artifact("my-dataset", type="dataset")
dataset.add_dir("data/")
run1.log_artifact(dataset)  # → my-dataset:v1
rn.finish()

# Run 2: 使用数据集训练模型
run2 = rn.init(project="training", name="model_train")
dataset = run2.use_artifact("my-dataset:v1")  # 自动记录使用
# 训练...
model = rn.Artifact("my-model", type="model")
model.add_file("model.pth")
run2.log_artifact(model)  # → my-model:v1
rn.finish()

# 系统自动记录血缘关系：
# my-dataset:v1 → run2 → my-model:v1
```

在 Web UI 中可以看到完整的血缘关系图。

---

## 🖥️ Web UI 功能

### Artifacts 页面

访问 `http://127.0.0.1:23300/artifacts` 可以：

1. **浏览所有 artifacts**
   - 按类型筛选（模型、数据集等）
   - 搜索 artifact 名称
   - 查看统计信息

2. **查看版本历史**
   - 所有版本列表
   - 版本对比
   - 创建时间和创建者

3. **文件管理**
   - 查看包含的文件
   - 文件大小和哈希值
   - 外部引用

4. **血缘关系可视化**
   - 图形化显示依赖关系
   - 上游依赖（输入）
   - 下游使用（输出）

---

## 💻 CLI 命令

### 列出所有 artifacts

```bash
$ runicorn artifacts --action list
Found 5 artifact(s):

Name                           Type       Versions   Size            Latest    
-------------------------------------------------------------------------------------
resnet50-model                 model      3          98.23 MB   v3
bert-base-finetuned            model      2          420.15 MB  v2
imagenet-subset                dataset    1          5120.00 MB v1
```

### 查看版本历史

```bash
$ runicorn artifacts --action versions --name resnet50-model
Versions for resnet50-model:

Version    Created                   Size            Files    Run
------------------------------------------------------------------------------------------
v1         2025-09-01 10:30:15       97.50 MB   1        20250901_103015_abc123
v2         2025-09-15 14:22:33       98.00 MB   1        20250915_142233_def456
v3         2025-09-30 16:45:12       98.23 MB   1        20250930_164512_ghi789
```

### 查看详细信息

```bash
$ runicorn artifacts --action info --name resnet50-model --version 3
Artifact: resnet50-model:v3
============================================================
Type:         model
Status:       ready
Created:      2025-09-30 16:45:12
Created by:   20250930_164512_ghi789
Size:         98.23 MB
Files:        1
Aliases:      latest, production

Metadata:
  architecture: ResNet50
  val_acc: 0.95
  epochs: 100
  optimizer: AdamW

Files (1):
  model.pth (98.2 MB)
```

### 查看存储统计

```bash
$ runicorn artifacts --action stats
Artifact Storage Statistics
============================================================
Total Artifacts:  5
Total Versions:   12
Total Size:       6.8 GB
Dedup Enabled:    True

Deduplication Stats:
  Pool Size:      5.2 GB
  Space Saved:    1.6 GB
  Dedup Ratio:    23.5%

By Type:
  Model      3 artifacts, 8 versions, 1.2 GB
  Dataset    2 artifacts, 4 versions, 5.6 GB
```

### 删除版本

```bash
# 软删除（可恢复）
$ runicorn artifacts --action delete --name old-model --version 1
Delete old-model:v1? [y/N] y
✅ Soft deleted old-model:v1

# 永久删除
$ runicorn artifacts --action delete --name old-model --version 1 --permanent
```

---

## 🎯 最佳实践

### 1. 命名规范

```python
# 好的命名
rn.Artifact("resnet50-imagenet", type="model")
rn.Artifact("mnist-augmented", type="dataset")
rn.Artifact("training-config", type="config")

# 避免
rn.Artifact("model", type="model")  # 太泛化
rn.Artifact("final_final_v2", type="model")  # 混乱
```

### 2. 元数据规范

```python
# 模型的典型元数据
model.add_metadata({
    "architecture": "ResNet50",
    "val_acc": 0.95,
    "val_loss": 0.23,
    "epochs": 100,
    "optimizer": "Adam",
    "learning_rate": 0.001,
    "batch_size": 64,
    "dataset": "imagenet-subset:v2",  # 关联数据集
    "framework": "pytorch",
    "framework_version": "2.0.0"
})

# 数据集的典型元数据
dataset.add_metadata({
    "num_samples": 50000,
    "num_classes": 10,
    "split_ratio": "0.8/0.2",
    "preprocessing": "normalize + augmentation",
    "augmentation": "flip + crop + color_jitter"
})
```

### 3. 版本管理策略

```python
# 开发阶段：频繁保存
run = rn.init(project="dev", name="experiment_123")
model = rn.Artifact("dev-model", type="model")
model.add_file("checkpoint.pth")
run.log_artifact(model)  # v1, v2, v3, ...

# 生产阶段：使用别名
# TODO: 别名功能待实现
# artifact.alias("production")  # 标记生产版本
```

### 4. 大文件优化

```python
# 对于超大数据集（>10 GB）
dataset = rn.Artifact("huge-dataset", type="dataset")

# 方式 1: 外部引用（不下载）
dataset.add_reference("s3://bucket/data", checksum="sha256:...")

# 方式 2: 分块上传（未来功能）
# dataset.add_dir("data/", chunk_size="1GB")
```

---

## 🔍 故障排除

### 问题 1: "Artifacts system is not available"

**原因**: artifacts 模块未正确加载

**解决**:
```bash
# 检查 Python 路径
python -c "import runicorn.artifacts; print('OK')"

# 重新安装
pip install --upgrade runicorn
```

### 问题 2: FileNotFoundError

**原因**: 文件路径不存在

**解决**:
```python
# 使用绝对路径
from pathlib import Path
model_path = Path("model.pth").resolve()
artifact.add_file(str(model_path))
```

### 问题 3: 磁盘空间不足

**原因**: 多个版本占用大量空间

**解决**:
```bash
# 查看统计
$ runicorn artifacts --action stats

# 删除旧版本
$ runicorn artifacts --action delete --name old-model --version 1 --permanent

# 清理孤立的去重文件（未来功能）
# $ runicorn artifacts --action cleanup-dedup
```

---

## 📊 Web UI 使用

### 访问 Artifacts 页面

1. 启动 viewer: `runicorn viewer`
2. 打开浏览器: `http://127.0.0.1:23300`
3. 点击顶部菜单 "Artifacts"（或"模型仓库"）

### 功能介绍

#### Artifacts 列表
- 查看所有已保存的模型和数据集
- 统计卡片显示总数、大小、去重节省等
- 按类型筛选
- 搜索功能

#### Artifact 详情
- **Info 标签**: 基本信息、元数据、标签
- **Files 标签**: 文件列表、外部引用
- **Version History 标签**: 所有版本历史
- **Lineage 标签**: 血缘关系图

#### 版本对比（未来功能）
- 对比两个版本的差异
- 查看元数据变化
- 查看文件变化

---

## 🔗 血缘追踪示例

### 完整工作流

```python
# Step 1: 准备数据集
run_data = rn.init(project="ml_pipeline", name="data_prep")
dataset = rn.Artifact("processed-data", type="dataset")
dataset.add_dir("processed_data/")
dataset.add_metadata({"num_samples": 10000})
run_data.log_artifact(dataset)  # → processed-data:v1
rn.finish()

# Step 2: 训练模型
run_train = rn.init(project="ml_pipeline", name="training")
dataset = run_train.use_artifact("processed-data:v1")  # 自动追踪
data_path = dataset.download()

# 训练...
model = rn.Artifact("trained-model", type="model")
model.add_file("model.pth")
model.add_metadata({"trained_with": "processed-data:v1"})
run_train.log_artifact(model)  # → trained-model:v1
rn.finish()

# Step 3: 模型评估
run_eval = rn.init(project="ml_pipeline", name="evaluation")
model = run_eval.use_artifact("trained-model:v1")  # 自动追踪
# 评估...
rn.finish()

# 血缘关系（自动生成）：
# processed-data:v1 → run_train → trained-model:v1 → run_eval
```

### 在 Web UI 查看血缘图

1. 进入 Artifacts 页面
2. 点击 `trained-model`
3. 切换到 "Lineage" 标签
4. 点击 "Load Lineage Graph"
5. 查看图形化的依赖关系

---

## 💾 存储结构

```
user_root_dir/
├── artifacts/                          # Artifacts 根目录
│   ├── models/                         # 模型类型
│   │   └── resnet50-model/             # Artifact 名称
│   │       ├── versions.json           # 版本索引
│   │       ├── v1/                     # 版本 1
│   │       │   ├── files/              # 实际文件
│   │       │   │   └── model.pth
│   │       │   ├── metadata.json       # 版本元数据
│   │       │   └── manifest.json       # 文件清单
│   │       ├── v2/                     # 版本 2
│   │       └── v3/                     # 版本 3
│   ├── datasets/                       # 数据集类型
│   │   └── imagenet-subset/
│   │       └── ...
│   └── .dedup/                         # 去重存储池
│       └── a1/
│           └── a1b2c3d4.../            # 按哈希存储
├── <project>/
│   └── <name>/
│       └── runs/
│           └── <run_id>/
│               ├── artifacts_used.json     # 此 run 使用的 artifacts
│               └── artifacts_created.json  # 此 run 创建的 artifacts
```

---

## ⚡ 性能优化

### 内容去重

Runicorn 自动对相同内容的文件进行去重：

```
场景：保存 10 个模型版本，每个 1 GB，实际变化 10%

Without dedup: 10 GB 磁盘占用
With dedup:    ~1.5 GB 磁盘占用
节省:          85%
```

### 硬链接

相同内容的文件使用硬链接，零额外空间：

```
v1/files/model.pth  ─┐
v2/files/model.pth  ─┼─> .dedup/a1b2c3.../  (实际文件)
v3/files/model.pth  ─┘

三个版本，只占用一份空间
```

---

## 📖 更多示例

查看完整示例：
- `examples/test_artifacts.py` - 完整工作流演示
- Web UI 中的 Quick Start Guide

---

## 🔮 未来功能（规划中）

- [ ] 别名管理（production, staging, etc.）
- [ ] 版本对比工具
- [ ] 增量上传（只传输变化部分）
- [ ] 压缩存储
- [ ] 云端集成（可选的 S3/OSS 同步）
- [ ] Artifact 搜索
- [ ] Artifact 导出/导入

---

## 📝 总结

Runicorn Artifacts 提供：
- ✅ **完全本地化**的版本控制
- ✅ **自动去重**节省空间
- ✅ **血缘追踪**保证可复现性
- ✅ **简洁 API**易于使用
- ✅ **零成本**永久免费

适合：
- 需要模型版本管理的项目
- 需要数据集版本控制的研究
- 需要完整血缘追踪的生产部署
- 对数据隐私敏感的场景

---

**文档更新**: 2025-09-30  
**相关文档**: [README](README.md), [架构文档](../../reference/zh/ARCHITECTURE.md)

