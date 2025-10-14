"""
Runicorn Remote Storage Module

Provides transparent access to remote artifacts storage via SSH with intelligent caching.

Features:
- Metadata-only sync: Fast initial setup (MB instead of GB)
- On-demand downloads: Download files only when needed
- Remote operations: Manage artifacts directly on server
- Transparent interface: Drop-in replacement for local storage

Usage:
    from runicorn.remote_storage import RemoteStorageAdapter, RemoteConfig
    
    # Configure connection
    config = RemoteConfig(
        host="gpu-server.edu",
        username="researcher",
        private_key_path="~/.ssh/id_rsa",
        remote_root="/home/researcher/runicorn_data"
    )
    
    # Create adapter
    adapter = RemoteStorageAdapter(config, cache_dir=Path("~/.runicorn_cache"))
    
    # Connect and sync metadata
    adapter.connect()
    adapter.sync_metadata()
    
    # Use like local storage
    artifacts = adapter.list_artifacts()
    metadata, manifest = adapter.load_artifact("my-model", "model", 3)
    
    # Download when needed
    task_id = adapter.download_artifact("my-model", "model", 3)
    
    # Manage remotely
    adapter.delete_artifact_version("old-model", "model", 1)
    adapter.set_artifact_alias("my-model", "model", 3, "production")
    
    # Clean up
    adapter.close()
"""
from __future__ import annotations

# Core models
from .models import (
    RemoteConfig,
    RemoteConnectionStatus,
    SyncStatus,
    SyncProgress,
    CachedFile,
    DownloadTask,
    RemoteStorageStats,
    RemoteOperation
)

# Cache manager
from .cache_manager import LocalCacheManager

# Services
from .metadata_sync import MetadataSyncService
from .file_fetcher import OnDemandFileFetcher
from .remote_executor import RemoteCommandExecutor

# Main adapter
from .adapter import RemoteStorageAdapter

__all__ = [
    # Models
    "RemoteConfig",
    "RemoteConnectionStatus",
    "SyncStatus",
    "SyncProgress",
    "CachedFile",
    "DownloadTask",
    "RemoteStorageStats",
    "RemoteOperation",
    
    # Services
    "LocalCacheManager",
    "MetadataSyncService",
    "OnDemandFileFetcher",
    "RemoteCommandExecutor",
    
    # Main adapter
    "RemoteStorageAdapter",
]

__version__ = "0.1.0"


