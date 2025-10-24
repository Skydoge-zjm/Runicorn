"""
Storage Utilities

Helper functions for determining correct storage root path
based on storage mode (local vs remote).
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request


def get_storage_root(request: Request) -> Path:
    """
    Get the appropriate storage root based on storage mode.
    
    For local mode: returns local storage_root
    For remote mode: returns cache experiments directory
    
    The remote cache structure is:
        metadata_dir/experiments/{project}/{name}/runs/{run_id}
    
    But iter_all_runs and other functions expect:
        root/{project}/{name}/runs/{run_id}
    
    So we return metadata_dir/experiments as the root for remote mode.
    
    Args:
        request: FastAPI request object with app state
        
    Returns:
        Path to storage root directory
    """
    storage_mode = getattr(request.app.state, 'storage_mode', 'local')
    
    if storage_mode == "remote" and hasattr(request.app.state, 'remote_adapter'):
        # Remote mode: read from cache experiments directory
        return request.app.state.remote_adapter.cache.metadata_dir / "experiments"
    else:
        # Local mode: read from local storage
        return request.app.state.storage_root
