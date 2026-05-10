"""
Remote Viewer Manager

Manages remote viewer sessions with SSH tunnel.
"""
from __future__ import annotations

import logging
import shlex
import threading
import time
import uuid
from typing import Optional, Dict

from ..host_key import HostKeyConfirmationRequiredError
from ..ssh_backend import SshBackend, AutoBackend, SshConnection
from .session import (
    RemoteViewerSession,
    STATUS_RUNNING,
    STATUS_RECONNECTING,
    STATUS_DEGRADED,
    STATUS_DISCONNECTED,
    STATUS_STOPPED,
)
from .tunnel import find_available_port

logger = logging.getLogger(__name__)

# Tunnel reconnect parameters.
_TUNNEL_MAX_RETRIES = 10
_TUNNEL_MAX_BACKOFF_S = 60

# Health monitor parameters.
_HEALTH_CHECK_INTERVAL_S = 30
_MAX_PROCESS_RESTART_ATTEMPTS = 3
_REMOTE_VIEWER_PYTHON_CHECK_MIN_TIMEOUT_S = 30
_REMOTE_VIEWER_RUNICORN_IMPORT_MIN_TIMEOUT_S = 120
_REMOTE_VIEWER_PORT_DISCOVERY_MIN_TIMEOUT_S = 30
_REMOTE_VIEWER_START_COMMAND_MIN_TIMEOUT_S = 30
_REMOTE_VIEWER_STARTUP_GRACE_S = 2
_REMOTE_VIEWER_HEALTH_MIN_TIMEOUT_S = 45
_REMOTE_VIEWER_HEALTH_PROBE_TIMEOUT_S = 6
_REMOTE_VIEWER_LOG_ROOT = "/tmp/runicorn-viewer"


class RemoteViewerManager:
    """
    Manager for Remote Viewer sessions.
    
    Handles:
    - Starting remote viewer process
    - Creating SSH tunnel
    - Session lifecycle management
    - Health monitoring (process + tunnel)
    - Automatic tunnel reconnection
    """
    
    def __init__(self, backend: Optional[SshBackend] = None):
        self._sessions: Dict[str, RemoteViewerSession] = {}
        self._lock = threading.Lock()
        # Prefer OpenSSH for port forwarding when possible.
        # Fallback logic is handled inside AutoBackend.
        self._backend = backend or AutoBackend()
        
        # Health monitor thread — started lazily on first session.
        self._health_thread: Optional[threading.Thread] = None
        self._health_stop = threading.Event()

    def _get_command_timeout(self, connection: SshConnection, minimum: int) -> int:
        configured = getattr(getattr(connection, "config", None), "timeout", 0)
        try:
            configured_timeout = int(configured)
        except (TypeError, ValueError):
            configured_timeout = 0
        return max(configured_timeout, minimum)
    
    def start_remote_viewer(
        self,
        connection: SshConnection,
        remote_root: str,
        local_port: Optional[int] = None,
        remote_port: Optional[int] = None,
        python_cmd: Optional[str] = None,
    ) -> RemoteViewerSession:
        """
        Start a remote viewer session.
        
        Steps:
        1. Check remote Python environment
        2. Find available remote port
        3. Start remote viewer process
        4. Find available local port
        5. Create SSH tunnel
        6. Verify health
        
        Args:
            connection: SSH connection to use
            remote_root: Remote storage root path
            local_port: Local port (auto-detect if None)
            remote_port: Remote port (auto-detect if None)
            python_cmd: Python command to use (auto-detect if None)
            
        Returns:
            RemoteViewerSession instance
            
        Raises:
            RuntimeError: If remote viewer cannot be started
        """
        if not connection.is_connected:
            raise RuntimeError("SSH connection is not active")
        
        session_id = str(uuid.uuid4())[:8]
        
        try:
            # Step 1: Check Python availability
            logger.info(f"[{session_id}] Checking remote Python...")
            if not python_cmd:
                python_cmd = self._find_python(connection)
                if not python_cmd:
                    raise RuntimeError("Python3 not found on remote server")
            logger.info(f"[{session_id}] Using Python: {python_cmd}")
            
            # Step 2: Check runicorn installation
            logger.info(f"[{session_id}] Checking runicorn installation...")
            remote_version = self._get_remote_runicorn_version(connection, python_cmd)
            logger.info(f"[{session_id}] Remote runicorn version: {remote_version}")
            
            # Step 3: Find available remote port
            if not remote_port:
                remote_port = self._find_remote_available_port(connection)
            logger.info(f"[{session_id}] Using remote port: {remote_port}")
            
            # Step 4: Start remote viewer process
            logger.info(f"[{session_id}] Starting remote viewer...")
            remote_pid = self._start_remote_viewer_process(
                connection,
                python_cmd,
                remote_root,
                remote_port,
                session_id
            )
            logger.info(f"[{session_id}] Remote viewer started (PID: {remote_pid})")
            
            # Step 5: Wait for viewer to be ready
            time.sleep(_REMOTE_VIEWER_STARTUP_GRACE_S)  # Give viewer time to start
            if not self._check_remote_viewer_health(
                connection,
                remote_port,
                session_id=session_id,
            ):
                raise RuntimeError("Remote viewer failed health check")
            logger.info(f"[{session_id}] Remote viewer is healthy")
            
            # Step 6: Find available local port
            if not local_port:
                local_port = find_available_port()
            logger.info(f"[{session_id}] Using local port: {local_port}")
            
            # Step 7: Create SSH tunnel
            logger.info(f"[{session_id}] Creating SSH tunnel...")
            ssh_host = connection.config.host
            session = RemoteViewerSession(
                session_id=session_id,
                connection=connection,
                remote_host=ssh_host,
                remote_port=remote_port,
                local_port=local_port,
                remote_root=remote_root,
                remote_pid=remote_pid,
                python_cmd=python_cmd,
            )
            
            # Start tunnel in separate thread (with auto-reconnect).
            # The first tunnel is created synchronously so that early failures
            # (host key, bind errors) can be reported back to the API caller.
            tunnel = self._backend.create_tunnel(
                connection=connection,
                local_port=local_port,
                remote_host="127.0.0.1",
                remote_port=remote_port,
                stop_event=session._stop_event,
            )

            # Capture tunnel errors (especially HostKeyConfirmationRequiredError) and
            # re-raise them in the main thread, so that API layer can return HTTP 409.
            tunnel_error: Dict[str, BaseException] = {}

            def _tunnel_runner_with_reconnect() -> None:
                """Run the tunnel with automatic reconnection on failure."""
                current_tunnel = tunnel
                retry_count = 0
                first_run = True

                while not session._stop_event.is_set():
                    _tunnel_up_ts = time.time()
                    try:
                        current_tunnel.start()  # Blocks until disconnect/error.
                    except BaseException as e:
                        if first_run:
                            # First attempt: propagate error to start_remote_viewer.
                            tunnel_error["error"] = e
                            return
                        if isinstance(e, HostKeyConfirmationRequiredError):
                            # Never retry host key problems.
                            logger.warning(
                                f"[{session_id}] Tunnel host key error, not retrying"
                            )
                            session.status = STATUS_DISCONNECTED
                            return
                        logger.warning(
                            f"[{session_id}] Tunnel error: {e}"
                        )

                    first_run = False

                    # If the (re)connected tunnel stayed up for a meaningful
                    # period, reset the retry budget so that transient
                    # failures later in the session also get full retries.
                    _tunnel_duration = time.time() - _tunnel_up_ts
                    if retry_count > 0 and _tunnel_duration > _TUNNEL_MAX_BACKOFF_S:
                        logger.debug(
                            f"[{session_id}] Tunnel was up for "
                            f"{_tunnel_duration:.0f}s, resetting retry counter"
                        )
                        retry_count = 0

                    if session._stop_event.is_set():
                        break

                    # --- Reconnect loop ---
                    if retry_count >= _TUNNEL_MAX_RETRIES:
                        logger.error(
                            f"[{session_id}] Tunnel reconnect failed after "
                            f"{_TUNNEL_MAX_RETRIES} attempts"
                        )
                        session.status = STATUS_DISCONNECTED
                        return

                    session.status = STATUS_RECONNECTING
                    backoff = min(2 ** retry_count, _TUNNEL_MAX_BACKOFF_S)
                    logger.info(
                        f"[{session_id}] Tunnel lost, reconnecting in {backoff}s "
                        f"(attempt {retry_count + 1}/{_TUNNEL_MAX_RETRIES})"
                    )

                    # Wait with interruptible sleep.
                    if session._stop_event.wait(timeout=backoff):
                        break

                    # If the underlying SSH connection is dead, try to
                    # re-establish it before rebuilding the tunnel.
                    if not connection.is_connected:
                        try:
                            logger.info(
                                f"[{session_id}] SSH connection lost, reconnecting..."
                            )
                            connection.connect()
                        except Exception as conn_err:
                            logger.warning(
                                f"[{session_id}] SSH reconnect failed: {conn_err}"
                            )
                            retry_count += 1
                            continue

                    # Rebuild the tunnel instance (the old one's resources
                    # are released when start() returns).
                    try:
                        # Check if a stop was requested while we were
                        # reconnecting (closes a race with stop()).
                        if session.status in (STATUS_STOPPED, STATUS_DISCONNECTED):
                            break
                        # Reset the stop event for the new tunnel.
                        session._stop_event = threading.Event()
                        current_tunnel = self._backend.create_tunnel(
                            connection=connection,
                            local_port=local_port,
                            remote_host="127.0.0.1",
                            remote_port=remote_port,
                            stop_event=session._stop_event,
                        )
                    except Exception as create_err:
                        logger.warning(
                            f"[{session_id}] Failed to create new tunnel: {create_err}"
                        )
                        retry_count += 1
                        continue

                    logger.info(
                        f"[{session_id}] New tunnel created, starting..."
                    )
                    retry_count += 1

                # Thread exiting normally (stop event set).
                if session.status not in (STATUS_STOPPED, STATUS_DISCONNECTED):
                    session.status = STATUS_STOPPED

            tunnel_thread = threading.Thread(
                target=_tunnel_runner_with_reconnect,
                daemon=True,
                name=f"tunnel-{session_id}",
            )
            tunnel_thread.start()
            session.tunnel_thread = tunnel_thread
            
            # Verify tunnel startup.
            # We poll for a short time so that early failures (host key, bind errors, etc.)
            # can be reported back to the API caller.
            deadline_s = 2.0
            t0 = time.time()
            while time.time() - t0 < deadline_s:
                err = tunnel_error.get("error")
                if err is not None:
                    break
                if not tunnel_thread.is_alive():
                    break
                time.sleep(0.05)

            err = tunnel_error.get("error")
            if err is not None:
                # Raise host key confirmation errors to the API layer.
                if isinstance(err, HostKeyConfirmationRequiredError):
                    raise err
                raise RuntimeError(f"SSH tunnel failed: {str(err)}") from err

            if not tunnel_thread.is_alive():
                raise RuntimeError("SSH tunnel failed to start")
            
            logger.info(
                f"[{session_id}] Remote Viewer ready at http://localhost:{local_port}"
            )
            
            # Register session
            with self._lock:
                self._sessions[session_id] = session
            
            # Ensure the health monitor is running.
            self._ensure_health_monitor()
            
            return session
            
        except Exception as e:
            logger.error(f"[{session_id}] Failed to start remote viewer: {e}")
            # Cleanup on failure
            try:
                self._cleanup_remote_viewer(connection, session_id, remote_port)
            except Exception as cleanup_error:
                logger.warning(f"Cleanup error: {cleanup_error}")
            raise
    
    def stop_remote_viewer(self, session_id: str) -> bool:
        """
        Stop a remote viewer session.
        
        Args:
            session_id: Session ID to stop
            
        Returns:
            True if session was stopped
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
        
        try:
            logger.info(f"[{session_id}] Stopping remote viewer...")
            
            # Stop tunnel
            session.stop()
            
            # Kill remote viewer process
            if session.remote_pid:
                try:
                    session.connection.exec_command(f"kill {session.remote_pid}")
                    logger.info(f"[{session_id}] Killed remote process (PID: {session.remote_pid})")
                except Exception as e:
                    logger.warning(f"Failed to kill remote process: {e}")
            
            # Remove session
            with self._lock:
                del self._sessions[session_id]
            
            logger.info(f"[{session_id}] Remote viewer stopped")
            return True
            
        except Exception as e:
            logger.error(f"[{session_id}] Error stopping remote viewer: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[RemoteViewerSession]:
        """Get session by ID."""
        return self._sessions.get(session_id)
    
    def list_sessions(self) -> list[RemoteViewerSession]:
        """List all active sessions."""
        with self._lock:
            return list(self._sessions.values())
    
    def cleanup_dead_sessions(self, *, keep_disconnected: bool = True) -> int:
        """Remove inactive sessions. Returns count of removed sessions."""
        count = 0
        with self._lock:
            dead_sessions = [
                sid for sid, session in self._sessions.items()
                if not session.is_active
                and not (
                    keep_disconnected and session.status == STATUS_DISCONNECTED
                )
            ]
            for sid in dead_sessions:
                # Stop the session before removing it to avoid leaking tunnel threads
                # (OpenSSH tunnel is a subprocess managed by the tunnel thread).
                try:
                    self._sessions[sid].stop()
                except Exception:
                    pass
                del self._sessions[sid]
                count += 1
        
        if count > 0:
            logger.info(f"Cleaned up {count} dead sessions")
        return count
    
    # Helper methods
    
    def _find_python(self, connection: SshConnection) -> Optional[str]:
        """Find Python3 executable on remote."""
        for cmd in ["python3", "python"]:
            try:
                stdout, stderr, exit_code = connection.exec_command(
                    f"which {cmd}",
                    timeout=self._get_command_timeout(
                        connection,
                        _REMOTE_VIEWER_PYTHON_CHECK_MIN_TIMEOUT_S,
                    ),
                )
                if exit_code == 0 and stdout.strip():
                    # Verify it's Python 3
                    stdout2, _, exit_code2 = connection.exec_command(
                        f"{cmd} --version",
                        timeout=self._get_command_timeout(
                            connection,
                            _REMOTE_VIEWER_PYTHON_CHECK_MIN_TIMEOUT_S,
                        ),
                    )
                    if exit_code2 == 0 and "Python 3" in stdout2:
                        return cmd
            except Exception:
                continue
        return None

    def _get_remote_runicorn_version(
        self,
        connection: SshConnection,
        python_cmd: str,
    ) -> str:
        """Check that runicorn is importable in the target environment."""
        stdout, stderr, exit_code = connection.exec_command(
            f"{python_cmd} -c 'import runicorn; print(getattr(runicorn, \"__version__\", \"unknown\"))'",
            timeout=self._get_command_timeout(
                connection,
                _REMOTE_VIEWER_RUNICORN_IMPORT_MIN_TIMEOUT_S,
            ),
        )
        if exit_code != 0:
            raise RuntimeError(
                f"runicorn not installed on remote server.\n"
                f"Please install: {python_cmd} -m pip install runicorn"
            )
        return stdout.strip()
    
    def _find_remote_available_port(
        self, 
        connection: SshConnection, 
        start_port: int = 8080, 
        end_port: int = 9000
    ) -> int:
        """Find available port on remote server."""
        # Use Python to find available port
        script = f"""
import socket
for port in range({start_port}, {end_port}):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', port))
        sock.close()
        print(port)
        break
    except OSError:
        continue
"""
        stdout, stderr, exit_code = connection.exec_command(
            f"python3 -c \"{script}\"",
            timeout=self._get_command_timeout(
                connection,
                _REMOTE_VIEWER_PORT_DISCOVERY_MIN_TIMEOUT_S,
            ),
        )
        if exit_code == 0 and stdout.strip().isdigit():
            return int(stdout.strip())
        
        raise RuntimeError("No available port found on remote server")
    
    def _start_remote_viewer_process(
        self,
        connection: SshConnection,
        python_cmd: str,
        remote_root: str,
        remote_port: int,
        session_id: str,
    ) -> int:
        """Start remote viewer process and return PID."""
        remote_log_dir = f"{_REMOTE_VIEWER_LOG_ROOT}/sessions/{session_id}"
        bootstrap_log_path = f"{remote_log_dir}/bootstrap.log"
        viewer_log_path = f"{remote_log_dir}/viewer.log"
        pid_path = f"{remote_log_dir}/viewer.pid"

        process_cmd = (
            f"setsid env "
            f"RUNICORN_REMOTE_MODE=1 "
            f"RUNICORN_REMOTE_SESSION_ID={shlex.quote(session_id)} "
            f"RUNICORN_REMOTE_LOG_ROOT={shlex.quote(_REMOTE_VIEWER_LOG_ROOT)} "
            f"RUNICORN_REMOTE_LOG_DIR={shlex.quote(remote_log_dir)} "
            f"RUNICORN_LOG_FILE={shlex.quote(viewer_log_path)} "
            f"{shlex.quote(python_cmd)} -m runicorn viewer "
            f"--storage {shlex.quote(remote_root)} "
            f"--host 127.0.0.1 "
            f"--port {remote_port} "
            f"--remote-mode "
            f"--log-level INFO"
        )
        launcher_script = (
            f"{process_cmd} "
            f"< /dev/null "
            f"> {shlex.quote(bootstrap_log_path)} 2>&1 "
            f"& printf '%s\\n' \"$!\" > {shlex.quote(pid_path)}"
        )
        cmd = (
            f"mkdir -p {shlex.quote(remote_log_dir)} && "
            f"sh -c {shlex.quote(launcher_script)} && "
            f"cat {shlex.quote(pid_path)}"
        )
        
        logger.info(f"Starting remote viewer with command: {cmd}")
        stdout, stderr, exit_code = connection.exec_command(
            cmd,
            timeout=self._get_command_timeout(
                connection,
                _REMOTE_VIEWER_START_COMMAND_MIN_TIMEOUT_S,
            ),
        )
        
        if exit_code != 0:
            raise RuntimeError(f"Failed to start remote viewer: {stderr}")
        
        pid_str = stdout.strip()
        if not pid_str.isdigit():
            raise RuntimeError(f"Invalid PID returned: {pid_str}")
        
        return int(pid_str)
    
    def _check_remote_viewer_health(
        self,
        connection: SshConnection,
        remote_port: int,
        timeout: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> bool:
        """Check if remote viewer is responding."""
        logger.info(f"Health check: Testing port {remote_port} on remote server")
        wait_budget = timeout or self._get_command_timeout(
            connection,
            _REMOTE_VIEWER_HEALTH_MIN_TIMEOUT_S,
        )

        # Try to connect to the port
        cmd = f"timeout 5 bash -c 'cat < /dev/null > /dev/tcp/127.0.0.1/{remote_port}'"

        for attempt in range(wait_budget):
            try:
                stdout, stderr, exit_code = connection.exec_command(
                    cmd,
                    timeout=_REMOTE_VIEWER_HEALTH_PROBE_TIMEOUT_S,
                )
                logger.debug(
                    f"Health check attempt {attempt + 1}/{wait_budget}: "
                    f"exit_code={exit_code}, stderr={stderr[:100]}"
                )
                if exit_code == 0:
                    logger.info(f"Health check passed on attempt {attempt + 1}")
                    return True
            except Exception as e:
                logger.debug(f"Health check attempt {attempt + 1} exception: {e}")
            time.sleep(1)
        
        # If health check failed, try to get viewer process logs
        logger.error(f"Health check failed after {wait_budget} attempts")
        if session_id:
            remote_log_dir = f"{_REMOTE_VIEWER_LOG_ROOT}/sessions/{session_id}"
            for log_name in ("bootstrap.log", "viewer.log"):
                log_path = f"{remote_log_dir}/{log_name}"
                log_stdout, _, _ = connection.exec_command(
                    f"test -f {shlex.quote(log_path)} && "
                    f"tail -20 {shlex.quote(log_path)} || true"
                )
                if log_stdout.strip():
                    logger.error(f"Remote viewer {log_name}:\n{log_stdout}")
        
        return False
    
    def _cleanup_remote_viewer(
        self,
        connection: SshConnection,
        session_id: str,
        remote_port: Optional[int] = None
    ) -> None:
        """Cleanup remote viewer resources."""
        try:
            # Kill any viewer process listening on the port
            if remote_port:
                cmd = f"lsof -ti:{remote_port} | xargs -r kill"
                connection.exec_command(cmd)
        except Exception as e:
            logger.debug(f"Cleanup warning: {e}")
    
    # ------------------------------------------------------------------
    # Health monitor
    # ------------------------------------------------------------------

    def _ensure_health_monitor(self) -> None:
        """Start the health monitor thread if not already running."""
        if self._health_thread is not None and self._health_thread.is_alive():
            return
        self._health_stop.clear()
        self._health_thread = threading.Thread(
            target=self._health_monitor_loop,
            daemon=True,
            name="session-health-monitor",
        )
        self._health_thread.start()
        logger.info("Session health monitor started")

    def _health_monitor_loop(self) -> None:
        """Periodically check all sessions for process / tunnel health."""
        while not self._health_stop.is_set():
            if self._health_stop.wait(timeout=_HEALTH_CHECK_INTERVAL_S):
                break

            with self._lock:
                sessions = list(self._sessions.values())

            monitored_sessions = [
                session for session in sessions
                if not session._stop_event.is_set()
                and session.status not in (STATUS_STOPPED, STATUS_DISCONNECTED)
            ]

            if not monitored_sessions:
                # No sessions left that still need health monitoring.
                logger.info("No monitorable sessions - health monitor exiting")
                return

            for session in monitored_sessions:
                try:
                    self._check_session_health(session)
                except Exception as e:
                    logger.debug(
                        f"[{session.session_id}] Health check exception: {e}"
                    )

    def _check_session_health(self, session: RemoteViewerSession) -> None:
        """Check a single session's remote process and tunnel health."""
        sid = session.session_id
        session.last_health_check = time.time()

        # 1. Check remote process via `kill -0 <pid>`.
        process_alive = True
        if session.remote_pid and session.connection.is_connected:
            try:
                _, _, exit_code = session.connection.exec_command(
                    f"kill -0 {session.remote_pid}", timeout=10
                )
                process_alive = exit_code == 0
            except Exception:
                # SSH itself might be broken; the tunnel reconnect logic
                # will handle that case.
                process_alive = False

        if not process_alive:
            session.health_check_failed_count += 1
            logger.warning(
                f"[{sid}] Remote process (PID {session.remote_pid}) not alive "
                f"(fail count: {session.health_check_failed_count})"
            )

            if session._restart_count < _MAX_PROCESS_RESTART_ATTEMPTS:
                # Try to restart the remote viewer process.
                try:
                    new_pid = self._start_remote_viewer_process(
                        session.connection,
                        session.python_cmd,
                        session.remote_root,
                        session.remote_port,
                        sid,
                    )
                    session.remote_pid = new_pid
                    session._restart_count += 1
                    session.health_check_failed_count = 0
                    session.status = STATUS_RUNNING
                    logger.info(
                        f"[{sid}] Remote process restarted (new PID: {new_pid}, "
                        f"attempt {session._restart_count}/{_MAX_PROCESS_RESTART_ATTEMPTS})"
                    )
                    return
                except Exception as restart_err:
                    logger.warning(
                        f"[{sid}] Failed to restart remote process: {restart_err}"
                    )

            # Cannot restart — mark degraded.
            if session.status == STATUS_RUNNING:
                session.status = STATUS_DEGRADED
                logger.warning(f"[{sid}] Session marked as degraded")
            return

        # Process is alive — reset failure counter.
        if session.health_check_failed_count > 0:
            session.health_check_failed_count = 0

        # 2. Tunnel health is handled by the reconnect logic inside
        #    _tunnel_runner_with_reconnect.  If the tunnel thread itself
        #    has died (all retries exhausted), the status is already
        #    DISCONNECTED.  If it's reconnecting, leave it alone.
        if session.status == STATUS_DEGRADED and session.connection.is_connected:
            # Process confirmed alive over SSH — recover from degraded.
            session.status = STATUS_RUNNING
            logger.info(f"[{sid}] Session recovered to running")
