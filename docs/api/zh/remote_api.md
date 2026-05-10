[English](../en/remote_api.md) | [简体中文](remote_api.md)

---

# Remote Viewer API 参考文档

> **版本**: v0.7.2  
> **最后更新**: 2026-05-10  
> **Base URL**: `http://127.0.0.1:23300`

## 概述

当前有效的远程接口统一位于 `/api/remote/*`。本文档只记录已在下列实现中核实过的接口：

- `src/runicorn/viewer/api/remote/__init__.py`
- `src/runicorn/viewer/api/remote/connections.py`
- `src/runicorn/viewer/api/remote/sessions.py`
- `src/runicorn/viewer/api/remote/viewer_routes.py`
- `src/runicorn/viewer/api/remote/known_hosts.py`
- `src/runicorn/viewer/api/remote/saved_connections.py`

旧的 `/api/unified/*` 与 `/api/ssh/*` 不再是当前接口表面，请改看 [ssh_api.md](./ssh_api.md) 中的历史说明。

## 当前接口总览

### 连接与会话

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/remote/connect` | 建立 SSH 连接 |
| `GET` | `/api/remote/sessions` | 列出连接池中的活动连接 |
| `POST` | `/api/remote/disconnect` | 移除指定连接 |
| `GET` | `/api/remote/status` | 汇总连接与 viewer session 状态 |

### 环境与运行时探测

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/remote/conda-envs` | 列出远端 Python/Conda 环境 |
| `GET` | `/api/remote/env-configs` | 批量读取环境的 Python / Runicorn 版本 |
| `GET` | `/api/remote/config` | 读取指定环境的运行时建议配置 |
| `GET` | `/api/remote/storage-candidates` | 探测远端存储候选目录 |

### Host Key 管理

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/remote/known-hosts/accept` | 接受并写入 host key |
| `GET` | `/api/remote/known-hosts/list` | 列出 Runicorn 管理的 `known_hosts` 条目 |
| `POST` | `/api/remote/known-hosts/remove` | 删除指定 host key 条目 |

### Remote Viewer

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/remote/viewer/start` | 启动远程 Viewer 并建立隧道 |
| `POST` | `/api/remote/viewer/stop` | 停止指定 viewer session |
| `GET` | `/api/remote/viewer/sessions` | 列出所有 viewer session |
| `GET` | `/api/remote/viewer/status/{session_id}` | 获取单个 viewer session 状态 |

### 已保存连接

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/remote/connections/saved` | 读取脱敏后的已保存连接 |
| `POST` | `/api/remote/connections/saved` | 保存连接配置列表 |

## SSH 后端与 host key 协议

Remote Viewer 的 SSH 隧道不是单一路径实现。当前代码会优先尝试 OpenSSH，随后回退到 AsyncSSH，再回退到 Paramiko。Host key 校验失败时，`connect` 与 `viewer/start` 都会返回统一的 `409 Conflict` 协议。

示例：

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

当 `reason` 为 `changed` 时，payload 还可能包含 `expected_fingerprint_sha256` 和 `expected_public_key`。客户端应先调用 `POST /api/remote/known-hosts/accept`，再重试原请求。

## 连接接口

### `POST /api/remote/connect`

请求体支持两种模式：

1. 直接提供连接字段：
   - `host`
   - `port`，默认 `22`
   - `username`
   - `password`
   - `private_key`
   - `private_key_path`
   - `passphrase`
   - `use_agent`
2. 通过 `saved_server_id` 从已保存服务器条目解析缺省凭据

若在解析后仍缺少 `host` 或 `username`，接口返回 `400`。

成功响应：

```json
{
  "ok": true,
  "connection_id": "user@example.com:22",
  "host": "example.com",
  "port": 22,
  "username": "user",
  "connected": true
}
```

### `GET /api/remote/sessions`

返回连接池中的活动连接列表：

```json
{
  "sessions": [
    {
      "key": "user@example.com:22",
      "host": "example.com",
      "port": 22,
      "username": "user",
      "connected": true
    }
  ]
}
```

### `POST /api/remote/disconnect`

请求体：

```json
{
  "host": "example.com",
  "port": 22,
  "username": "user"
}
```

成功时返回：

```json
{"ok": true, "message": "Connection removed"}
```

未找到时返回：

```json
{"ok": false, "message": "Connection not found"}
```

### `GET /api/remote/status`

返回整体 remote 运行状态：

```json
{
  "connections": [],
  "viewer_sessions": [],
  "connection_count": 0,
  "viewer_session_count": 0
}
```

## 环境与配置接口

### `GET /api/remote/conda-envs`

查询参数：

- `connection_id`

成功时返回：

```json
{
  "ok": true,
  "envs": [
    {
      "name": "base",
      "type": "conda",
      "python_version": "3.11.9",
      "path": "/opt/conda/bin/python",
      "is_default": true
    }
  ]
}
```

### `GET /api/remote/env-configs`

查询参数：

- `connection_id`

成功时返回按环境名组织的摘要：

```json
{
  "ok": true,
  "configs": {
    "base": {
      "pythonVersion": "3.11.9",
      "runicornVersion": "0.7.2"
    }
  }
}
```

### `GET /api/remote/config`

查询参数：

- `connection_id`
- `conda_env`，默认 `system`

成功响应字段已经在代码中核实：

```json
{
  "ok": true,
  "condaEnv": "system",
  "pythonVersion": "Python 3.11.9",
  "runicornVersion": "0.7.2",
  "defaultStorageRoot": "/home/user/runicorn_data",
  "storageRootExists": true,
  "suggestedRemotePort": 23300,
  "connectionId": "user@example.com:22",
  "homeDirectory": "/home/user"
}
```

### `GET /api/remote/storage-candidates`

查询参数：

- `connection_id`
- `conda_env`，默认 `system`
- `scan_root`，可选
- `max_depth`，代码中会被钳制到 `1..8`

响应：

```json
{
  "scan_root": null,
  "max_depth": 3,
  "candidates": []
}
```

## Known Hosts 接口

### `POST /api/remote/known-hosts/accept`

请求体：

```json
{
  "host": "example.com",
  "port": 22,
  "key_type": "ssh-ed25519",
  "public_key": "ssh-ed25519 AAAA...",
  "fingerprint_sha256": "SHA256:..."
}
```

成功响应：

```json
{"ok": true}
```

### `GET /api/remote/known-hosts/list`

成功响应：

```json
{
  "entries": [
    {
      "host": "example.com",
      "port": 22,
      "known_hosts_host": "example.com",
      "key_type": "ssh-ed25519",
      "key_base64": "AAAA...",
      "fingerprint_sha256": "SHA256:..."
    }
  ]
}
```

### `POST /api/remote/known-hosts/remove`

请求体：

```json
{
  "host": "example.com",
  "port": 22,
  "key_type": "ssh-ed25519"
}
```

成功响应：

```json
{"ok": true, "changed": true}
```

## Remote Viewer 接口

### `POST /api/remote/viewer/start`

请求体在连接字段之外还支持：

- `remote_root`
- `local_port`
- `remote_port`
- `conda_env`
- `saved_server_id`

成功响应：

```json
{
  "ok": true,
  "session": {
    "sessionId": "abcd1234",
    "host": "example.com",
    "sshPort": 22,
    "username": "user",
    "localPort": 18080,
    "remotePort": 23300,
    "remoteRoot": "/data/runicorn",
    "remotePid": 12345,
    "status": "running",
    "startedAt": 1760000000000,
    "uptimeSeconds": 1.2,
    "isActive": true,
    "url": "http://localhost:18080"
  },
  "message": "Remote Viewer ready at http://localhost:18080"
}
```

### `POST /api/remote/viewer/stop`

请求体：

```json
{"session_id": "abcd1234"}
```

成功响应：

```json
{"ok": true, "message": "Session abcd1234 stopped"}
```

### `GET /api/remote/viewer/sessions`

返回值为 `session.to_dict()` 列表，字段与上面的 `session` 对象一致。

### `GET /api/remote/viewer/status/{session_id}`

返回单个 `session.to_dict()`。当前会话状态枚举来自 `src/runicorn/remote/viewer/session.py`：

- `running`
- `reconnecting`
- `degraded`
- `disconnected`
- `stopped`

## 已保存连接接口

### `GET /api/remote/connections/saved`

返回脱敏后的连接配置，只保留 `kind` 为 `server` 或 `connection` 的条目。测试已覆盖：

- 保存的 `password` / `passphrase` 不直接回显
- 会补充 `hasSavedPassword` / `hasSavedPassphrase`
- `private_key_path` 会规范化为 `privateKeyPath`

响应示例：

```json
{
  "ok": true,
  "connections": [
    {
      "kind": "server",
      "id": "srv_admin_example_22",
      "host": "example.com",
      "port": 22,
      "username": "admin",
      "authMethod": "password",
      "hasSavedPassword": true,
      "hasSavedPassphrase": false
    }
  ]
}
```

### `POST /api/remote/connections/saved`

请求体为连接配置数组。成功响应：

```json
{"ok": true, "message": "Connections saved successfully"}
```

## 错误处理

当前接口使用 FastAPI 标准错误体：

```json
{"detail": "message"}
```

已核实的常见状态码：

- `400`: 参数不完整、格式非法、连接池或 manager 未初始化
- `404`: 连接或 session 不存在
- `409`: host key 需要用户确认
- `500`: 远端命令、保存配置、viewer 启动等运行时失败
- `503`: remote 模块不可用

## 明确不在当前实现中的接口

以下接口在本文档更新时未在 `src/runicorn/viewer/api/remote/` 中找到实现，因此不再作为当前参考保留：

- `/api/remote/fs/list`
- `/api/remote/fs/exists`

如未来重新引入，应在实现落地后再补回主文档。

---

**[返回 API 索引](API_INDEX.md)** | **[SSH 历史说明](ssh_api.md)**
