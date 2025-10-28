[English](ssh_api.md) | [简体中文](../zh/ssh_api.md)

---

# SSH/Remote API - Remote Server Synchronization

> ⚠️ **Deprecated in v0.5.0**
> 
> This API has been replaced by **Remote Viewer API**, which provides better performance and user experience.
> 
> - **New API**: [Remote API Documentation](./remote_api.md)
> - **Migration Guide**: [v0.4.x → v0.5.0 Migration Guide](../../guides/en/MIGRATION_GUIDE_v0.4_to_v0.5.md)
> - **Maintenance Status**: This API will be removed in v0.6.0
> - **Recommendation**: Migrate to Remote Viewer API immediately

**Module**: SSH/Remote API (**Deprecated**)  
**Base Path**: `/api/unified` (Unified API), `/api/ssh` (Legacy)  
**Version**: v1.0  
**Description**: Connect to remote Linux servers via SSH and synchronize experiment data in real-time.

---

## Endpoints Overview

### Unified SSH API (Recommended)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/unified/connect` | Connect to remote server |
| POST | `/unified/disconnect` | Disconnect from remote server |
| GET | `/unified/status` | Get connection and sync status |
| GET | `/unified/listdir` | Browse remote directories |
| POST | `/unified/configure_mode` | Configure sync mode (smart/mirror) |
| POST | `/unified/deactivate_mode` | Deactivate sync mode |

### Legacy SSH API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ssh/connect` | Connect to SSH server |
| GET | `/ssh/sessions` | List active SSH sessions |
| POST | `/ssh/close` | Close SSH session |
| GET | `/ssh/listdir` | List remote directory |
| POST | `/ssh/mirror/start` | Start mirror task |
| POST | `/ssh/mirror/stop` | Stop mirror task |
| GET | `/ssh/mirror/list` | List active mirror tasks |

---

## Connect to Remote Server

Establish SSH connection to remote server.

### Request

```http
POST /api/unified/connect
Content-Type: application/json
```

**Request Body**:
```json
{
  "host": "192.168.1.100",
  "port": 22,
  "username": "user",
  "password": "secret123",
  "use_agent": false
}
```

### Request Body Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `host` | string | Yes | Server hostname or IP address |
| `port` | number | No | SSH port (default: 22) |
| `username` | string | Yes | SSH username |
| `password` | string | Conditional | Password (if not using key auth) |
| `private_key` | string | Conditional | Private key content (if using key auth) |
| `private_key_path` | string | Conditional | Path to private key file |
| `passphrase` | string | No | Private key passphrase |
| `use_agent` | boolean | No | Use SSH agent (default: true) |

### Response

**Status Code**: `200 OK`

**Response Body**:
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

### Error Responses

**401 Unauthorized** (authentication failed):
```json
{
  "detail": "Authentication failed: Invalid credentials"
}
```

**Connection errors**:
```json
{
  "detail": "Connection failed: Connection timed out"
}
```

**Rate limit** (5 attempts per minute):
```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 45
}
```

### Examples

**Example 1**: Password authentication
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
    print(f"✓ Connected to {result['host']}")
else:
    error = response.json()
    print(f"✗ Connection failed: {error['detail']}")
```

**Example 2**: Private key authentication
```python
import requests

# Read private key
with open('/path/to/id_rsa', 'r') as f:
    private_key = f.read()

response = requests.post('http://127.0.0.1:23300/api/unified/connect', json={
    "host": "gpu-server.com",
    "port": 22,
    "username": "admin",
    "private_key": private_key,
    "passphrase": "key_password",  # If key is encrypted
    "use_agent": False
})

result = response.json()
print(result['message'])
```

**Example 3**: SSH agent authentication (most secure)
```python
import requests

# No password or key needed - uses SSH agent
response = requests.post('http://127.0.0.1:23300/api/unified/connect', json={
    "host": "secure-server.com",
    "port": 22,
    "username": "user",
    "use_agent": True  # Use SSH agent
})

result = response.json()
print(result['message'])
```

---

## Get Connection Status

Check current SSH connection and sync status.

### Request

```http
GET /api/unified/status
```

### Response

**Status Code**: `200 OK`

**Response Body** (connected with smart mode):
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

**Response Body** (not connected):
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

## Browse Remote Directory

List files and directories on remote server.

### Request

```http
GET /api/unified/listdir?path={path}
```

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | string | No | `~` | Remote path to list (empty = home directory) |

### Response

**Status Code**: `200 OK`

**Response Body**:
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
      "name": "artifacts",
      "path": "/data/runicorn/artifacts",
      "type": "dir",
      "size": 0,
      "mtime": 1704024000
    }
  ]
}
```

### Example

**Python** (directory browser):
```python
import requests

def browse_remote(path=""):
    """Browse remote directory"""
    response = requests.get(
        'http://127.0.0.1:23300/api/unified/listdir',
        params={'path': path}
    )
    
    data = response.json()
    
    print(f"\nCurrent: {data['current_path']}")
    print("-" * 60)
    
    for item in sorted(data['items'], key=lambda x: (x['type'] != 'dir', x['name'])):
        icon = "📁" if item['type'] == 'dir' else "📄"
        size = f"{item['size']:,} bytes" if item['type'] == 'file' else ""
        print(f"{icon} {item['name']:<40} {size}")
    
    return data['items']

# Usage
items = browse_remote("/data/runicorn")

# Navigate to subdirectory
subdirs = [item for item in items if item['type'] == 'dir']
if subdirs:
    browse_remote(subdirs[0]['path'])
```

---

## Configure Sync Mode

Configure remote synchronization mode.

### Request

```http
POST /api/unified/configure_mode
Content-Type: application/json
```

**Request Body** (Smart Mode):
```json
{
  "mode": "smart",
  "remote_root": "/data/runicorn",
  "auto_sync": true,
  "sync_interval_minutes": 5
}
```

**Request Body** (Mirror Mode):
```json
{
  "mode": "mirror",
  "remote_root": "/data/runicorn",
  "mirror_interval": 2.0
}
```

### Request Body Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | `smart` or `mirror` |
| `remote_root` | string | Yes | Remote storage root path |
| `auto_sync` | boolean | No | Enable automatic sync (smart mode only) |
| `sync_interval_minutes` | number | No | Sync interval in minutes (default: 5) |
| `mirror_interval` | number | No | Mirror scan interval in seconds (default: 2.0) |

### Sync Modes Explained

**Smart Mode** (Recommended):
- Metadata-only sync (fast)
- On-demand file download
- Suitable for large datasets
- Lower bandwidth usage

**Mirror Mode** (Real-time):
- Full file synchronization
- Real-time mirroring
- Higher bandwidth usage
- Suitable for active development

### Response

**Status Code**: `200 OK`

**Response Body**:
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

### Example

**Python**:
```python
import requests

# Configure smart mode
response = requests.post('http://127.0.0.1:23300/api/unified/configure_mode', json={
    "mode": "smart",
    "remote_root": "/data/runicorn",
    "auto_sync": True,
    "sync_interval_minutes": 5
})

result = response.json()
print(result['message'])

# Check status
status = requests.get('http://127.0.0.1:23300/api/unified/status').json()
print(f"Smart mode active: {status['smart_mode']['active']}")
print(f"Next sync: {status['smart_mode']['next_sync_at']}")
```

---

## Complete Workflow Example

### Scenario: Sync Remote Training to Local Viewer

```python
import requests
import time

BASE_URL = "http://127.0.0.1:23300/api"

# Step 1: Connect to remote server
print("1. Connecting to remote server...")
conn_response = requests.post(f"{BASE_URL}/unified/connect", json={
    "host": "gpu-server.local",
    "port": 22,
    "username": "researcher",
    "password": "secret",
    "use_agent": False
})

if conn_response.status_code != 200:
    print(f"✗ Connection failed: {conn_response.json()['detail']}")
    exit(1)

print("✓ Connected")

# Step 2: Browse to find runicorn root
print("\n2. Browsing remote directories...")
listdir_response = requests.get(f"{BASE_URL}/unified/listdir", params={"path": "/data"})
items = listdir_response.json()['items']

for item in items:
    if item['type'] == 'dir':
        print(f"  📁 {item['name']}")

# Step 3: Configure smart sync
print("\n3. Configuring smart sync mode...")
mode_response = requests.post(f"{BASE_URL}/unified/configure_mode", json={
    "mode": "smart",
    "remote_root": "/data/runicorn",
    "auto_sync": True,
    "sync_interval_minutes": 5
})

print("✓ Smart mode activated")

# Step 4: Wait for first sync
print("\n4. Waiting for synchronization...")
time.sleep(10)

# Step 5: Check status
status_response = requests.get(f"{BASE_URL}/unified/status")
status = status_response.json()

print(f"✓ Cached experiments: {status['cached_experiments']}")
print(f"✓ Cached artifacts: {status['cached_artifacts']}")

# Step 6: Query experiments (now available locally)
print("\n5. Querying synchronized experiments...")
runs_response = requests.get(f"{BASE_URL}/runs")
runs = runs_response.json()

print(f"✓ Found {len(runs)} experiments")
for run in runs[:5]:
    print(f"  - {run['id']}: {run['project']}/{run['name']}")

# Step 7: Disconnect when done
print("\n6. Disconnecting...")
disconnect_response = requests.post(f"{BASE_URL}/unified/disconnect")
print("✓ Disconnected")
```

---

## Security Best Practices

### 1. Use SSH Keys Instead of Passwords

```python
# ✅ Good: SSH key authentication
with open('~/.ssh/id_rsa', 'r') as f:
    private_key = f.read()

response = requests.post('/api/unified/connect', json={
    "host": "server.com",
    "username": "user",
    "private_key": private_key,
    "use_agent": False
})

# ❌ Avoid: Hardcoded passwords
response = requests.post('/api/unified/connect', json={
    "host": "server.com",
    "username": "user",
    "password": "hardcoded_password"  # Security risk!
})
```

### 2. Use SSH Agent (Most Secure)

```python
# ✅ Best: SSH agent (no credentials in code)
response = requests.post('/api/unified/connect', json={
    "host": "server.com",
    "username": "user",
    "use_agent": True  # Uses system SSH agent
})

# Add your key to SSH agent first:
# ssh-add ~/.ssh/id_rsa
```

### 3. Never Log Credentials

```python
import requests
import logging

connection_config = {
    "host": "server.com",
    "username": "user",
    "password": "secret"
}

# ❌ Bad: Logs password
logging.info(f"Connecting with config: {connection_config}")

# ✅ Good: Redact sensitive data
safe_config = {k: v for k, v in connection_config.items() if k not in ['password', 'private_key']}
logging.info(f"Connecting with config: {safe_config}")
```

---

## Sync Modes Comparison

### Smart Mode

**Best for**: Large datasets, limited bandwidth

**How it works**:
1. Sync metadata only (JSON files, ~KB)
2. Files downloaded on-demand
3. Cache locally after download

**Advantages**:
- ✅ Fast initial sync (seconds)
- ✅ Low bandwidth usage
- ✅ Efficient for large files

**Disadvantages**:
- ⚠️ Files not immediately available
- ⚠️ Requires download before viewing

**Use case**: Production environment, viewing historical experiments

### Mirror Mode

**Best for**: Active development, real-time monitoring

**How it works**:
1. Full synchronization of all files
2. Incremental updates every 2 seconds
3. Real-time tailing of logs

**Advantages**:
- ✅ All files immediately available
- ✅ Real-time updates
- ✅ No download needed

**Disadvantages**:
- ⚠️ Slower initial sync (minutes to hours)
- ⚠️ Higher bandwidth usage
- ⚠️ Requires stable connection

**Use case**: Monitoring training in progress, debugging

---

## Error Codes

| Status Code | Scenario | Solution |
|-------------|----------|----------|
| `400` | Invalid credentials | Check username/password |
| `401` | Authentication failed | Verify credentials, check SSH key |
| `404` | Remote path not found | Verify remote_root path |
| `408` | Connection timeout | Check network, firewall rules |
| `429` | Rate limit exceeded | Wait before retrying (max 5 attempts/min) |
| `500` | SSH error | Check server SSH configuration |

---

## Monitoring Connection

### Health Check Loop

```python
import requests
import time

def monitor_connection(check_interval=30):
    """Monitor SSH connection health"""
    
    while True:
        try:
            response = requests.get('http://127.0.0.1:23300/api/unified/status', timeout=5)
            status = response.json()
            
            if status['connection']['connected']:
                uptime = status['connection']['uptime_seconds']
                cached = status.get('cached_experiments', 0)
                print(f"✓ Connected (uptime: {uptime}s, cached: {cached} experiments)")
            else:
                print("✗ Not connected")
                break
                
        except Exception as e:
            print(f"✗ Health check failed: {e}")
            break
        
        time.sleep(check_interval)

# Usage
monitor_connection(check_interval=30)
```

---

## Data Models

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
  size: number        // Bytes (0 for directories)
  mtime: number       // Unix timestamp
}
```

---

## Rate Limits

SSH operations are rate-limited to prevent brute-force attacks:

| Endpoint | Limit | Window | Reason |
|----------|-------|--------|--------|
| `/unified/connect` | 5 requests | 60 seconds | Prevent brute-force |
| `/unified/listdir` | 30 requests | 60 seconds | Prevent server load |
| `/unified/configure_mode` | 10 requests | 60 seconds | Prevent abuse |

---

## Troubleshooting

### Connection Issues

**Problem**: "Connection timed out"

**Solutions**:
1. Check network connectivity: `ping {host}`
2. Verify SSH port is accessible: `telnet {host} 22`
3. Check firewall rules
4. Try increasing timeout (future feature)

**Problem**: "Authentication failed"

**Solutions**:
1. Verify credentials
2. Check SSH key permissions: `chmod 600 ~/.ssh/id_rsa`
3. Verify SSH server allows password/key auth
4. Check `/var/log/auth.log` on server

**Problem**: "Host key verification failed"

**Solutions**:
1. Runicorn auto-accepts new host keys
2. If issue persists, clear `~/.ssh/known_hosts`
3. Check server SSH configuration

### Sync Issues

**Problem**: "No experiments appear after sync"

**Diagnostics**:
```python
import requests

# Check connection
status = requests.get('http://127.0.0.1:23300/api/unified/status').json()

if not status['connection']['connected']:
    print("✗ Not connected to remote")
elif not status['smart_mode']['active']:
    print("✗ Smart mode not active")
else:
    print(f"✓ Connected, cached {status['cached_experiments']} experiments")
    
    # Check if remote_root is correct
    listdir = requests.get('/api/unified/listdir', params={'path': status['smart_mode']['remote_root']}).json()
    print(f"Remote root contents: {[item['name'] for item in listdir['items']]}")
```

---

## Related APIs

- **Config API**: Save SSH connections - [config_api.md](./config_api.md)
- **Runs API**: Query synced experiments - [runs_api.md](./runs_api.md)
- **Artifacts API**: Access remote artifacts - [artifacts_api.md](./artifacts_api.md)

---

**Last Updated**: 2025-10-14

