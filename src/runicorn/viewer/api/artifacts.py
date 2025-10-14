"""
Artifacts API Routes

Handles artifact version control, listing, and lineage queries.
Supports both local and remote storage modes transparently.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Storage Adapter Helper ====================

def _get_storage_adapter(request: Request) -> Tuple[Any, bool]:
    """
    Get appropriate storage adapter based on current mode.
    
    This function provides transparent access to either local or remote storage,
    allowing all endpoints to work with both modes without code duplication.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Tuple of (storage_adapter, is_remote)
        
    Raises:
        HTTPException: If storage system is not available
    """
    storage_mode = getattr(request.app.state, 'storage_mode', 'local')
    
    if storage_mode == 'remote':
        # Remote mode: use remote adapter
        adapter = getattr(request.app.state, 'remote_adapter', None)
        
        if not adapter:
            raise HTTPException(
                status_code=400,
                detail="Remote mode enabled but not connected. Please connect to remote server first."
            )
        
        if not adapter.is_connected():
            raise HTTPException(
                status_code=400,
                detail="Remote connection is not active. Please reconnect."
            )
        
        return adapter, True
    
    else:
        # Local mode: use local artifact storage
        try:
            from ...artifacts import create_artifact_storage
            
            storage_root = request.app.state.storage_root
            artifact_storage = create_artifact_storage(storage_root)
            
            return artifact_storage, False
            
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="Artifacts system is not available"
            )


def _determine_artifact_type(
    storage_adapter: Any,
    artifact_name: str,
    is_remote: bool
) -> Optional[str]:
    """
    Determine artifact type by searching storage.
    
    Args:
        storage_adapter: Storage adapter (local or remote)
        artifact_name: Artifact name
        is_remote: Whether using remote storage
        
    Returns:
        Artifact type or None if not found
    """
    if is_remote:
        # Remote mode: search cached metadata
        artifacts = storage_adapter.list_artifacts()
        for art in artifacts:
            if art['name'] == artifact_name:
                return art['type']
        return None
    else:
        # Local mode: search file system
        for type_candidate in ["model", "dataset", "config", "code", "custom"]:
            artifact_dir = storage_adapter.artifacts_root / type_candidate / artifact_name
            if artifact_dir.exists():
                return type_candidate
        return None


class ArtifactListItem(BaseModel):
    """Model for artifact list item response."""
    name: str
    type: str
    num_versions: int
    latest_version: int
    size_bytes: int
    created_at: float
    updated_at: float
    aliases: Dict[str, int]


class ArtifactVersionItem(BaseModel):
    """Model for artifact version item response."""
    version: int
    created_at: float
    created_by_run: str
    size_bytes: int
    num_files: int
    status: str
    aliases: List[str]


class ArtifactDetailResponse(BaseModel):
    """Model for detailed artifact information."""
    name: str
    type: str
    version: int
    created_at: float
    updated_at: float
    created_by_run: str
    created_by_user: Optional[str]
    size_bytes: int
    num_files: int
    num_references: int
    status: str
    metadata: Dict[str, Any]
    description: str
    tags: List[str]
    aliases: List[str]
    manifest_digest: Optional[str]


@router.get("/artifacts", response_model=List[ArtifactListItem])
async def list_artifacts(
    request: Request,
    type: Optional[str] = Query(None, description="Filter by artifact type")
) -> List[ArtifactListItem]:
    """
    List all artifacts with optional type filter.
    
    Works transparently with both local and remote storage modes.
    
    Args:
        type: Optional artifact type filter (model, dataset, config, etc.)
        
    Returns:
        List of artifact summaries
    """
    try:
        # Get appropriate storage adapter (local or remote)
        storage_adapter, is_remote = _get_storage_adapter(request)
        
        # List artifacts (same interface for both modes)
        artifacts = storage_adapter.list_artifacts(type=type)
        
        return [ArtifactListItem(**a) for a in artifacts]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list artifacts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifacts/{artifact_name}/versions", response_model=List[ArtifactVersionItem])
async def list_artifact_versions(
    request: Request,
    artifact_name: str,
    type: Optional[str] = Query(None, description="Artifact type hint")
) -> List[ArtifactVersionItem]:
    """
    List all versions of a specific artifact.
    
    Works transparently with both local and remote storage modes.
    
    Args:
        artifact_name: Name of the artifact
        type: Optional artifact type hint
        
    Returns:
        List of version information
    """
    try:
        # Get appropriate storage adapter (local or remote)
        storage_adapter, is_remote = _get_storage_adapter(request)
        
        # List versions (same interface for both modes)
        versions = storage_adapter.list_versions(artifact_name, type)
        
        # Convert to response model
        if is_remote:
            # Remote mode: versions are dicts
            return [ArtifactVersionItem(**v) for v in versions]
        else:
            # Local mode: versions are ArtifactVersionInfo objects
            return [ArtifactVersionItem(**v.to_dict()) for v in versions]
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list versions for {artifact_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifacts/{artifact_name}/v{version}", response_model=ArtifactDetailResponse)
async def get_artifact_detail(
    request: Request,
    artifact_name: str,
    version: int,
    type: Optional[str] = Query(None, description="Artifact type hint")
) -> ArtifactDetailResponse:
    """
    Get detailed information for a specific artifact version.
    
    Works transparently with both local and remote storage modes.
    
    Args:
        artifact_name: Name of the artifact
        version: Version number
        type: Optional artifact type hint
        
    Returns:
        Detailed artifact information
    """
    try:
        # Get appropriate storage adapter (local or remote)
        storage_adapter, is_remote = _get_storage_adapter(request)
        
        # Determine type if not provided
        if not type:
            type = _determine_artifact_type(storage_adapter, artifact_name, is_remote)
        
        if not type:
            raise FileNotFoundError(f"Artifact not found: {artifact_name}")
        
        # Load artifact metadata
        metadata, manifest = storage_adapter.load_artifact(artifact_name, type, version)
        
        # Convert to response model
        if is_remote:
            # Remote mode: metadata is dict
            return ArtifactDetailResponse(**metadata)
        else:
            # Local mode: metadata is ArtifactMetadata object
            return ArtifactDetailResponse(**metadata.to_dict())
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get artifact detail for {artifact_name}:v{version}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifacts/{artifact_name}/v{version}/files")
async def list_artifact_files(
    request: Request,
    artifact_name: str,
    version: int,
    type: Optional[str] = Query(None, description="Artifact type hint")
) -> Dict[str, Any]:
    """
    List all files in a specific artifact version.
    
    Works transparently with both local and remote storage modes.
    
    Args:
        artifact_name: Name of the artifact
        version: Version number
        type: Optional artifact type hint
        
    Returns:
        Dictionary with files and references
    """
    try:
        # Get appropriate storage adapter (local or remote)
        storage_adapter, is_remote = _get_storage_adapter(request)
        
        # Determine type if not provided
        if not type:
            type = _determine_artifact_type(storage_adapter, artifact_name, is_remote)
        
        if not type:
            raise FileNotFoundError(f"Artifact not found: {artifact_name}")
        
        # Load artifact metadata
        metadata, manifest = storage_adapter.load_artifact(artifact_name, type, version)
        
        # Process files based on mode
        files_with_paths = []
        
        if is_remote:
            # Remote mode: metadata and manifest are dicts
            for f in manifest.get("files", []):
                file_dict = dict(f) if isinstance(f, dict) else f
                # Note: absolute_path not available for remote (files not downloaded yet)
                file_dict['absolute_path'] = None
                file_dict['is_remote'] = True
                files_with_paths.append(file_dict)
            
            references = manifest.get("references", [])
            total_size = manifest.get("total_size", 0)
            total_files = manifest.get("total_files", 0)
            total_references = manifest.get("total_references", 0)
        else:
            # Local mode: manifest is ArtifactManifest object
            for f in manifest.files:
                file_dict = f.to_dict()
                # Add absolute storage path
                abs_path = storage_adapter.get_artifact_file_path(artifact_name, type, version, f.path)
                file_dict['absolute_path'] = str(abs_path) if abs_path else None
                file_dict['is_remote'] = False
                files_with_paths.append(file_dict)
            
            references = [r.to_dict() for r in manifest.references]
            total_size = manifest.total_size
            total_files = manifest.total_files
            total_references = manifest.total_references
        
        return {
            "artifact": f"{artifact_name}:v{version}",
            "files": files_with_paths,
            "references": references,
            "total_size": total_size,
            "total_files": total_files,
            "total_references": total_references,
            "is_remote": is_remote
        }
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list files for {artifact_name}:v{version}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifacts/{artifact_name}/v{version}/lineage")
async def get_artifact_lineage(
    request: Request,
    artifact_name: str,
    version: int,
    type: Optional[str] = Query(None, description="Artifact type hint"),
    max_depth: int = Query(3, description="Maximum depth to traverse")
) -> Dict[str, Any]:
    """
    Get lineage graph for an artifact.
    
    Works with both local and remote storage modes.
    For remote mode, lineage is built from cached metadata.
    
    Args:
        artifact_name: Name of the artifact
        version: Version number
        type: Optional artifact type hint
        max_depth: Maximum depth to traverse (default: 3)
        
    Returns:
        Lineage graph with nodes and edges
    """
    try:
        from ...artifacts import LineageTracker
        
        # Get storage mode and determine storage root
        storage_mode = getattr(request.app.state, 'storage_mode', 'local')
        
        if storage_mode == 'remote':
            # Remote mode: use cache metadata directory
            adapter = getattr(request.app.state, 'remote_adapter', None)
            if not adapter or not adapter.cache:
                raise HTTPException(
                    status_code=400,
                    detail="Remote mode but cache not available"
                )
            # Use cache metadata directory as storage root for lineage tracking
            storage_root = adapter.cache.metadata_dir / "experiments"
            # Note: LineageTracker will search in this directory tree
        else:
            # Local mode: use regular storage root
            storage_root = request.app.state.storage_root
        
        # Determine type
        # Get appropriate storage adapter to search for type
        storage_adapter, is_remote = _get_storage_adapter(request)
        
        if not type:
            type = _determine_artifact_type(storage_adapter, artifact_name, is_remote)
        
        if not type:
            raise FileNotFoundError(f"Artifact not found: {artifact_name}")
        
        # Build lineage graph
        tracker = LineageTracker(storage_root.parent if storage_mode == 'remote' else storage_root)
        graph = tracker.build_lineage_graph(artifact_name, type, version, max_depth)
        
        return graph.to_dict()
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Artifacts system is not available"
        )
    except Exception as e:
        logger.error(f"Failed to build lineage for {artifact_name}:v{version}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifacts/stats")
async def get_artifacts_stats(request: Request) -> Dict[str, Any]:
    """
    Get artifact storage statistics.
    
    Works with both local and remote storage modes.
    For remote mode, returns cache statistics and remote storage stats.
    
    Returns:
        Storage statistics including size, deduplication ratio, etc.
    """
    try:
        storage_mode = getattr(request.app.state, 'storage_mode', 'local')
        
        if storage_mode == 'remote':
            # Remote mode: return remote storage stats
            adapter = getattr(request.app.state, 'remote_adapter', None)
            if not adapter:
                raise HTTPException(
                    status_code=400,
                    detail="Remote mode but not connected"
                )
            
            stats = adapter.get_stats()
            return stats.to_dict()
        else:
            # Local mode: return local storage stats
            from ...artifacts import create_artifact_storage
            
            storage_root = request.app.state.storage_root
            artifact_storage = create_artifact_storage(storage_root)
            
            return artifact_storage.get_storage_stats()
        
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Artifacts system is not available"
        )
    except Exception as e:
        logger.error(f"Failed to get artifact stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/artifacts/{artifact_name}/v{version}")
async def delete_artifact_version(
    request: Request,
    artifact_name: str,
    version: int,
    type: Optional[str] = Query(None, description="Artifact type hint"),
    permanent: bool = Query(False, description="Permanent delete (vs soft delete)")
) -> Dict[str, Any]:
    """
    Delete an artifact version.
    
    Works transparently with both local and remote storage modes.
    For remote mode, deletion is performed on the remote server.
    
    Args:
        artifact_name: Name of the artifact
        version: Version number to delete
        type: Optional artifact type hint
        permanent: If True, permanently delete; if False, soft delete
        
    Returns:
        Success message
    """
    try:
        # Get appropriate storage adapter (local or remote)
        storage_adapter, is_remote = _get_storage_adapter(request)
        
        # Determine type if not provided
        if not type:
            type = _determine_artifact_type(storage_adapter, artifact_name, is_remote)
        
        if not type:
            raise FileNotFoundError(f"Artifact not found: {artifact_name}")
        
        # Delete artifact version
        success = storage_adapter.delete_artifact_version(
            artifact_name,
            type,
            version,
            soft_delete=not permanent
        )
        
        if success:
            delete_mode = 'Permanently deleted' if permanent else 'Soft deleted'
            location = 'on remote server' if is_remote else 'locally'
            
            return {
                "success": True,
                "message": f"{delete_mode} {artifact_name}:v{version} {location}"
            }
        else:
            raise HTTPException(status_code=404, detail="Version not found")
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete {artifact_name}:v{version}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

