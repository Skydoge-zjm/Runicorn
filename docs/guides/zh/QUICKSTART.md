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
    
    run.log({
        "loss": loss,
        "accuracy": accuracy
    }, step=epoch)

# 完成
run.finish()
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
run.finish()
```

### 加载模型

```python
import runicorn as rn

run = rn.init(project="inference")

# 加载模型
artifact = run.use_artifact("my-model:latest")
model_path = artifact.download()

# 使用模型...
run.finish()
```

---

## 🌐 Remote Viewer (v0.5.0 新功能)

在远程服务器训练，本地实时查看结果 - **无需同步数据**！

### 5分钟快速开始

#### 步骤 1: 确保远程服务器已安装 Runicorn

```bash
# SSH 登录到远程服务器
ssh user@gpu-server.com

# 安装 Runicorn
pip install runicorn
```

#### 步骤 2: 启动本地 Viewer

```bash
runicorn viewer
```

#### 步骤 3: 连接远程服务器

1. 在浏览器中点击 **"Remote"** 菜单
2. 填写 SSH 连接信息:
   - 主机: `gpu-server.com`
   - 用户: `your-username`
   - 认证: SSH 密钥或密码
3. 点击 **"连接到服务器"**

#### 步骤 4: 选择 Python 环境

系统自动检测远程环境，选择已安装 Runicorn 的环境。

#### 步骤 5: 启动 Remote Viewer

点击 **"启动 Remote Viewer"**，自动打开新标签页访问远程数据！

**优势**:
- ✅ 实时访问，延迟 < 100ms
- ✅ 零本地存储占用
- ✅ 连接启动仅需数秒

**完整指南**: [Remote Viewer 用户指南](REMOTE_VIEWER_GUIDE.md)

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
- **[Remote Viewer 指南](REMOTE_VIEWER_GUIDE.md)** - 远程服务器实时访问
- **[演示示例](DEMO_EXAMPLES_GUIDE.md)** - 示例代码讲解
- **[迁移指南](MIGRATION_GUIDE_v0.4_to_v0.5.md)** - 从 0.4.x 升级到 0.5.0

---

**[返回指南](README.md)** | **[返回主页](../../README.md)**

