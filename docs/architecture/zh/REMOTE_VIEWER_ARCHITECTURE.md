[English](../en/REMOTE_VIEWER_ARCHITECTURE.md) | [简体中文](REMOTE_VIEWER_ARCHITECTURE.md)

---

# Remote Viewer 架构设计

**文档类型**: 架构  
**版本**: v0.7.0  
**最后更新**: 2026-05-10  
**状态**: 已实现

## 概述

Remote Viewer 的当前实现不是“远程文件同步”，而是通过本地 Viewer API 管理 SSH 连接、远端 Viewer 进程和本地端口转发，让浏览器访问一个被转发回本机的远端 Viewer。

本文档内容基于以下实现链路核实：

- `src/runicorn/viewer/api/remote/*.py`
- `src/runicorn/remote/connection.py`
- `src/runicorn/remote/ssh_backend.py`
- `src/runicorn/remote/viewer/manager.py`
- `src/runicorn/remote/viewer/session.py`
- `src/runicorn/remote/viewer/tunnel.py`

## 当前结构

```text
Browser / Frontend
  -> /api/remote/* (FastAPI)
  -> SSHConnectionPool
  -> RemoteViewerManager
  -> SSH backend fallback chain
       OpenSSH -> AsyncSSH -> Paramiko
  -> remote runicorn viewer process
  -> local forwarded URL (http://localhost:<localPort>)
```

这里有两个关键分层：

1. 连接层  
   负责 SSH 认证、连接缓存、命令执行、环境探测。
2. Viewer 会话层  
   负责远端 viewer 进程、隧道生命周期、健康检查和恢复。

## API 层职责

当前 `/api/remote/*` 大致分为五组：

1. SSH 连接与状态  
   `connect`、`sessions`、`disconnect`、`status`
2. 环境探测  
   `conda-envs`、`env-configs`、`config`、`storage-candidates`
3. host key 管理  
   `known-hosts/accept`、`list`、`remove`
4. viewer 会话  
   `viewer/start`、`stop`、`sessions`、`status/{session_id}`
5. 已保存连接  
   `connections/saved`

其中 `connect` 与 `viewer/start` 都支持通过 `saved_server_id` 解析已保存服务器条目，而不是要求每次都显式传递完整凭据。

## 连接模型

### SSHConnectionPool

`request.app.state.connection_pool` 作为 SSH 连接池使用。当前 API 层在首次请求时按需初始化连接池，并通过 `host + port + username` 组合管理连接。

`/api/remote/connect` 的职责是：

1. 合并显式请求体与 `saved_server_id` 对应的保存配置
2. 组装 `SSHConfig`
3. 通过连接池获取或创建连接
4. 返回可供后续环境探测和 viewer 启动使用的 `connection_id`

### 已保存服务器条目

保存配置不只是 UI 辅助。当前它已经是远程工作流的一部分：

- `GET /api/remote/connections/saved` 返回脱敏后的连接定义
- `POST /api/remote/connections/saved` 保存列表
- 远程连接与 viewer 启动都可以用 `saved_server_id` 补全凭据

这意味着“saved server / profile”已经进入当前 remote 主模型，而不是外部附属能力。

## SSH backend 回退链

Remote Viewer 当前不是固定使用单一 Paramiko 隧道。`src/runicorn/remote/ssh_backend.py` 中实现了回退链：

1. OpenSSH  
   优先使用系统 `ssh` / `ssh-keyscan`，兼容原生客户端行为。
2. AsyncSSH  
   当 OpenSSH 不可用或不适合当前场景时回退。
3. Paramiko  
   作为最终保底实现。

这个回退链的意义是把“能否连通远端 viewer”从单个依赖的成功与否中解耦出来，提高兼容性。

## Host key 协议

Host key 校验是当前协议的一部分，而不是文档层面的补充说明。

当前行为：

1. 建连或启动 viewer 时执行 host key 校验
2. unknown / changed 情况统一抛到 API 层
3. API 返回 `409 Conflict`
4. 前端调用 `POST /api/remote/known-hosts/accept`
5. 用户确认后重试原请求

因此：

- host key 不是静默自动接受
- `known_hosts` 管理属于显式用户交互面

## Viewer 会话模型

`RemoteViewerManager` 负责：

1. 启动远端 viewer 进程
2. 选择本地与远端端口
3. 建立和维护 SSH 隧道
4. 维护 session 注册表
5. 监控远端进程与隧道状态
6. 在允许的边界内重连或重启

`RemoteViewerSession.to_dict()` 暴露给前端的核心字段包括：

- `sessionId`
- `host`
- `sshPort`
- `username`
- `localPort`
- `remotePort`
- `remoteRoot`
- `remotePid`
- `status`
- `startedAt`
- `uptimeSeconds`
- `isActive`
- `url`

## 会话状态机

当前状态枚举定义在 `src/runicorn/remote/viewer/session.py`：

- `running`
- `reconnecting`
- `degraded`
- `disconnected`
- `stopped`

状态语义：

1. `running`  
   远端进程与隧道处于可用状态。
2. `reconnecting`  
   隧道或 SSH 连接暂时丢失，manager 正在重建。
3. `degraded`  
   远端进程健康检查失败，且自动重启未立即恢复。
4. `disconnected`  
   连接彻底失效，会话不再可恢复。
5. `stopped`  
   用户或系统显式停止该会话。

实现里还有两个值得注意的边界：

- `reconnecting` 和 `degraded` 仍被视为“active”，避免过早被清理
- 若健康检查确认进程恢复，`degraded` 可以回到 `running`

## 健康检查与恢复

当前恢复逻辑主要位于 `RemoteViewerManager`：

1. 隧道异常时进入 `reconnecting`
2. 若 SSH 连接可恢复，则重建隧道
3. 若远端 viewer 进程死亡，会尝试重启远端进程
4. 重启失败后标记为 `degraded`
5. 当连接彻底不可恢复时，标记为 `disconnected`

所以当前模型不是“失败即销毁”，而是有限恢复 + 明确状态暴露。

## 关闭语义

`POST /api/remote/viewer/stop` 除了停止 viewer session，还会检查该 SSH 连接是否仍被其他 session 复用。

- 若仍被其他 session 使用，则保留连接
- 若已无其他 session 使用，则自动从连接池移除

这让“Viewer 会话”和“SSH 连接”在生命周期上保持松耦合但可协调。

## 与旧模型的区别

当前实现已经明显区别于早期文档中的简化认知：

1. 不是单一 Paramiko 隧道
2. 不是只有 `running/stopped` 两态
3. 不是忽略 host key 交互
4. saved server / profile 已进入主工作流
5. Viewer 管理器承担恢复与健康检查职责

## 维护要求

当以下内容变更时，需要同步更新本文档与 `docs/api/*/remote_api.md`：

1. `/api/remote/*` 路由增删
2. 409 host key 协议字段变化
3. SSH backend 回退链变化
4. session 状态枚举变化
5. saved server / profile 在 remote 工作流中的角色变化

---

- **[Remote API 文档](../../api/zh/remote_api.md)**
- **[SSH API 历史说明](../../api/zh/ssh_api.md)**
- **[架构文档索引](README.md)**
