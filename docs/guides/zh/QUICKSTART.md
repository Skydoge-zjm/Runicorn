[English](../en/QUICKSTART.md) | [简体中文](QUICKSTART.md)

---

# Runicorn 快速上手指南

5 分钟了解核心功能。

---

## 📦 安装

```bash
pip install runicorn
```

**要求**: Python 3.8+

---

## 🚀 基础使用

### 1. 实验追踪

```python
import runicorn as rn

# 初始化实验
run = rn.init(project="my_project", name="experiment_1")

# 记录指标
for epoch in range(10):
    loss = 1.0 / (1 + epoch)
    accuracy = 0.5 + epoch * 0.05
    
    rn.log({
        "loss": loss,
        "accuracy": accuracy
    }, step=epoch)

# 完成
rn.finish()
print(f"实验 ID: {run.id}")
```

### 2. 启动查看器

```bash
runicorn viewer
```

打开浏览器: [http://127.0.0.1:23300](http://127.0.0.1:23300)

---

## 📊 查看结果

在 Web 界面中：

- **实验列表**: 查看所有运行
- **实验详情**: 点击查看图表和日志
- **指标图表**: 交互式训练曲线
- **实时日志**: 实时日志流

---

## 💾 模型版本控制

### 保存模型

```python
import runicorn as rn

run = rn.init(project="training")

# 训练后
# torch.save(model.state_dict(), "model.pth")

# 保存为版本化 artifact
artifact = rn.Artifact("my-model", type="model")
artifact.add_file("model.pth")
artifact.add_metadata({"accuracy": 0.95})

version = run.log_artifact(artifact)  # v1, v2, v3...
rn.finish()
```

### 加载模型

```python
import runicorn as rn

run = rn.init(project="inference")

# 加载模型
artifact = run.use_artifact("my-model:latest")
model_path = artifact.download()

# 使用模型...
rn.finish()
```

---

## 🔄 远程同步

在远程服务器训练，本地实时查看结果。

**在 Web 界面**:
1. 进入"远程"页面
2. 输入 SSH 凭据
3. 点击"配置智能模式"
4. 实验自动同步！

---

## ⚙️ 配置

### 设置存储位置

```bash
runicorn config --set-user-root "E:\RunicornData"
```

或在 Web 界面: 设置 (⚙️) → 数据目录

---

## 📚 了解更多

- **[Artifacts 指南](ARTIFACTS_GUIDE.md)** - 模型版本控制
- **[远程存储指南](REMOTE_STORAGE_USER_GUIDE.md)** - 远程同步设置
- **[演示示例](DEMO_EXAMPLES_GUIDE.md)** - 示例代码讲解

---

**[返回指南](README.md)** | **[返回主页](../../README.md)**

