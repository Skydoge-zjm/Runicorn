"""
Remote Viewer Session Management
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

from ..ssh_backend import SshConnection

logger = logging.getLogger(__name__)


# Explicit session status values.
STATUS_RUNNING = "running"
STATUS_RECONNECTING = "reconnecting"
STATUS_DEGRADED = "degraded"
STATUS_DISCONNECTED = "disconnected"
STATUS_STOPPED = "stopped"


@dataclass
class RemoteViewerSession:
    """
    Remote Viewer session information.
    
    Represents an active remote viewer instance with SSH tunnel.
    """
    session_id: str
    connection: SshConnection
    remote_host: str
    remote_port: int
    local_port: int
    remote_root: str
    remote_pid: Optional[int] = None
    python_cmd: str = "python3"
    started_at: float = 0.0
    tunnel_thread: Optional[threading.Thread] = None
    _stop_event: threading.Event = None

    # Explicit status managed by health monitor / tunnel reconnect logic.
    status: str = STATUS_RUNNING

    # Health monitoring bookkeeping.
    health_check_failed_count: int = 0
    last_health_check: float = 0.0
    _restart_count: int = 0
    
    def __post_init__(self):
        if self.started_at == 0.0:
            self.started_at = time.time()
        if self._stop_event is None:
            self._stop_event = threading.Event()
    
    @property
    def is_active(self) -> bool:
        """Check if session is still active."""
        if self._stop_event.is_set():
            return False
        if self.status in (STATUS_STOPPED, STATUS_DISCONNECTED):
            return False
        # Still "active" during reconnecting / degraded so that cleanup
        # does not remove sessions that may recover.
        if self.status in (STATUS_RECONNECTING, STATUS_DEGRADED):
            return True
        return (
            self.connection.is_connected 
            and self.tunnel_thread is not None
            and self.tunnel_thread.is_alive()
        )
    
    @property
    def uptime_seconds(self) -> float:
        """Get session uptime in seconds."""
        return time.time() - self.started_at
    
    def stop(self) -> None:
        """Signal session to stop."""
        self.status = STATUS_STOPPED
        self._stop_event.set()
    
    def to_dict(self) -> dict:
        """Convert session to dict for API response (frontend-compatible format)."""
        return {
            # Frontend expects camelCase
            "sessionId": self.session_id,
            "host": self.remote_host,
            "sshPort": self.connection.config.port if self.connection else 22,
            "username": self.connection.config.username if self.connection else "unknown",
            "localPort": self.local_port,
            "remotePort": self.remote_port,
            "remoteRoot": self.remote_root,
            "remotePid": self.remote_pid,
            "status": self.status,
            "startedAt": int(self.started_at * 1000),  # Convert to milliseconds for JS
            "uptimeSeconds": self.uptime_seconds,
            "isActive": self.is_active,
            "url": f"http://localhost:{self.local_port}",
        }
