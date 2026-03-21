"""
Configuration Management API Routes

Handles user configuration settings and storage directory management.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, Body
from ...config import (
    get_user_root_dir, 
    set_user_root_dir,
    get_ssh_connections,
    add_ssh_connection,
    remove_ssh_connection,
    get_config_file_path,
    load_user_config
)
from ...storage.file_utils import get_storage_root

logger = logging.getLogger(__name__)
router = APIRouter()


def _storage_backend_payload(request: Request) -> Dict[str, Any]:
    backend = getattr(request.app.state, "storage_backend", None)
    using_sqlite = backend is not None
    return {
        "mode": "sqlite" if using_sqlite else "file",
        "label": "SQLite-backed" if using_sqlite else "File-based fallback",
        "available": using_sqlite,
        "backend_class": backend.__class__.__name__ if backend is not None else None,
    }


def _detect_local_storage_candidates(*, scan_root: str | None, max_depth: int) -> Dict[str, Any]:
    common_names = {".runicorn", "runicorn_data"}
    prune = {
        ".cache", ".cargo", ".conda", ".git", ".hg", ".idea", ".local", ".npm",
        ".rustup", ".ssh", ".venv", ".vscode", "__pycache__", "anaconda", "anaconda3",
        "env", "miniconda", "miniconda3", "node_modules", "venv",
    }
    max_run_depth = 4
    max_candidates = 12
    max_run_scan = 64

    root = Path(scan_root).expanduser().resolve() if scan_root else Path.home().resolve()
    if not root.exists():
        raise HTTPException(status_code=400, detail="Scan root does not exist")
    if not root.is_dir():
        raise HTTPException(status_code=400, detail="Scan root is not a directory")

    def run_count_for(candidate_root: Path) -> int:
        runs_dir = candidate_root / "runs"
        if not runs_dir.is_dir():
            return 0

        count = 0
        for current, dirs, files in os.walk(runs_dir):
            current_path = Path(current)
            rel_depth = 0 if current_path == runs_dir else len(current_path.relative_to(runs_dir).parts)
            if rel_depth > max_run_depth:
                dirs[:] = []
                continue
            if "meta.json" in files or "status.json" in files:
                count += 1
                dirs[:] = []
                if count >= max_run_scan:
                    break
        return count

    candidates = []
    for current, dirs, _files in os.walk(root):
        current_path = Path(current)
        rel_depth = 0 if current_path == root else len(current_path.relative_to(root).parts)
        if rel_depth > max_depth:
            dirs[:] = []
            continue

        dirs[:] = [
            name for name in dirs
            if name not in prune and (not name.startswith(".") or name in common_names)
        ]

        has_runs = (current_path / "runs").is_dir()
        has_archive = (current_path / "archive").is_dir()
        has_index = (current_path / "index").is_dir()
        common_name = current_path.name in common_names

        if not has_runs and not has_archive and not has_index and not common_name:
            continue

        run_count = run_count_for(current_path) if has_runs else 0
        if not (run_count > 0 or has_archive or has_index or (common_name and has_runs)):
            continue

        score = 0
        if run_count > 0:
            score += 100 + min(run_count, 20)
        if has_archive:
            score += 25
        if has_index:
            score += 15
        if common_name:
            score += 10

        candidates.append({
            "path": str(current_path),
            "run_count": run_count,
            "has_archive": has_archive,
            "has_index": has_index,
            "score": score,
        })

    candidates.sort(key=lambda item: (-item["score"], item["path"]))
    deduped = []
    seen = set()
    for item in candidates:
        path = item["path"]
        if path in seen:
            continue
        seen.add(path)
        deduped.append(item)
        if len(deduped) >= max_candidates:
            break

    return {
        "scan_root": str(root),
        "max_depth": max_depth,
        "candidates": deduped,
    }


@router.get("/config")
async def get_config(request: Request) -> Dict[str, Any]:
    """
    Get current configuration settings.
    
    Returns:
        Current configuration including user root directory, storage path, and config file locations
    """
    storage_root = request.app.state.storage_root
    config_file_path = get_config_file_path()
    
    return {
        "user_root_dir": str(get_user_root_dir() or storage_root),
        "storage": str(storage_root),
        "config_file": str(config_file_path),
        "home_directory": str(Path.home().resolve()),
        "storage_backend": _storage_backend_payload(request),
    }


@router.get("/config/storage-candidates")
async def get_local_storage_candidates(
    scan_root: str | None = None,
    max_depth: int = 3,
) -> Dict[str, Any]:
    effective_depth = max(1, min(int(max_depth), 8))
    return _detect_local_storage_candidates(
        scan_root=scan_root,
        max_depth=effective_depth,
    )


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
        
        # Set the user root directory (persists to config file; raises on save failure)
        resolved_path = set_user_root_dir(in_path)
        
    except PermissionError as e:
        logger.error(f"Failed to set user root directory (permission): {e}")
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: {e}"
        )
    except OSError as e:
        logger.error(f"Failed to set user root directory (filesystem): {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid path or filesystem error: {e}"
        )
    except Exception as e:
        logger.error(f"Failed to set user root directory: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Config saved to memory but failed to persist to disk: {e}"
        )

    try:
        # Recompute storage root and reinitialize backend + background tasks
        new_storage_root = get_storage_root(str(resolved_path))
        from .. import reinitialize_storage
        await reinitialize_storage(request.app, new_storage_root)
    except Exception as e:
        logger.error(f"Failed to reinitialize storage: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reinitialize storage: {e}"
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
