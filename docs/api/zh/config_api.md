[English](../en/config_api.md) | [简体中文](config_api.md)

---

# Config API - 配置管理

**模块**: Config API  
**基础路径**: `/api/config`  
**版本**: v1.0  
**描述**: 管理 Runicorn 配置，包括存储路径和 SSH 连接。

---

## 端点概览

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/config` | 获取当前配置 |
| POST | `/config/user_root_dir` | 设置用户根目录 |
| GET | `/config/ssh_connections` | 获取已保存的 SSH 连接 |
| POST | `/config/ssh_connections` | 保存 SSH 连接 |
| DELETE | `/config/ssh_connections/{key}` | 删除 SSH 连接 |
| GET | `/config/ssh_connections/{key}/details` | 获取连接详情 |

---

## 获取配置

检索当前 Runicorn 配置。

### 请求

```http
GET /api/config
```

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "user_root_dir": "E:\\RunicornData",
  "storage": "E:\\RunicornData",
  "config_file": "C:\\Users\\username\\AppData\\Roaming\\Runicorn\\config.json",
  "version": "0.4.0"
}
```

### 示例

**Python**:
```python
import requests

config = requests.get('http://127.0.0.1:23300/api/config').json()

print(f"存储根目录: {config['storage']}")
print(f"配置文件: {config['config_file']}")
print(f"版本: {config['version']}")
```

---

## 设置用户根目录

配置全局存储根目录。

### 请求

```http
POST /api/config/user_root_dir
Content-Type: application/json
```

**请求体**:
```json
{
  "path": "E:\\RunicornData"
}
```

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "ok": true,
  "user_root_dir": "E:\\RunicornData",
  "storage": "E:\\RunicornData",
  "message": "User root directory updated successfully"
}
```

### 示例

**Python**:
```python
import requests

new_path = "E:\\MLExperiments\\RunicornData"

response = requests.post(
    'http://127.0.0.1:23300/api/config/user_root_dir',
    json={"path": new_path}
)

if response.status_code == 200:
    result = response.json()
    print(f"✓ 存储根目录已更新为: {result['storage']}")
else:
    error = response.json()
    print(f"✗ 错误: {error['detail']}")
```

---

## 获取已保存的 SSH 连接

检索已保存的 SSH 连接配置列表。

### 请求

```http
GET /api/config/ssh_connections
```

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "connections": [
    {
      "key": "user@192.168.1.100:22@user",
      "host": "192.168.1.100",
      "port": 22,
      "username": "user",
      "name": "实验室服务器",
      "auth_method": "password",
      "has_password": true,
      "has_private_key": false
    }
  ]
}
```

### 安全提示

> 🔒 **安全**: 密码和私钥在存储前会使用平台特定的凭据管理器**加密**。

---

## 保存 SSH 连接

保存新的 SSH 连接或更新现有连接。

### 请求

```http
POST /api/config/ssh_connections
Content-Type: application/json
```

**请求体**:
```json
{
  "host": "192.168.1.100",
  "port": 22,
  "username": "user",
  "name": "实验室服务器",
  "auth_method": "password",
  "remember_password": true,
  "password": "secret123"
}
```

### 示例

**Python**（密码认证）:
```python
import requests

connection = {
    "host": "192.168.1.100",
    "port": 22,
    "username": "user",
    "name": "实验室服务器",
    "auth_method": "password",
    "remember_password": True,
    "password": "secret123"
}

response = requests.post(
    'http://127.0.0.1:23300/api/config/ssh_connections',
    json=connection
)

result = response.json()
print(f"连接已保存: {result['key']}")
```

---

## 删除 SSH 连接

删除已保存的 SSH 连接。

### 请求

```http
DELETE /api/config/ssh_connections/{key}
```

### 示例

**Python**:
```python
import requests
from urllib.parse import quote

connection_key = "user@192.168.1.100:22@user"

response = requests.delete(
    f'http://127.0.0.1:23300/api/config/ssh_connections/{quote(connection_key)}'
)

result = response.json()
print(result['message'])
```

---

## 速率限制

| 端点 | 限制 | 窗口 |
|------|------|------|
| `GET /config` | 60 次请求 | 60 秒 |
| `POST /config/user_root_dir` | 10 次请求 | 60 秒 |
| `POST /config/ssh_connections` | 20 次请求 | 60 秒 |
| `DELETE /config/ssh_connections/{key}` | 20 次请求 | 60 秒 |

---

## CLI 替代方案

所有配置操作也可以通过 CLI 执行：

```bash
# 获取当前配置
runicorn config --show

# 设置用户根目录
runicorn config --set-user-root "E:\\RunicornData"
```

---

## 相关 API

- **SSH API**: 使用已保存的连接 - [ssh_api.md](ssh_api.md)
- **Runs API**: 配置运行存储 - [runs_api.md](runs_api.md)

---

**最后更新**: 2025-10-14

