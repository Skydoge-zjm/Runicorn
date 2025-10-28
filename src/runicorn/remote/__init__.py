"""
Remote Access Module

Provides unified remote access capabilities:
- SSH connection management with connection pool
- Remote Viewer mode (VSCode-like remote access)
"""
from __future__ import annotations

from .connection import SSHConnection, SSHConnectionPool, SSHConfig

__all__ = [
    "SSHConnection",
    "SSHConnectionPool", 
    "SSHConfig",
]
