[English](../en/ssh_api.md) | [简体中文](ssh_api.md)

---

# SSH/Remote API - 远程服务器同步

> ⚠️ **已弃用于 v0.5.0**
>
> 该 API 已被 **Remote Viewer API** 替代，后者提供更好的性能和用户体验。
>
> - **新 API**: [Remote API 文档](./remote_api.md)
> - **迁移指南**: [v0.4.x → v0.5.0 迁移指南](../../guides/zh/MIGRATION_GUIDE_v0.4_to_v0.5.md)
> - **维护状态**: 该 API 已弃用，目前仅为向后兼容而保留；暂未承诺具体移除版本
> - **推荐**: 立即迁移到 Remote Viewer API

**模块**: SSH/Remote API (**已弃用**)
**基础路径**: `/api/unified` (统一 API), `/api/ssh` (遗留)
**版本**: v1.0
**描述**: 通过 SSH 连接到远程 Linux 服务器并实时同步实验数据。

---

## 端点概览

### 统一 SSH API（推荐）

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/unified/connect` | 连接到远程服务器 |
| POST | `/unified/disconnect` | 断开远程服务器连接 |
| GET | `/unified/status` | 获取连接和同步状态 |
| GET | `/unified/listdir` | 浏览远程目录 |
| POST | `/unified/configure_mode` | 配置同步模式（smart/mirror）|
| POST | `/unified/deactivate_mode` | 停用同步模式 |

### 遗留 SSH API

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/ssh/connect` | 连接到 SSH 服务器 |
| GET | `/ssh/sessions` | 列出活动的 SSH 会话 |
| POST | `/ssh/close` | 关闭 SSH 会话 |
| GET | `/ssh/listdir` | 列出远程目录 |
| POST | `/ssh/mirror/start` | 启动镜像任务 |
| POST | `/ssh/mirror/stop` | 停止镜像任务 |
| GET | `/ssh/mirror/list` | 列出活动的镜像任务 |

---

## 连接到远程服务器

建立到远程服务器的 SSH 连接。

### 请求

```http
POST /api/unified/connect
Content-Type: application/json
```

**请求体**:
```json
{
  "host": "192.168.1.100",
  "port": 22,
  "username": "user",
  "password": "secret123",
  "use_agent": false
}
```

### 请求体 Schema

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `host` | string | 是 | 服务器主机名或 IP 地址 |
| `port` | number | 否 | SSH 端口（默认：22）|
| `username` | string | 是 | SSH 用户名 |
| `password` | string | 条件 | 密码（如果不使用密钥认证）|
| `private_key` | string | 条件 | 私钥内容（如果使用密钥认证）|
| `private_key_path` | string | 条件 | 私钥文件路径 |
| `passphrase` | string | 否 | 私钥密码 |
| `use_agent` | boolean | 否 | 使用 SSH agent（默认：true）|

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "ok": true,
  "status": "connected",
  "host": "192.168.1.100",
  "port": 22,
  "username": "user",
  "message": "Successfully connected to 192.168.1.100"
}
```

### 错误响应

**401 未授权**（认证失败）:
```json
{
  "detail": "Authentication failed: Invalid credentials"
}
```

**连接错误**:
```json
{
  "detail": "Connection failed: Connection timed out"
}
```

**速率限制**（每分钟 5 次尝试）:
```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 45
}
```

### 示例

**示例 1**: 密码认证
```python
import requests

response = requests.post('http://127.0.0.1:23300/api/unified/connect', json={
    "host": "192.168.1.100",
    "port": 22,
    "username": "user",
    "password": "secret123",
    "use_agent": False
})

if response.status_code == 200:
    result = response.json()
    print(f"✓ 已连接到 {result['host']}")
else:
    error = response.json()
    print(f"✗ 连接失败: {error['detail']}")
```

**示例 2**: 私钥认证
```python
import requests

# 读取私钥
with open('/path/to/id_rsa', 'r') as f:
    private_key = f.read()

response = requests.post('http://127.0.0.1:23300/api/unified/connect', json={
    "host": "gpu-server.com",
    "port": 22,
    "username": "admin",
    "private_key": private_key,
    "passphrase": "key_password",  # 如果密钥已加密
    "use_agent": False
})

result = response.json()
print(result['message'])
```

**示例 3**: SSH agent 认证（最安全）
```python
import requests

# 不需要密码或密钥 - 使用 SSH agent
response = requests.post('http://127.0.0.1:23300/api/unified/connect', json={
    "host": "secure-server.com",
    "port": 22,
    "username": "user",
    "use_agent": True  # 使用 SSH agent
})

result = response.json()
print(result['message'])
```

---

## 获取连接状态

检查当前 SSH 连接和同步状态。

### 请求

```http
GET /api/unified/status
```

### 响应

**状态码**: `200 OK`

**响应体**（已连接并启用智能模式）:
```json
{
  "connection": {
    "connected": true,
    "host": "192.168.1.100",
    "port": 22,
    "username": "user",
    "uptime_seconds": 3600
  },
  "smart_mode": {
    "active": true,
    "remote_root": "/data/runicorn",
    "auto_sync": true,
    "sync_interval_minutes": 5,
    "last_sync_at": 1704067200.0,
    "next_sync_at": 1704067500.0
  },
  "mirror_mode": {
    "active": false
  },
  "cached_experiments": 127,
  "cached_artifacts": 43
}
```

**响应体**（未连接）:
```json
{
  "connection": {
    "connected": false
  },
  "smart_mode": {
    "active": false
  },
  "mirror_mode": {
    "active": false
  }
}
```

---

## 浏览远程目录

列出远程服务器上的文件和目录。

### 请求

```http
GET /api/unified/listdir?path={path}
```

**查询参数**:
| 参数 | 类型 | 必需 | 默认值 | 描述 |
|------|------|------|---------|------|
| `path` | string | 否 | `~` | 要列出的远程路径（空 = 主目录）|

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "ok": true,
  "current_path": "/data/runicorn",
  "items": [
    {
      "name": "image_classification",
      "path": "/data/runicorn/image_classification",
      "type": "dir",
      "size": 0,
      "mtime": 1704067200
    },
    {
      "name": "nlp",
      "path": "/data/runicorn/nlp",
      "type": "dir",
      "size": 0,
      "mtime": 1704053400
    },
    {
      "name": "archive",
      "path": "/data/runicorn/archive",
      "type": "dir",
      "size": 0,
      "mtime": 1704024000
    }
  ]
}
```

### 示例

**Python** (目录浏览器):
```python
import requests

def browse_remote(path=""):
    """浏览远程目录"""
    response = requests.get(
        'http://127.0.0.1:23300/api/unified/listdir',
        params={'path': path}
    )

    data = response.json()

    print(f"\n当前: {data['current_path']}")
    print("-" * 60)

    for item in sorted(data['items'], key=lambda x: (x['type'] != 'dir', x['name'])):
        icon = "📁" if item['type'] == 'dir' else "📄"
        size = f"{item['size']:,} bytes" if item['type'] == 'file' else ""
        print(f"{icon} {item['name']:<40} {size}")

    return data['items']

# 使用
items = browse_remote("/data/runicorn")

# 导航到子目录
subdirs = [item for item in items if item['type'] == 'dir']
if subdirs:
    browse_remote(subdirs[0]['path'])
```

---

## 配置同步模式

配置远程同步模式。

### 请求

```http
POST /api/unified/configure_mode
Content-Type: application/json
```

**请求体**（智能模式）:
```json
{
  "mode": "smart",
  "remote_root": "/data/runicorn",
  "auto_sync": true,
  "sync_interval_minutes": 5
}
```

**请求体**（镜像模式）:
```json
{
  "mode": "mirror",
  "remote_root": "/data/runicorn",
  "mirror_interval": 2.0
}
```

### 请求体 Schema

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `mode` | string | 是 | `smart` 或 `mirror` |
| `remote_root` | string | 是 | 远程存储根路径 |
| `auto_sync` | boolean | 否 | 启用自动同步（仅智能模式）|
| `sync_interval_minutes` | number | 否 | 同步间隔（分钟）（默认：5）|
| `mirror_interval` | number | 否 | 镜像扫描间隔（秒）（默认：2.0）|

### 同步模式说明

**智能模式**（推荐）:
- 仅同步元数据（快）
- 按需下载文件
- 适合大数据集
- 较低带宽使用

**镜像模式**（实时）:
- 完整文件同步
- 实时镜像
- 较高带宽使用
- 适合活跃开发

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "ok": true,
  "mode": "smart",
  "message": "Smart mode configured successfully",
  "config": {
    "remote_root": "/data/runicorn",
    "auto_sync": true,
    "sync_interval_minutes": 5
  }
}
```

### 示例

**Python**:
```python
import requests

# 配置智能模式
response = requests.post('http://127.0.0.1:23300/api/unified/configure_mode', json={
    "mode": "smart",
    "remote_root": "/data/runicorn",
    "auto_sync": True,
    "sync_interval_minutes": 5
})

result = response.json()
print(result['message'])

# 检查状态
status = requests.get('http://127.0.0.1:23300/api/unified/status').json()
print(f"智能模式已激活: {status['smart_mode']['active']}")
print(f"下次同步: {status['smart_mode']['next_sync_at']}")
```

---

## 完整工作流示例

### 场景: 将远程训练同步到本地查看器

```python
import requests
import time

BASE_URL = "http://127.0.0.1:23300/api"

# 步骤 1: 连接到远程服务器
print("1. 连接到远程服务器...")
conn_response = requests.post(f"{BASE_URL}/unified/connect", json={
    "host": "gpu-server.local",
    "port": 22,
    "username": "researcher",
    "password": "secret",
    "use_agent": False
})

if conn_response.status_code != 200:
    print(f"✗ 连接失败: {conn_response.json()['detail']}")
    exit(1)

print("✓ 已连接")

# 步骤 2: 浏览以查找 runicorn 根目录
print("\n2. 浏览远程目录...")
listdir_response = requests.get(f"{BASE_URL}/unified/listdir", params={"path": "/data"})
items = listdir_response.json()['items']

for item in items:
    if item['type'] == 'dir':
        print(f"  📁 {item['name']}")

# 步骤 3: 配置智能同步
print("\n3. 配置智能同步模式...")
mode_response = requests.post(f"{BASE_URL}/unified/configure_mode", json={
    "mode": "smart",
    "remote_root": "/data/runicorn",
    "auto_sync": True,
    "sync_interval_minutes": 5
})

print("✓ 智能模式已激活")

# 步骤 4: 等待首次同步
print("\n4. 等待同步...")
time.sleep(10)

# 步骤 5: 检查状态
status_response = requests.get(f"{BASE_URL}/unified/status")
status = status_response.json()

print(f"✓ 已缓存实验: {status['cached_experiments']}")
print(f"✓ 已缓存 artifacts: {status['cached_artifacts']}")

# 步骤 6: 查询实验（现在本地可用）
print("\n5. 查询已同步的实验...")
runs_response = requests.get(f"{BASE_URL}/runs")
runs = runs_response.json()

print(f"✓ 找到 {len(runs)} 个实验")
for run in runs[:5]:
    print(f"  - {run['id']}: {run['project']}/{run['name']}")

# 步骤 7: 完成后断开连接
print("\n6. 断开连接...")
disconnect_response = requests.post(f"{BASE_URL}/unified/disconnect")
print("✓ 已断开连接")
```

---

## 安全最佳实践

### 1. 使用 SSH 密钥而非密码

```python
# ✅ 好: SSH 密钥认证
with open('~/.ssh/id_rsa', 'r') as f:
    private_key = f.read()

response = requests.post('/api/unified/connect', json={
    "host": "server.com",
    "username": "user",
    "private_key": private_key,
    "use_agent": False
})

# ❌ 避免: 硬编码密码
response = requests.post('/api/unified/connect', json={
    "host": "server.com",
    "username": "user",
    "password": "hardcoded_password"  # 安全风险！
})
```

### 2. 使用 SSH Agent（最安全）

```python
# ✅ 最佳: SSH agent（代码中无凭据）
response = requests.post('/api/unified/connect', json={
    "host": "server.com",
    "username": "user",
    "use_agent": True  # 使用系统 SSH agent
})

# 首先将密钥添加到 SSH agent:
# ssh-add ~/.ssh/id_rsa
```

### 3. 永远不要记录凭据

```python
import requests
import logging

connection_config = {
    "host": "server.com",
    "username": "user",
    "password": "secret"
}

# ❌ 差: 记录密码
logging.info(f"Connecting with config: {connection_config}")

# ✅ 好: 隐去敏感数据
safe_config = {k: v for k, v in connection_config.items() if k not in ['password', 'private_key']}
logging.info(f"Connecting with config: {safe_config}")
```

---

## 同步模式对比

### 智能模式

**最适合**: 大数据集，有限带宽

**工作原理**:
1. 仅同步元数据（JSON 文件，~KB）
2. 按需下载文件
3. 下载后本地缓存

**优点**:
- ✅ 快速初始同步（秒级）
- ✅ 低带宽使用
- ✅ 对大文件高效

**缺点**:
- ⚠️ 文件不立即可用
- ⚠️ 查看前需要下载

**用例**: 生产环境，查看历史实验

### 镜像模式

**最适合**: 活跃开发，实时监控

**工作原理**:
1. 完整文件同步
2. 每 2 秒增量更新
3. 实时日志跟踪

**优点**:
- ✅ 所有文件立即可用
- ✅ 实时更新
- ✅ 无需下载

**缺点**:
- ⚠️ 初始同步较慢（分钟到小时）
- ⚠️ 较高带宽使用
- ⚠️ 需要稳定连接

**用例**: 监控正在进行的训练，调试

---

## 错误码

| 状态码 | 场景 | 解决方案 |
|--------|------|----------|
| `400` | 无效凭据 | 检查用户名/密码 |
| `401` | 认证失败 | 验证凭据，检查 SSH 密钥 |
| `404` | 远程路径未找到 | 验证 remote_root 路径 |
| `408` | 连接超时 | 检查网络，防火墙规则 |
| `429` | 超过速率限制 | 重试前等待（最多 5 次尝试/分钟）|
| `500` | SSH 错误 | 检查服务器 SSH 配置 |

---

## 监控连接

### 健康检查循环

```python
import requests
import time

def monitor_connection(check_interval=30):
    """监控 SSH 连接健康状况"""

    while True:
        try:
            response = requests.get('http://127.0.0.1:23300/api/unified/status', timeout=5)
            status = response.json()

            if status['connection']['connected']:
                uptime = status['connection']['uptime_seconds']
                cached = status.get('cached_experiments', 0)
                print(f"✓ 已连接（运行时间: {uptime}秒，已缓存: {cached} 个实验）")
            else:
                print("✗ 未连接")
                break

        except Exception as e:
            print(f"✗ 健康检查失败: {e}")
            break

        time.sleep(check_interval)

# 使用
monitor_connection(check_interval=30)
```

---

## 数据模型

### ConnectionStatus

```typescript
interface ConnectionStatus {
  connected: boolean
  host?: string
  port?: number
  username?: string
  uptime_seconds?: number
}
```

### SmartModeConfig

```typescript
interface SmartModeConfig {
  active: boolean
  remote_root?: string
  auto_sync?: boolean
  sync_interval_minutes?: number
  last_sync_at?: number
  next_sync_at?: number
}
```

### RemoteDirectoryItem

```typescript
interface RemoteDirectoryItem {
  name: string
  path: string
  type: "dir" | "file" | "unknown"
  size: number        // 字节（目录为 0）
  mtime: number       // Unix 时间戳
}
```

---

## 速率限制

SSH 操作受速率限制以防止暴力破解攻击：

| 端点 | 限制 | 窗口 | 原因 |
|------|------|------|------|
| `/unified/connect` | 5 次请求 | 60 秒 | 防止暴力破解 |
| `/unified/listdir` | 30 次请求 | 60 秒 | 防止服务器负载 |
| `/unified/configure_mode` | 10 次请求 | 60 秒 | 防止滥用 |

---

## 故障排查

### 连接问题

**问题**: "Connection timed out"

**解决方案**:
1. 检查网络连接: `ping {host}`
2. 验证 SSH 端口可访问: `telnet {host} 22`
3. 检查防火墙规则
4. 尝试增加超时时间（未来功能）

**问题**: "Authentication failed"

**解决方案**:
1. 验证凭据
2. 检查 SSH 密钥权限: `chmod 600 ~/.ssh/id_rsa`
3. 验证 SSH 服务器允许密码/密钥认证
4. 检查服务器上的 `/var/log/auth.log`

**问题**: "Host key verification failed"

**解决方案**:
1. Runicorn 自动接受新的主机密钥
2. 如果问题仍然存在，清除 `~/.ssh/known_hosts`
3. 检查服务器 SSH 配置

### 同步问题

**问题**: "同步后没有实验出现"

**诊断**:
```python
import requests

# 检查连接
status = requests.get('http://127.0.0.1:23300/api/unified/status').json()

if not status['connection']['connected']:
    print("✗ 未连接到远程")
elif not status['smart_mode']['active']:
    print("✗ 智能模式未激活")
else:
    print(f"✓ 已连接，已缓存 {status['cached_experiments']} 个实验")

    # 检查 remote_root 是否正确
    listdir = requests.get('/api/unified/listdir', params={'path': status['smart_mode']['remote_root']}).json()
    print(f"远程根目录内容: {[item['name'] for item in listdir['items']]}")
```

---

## 相关 API

- **Config API**: 保存 SSH 连接 - [config_api.md](./config_api.md)
- **Runs API**: 查询已同步的实验 - [runs_api.md](./runs_api.md)
- **Remote Viewer API**: 使用当前的远程会话工作流 - [remote_api.md](./remote_api.md)

---

**最后更新**: 2026-03-28


