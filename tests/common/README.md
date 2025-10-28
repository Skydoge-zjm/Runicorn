# Common Test Scripts

通用测试脚本和示例代码。

## 📁 文件说明

### 1. `create_sample_experiments.py`
创建示例实验数据，用于测试 Runicorn 系统。

**功能**：
- 创建 4 个不同类型的实验：
  - 图像分类 (ResNet50)
  - NLP (BERT fine-tuning)
  - 强化学习 (DQN)
  - 失败实验 (用于测试错误处理)

**使用方法**：
```bash
python tests/common/create_sample_experiments.py
```

**创建的实验**：
- `vision/resnet50_baseline` - 100 epochs 图像分类
- `nlp/bert_finetuning` - 5 epochs NLP 训练
- `rl/dqn_cartpole` - 500 episodes 强化学习
- `vision/mobilenet_unstable` - 失败实验 (Loss NaN)

---

### 2. `test_api_client.py`
测试 Python API Client 的所有功能。

**功能**：
- 连接测试
- 实验列表查询
- 指标数据获取
- Artifacts API
- Remote API
- 数据导出
- 错误处理
- 高级查询

**使用方法**：
```bash
# 1. 确保 Viewer 正在运行
runicorn viewer

# 2. (可选) 创建示例数据
python tests/common/create_sample_experiments.py

# 3. 运行测试
python tests/common/test_api_client.py
```

**测试内容**：
1. ✅ 连接到 Viewer
2. ✅ 列出实验
3. ✅ 获取实验详情
4. ✅ 获取指标数据
5. ✅ 列出项目
6. ✅ 获取配置
7. ✅ Artifacts API
8. ✅ Remote API
9. ✅ 数据导出
10. ✅ 上下文管理器
11. ✅ 错误处理
12. ✅ 高级查询

---

### 3. `demo_artifacts_workflow.py`
演示完整的 Artifacts 工作流程。

**功能**：
- 训练并保存模型为 Artifacts
- 加载 Artifacts 进行推理
- 微调模型并保存新版本
- 数据集 Artifacts 与外部引用
- 多文件 Artifacts（checkpoint）

**使用方法**：
```bash
python tests/common/demo_artifacts_workflow.py
```

**5 个场景**：
1. **训练并保存模型**：训练 ResNet50，保存为 artifact v1
2. **加载模型推理**：加载已保存的模型进行推理
3. **微调并创建新版本**：在 v1 基础上微调，保存为 v2
4. **数据集 Artifacts**：保存数据集元数据 + S3 外部引用
5. **多文件 Artifacts**：保存 BERT checkpoint（4个文件）

**学习内容**：
- `run.log_artifact(artifact)` - 保存 artifact
- `run.use_artifact("name:latest")` - 加载 artifact
- `artifact.download()` - 下载文件
- `artifact.add_file()` / `add_dir()` - 添加文件/目录
- `artifact.add_metadata()` / `add_tags()` - 添加元数据和标签
- `artifact.add_reference()` - 添加外部引用（S3/URL）
- 版本管理：v1, v2, v3... 自动递增

---

## 🚀 快速开始

### 完整测试流程

```bash
# 步骤 1: 安装依赖
pip install -e .

# 步骤 2: 创建示例数据
python tests/common/create_sample_experiments.py

# 步骤 3: 测试 Artifacts 功能
python tests/common/demo_artifacts_workflow.py

# 步骤 4: 启动 Viewer
runicorn viewer

# 步骤 5: 在另一个终端测试 API
python tests/common/test_api_client.py
```

---

## 📖 使用示例

### 在自己的脚本中使用 API Client

```python
import runicorn.api as api

# 连接到 Viewer
client = api.connect("http://localhost:23300")

# 列出所有实验
experiments = client.list_experiments(project="vision")
print(f"Found {len(experiments)} experiments")

# 获取指标数据
for exp in experiments:
    metrics = client.get_metrics(exp["id"])
    print(f"Experiment: {exp['name']}")
    print(f"Metrics: {list(metrics['metrics'].keys())}")

# 关闭连接
client.close()
```

### 使用上下文管理器

```python
import runicorn.api as api

with api.connect() as client:
    experiments = client.list_experiments()
    # ... 使用 client
# 自动关闭
```

### 使用 Artifacts 进行模型版本管理

```python
import runicorn as rn

# 训练并保存模型
run = rn.init(project="training", name="resnet_v1")

# ... 训练代码 ...

# 保存模型为 artifact
artifact = rn.Artifact("my-model", type="model")
artifact.add_file("model.pth")
artifact.add_metadata({"accuracy": 0.95})
version = run.log_artifact(artifact)  # v1
run.finish()

# 稍后加载模型进行推理
run2 = rn.init(project="inference", name="batch_001")
artifact = run2.use_artifact("my-model:latest")  # 或 "my-model:v1"
model_path = artifact.download()  # 下载到临时目录
# ... 使用模型 ...
run2.finish()
```

---

## 🧪 测试要求

### 环境要求
- Python 3.8+
- Runicorn 已安装 (`pip install -e .`)
- Viewer 正在运行

### 可选依赖
- `pandas` - 用于 DataFrame 工具函数

---

## 📝 注意事项

1. **Viewer 必须运行**：所有 API 测试都需要 Viewer 在后台运行
2. **示例数据**：`test_api_client.py` 需要有实验数据才能完整测试
3. **端口配置**：默认使用 `http://127.0.0.1:23300`，如需修改请编辑脚本

---

## 🔧 自定义配置

### 修改 Viewer 地址

在脚本中修改连接地址：

```python
# 默认
client = api.connect("http://127.0.0.1:23300")

# 自定义
client = api.connect("http://localhost:8080")
```

### 修改超时设置

```python
client = api.connect(
    base_url="http://localhost:23300",
    timeout=60,  # 60 秒超时
    max_retries=5  # 最多重试 5 次
)
```

---

## 🐛 故障排查

### 问题 1: ConnectionError

**错误**：`Failed to connect to Runicorn Viewer`

**解决**：
1. 确保 Viewer 正在运行：`runicorn viewer`
2. 检查端口是否正确（默认 23300）
3. 检查防火墙设置

### 问题 2: No experiments found

**错误**：测试显示 0 个实验

**解决**：
1. 运行 `create_sample_experiments.py` 创建示例数据
2. 或手动运行一些训练脚本

### 问题 3: Import errors

**错误**：`ModuleNotFoundError: No module named 'runicorn.api'`

**解决**：
```bash
# 确保在项目根目录
pip install -e .
```

---

## 📚 相关文档

- [API_USAGE_GUIDE.md](../API_USAGE_GUIDE.md) - SDK API 使用指南
- [test_api_client.py](../../test_api_client.py) - 另一个 API 测试示例
- [docs/guides/zh/QUICKSTART.md](../../docs/guides/zh/QUICKSTART.md) - 快速开始指南
