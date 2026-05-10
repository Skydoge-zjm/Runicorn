[English](remote_api.md) | [简体中文](../zh/remote_api.md)

---

# Remote Viewer API Reference

> **Version**: v0.7.2  
> **Last Updated**: 2026-05-10  
> **Base URL**: `http://127.0.0.1:23300`

## Overview

The current remote surface lives under `/api/remote/*`. This document only describes endpoints verified in:

- `src/runicorn/viewer/api/remote/__init__.py`
- `src/runicorn/viewer/api/remote/connections.py`
- `src/runicorn/viewer/api/remote/sessions.py`
- `src/runicorn/viewer/api/remote/viewer_routes.py`
- `src/runicorn/viewer/api/remote/known_hosts.py`
- `src/runicorn/viewer/api/remote/saved_connections.py`

Legacy `/api/unified/*` and `/api/ssh/*` routes are not part of the current API surface. See [ssh_api.md](./ssh_api.md) for the historical note.

## Current endpoint inventory

### Connection and session endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/remote/connect` | Establish an SSH connection |
| `GET` | `/api/remote/sessions` | List active SSH connections from the pool |
| `POST` | `/api/remote/disconnect` | Remove a specific SSH connection |
| `GET` | `/api/remote/status` | Summarize connections and viewer sessions |

### Runtime discovery endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/remote/conda-envs` | List remote Python/Conda environments |
| `GET` | `/api/remote/env-configs` | Batch-read Python / Runicorn versions by environment |
| `GET` | `/api/remote/config` | Get runtime defaults for a chosen environment |
| `GET` | `/api/remote/storage-candidates` | Detect candidate remote storage roots |

### Known-hosts endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/remote/known-hosts/accept` | Accept and persist a host key |
| `GET` | `/api/remote/known-hosts/list` | List entries in Runicorn-managed `known_hosts` |
| `POST` | `/api/remote/known-hosts/remove` | Remove a specific host key entry |

### Remote Viewer endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/remote/viewer/start` | Start Remote Viewer and create the tunnel |
| `POST` | `/api/remote/viewer/stop` | Stop a specific viewer session |
| `GET` | `/api/remote/viewer/sessions` | List all viewer sessions |
| `GET` | `/api/remote/viewer/status/{session_id}` | Get one viewer session |

### Saved connection endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/remote/connections/saved` | Load masked saved connections |
| `POST` | `/api/remote/connections/saved` | Save the connection list |

## SSH backend and host-key protocol

The SSH tunnel path is not a single implementation. Current code prefers OpenSSH, then falls back to AsyncSSH, then Paramiko. Host key validation failures from both `connect` and `viewer/start` use the same `409 Conflict` payload.

Example:

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

If `reason` is `changed`, the payload may also include `expected_fingerprint_sha256` and `expected_public_key`. Clients should call `POST /api/remote/known-hosts/accept` before retrying.

## Connection endpoints

### `POST /api/remote/connect`

The request supports two patterns:

1. Provide connection fields directly:
   - `host`
   - `port`, default `22`
   - `username`
   - `password`
   - `private_key`
   - `private_key_path`
   - `passphrase`
   - `use_agent`
2. Provide `saved_server_id` and let the server resolve the saved entry

If `host` or `username` is still missing after resolution, the endpoint returns `400`.

Success response:

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

Returns active SSH connections:

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

Request body:

```json
{
  "host": "example.com",
  "port": 22,
  "username": "user"
}
```

Success response:

```json
{"ok": true, "message": "Connection removed"}
```

When the connection is absent:

```json
{"ok": false, "message": "Connection not found"}
```

### `GET /api/remote/status`

Returns the current remote summary:

```json
{
  "connections": [],
  "viewer_sessions": [],
  "connection_count": 0,
  "viewer_session_count": 0
}
```

## Runtime discovery endpoints

### `GET /api/remote/conda-envs`

Query parameters:

- `connection_id`

Success response:

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

Query parameters:

- `connection_id`

Success response:

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

Query parameters:

- `connection_id`
- `conda_env`, default `system`

Verified response fields:

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

Query parameters:

- `connection_id`
- `conda_env`, default `system`
- `scan_root`, optional
- `max_depth`, clamped by the implementation to `1..8`

Response:

```json
{
  "scan_root": null,
  "max_depth": 3,
  "candidates": []
}
```

## Known-hosts endpoints

### `POST /api/remote/known-hosts/accept`

Request body:

```json
{
  "host": "example.com",
  "port": 22,
  "key_type": "ssh-ed25519",
  "public_key": "ssh-ed25519 AAAA...",
  "fingerprint_sha256": "SHA256:..."
}
```

Success response:

```json
{"ok": true}
```

### `GET /api/remote/known-hosts/list`

Success response:

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

Request body:

```json
{
  "host": "example.com",
  "port": 22,
  "key_type": "ssh-ed25519"
}
```

Success response:

```json
{"ok": true, "changed": true}
```

## Remote Viewer endpoints

### `POST /api/remote/viewer/start`

In addition to the SSH connection fields, the request supports:

- `remote_root`
- `local_port`
- `remote_port`
- `conda_env`
- `saved_server_id`

Success response:

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

Request body:

```json
{"session_id": "abcd1234"}
```

Success response:

```json
{"ok": true, "message": "Session abcd1234 stopped"}
```

### `GET /api/remote/viewer/sessions`

Returns a list of `session.to_dict()` objects with the same fields as the `session` example above.

### `GET /api/remote/viewer/status/{session_id}`

Returns one `session.to_dict()` object. The status enum is defined in `src/runicorn/remote/viewer/session.py`:

- `running`
- `reconnecting`
- `degraded`
- `disconnected`
- `stopped`

## Saved connection endpoints

### `GET /api/remote/connections/saved`

Returns masked saved connections. The current test suite confirms:

- stored `password` / `passphrase` values are not echoed back
- `hasSavedPassword` / `hasSavedPassphrase` are added
- `private_key_path` is normalized to `privateKeyPath`

Example:

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

Request body: an array of saved connection entries.

Success response:

```json
{"ok": true, "message": "Connections saved successfully"}
```

## Error handling

The API uses the standard FastAPI error envelope:

```json
{"detail": "message"}
```

Verified status codes:

- `400`: incomplete or invalid input, missing manager/pool state
- `404`: connection or session not found
- `409`: host key confirmation required
- `500`: runtime failure while connecting, saving, probing, or starting viewer
- `503`: remote module unavailable

## Endpoints not present in the current implementation

The following routes were not found under `src/runicorn/viewer/api/remote/` when this document was updated, so they are intentionally excluded from the active API reference:

- `/api/remote/fs/list`
- `/api/remote/fs/exists`

If they are reintroduced later, they should be documented only after the implementation lands.

---

**[Back to API Index](API_INDEX.md)** | **[SSH historical note](ssh_api.md)**
