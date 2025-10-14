"""
Remote Storage Adapter

Provides transparent access to remote artifacts storage via SSH.
"""
from __future__ import annotations

import logging
import threading
import time
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable

import paramiko

from .models import (
    RemoteConfig,
    RemoteConnectionStatus,
    SyncProgress,
    DownloadTask,
    RemoteStorageStats
)
from .cache_manager import LocalCacheManager
from .metadata_sync import MetadataSyncService
from .file_fetcher import OnDemandFileFetcher
from .remote_executor import RemoteCommandExecutor

logger = logging.getLogger(__name__)


class RemoteStorageAdapter:
    """
    Remote storage adapter providing transparent access to remote artifacts.
    
    This adapter implements the same interface as ArtifactStorage but operates
    on remote data via SSH, with intelligent local caching.
    
    Key features:
    1. Metadata-only sync: Only sync small metadata files, not large model files
    2. On-demand downloads: Download files only when explicitly requested
    3. Remote operations: Execute management operations on remote server
    4. Transparent interface: UI layer doesn't need to know it's remote
    
    Usage:
        # Initialize
        config = RemoteConfig(host="server.edu", username="user", ...)
        adapter = RemoteStorageAdapter(config, cache_dir)
        
        # Connect and sync metadata
        adapter.connect()
        adapter.sync_metadata()
        
        # Use like local storage
        artifacts = adapter.list_artifacts()  # Fast, from cache
        metadata = adapter.load_artifact("model", "resnet50", 3)  # Fast, from cache
        
        # Download when needed
        files = adapter.download_artifact("model", "resnet50", 3)  # Explicit download
        
        # Manage remotely
        adapter.delete_artifact_version("model", "resnet50", 1)  # Operates on server
    """
    
    def __init__(
        self,
        config: RemoteConfig,
        cache_dir: Path,
        auto_sync: bool = True,
        sync_interval_seconds: int = 600
    ):
        """
        Initialize remote storage adapter.
        
        Args:
            config: Remote connection configuration
            cache_dir: Local cache directory
            auto_sync: Enable automatic background sync (default: True)
            sync_interval_seconds: Auto-sync interval in seconds (default: 10 minutes)
        """
        # Validate configuration
        is_valid, error = config.validate()
        if not is_valid:
            raise ValueError(f"Invalid remote configuration: {error}")
        
        self.config = config
        self.cache_dir = Path(cache_dir)
        self.auto_sync = auto_sync
        self.sync_interval = sync_interval_seconds
        
        # Connection state
        self._status = RemoteConnectionStatus.DISCONNECTED
        self._status_lock = threading.RLock()
        
        # SSH/SFTP clients
        self._ssh_client: Optional[paramiko.SSHClient] = None
        self._sftp_client: Optional[paramiko.SFTPClient] = None
        
        # Services (initialized after connection)
        self.cache: Optional[LocalCacheManager] = None
        self.metadata_sync: Optional[MetadataSyncService] = None
        self.file_fetcher: Optional[OnDemandFileFetcher] = None
        self.remote_executor: Optional[RemoteCommandExecutor] = None
        
        # Initialize cache manager immediately
        self.cache = LocalCacheManager(self.cache_dir)
        
        logger.info(f"Remote storage adapter initialized for {config.host}")
    
    # ==================== Connection Management ====================
    
    def connect(self) -> bool:
        """
        Establish SSH connection to remote server.
        
        Returns:
            True if connection successful
            
        Raises:
            RuntimeError: If connection fails
        """
        with self._status_lock:
            if self._status == RemoteConnectionStatus.CONNECTED:
                logger.warning("Already connected")
                return True
            
            self._status = RemoteConnectionStatus.CONNECTING
        
        try:
            # Create SSH client
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Prepare connection parameters
            connect_kwargs = {
                "hostname": self.config.host,
                "port": self.config.port,
                "username": self.config.username,
                "timeout": self.config.timeout,
                "allow_agent": self.config.use_agent,
                "look_for_keys": self.config.use_agent,
            }
            
            # Handle authentication
            if self.config.password:
                connect_kwargs["password"] = self.config.password
            
            # Handle private key
            pkey = self._load_private_key()
            if pkey:
                connect_kwargs["pkey"] = pkey
            
            # Connect
            client.connect(**connect_kwargs)
            self._ssh_client = client
            self._sftp_client = client.open_sftp()
            
            # Initialize services
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
            
            # Update status
            with self._status_lock:
                self._status = RemoteConnectionStatus.CONNECTED
            
            logger.info(f"Connected to {self.config.username}@{self.config.host}")
            
            # Start auto-sync if enabled
            if self.auto_sync:
                self.metadata_sync.start_background_sync(self.sync_interval)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.config.host}: {e}")
            with self._status_lock:
                self._status = RemoteConnectionStatus.ERROR
            raise RuntimeError(f"Connection failed: {e}") from e
    
    def _load_private_key(self) -> Optional[paramiko.PKey]:
        """
        Load private key from config.
        
        Returns:
            Private key object or None
        """
        if self.config.private_key:
            # Key content provided
            try:
                # Try RSA first
                return paramiko.RSAKey.from_private_key(
                    StringIO(self.config.private_key),
                    password=self.config.passphrase
                )
            except Exception:
                try:
                    # Try Ed25519
                    return paramiko.Ed25519Key.from_private_key(
                        StringIO(self.config.private_key),
                        password=self.config.passphrase
                    )
                except Exception as e:
                    logger.error(f"Failed to parse private key: {e}")
                    return None
        
        elif self.config.private_key_path:
            # Key file path provided
            try:
                key_path = Path(self.config.private_key_path).expanduser()
                
                # Try RSA first
                try:
                    return paramiko.RSAKey.from_private_key_file(
                        str(key_path),
                        password=self.config.passphrase
                    )
                except Exception:
                    # Try Ed25519
                    return paramiko.Ed25519Key.from_private_key_file(
                        str(key_path),
                        password=self.config.passphrase
                    )
            except Exception as e:
                logger.error(f"Failed to load private key from {self.config.private_key_path}: {e}")
                return None
        
        return None
    
    def disconnect(self) -> None:
        """Disconnect from remote server and clean up resources."""
        # Stop background sync
        if self.metadata_sync:
            self.metadata_sync.stop_background_sync()
        
        # Close SFTP
        if self._sftp_client:
            try:
                self._sftp_client.close()
                logger.debug("SFTP client closed")
            except Exception as e:
                logger.warning(f"Error closing SFTP: {e}")
            finally:
                self._sftp_client = None
        
        # Close SSH
        if self._ssh_client:
            try:
                self._ssh_client.close()
                logger.debug("SSH client closed")
            except Exception as e:
                logger.warning(f"Error closing SSH: {e}")
            finally:
                self._ssh_client = None
        
        with self._status_lock:
            self._status = RemoteConnectionStatus.DISCONNECTED
        
        logger.info("Disconnected from remote server")
    
    def is_connected(self) -> bool:
        """
        Check if connected to remote server.
        
        Returns:
            True if connected
        """
        with self._status_lock:
            return self._status == RemoteConnectionStatus.CONNECTED
    
    def get_status(self) -> RemoteConnectionStatus:
        """
        Get current connection status.
        
        Returns:
            Current connection status
        """
        with self._status_lock:
            return self._status
    
    # ==================== Metadata Synchronization ====================
    
    def sync_metadata(
        self,
        on_progress: Optional[Callable[[SyncProgress], None]] = None
    ) -> bool:
        """
        Synchronize metadata from remote server to local cache.
        
        Args:
            on_progress: Optional progress callback
            
        Returns:
            True if sync successful
            
        Raises:
            RuntimeError: If not connected
        """
        if not self.is_connected() or not self.metadata_sync:
            raise RuntimeError("Not connected to remote server")
        
        # Add progress callback
        if on_progress:
            self.metadata_sync.add_progress_callback(on_progress)
        
        # Start sync
        with self._status_lock:
            self._status = RemoteConnectionStatus.SYNCING
        
        try:
            success = self.metadata_sync.sync_all()
            
            with self._status_lock:
                self._status = RemoteConnectionStatus.CONNECTED
            
            return success
            
        except Exception as e:
            logger.error(f"Metadata sync failed: {e}")
            with self._status_lock:
                self._status = RemoteConnectionStatus.ERROR
            raise
    
    def get_sync_progress(self) -> Optional[SyncProgress]:
        """
        Get current metadata sync progress.
        
        Returns:
            SyncProgress object or None if not available
        """
        if not self.metadata_sync:
            return None
        
        return self.metadata_sync.get_progress()
    
    # ==================== Artifact Storage Interface ====================
    # These methods mirror ArtifactStorage interface for transparency
    
    def list_artifacts(self, type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List artifacts from local cache.
        
        Args:
            type: Optional artifact type filter
            
        Returns:
            List of artifact summaries
        """
        if not self.cache:
            return []
        
        return self.cache.list_artifacts(type=type)
    
    def list_versions(
        self,
        name: str,
        type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List versions of an artifact from local cache.
        
        Args:
            name: Artifact name
            type: Optional artifact type
            
        Returns:
            List of version information
        """
        if not self.cache:
            return []
        
        return self.cache.list_artifact_versions(name, type)
    
    def load_artifact(
        self,
        name: str,
        type: str,
        version: int
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Load artifact metadata and manifest from local cache.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Version number
            
        Returns:
            Tuple of (metadata, manifest) or (None, None) if not cached
        """
        if not self.cache:
            return None, None
        
        metadata = self.cache.get_artifact_metadata(name, type, version)
        manifest = self.cache.get_artifact_manifest(name, type, version)
        
        return metadata, manifest
    
    def download_artifact(
        self,
        name: str,
        type: str,
        version: int,
        target_dir: Optional[Path] = None,
        on_progress: Optional[Callable[[DownloadTask], None]] = None
    ) -> str:
        """
        Download artifact files from remote server.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Version number
            target_dir: Optional target directory
            on_progress: Optional progress callback
            
        Returns:
            Task ID for tracking download
            
        Raises:
            RuntimeError: If not connected
        """
        if not self.is_connected() or not self.file_fetcher:
            raise RuntimeError("Not connected to remote server")
        
        return self.file_fetcher.download_artifact(
            name, type, version, target_dir, on_progress
        )
    
    def get_download_status(self, task_id: str) -> Optional[DownloadTask]:
        """
        Get status of a download task.
        
        Args:
            task_id: Download task ID
            
        Returns:
            DownloadTask object or None if not found
        """
        if not self.file_fetcher:
            return None
        
        return self.file_fetcher.get_task_status(task_id)
    
    def cancel_download(self, task_id: str) -> bool:
        """
        Cancel an ongoing download.
        
        Args:
            task_id: Download task ID
            
        Returns:
            True if cancelled
        """
        if not self.file_fetcher:
            return False
        
        return self.file_fetcher.cancel_download(task_id)
    
    def delete_artifact_version(
        self,
        name: str,
        type: str,
        version: int,
        soft_delete: bool = True
    ) -> bool:
        """
        Delete artifact version on remote server.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Version number
            soft_delete: If True, soft delete (default)
            
        Returns:
            True if deletion successful
            
        Raises:
            RuntimeError: If not connected
        """
        if not self.is_connected() or not self.remote_executor:
            raise RuntimeError("Not connected to remote server")
        
        return self.remote_executor.delete_artifact_version(
            name, type, version, soft_delete
        )
    
    def set_artifact_alias(
        self,
        name: str,
        type: str,
        version: int,
        alias: str
    ) -> bool:
        """
        Set alias for artifact version on remote server.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Version number
            alias: Alias name
            
        Returns:
            True if operation successful
            
        Raises:
            RuntimeError: If not connected
        """
        if not self.is_connected() or not self.remote_executor:
            raise RuntimeError("Not connected to remote server")
        
        return self.remote_executor.set_artifact_alias(name, type, version, alias)
    
    def add_artifact_tags(
        self,
        name: str,
        type: str,
        version: int,
        tags: List[str]
    ) -> bool:
        """
        Add tags to artifact version on remote server.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Version number
            tags: List of tags to add
            
        Returns:
            True if operation successful
            
        Raises:
            RuntimeError: If not connected
        """
        if not self.is_connected() or not self.remote_executor:
            raise RuntimeError("Not connected to remote server")
        
        return self.remote_executor.add_artifact_tags(name, type, version, tags)
    
    # ==================== Statistics and Monitoring ====================
    
    def get_stats(self) -> RemoteStorageStats:
        """
        Get storage statistics.
        
        Returns:
            RemoteStorageStats object
        """
        stats = self.cache.get_stats() if self.cache else RemoteStorageStats()
        
        # Update connection status
        stats.connected = self.is_connected()
        
        return stats
    
    def verify_connection(self) -> bool:
        """
        Verify connection is still active.
        
        Returns:
            True if connection is active
        """
        if not self.is_connected() or not self.remote_executor:
            return False
        
        try:
            return self.remote_executor.test_connection()
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            return False
    
    def verify_remote_structure(self) -> Dict[str, bool]:
        """
        Verify remote storage structure.
        
        Returns:
            Dictionary with verification results
        """
        if not self.is_connected() or not self.remote_executor:
            return {"error": "Not connected"}
        
        try:
            return self.remote_executor.verify_remote_structure()
        except Exception as e:
            logger.error(f"Structure verification failed: {e}")
            return {"error": str(e)}
    
    # ==================== Cache Management ====================
    
    def clear_cache(self) -> None:
        """Clear local cache (metadata and downloaded files)."""
        if self.cache:
            self.cache.clear_cache()
            logger.info("Local cache cleared")
    
    def cleanup_cache(self) -> None:
        """Clean up old cached files using LRU strategy."""
        if self.cache:
            cleaned = self.cache.cleanup_old_files()
            logger.info(f"Cache cleanup: removed {cleaned} files")
    
    # ==================== Lifecycle Management ====================
    
    def close(self) -> None:
        """Close connection and clean up resources."""
        logger.info("Closing remote storage adapter...")
        
        # Disconnect from server
        self.disconnect()
        
        # Close cache manager
        if self.cache:
            self.cache.close()
        
        logger.info("Remote storage adapter closed")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __repr__(self) -> str:
        """String representation."""
        status = self._status.value if self._status else "unknown"
        return (
            f"<RemoteStorageAdapter "
            f"host={self.config.host} "
            f"status={status}>"
        )


