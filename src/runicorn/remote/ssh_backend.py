from __future__ import annotations

import asyncio
import base64
import logging
import os
import shlex
import shutil
import subprocess
import threading
import time
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional, Protocol, Tuple, TYPE_CHECKING


if TYPE_CHECKING:
    from .connection import SSHConfig


logger = logging.getLogger(__name__)


class OpenSSHFallbackError(RuntimeError):
    """Error type for cases where falling back to another backend is reasonable."""


class _OpenSSHAskpassHelper:
    _SECRET_ENV = "RUNICORN_SSH_ASKPASS_SECRET"

    def __init__(self, secret: str):
        self._secret = secret
        self._temp_dir: Optional[Path] = None

    def build_env(self) -> dict[str, str]:
        temp_dir = Path(tempfile.mkdtemp(prefix="runicorn-ssh-askpass-"))
        self._temp_dir = temp_dir

        if os.name == "nt":
            wrapper = temp_dir / "askpass.cmd"
            powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
            powershell_cmd = str(powershell) if powershell.exists() else "powershell"
            wrapper.write_text(
                (
                    "@echo off\r\n"
                    f'"{powershell_cmd}" -NoLogo -NoProfile -NonInteractive '
                    "-ExecutionPolicy Bypass "
                    f'-Command "[Console]::Out.Write($env:{self._SECRET_ENV})"\r\n'
                ),
                encoding="utf-8",
            )
        else:
            wrapper = temp_dir / "askpass.sh"
            wrapper.write_text(
                (
                    "#!/bin/sh\n"
                    f'printf "%s" "${self._SECRET_ENV}"\n'
                ),
                encoding="utf-8",
            )
            wrapper.chmod(0o700)

        env = os.environ.copy()
        env["SSH_ASKPASS"] = str(wrapper)
        env["SSH_ASKPASS_REQUIRE"] = "force"
        env[self._SECRET_ENV] = self._secret
        env.setdefault("DISPLAY", "runicorn-askpass:0")
        return env

    def cleanup(self) -> None:
        if self._temp_dir is not None:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            self._temp_dir = None


class SshTunnel(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...


class SshConnection(Protocol):
    config: "SSHConfig"
    env_cache: dict[str, Any]

    def connect(self) -> bool: ...

    def disconnect(self) -> None: ...

    def exec_command(self, command: str, timeout: Optional[int] = None) -> Tuple[str, str, int]: ...

    def get_sftp(self) -> Any: ...

    @property
    def is_connected(self) -> bool: ...


class SshBackend(ABC):
    @abstractmethod
    def connect(self, config: "SSHConfig") -> SshConnection:
        raise NotImplementedError

    @abstractmethod
    def create_tunnel(
        self,
        *,
        connection: SshConnection,
        local_port: int,
        remote_host: str,
        remote_port: int,
        stop_event: threading.Event,
    ) -> SshTunnel:
        raise NotImplementedError


class ParamikoBackend(SshBackend):
    def connect(self, config: "SSHConfig") -> SshConnection:
        from .connection import SSHConnection

        conn = SSHConnection(config)
        conn.connect()
        return conn

    def create_tunnel(
        self,
        *,
        connection: SshConnection,
        local_port: int,
        remote_host: str,
        remote_port: int,
        stop_event: threading.Event,
    ) -> SshTunnel:
        from .viewer.tunnel import SSHTunnel

        client = getattr(connection, "_client", None)
        if client is None:
            raise RuntimeError("SSH client not initialized")

        transport = client.get_transport()
        if transport is None:
            raise RuntimeError("SSH transport not available")

        return SSHTunnel(
            ssh_transport=transport,
            local_port=local_port,
            remote_host=remote_host,
            remote_port=remote_port,
            stop_event=stop_event,
        )


class OpenSSHTunnel:
    """SSH local port forwarding implemented via the system OpenSSH client.

    This tunnel is designed to run in a dedicated thread.
    - `start()` blocks until `stop_event` is set or the ssh process exits.
    - `stop()` terminates the ssh process.

    Security:
    - Forces strict host key checking.
    - Uses Runicorn-managed known_hosts file.
    - Binds the local forwarded port to 127.0.0.1 only.
    """

    def __init__(
        self,
        *,
        ssh_path: str,
        host: str,
        port: int,
        username: str,
        password: Optional[str],
        private_key_path: Optional[str],
        use_agent: bool,
        local_port: int,
        remote_host: str,
        remote_port: int,
        known_hosts_path: Path,
        stop_event: threading.Event,
    ):
        self._ssh_path = ssh_path
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._private_key_path = private_key_path
        self._use_agent = use_agent
        self._local_port = local_port
        self._remote_host = remote_host
        self._remote_port = remote_port
        self._known_hosts_path = known_hosts_path
        self._stop_event = stop_event
        # NOTE: Do not subscript Popen for Python 3.8 compatibility.
        self._proc: Optional[subprocess.Popen] = None
        self._stderr_lines: List[str] = []
        self._stderr_lock = threading.Lock()
        self._askpass_helper: Optional[_OpenSSHAskpassHelper] = None

    def start(self) -> None:
        """Start and monitor the ssh tunnel process."""

        from .known_hosts import format_known_hosts_host
        from .host_key import HostKeyConfirmationRequiredError, HostKeyProblem
        from .known_hosts import compute_fingerprint_sha256, parse_openssh_public_key, find_known_host_key_base64

        # Ensure parent directory exists (OpenSSH expects the file path to be valid).
        try:
            self._known_hosts_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Best effort; if it fails OpenSSH will report a readable error.
            pass

        known_hosts_host = format_known_hosts_host(self._host, self._port)

        user_host = f"{self._username}@{self._host}" if self._username else self._host
        forward_spec = f"127.0.0.1:{self._local_port}:{self._remote_host}:{self._remote_port}"

        batch_mode = "no" if self._password else "yes"
        cmd = [
            self._ssh_path,
            "-N",
            "-L",
            forward_spec,
            "-p",
            str(self._port),
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            f"BatchMode={batch_mode}",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            f"UserKnownHostsFile={str(self._known_hosts_path)}",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=3",
        ]

        if self._private_key_path:
            cmd.extend(
                [
                    "-i",
                    str(Path(self._private_key_path).expanduser()),
                    "-o",
                    "IdentitiesOnly=yes",
                ]
            )

        if not self._use_agent:
            cmd.extend(["-o", "IdentityAgent=none"])

        if self._password:
            cmd.extend(
                [
                    "-o",
                    "PreferredAuthentications=keyboard-interactive,password",
                    "-o",
                    "PubkeyAuthentication=no",
                    "-o",
                    "NumberOfPasswordPrompts=1",
                ]
            )

        cmd.append(user_host)

        logger.info(
            "Starting OpenSSH tunnel: ssh=%s target=%s port=%s forward=%s known_hosts=%s",
            self._ssh_path,
            self._host,
            self._port,
            forward_spec,
            str(self._known_hosts_path),
        )

        # NOTE: We intentionally capture stderr for troubleshooting and error mapping.
        # stdout is not expected to be used when -N.
        creationflags = 0
        if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            # Prevent popping up a console window on Windows/Tauri.
            creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW"))

        env = None
        if self._password:
            self._askpass_helper = _OpenSSHAskpassHelper(self._password)
            env = self._askpass_helper.build_env()

        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=creationflags,
            env=env,
        )

        # Drain stderr in a background thread to avoid blocking if the buffer fills.
        # We keep only the last N lines for diagnostics.
        stderr_thread = None
        if self._proc.stderr is not None:
            stderr_thread = threading.Thread(
                target=self._drain_stderr,
                args=(self._proc.stderr,),
                daemon=True,
                name=f"openssh-stderr-{self._local_port}",
            )
            stderr_thread.start()

        # Quick health check: if the process exits immediately, we want a useful error.
        # We wait a short time to allow ExitOnForwardFailure / host key errors to surface.
        early_exit_deadline_s = 2.0
        # Avoid importing time at module level to keep file lightweight.
        import time

        t0 = time.time()
        while time.time() - t0 < early_exit_deadline_s:
            if self._stop_event.is_set():
                break
            if self._proc.poll() is not None:
                break
            time.sleep(0.05)

        if self._proc.poll() is not None:
            if stderr_thread is not None:
                try:
                    stderr_thread.join(timeout=0.5)
                except Exception:
                    pass

            normalized = self._get_stderr_snapshot().strip()
            logger.warning(
                "OpenSSH tunnel exited early: returncode=%s stderr=%s",
                self._proc.returncode,
                (normalized[:500] if normalized else ""),
            )

            # Map host key failures to the standard 409 flow.
            if self._is_host_key_failure(normalized):
                reason = "changed" if "REMOTE HOST IDENTIFICATION HAS CHANGED" in normalized else "unknown"

                # Best-effort: use ssh-keyscan to obtain the presented key for UI confirmation.
                presented = self._ssh_keyscan(host=self._host, port=self._port)
                if presented is None:
                    raise RuntimeError(
                        "Host key verification failed, but could not retrieve host key via ssh-keyscan"
                    )

                parsed = parse_openssh_public_key(presented)
                fingerprint = compute_fingerprint_sha256(parsed.key_bytes)

                expected_public_key = None
                expected_fingerprint = None
                if reason == "changed":
                    expected_key_base64 = find_known_host_key_base64(
                        host=self._host, port=self._port, key_type=parsed.key_type
                    )
                    if expected_key_base64:
                        expected_public_key = f"{parsed.key_type} {expected_key_base64}"
                        try:
                            expected_parsed = parse_openssh_public_key(expected_public_key)
                            expected_fingerprint = compute_fingerprint_sha256(expected_parsed.key_bytes)
                        except Exception:
                            expected_public_key = None
                            expected_fingerprint = None

                problem = HostKeyProblem(
                    host=self._host,
                    port=self._port,
                    known_hosts_host=known_hosts_host,
                    key_type=parsed.key_type,
                    fingerprint_sha256=fingerprint,
                    public_key=f"{parsed.key_type} {parsed.key_base64}",
                    reason=reason,
                    expected_fingerprint_sha256=expected_fingerprint,
                    expected_public_key=expected_public_key,
                )

                raise HostKeyConfirmationRequiredError(problem)

            raise RuntimeError(
                f"OpenSSH tunnel failed to start (returncode={self._proc.returncode}): {normalized}"
            )

        # Main loop: keep the ssh process alive until stop_event is set.
        try:
            while not self._stop_event.is_set():
                if self._proc.poll() is not None:
                    # Process exited unexpectedly; stop the tunnel thread.
                    logger.warning(
                        "OpenSSH tunnel process exited unexpectedly: returncode=%s",
                        self._proc.returncode,
                    )
                    break
                time.sleep(0.2)
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the ssh tunnel process."""

        self._stop_event.set()

        proc = self._proc
        self._proc = None

        if proc is None:
            if self._askpass_helper is not None:
                self._askpass_helper.cleanup()
                self._askpass_helper = None
            return

        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except Exception:
                    proc.kill()
        except Exception:
            # Best effort termination.
            pass

        try:
            if proc.stderr is not None:
                proc.stderr.close()
        except Exception:
            pass

        if self._askpass_helper is not None:
            self._askpass_helper.cleanup()
            self._askpass_helper = None

    @staticmethod
    def _is_host_key_failure(stderr: str) -> bool:
        s = stderr or ""
        if "Host key verification failed" in s:
            return True
        if "REMOTE HOST IDENTIFICATION HAS CHANGED" in s:
            return True
        if "requested strict checking" in s and "host key" in s:
            return True
        return False

    @staticmethod
    def _ssh_keyscan(*, host: str, port: int) -> Optional[str]:
        """Best-effort ssh-keyscan to obtain the presented host key.

        Returns:
            A string like '<key_type> <base64>' or None.
        """

        keyscan = shutil.which("ssh-keyscan")
        if not keyscan:
            return None

        try:
            creationflags = 0
            if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
                creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW"))

            res = subprocess.run(
                [keyscan, "-p", str(port), "-T", "5", host],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
                creationflags=creationflags,
            )
        except Exception:
            return None

        if res.returncode != 0:
            return None

        for raw in (res.stdout or "").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) < 3:
                continue

            # ssh-keyscan returns: <host> <key_type> <base64>
            key_type = parts[1]
            key_base64 = parts[2]
            return f"{key_type} {key_base64}"

        return None

    def _drain_stderr(self, stream: Any) -> None:
        """Continuously read stderr and keep last lines for troubleshooting."""

        try:
            for raw in stream:
                line = (raw or "").rstrip("\n")
                if not line:
                    continue
                with self._stderr_lock:
                    self._stderr_lines.append(line)
                    # Keep only last 200 lines.
                    if len(self._stderr_lines) > 200:
                        self._stderr_lines = self._stderr_lines[-200:]
        except Exception:
            return

    def _get_stderr_snapshot(self) -> str:
        with self._stderr_lock:
            return "\n".join(self._stderr_lines)


class OpenSSHBackend(SshBackend):
    """OpenSSH-based backend for command execution and tunneling.

    NOTE:
    - Remote commands prefer the system OpenSSH client.
    - SFTP remains available through the connection's lazy Paramiko fallback.
    """

    def __init__(self, ssh_path: Optional[str] = None):
        self._ssh_path = ssh_path

    @staticmethod
    def _resolve_ssh_path(explicit_path: Optional[str]) -> Optional[str]:
        """Resolve the ssh executable path.

        Priority:
        1) explicit_path
        2) env RUNICORN_SSH_PATH
        3) PATH lookup
        """

        candidates: List[str] = []
        if explicit_path:
            candidates.append(explicit_path)

        env_path = os.environ.get("RUNICORN_SSH_PATH")
        if env_path:
            candidates.append(env_path)

        which = shutil.which("ssh")
        if which:
            candidates.append(which)

        for cand in candidates:
            try:
                if not cand:
                    continue
                # Accept a direct path or a command name.
                resolved = cand
                if os.path.sep in cand or (os.name == "nt" and ":" in cand):
                    if not Path(cand).exists():
                        continue
                # Probe availability.
                creationflags = 0
                if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
                    creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW"))
                res = subprocess.run(
                    [resolved, "-V"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    creationflags=creationflags,
                )
                if res.returncode == 0 or (res.stderr and "OpenSSH" in res.stderr):
                    return resolved
            except Exception:
                continue

        return None

    def connect(self, config: "SSHConfig") -> SshConnection:
        conn = OpenSSHCommandConnection(config, ssh_path=self._ssh_path)
        conn.connect()
        return conn

    def create_tunnel(
        self,
        *,
        connection: SshConnection,
        local_port: int,
        remote_host: str,
        remote_port: int,
        stop_event: threading.Event,
    ) -> SshTunnel:
        from ..config import get_known_hosts_file_path

        ssh_path = self._resolve_ssh_path(self._ssh_path)
        if not ssh_path:
            raise OpenSSHFallbackError("OpenSSH client not available")

        # For the Phase 0/1 flow we require ssh-keyscan to construct the 409 host key payload
        # in unknown/changed scenarios. If it's not available, fall back to Paramiko.
        if not shutil.which("ssh-keyscan"):
            raise OpenSSHFallbackError("ssh-keyscan not available")

        cfg = connection.config

        known_hosts = get_known_hosts_file_path()

        return OpenSSHTunnel(
            ssh_path=ssh_path,
            host=cfg.host,
            port=cfg.port,
            username=cfg.username,
            password=getattr(cfg, "password", None),
            private_key_path=getattr(cfg, "private_key_path", None),
            use_agent=getattr(cfg, "use_agent", True),
            local_port=local_port,
            remote_host=remote_host,
            remote_port=remote_port,
            known_hosts_path=known_hosts,
            stop_event=stop_event,
        )


class AsyncSSHTunnel:
    """SSH local port forwarding implemented via AsyncSSH.

    This tunnel runs an asyncio event loop inside the tunnel thread.

    Security:
    - Host key verification is enforced by validating against Runicorn-managed
      known_hosts file.
    - Binds the local forwarded port to 127.0.0.1 only.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: Optional[str],
        private_key: Optional[str],
        private_key_path: Optional[str],
        passphrase: Optional[str],
        use_agent: bool,
        timeout: int,
        keepalive_interval: int,
        local_port: int,
        remote_host: str,
        remote_port: int,
        known_hosts_path: Path,
        stop_event: threading.Event,
    ):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._private_key = private_key
        self._private_key_path = private_key_path
        self._passphrase = passphrase
        self._use_agent = use_agent
        self._timeout = timeout
        self._keepalive_interval = keepalive_interval
        self._local_port = local_port
        self._remote_host = remote_host
        self._remote_port = remote_port
        self._known_hosts_path = known_hosts_path
        self._stop_event = stop_event

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._conn: Any = None
        self._listener: Any = None
        self._start_error: Optional[BaseException] = None

    def start(self) -> None:
        """Start the tunnel and block until stop_event is set."""

        loop = asyncio.new_event_loop()
        self._loop = loop

        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._run())
        finally:
            try:
                loop.stop()
            except Exception:
                pass
            try:
                loop.close()
            except Exception:
                pass

    def stop(self) -> None:
        """Signal the tunnel to stop."""

        self._stop_event.set()

        loop = self._loop
        if loop is None:
            return

        try:
            loop.call_soon_threadsafe(lambda: None)
        except Exception:
            pass

    async def _run(self) -> None:
        from .host_key import HostKeyConfirmationRequiredError

        try:
            await self._start_asyncssh_tunnel()
        except BaseException as e:
            self._start_error = e
            raise

        # Wait until stopped.
        await self._wait_stop_event()

        await self._shutdown_asyncssh_tunnel()

        # If a host key confirmation was raised during startup it should have
        # already propagated. This is here for defensive completeness.
        if isinstance(self._start_error, HostKeyConfirmationRequiredError):
            raise self._start_error

    async def _wait_stop_event(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._stop_event.wait)

    async def _start_asyncssh_tunnel(self) -> None:
        """Open AsyncSSH connection and create local port forwarding."""

        try:
            import asyncssh
            from asyncssh.client import SSHClient
            from asyncssh.known_hosts import match_known_hosts
            from asyncssh.misc import HostKeyNotVerifiable
        except Exception as e:
            raise RuntimeError(
                "AsyncSSH is required for AsyncSSHBackend but is not available"
            ) from e

        from .host_key import HostKeyConfirmationRequiredError, HostKeyProblem
        from .known_hosts import compute_fingerprint_sha256, format_known_hosts_host

        known_hosts_path = self._known_hosts_path
        try:
            known_hosts_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        host_key_problem: dict = {"problem": None}

        class _RunicornSSHClient(SSHClient):
            def validate_host_public_key(self, host: str, addr: str, port: int, key: Any) -> bool:
                # Validate server host key against Runicorn known_hosts.
                # We intentionally build the same 409 payload as the Paramiko/OpenSSH flows.
                key_type = key.get_algorithm()
                key_bytes = key.public_data
                key_base64 = base64.b64encode(key_bytes).decode("ascii")

                try:
                    result = match_known_hosts(str(known_hosts_path), host, addr, port)
                    host_keys = result[0]
                except Exception:
                    host_keys = []

                for hk in host_keys:
                    try:
                        if hk.public_data == key_bytes:
                            return True
                    except Exception:
                        continue

                reason = "changed" if host_keys else "unknown"

                expected_public_key = None
                expected_fingerprint = None
                if reason == "changed":
                    try:
                        expected = None
                        for hk in host_keys:
                            try:
                                if hk.get_algorithm() == key_type:
                                    expected = hk
                                    break
                            except Exception:
                                continue
                        if expected is None and host_keys:
                            expected = host_keys[0]
                        expected_key_type = expected.get_algorithm()
                        expected_key_base64 = base64.b64encode(expected.public_data).decode("ascii")
                        expected_public_key = f"{expected_key_type} {expected_key_base64}"
                        expected_fingerprint = compute_fingerprint_sha256(expected.public_data)
                    except Exception:
                        expected_public_key = None
                        expected_fingerprint = None

                problem = HostKeyProblem(
                    host=host,
                    port=port,
                    known_hosts_host=format_known_hosts_host(host, port),
                    key_type=key_type,
                    fingerprint_sha256=compute_fingerprint_sha256(key_bytes),
                    public_key=f"{key_type} {key_base64}",
                    reason=reason,
                    expected_fingerprint_sha256=expected_fingerprint,
                    expected_public_key=expected_public_key,
                )

                # Store the problem so that if AsyncSSH wraps this as HostKeyNotVerifiable
                # we can still surface a stable 409 payload to the API layer.
                host_key_problem["problem"] = problem
                return False

        # Build client_keys argument.
        client_keys: Optional[List[Any]] = None
        if self._private_key_path:
            client_keys = [self._private_key_path]
        elif self._private_key:
            # AsyncSSH accepts key data as bytes.
            client_keys = [self._private_key.encode("utf-8")]

        logger.info(
            "Starting AsyncSSH tunnel: target=%s port=%s local_port=%s remote=%s:%s",
            self._host,
            self._port,
            self._local_port,
            self._remote_host,
            self._remote_port,
        )

        # NOTE: We pass known_hosts=None and implement our own validation callback.
        # This ensures we can always build the 409 payload with the presented host key.
        try:
            connect_kwargs: dict = {
                "port": self._port,
                "username": self._username,
                "password": self._password,
                "client_keys": client_keys,
                "passphrase": self._passphrase,
                "known_hosts": None,
                "client_factory": _RunicornSSHClient,
                "login_timeout": self._timeout,
                "keepalive_interval": self._keepalive_interval,
            }

            # Only pass agent_path when we explicitly want to disable the SSH agent.
            # When enabled, we let AsyncSSH use its default behavior.
            if not self._use_agent:
                connect_kwargs["agent_path"] = None

            self._conn = await asyncssh.connect(self._host, **connect_kwargs)
        except Exception as e:
            # Normalize host key issues to the existing 409 protocol.
            problem = host_key_problem.get("problem")
            try:
                if isinstance(e, HostKeyNotVerifiable) and problem is not None:
                    raise HostKeyConfirmationRequiredError(problem) from e
            except Exception:
                # If asyncssh.misc isn't available or type checks fail, just fall through.
                pass
            raise

        self._listener = await self._conn.forward_local_port(
            "127.0.0.1",
            self._local_port,
            self._remote_host,
            self._remote_port,
        )

    async def _shutdown_asyncssh_tunnel(self) -> None:
        listener = self._listener
        self._listener = None
        if listener is not None:
            try:
                listener.close()
                if hasattr(listener, "wait_closed"):
                    await listener.wait_closed()
            except Exception:
                pass

        conn = self._conn
        self._conn = None
        if conn is not None:
            try:
                conn.close()
                await conn.wait_closed()
            except Exception:
                pass


class AsyncSSHBackend(SshBackend):
    """AsyncSSH-based backend.

    For now, this backend is used for tunneling only.
    Remote command execution/SFTP still uses the existing Paramiko connection.
    """

    def connect(self, config: "SSHConfig") -> SshConnection:
        # Keep using Paramiko for exec_command/SFTP until a full migration is done.
        return ParamikoBackend().connect(config)

    def create_tunnel(
        self,
        *,
        connection: SshConnection,
        local_port: int,
        remote_host: str,
        remote_port: int,
        stop_event: threading.Event,
    ) -> SshTunnel:
        from ..config import get_known_hosts_file_path

        cfg = connection.config
        known_hosts = get_known_hosts_file_path()

        return AsyncSSHTunnel(
            host=cfg.host,
            port=cfg.port,
            username=cfg.username,
            password=getattr(cfg, "password", None),
            private_key=getattr(cfg, "private_key", None),
            private_key_path=getattr(cfg, "private_key_path", None),
            passphrase=getattr(cfg, "passphrase", None),
            use_agent=getattr(cfg, "use_agent", True),
            timeout=getattr(cfg, "timeout", 30),
            keepalive_interval=getattr(cfg, "keepalive_interval", 30),
            local_port=local_port,
            remote_host=remote_host,
            remote_port=remote_port,
            known_hosts_path=known_hosts,
            stop_event=stop_event,
        )


class OpenSSHCommandConnection:
    """Command-oriented SSH connection implemented via the system OpenSSH client.

    This connection intentionally focuses on command execution first. SFTP remains
    available through a lazy Paramiko fallback so that existing file APIs keep
    working while command paths move off Paramiko.
    """

    _HEALTH_CHECK_TTL_S = 5.0

    def __init__(self, config: "SSHConfig", ssh_path: Optional[str] = None):
        self.config = config
        self.env_cache: dict[str, Any] = {}
        self._ssh_path = ssh_path
        self._connected = False
        self._last_health_check = 0.0
        self._lock = threading.Lock()
        self._paramiko_fallback: Optional[SshConnection] = None

    def connect(self) -> bool:
        with self._lock:
            if self._connected and self._check_health_locked():
                return True

            try:
                self._run_ssh_command("exit 0", timeout=self.config.timeout)
                self._connected = True
                self._last_health_check = time.monotonic()
                logger.info("OpenSSH command connection ready: %s", self.config.get_key())
                return True
            except Exception:
                self._connected = False
                self._last_health_check = 0.0
                raise

    def disconnect(self) -> None:
        with self._lock:
            self._connected = False
            self._last_health_check = 0.0

            if self._paramiko_fallback is not None:
                try:
                    self._paramiko_fallback.disconnect()
                except Exception as e:
                    logger.warning(f"Error closing Paramiko fallback SSH connection: {e}")
                self._paramiko_fallback = None

            logger.info("OpenSSH command connection disconnected: %s", self.config.get_key())

    def exec_command(self, command: str, timeout: Optional[int] = None) -> Tuple[str, str, int]:
        if not self._connected:
            raise RuntimeError("Not connected to SSH server")

        try:
            stdout, stderr, exit_code = self._run_ssh_command(
                command,
                timeout=timeout or self.config.timeout,
            )
        except Exception:
            with self._lock:
                self._connected = False
                self._last_health_check = 0.0
            raise

        with self._lock:
            self._connected = True
            self._last_health_check = time.monotonic()

        return stdout, stderr, exit_code

    def get_sftp(self) -> Any:
        with self._lock:
            if self._paramiko_fallback is None:
                logger.info(
                    "Creating Paramiko fallback connection for SFTP: %s",
                    self.config.get_key(),
                )
                self._paramiko_fallback = ParamikoBackend().connect(self.config)

            return self._paramiko_fallback.get_sftp()

    @property
    def is_connected(self) -> bool:
        with self._lock:
            if not self._connected:
                return False
            if time.monotonic() - self._last_health_check <= self._HEALTH_CHECK_TTL_S:
                return True

            healthy = self._check_health_locked()
            self._connected = healthy
            if healthy:
                self._last_health_check = time.monotonic()
            return healthy

    def get_paramiko_fallback_connection(self) -> SshConnection:
        with self._lock:
            if self._paramiko_fallback is None:
                logger.info(
                    "Creating Paramiko fallback connection for tunnel/SFTP: %s",
                    self.config.get_key(),
                )
                self._paramiko_fallback = ParamikoBackend().connect(self.config)
            return self._paramiko_fallback

    def _check_health_locked(self) -> bool:
        try:
            self._run_ssh_command("exit 0", timeout=min(self.config.timeout, 5))
            return True
        except Exception:
            return False

    def _run_ssh_command(self, command: str, timeout: int) -> Tuple[str, str, int]:
        cmd = self._build_ssh_command(command)
        creationflags = 0
        if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW"))

        askpass_helper: Optional[_OpenSSHAskpassHelper] = None
        env = None
        if self.config.password:
            askpass_helper = _OpenSSHAskpassHelper(self.config.password)
            env = askpass_helper.build_env()

        try:
            result = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
                creationflags=creationflags,
                env=env,
            )
        except subprocess.TimeoutExpired as e:
            logger.warning("OpenSSH command timed out: host=%s cmd=%s", self.config.host, command)
            raise TimeoutError(
                f"OpenSSH command timed out after {timeout}s: {command}"
            ) from e
        except Exception as e:
            logger.error(f"Failed to launch OpenSSH command: {e}")
            raise RuntimeError(f"Failed to launch OpenSSH client: {e}") from e
        finally:
            if askpass_helper is not None:
                askpass_helper.cleanup()

        stdout = result.stdout or ""
        stderr = result.stderr or ""

        if OpenSSHTunnel._is_host_key_failure(stderr):
            raise self._build_host_key_error(stderr)

        if self._is_transport_failure(result.returncode, stderr):
            raise RuntimeError(stderr.strip() or "OpenSSH transport failed")

        return stdout, stderr, int(result.returncode)

    def _build_ssh_command(self, remote_command: str) -> List[str]:
        from ..config import get_known_hosts_file_path

        self._ensure_supported()

        ssh_path = OpenSSHBackend._resolve_ssh_path(self._ssh_path)
        if not ssh_path:
            raise OpenSSHFallbackError("OpenSSH client not available")

        known_hosts_path = get_known_hosts_file_path()
        try:
            known_hosts_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        user_host = f"{self.config.username}@{self.config.host}" if self.config.username else self.config.host

        cmd = [
            ssh_path,
            "-T",
            "-p",
            str(self.config.port),
            "-o",
            f"BatchMode={'no' if self.config.password else 'yes'}",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            f"UserKnownHostsFile={str(known_hosts_path)}",
            "-o",
            f"ConnectTimeout={max(int(self.config.timeout), 1)}",
            "-o",
            f"ServerAliveInterval={max(int(self.config.keepalive_interval), 1)}",
            "-o",
            "ServerAliveCountMax=3",
        ]

        if self.config.private_key_path:
            cmd.extend(
                [
                    "-i",
                    str(Path(self.config.private_key_path).expanduser()),
                    "-o",
                    "IdentitiesOnly=yes",
                ]
            )

        if not self.config.use_agent:
            cmd.extend(["-o", "IdentityAgent=none"])

        if self.config.password:
            cmd.extend(
                [
                    "-o",
                    "PreferredAuthentications=keyboard-interactive,password",
                    "-o",
                    "PubkeyAuthentication=no",
                    "-o",
                    "NumberOfPasswordPrompts=1",
                ]
            )

        cmd.extend([user_host, remote_command])
        return cmd

    def _ensure_supported(self) -> None:
        if self.config.private_key:
            raise OpenSSHFallbackError("OpenSSH command connection does not support inline private keys")
        if not shutil.which("ssh-keyscan"):
            raise OpenSSHFallbackError("ssh-keyscan not available")

    def _build_host_key_error(self, stderr: str) -> Exception:
        from .host_key import HostKeyConfirmationRequiredError, HostKeyProblem
        from .known_hosts import (
            compute_fingerprint_sha256,
            find_known_host_key_base64,
            format_known_hosts_host,
            parse_openssh_public_key,
        )

        reason = "changed" if "REMOTE HOST IDENTIFICATION HAS CHANGED" in stderr else "unknown"
        presented = OpenSSHTunnel._ssh_keyscan(host=self.config.host, port=self.config.port)
        if presented is None:
            return RuntimeError(
                "Host key verification failed, but could not retrieve host key via ssh-keyscan"
            )

        parsed = parse_openssh_public_key(presented)
        expected_public_key = None
        expected_fingerprint = None
        if reason == "changed":
            expected_key_base64 = find_known_host_key_base64(
                host=self.config.host,
                port=self.config.port,
                key_type=parsed.key_type,
            )
            if expected_key_base64:
                expected_public_key = f"{parsed.key_type} {expected_key_base64}"
                try:
                    expected_parsed = parse_openssh_public_key(expected_public_key)
                    expected_fingerprint = compute_fingerprint_sha256(expected_parsed.key_bytes)
                except Exception:
                    expected_public_key = None
                    expected_fingerprint = None

        problem = HostKeyProblem(
            host=self.config.host,
            port=self.config.port,
            known_hosts_host=format_known_hosts_host(self.config.host, self.config.port),
            key_type=parsed.key_type,
            fingerprint_sha256=compute_fingerprint_sha256(parsed.key_bytes),
            public_key=f"{parsed.key_type} {parsed.key_base64}",
            reason=reason,
            expected_fingerprint_sha256=expected_fingerprint,
            expected_public_key=expected_public_key,
        )
        return HostKeyConfirmationRequiredError(problem)

    @staticmethod
    def _is_transport_failure(returncode: int, stderr: str) -> bool:
        if returncode != 255:
            return False

        markers = [
            "Permission denied",
            "Could not resolve hostname",
            "Connection refused",
            "Connection timed out",
            "No route to host",
            "Connection closed by",
            "Connection reset by",
            "Broken pipe",
            "kex_exchange_identification",
            "Host key verification failed",
        ]
        return any(marker in stderr for marker in markers)


class AutoBackend(SshBackend):
    """Backend selector.

    This class is designed as a pragmatic migration step:
    - Prefer OpenSSH for tunneling when possible.
    - Fall back to AsyncSSH when OpenSSH is unavailable or unsupported for the current config.
    - Fall back to Paramiko as the last resort.

    Fallback order:
    OpenSSH -> AsyncSSH -> Paramiko
    """

    def __init__(self, openssh_backend: Optional[OpenSSHBackend] = None):
        self._openssh = openssh_backend or OpenSSHBackend()
        self._asyncssh = AsyncSSHBackend()
        self._paramiko = ParamikoBackend()

    def connect(self, config: "SSHConfig") -> SshConnection:
        try:
            return self._openssh.connect(config)
        except OpenSSHFallbackError as e:
            logger.info(
                "Falling back from OpenSSH connection backend: reason=%s",
                str(e),
            )
            return self._paramiko.connect(config)

    def create_tunnel(
        self,
        *,
        connection: SshConnection,
        local_port: int,
        remote_host: str,
        remote_port: int,
        stop_event: threading.Event,
    ) -> SshTunnel:
        from .host_key import HostKeyConfirmationRequiredError

        try:
            return self._openssh.create_tunnel(
                connection=connection,
                local_port=local_port,
                remote_host=remote_host,
                remote_port=remote_port,
                stop_event=stop_event,
            )
        except OpenSSHFallbackError as e:
            if isinstance(e, HostKeyConfirmationRequiredError):
                raise

            logger.info(
                "Falling back from OpenSSH tunnel backend: reason=%s",
                str(e),
            )

        try:
            return self._asyncssh.create_tunnel(
                connection=connection,
                local_port=local_port,
                remote_host=remote_host,
                remote_port=remote_port,
                stop_event=stop_event,
            )
        except Exception as e:
            if isinstance(e, HostKeyConfirmationRequiredError):
                raise

            logger.info(
                "Falling back from AsyncSSH tunnel backend: reason=%s",
                str(e),
            )

        fallback_connection = connection
        get_paramiko_fallback_connection = getattr(
            connection,
            "get_paramiko_fallback_connection",
            None,
        )
        if callable(get_paramiko_fallback_connection):
            fallback_connection = get_paramiko_fallback_connection()

        return self._paramiko.create_tunnel(
            connection=fallback_connection,
            local_port=local_port,
            remote_host=remote_host,
            remote_port=remote_port,
            stop_event=stop_event,
        )
