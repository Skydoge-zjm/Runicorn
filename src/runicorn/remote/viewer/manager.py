"""
Remote Viewer Manager

Manages remote viewer sessions with SSH tunnel.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Optional, Dict

from ..connection import SSHConnection
from ..host_key import HostKeyConfirmationRequiredError
from ..ssh_backend import SshBackend, AutoBackend
from .session import RemoteViewerSession
from .tunnel import find_available_port

logger = logging.getLogger(__name__)


class RemoteViewerManager:
    """
    Manager for Remote Viewer sessions.
    
    Handles:
    - Starting remote viewer process
    - Creating SSH tunnel
    - Session lifecycle management
    """
    
    def __init__(self, backend: Optional[SshBackend] = None):
        self._sessions: Dict[str, RemoteViewerSession] = {}
        self._lock = threading.Lock()
        # Prefer OpenSSH for port forwarding when possible.
        # Fallback logic is handled inside AutoBackend.
        self._backend = backend or AutoBackend()
    
    def start_remote_viewer(
        self,
        connection: SSHConnection,
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
            stdout, stderr, exit_code = connection.exec_command(
                f"{python_cmd} -c 'import runicorn; print(getattr(runicorn, \"__version__\", \"unknown\"))'"
            )
            if exit_code != 0:
                raise RuntimeError(
                    f"runicorn not installed on remote server.\n"
                    f"Please install: {python_cmd} -m pip install runicorn"
                )
            remote_version = stdout.strip()
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
            time.sleep(2)  # Give viewer time to start
            if not self._check_remote_viewer_health(connection, remote_port):
                raise RuntimeError("Remote viewer failed health check")
            logger.info(f"[{session_id}] Remote viewer is healthy")
            
            # Step 6: Find available local port
            if not local_port:
                local_port = find_available_port()
            logger.info(f"[{session_id}] Using local port: {local_port}")
            
            # Step 7: Create SSH tunnel
            logger.info(f"[{session_id}] Creating SSH tunnel...")
            session = RemoteViewerSession(
                session_id=session_id,
                connection=connection,
                remote_host="127.0.0.1",
                remote_port=remote_port,
                local_port=local_port,
                remote_root=remote_root,
                remote_pid=remote_pid,
            )
            
            # Start tunnel in separate thread
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

            def _tunnel_runner() -> None:
                try:
                    tunnel.start()
                except BaseException as e:
                    tunnel_error["error"] = e
                    # Ensure stop signal is set so that the session can be cleaned up.
                    try:
                        session._stop_event.set()
                    except Exception:
                        pass

            tunnel_thread = threading.Thread(
                target=_tunnel_runner,
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
    
    def cleanup_dead_sessions(self) -> int:
        """Remove inactive sessions. Returns count of removed sessions."""
        count = 0
        with self._lock:
            dead_sessions = [
                sid for sid, session in self._sessions.items()
                if not session.is_active
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
    
    def _find_python(self, connection: SSHConnection) -> Optional[str]:
        """Find Python3 executable on remote."""
        for cmd in ["python3", "python"]:
            try:
                stdout, stderr, exit_code = connection.exec_command(
                    f"which {cmd}"
                )
                if exit_code == 0 and stdout.strip():
                    # Verify it's Python 3
                    stdout2, _, exit_code2 = connection.exec_command(
                        f"{cmd} --version"
                    )
                    if exit_code2 == 0 and "Python 3" in stdout2:
                        return cmd
            except Exception:
                continue
        return None
    
    def _find_remote_available_port(
        self, 
        connection: SSHConnection, 
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
            f"python3 -c \"{script}\""
        )
        if exit_code == 0 and stdout.strip().isdigit():
            return int(stdout.strip())
        
        raise RuntimeError(f"No available port found on remote server")
    
    def _start_remote_viewer_process(
        self,
        connection: SSHConnection,
        python_cmd: str,
        remote_root: str,
        remote_port: int,
        session_id: str,
    ) -> int:
        """Start remote viewer process and return PID."""
        # Build command
        cmd = (
            f"nohup {python_cmd} -m runicorn viewer "
            f"--storage '{remote_root}' "
            f"--host 127.0.0.1 "
            f"--port {remote_port} "
            f"--remote-mode "
            f"--log-level INFO "
            f"> /tmp/runicorn_viewer_{session_id}.log 2>&1 & echo $!"
        )
        
        logger.info(f"Starting remote viewer with command: {cmd}")
        stdout, stderr, exit_code = connection.exec_command(cmd, timeout=5)
        
        if exit_code != 0:
            raise RuntimeError(f"Failed to start remote viewer: {stderr}")
        
        pid_str = stdout.strip()
        if not pid_str.isdigit():
            raise RuntimeError(f"Invalid PID returned: {pid_str}")
        
        return int(pid_str)
    
    def _check_remote_viewer_health(
        self,
        connection: SSHConnection,
        remote_port: int,
        timeout: int = 10
    ) -> bool:
        """Check if remote viewer is responding."""
        logger.info(f"Health check: Testing port {remote_port} on remote server")
        
        # Try to connect to the port
        cmd = f"timeout 5 bash -c 'cat < /dev/null > /dev/tcp/127.0.0.1/{remote_port}'"
        
        for attempt in range(timeout):
            try:
                stdout, stderr, exit_code = connection.exec_command(cmd, timeout=6)
                logger.debug(f"Health check attempt {attempt + 1}/{timeout}: exit_code={exit_code}, stderr={stderr[:100]}")
                if exit_code == 0:
                    logger.info(f"Health check passed on attempt {attempt + 1}")
                    return True
            except Exception as e:
                logger.debug(f"Health check attempt {attempt + 1} exception: {e}")
            time.sleep(1)
        
        # If health check failed, try to get viewer process logs
        logger.error(f"Health check failed after {timeout} attempts")
        log_stdout, _, _ = connection.exec_command(
            f"cat /tmp/runicorn_viewer_*.log 2>/dev/null | tail -20"
        )
        if log_stdout.strip():
            logger.error(f"Remote viewer logs:\n{log_stdout}")
        
        return False
    
    def _cleanup_remote_viewer(
        self,
        connection: SSHConnection,
        session_id: str,
        remote_port: Optional[int] = None
    ) -> None:
        """Cleanup remote viewer resources."""
        try:
            # Kill any viewer process listening on the port
            if remote_port:
                cmd = f"lsof -ti:{remote_port} | xargs -r kill"
                connection.exec_command(cmd)
            
            # Remove log file
            connection.exec_command(f"rm -f /tmp/runicorn_viewer_{session_id}.log")
        except Exception as e:
            logger.debug(f"Cleanup warning: {e}")
