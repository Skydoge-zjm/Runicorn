# Remote Viewer API Reference

> **Version**: v0.5.0  
> **Last Updated**: 2025-10-25  
> **Base URL**: `http://localhost:23300`

[English](remote_api.md) | [简体中文](../zh/remote_api.md)

---

## 📖 Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Connection Management](#connection-management)
- [Environment Detection](#environment-detection)
- [Remote Viewer Management](#remote-viewer-management)
- [Health Checks](#health-checks)
- [Error Handling](#error-handling)

---

## Overview

The Remote Viewer API provides complete functionality for connecting to remote servers via SSH and launching Remote Viewer. It follows RESTful design principles and supports JSON format for requests and responses.

### Key Features

- 🔌 **SSH Connection Management**: Support for key and password authentication
- 🐍 **Auto Environment Detection**: Identifies Conda, Virtualenv and other Python environments
- 🚀 **Viewer Lifecycle**: Start, monitor, and stop remote Viewer
- 💓 **Health Monitoring**: Real-time connection and Viewer status checks
- 🔒 **Security**: All communication via SSH encryption

### Workflow

```
1. POST /api/remote/connect          # Establish SSH connection
2. GET /api/remote/environments      # Detect Python environments
3. POST /api/remote/viewer/start     # Start Remote Viewer
4. GET /api/remote/viewer/status     # Monitor status
5. DELETE /api/remote/connections/id # Disconnect
```

---

## Authentication

The Remote API currently does not require additional authentication. All requests are sent through the local Viewer instance.

**Note**: SSH connections themselves require authentication (key or password).

---

## Connection Management

### POST /api/remote/connect

Establish an SSH connection to a remote server.

#### Request

**URL**: `POST /api/remote/connect`

**Headers**:
```
Content-Type: application/json
```

**Body Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `host` | string | ✅ | Remote server address (domain or IP) |
| `port` | integer | ❌ | SSH port (default: 22) |
| `username` | string | ✅ | SSH username |
| `auth_method` | string | ✅ | Authentication method: `"key"`, `"password"`, `"agent"` |
| `private_key_path` | string | ⚠️ | Private key path (required if auth_method="key") |
| `password` | string | ⚠️ | SSH password (required if auth_method="password") |
| `timeout` | integer | ❌ | Connection timeout in seconds (default: 30) |

#### Request Examples

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

#### Response

**Success Response** (200 OK):
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
    "python_version": "3.10.8"
  },
  "created_at": "2025-10-25T10:30:00Z"
}
```

**Error Response** (400/401/500):
```json
{
  "success": false,
  "error": "authentication_failed",
  "message": "SSH authentication failed: Invalid private key"
}
```

#### Error Codes

| Status Code | Error Code | Description |
|-------------|------------|-------------|
| 400 | `invalid_parameters` | Missing required parameters |
| 401 | `authentication_failed` | SSH authentication failed |
| 408 | `connection_timeout` | Connection timeout |
| 500 | `ssh_error` | SSH connection error |

---

### GET /api/remote/connections

Get a list of all active remote connections.

#### Request

**URL**: `GET /api/remote/connections`

#### Request Examples

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

#### Response

**Success Response** (200 OK):
```json
{
  "success": true,
  "connections": [
    {
      "connection_id": "conn_1a2b3c4d",
      "host": "gpu-server.com",
      "status": "connected",
      "viewer": {
        "status": "running",
        "url": "http://localhost:8081"
      }
    }
  ],
  "total": 1
}
```

---

### DELETE /api/remote/connections/{id}

Disconnect a specified remote connection.

#### Request

**URL**: `DELETE /api/remote/connections/{connection_id}`

**Query Parameters**:
- `cleanup_viewer` (boolean): Also cleanup Remote Viewer (default: true)

#### Request Examples

**cURL**:
```bash
curl -X DELETE "http://localhost:23300/api/remote/connections/conn_1a2b3c4d?cleanup_viewer=true"
```

#### Response

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Connection disconnected successfully",
  "connection_id": "conn_1a2b3c4d"
}
```

---

## Environment Detection

### GET /api/remote/environments

List Python environments detected on the remote server.

#### Request

**URL**: `GET /api/remote/environments`

**Query Parameters**:
- `connection_id` (string, required): Connection ID
- `filter` (string, optional): Filter criteria: `"all"` or `"runicorn_only"`

#### Request Examples

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

#### Response

**Success Response** (200 OK):
```json
{
  "success": true,
  "environments": [
    {
      "name": "pytorch-env",
      "type": "conda",
      "python_version": "3.9.15",
      "runicorn_installed": true,
      "runicorn_version": "0.5.0",
      "storage_root": "/data/experiments"
    }
  ],
  "total": 1
}
```

---

### POST /api/remote/environments/detect

Re-detect Python environments on the remote server.

#### Request

**URL**: `POST /api/remote/environments/detect`

**Body Parameters**:
- `connection_id` (string, required): Connection ID
- `force_refresh` (boolean, optional): Force cache refresh

#### Request Examples

**cURL**:
```bash
curl -X POST http://localhost:23300/api/remote/environments/detect \
  -H "Content-Type: application/json" \
  -d '{"connection_id": "conn_1a2b3c4d", "force_refresh": true}'
```

#### Response

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Environments detected successfully",
  "environments_found": 3
}
```

---

### GET /api/remote/config

Get the Runicorn configuration from the remote server.

#### Request

**URL**: `GET /api/remote/config`

**Query Parameters**:
- `connection_id` (string, required): Connection ID
- `env_name` (string, required): Environment name

#### Request Examples

**cURL**:
```bash
curl "http://localhost:23300/api/remote/config?connection_id=conn_1a2b3c4d&env_name=pytorch-env"
```

#### Response

**Success Response** (200 OK):
```json
{
  "success": true,
  "config": {
    "user_root_dir": "/data/experiments",
    "viewer_port": 23300
  },
  "runicorn_version": "0.5.0"
}
```

---

## Remote Viewer Management

### POST /api/remote/viewer/start

Start Remote Viewer on the remote server.

#### Request

**URL**: `POST /api/remote/viewer/start`

**Body Parameters**:
- `connection_id` (string, required): Connection ID
- `env_name` (string, required): Python environment name
- `remote_root` (string, optional): Remote storage root directory
- `auto_open` (boolean, optional): Auto-open browser (default: true)

#### Request Examples

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
print(f"Viewer URL: {viewer_info['viewer']['url']}")
```

#### Response

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Remote Viewer started successfully",
  "viewer": {
    "status": "running",
    "local_port": 8081,
    "url": "http://localhost:8081",
    "started_at": "2025-10-25T10:40:00Z"
  }
}
```

---

### POST /api/remote/viewer/stop

Stop Remote Viewer on the remote server.

#### Request

**URL**: `POST /api/remote/viewer/stop`

**Body Parameters**:
- `connection_id` (string, required): Connection ID
- `cleanup` (boolean, optional): Cleanup temporary files (default: true)

#### Request Examples

**cURL**:
```bash
curl -X POST http://localhost:23300/api/remote/viewer/stop \
  -H "Content-Type: application/json" \
  -d '{"connection_id": "conn_1a2b3c4d"}'
```

#### Response

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Remote Viewer stopped successfully"
}
```

---

### GET /api/remote/viewer/status

Get the current status of Remote Viewer.

#### Request

**URL**: `GET /api/remote/viewer/status`

**Query Parameters**:
- `connection_id` (string, required): Connection ID

#### Request Examples

**cURL**:
```bash
curl "http://localhost:23300/api/remote/viewer/status?connection_id=conn_1a2b3c4d"
```

#### Response

**Success Response** (200 OK):
```json
{
  "success": true,
  "viewer": {
    "status": "running",
    "url": "http://localhost:8081",
    "uptime_seconds": 3600,
    "health": "healthy"
  }
}
```

---

### GET /api/remote/viewer/logs

Get log output from Remote Viewer.

#### Request

**URL**: `GET /api/remote/viewer/logs`

**Query Parameters**:
- `connection_id` (string, required): Connection ID
- `lines` (integer, optional): Number of log lines (default: 100)

#### Request Examples

**cURL**:
```bash
curl "http://localhost:23300/api/remote/viewer/logs?connection_id=conn_1a2b3c4d&lines=50"
```

#### Response

**Success Response** (200 OK):
```json
{
  "success": true,
  "logs": [
    "[2025-10-25 10:40:00] INFO: Starting Remote Viewer",
    "[2025-10-25 10:40:01] INFO: Viewer listening on port 45342"
  ],
  "total_lines": 2
}
```

---

## Health Checks

### GET /api/remote/health

Get the health status of a connection.

#### Request

**URL**: `GET /api/remote/health`

**Query Parameters**:
- `connection_id` (string, required): Connection ID

#### Response

**Success Response** (200 OK):
```json
{
  "success": true,
  "health": "healthy",
  "checks": {
    "ssh_connection": "pass",
    "viewer_process": "pass",
    "tunnel_active": "pass"
  }
}
```

---

### GET /api/remote/ping

Test remote connection latency.

#### Request

**URL**: `GET /api/remote/ping`

**Query Parameters**:
- `connection_id` (string, required): Connection ID

#### Response

**Success Response** (200 OK):
```json
{
  "success": true,
  "latency_ms": 45,
  "timestamp": "2025-10-25T11:00:00Z"
}
```

---

## Error Handling

All API endpoints return a unified error response format when errors occur.

### Error Response Format

```json
{
  "success": false,
  "error": "error_code",
  "message": "Human-readable error message"
}
```

### Common Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `invalid_parameters` | Invalid request parameters |
| 401 | `authentication_failed` | SSH authentication failed |
| 404 | `connection_not_found` | Connection not found |
| 404 | `environment_not_found` | Environment not found |
| 408 | `connection_timeout` | Connection timeout |
| 409 | `viewer_already_running` | Viewer already running |
| 500 | `internal_error` | Internal server error |

---

**Author**: Runicorn Development Team  
**Version**: v0.5.0  
**Last Updated**: 2025-10-25

**[Back to API Index](API_INDEX.md)** | **[View Quick Reference](QUICK_REFERENCE.md)**
