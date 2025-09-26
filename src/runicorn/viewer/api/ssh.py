"""
SSH Remote Sync API Routes

Handles SSH connections and remote experiment mirroring.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, Body
from pydantic import BaseModel

from ...ssh_sync import (
    create_session, 
    close_session,
    list_sessions,
    sftp_listdir,
    start_mirror,
    stop_mirror,
    list_mirrors
)

logger = logging.getLogger(__name__)
router = APIRouter()


class SSHConnectBody(BaseModel):
    """SSH connection parameters."""
    host: str
    port: int = 22
    username: str
    password: str = None
    pkey: str = None  # private key content
    pkey_path: str = None
    passphrase: str = None
    use_agent: bool = True


class SSHCloseBody(BaseModel):
    """SSH session close parameters."""
    session_id: str


class SSHMirrorStartBody(BaseModel):
    """SSH mirror start parameters."""
    session_id: str
    remote_root: str
    interval: float = 2.0


class SSHMirrorStopBody(BaseModel):
    """SSH mirror stop parameters."""
    task_id: str


@router.post("/ssh/connect")
async def ssh_connect(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Create SSH connection to remote server.
    
    Args:
        payload: SSH connection parameters
        
    Returns:
        Connection result with session ID
        
    Raises:
        HTTPException: If connection fails
    """
    try:
        host = str(payload.get("host") or "").strip()
        username = str(payload.get("username") or "").strip()
        
        if not host or not username:
            raise HTTPException(status_code=400, detail="host and username are required")
        
        port = int(payload.get("port") or 22)
        session = create_session(
            host=host,
            port=port,
            username=username,
            password=payload.get("password"),
            pkey_str=payload.get("pkey"),
            pkey_path=payload.get("pkey_path"),
            passphrase=payload.get("passphrase"),
            use_agent=bool(payload.get("use_agent", True)),
        )
        
        return {"ok": True, "session_id": session.id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SSH connect failed: {e}")


@router.get("/ssh/sessions")
async def ssh_sessions() -> Dict[str, Any]:
    """
    List active SSH sessions.
    
    Returns:
        List of active SSH sessions
    """
    return {"sessions": list_sessions()}


@router.post("/ssh/close")
async def ssh_close(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Close SSH session.
    
    Args:
        payload: Session close parameters
        
    Returns:
        Close operation result
        
    Raises:
        HTTPException: If session_id is missing
    """
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    ok = close_session(session_id)
    return {"ok": bool(ok)}


@router.get("/ssh/listdir")
async def ssh_listdir(session_id: str, path: str = None) -> Dict[str, Any]:
    """
    List directory contents on remote server.
    
    Args:
        session_id: SSH session ID
        path: Remote directory path (default: home directory)
        
    Returns:
        Directory listing
        
    Raises:
        HTTPException: If operation fails
    """
    try:
        items = sftp_listdir(session_id, path or "~")
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ssh/mirror/start")
async def ssh_mirror_start(request: Request, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Start SSH mirroring task.
    
    Args:
        payload: Mirror start parameters
        
    Returns:
        Mirror task information
        
    Raises:
        HTTPException: If required parameters are missing or operation fails
    """
    try:
        session_id = str(payload.get("session_id") or "").strip()
        remote_root = str(payload.get("remote_root") or "").strip()
        
        if not session_id or not remote_root:
            raise HTTPException(status_code=400, detail="session_id and remote_root are required")
        
        interval = float(payload.get("interval") or 2.0)
        local_root = request.app.state.storage_root
        
        task = start_mirror(
            session_id=session_id, 
            remote_root=remote_root, 
            local_root=local_root, 
            interval=interval
        )
        
        return {
            "ok": True, 
            "task": {
                "id": task.id,
                "session_id": task.session.id,
                "remote_root": task.remote_root,
                "local_root": str(task.local_root),
                "interval": task.interval,
                "stats": dict(task.stats),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Mirror start failed: {e}")


@router.post("/ssh/mirror/stop")
async def ssh_mirror_stop(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Stop SSH mirroring task.
    
    Args:
        payload: Mirror stop parameters
        
    Returns:
        Stop operation result
        
    Raises:
        HTTPException: If task_id is missing
    """
    task_id = str(payload.get("task_id") or "").strip()
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id required")
    
    ok = stop_mirror(task_id)
    return {"ok": bool(ok)}


@router.get("/ssh/mirror/list")
async def ssh_mirror_list(request: Request) -> Dict[str, Any]:
    """
    List active mirror tasks.
    
    Returns:
        List of active mirror tasks with storage information
    """
    storage_root = request.app.state.storage_root
    return {"mirrors": list_mirrors(), "storage": str(storage_root)}
