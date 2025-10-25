[English](../en/REMOTE_VIEWER_ARCHITECTURE.md) | [简体中文](REMOTE_VIEWER_ARCHITECTURE.md)

---

# Remote Viewer 架构设计

**文档类型**: 架构  
**版本**: v0.5.0  
**最后更新**: 2025-10-25  
**状态**: 已实现 ✅

---

## 概述

### 设计目标

Remote Viewer 是 Runicorn v0.5.0 引入的核心功能，旨在提供类似 VSCode Remote 的远程服务器访问体验，无需文件同步即可实时访问远程实验数据。

**核心目标**:
1. **零配置体验**: 用户只需提供 SSH 凭据，系统自动完成所有配置
2. **实时数据访问**: 直接在远程环境运行 Viewer，无需本地同步
3. **低延迟**: 通过 SSH 隧道实现近乎本地的访问速度
4. **安全性**: 基于 SSH 加密通信，不暴露额外端口
5. **自动清理**: 连接断开后自动清理远程资源

### 核心理念

**为什么需要 Remote Viewer？**

传统的 SSH 文件同步方案存在以下问题：
- ❌ 需要将大量数据从远程服务器同步到本地
- ❌ 同步过程耗时，尤其是大型模型和数据集
- ❌ 占用本地存储空间
- ❌ 数据更新需要重新同步
- ❌ 多人协作时容易产生冲突

**Remote Viewer 的解决方案**:
- ✅ 无需文件同步，Viewer 直接在远程运行
- ✅ 通过 SSH 隧道将远程端口转发到本地
- ✅ 本地浏览器访问，体验与本地无异
- ✅ 实时数据，无需等待同步
- ✅ 节省本地存储空间
- ✅ 支持多人同时访问

### 与 VSCode Remote 对比

| 方面 | VSCode Remote | Runicorn Remote Viewer |
|------|---------------|------------------------|
| **连接方式** | SSH | SSH |
| **端口转发** | 是 | 是 |
| **自动清理** | 是 | 是 |
| **环境检测** | 部分 | 完全自动 |
| **临时进程** | 后台服务 | 临时 Viewer |
| **配置复杂度** | 低 | 极低 |
| **ML 专用优化** | 否 | 是 |

---

## 架构设计

### 整体架构

Remote Viewer 采用**代理模式**和**RPC（远程过程调用）**设计，将用户请求通过 SSH 隧道转发到远程服务器上运行的临时 Viewer 实例。

**核心组件层次**:
```
1. 用户界面层（浏览器）
   ↓ HTTP
2. 本地 Viewer API 层（Remote API）
   ↓ SSH + 端口转发
3. SSH 隧道层（加密通信）
   ↓ TCP
4. 远程 Viewer 实例（临时进程）
   ↓ 文件 I/O
5. 远程数据存储（RunicornData）
```

### 组件划分

系统分为 **5 个核心组件**：

#### 1. Connection Manager (连接管理器)

**职责**: 管理 SSH 连接的完整生命周期

**主要功能**:
- SSH 连接建立和认证（密码/密钥）
- 连接池管理（支持多个并发连接）
- 连接状态跟踪
- 自动重连机制
- 连接断开和资源清理

**技术实现**:
- 使用 `paramiko.SSHClient` 建立 SSH 连接
- 支持密码认证和 SSH 密钥认证
- 使用 `paramiko.AgentKeys` 支持 SSH Agent
- 连接超时设置：30 秒
- Keep-alive 间隔：60 秒

#### 2. Environment Detector (环境检测器)

**职责**: 自动发现和验证远程服务器的 Python 环境

**检测算法**:
```
1. 执行 `which python` 获取系统 Python
2. 检查 conda 环境: `conda env list`
3. 扫描常见 virtualenv 目录
4. 对每个 Python 环境:
   a. 执行 `python -c "import runicorn; print(runicorn.__version__)"`
   b. 如果成功，记录环境信息
   c. 获取配置: `python -c "import runicorn.config; print(...)"`
5. 返回所有有效环境列表
```

#### 3. Viewer Launcher (Viewer 启动器)

**职责**: 在远程服务器启动和管理临时 Viewer 进程

**启动流程**:
```
1. 检查目标端口是否可用
2. 构建启动命令:
   source /path/to/env/bin/activate && \
   runicorn viewer --host 127.0.0.1 --port 23300 --no-open-browser \
   > /tmp/runicorn_viewer_{connection_id}.log 2>&1 &
3. 通过 SSH 执行命令
4. 获取进程 PID
5. 等待 2-3 秒确认启动成功
6. 检查端口是否监听: `netstat -tuln | grep :23300`
7. 返回进程信息
```

#### 4. Tunnel Manager (隧道管理器)

**职责**: 建立和维护 SSH 端口转发隧道

**技术实现**:
- 使用 `paramiko` 的 Transport.open_channel 创建隧道
- 本地端口自动选择（8081-8099 范围）
- 后台线程处理端口转发
- 隧道健康监控和自动重建

#### 5. Health Checker (健康检查器)

**职责**: 监控连接和 Viewer 的健康状态

**健康检查逻辑**:
```
每 30 秒执行一次健康检查:

1. 连接检查: 执行简单命令测试
2. Viewer 检查: HTTP GET /api/health
3. 隧道检查: 测试本地端口连通性
4. 异常处理: 自动重连/重建
```

---

## 安全设计

### SSH 认证

**支持的认证方式**:
1. **密码认证**: 用户名 + 密码
2. **SSH 密钥认证**: 私钥文件 + 可选密码短语
3. **SSH Agent**: 使用系统 SSH Agent

**安全实践**:
- ✅ 密码不存储在本地，仅在内存中
- ✅ 私钥路径可配置，支持 `~/.ssh/id_rsa` 等
- ✅ SSH Agent 优先，避免暴露密钥
- ✅ 连接使用加密通道（SSH 协议）

### 网络安全

- ✅ Viewer 仅监听 `127.0.0.1`，不对外暴露
- ✅ SSH 隧道加密所有通信
- ✅ 无需开放额外防火墙端口
- ✅ 自动清理，防止僵尸进程

---

## 性能特征

### 延迟测试

在典型场景下的性能表现：

| 操作 | 本地模式 | Remote Viewer | 差异 |
|------|---------|---------------|------|
| 加载实验列表 | 50ms | 120ms | +70ms |
| 查看实验详情 | 30ms | 90ms | +60ms |
| 加载指标图表 | 80ms | 180ms | +100ms |
| 实时日志流 | 10ms | 50ms | +40ms |

**结论**: Remote Viewer 延迟增加约 50-100ms，但仍保持良好的用户体验。

### 带宽优化

- 仅传输必要数据（元数据、指标）
- 图片等大文件按需加载
- 支持数据压缩（gzip）
- 典型会话带宽：< 1 MB/min

---

## 故障处理

### 常见故障场景

| 故障 | 检测方式 | 恢复策略 |
|------|---------|---------|
| SSH 连接断开 | Keep-alive 失败 | 自动重连（最多 3 次）|
| Viewer 进程崩溃 | 健康检查失败 | 通知用户，提供日志 |
| 隧道断开 | 端口不可达 | 重建隧道 |
| 端口冲突 | 启动失败 | 自动选择其他端口 |

---

## 相关文档

- **[SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)** - 系统整体架构
- **[Remote API 文档](../../api/zh/remote_api.md)** - API 参考
- **[Remote Viewer 用户指南](../../guides/zh/REMOTE_VIEWER_GUIDE.md)** - 使用指南

---

**导航**: [架构文档索引](README.md) | [主文档](../../README.md)


