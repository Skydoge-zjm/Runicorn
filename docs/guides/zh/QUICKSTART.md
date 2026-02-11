[English](../en/QUICKSTART.md) | [简体中文](QUICKSTART.md)

---

# Runicorn 快速上手指南

> **版本**: v0.6.0

5 分钟了解核心功能。

---

## 📦 安装

```bash
pip install runicorn
```

**要求**: Python 3.10+

---

## 🚀 基础使用

### 1. 实验追踪

```python
import runicorn as rn

# 初始化实验，启用控制台捕获 (v0.6.0)
run = rn.init(
    path="my_project/experiment_1",
    capture_console=True,  # 捕获 print 输出到 logs.txt
)

# 所有 print 输出自动捕获
print("开始训练...")

# 记录指标
for epoch in range(10):
    loss = 1.0 / (1 + epoch)
    accuracy = 0.5 + epoch * 0.05
    
    print(f"Epoch {epoch}: loss={loss:.4f}, acc={accuracy:.2f}")
    
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

- **实验列表**: 查看所有运行，支持路径层级导航
- **实验详情**: 点击查看图表和日志
- **指标图表**: 交互式训练曲线，支持内联比较
- **实时日志**: 实时日志流，支持 ANSI 颜色
- **路径树导航**: VSCode 风格的文件夹导航 (v0.6.0)

---

## 📝 增强日志 (v0.6.0 新功能)

自动捕获所有控制台输出，无需修改代码：

```python
import runicorn as rn
from tqdm import tqdm

# 启用控制台捕获
run = rn.init(path="training", capture_console=True, tqdm_mode="smart")

print("开始训练...")

# tqdm 进度条智能处理
for batch in tqdm(dataloader, desc="训练中"):
    loss = train_step(batch)
    run.log({"loss": loss})

run.finish()
```

**特性**:
- ✅ 自动捕获 `print()` 到 `logs.txt`
- ✅ 智能 tqdm 处理（无日志膨胀）
- ✅ 通过 `run.get_logging_handler()` 集成 Python logging
- ✅ CV 项目的 MetricLogger 兼容

**完整指南**: [增强日志指南](ENHANCED_LOGGING_GUIDE.md)

---

## 📦 资产系统 (v0.6.0 新功能)

高效的工作区快照，支持 SHA256 去重：

```python
import runicorn as rn
from runicorn import snapshot_workspace
from pathlib import Path

run = rn.init(path="training")

# 快照代码以确保可复现性
result = snapshot_workspace(
    root=Path("."),
    out_zip=run.run_dir / "code_snapshot.zip",
)
print(f"捕获了 {result['file_count']} 个文件")

# 训练...
run.finish()
```

**特性**:
- ✅ SHA256 内容寻址存储
- ✅ 通过去重节省 50-90% 存储空间
- ✅ `.rnignore` 支持（类似 `.gitignore`）
- ✅ 基于清单的恢复

**完整指南**: [资产系统指南](ASSETS_GUIDE.md)

---

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

### v0.6.0 新功能
- **[增强日志指南](ENHANCED_LOGGING_GUIDE.md)** - 控制台捕获、Python logging 集成
- **[资产系统指南](ASSETS_GUIDE.md)** - SHA256 去重、工作区快照

### 核心功能
- **[Remote Viewer 指南](REMOTE_VIEWER_GUIDE.md)** - 远程服务器实时访问
- **[演示示例](DEMO_EXAMPLES_GUIDE.md)** - 示例代码讲解

### 迁移
- **[迁移指南](MIGRATION_GUIDE_v0.4_to_v0.5.md)** - 从 0.4.x 升级到 0.5.0

---

**[返回指南](README.md)** | **[返回主页](../../README.md)**

