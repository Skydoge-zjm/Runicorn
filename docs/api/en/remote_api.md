# Remote Viewer API Reference

> **Version**: v0.5.4  
> **Last Updated**: 2025-12-22  
> **Base URL**: `http://127.0.0.1:23300`

[English](remote_api.md) | [简体中文](../zh/remote_api.md)

---

## 📖 Table of Contents

- [Overview](#overview)
- [Host Key Verification (HTTP 409)](#host-key-verification-http-409)
- [Authentication](#authentication)
- [Connection Management](#connection-management)
- [Known Hosts Management](#known-hosts-management)
- [Environment & Config](#environment--config)
- [Remote Viewer Management](#remote-viewer-management)
- [Remote File System](#remote-file-system)
- [Status](#status)
- [Saved Connections](#saved-connections)
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
1. POST /api/remote/connect              # Establish SSH connection
2. (optional) GET /api/remote/conda-envs # List envs for UI selection
3. POST /api/remote/viewer/start         # Start Remote Viewer + create SSH tunnel
4. GET /api/remote/viewer/status/{id}    # Monitor a session
5. POST /api/remote/disconnect           # Disconnect SSH connection
```

---

## Host Key Verification (HTTP 409)

When SSH host key verification fails (unknown host key or host key changed), the API returns:

- HTTP status: `409 Conflict`
- Response body:

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

If `reason` is `"changed"`, the payload may include:

- `expected_fingerprint_sha256`
- `expected_public_key`

To proceed, the client should call `POST /api/remote/known-hosts/accept` and then retry the original request.

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
| `password` | string \/ null | ❌ | SSH password (optional) |
| `private_key` | string \/ null | ❌ | Private key content (optional) |
| `private_key_path` | string \/ null | ❌ | Private key path (optional) |
| `passphrase` | string \/ null | ❌ | Passphrase for private key (optional) |
| `use_agent` | boolean | ❌ | Use SSH agent (default: true) |

#### Request Examples

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

#### Response

**Success Response** (200 OK):
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

**Error Response** (400/401/500):
```json
{
  "detail": "Connection failed: <reason>"
}
```

**Host Key Error** (409 Conflict):

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

#### Status Codes

| Status Code | Meaning |
|-------------|---------|
| 409 | Host key confirmation required (see 409 payload above) |
| 500 | Connection failed (`detail` contains error message) |
| 503 | Remote module not available |
| 422 | Validation error (FastAPI / Pydantic) |

---

### GET /api/remote/sessions

Get a list of all active remote connections.

#### Request

**URL**: `GET /api/remote/sessions`

#### Request Examples

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

#### Response

**Success Response** (200 OK):
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

Disconnect a specified remote connection.

#### Request

**URL**: `POST /api/remote/disconnect`

**Body Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `host` | string | ✅ | Remote host |
| `port` | integer | ❌ | SSH port (default: 22) |
| `username` | string | ✅ | SSH username |

#### Request Examples

**cURL**:
```bash
curl -X POST http://localhost:23300/api/remote/disconnect \
  -H "Content-Type: application/json" \
  -d '{"host": "gpu-server.com", "port": 22, "username": "mluser"}'
```

#### Response

**Success Response** (200 OK):
```json
{
  "ok": true,
  "message": "Connection removed"
}
```

---

## Known Hosts Management

### POST /api/remote/known-hosts/accept

Accept a host key and write it into Runicorn-managed `known_hosts`.

**URL**: `POST /api/remote/known-hosts/accept`

**Body Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `host` | string | ✅ | Remote host |
| `port` | integer | ✅ | SSH port |
| `key_type` | string | ✅ | Public key type (e.g. `ssh-ed25519`) |
| `public_key` | string | ✅ | OpenSSH public key (`<type> <base64>`) |
| `fingerprint_sha256` | string | ✅ | Fingerprint returned from 409 payload |

**Response**:

```json
{"ok": true}
```

### GET /api/remote/known-hosts/list

List all entries in Runicorn-managed `known_hosts`.

**URL**: `GET /api/remote/known-hosts/list`

**Response**:

```json
{
  "entries": [
    {
      "host": "gpu-server.com",
      "port": 22,
      "known_hosts_host": "gpu-server.com",
      "key_type": "ssh-ed25519",
      "key_base64": "AAAA...",
      "fingerprint_sha256": "SHA256:..."
    }
  ]
}
```

### POST /api/remote/known-hosts/remove

Remove a specific `known_hosts` entry.

**URL**: `POST /api/remote/known-hosts/remove`

**Body**:

```json
{"host": "gpu-server.com", "port": 22, "key_type": "ssh-ed25519"}
```

**Response**:

```json
{"ok": true, "changed": true}
```

---

## Environment & Config

### GET /api/remote/conda-envs

List Python environments on the remote server.

**URL**: `GET /api/remote/conda-envs`

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `connection_id` | string | ✅ | Connection ID (`user@host:port`) |

**Response**:

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

### GET /api/remote/config

Get remote runtime information and suggested defaults.

**URL**: `GET /api/remote/config`

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `connection_id` | string | ✅ | Connection ID (`user@host:port`) |
| `conda_env` | string | ❌ | Conda env name (default: `system`) |

**Response**:

```json
{
  "ok": true,
  "condaEnv": "system",
  "pythonVersion": "Python 3.11.9",
  "runicornVersion": "0.5.4",
  "defaultStorageRoot": "/home/user/runicorn_data",
  "storageRootExists": true,
  "suggestedRemotePort": 23300,
  "connectionId": "user@host:22"
}
```

---

## Remote Viewer Management

### POST /api/remote/viewer/start

Start Remote Viewer session with SSH tunnel.

**URL**: `POST /api/remote/viewer/start`

**Body Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `host` | string | ✅ | Remote host |
| `port` | integer | ❌ | SSH port (default: 22) |
| `username` | string | ✅ | SSH username |
| `password` | string \/ null | ❌ | SSH password |
| `private_key` | string \/ null | ❌ | Private key content |
| `private_key_path` | string \/ null | ❌ | Private key path |
| `passphrase` | string \/ null | ❌ | Private key passphrase |
| `use_agent` | boolean | ❌ | Use SSH agent (default: true) |
| `remote_root` | string | ✅ | Remote storage root directory |
| `local_port` | integer \/ null | ❌ | Local forwarded port (auto if null) |
| `remote_port` | integer \/ null | ❌ | Remote Viewer port (auto if null) |
| `conda_env` | string \/ null | ❌ | Conda env name (optional) |

**Response**:

```json
{
  "ok": true,
  "session": {
    "sessionId": "abcd1234",
    "localPort": 18080,
    "remotePort": 19090,
    "remoteRoot": "/data/experiments",
    "status": "running",
    "url": "http://localhost:18080"
  },
  "message": "Remote Viewer ready at http://localhost:18080"
}
```

### POST /api/remote/viewer/stop

Stop a Remote Viewer session.

**URL**: `POST /api/remote/viewer/stop`

**Body**:

```json
{"session_id": "abcd1234"}
```

### GET /api/remote/viewer/sessions

List active Remote Viewer sessions.

**URL**: `GET /api/remote/viewer/sessions`

### GET /api/remote/viewer/status/{session_id}

Get a session status.

**URL**: `GET /api/remote/viewer/status/{session_id}`

---

## Remote File System

### GET /api/remote/fs/list

List a remote directory via SFTP.

**URL**: `GET /api/remote/fs/list`

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `connection_id` | string | ✅ | Connection ID (`user@host:port`) |
| `path` | string | ❌ | Remote path (default: `~`) |

### GET /api/remote/fs/exists

Check if a remote path exists.

**URL**: `GET /api/remote/fs/exists`

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `connection_id` | string | ✅ | Connection ID (`user@host:port`) |
| `path` | string | ✅ | Remote path |

---

## Status

### GET /api/remote/status

Get overall remote status.

**URL**: `GET /api/remote/status`

---

## Saved Connections

### GET /api/remote/connections/saved

Load saved SSH connections.

### POST /api/remote/connections/saved

Save SSH connections.

---

## Error Handling

Runicorn Viewer uses FastAPI error responses:

```json
{"detail": "<message>"}
```

In some cases (e.g. host key verification), `detail` is a structured object (see HTTP 409 section).

---

**Author**: Runicorn Development Team  
**Version**: v0.5.4  
**Last Updated**: 2025-12-22

**[Back to API Index](API_INDEX.md)** | **[View Quick Reference](QUICK_REFERENCE.md)**
