"""
Remote Storage API Routes

Handles remote storage configuration, connection, synchronization, and management.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, Body, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Request/Response Models ====================

class RemoteConnectRequest(BaseModel):
    """Remote connection request model."""
    host: str = Field(..., description="Remote server hostname or IP")
    port: int = Field(22, description="SSH port")
    username: str = Field(..., description="SSH username")
    password: Optional[str] = Field(None, description="SSH password")
    private_key: Optional[str] = Field(None, description="Private key content")
    private_key_path: Optional[str] = Field(None, description="Path to private key file")
    passphrase: Optional[str] = Field(None, description="Passphrase for private key")
    use_agent: bool = Field(True, description="Use SSH agent")
    remote_root: str = Field(..., description="Remote storage root directory")
    auto_sync: bool = Field(True, description="Enable automatic background sync")
    sync_interval_minutes: int = Field(10, description="Auto-sync interval in minutes")


class RemoteStatusResponse(BaseModel):
    """Remote storage status response."""
    mode: str = Field(..., description="Storage mode: local or remote")
    connected: bool = Field(..., description="Whether connected to remote")
    status: str = Field(..., description="Connection status")
    sync_progress: Optional[Dict[str, Any]] = Field(None, description="Current sync progress")
    stats: Optional[Dict[str, Any]] = Field(None, description="Storage statistics")


class DownloadStatusResponse(BaseModel):
    """Download task status response."""
    task_id: str
    artifact_name: str
    artifact_type: str
    artifact_version: int
    target_dir: str
    total_files: int
    downloaded_files: int
    total_bytes: int
    downloaded_bytes: int
    progress_percent: float
    status: str
    error: Optional[str] = None


# ==================== Connection Management ====================

@router.post("/remote/connect")
async def connect_remote(request: Request, payload: RemoteConnectRequest) -> Dict[str, Any]:
    """
    Connect to remote server and initialize adapter.
    
    This endpoint:
    1. Validates remote configuration
    2. Establishes SSH connection
    3. Creates remote storage adapter
    4. Stores adapter in app state
    5. Verifies remote storage structure
    
    Args:
        payload: Remote connection configuration
        
    Returns:
        Connection result with session information
        
    Raises:
        HTTPException: If connection fails or configuration invalid
    """
    try:
        from ...remote_storage import RemoteStorageAdapter, RemoteConfig
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Remote storage module is not available"
        )
    
    try:
        # Create configuration
        config = RemoteConfig(
            host=payload.host.strip(),
            port=payload.port,
            username=payload.username.strip(),
            password=payload.password,
            private_key=payload.private_key,
            private_key_path=payload.private_key_path,
            passphrase=payload.passphrase,
            use_agent=payload.use_agent,
            remote_root=payload.remote_root.strip()
        )
        
        # Validate configuration
        is_valid, error = config.validate()
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid configuration: {error}"
            )
        
        # Create cache directory
        from pathlib import Path
        cache_dir = Path.home() / ".runicorn_remote_cache" / f"{payload.host}_{payload.username}"
        
        # Create adapter
        adapter = RemoteStorageAdapter(
            config,
            cache_dir,
            auto_sync=payload.auto_sync,
            sync_interval_seconds=payload.sync_interval_minutes * 60
        )
        
        # Connect to remote server
        logger.info(f"Connecting to {payload.username}@{payload.host}...")
        adapter.connect()
        
        # Store in app state
        # Close any existing adapter first
        if hasattr(request.app.state, 'remote_adapter') and request.app.state.remote_adapter:
            try:
                request.app.state.remote_adapter.close()
            except Exception as e:
                logger.warning(f"Failed to close previous adapter: {e}")
        
        request.app.state.remote_adapter = adapter
        request.app.state.storage_mode = "remote"
        
        # Verify remote structure
        structure = adapter.verify_remote_structure()
        
        logger.info(f"Successfully connected to {payload.host}")
        
        return {
            "ok": True,
            "status": "connected",
            "host": payload.host,
            "username": payload.username,
            "remote_root": payload.remote_root,
            "cache_dir": str(cache_dir),
            "structure_verified": structure,
            "auto_sync": payload.auto_sync,
            "sync_interval_minutes": payload.sync_interval_minutes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Remote connection failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Connection failed: {str(e)}"
        )


@router.post("/remote/disconnect")
async def disconnect_remote(request: Request) -> Dict[str, Any]:
    """
    Disconnect from remote server.
    
    This endpoint:
    1. Closes remote adapter connection
    2. Cleans up resources
    3. Switches back to local mode
    
    Returns:
        Disconnection result
        
    Raises:
        HTTPException: If not connected
    """
    adapter = getattr(request.app.state, 'remote_adapter', None)
    
    if not adapter:
        raise HTTPException(
            status_code=400,
            detail="Not connected to remote server"
        )
    
    try:
        # Close adapter
        adapter.close()
        
        # Clear app state
        request.app.state.remote_adapter = None
        request.app.state.storage_mode = "local"
        
        logger.info("Disconnected from remote server")
        
        return {
            "ok": True,
            "status": "disconnected",
            "message": "Disconnected from remote server"
        }
        
    except Exception as e:
        logger.error(f"Disconnect failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/remote/status", response_model=RemoteStatusResponse)
async def get_remote_status(request: Request) -> RemoteStatusResponse:
    """
    Get remote connection and sync status.
    
    Returns current state including:
    - Connection status
    - Sync progress
    - Storage statistics
    - Cache information
    
    Returns:
        Current remote storage status
    """
    adapter = getattr(request.app.state, 'remote_adapter', None)
    storage_mode = getattr(request.app.state, 'storage_mode', 'local')
    
    if not adapter:
        return RemoteStatusResponse(
            mode=storage_mode,
            connected=False,
            status="disconnected"
        )
    
    try:
        is_connected = adapter.is_connected()
        connection_status = adapter.get_status()
        sync_progress = adapter.get_sync_progress()
        stats = adapter.get_stats()
        
        return RemoteStatusResponse(
            mode=storage_mode,
            connected=is_connected,
            status=connection_status.value,
            sync_progress=sync_progress.to_dict() if sync_progress else None,
            stats=stats.to_dict()
        )
        
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        return RemoteStatusResponse(
            mode=storage_mode,
            connected=False,
            status="error"
        )


# ==================== Metadata Synchronization ====================

@router.post("/remote/sync")
async def sync_remote_metadata(request: Request) -> Dict[str, Any]:
    """
    Trigger manual metadata synchronization.
    
    This endpoint:
    1. Starts metadata sync from remote to local cache
    2. Returns immediately with sync task info
    3. Client can poll /remote/status for progress
    
    Returns:
        Sync initiation result
        
    Raises:
        HTTPException: If not connected or sync fails
    """
    adapter = getattr(request.app.state, 'remote_adapter', None)
    
    if not adapter:
        raise HTTPException(
            status_code=400,
            detail="Not connected to remote server"
        )
    
    if not adapter.is_connected():
        raise HTTPException(
            status_code=400,
            detail="Remote connection is not active"
        )
    
    try:
        # Start sync (this runs in background)
        import threading
        
        def sync_worker() -> None:
            try:
                adapter.sync_metadata()
                logger.info("Manual metadata sync completed")
            except Exception as e:
                logger.error(f"Manual metadata sync failed: {e}")
        
        thread = threading.Thread(target=sync_worker, daemon=True)
        thread.start()
        
        return {
            "ok": True,
            "message": "Metadata sync started",
            "info": "Poll /api/remote/status to track progress"
        }
        
    except Exception as e:
        logger.error(f"Failed to start sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== File Downloads ====================

@router.post("/remote/download/{artifact_name}/v{version}")
async def download_artifact_files(
    request: Request,
    artifact_name: str,
    version: int,
    type: Optional[str] = Query(None, description="Artifact type hint"),
    payload: Optional[Dict[str, Any]] = Body(None)
) -> Dict[str, Any]:
    """
    Download artifact files from remote server.
    
    This endpoint:
    1. Validates artifact exists in cache
    2. Starts background download task
    3. Returns task ID for progress tracking
    
    Args:
        artifact_name: Name of the artifact
        version: Version number
        type: Optional artifact type hint
        target_dir: Optional custom target directory
        
    Returns:
        Download task information including task_id
        
    Raises:
        HTTPException: If not connected or artifact not found
    """
    adapter = getattr(request.app.state, 'remote_adapter', None)
    
    if not adapter:
        raise HTTPException(
            status_code=400,
            detail="Not connected to remote server"
        )
    
    if not adapter.is_connected():
        raise HTTPException(
            status_code=400,
            detail="Remote connection is not active"
        )
    
    try:
        # Determine artifact type if not provided
        if not type:
            # Try to find artifact in cache
            from pathlib import Path
            artifacts_root = adapter.cache.metadata_dir / "artifacts"
            
            for type_candidate in ["model", "dataset", "config", "code", "custom"]:
                artifact_dir = artifacts_root / type_candidate / artifact_name
                if artifact_dir.exists():
                    type = type_candidate
                    break
            
            if not type:
                raise HTTPException(
                    status_code=404,
                    detail=f"Artifact not found in cache: {artifact_name}. Please sync metadata first."
                )
        
        # Parse and validate target directory from payload
        from ...security.path_validation import validate_path
        from pathlib import Path
        
        target_dir = payload.get("target_dir") if payload else None
        
        # If target directory is specified, validate it
        if target_dir:
            # Get the storage root as base directory
            storage_root = request.app.state.storage_root
            
            # Validate the path is safe
            is_valid, safe_path, error = validate_path(
                target_dir,
                storage_root,
                allow_symlinks=False
            )
            
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid target directory: {error}"
                )
            
            target_path = safe_path
        else:
            target_path = None
        
        # Start download
        task_id = adapter.download_artifact(
            artifact_name,
            type,
            version,
            target_dir=target_path
        )
        
        logger.info(f"Started download task {task_id} for {artifact_name}:v{version}")
        
        return {
            "ok": True,
            "task_id": task_id,
            "artifact": f"{artifact_name}:v{version}",
            "message": "Download started. Use /api/remote/download/{task_id}/status to track progress."
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        # User error - invalid input
        logger.warning(f"Invalid download request: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        # Permission issues
        logger.error(f"Permission denied during download: {e}")
        raise HTTPException(status_code=403, detail="Permission denied")
    except IOError as e:
        # I/O errors (disk full, network issues, etc.)
        logger.error(f"I/O error during download: {e}")
        raise HTTPException(status_code=503, detail="Storage or network error")
    except Exception as e:
        # Unexpected errors - log full details but return generic message
        logger.error(f"Unexpected error during download: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/remote/download/{task_id}/status", response_model=DownloadStatusResponse)
async def get_download_status(
    request: Request,
    task_id: str
) -> DownloadStatusResponse:
    """
    Get download task status and progress.
    
    Args:
        task_id: Download task ID
        
    Returns:
        Download task status with progress information
        
    Raises:
        HTTPException: If task not found
    """
    adapter = getattr(request.app.state, 'remote_adapter', None)
    
    if not adapter:
        raise HTTPException(
            status_code=400,
            detail="Not connected to remote server"
        )
    
    task = adapter.get_download_status(task_id)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Download task not found: {task_id}"
        )
    
    return DownloadStatusResponse(
        task_id=task.task_id,
        artifact_name=task.artifact_name,
        artifact_type=task.artifact_type,
        artifact_version=task.artifact_version,
        target_dir=task.target_dir,
        total_files=task.total_files,
        downloaded_files=task.downloaded_files,
        total_bytes=task.total_bytes,
        downloaded_bytes=task.downloaded_bytes,
        progress_percent=task.progress_percent,
        status=task.status,
        error=task.error
    )


@router.delete("/remote/download/{task_id}")
async def cancel_download(request: Request, task_id: str) -> Dict[str, Any]:
    """
    Cancel an ongoing download task.
    
    Args:
        task_id: Download task ID to cancel
        
    Returns:
        Cancellation result
        
    Raises:
        HTTPException: If task not found or already completed
    """
    adapter = getattr(request.app.state, 'remote_adapter', None)
    
    if not adapter:
        raise HTTPException(
            status_code=400,
            detail="Not connected to remote server"
        )
    
    success = adapter.cancel_download(task_id)
    
    if success:
        return {
            "ok": True,
            "message": f"Download task {task_id} cancelled"
        }
    else:
        raise HTTPException(
            status_code=404,
            detail="Task not found or already completed"
        )


@router.get("/remote/downloads")
async def list_downloads(request: Request) -> Dict[str, Any]:
    """
    List all download tasks (active and completed).
    
    Returns:
        List of download tasks
    """
    adapter = getattr(request.app.state, 'remote_adapter', None)
    
    if not adapter:
        return {"downloads": []}
    
    if not adapter.file_fetcher:
        return {"downloads": []}
    
    all_downloads = adapter.file_fetcher.list_all_downloads()
    active_downloads = adapter.file_fetcher.list_active_downloads()
    
    return {
        "downloads": [task.to_dict() for task in all_downloads],
        "active_count": len(active_downloads),
        "total_count": len(all_downloads)
    }


# ==================== Cache Management ====================

@router.post("/remote/cache/clear")
async def clear_cache(request: Request) -> Dict[str, Any]:
    """
    Clear local cache (metadata and downloaded files).
    
    Returns:
        Cache clear result
        
    Raises:
        HTTPException: If operation fails
    """
    adapter = getattr(request.app.state, 'remote_adapter', None)
    
    if not adapter:
        raise HTTPException(
            status_code=400,
            detail="Not connected to remote server"
        )
    
    try:
        adapter.clear_cache()
        
        return {
            "ok": True,
            "message": "Cache cleared successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/remote/cache/cleanup")
async def cleanup_cache(request: Request) -> Dict[str, Any]:
    """
    Clean up old cached files using LRU strategy.
    
    Returns:
        Cleanup result with number of files removed
    """
    adapter = getattr(request.app.state, 'remote_adapter', None)
    
    if not adapter:
        raise HTTPException(
            status_code=400,
            detail="Not connected to remote server"
        )
    
    try:
        # Run cleanup
        if adapter.cache:
            cleaned = adapter.cache.cleanup_old_files()
            
            return {
                "ok": True,
                "files_removed": cleaned,
                "message": f"Cleaned up {cleaned} old files"
            }
        else:
            return {
                "ok": True,
                "files_removed": 0,
                "message": "No cache manager available"
            }
        
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Storage Mode Management ====================

@router.post("/remote/mode/switch")
async def switch_storage_mode(
    request: Request,
    mode: str = Body(..., embed=True, description="Storage mode: local or remote")
) -> Dict[str, Any]:
    """
    Switch between local and remote storage mode.
    
    Args:
        mode: Target storage mode ("local" or "remote")
        
    Returns:
        Mode switch result
        
    Raises:
        HTTPException: If invalid mode or not connected when switching to remote
    """
    if mode not in ["local", "remote"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: {mode}. Must be 'local' or 'remote'"
        )
    
    if mode == "remote":
        # Check if remote adapter is available
        adapter = getattr(request.app.state, 'remote_adapter', None)
        if not adapter or not adapter.is_connected():
            raise HTTPException(
                status_code=400,
                detail="Cannot switch to remote mode: not connected. Please connect first."
            )
    
    # Switch mode
    request.app.state.storage_mode = mode
    
    return {
        "ok": True,
        "mode": mode,
        "message": f"Switched to {mode} storage mode"
    }


@router.get("/remote/mode")
async def get_storage_mode(request: Request) -> Dict[str, Any]:
    """
    Get current storage mode.
    
    Returns:
        Current storage mode information
    """
    storage_mode = getattr(request.app.state, 'storage_mode', 'local')
    adapter = getattr(request.app.state, 'remote_adapter', None)
    
    return {
        "mode": storage_mode,
        "remote_available": adapter is not None,
        "remote_connected": adapter.is_connected() if adapter else False
    }


# ==================== Remote Operations ====================

@router.post("/remote/artifacts/{artifact_name}/v{version}/alias")
async def set_remote_alias(
    request: Request,
    artifact_name: str,
    version: int,
    alias: str = Body(..., embed=True),
    type: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Set alias for artifact version on remote server.
    
    Args:
        artifact_name: Artifact name
        version: Version number
        alias: Alias name (e.g., "production", "stable")
        type: Optional artifact type hint
        
    Returns:
        Operation result
        
    Raises:
        HTTPException: If not connected or operation fails
    """
    adapter = getattr(request.app.state, 'remote_adapter', None)
    
    if not adapter or not adapter.is_connected():
        raise HTTPException(
            status_code=400,
            detail="Not connected to remote server"
        )
    
    try:
        # Determine type if not provided
        if not type:
            artifacts = adapter.list_artifacts()
            for art in artifacts:
                if art['name'] == artifact_name:
                    type = art['type']
                    break
            
            if not type:
                raise ValueError(f"Artifact type not found for: {artifact_name}")
        
        # Set alias on remote
        success = adapter.set_artifact_alias(artifact_name, type, version, alias)
        
        if success:
            return {
                "ok": True,
                "message": f"Set alias '{alias}' → {artifact_name}:v{version}"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to set alias on remote server"
            )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to set alias: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/remote/artifacts/{artifact_name}/v{version}/tags")
async def add_remote_tags(
    request: Request,
    artifact_name: str,
    version: int,
    tags: List[str] = Body(..., embed=True),
    type: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Add tags to artifact version on remote server.
    
    Args:
        artifact_name: Artifact name
        version: Version number
        tags: List of tags to add
        type: Optional artifact type hint
        
    Returns:
        Operation result
        
    Raises:
        HTTPException: If not connected or operation fails
    """
    adapter = getattr(request.app.state, 'remote_adapter', None)
    
    if not adapter or not adapter.is_connected():
        raise HTTPException(
            status_code=400,
            detail="Not connected to remote server"
        )
    
    try:
        # Determine type if not provided
        if not type:
            artifacts = adapter.list_artifacts()
            for art in artifacts:
                if art['name'] == artifact_name:
                    type = art['type']
                    break
            
            if not type:
                raise ValueError(f"Artifact type not found for: {artifact_name}")
        
        # Add tags on remote
        success = adapter.add_artifact_tags(artifact_name, type, version, tags)
        
        if success:
            return {
                "ok": True,
                "message": f"Added tags {tags} to {artifact_name}:v{version}"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to add tags on remote server"
            )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Diagnostics ====================

@router.get("/remote/verify")
async def verify_remote_connection(request: Request) -> Dict[str, Any]:
    """
    Verify remote connection and storage structure.
    
    Returns:
        Verification results including structure checks
    """
    adapter = getattr(request.app.state, 'remote_adapter', None)
    
    if not adapter:
        return {
            "connected": False,
            "error": "Not connected to remote server"
        }
    
    try:
        # Test connection
        connection_ok = adapter.verify_connection()
        
        # Verify structure
        structure = adapter.verify_remote_structure()
        
        return {
            "connected": connection_ok,
            "structure": structure,
            "adapter_status": adapter.get_status().value
        }
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return {
            "connected": False,
            "error": str(e)
        }

