"""
Remote Viewer Session Management
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

from ..connection import SSHConnection

logger = logging.getLogger(__name__)


@dataclass
class RemoteViewerSession:
    """
    Remote Viewer session information.
    
    Represents an active remote viewer instance with SSH tunnel.
    """
    session_id: str
    connection: SSHConnection
    remote_host: str
    remote_port: int
    local_port: int
    remote_root: str
    remote_pid: Optional[int] = None
    started_at: float = 0.0
    tunnel_thread: Optional[threading.Thread] = None
    _stop_event: threading.Event = None
    
    def __post_init__(self):
        if self.started_at == 0.0:
            self.started_at = time.time()
        if self._stop_event is None:
            self._stop_event = threading.Event()
    
    @property
    def is_active(self) -> bool:
        """Check if session is still active."""
        return (
            self.connection.is_connected 
            and self.tunnel_thread is not None
            and self.tunnel_thread.is_alive()
            and not self._stop_event.is_set()
        )
    
    @property
    def uptime_seconds(self) -> float:
        """Get session uptime in seconds."""
        return time.time() - self.started_at
    
    def stop(self) -> None:
        """Signal session to stop."""
        self._stop_event.set()
    
    def to_dict(self) -> dict:
        """Convert session to dict for API response (frontend-compatible format)."""
        # Determine status based on session state
        if not self.is_active:
            status = "stopped"
        elif self.tunnel_thread and self.tunnel_thread.is_alive():
            status = "running"
        else:
            status = "connecting"
        
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
            "status": status,
            "startedAt": int(self.started_at * 1000),  # Convert to milliseconds for JS
            "uptimeSeconds": self.uptime_seconds,
            "isActive": self.is_active,
            "url": f"http://localhost:{self.local_port}",
        }
