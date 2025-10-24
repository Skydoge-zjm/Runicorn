"""
Unified Remote Storage Adapter

Extends RemoteStorageAdapter to use UnifiedSSHConnection for connection sharing.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .adapter import RemoteStorageAdapter
from .models import RemoteConfig, RemoteConnectionStatus
from ..ssh import UnifiedSSHConnection

logger = logging.getLogger(__name__)


class UnifiedRemoteStorageAdapter(RemoteStorageAdapter):
    """
    Remote storage adapter that uses UnifiedSSHConnection.
    
    This allows the adapter to share SSH connections with other components,
    avoiding duplicate connections to the same server.
    """
    
    def __init__(
        self,
        unified_connection: UnifiedSSHConnection,
        remote_root: str,
        cache_dir: Path,
        auto_sync: bool = True,
        sync_interval_seconds: int = 600
    ):
        """
        Initialize unified adapter with existing connection.
        
        Args:
            unified_connection: Pre-established UnifiedSSHConnection
            remote_root: Remote storage root directory
            cache_dir: Local cache directory
            auto_sync: Whether to enable auto-sync
            sync_interval_seconds: Sync interval in seconds
        """
        # Create a config from the unified connection
        config = RemoteConfig(
            host=unified_connection.host,
            port=unified_connection.port,
            username=unified_connection.username,
            password=unified_connection.password,
            private_key=unified_connection.private_key,
            private_key_path=unified_connection.private_key_path,
            passphrase=unified_connection.passphrase,
            use_agent=unified_connection.use_agent,
            remote_root=remote_root
        )
        
        # Initialize parent with config
        super().__init__(config, cache_dir, auto_sync, sync_interval_seconds)
        
        # Store reference to unified connection
        self._unified_connection = unified_connection
        
        # Override the connection state since we're using existing connection
        if unified_connection.is_connected():
            self._ssh_client = unified_connection._ssh_client
            self._sftp_client = unified_connection._sftp_client
            self._status = RemoteConnectionStatus.CONNECTED
            
            # Initialize services with existing connection
            self._initialize_services()
            
            # Acquire reference to prevent disconnection
            unified_connection.acquire()
            
            logger.info(f"Unified adapter initialized with existing connection to {config.host}")
    
    def connect(self) -> bool:
        """
        Connect using the unified connection.
        
        Returns:
            True if connection successful
        """
        with self._status_lock:
            if self._status == RemoteConnectionStatus.CONNECTED:
                logger.warning("Already connected")
                return True
            
            self._status = RemoteConnectionStatus.CONNECTING
        
        try:
            # Check if unified connection is active
            if not self._unified_connection.is_connected():
                # Try to connect
                success, error = self._unified_connection.connect()
                if not success:
                    raise RuntimeError(f"Failed to connect: {error}")
            
            # Use the unified connection's clients
            self._ssh_client = self._unified_connection._ssh_client
            self._sftp_client = self._unified_connection._sftp_client
            
            # Initialize services
            self._initialize_services()
            
            # Update status
            with self._status_lock:
                self._status = RemoteConnectionStatus.CONNECTED
            
            # Acquire reference
            self._unified_connection.acquire()
            
            # Start auto-sync if enabled
            if self.auto_sync and self.metadata_sync:
                self.metadata_sync.start_background_sync(self.sync_interval)
            
            logger.info(f"Connected via unified connection to {self.config.host}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            with self._status_lock:
                self._status = RemoteConnectionStatus.DISCONNECTED
            raise RuntimeError(f"Connection failed: {e}")
    
    def _initialize_services(self):
        """Initialize services with existing SSH/SFTP clients."""
        from .metadata_sync import MetadataSyncService
        from .file_fetcher import OnDemandFileFetcher
        from .remote_executor import RemoteCommandExecutor
        
        self.metadata_sync = MetadataSyncService(
            self._ssh_client,
            self._sftp_client,
            self.config.remote_root,
            self.cache
        )
        
        self.file_fetcher = OnDemandFileFetcher(
            self._sftp_client,
            self.config.remote_root,
            self.cache
        )
        
        self.remote_executor = RemoteCommandExecutor(
            self._ssh_client,
            self.config.remote_root,
            self.metadata_sync
        )
    
    def close(self) -> None:
        """
        Close adapter and release unified connection reference.
        """
        # Stop sync thread first
        if self.metadata_sync:
            self.metadata_sync.stop_background_sync()
        
        # Release reference to unified connection
        if hasattr(self, '_unified_connection'):
            self._unified_connection.release()
        
        # Clear references but don't close the actual clients
        # (they're managed by UnifiedSSHConnection)
        self._ssh_client = None
        self._sftp_client = None
        
        # Update status
        with self._status_lock:
            self._status = RemoteConnectionStatus.DISCONNECTED
        
        logger.info(f"Unified adapter closed for {self.config.host}")
