[English](REMOTE_VIEWER_ARCHITECTURE.md) | [简体中文](../zh/REMOTE_VIEWER_ARCHITECTURE.md)

---

# Remote Viewer Architecture

**Document Type**: Architecture  
**Version**: v0.7.2  
**Last Updated**: 2026-05-10  
**Status**: Implemented

## Overview

The current Remote Viewer implementation is not a remote file-sync feature. It is a local Viewer API that manages SSH connections, remote Viewer processes, and local port forwarding so the browser talks to a Viewer running on the remote machine through a forwarded localhost URL.

This document is grounded in:

- `src/runicorn/viewer/api/remote/*.py`
- `src/runicorn/remote/connection.py`
- `src/runicorn/remote/ssh_backend.py`
- `src/runicorn/remote/viewer/manager.py`
- `src/runicorn/remote/viewer/session.py`
- `src/runicorn/remote/viewer/tunnel.py`

## Current structure

```text
Browser / Frontend
  -> /api/remote/* (FastAPI)
  -> SSHConnectionPool
  -> RemoteViewerManager
  -> SSH backend fallback chain
       OpenSSH -> AsyncSSH -> Paramiko
  -> remote runicorn viewer process
  -> local forwarded URL (http://localhost:<localPort>)
```

Two separations matter in the current design:

1. Connection layer  
   Handles SSH authentication, connection reuse, command execution, and environment probing.
2. Viewer session layer  
   Handles the remote Viewer process, tunnel lifecycle, health checks, and recovery.

## API-layer responsibilities

The current `/api/remote/*` surface is split into five groups:

1. SSH connection and summary state  
   `connect`, `sessions`, `disconnect`, `status`
2. Runtime discovery  
   `conda-envs`, `env-configs`, `config`, `storage-candidates`
3. Host-key management  
   `known-hosts/accept`, `list`, `remove`
4. Viewer sessions  
   `viewer/start`, `stop`, `sessions`, `status/{session_id}`
5. Saved connections  
   `connections/saved`

Both `connect` and `viewer/start` can resolve credentials through `saved_server_id` rather than requiring a fully explicit credential payload every time.

## Connection model

### SSHConnectionPool

`request.app.state.connection_pool` is the API-layer SSH connection pool. The API initializes it lazily and keys connections by `host + port + username`.

`/api/remote/connect` is responsible for:

1. merging direct request fields with a saved server entry when `saved_server_id` is present
2. building `SSHConfig`
3. getting or creating the pooled connection
4. returning a `connection_id` that later runtime and viewer calls can reuse

### Saved server entries

Saved connections are not just a UI convenience anymore. They are part of the current remote workflow:

- `GET /api/remote/connections/saved` returns masked saved entries
- `POST /api/remote/connections/saved` persists the list
- connection establishment and viewer startup can both consume `saved_server_id`

That makes saved server / profile state part of the active remote model.

## SSH backend fallback chain

Remote Viewer no longer relies on a single Paramiko tunnel path. `src/runicorn/remote/ssh_backend.py` implements a fallback chain:

1. OpenSSH  
   Preferred when the system `ssh` / `ssh-keyscan` path is available.
2. AsyncSSH  
   Used when OpenSSH is unavailable or not suitable for the scenario.
3. Paramiko  
   Final fallback implementation.

This keeps tunnel creation from depending on one transport choice.

## Host-key protocol

Host-key validation is part of the current protocol, not an incidental detail.

Current flow:

1. connect or viewer startup triggers host-key validation
2. unknown / changed keys are normalized to the API layer
3. the API returns `409 Conflict`
4. the frontend calls `POST /api/remote/known-hosts/accept`
5. the original action is retried after explicit user confirmation

Implications:

- host keys are not silently auto-accepted
- `known_hosts` management is part of the user-visible remote workflow

## Viewer session model

`RemoteViewerManager` is responsible for:

1. starting the remote Viewer process
2. selecting local and remote ports
3. creating and maintaining the SSH tunnel
4. registering sessions
5. monitoring the remote process and tunnel
6. attempting bounded recovery when failures occur

`RemoteViewerSession.to_dict()` currently exposes:

- `sessionId`
- `host`
- `sshPort`
- `username`
- `localPort`
- `remotePort`
- `remoteRoot`
- `remotePid`
- `status`
- `startedAt`
- `uptimeSeconds`
- `isActive`
- `url`

## Session state machine

The current status enum is defined in `src/runicorn/remote/viewer/session.py`:

- `running`
- `reconnecting`
- `degraded`
- `disconnected`
- `stopped`

State meaning:

1. `running`  
   Remote process and tunnel are healthy.
2. `reconnecting`  
   The tunnel or SSH connection was lost and the manager is rebuilding it.
3. `degraded`  
   Process health checks failed and automatic restart did not immediately restore the session.
4. `disconnected`  
   The connection is no longer recoverable.
5. `stopped`  
   The session was explicitly stopped.

Two implementation details are important:

- `reconnecting` and `degraded` still count as active so cleanup does not remove recoverable sessions too early
- `degraded` can transition back to `running` once process health is restored

## Health checks and recovery

The main recovery logic lives in `RemoteViewerManager`:

1. tunnel failure moves the session to `reconnecting`
2. if the SSH connection can be recovered, the tunnel is rebuilt
3. if the remote Viewer process dies, the manager attempts a process restart
4. if restart fails, the session is marked `degraded`
5. if the connection cannot be recovered, the session becomes `disconnected`

So the current model is bounded recovery plus explicit state exposure, not immediate teardown on first failure.

## Stop semantics

`POST /api/remote/viewer/stop` does more than stop the viewer session. It also checks whether the underlying SSH connection is still shared by other sessions.

- if other sessions still use that SSH connection, the connection is kept
- if no remaining sessions use it, the API removes it from the pool automatically

This keeps viewer-session lifetime and SSH-connection lifetime loosely coupled but coordinated.

## How this differs from the older simplified model

The current implementation is materially different from earlier simplified descriptions:

1. it is not a single Paramiko tunnel path
2. it is not a two-state `running/stopped` system
3. it does not ignore host-key confirmation
4. saved server / profile state is part of the primary workflow
5. the viewer manager owns health checks and bounded recovery

## Maintenance rule

Update this document together with `docs/api/*/remote_api.md` whenever any of the following changes:

1. `/api/remote/*` routes are added or removed
2. the 409 host-key payload changes
3. the SSH backend fallback chain changes
4. the session status enum changes
5. the role of saved server / profile state changes in the remote flow

---

- **[Remote API Reference](../../api/en/remote_api.md)**
- **[SSH API Historical Note](../../api/en/ssh_api.md)**
- **[Architecture Index](README.md)**
