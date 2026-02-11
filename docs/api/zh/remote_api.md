# Remote Viewer API 参考文档

> **版本**: v0.6.0  
> **最后更新**: 2025-01-XX  
> **Base URL**: `http://127.0.0.1:23300`

[English](../en/remote_api.md) | [简体中文](remote_api.md)

---

## 📖 目录

- [概述](#概述)
- [SSH 后端架构](#ssh-后端架构)
- [Host Key 校验（HTTP 409）](#host-key-校验http-409)
- [认证](#认证)
- [连接管理](#连接管理)
- [Known Hosts 管理](#known-hosts-管理)
- [环境与配置](#环境与配置)
- [Remote Viewer 管理](#remote-viewer-管理)
- [远程文件系统](#远程文件系统)
- [状态](#状态)
- [已保存连接](#已保存连接)
- [错误处理](#错误处理)

---

## 概述

Remote Viewer API 提供了通过 SSH 连接远程服务器并启动 Remote Viewer 的完整功能。采用 RESTful 设计，支持 JSON 格式的请求和响应。

### 主要特性

- 🔌 **SSH 连接管理**: 支持密钥和密码认证
- 🐍 **环境自动检测**: 识别 Conda、Virtualenv 等 Python 环境
- 🚀 **Viewer 生命周期**: 启动、监控、停止远程 Viewer
- 💓 **健康监控**: 实时连接和 Viewer 状态检查
- 🔒 **安全**: 所有通信通过 SSH 加密
- 🔄 **多后端架构**: 自动回退链以获得最大兼容性 (v0.6.0)

### 工作流程

```
1. POST /api/remote/connect               # 建立 SSH 连接
2. （可选）GET /api/remote/conda-envs     # 列出远端环境供 UI 选择
3. POST /api/remote/viewer/start          # 启动 Remote Viewer + 建立 SSH 隧道
4. GET /api/remote/viewer/status/{id}     # 查询某个会话状态
5. POST /api/remote/disconnect            # 断开 SSH 连接
```

---

## SSH 后端架构

> **v0.6.0 新增**: 多后端回退架构，提升兼容性和稳定性。

### 设计概述

Runicorn v0.6.0 引入了新的 SSH 后端架构，将**连接**和**隧道**关注点分离：

| 层 | 实现 | 描述 |
|---|------|------|
| **连接** | Paramiko（始终） | SSH 连接、命令执行、SFTP |
| **隧道** | AutoBackend | 本地端口转发，带回退链 |

### AutoBackend 回退链

`AutoBackend` 类自动选择最佳可用的隧道实现：

```
┌─────────────────────────────────────────────────────────────┐
│                     AutoBackend                              │
├─────────────────────────────────────────────────────────────┤
│  1. OpenSSH 隧道（首选）                                     │
│     └─ 使用系统 OpenSSH 客户端（ssh 命令）                   │
│     └─ 要求: PATH 中有 ssh + ssh-keyscan                    │
│     └─ 不支持密码认证                                        │
│                                                              │
│  2. AsyncSSH 隧道（回退）                                    │
│     └─ 纯 Python 异步实现                                    │
│     └─ 要求: asyncssh 包                                     │
│     └─ 支持所有认证方式                                      │
│                                                              │
│  3. Paramiko 隧道（最终回退）                                │
│     └─ 纯 Python 同步实现                                    │
│     └─ 始终可用                                              │
│     └─ 支持所有认证方式                                      │
└─────────────────────────────────────────────────────────────┘
```

### 后端选择逻辑

```python
# 后端选择伪代码
def create_tunnel(connection, local_port, remote_port):
    # 首先尝试 OpenSSH（最佳性能，原生集成）
    try:
        return OpenSSHTunnel(...)
    except (SSHNotFound, PasswordAuthRequired, HostKeyError):
        pass  # 继续（HostKeyError 除外，会重新抛出）
    
    # 其次尝试 AsyncSSH（异步，性能良好）
    try:
        return AsyncSSHTunnel(...)
    except (AsyncSSHNotAvailable, HostKeyError):
        pass  # 继续（HostKeyError 除外，会重新抛出）
    
    # 最终回退到 Paramiko（始终可用）
    return ParamikoTunnel(...)
```

### OpenSSH 后端详情

当可用时，OpenSSH 提供最佳性能和原生操作系统集成：

**要求**:
- PATH 中有 `ssh` 命令（或通过 `RUNICORN_SSH_PATH` 设置）
- PATH 中有 `ssh-keyscan` 命令（用于获取主机密钥）
- SSH 密钥认证（不支持密码认证）

**特性**:
- 使用 `BatchMode=yes` 进行非交互操作
- `ExitOnForwardFailure=yes` 确保可靠的隧道建立
- `StrictHostKeyChecking=yes` 配合 Runicorn 管理的 known_hosts
- `ServerAliveInterval=30` 保持连接活跃

**命令示例**:
```bash
ssh -N -L 127.0.0.1:8080:localhost:23300 \
    -p 22 \
    -o ExitOnForwardFailure=yes \
    -o BatchMode=yes \
    -o StrictHostKeyChecking=yes \
    -o UserKnownHostsFile=/path/to/runicorn/known_hosts \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    user@remote-server
```

### 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `RUNICORN_SSH_PATH` | ssh 可执行文件路径 | 从 PATH 自动检测 |

**示例**:
```bash
# 使用特定的 OpenSSH 安装
export RUNICORN_SSH_PATH="/usr/local/bin/ssh"

# 或在 Windows 上使用 Git Bash
set RUNICORN_SSH_PATH=C:\Program Files\Git\usr\bin\ssh.exe
```

### 安全特性

所有后端都强制执行严格的安全措施：

1. **主机密钥验证**: 始终启用，使用 Runicorn 管理的 `known_hosts`
2. **不自动接受**: 未知主机密钥触发 HTTP 409 以供用户确认
3. **密钥变更检测**: 当主机密钥与已知值不同时发出警告
4. **本地绑定**: 隧道仅绑定到 `127.0.0.1`（不暴露到网络）

---

## Host Key 校验（HTTP 409）

当 SSH Host Key 校验失败（unknown / changed）时，API 会返回：

- HTTP 状态码：`409 Conflict`
- 响应体（FastAPI 会包在 `detail` 内）：

```json
{
  "detail": {
    "code": "HOST_KEY_CONFIRMATION_REQUIRED",
    "message": "Host key verification failed",
    "host_key": {
      "host": "example.com",
      "port": 22,
      "known_hosts_host": "example.com",
      "key_type": "ssh-ed25519",
      "fingerprint_sha256": "SHA256:...",
      "public_key": "ssh-ed25519 AAAA...",
      "reason": "unknown"
    }
  }
}
```

当 `reason == "changed"` 时，可能额外包含：

- `expected_fingerprint_sha256`
- `expected_public_key`

客户端应调用 `POST /api/remote/known-hosts/accept` 写入 Runicorn 管理的 `known_hosts`，然后重试原请求。

---

## 认证

Remote API 当前不需要额外的认证。所有请求通过本地 Viewer 实例发送。

**注意**: SSH 连接本身需要认证（密钥或密码）。

---

## 连接管理

### POST /api/remote/connect

建立到远程服务器的 SSH 连接。

#### 请求

**URL**: `POST /api/remote/connect`

**Headers**:
```
Content-Type: application/json
```

**Body Parameters**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `host` | string | ✅ | 远程服务器地址（域名或IP） |
| `port` | integer | ❌ | SSH 端口（默认: 22） |
| `username` | string | ✅ | SSH 用户名 |
| `password` | string / null | ❌ | SSH 密码（可选） |
| `private_key` | string / null | ❌ | 私钥内容（可选） |
| `private_key_path` | string / null | ❌ | 私钥路径（可选） |
| `passphrase` | string / null | ❌ | 私钥密码（可选） |
| `use_agent` | boolean | ❌ | 使用 SSH Agent（默认: true） |

#### 请求示例

**cURL**:
```bash
curl -X POST http://localhost:23300/api/remote/connect \
  -H "Content-Type: application/json" \
  -d '{
    "host": "gpu-server.com",
    "port": 22,
    "username": "mluser",
    "password": null,
    "private_key": null,
    "private_key_path": "~/.ssh/id_rsa",
    "passphrase": null,
    "use_agent": true
  }'
```

**Python**:
```python
import requests

response = requests.post(
    "http://localhost:23300/api/remote/connect",
    json={
        "host": "gpu-server.com",
        "port": 22,
        "username": "mluser",
        "password": None,
        "private_key": None,
        "private_key_path": "~/.ssh/id_rsa",
        "passphrase": None,
        "use_agent": True,
    }
)

result = response.json()
connection_id = result["connection_id"]
```

**JavaScript**:
```javascript
const response = await fetch('http://localhost:23300/api/remote/connect', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    host: 'gpu-server.com',
    port: 22,
    username: 'mluser',
    password: null,
    private_key: null,
    private_key_path: '~/.ssh/id_rsa',
    passphrase: null,
    use_agent: true
  })
});

const result = await response.json();
const connectionId = result.connection_id;
```

#### 响应

**成功响应** (200 OK):
```json
{
  "ok": true,
  "connection_id": "mluser@gpu-server.com:22",
  "host": "gpu-server.com",
  "port": 22,
  "username": "mluser",
  "connected": true
}
```

**错误响应** (500/503/422):
```json
{
  "detail": "Connection failed: <reason>"
}
```

#### 状态码

| 状态码 | 含义 |
|--------|------|
| 409 | Host key 需要用户确认（见上方 409 协议） |
| 500 | 连接失败（`detail` 为错误信息） |
| 503 | Remote 模块不可用 |
| 422 | 参数校验失败（FastAPI / Pydantic） |

#### 注意事项

- 私钥路径支持 `~` 展开
- 私钥内容应为完整的 PEM 格式
- 连接建立后会自动保持心跳
- 同一服务器可以建立多个连接

---

### GET /api/remote/sessions

获取所有活动的远程连接列表。

#### 请求

**URL**: `GET /api/remote/sessions`

**Query Parameters**: 无

#### 请求示例

**cURL**:
```bash
curl http://localhost:23300/api/remote/sessions
```

**Python**:
```python
import requests

response = requests.get("http://localhost:23300/api/remote/sessions")
sessions = response.json()["sessions"]
```

**JavaScript**:
```javascript
const response = await fetch('http://localhost:23300/api/remote/sessions');
const { sessions } = await response.json();
```

#### 响应

**成功响应** (200 OK):
```json
{
  "sessions": [
    {
      "key": "mluser@gpu-server.com:22",
      "host": "gpu-server.com",
      "port": 22,
      "username": "mluser",
      "connected": true
    }
  ]
}
```

---

### POST /api/remote/disconnect

断开指定的远程连接。

#### 请求

**URL**: `POST /api/remote/disconnect`

**Body Parameters**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `host` | string | ✅ | 远程主机 |
| `port` | integer | ❌ | SSH 端口（默认: 22） |
| `username` | string | ✅ | SSH 用户名 |

#### 请求示例

**cURL**:
```bash
curl -X POST http://localhost:23300/api/remote/disconnect \
  -H "Content-Type: application/json" \
  -d '{"host": "gpu-server.com", "port": 22, "username": "mluser"}'
```

**Python**:
```python
import requests

response = requests.post(
    "http://localhost:23300/api/remote/disconnect",
    json={"host": "gpu-server.com", "port": 22, "username": "mluser"}
)
```

#### 响应

**成功响应** (200 OK):
```json
{
  "ok": true,
  "message": "Connection removed"
}
```

---

## Known Hosts 管理

### POST /api/remote/known-hosts/accept

接受 host key 并写入 Runicorn 管理的 `known_hosts`。

**URL**: `POST /api/remote/known-hosts/accept`

**Body Parameters**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `host` | string | ✅ | 远程主机 |
| `port` | integer | ✅ | SSH 端口 |
| `key_type` | string | ✅ | 公钥类型（如 `ssh-ed25519`） |
| `public_key` | string | ✅ | OpenSSH 公钥（`<type> <base64>`） |
| `fingerprint_sha256` | string | ✅ | 与 409 返回一致的指纹 |

**响应**:

```json
{"ok": true}
```

### GET /api/remote/known-hosts/list

列出 `known_hosts` 中的条目。

**URL**: `GET /api/remote/known-hosts/list`

### POST /api/remote/known-hosts/remove

删除 `known_hosts` 中的一个条目。

**URL**: `POST /api/remote/known-hosts/remove`

---

## 环境与配置

### GET /api/remote/conda-envs

列出远端 Python 环境。

**URL**: `GET /api/remote/conda-envs`

**Query Parameters**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `connection_id` | string | ✅ | 连接ID（`user@host:port`） |

### GET /api/remote/config

获取远端运行环境信息与建议配置。

**URL**: `GET /api/remote/config`

**Query Parameters**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `connection_id` | string | ✅ | 连接ID（`user@host:port`） |
| `conda_env` | string | ❌ | Conda 环境名（默认: `system`） |

---

## Remote Viewer 管理

### POST /api/remote/viewer/start

启动 Remote Viewer 会话并建立 SSH 隧道。

**URL**: `POST /api/remote/viewer/start`

### POST /api/remote/viewer/stop

停止一个 Remote Viewer 会话。

**URL**: `POST /api/remote/viewer/stop`

### GET /api/remote/viewer/sessions

列出所有 Remote Viewer 会话。

**URL**: `GET /api/remote/viewer/sessions`

### GET /api/remote/viewer/status/{session_id}

查询某个会话状态。

**URL**: `GET /api/remote/viewer/status/{session_id}`

---

## 远程文件系统

### GET /api/remote/fs/list

通过 SFTP 列出远端目录。

### GET /api/remote/fs/exists

检查远端路径是否存在。

---

## 状态

### GET /api/remote/status

获取 remote 总体状态（连接池 + viewer sessions）。

---

## 已保存连接

### GET /api/remote/connections/saved

读取已保存的 SSH 连接配置。

### POST /api/remote/connections/saved

保存 SSH 连接配置。

---

## 错误处理

Runicorn Viewer 使用 FastAPI 的标准错误响应：

```json
{"detail": "<message>"}
```

部分错误（如 host key 校验）会返回结构化的 `detail`（见 HTTP 409 协议）。

---

**作者**: Runicorn Development Team  
**版本**: v0.6.0  
**最后更新**: 2025-01-XX

**[返回 API 索引](API_INDEX.md)** | **[查看快速参考](QUICK_REFERENCE.md)**
