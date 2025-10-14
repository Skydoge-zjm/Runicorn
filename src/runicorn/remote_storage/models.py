"""
Remote Storage Data Models

Defines core data structures for the remote storage system.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class RemoteConnectionStatus(str, Enum):
    """Remote connection status enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SYNCING = "syncing"
    ERROR = "error"


class SyncStatus(str, Enum):
    """Metadata sync status enumeration."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RemoteConfig:
    """
    Remote server connection configuration.
    
    Attributes:
        host: Remote server hostname or IP
        port: SSH port (default: 22)
        username: SSH username
        password: Optional SSH password
        private_key: Optional private key content
        private_key_path: Optional path to private key file
        passphrase: Optional passphrase for private key
        use_agent: Whether to use SSH agent
        remote_root: Remote storage root directory
        timeout: Connection timeout in seconds
    """
    host: str
    port: int = 22
    username: str = ""
    password: Optional[str] = None
    private_key: Optional[str] = None
    private_key_path: Optional[str] = None
    passphrase: Optional[str] = None
    use_agent: bool = True
    remote_root: str = ""
    timeout: float = 15.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RemoteConfig:
        """Create from dictionary."""
        return cls(**data)
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate configuration.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.host or not self.host.strip():
            return False, "Host is required"
        
        if not self.username or not self.username.strip():
            return False, "Username is required"
        
        if self.port < 1 or self.port > 65535:
            return False, f"Invalid port: {self.port}"
        
        if not self.remote_root or not self.remote_root.strip():
            return False, "Remote root directory is required"
        
        # At least one authentication method required
        has_auth = (
            (self.password and self.password.strip()) or
            (self.private_key and self.private_key.strip()) or
            (self.private_key_path and self.private_key_path.strip()) or
            self.use_agent
        )
        
        if not has_auth:
            return False, "At least one authentication method is required"
        
        return True, None


@dataclass
class SyncProgress:
    """
    Metadata synchronization progress tracking.
    
    Attributes:
        status: Current sync status
        started_at: Timestamp when sync started
        completed_at: Timestamp when sync completed
        total_files: Total number of files to sync
        synced_files: Number of files synced so far
        total_bytes: Total bytes to sync
        synced_bytes: Bytes synced so far
        current_file: Currently syncing file path
        errors: List of error messages encountered
    """
    status: SyncStatus = SyncStatus.IDLE
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    total_files: int = 0
    synced_files: int = 0
    total_bytes: int = 0
    synced_bytes: int = 0
    current_file: str = ""
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @property
    def progress_percent(self) -> float:
        """Calculate sync progress percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.synced_files / self.total_files) * 100.0
    
    @property
    def is_running(self) -> bool:
        """Check if sync is currently running."""
        return self.status == SyncStatus.RUNNING
    
    @property
    def is_completed(self) -> bool:
        """Check if sync is completed."""
        return self.status == SyncStatus.COMPLETED
    
    @property
    def has_errors(self) -> bool:
        """Check if sync has errors."""
        return len(self.errors) > 0 or self.status == SyncStatus.FAILED
    
    def start(self) -> None:
        """Mark sync as started."""
        self.status = SyncStatus.RUNNING
        self.started_at = time.time()
        self.errors.clear()
    
    def complete(self) -> None:
        """Mark sync as completed."""
        self.status = SyncStatus.COMPLETED
        self.completed_at = time.time()
    
    def fail(self, error: str) -> None:
        """Mark sync as failed with error message."""
        self.status = SyncStatus.FAILED
        self.completed_at = time.time()
        self.errors.append(error)
    
    def update_progress(self, synced_files: int, synced_bytes: int, current_file: str = "") -> None:
        """Update sync progress."""
        self.synced_files = synced_files
        self.synced_bytes = synced_bytes
        self.current_file = current_file


@dataclass
class CachedFile:
    """
    Cached file metadata.
    
    Attributes:
        remote_path: Remote file path (relative to remote_root)
        local_path: Local cache file path
        size_bytes: File size in bytes
        remote_mtime: Remote file modification time
        cached_at: Timestamp when file was cached
        last_accessed: Timestamp when file was last accessed
        checksum: Optional file checksum (for verification)
    """
    remote_path: str
    local_path: str
    size_bytes: int
    remote_mtime: float
    cached_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    checksum: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CachedFile:
        """Create from dictionary."""
        return cls(**data)
    
    def is_stale(self, max_age_seconds: float = 3600) -> bool:
        """
        Check if cached file is stale.
        
        Args:
            max_age_seconds: Maximum age in seconds before considered stale
            
        Returns:
            True if file is stale
        """
        age = time.time() - self.cached_at
        return age > max_age_seconds


@dataclass
class DownloadTask:
    """
    File download task tracking.
    
    Attributes:
        task_id: Unique task identifier
        artifact_name: Artifact name
        artifact_type: Artifact type
        artifact_version: Artifact version
        target_dir: Local target directory
        total_files: Total number of files to download
        downloaded_files: Number of files downloaded
        total_bytes: Total bytes to download
        downloaded_bytes: Bytes downloaded so far
        started_at: Timestamp when download started
        completed_at: Timestamp when download completed
        status: Download status
        error: Error message if failed
    """
    task_id: str
    artifact_name: str
    artifact_type: str
    artifact_version: int
    target_dir: str
    total_files: int = 0
    downloaded_files: int = 0
    total_bytes: int = 0
    downloaded_bytes: int = 0
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    status: str = "running"
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @property
    def progress_percent(self) -> float:
        """Calculate download progress percentage."""
        if self.total_bytes == 0:
            return 0.0
        return (self.downloaded_bytes / self.total_bytes) * 100.0
    
    @property
    def is_running(self) -> bool:
        """Check if download is running."""
        return self.status == "running"
    
    @property
    def is_completed(self) -> bool:
        """Check if download is completed."""
        return self.status == "completed"
    
    @property
    def is_failed(self) -> bool:
        """Check if download failed."""
        return self.status == "failed"
    
    def complete(self) -> None:
        """Mark download as completed."""
        self.status = "completed"
        self.completed_at = time.time()
    
    def fail(self, error: str) -> None:
        """Mark download as failed."""
        self.status = "failed"
        self.error = error
        self.completed_at = time.time()
    
    def update_progress(self, downloaded_files: int, downloaded_bytes: int) -> None:
        """Update download progress."""
        self.downloaded_files = downloaded_files
        self.downloaded_bytes = downloaded_bytes


@dataclass
class RemoteStorageStats:
    """
    Remote storage statistics.
    
    Attributes:
        connected: Whether connected to remote server
        last_sync: Timestamp of last successful sync
        total_artifacts: Total number of artifacts on remote
        cached_artifacts: Number of artifacts with cached metadata
        cache_size_bytes: Total size of local cache in bytes
        remote_size_bytes: Total size on remote server in bytes
        sync_count: Number of successful syncs
        error_count: Number of sync errors
    """
    connected: bool = False
    last_sync: Optional[float] = None
    total_artifacts: int = 0
    cached_artifacts: int = 0
    cache_size_bytes: int = 0
    remote_size_bytes: int = 0
    sync_count: int = 0
    error_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RemoteStorageStats:
        """Create from dictionary."""
        return cls(**data)


@dataclass
class RemoteOperation:
    """
    Remote operation tracking.
    
    Attributes:
        operation_id: Unique operation identifier
        operation_type: Type of operation (delete, set_alias, etc.)
        artifact_name: Target artifact name
        artifact_type: Target artifact type
        artifact_version: Target artifact version
        parameters: Operation-specific parameters
        started_at: Timestamp when operation started
        completed_at: Timestamp when operation completed
        status: Operation status
        result: Operation result data
        error: Error message if failed
    """
    operation_id: str
    operation_type: str
    artifact_name: str
    artifact_type: str
    artifact_version: int
    parameters: Dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    status: str = "running"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return asdict(self)
    
    def complete(self, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark operation as completed."""
        self.status = "completed"
        self.completed_at = time.time()
        self.result = result
    
    def fail(self, error: str) -> None:
        """Mark operation as failed."""
        self.status = "failed"
        self.error = error
        self.completed_at = time.time()


