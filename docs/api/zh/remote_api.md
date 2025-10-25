# Remote Viewer API 参考文档

> **版本**: v0.5.0  
> **最后更新**: 2025-10-25  
> **Base URL**: `http://localhost:23300`

[English](../en/remote_api.md) | [简体中文](remote_api.md)

---

## 📖 目录

- [概述](#概述)
- [认证](#认证)
- [连接管理](#连接管理)
  - [POST /api/remote/connect](#post-apiremoteconnect)
  - [GET /api/remote/connections](#get-apiremoteconnections)
  - [DELETE /api/remote/connections/{id}](#delete-apiremoteconnectionsid)
- [环境检测](#环境检测)
- [Remote Viewer 管理](#remote-viewer-管理)
- [健康检查](#健康检查)
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

### 工作流程

```
1. POST /api/remote/connect          # 建立 SSH 连接
2. GET /api/remote/environments      # 检测 Python 环境
3. POST /api/remote/viewer/start     # 启动 Remote Viewer
4. GET /api/remote/viewer/status     # 监控状态
5. DELETE /api/remote/connections/id # 断开连接
```

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
| `auth_method` | string | ✅ | 认证方式: `"key"`, `"password"`, `"agent"` |
| `private_key_path` | string | ⚠️ | 私钥路径（auth_method="key" 时必需） |
| `private_key_content` | string | ⚠️ | 私钥内容（替代 private_key_path） |
| `key_passphrase` | string | ❌ | 私钥密码（如果私钥有密码保护） |
| `password` | string | ⚠️ | SSH 密码（auth_method="password" 时必需） |
| `timeout` | integer | ❌ | 连接超时（秒，默认: 30） |

#### 请求示例

**cURL**:
```bash
curl -X POST http://localhost:23300/api/remote/connect \
  -H "Content-Type: application/json" \
  -d '{
    "host": "gpu-server.com",
    "port": 22,
    "username": "mluser",
    "auth_method": "key",
    "private_key_path": "~/.ssh/id_rsa"
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
        "auth_method": "key",
        "private_key_path": "~/.ssh/id_rsa"
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
    auth_method: 'key',
    private_key_path: '~/.ssh/id_rsa'
  })
});

const result = await response.json();
const connectionId = result.connection_id;
```

#### 响应

**成功响应** (200 OK):
```json
{
  "success": true,
  "connection_id": "conn_1a2b3c4d",
  "host": "gpu-server.com",
  "port": 22,
  "username": "mluser",
  "status": "connected",
  "server_info": {
    "hostname": "gpu-server-01",
    "os": "Linux",
    "kernel": "5.15.0-76-generic",
    "python_version": "3.10.8"
  },
  "created_at": "2025-10-25T10:30:00Z"
}
```

**错误响应** (400/401/500):
```json
{
  "success": false,
  "error": "authentication_failed",
  "message": "SSH authentication failed: Invalid private key",
  "details": {
    "host": "gpu-server.com",
    "username": "mluser",
    "auth_method": "key"
  }
}
```

#### 错误码

| 状态码 | 错误码 | 描述 |
|--------|--------|------|
| 400 | `invalid_parameters` | 缺少必需参数或参数格式错误 |
| 401 | `authentication_failed` | SSH 认证失败 |
| 408 | `connection_timeout` | 连接超时 |
| 500 | `ssh_error` | SSH 连接错误 |
| 503 | `service_unavailable` | SSH 服务不可用 |

#### 注意事项

- 私钥路径支持 `~` 展开
- 私钥内容应为完整的 PEM 格式
- 连接建立后会自动保持心跳
- 同一服务器可以建立多个连接

---

### GET /api/remote/connections

获取所有活动的远程连接列表。

#### 请求

**URL**: `GET /api/remote/connections`

**Query Parameters**: 无

#### 请求示例

**cURL**:
```bash
curl http://localhost:23300/api/remote/connections
```

**Python**:
```python
import requests

response = requests.get("http://localhost:23300/api/remote/connections")
connections = response.json()["connections"]
```

**JavaScript**:
```javascript
const response = await fetch('http://localhost:23300/api/remote/connections');
const { connections } = await response.json();
```

#### 响应

**成功响应** (200 OK):
```json
{
  "success": true,
  "connections": [
    {
      "connection_id": "conn_1a2b3c4d",
      "host": "gpu-server.com",
      "port": 22,
      "username": "mluser",
      "status": "connected",
      "created_at": "2025-10-25T10:30:00Z",
      "last_ping": "2025-10-25T10:35:00Z",
      "viewer": {
        "status": "running",
        "local_port": 8081,
        "remote_port": 45342,
        "url": "http://localhost:8081"
      }
    }
  ],
  "total": 1
}
```

---

### DELETE /api/remote/connections/{id}

断开指定的远程连接。

#### 请求

**URL**: `DELETE /api/remote/connections/{connection_id}`

**Path Parameters**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `connection_id` | string | ✅ | 连接ID |

**Query Parameters**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `force` | boolean | ❌ | 强制断开（默认: false） |
| `cleanup_viewer` | boolean | ❌ | 同时清理 Remote Viewer（默认: true） |

#### 请求示例

**cURL**:
```bash
curl -X DELETE "http://localhost:23300/api/remote/connections/conn_1a2b3c4d?cleanup_viewer=true"
```

**Python**:
```python
import requests

response = requests.delete(
    "http://localhost:23300/api/remote/connections/conn_1a2b3c4d",
    params={"cleanup_viewer": True}
)
```

#### 响应

**成功响应** (200 OK):
```json
{
  "success": true,
  "message": "Connection disconnected successfully",
  "connection_id": "conn_1a2b3c4d",
  "cleanup_performed": {
    "ssh_tunnel": true,
    "remote_viewer": true,
    "temp_files": true
  }
}
```

---

## 环境检测

### GET /api/remote/environments

列出远程服务器上检测到的 Python 环境。

#### 请求

**URL**: `GET /api/remote/environments`

**Query Parameters**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `connection_id` | string | ✅ | 连接ID |
| `filter` | string | ❌ | 过滤条件: `"all"`, `"runicorn_only"` (默认: "all") |

#### 请求示例

**cURL**:
```bash
curl "http://localhost:23300/api/remote/environments?connection_id=conn_1a2b3c4d"
```

**Python**:
```python
import requests

response = requests.get(
    "http://localhost:23300/api/remote/environments",
    params={"connection_id": "conn_1a2b3c4d"}
)

environments = response.json()["environments"]
```

#### 响应

**成功响应** (200 OK):
```json
{
  "success": true,
  "connection_id": "conn_1a2b3c4d",
  "environments": [
    {
      "name": "pytorch-env",
      "type": "conda",
      "python_version": "3.9.15",
      "python_path": "/home/mluser/miniconda3/envs/pytorch-env/bin/python",
      "runicorn_installed": true,
      "runicorn_version": "0.5.0",
      "storage_root": "/data/experiments",
      "is_active": true
    }
  ],
  "total": 1
}
```

---

### POST /api/remote/environments/detect

重新检测远程服务器上的 Python 环境。

#### 请求

**URL**: `POST /api/remote/environments/detect`

**Body Parameters**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `connection_id` | string | ✅ | 连接ID |
| `force_refresh` | boolean | ❌ | 强制刷新缓存（默认: false） |

#### 请求示例

**cURL**:
```bash
curl -X POST http://localhost:23300/api/remote/environments/detect \
  -H "Content-Type: application/json" \
  -d '{"connection_id": "conn_1a2b3c4d", "force_refresh": true}'
```

#### 响应

**成功响应** (200 OK):
```json
{
  "success": true,
  "message": "Environments detected successfully",
  "connection_id": "conn_1a2b3c4d",
  "environments_found": 3,
  "detection_time": "2025-10-25T10:35:00Z"
}
```

---

### GET /api/remote/config

获取远程服务器的 Runicorn 配置。

#### 请求

**URL**: `GET /api/remote/config`

**Query Parameters**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `connection_id` | string | ✅ | 连接ID |
| `env_name` | string | ✅ | 环境名称 |

#### 请求示例

**cURL**:
```bash
curl "http://localhost:23300/api/remote/config?connection_id=conn_1a2b3c4d&env_name=pytorch-env"
```

#### 响应

**成功响应** (200 OK):
```json
{
  "success": true,
  "connection_id": "conn_1a2b3c4d",
  "env_name": "pytorch-env",
  "config": {
    "user_root_dir": "/data/experiments",
    "viewer_port": 23300,
    "log_level": "INFO"
  },
  "runicorn_version": "0.5.0"
}
```

---

## Remote Viewer 管理

### POST /api/remote/viewer/start

在远程服务器上启动 Remote Viewer。

#### 请求

**URL**: `POST /api/remote/viewer/start`

**Body Parameters**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `connection_id` | string | ✅ | 连接ID |
| `env_name` | string | ✅ | Python 环境名称 |
| `remote_root` | string | ❌ | 远程存储根目录（默认: 自动检测） |
| `local_port` | integer | ❌ | 本地转发端口（默认: 自动分配） |
| `auto_open` | boolean | ❌ | 是否自动打开浏览器（默认: true） |

#### 请求示例

**cURL**:
```bash
curl -X POST http://localhost:23300/api/remote/viewer/start \
  -H "Content-Type: application/json" \
  -d '{
    "connection_id": "conn_1a2b3c4d",
    "env_name": "pytorch-env",
    "auto_open": true
  }'
```

**Python**:
```python
import requests

response = requests.post(
    "http://localhost:23300/api/remote/viewer/start",
    json={
        "connection_id": "conn_1a2b3c4d",
        "env_name": "pytorch-env",
        "auto_open": True
    }
)

viewer_info = response.json()
print(f"Viewer URL: {viewer_info['url']}")
```

#### 响应

**成功响应** (200 OK):
```json
{
  "success": true,
  "message": "Remote Viewer started successfully",
  "connection_id": "conn_1a2b3c4d",
  "viewer": {
    "status": "running",
    "local_port": 8081,
    "remote_port": 45342,
    "url": "http://localhost:8081",
    "remote_root": "/data/experiments",
    "env_name": "pytorch-env",
    "started_at": "2025-10-25T10:40:00Z"
  }
}
```

---

### POST /api/remote/viewer/stop

停止远程服务器上的 Remote Viewer。

#### 请求

**URL**: `POST /api/remote/viewer/stop`

**Body Parameters**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `connection_id` | string | ✅ | 连接ID |
| `cleanup` | boolean | ❌ | 清理临时文件（默认: true） |

#### 请求示例

**cURL**:
```bash
curl -X POST http://localhost:23300/api/remote/viewer/stop \
  -H "Content-Type: application/json" \
  -d '{"connection_id": "conn_1a2b3c4d"}'
```

#### 响应

**成功响应** (200 OK):
```json
{
  "success": true,
  "message": "Remote Viewer stopped successfully",
  "connection_id": "conn_1a2b3c4d",
  "stopped_at": "2025-10-25T11:00:00Z"
}
```

---

### GET /api/remote/viewer/status

获取 Remote Viewer 的当前状态。

#### 请求

**URL**: `GET /api/remote/viewer/status`

**Query Parameters**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `connection_id` | string | ✅ | 连接ID |

#### 请求示例

**cURL**:
```bash
curl "http://localhost:23300/api/remote/viewer/status?connection_id=conn_1a2b3c4d"
```

#### 响应

**成功响应** (200 OK):
```json
{
  "success": true,
  "connection_id": "conn_1a2b3c4d",
  "viewer": {
    "status": "running",
    "local_port": 8081,
    "url": "http://localhost:8081",
    "uptime_seconds": 3600,
    "health": "healthy"
  }
}
```

---

### GET /api/remote/viewer/logs

获取 Remote Viewer 的日志输出。

#### 请求

**URL**: `GET /api/remote/viewer/logs`

**Query Parameters**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `connection_id` | string | ✅ | 连接ID |
| `lines` | integer | ❌ | 返回的日志行数（默认: 100） |
| `level` | string | ❌ | 日志级别过滤 |

#### 请求示例

**cURL**:
```bash
curl "http://localhost:23300/api/remote/viewer/logs?connection_id=conn_1a2b3c4d&lines=50"
```

#### 响应

**成功响应** (200 OK):
```json
{
  "success": true,
  "connection_id": "conn_1a2b3c4d",
  "logs": [
    "[2025-10-25 10:40:00] INFO: Starting Remote Viewer",
    "[2025-10-25 10:40:01] INFO: Viewer listening on port 45342"
  ],
  "total_lines": 2
}
```

---

## 健康检查

### GET /api/remote/health

获取连接的健康状态。

#### 请求

**URL**: `GET /api/remote/health`

**Query Parameters**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `connection_id` | string | ✅ | 连接ID |

#### 响应

**成功响应** (200 OK):
```json
{
  "success": true,
  "connection_id": "conn_1a2b3c4d",
  "health": "healthy",
  "checks": {
    "ssh_connection": "pass",
    "viewer_process": "pass",
    "tunnel_active": "pass"
  },
  "last_check": "2025-10-25T11:00:00Z"
}
```

---

### GET /api/remote/ping

测试远程连接。

#### 请求

**URL**: `GET /api/remote/ping`

**Query Parameters**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `connection_id` | string | ✅ | 连接ID |

#### 响应

**成功响应** (200 OK):
```json
{
  "success": true,
  "connection_id": "conn_1a2b3c4d",
  "latency_ms": 45,
  "timestamp": "2025-10-25T11:00:00Z"
}
```

---

## 错误处理

所有 API 端点在发生错误时返回统一格式的错误响应。

### 错误响应格式

```json
{
  "success": false,
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    "additional": "context"
  }
}
```

### 常见错误码

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | `invalid_parameters` | 请求参数无效 |
| 401 | `authentication_failed` | SSH 认证失败 |
| 404 | `connection_not_found` | 连接不存在 |
| 404 | `environment_not_found` | 环境不存在 |
| 408 | `connection_timeout` | 连接超时 |
| 409 | `viewer_already_running` | Viewer 已在运行 |
| 500 | `internal_error` | 内部服务器错误 |
| 503 | `service_unavailable` | 服务不可用 |

---

## 速率限制

Remote API 目前不实施速率限制。

---

**作者**: Runicorn Development Team  
**版本**: v0.5.0  
**最后更新**: 2025-10-25

**[返回 API 索引](API_INDEX.md)** | **[查看快速参考](QUICK_REFERENCE.md)**
