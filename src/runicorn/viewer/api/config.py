"""
Configuration Management API Routes

Handles user configuration settings and storage directory management.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, Body
from ...config import (
    get_user_root_dir, 
    set_user_root_dir,
    get_ssh_connections,
    add_ssh_connection,
    remove_ssh_connection
)
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


@router.get("/config/ssh_connections")
async def get_saved_ssh_connections() -> Dict[str, Any]:
    """
    Get saved SSH connection configurations.
    
    Returns:
        List of saved SSH connections with sensitive data masked
    """
    connections = get_ssh_connections()
    
    # Mask sensitive data
    masked_connections = []
    for conn in connections:
        masked = conn.copy()
        # Never return passwords or private keys
        masked.pop('password', None)
        masked.pop('private_key', None)
        masked.pop('passphrase', None)
        # Only indicate if password/key was saved
        masked['has_password'] = bool(conn.get('password'))
        masked['has_private_key'] = bool(conn.get('private_key'))
        masked_connections.append(masked)
    
    return {"connections": masked_connections}


@router.post("/config/ssh_connections")
async def save_ssh_connection(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Save an SSH connection configuration.
    
    Args:
        payload: SSH connection details including host, port, username, etc.
        
    Returns:
        Success response
    """
    try:
        connection = {
            'host': payload.get('host'),
            'port': payload.get('port', 22),
            'username': payload.get('username'),
            'name': payload.get('name', ''),  # Optional friendly name
            'remember_password': payload.get('remember_password', False),
            'auth_method': payload.get('auth_method', 'password'),
        }
        
        # Only save password/keys if explicitly requested
        if connection['remember_password']:
            if payload.get('password'):
                connection['password'] = payload['password']
            if payload.get('private_key'):
                connection['private_key'] = payload['private_key']
            if payload.get('private_key_path'):
                connection['private_key_path'] = payload['private_key_path']
            if payload.get('passphrase'):
                connection['passphrase'] = payload['passphrase']
        else:
            # Save paths but not actual credentials
            if payload.get('private_key_path'):
                connection['private_key_path'] = payload['private_key_path']
        
        add_ssh_connection(connection)
        
        return {"ok": True, "message": "SSH connection saved"}
        
    except Exception as e:
        logger.error(f"Failed to save SSH connection: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to save connection: {e}"
        )


@router.get("/config/ssh_connections/{key}/details")
async def get_ssh_connection_details(key: str) -> Dict[str, Any]:
    """
    Get full details of a saved SSH connection (including credentials).
    This is used for one-click connection.
    
    Args:
        key: Connection key (host:port@username)
        
    Returns:
        Full connection details including credentials
    """
    try:
        connections = get_ssh_connections()
        
        # Find the connection by key
        for conn in connections:
            if conn.get('key') == key:
                # Return full details including password/key for one-click connect
                return {"ok": True, "connection": conn}
        
        raise HTTPException(
            status_code=404,
            detail=f"Connection not found: {key}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get SSH connection details: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get connection details: {e}"
        )


@router.delete("/config/ssh_connections/{key}")
async def delete_ssh_connection(key: str) -> Dict[str, Any]:
    """
    Delete a saved SSH connection.
    
    Args:
        key: Connection key (host:port@username)
        
    Returns:
        Success response
    """
    try:
        remove_ssh_connection(key)
        return {"ok": True, "message": "SSH connection removed"}
        
    except Exception as e:
        logger.error(f"Failed to remove SSH connection: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to remove connection: {e}"
        )
