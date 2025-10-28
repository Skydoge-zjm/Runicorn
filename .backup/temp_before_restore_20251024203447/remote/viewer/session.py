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
        """Convert session to dict for API response."""
        return {
            "session_id": self.session_id,
            "remote_host": self.remote_host,
            "remote_port": self.remote_port,
            "local_port": self.local_port,
            "remote_root": self.remote_root,
            "remote_pid": self.remote_pid,
            "started_at": self.started_at,
            "uptime_seconds": self.uptime_seconds,
            "is_active": self.is_active,
            "url": f"http://localhost:{self.local_port}",
        }
