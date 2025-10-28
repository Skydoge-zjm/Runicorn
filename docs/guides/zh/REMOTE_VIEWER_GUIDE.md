# Runicorn Remote Viewer 用户指南

> **Version**: v0.5.0  
> **Last Updated**: 2025-10-25  
> **Author**: Runicorn Development Team

[English](../en/REMOTE_VIEWER_GUIDE.md) | [简体中文](REMOTE_VIEWER_GUIDE.md)

---

## 📖 目录

1. [什么是 Remote Viewer](#什么是-remote-viewer)
2. [架构原理](#架构原理)
3. [使用前准备](#使用前准备)
4. [详细使用步骤](#详细使用步骤)
5. [高级功能](#高级功能)
6. [故障排查](#故障排查)
7. [最佳实践](#最佳实践)
8. [FAQ](#faq)

---

## 什么是 Remote Viewer

### 概述

Remote Viewer 采用**类似 VSCode Remote Development 的架构**，让你可以：

- 在**远程服务器上运行 Viewer 进程**
- 通过 **SSH 隧道**在本地浏览器访问
- **实时查看**远程实验数据，无需同步

### 对比传统方式

| 特性 | 传统同步 (0.4.x) | Remote Viewer (0.5.0) |
|------|------------------|----------------------|
| **数据传输** | 全量同步 | 实时访问 |
| **本地存储** | 需要（镜像） | 不需要 |
| **延迟** | 5-10 分钟 | < 100ms |
| **初始等待** | 数小时（大数据集） | 数秒（启动） |
| **网络要求** | 初始大带宽 | 持续小流量 |
| **功能完整性** | 部分功能受限 | 100% 功能 |

### 使用场景

✅ **适合**:
- 远程 GPU 服务器训练模型
- 数据集太大无法同步到本地
- 需要实时监控远程实验
- 多台服务器的实验管理

❌ **不适合**:
- 完全离线环境
- 网络不稳定
- Windows 远程服务器（暂不支持）

---

## 架构原理

### 工作流程

```
┌─────────────────┐                    ┌──────────────────────┐
│   本地机器       │                    │    远程服务器         │
│                 │                    │                      │
│  1. 启动本地     │    SSH 连接        │  2. 检测 Python      │
│     Viewer      ├───────────────────>│     环境             │
│                 │                    │                      │
│  3. 选择环境     │                    │  4. 启动远程         │
│                 │                    │     Viewer 进程      │
│                 │                    │     (后台运行)        │
│                 │                    │                      │
│  5. 建立 SSH     │    端口转发        │  6. Viewer 监听      │
│     隧道        │<───────────────────│     localhost:45342  │
│                 │                    │                      │
│  7. 浏览器访问   │                    │  8. 读取数据并       │
│     localhost:  │                    │     返回给前端        │
│     8081        │                    │                      │
└─────────────────┘                    └──────────────────────┘
```

### 技术细节

- **远程 Viewer 进程**: 独立的 FastAPI 服务器，运行在远程服务器
- **SSH 隧道**: 本地端口 (如 8081) 映射到远程 Viewer 端口 (如 45342)
- **进程管理**: 远程 Viewer 以后台进程运行，断开连接后自动清理
- **会话隔离**: 每个连接使用独立的端口，互不干扰

---

## 使用前准备

### 本地机器要求

- Python 3.8+
- Runicorn 已安装 (`pip install runicorn`)
- SSH 客户端（Windows/Linux/macOS 自带）

### 远程服务器要求

1. **操作系统**: Linux (Ubuntu, CentOS, etc.) 或 WSL
2. **Python 环境**: 
   - Python 3.8+
   - 推荐使用 Conda 或 Virtualenv
3. **Runicorn 安装**: 
   ```bash
   pip install runicorn
   ```
4. **SSH 访问**: 
   - SSH 服务已启动
   - 有效的登录凭据（密钥或密码）

### 网络要求

- 稳定的 SSH 连接
- 推荐带宽: 1 Mbps+ (实时图表更新)
- 延迟: < 500ms (跨国连接可能较慢)

---

## 详细使用步骤

### 步骤 1: 启动本地 Viewer

```bash
runicorn viewer
```

浏览器自动打开 http://localhost:23300

### 步骤 2: 进入 Remote 页面

点击顶部菜单栏的 **"Remote"** 按钮。

### 步骤 3: 配置 SSH 连接

#### 3.1 填写服务器信息

**基本信息**:
- **主机** (Host): 服务器地址
  - 域名: `gpu-server.lab.edu`
  - IP: `192.168.1.100`
- **端口** (Port): 默认 `22`
- **用户名** (User): SSH 登录用户名

#### 3.2 选择认证方式

**方式 1: SSH 密钥（推荐）**

- 点击 "SSH 密钥" 标签页
- **私钥路径**: 输入或选择私钥文件
  - Linux/macOS: `~/.ssh/id_rsa`
  - Windows: `C:\Users\YourName\.ssh\id_rsa`
- **私钥密码** (可选): 如果密钥有密码保护

**方式 2: 密码**

- 点击 "密码" 标签页
- 输入 SSH 登录密码

**方式 3: SSH Agent**

- 如果已配置 SSH Agent，选择此选项
- 系统会自动使用 Agent 中的密钥

#### 3.3 点击连接

点击 **"连接到服务器"** 按钮。

**连接成功提示**:
```
✅ SSH 连接成功
服务器: gpu-server.lab.edu
用户: your-username
```

### 步骤 4: 选择 Python 环境

#### 4.1 查看检测到的环境

系统会自动检测远程服务器上的 Python 环境，显示列表:

| 环境名称 | Python 版本 | Runicorn 版本 | 存储根目录 |
|---------|------------|--------------|-----------|
| base | Python 3.10.8 | 0.5.0 | /home/user/RunicornData |
| pytorch-env | Python 3.9.15 | 0.5.0 | /data/experiments |
| tf-gpu | Python 3.8.12 | ❌ 未安装 | - |

#### 4.2 选择合适的环境

点击环境卡片上的 **"使用此环境"** 按钮。

**注意事项**:
- ✅ 必须选择已安装 Runicorn 的环境
- ✅ 推荐选择与训练脚本相同的环境
- ⚠️  未安装 Runicorn 的环境会显示警告

### 步骤 5: 确认配置

#### 5.1 查看配置摘要

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
远程配置摘要
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
远程服务器: gpu-server.lab.edu:22
用户: your-username
Python 环境: pytorch-env
Python 版本: Python 3.9.15
Runicorn 版本: 0.5.0
存储根目录: /data/experiments
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### 5.2 检查路径

确认 **存储根目录** 是否正确:
- 这是远程服务器上 Runicorn 数据存储的位置
- 通常是 `~/RunicornData` 或自定义路径

#### 5.3 启动 Remote Viewer

点击 **"启动 Remote Viewer"** 按钮。

**启动过程**:
1. 在远程服务器启动 Viewer 进程
2. 建立 SSH 隧道
3. 健康检查
4. 自动打开新浏览器标签页

**预计时间**: 5-15 秒

### 步骤 6: 使用 Remote Viewer

#### 6.1 访问远程数据

新标签页打开后，地址类似:
```
http://localhost:8081
```

界面与本地 Viewer 完全相同，包括:
- 实验列表
- 实验详情
- 图表可视化
- 日志查看
- Artifacts 管理

#### 6.2 管理连接

在 Remote 页面底部可以看到活动连接:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
活动连接
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 gpu-server.lab.edu
   用户: your-username
   环境: pytorch-env
   本地端口: 8081
   状态: 运行中
   
   [打开 Viewer]  [停止连接]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 高级功能

### 多服务器管理

可以同时连接多台服务器:

```
🟢 gpu-server-01 → localhost:8081
🟢 gpu-server-02 → localhost:8082
🟢 data-server   → localhost:8083
```

每个连接独立运行，互不干扰。

### 自定义存储路径

如果远程服务器的 Runicorn 数据不在默认位置:

1. 选择环境后，点击 **"自定义路径"**
2. 输入实际的存储根目录路径
3. 确认并启动

### 端口冲突处理

如果本地端口被占用，系统会自动选择其他可用端口。

---

## 故障排查

### 问题 1: 连接失败

**症状**: 显示 "SSH 连接失败"

**可能原因**:
- SSH 服务未启动
- 主机名或 IP 错误
- 端口错误
- 防火墙阻止

**解决方法**:
```bash
# 测试 SSH 连接
ssh username@hostname

# 检查 SSH 服务
sudo systemctl status sshd
```

### 问题 2: 未检测到环境

**症状**: 环境列表为空

**可能原因**:
- 远程服务器上没有安装 Python
- Conda 未正确配置

**解决方法**:
```bash
# 在远程服务器上检查
which python3
conda env list
```

### 问题 3: Runicorn 版本不匹配

**症状**: 显示 "Runicorn 版本不兼容"

**解决方法**:
```bash
# 更新远程 Runicorn
pip install -U runicorn
```

### 问题 4: Remote Viewer 启动失败

**症状**: "无法启动远程 Viewer"

**排查步骤**:
1. 检查远程日志:
   ```bash
   tail -f /tmp/runicorn_viewer_*.log
   ```
2. 确认端口未被占用:
   ```bash
   netstat -tuln | grep 45342
   ```
3. 检查权限:
   ```bash
   ls -la ~/RunicornData
   ```

---

## 最佳实践

### 1. 使用 SSH 密钥

✅ **推荐**: SSH 密钥认证
- 更安全
- 无需每次输入密码
- 支持 Agent 转发

```bash
# 生成 SSH 密钥
ssh-keygen -t rsa -b 4096

# 复制公钥到服务器
ssh-copy-id username@hostname
```

### 2. 配置 SSH Config

在 `~/.ssh/config` 中配置服务器:

```
Host gpu-server
    HostName gpu-server.lab.edu
    User your-username
    Port 22
    IdentityFile ~/.ssh/id_rsa
    ServerAliveInterval 60
```

然后在 Runicorn 中只需输入主机名 `gpu-server`。

### 3. 使用 tmux/screen

在远程服务器上使用 tmux 或 screen，即使 SSH 断开，训练也会继续:

```bash
# 启动 tmux
tmux new -s training

# 运行训练脚本
python train.py

# 分离会话: Ctrl+B, D
```

### 4. 定期清理

定期清理旧的实验数据:

```bash
# 查看存储使用
du -sh ~/RunicornData

# 删除旧实验（在 Viewer 中操作）
```

---

## FAQ

### Q1: Remote Viewer 和旧的"远程同步"有什么区别？

**A**: 完全不同的架构:

| 特性 | 远程同步 (0.4.x) | Remote Viewer (0.5.0) |
|------|------------------|---------------------|
| 原理 | 文件同步 | 远程运行 Viewer |
| 数据位置 | 本地副本 | 远程服务器 |
| 实时性 | 延迟 | 实时 |
| 存储需求 | 大 | 无 |

### Q2: 支持 Windows 远程服务器吗？

**A**: 目前不支持，仅支持 Linux 和 WSL。Windows 支持在路线图中。

### Q3: 可以同时连接多台服务器吗？

**A**: 可以，每个连接使用不同的本地端口。

### Q4: 断开连接后数据会丢失吗？

**A**: 不会，数据仍在远程服务器上。重新连接即可继续访问。

### Q5: 需要保持 SSH 连接吗？

**A**: 是的，关闭 SSH 连接会导致 Remote Viewer 不可访问，但远程数据不受影响。

### Q6: 性能如何？

**A**: 
- 延迟: < 100ms (局域网), < 500ms (跨国)
- 带宽: 约 100-500 KB/s (实时图表更新)
- CPU: 远程服务器 < 5%, 本地 < 2%

### Q7: 安全吗？

**A**: 
- ✅ 所有通信通过 SSH 加密
- ✅ Viewer 只监听 localhost
- ✅ 不会暴露到公网
- ✅ 支持 SSH 密钥认证

### Q8: 如何停止 Remote Viewer？

**A**: 
- 在 Remote 页面点击 "停止连接"
- 或关闭本地 Viewer
- 远程进程会自动清理

---

## 更多资源

- [API 文档](../../api/zh/remote_api.md)
- [架构文档](../../architecture/zh/REMOTE_VIEWER_ARCHITECTURE.md)
- [故障排查](../../reference/zh/TROUBLESHOOTING.md)

---

**作者**: Runicorn Development Team  
**版本**: v0.5.0  
**最后更新**: 2025-10-25
