[English](SSH_BACKEND_ARCHITECTURE.md) | [简体中文](../zh/SSH_BACKEND_ARCHITECTURE.md)

---

# SSH Backend Architecture

**Document Type**: Architecture  
**Version**: v0.6.0  
**Last Updated**: 2025-01-XX

---

## Overview

Runicorn v0.6.0 introduces a new multi-backend SSH architecture designed for maximum compatibility and reliability. The architecture separates **connection management** from **tunnel transport**, allowing different implementations to be used for each layer.

### Design Principles

1. **Separation of Concerns**: Connection (exec/SFTP) and tunneling are independent layers
2. **Graceful Fallback**: Automatic backend selection with fallback chain
3. **Security First**: Strict host key verification with user confirmation flow
4. **Zero Configuration**: Works out of the box with automatic backend detection

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Remote Viewer System                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     AutoBackend (Selector)                        │  │
│  │                                                                    │  │
│  │   connect() ──────────────────────────────────────────────────►  │  │
│  │                         Always Paramiko                           │  │
│  │                                                                    │  │
│  │   create_tunnel() ────────────────────────────────────────────►  │  │
│  │                                                                    │  │
│  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │  │
│  │   │  OpenSSH    │───►│  AsyncSSH   │───►│  Paramiko   │         │  │
│  │   │  Tunnel     │    │  Tunnel     │    │  Tunnel     │         │  │
│  │   └─────────────┘    └─────────────┘    └─────────────┘         │  │
│  │        ▲                   ▲                   ▲                  │  │
│  │        │ Fallback          │ Fallback          │ Final            │  │
│  │        │ on error          │ on error          │ fallback         │  │
│  └────────┼───────────────────┼───────────────────┼─────────────────┘  │
│           │                   │                   │                     │
├───────────┼───────────────────┼───────────────────┼─────────────────────┤
│           │                   │                   │                     │
│  ┌────────▼───────────────────▼───────────────────▼─────────────────┐  │
│  │                    Connection Layer (Paramiko)                    │  │
│  │                                                                    │  │
│  │   ┌─────────────────────┐    ┌─────────────────────────────────┐ │  │
│  │   │   SSHConnection     │    │     SSHConnectionPool           │ │  │
│  │   │   - exec_command()  │    │     - get_or_create()           │ │  │
│  │   │   - get_sftp()      │    │     - remove()                  │ │  │
│  │   │   - is_connected    │    │     - close_all()               │ │  │
│  │   └─────────────────────┘    └─────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                         Security Layer                                   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Host Key Verification                          │  │
│  │                                                                    │  │
│  │   ┌─────────────────┐    ┌─────────────────────────────────────┐ │  │
│  │   │  KnownHostsStore │    │  HostKeyConfirmationRequiredError  │ │  │
│  │   │  - list_host_keys│    │  - HostKeyProblem dataclass        │ │  │
│  │   │  - upsert_host_key│   │  - 409 HTTP response protocol      │ │  │
│  │   │  - remove_host_key│   └─────────────────────────────────────┘ │  │
│  │   └─────────────────┘                                             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Connection Layer

The connection layer handles SSH session establishment, command execution, and SFTP operations. It **always uses Paramiko** for maximum compatibility.

### SSHConnection

**File**: `src/runicorn/remote/connection.py`

**Responsibility**: Manage a single SSH connection with automatic keepalive.

```python
@dataclass
class SSHConfig:
    host: str
    port: int = 22
    username: str = ""
    password: Optional[str] = None
    private_key: Optional[str] = None      # Key content
    private_key_path: Optional[str] = None # Path to key file
    passphrase: Optional[str] = None
    use_agent: bool = True
    timeout: int = 30
    keepalive_interval: int = 30
    compression: bool = True

class SSHConnection:
    def connect(self) -> bool
    def disconnect(self) -> None
    def exec_command(self, command: str, timeout: Optional[int] = None) -> Tuple[str, str, int]
    def get_sftp(self) -> SFTPClient
    @property
    def is_connected(self) -> bool
```

**Features**:
- Auto keepalive (default 30s interval)
- Connection health check via `transport.send_ignore()`
- Support for RSA, Ed25519, and ECDSA keys
- Thread-safe with internal locking

### SSHConnectionPool

**Responsibility**: Manage multiple SSH connections with reuse.

```python
class SSHConnectionPool:
    def get_or_create(self, config: SSHConfig) -> SSHConnection
    def remove(self, host: str, port: int, username: str) -> bool
    def get_connection(self, host: str, port: int, username: str) -> Optional[SSHConnection]
    def close_all(self) -> None
    def list_connections(self) -> list[Dict[str, any]]
```

**Connection Key Format**: `{username}@{host}:{port}`

---

## Tunnel Layer

The tunnel layer handles SSH port forwarding for the Remote Viewer. It uses a **fallback chain** to maximize compatibility across different environments.

### AutoBackend

**File**: `src/runicorn/remote/ssh_backend.py`

**Responsibility**: Automatically select the best available tunnel backend.

```python
class AutoBackend(SshBackend):
    def connect(self, config: SSHConfig) -> SshConnection:
        # Always uses Paramiko
        return self._paramiko.connect(config)
    
    def create_tunnel(self, *, connection, local_port, remote_host, remote_port, stop_event) -> SshTunnel:
        # Fallback chain: OpenSSH → AsyncSSH → Paramiko
        try:
            return self._openssh.create_tunnel(...)
        except Exception as e:
            if isinstance(e, HostKeyConfirmationRequiredError):
                raise  # Don't fallback on host key issues
            logger.info(f"Falling back from OpenSSH: {e}")
        
        try:
            return self._asyncssh.create_tunnel(...)
        except Exception as e:
            if isinstance(e, HostKeyConfirmationRequiredError):
                raise
            logger.info(f"Falling back from AsyncSSH: {e}")
        
        return self._paramiko.create_tunnel(...)
```

### Fallback Chain

| Priority | Backend | When Used | Limitations |
|----------|---------|-----------|-------------|
| 1 | **OpenSSH** | System `ssh` available, key-based auth | No password auth |
| 2 | **AsyncSSH** | `asyncssh` package installed | Requires Python asyncio |
| 3 | **Paramiko** | Always available | Slower than native SSH |

---

## Backend Implementations

### OpenSSHTunnel

**Responsibility**: SSH tunneling via system OpenSSH client.

**Advantages**:
- Uses native SSH client (fastest, most compatible)
- Leverages system SSH agent automatically
- Better handling of complex network configurations

**Implementation Details**:

```python
class OpenSSHTunnel:
    def start(self) -> None:
        cmd = [
            self._ssh_path,
            "-N",                                    # No remote command
            "-L", f"127.0.0.1:{local}:{remote_host}:{remote_port}",
            "-p", str(port),
            "-o", "ExitOnForwardFailure=yes",
            "-o", "BatchMode=yes",                   # No interactive prompts
            "-o", "StrictHostKeyChecking=yes",
            "-o", f"UserKnownHostsFile={known_hosts}",
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            f"{username}@{host}",
        ]
        self._proc = subprocess.Popen(cmd, ...)
```

**Host Key Handling**:
- Uses `ssh-keyscan` to retrieve presented host key on verification failure
- Constructs `HostKeyProblem` for 409 confirmation flow
- Supports both "unknown" and "changed" key scenarios

**Limitations**:
- Requires `ssh` and `ssh-keyscan` in PATH
- Does not support password authentication (BatchMode=yes)
- Windows: Requires OpenSSH client installed

### AsyncSSHTunnel

**Responsibility**: Async SSH tunneling via AsyncSSH library.

**Advantages**:
- Pure Python, no external dependencies
- Async-native for better performance
- Full authentication method support

**Implementation Details**:

```python
class AsyncSSHTunnel:
    async def _start_asyncssh_tunnel(self) -> None:
        class _RunicornSSHClient(SSHClient):
            def validate_host_public_key(self, host, addr, port, key) -> bool:
                # Custom validation against Runicorn known_hosts
                # Returns False to trigger HostKeyNotVerifiable
                # Stores HostKeyProblem for 409 flow
                ...
        
        self._conn = await asyncssh.connect(
            host,
            port=port,
            username=username,
            known_hosts=None,  # Use custom validation
            client_factory=_RunicornSSHClient,
            ...
        )
        
        self._listener = await self._conn.forward_local_port(
            "127.0.0.1", local_port, remote_host, remote_port
        )
```

**Host Key Handling**:
- Custom `SSHClient` subclass with `validate_host_public_key` callback
- Validates against Runicorn-managed known_hosts
- Converts `HostKeyNotVerifiable` to `HostKeyConfirmationRequiredError`

### SSHTunnel (Paramiko)

**File**: `src/runicorn/remote/viewer/tunnel.py`

**Responsibility**: Final fallback using Paramiko's transport layer.

**Advantages**:
- Always available (Paramiko is a core dependency)
- Full feature support including password auth
- Well-tested, stable implementation

**Implementation**:
- Uses `paramiko.Transport.request_port_forward()`
- Runs forwarding in a background thread
- Handles connection cleanup on stop

---

## Security Architecture

### Host Key Verification

Runicorn enforces **strict host key checking** across all backends. Unknown or changed host keys trigger a user confirmation flow.

#### KnownHostsStore

**File**: `src/runicorn/remote/known_hosts.py`

**Responsibility**: Thread-safe management of Runicorn's known_hosts file.

```python
class KnownHostsStore:
    def list_host_keys(self) -> List[dict]
    def upsert_host_key(self, host: str, port: int, key_type: str, key_base64: str) -> bool
    def remove_host_key(self, host: str, port: int, key_type: str) -> bool
```

**Features**:
- File locking with `filelock` for concurrent access
- Atomic writes via temp file + rename
- OpenSSH-compatible format
- Separate from system known_hosts

**Storage Location**: `{user_root_dir}/known_hosts`

#### HostKeyProblem

**File**: `src/runicorn/remote/host_key.py`

**Responsibility**: Normalized representation of host key verification issues.

```python
@dataclass(frozen=True)
class HostKeyProblem:
    host: str
    port: int
    known_hosts_host: str           # e.g., "[host]:2222" or "host"
    key_type: str                   # e.g., "ssh-ed25519"
    fingerprint_sha256: str         # e.g., "SHA256:abc..."
    public_key: str                 # e.g., "ssh-ed25519 AAAA..."
    reason: Literal["unknown", "changed"]
    expected_fingerprint_sha256: Optional[str] = None  # For "changed"
    expected_public_key: Optional[str] = None          # For "changed"
```

### 409 Confirmation Protocol

When host key verification fails, the API returns HTTP 409 with the `HostKeyProblem` details:

```json
{
  "error": "host_key_confirmation_required",
  "problem": {
    "host": "gpu-server.example.com",
    "port": 22,
    "known_hosts_host": "gpu-server.example.com",
    "key_type": "ssh-ed25519",
    "fingerprint_sha256": "SHA256:abcdef...",
    "public_key": "ssh-ed25519 AAAAC3...",
    "reason": "unknown"
  }
}
```

**Frontend Flow**:
1. Display fingerprint and key type to user
2. User confirms or rejects the key
3. On confirm: POST to `/api/remote/known-hosts/add` with key details
4. Retry the original connection

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RUNICORN_SSH_PATH` | Path to SSH executable | Auto-detect from PATH |

### Backend Detection

The `OpenSSHBackend` resolves the SSH executable path in this order:

1. Explicit path passed to constructor
2. `RUNICORN_SSH_PATH` environment variable
3. `shutil.which("ssh")` PATH lookup

Validation: Runs `ssh -V` to verify the executable works.

---

## Error Handling

### Exception Hierarchy

```
Exception
└── HostKeyConfirmationRequiredError
    ├── UnknownHostKeyError      # Host not in known_hosts
    └── HostKeyChangedError      # Key mismatch (potential MITM)
```

### Fallback Behavior

- **Host key errors**: Never fallback, always raise to trigger 409 flow
- **Backend unavailable**: Fallback to next backend in chain
- **Connection errors**: Propagate to caller for retry logic

---

## Performance Characteristics

| Backend | Startup Time | Throughput | Memory |
|---------|--------------|------------|--------|
| OpenSSH | ~100ms | Native | Low (external process) |
| AsyncSSH | ~200ms | Good | Medium |
| Paramiko | ~300ms | Good | Medium |

**Recommendation**: Let AutoBackend choose automatically. Manual backend selection is rarely needed.

---

## Related Documentation

- **[REMOTE_VIEWER_ARCHITECTURE.md](REMOTE_VIEWER_ARCHITECTURE.md)** - Remote Viewer system design
- **[COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md)** - Component details
- **[../api/en/remote_api.md](../../api/en/remote_api.md)** - Remote API reference

---

**Navigation**: [Architecture Docs Index](README.md) | [Main Docs](../../README.md)
