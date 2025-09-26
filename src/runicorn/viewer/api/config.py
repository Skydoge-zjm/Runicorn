"""
Configuration Management API Routes

Handles user configuration settings and storage directory management.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, Body
from ...config import get_user_root_dir, set_user_root_dir
from ..services.storage import get_storage_root

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/config")
async def get_config(request: Request) -> Dict[str, Any]:
    """
    Get current configuration settings.
    
    Returns:
        Current configuration including user root directory and storage path
    """
    storage_root = request.app.state.storage_root
    
    return {
        "user_root_dir": str(get_user_root_dir() or ""),
        "storage": str(storage_root),
    }


@router.post("/config/user_root_dir")
async def set_user_root(request: Request, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Set the user root directory for experiment storage.
    
    Args:
        payload: Dictionary containing the new path
        
    Returns:
        Success message with updated paths
        
    Raises:
        HTTPException: If path is invalid or cannot be set
    """
    try:
        # Extract path from payload
        raw_path = payload.get("path") if isinstance(payload, dict) else None
        in_path = str(raw_path or "")
        
        logger.debug(f"Setting user root directory to: '{in_path}'")
        
        # Expand environment variables on all platforms (Windows: %VAR%, POSIX: $VAR)
        in_path = os.path.expandvars(in_path)
        
        # Set the user root directory
        resolved_path = set_user_root_dir(in_path)
        
    except Exception as e:
        logger.error(f"Failed to set user root directory: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid path or permission error: {e}"
        )

    try:
        # Recompute storage root to apply immediately using the path we just set
        # Passing it explicitly avoids racing on config read and prevents CWD fallback
        new_storage_root = get_storage_root(str(resolved_path))
        
        # Update app state with new storage root
        request.app.state.storage_root = new_storage_root
        
    except Exception as e:
        logger.error(f"Failed to reinitialize storage root: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to reinitialize storage root: {e}"
        )

    return {
        "ok": True,
        "user_root_dir": str(resolved_path),
        "storage": str(new_storage_root),
    }
