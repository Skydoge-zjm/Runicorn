[English](../en/SSH_BACKEND_ARCHITECTURE.md) | [简体中文](SSH_BACKEND_ARCHITECTURE.md)

---

# SSH 后端架构

**文档类型**: 架构  
**版本**: v0.6.0  
**最后更新**: 2025-01-XX

---

## 概述

Runicorn v0.6.0 引入了全新的多后端 SSH 架构，旨在实现最大的兼容性和可靠性。该架构将**连接管理**与**隧道传输**分离，允许每一层使用不同的实现。

### 设计原则

1. **关注点分离**: 连接（exec/SFTP）和隧道是独立的层
2. **优雅回退**: 自动后端选择与回退链
3. **安全优先**: 严格的主机密钥验证与用户确认流程
4. **零配置**: 开箱即用，自动检测后端

---

## 架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Remote Viewer 系统                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     AutoBackend (选择器)                          │  │
│  │                                                                    │  │
│  │   connect() ──────────────────────────────────────────────────►  │  │
│  │                         始终使用 Paramiko                         │  │
│  │                                                                    │  │
│  │   create_tunnel() ────────────────────────────────────────────►  │  │
│  │                                                                    │  │
│  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │  │
│  │   │  OpenSSH    │───►│  AsyncSSH   │───►│  Paramiko   │         │  │
│  │   │  隧道       │    │  隧道       │    │  隧道       │         │  │
│  │   └─────────────┘    └─────────────┘    └─────────────┘         │  │
│  │        ▲                   ▲                   ▲                  │  │
│  │        │ 出错时回退        │ 出错时回退        │ 最终             │  │
│  │        │                   │                   │ 回退             │  │
│  └────────┼───────────────────┼───────────────────┼─────────────────┘  │
│           │                   │                   │                     │
├───────────┼───────────────────┼───────────────────┼─────────────────────┤
│           │                   │                   │                     │
│  ┌────────▼───────────────────▼───────────────────▼─────────────────┐  │
│  │                    连接层 (Paramiko)                              │  │
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
│                         安全层                                           │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    主机密钥验证                                    │  │
│  │                                                                    │  │
│  │   ┌─────────────────┐    ┌─────────────────────────────────────┐ │  │
│  │   │  KnownHostsStore │    │  HostKeyConfirmationRequiredError  │ │  │
│  │   │  - list_host_keys│    │  - HostKeyProblem 数据类           │ │  │
│  │   │  - upsert_host_key│   │  - 409 HTTP 响应协议               │ │  │
│  │   │  - remove_host_key│   └─────────────────────────────────────┘ │  │
│  │   └─────────────────┘                                             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 连接层

连接层处理 SSH 会话建立、命令执行和 SFTP 操作。它**始终使用 Paramiko** 以获得最大兼容性。

### SSHConnection

**文件**: `src/runicorn/remote/connection.py`

**职责**: 管理单个 SSH 连接，支持自动保活。

```python
@dataclass
class SSHConfig:
    host: str
    port: int = 22
    username: str = ""
    password: Optional[str] = None
    private_key: Optional[str] = None      # 密钥内容
    private_key_path: Optional[str] = None # 密钥文件路径
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

**特性**:
- 自动保活（默认 30 秒间隔）
- 通过 `transport.send_ignore()` 进行连接健康检查
- 支持 RSA、Ed25519 和 ECDSA 密钥
- 内部锁保证线程安全

### SSHConnectionPool

**职责**: 管理多个 SSH 连接，支持复用。

```python
class SSHConnectionPool:
    def get_or_create(self, config: SSHConfig) -> SSHConnection
    def remove(self, host: str, port: int, username: str) -> bool
    def get_connection(self, host: str, port: int, username: str) -> Optional[SSHConnection]
    def close_all(self) -> None
    def list_connections(self) -> list[Dict[str, any]]
```

**连接键格式**: `{username}@{host}:{port}`

---

## 隧道层

隧道层处理 Remote Viewer 的 SSH 端口转发。它使用**回退链**以最大化跨不同环境的兼容性。

### AutoBackend

**文件**: `src/runicorn/remote/ssh_backend.py`

**职责**: 自动选择最佳可用的隧道后端。

```python
class AutoBackend(SshBackend):
    def connect(self, config: SSHConfig) -> SshConnection:
        # 始终使用 Paramiko
        return self._paramiko.connect(config)
    
    def create_tunnel(self, *, connection, local_port, remote_host, remote_port, stop_event) -> SshTunnel:
        # 回退链: OpenSSH → AsyncSSH → Paramiko
        try:
            return self._openssh.create_tunnel(...)
        except Exception as e:
            if isinstance(e, HostKeyConfirmationRequiredError):
                raise  # 主机密钥问题不回退
            logger.info(f"从 OpenSSH 回退: {e}")
        
        try:
            return self._asyncssh.create_tunnel(...)
        except Exception as e:
            if isinstance(e, HostKeyConfirmationRequiredError):
                raise
            logger.info(f"从 AsyncSSH 回退: {e}")
        
        return self._paramiko.create_tunnel(...)
```

### 回退链

| 优先级 | 后端 | 使用条件 | 限制 |
|--------|------|----------|------|
| 1 | **OpenSSH** | 系统 `ssh` 可用，密钥认证 | 不支持密码认证 |
| 2 | **AsyncSSH** | 已安装 `asyncssh` 包 | 需要 Python asyncio |
| 3 | **Paramiko** | 始终可用 | 比原生 SSH 慢 |

---

## 后端实现

### OpenSSHTunnel

**职责**: 通过系统 OpenSSH 客户端进行 SSH 隧道。

**优势**:
- 使用原生 SSH 客户端（最快、最兼容）
- 自动利用系统 SSH agent
- 更好地处理复杂网络配置

**实现细节**:

```python
class OpenSSHTunnel:
    def start(self) -> None:
        cmd = [
            self._ssh_path,
            "-N",                                    # 不执行远程命令
            "-L", f"127.0.0.1:{local}:{remote_host}:{remote_port}",
            "-p", str(port),
            "-o", "ExitOnForwardFailure=yes",
            "-o", "BatchMode=yes",                   # 无交互提示
            "-o", "StrictHostKeyChecking=yes",
            "-o", f"UserKnownHostsFile={known_hosts}",
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            f"{username}@{host}",
        ]
        self._proc = subprocess.Popen(cmd, ...)
```

**主机密钥处理**:
- 验证失败时使用 `ssh-keyscan` 获取呈现的主机密钥
- 构造 `HostKeyProblem` 用于 409 确认流程
- 支持 "unknown" 和 "changed" 两种密钥场景

**限制**:
- 需要 PATH 中有 `ssh` 和 `ssh-keyscan`
- 不支持密码认证（BatchMode=yes）
- Windows: 需要安装 OpenSSH 客户端

### AsyncSSHTunnel

**职责**: 通过 AsyncSSH 库进行异步 SSH 隧道。

**优势**:
- 纯 Python，无外部依赖
- 原生异步，性能更好
- 完整的认证方法支持

**实现细节**:

```python
class AsyncSSHTunnel:
    async def _start_asyncssh_tunnel(self) -> None:
        class _RunicornSSHClient(SSHClient):
            def validate_host_public_key(self, host, addr, port, key) -> bool:
                # 针对 Runicorn known_hosts 的自定义验证
                # 返回 False 触发 HostKeyNotVerifiable
                # 存储 HostKeyProblem 用于 409 流程
                ...
        
        self._conn = await asyncssh.connect(
            host,
            port=port,
            username=username,
            known_hosts=None,  # 使用自定义验证
            client_factory=_RunicornSSHClient,
            ...
        )
        
        self._listener = await self._conn.forward_local_port(
            "127.0.0.1", local_port, remote_host, remote_port
        )
```

**主机密钥处理**:
- 自定义 `SSHClient` 子类，带 `validate_host_public_key` 回调
- 针对 Runicorn 管理的 known_hosts 进行验证
- 将 `HostKeyNotVerifiable` 转换为 `HostKeyConfirmationRequiredError`

### SSHTunnel (Paramiko)

**文件**: `src/runicorn/remote/viewer/tunnel.py`

**职责**: 使用 Paramiko 传输层的最终回退。

**优势**:
- 始终可用（Paramiko 是核心依赖）
- 完整功能支持，包括密码认证
- 经过充分测试，实现稳定

**实现**:
- 使用 `paramiko.Transport.request_port_forward()`
- 在后台线程中运行转发
- 停止时处理连接清理

---

## 安全架构

### 主机密钥验证

Runicorn 在所有后端中强制执行**严格的主机密钥检查**。未知或已更改的主机密钥会触发用户确认流程。

#### KnownHostsStore

**文件**: `src/runicorn/remote/known_hosts.py`

**职责**: 线程安全地管理 Runicorn 的 known_hosts 文件。

```python
class KnownHostsStore:
    def list_host_keys(self) -> List[dict]
    def upsert_host_key(self, host: str, port: int, key_type: str, key_base64: str) -> bool
    def remove_host_key(self, host: str, port: int, key_type: str) -> bool
```

**特性**:
- 使用 `filelock` 进行文件锁定以支持并发访问
- 通过临时文件 + 重命名实现原子写入
- OpenSSH 兼容格式
- 与系统 known_hosts 分离

**存储位置**: `{user_root_dir}/known_hosts`

#### HostKeyProblem

**文件**: `src/runicorn/remote/host_key.py`

**职责**: 主机密钥验证问题的规范化表示。

```python
@dataclass(frozen=True)
class HostKeyProblem:
    host: str
    port: int
    known_hosts_host: str           # 例如 "[host]:2222" 或 "host"
    key_type: str                   # 例如 "ssh-ed25519"
    fingerprint_sha256: str         # 例如 "SHA256:abc..."
    public_key: str                 # 例如 "ssh-ed25519 AAAA..."
    reason: Literal["unknown", "changed"]
    expected_fingerprint_sha256: Optional[str] = None  # 用于 "changed"
    expected_public_key: Optional[str] = None          # 用于 "changed"
```

### 409 确认协议

当主机密钥验证失败时，API 返回 HTTP 409 并附带 `HostKeyProblem` 详情：

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

**前端流程**:
1. 向用户显示指纹和密钥类型
2. 用户确认或拒绝密钥
3. 确认后: POST 到 `/api/remote/known-hosts/add` 附带密钥详情
4. 重试原始连接

---

## 配置

### 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `RUNICORN_SSH_PATH` | SSH 可执行文件路径 | 从 PATH 自动检测 |

### 后端检测

`OpenSSHBackend` 按以下顺序解析 SSH 可执行文件路径：

1. 传递给构造函数的显式路径
2. `RUNICORN_SSH_PATH` 环境变量
3. `shutil.which("ssh")` PATH 查找

验证: 运行 `ssh -V` 以验证可执行文件可用。

---

## 错误处理

### 异常层次

```
Exception
└── HostKeyConfirmationRequiredError
    ├── UnknownHostKeyError      # 主机不在 known_hosts 中
    └── HostKeyChangedError      # 密钥不匹配（潜在中间人攻击）
```

### 回退行为

- **主机密钥错误**: 永不回退，始终抛出以触发 409 流程
- **后端不可用**: 回退到链中的下一个后端
- **连接错误**: 传播给调用者进行重试逻辑

---

## 性能特征

| 后端 | 启动时间 | 吞吐量 | 内存 |
|------|----------|--------|------|
| OpenSSH | ~100ms | 原生 | 低（外部进程）|
| AsyncSSH | ~200ms | 良好 | 中等 |
| Paramiko | ~300ms | 良好 | 中等 |

**建议**: 让 AutoBackend 自动选择。很少需要手动选择后端。

---

## 相关文档

- **[REMOTE_VIEWER_ARCHITECTURE.md](REMOTE_VIEWER_ARCHITECTURE.md)** - Remote Viewer 系统设计
- **[COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md)** - 组件详情
- **[../api/zh/remote_api.md](../../api/zh/remote_api.md)** - Remote API 参考

---

**导航**: [架构文档索引](README.md) | [主文档](../../README.md)
