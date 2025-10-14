[English](config_api.md) | [简体中文](../zh/config_api.md)

---

# Config API - Configuration Management

**Module**: Config API  
**Base Path**: `/api/config`  
**Version**: v1.0  
**Description**: Manage Runicorn configuration including storage paths and SSH connections.

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/config` | Get current configuration |
| POST | `/config/user_root_dir` | Set user root directory |
| GET | `/config/ssh_connections` | Get saved SSH connections |
| POST | `/config/ssh_connections` | Save SSH connection |
| DELETE | `/config/ssh_connections/{key}` | Delete SSH connection |
| GET | `/config/ssh_connections/{key}/details` | Get connection details |

---

## Get Configuration

Retrieve current Runicorn configuration.

### Request

```http
GET /api/config
```

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "user_root_dir": "E:\\RunicornData",
  "storage": "E:\\RunicornData",
  "config_file": "C:\\Users\\username\\AppData\\Roaming\\Runicorn\\config.json",
  "version": "0.4.0"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `user_root_dir` | string | User-configured storage root directory |
| `storage` | string | Effective storage path (resolved) |
| `config_file` | string | Path to configuration file |
| `version` | string | Runicorn version |

### Example

**cURL**:
```bash
curl http://127.0.0.1:23300/api/config
```

**Python**:
```python
import requests

config = requests.get('http://127.0.0.1:23300/api/config').json()

print(f"Storage root: {config['storage']}")
print(f"Config file: {config['config_file']}")
print(f"Version: {config['version']}")
```

---

## Set User Root Directory

Configure the global storage root directory.

### Request

```http
POST /api/config/user_root_dir
Content-Type: application/json
```

**Request Body**:
```json
{
  "path": "E:\\RunicornData"
}
```

### Request Body Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | string | Yes | Absolute path to storage directory |

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "ok": true,
  "user_root_dir": "E:\\RunicornData",
  "storage": "E:\\RunicornData",
  "message": "User root directory updated successfully"
}
```

### Error Responses

**400 Bad Request** (invalid path):
```json
{
  "detail": "Invalid path: Path does not exist or is not writable"
}
```

### Example

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
    print(f"✓ Storage root updated to: {result['storage']}")
else:
    error = response.json()
    print(f"✗ Error: {error['detail']}")
```

**JavaScript**:
```javascript
async function setStorageRoot(path) {
  try {
    const response = await fetch('http://127.0.0.1:23300/api/config/user_root_dir', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail)
    }
    
    const result = await response.json()
    console.log(`Storage updated: ${result.storage}`)
    
    // Reload page to reflect changes
    window.location.reload()
    
  } catch (error) {
    console.error('Failed to update storage root:', error.message)
  }
}

// Usage
setStorageRoot("E:\\RunicornData")
```

---

## Get Saved SSH Connections

Retrieve list of saved SSH connection configurations.

### Request

```http
GET /api/config/ssh_connections
```

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "connections": [
    {
      "key": "user@192.168.1.100:22@user",
      "host": "192.168.1.100",
      "port": 22,
      "username": "user",
      "name": "Lab Server",
      "auth_method": "password",
      "has_password": true,
      "has_private_key": false
    },
    {
      "key": "admin@gpu-server.com:22@admin",
      "host": "gpu-server.com",
      "port": 22,
      "username": "admin",
      "name": "GPU Cluster",
      "auth_method": "key",
      "has_password": false,
      "has_private_key": true,
      "private_key_path": "~/.ssh/id_rsa"
    }
  ]
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Unique connection identifier |
| `host` | string | Server hostname or IP |
| `port` | number | SSH port |
| `username` | string | SSH username |
| `name` | string | User-friendly connection name |
| `auth_method` | string | `password`, `key`, or `agent` |
| `has_password` | boolean | Whether password is saved |
| `has_private_key` | boolean | Whether private key is saved |
| `private_key_path` | string | Path to private key file (if used) |

### Security Note

> 🔒 **Security**: Passwords and private keys are **encrypted** before storage using platform-specific credential managers.

---

## Save SSH Connection

Save a new SSH connection or update existing one.

### Request

```http
POST /api/config/ssh_connections
Content-Type: application/json
```

**Request Body**:
```json
{
  "host": "192.168.1.100",
  "port": 22,
  "username": "user",
  "name": "Lab Server",
  "auth_method": "password",
  "remember_password": true,
  "password": "secret123"
}
```

### Request Body Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `host` | string | Yes | Server hostname or IP address |
| `port` | number | No | SSH port (default: 22) |
| `username` | string | Yes | SSH username |
| `name` | string | No | User-friendly name |
| `auth_method` | string | Yes | `password`, `key`, or `agent` |
| `remember_password` | boolean | No | Whether to save password |
| `password` | string | Conditional | Required if auth_method=password |
| `private_key` | string | Conditional | Private key content (if auth_method=key) |
| `private_key_path` | string | Conditional | Path to private key file |
| `passphrase` | string | No | Private key passphrase |

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "ok": true,
  "message": "SSH connection saved successfully",
  "key": "user@192.168.1.100:22@user"
}
```

### Example

**Python** (password auth):
```python
import requests

connection = {
    "host": "192.168.1.100",
    "port": 22,
    "username": "user",
    "name": "Lab Server",
    "auth_method": "password",
    "remember_password": True,
    "password": "secret123"
}

response = requests.post(
    'http://127.0.0.1:23300/api/config/ssh_connections',
    json=connection
)

result = response.json()
print(f"Connection saved: {result['key']}")
```

**Python** (key auth):
```python
import requests

# Read private key
with open('/path/to/id_rsa', 'r') as f:
    private_key_content = f.read()

connection = {
    "host": "gpu-server.com",
    "port": 22,
    "username": "admin",
    "name": "GPU Cluster",
    "auth_method": "key",
    "private_key": private_key_content,
    "passphrase": "key_password"  # If key is encrypted
}

response = requests.post(
    'http://127.0.0.1:23300/api/config/ssh_connections',
    json=connection
)

if response.status_code == 200:
    print("✓ SSH connection saved")
else:
    print(f"✗ Error: {response.json()['detail']}")
```

---

## Delete SSH Connection

Remove a saved SSH connection.

### Request

```http
DELETE /api/config/ssh_connections/{key}
```

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `key` | string | Yes | Connection key (URL encoded) |

### Response

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "ok": true,
  "message": "SSH connection deleted successfully"
}
```

### Example

**Python**:
```python
import requests
from urllib.parse import quote

# Key from GET /config/ssh_connections
connection_key = "user@192.168.1.100:22@user"

response = requests.delete(
    f'http://127.0.0.1:23300/api/config/ssh_connections/{quote(connection_key)}'
)

result = response.json()
print(result['message'])
```

---

## Configuration File

### Location

Configuration is stored in platform-specific locations:

- **Windows**: `%APPDATA%\Runicorn\config.json`
- **macOS**: `~/Library/Application Support/Runicorn/config.json`
- **Linux**: `~/.config/runicorn/config.json`

### File Structure

```json
{
  "user_root_dir": "E:\\RunicornData",
  "ssh_connections": [
    {
      "encrypted_password": "gAAAAABl...",
      "key": "user@192.168.1.100:22@user",
      "host": "192.168.1.100",
      "port": 22,
      "username": "user"
    }
  ]
}
```

### Manual Editing

> ⚠️ **Warning**: Manually editing `config.json` is **not recommended**. Use the API or CLI instead.

**If you must edit manually**:
1. Stop the Runicorn viewer
2. Edit the file
3. Restart the viewer
4. Verify with `GET /api/config`

---

## Storage Root Priority

Runicorn determines storage root in this order:

```
1. runicorn.init(storage="E:\\CustomPath")  # Highest priority
   ↓
2. Environment variable: RUNICORN_DIR
   ↓
3. User config: user_root_dir (set via API/CLI)
   ↓
4. Legacy default: ./.runicorn/  # Lowest priority
```

### Example

**Python**:
```python
import os
import runicorn as rn

# Method 1: Explicit parameter (highest priority)
run = rn.init(project="demo", storage="E:\\CustomPath")

# Method 2: Environment variable
os.environ['RUNICORN_DIR'] = "E:\\CustomPath"
run = rn.init(project="demo")

# Method 3: User config (via API)
import requests
requests.post('http://127.0.0.1:23300/api/config/user_root_dir', 
              json={"path": "E:\\CustomPath"})
run = rn.init(project="demo")

# Method 4: Default (legacy)
run = rn.init(project="demo")  # Uses ./.runicorn/
```

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `GET /config` | 60 requests | 60 seconds |
| `POST /config/user_root_dir` | 10 requests | 60 seconds |
| `POST /config/ssh_connections` | 20 requests | 60 seconds |
| `DELETE /config/ssh_connections/{key}` | 20 requests | 60 seconds |

---

## CLI Alternative

All configuration operations can also be performed via CLI:

```bash
# Get current config
runicorn config --show

# Set user root directory
runicorn config --set-user-root "E:\\RunicornData"
```

---

## Related APIs

- **SSH API**: Use saved connections - [ssh_api.md](./ssh_api.md)
- **Runs API**: Configure storage for runs - [runs_api.md](./runs_api.md)

---

**Last Updated**: 2025-10-14

