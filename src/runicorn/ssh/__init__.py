"""
SSH Module for Runicorn

Provides SSH/SFTP connection management, host key verification, and file operations.
"""

from .connection import UnifiedSSHConnection, SSHConnectionPool
from .host_keys import (
    load_host_keys,
    get_host_key_policy,
    add_trusted_host,
    KnownHostsPolicy,
    TrustOnFirstUsePolicy
)
from .session import SSHSession
from .mirror import (
    MirrorTask,
    start_mirror,
    stop_mirror,
    list_mirrors,
    get_mirror
)
from .utils import sftp_listdir_with_attrs, resolve_sftp_home

__all__ = [
    # Connection management
    'UnifiedSSHConnection',
    'SSHConnectionPool',
    'SSHSession',
    
    # Host key management
    'load_host_keys',
    'get_host_key_policy',
    'add_trusted_host',
    'KnownHostsPolicy',
    'TrustOnFirstUsePolicy',
    
    # Mirror and sync
    'MirrorTask',
    'start_mirror',
    'stop_mirror',
    'list_mirrors',
    'get_mirror',
    
    # Utilities
    'sftp_listdir_with_attrs',
    'resolve_sftp_home',
]
