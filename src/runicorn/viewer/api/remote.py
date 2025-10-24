"""
Unified Remote API Routes

Provides unified remote access via SSH for Remote Viewer mode.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Body
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Request/Response Models ====================

class SSHConnectRequest(BaseModel):
    """SSH connection request."""
    host: str = Field(..., description="Remote server hostname or IP")
    port: int = Field(22, description="SSH port")
    username: str = Field(..., description="SSH username")
    password: Optional[str] = Field(None, description="SSH password")
    private_key: Optional[str] = Field(None, description="Private key content")
    private_key_path: Optional[str] = Field(None, description="Path to private key file")
    passphrase: Optional[str] = Field(None, description="Passphrase for private key")
    use_agent: bool = Field(True, description="Use SSH agent")


class RemoteViewerStartRequest(BaseModel):
    """Remote Viewer start request."""
    host: str = Field(..., description="Remote server hostname or IP")
    port: int = Field(22, description="SSH port")
    username: str = Field(..., description="SSH username")
    password: Optional[str] = Field(None, description="SSH password")
    private_key: Optional[str] = Field(None, description="Private key content")
    private_key_path: Optional[str] = Field(None, description="Path to private key file")
    passphrase: Optional[str] = Field(None, description="Passphrase for private key")
    use_agent: bool = Field(True, description="Use SSH agent")
    remote_root: str = Field(..., description="Remote storage root directory")
    local_port: Optional[int] = Field(None, description="Local port (auto-detect if None)")
    remote_port: Optional[int] = Field(None, description="Remote port (auto-detect if None)")


# ==================== Connection Management ====================

@router.post("/remote/connect")
async def connect_remote(request: Request, payload: SSHConnectRequest) -> Dict[str, Any]:
    """
    Establish SSH connection and add to connection pool.
    
    Args:
        payload: SSH connection configuration
        
    Returns:
        Connection result with connection_id
        
    Raises:
        HTTPException: If connection fails
    """
    try:
        from ...remote import SSHConfig, SSHConnectionPool
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Remote module not available: {e}"
        )
    
    try:
        # Get connection pool from app state
        if not hasattr(request.app.state, 'connection_pool'):
            # Initialize connection pool
            request.app.state.connection_pool = SSHConnectionPool()
        
        pool: SSHConnectionPool = request.app.state.connection_pool
        
        # Create SSH configuration
        config = SSHConfig(
            host=payload.host,
            port=payload.port,
            username=payload.username,
            password=payload.password,
            private_key=payload.private_key,
            private_key_path=payload.private_key_path,
            passphrase=payload.passphrase,
            use_agent=payload.use_agent,
        )
        
        # Get or create connection
        connection = pool.get_or_create(config)
        
        logger.info(f"SSH connection established: {config.get_key()}")
        
        return {
            "ok": True,
            "connection_id": config.get_key(),
            "host": payload.host,
            "port": payload.port,
            "username": payload.username,
            "connected": connection.is_connected,
        }
        
    except Exception as e:
        logger.error(f"SSH connection failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Connection failed: {str(e)}"
        )


@router.get("/remote/sessions")
async def list_sessions(request: Request) -> Dict[str, Any]:
    """
    List all active SSH connections.
    
    Returns:
        List of active SSH sessions
    """
    if not hasattr(request.app.state, 'connection_pool'):
        return {"sessions": []}
    
    pool: SSHConnectionPool = request.app.state.connection_pool
    connections = pool.list_connections()
    
    return {"sessions": connections}


@router.post("/remote/disconnect")
async def disconnect_remote(
    request: Request,
    host: str = Body(..., embed=True),
    port: int = Body(22, embed=True),
    username: str = Body(..., embed=True)
) -> Dict[str, Any]:
    """
    Disconnect SSH connection.
    
    Args:
        host: Remote host
        port: SSH port
        username: SSH username
        
    Returns:
        Disconnection result
    """
    if not hasattr(request.app.state, 'connection_pool'):
        return {"ok": False, "message": "No connection pool"}
    
    pool: SSHConnectionPool = request.app.state.connection_pool
    removed = pool.remove(host, port, username)
    
    if removed:
        return {"ok": True, "message": "Connection removed"}
    else:
        return {"ok": False, "message": "Connection not found"}


# ==================== Remote Viewer ====================

@router.post("/remote/viewer/start")
async def start_remote_viewer(
    request: Request, 
    payload: RemoteViewerStartRequest
) -> Dict[str, Any]:
    """
    Start Remote Viewer session with SSH tunnel.
    
    This endpoint:
    1. Establishes SSH connection (or reuses existing)
    2. Starts remote viewer process
    3. Creates SSH tunnel (local port -> remote viewer)
    4. Returns local URL for accessing remote viewer
    
    Args:
        payload: Remote Viewer configuration
        
    Returns:
        Remote Viewer session information
        
    Raises:
        HTTPException: If remote viewer cannot be started
    """
    try:
        from ...remote import SSHConfig, SSHConnectionPool
        from ...remote.viewer import RemoteViewerManager
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Remote Viewer module not available: {e}"
        )
    
    try:
        # Initialize connection pool if needed
        if not hasattr(request.app.state, 'connection_pool'):
            request.app.state.connection_pool = SSHConnectionPool()
        
        # Initialize viewer manager if needed
        if not hasattr(request.app.state, 'viewer_manager'):
            request.app.state.viewer_manager = RemoteViewerManager()
        
        pool: SSHConnectionPool = request.app.state.connection_pool
        manager: RemoteViewerManager = request.app.state.viewer_manager
        
        # Get or create SSH connection
        config = SSHConfig(
            host=payload.host,
            port=payload.port,
            username=payload.username,
            password=payload.password,
            private_key=payload.private_key,
            private_key_path=payload.private_key_path,
            passphrase=payload.passphrase,
            use_agent=payload.use_agent,
        )
        
        connection = pool.get_or_create(config)
        logger.info(f"Using SSH connection: {config.get_key()}")
        
        # Start remote viewer session
        session = manager.start_remote_viewer(
            connection=connection,
            remote_root=payload.remote_root,
            local_port=payload.local_port,
            remote_port=payload.remote_port,
        )
        
        logger.info(f"Remote Viewer started: {session.session_id}")
        
        return {
            "ok": True,
            "session": session.to_dict(),
            "message": f"Remote Viewer ready at http://localhost:{session.local_port}",
        }
        
    except Exception as e:
        logger.error(f"Failed to start Remote Viewer: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start Remote Viewer: {str(e)}"
        )


@router.post("/remote/viewer/stop")
async def stop_remote_viewer(
    request: Request,
    session_id: str = Body(..., embed=True)
) -> Dict[str, Any]:
    """
    Stop Remote Viewer session.
    
    Args:
        session_id: Session ID to stop
        
    Returns:
        Stop operation result
    """
    if not hasattr(request.app.state, 'viewer_manager'):
        raise HTTPException(
            status_code=400,
            detail="Remote Viewer manager not initialized"
        )
    
    manager: RemoteViewerManager = request.app.state.viewer_manager
    success = manager.stop_remote_viewer(session_id)
    
    if success:
        return {"ok": True, "message": f"Session {session_id} stopped"}
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )


@router.get("/remote/viewer/sessions")
async def list_remote_viewer_sessions(request: Request) -> Dict[str, Any]:
    """
    List all active Remote Viewer sessions.
    
    Returns:
        List of active Remote Viewer sessions
    """
    if not hasattr(request.app.state, 'viewer_manager'):
        return {"sessions": []}
    
    manager: RemoteViewerManager = request.app.state.viewer_manager
    
    # Cleanup dead sessions
    manager.cleanup_dead_sessions()
    
    sessions = manager.list_sessions()
    
    return {
        "sessions": [session.to_dict() for session in sessions]
    }


# ==================== Remote File System ====================

@router.get("/remote/fs/list")
async def list_remote_directory(
    request: Request,
    connection_id: str,
    path: str = "~"
) -> Dict[str, Any]:
    """
    List remote directory contents.
    
    Args:
        connection_id: SSH connection ID (format: user@host:port)
        path: Remote directory path
        
    Returns:
        Directory listing
        
    Raises:
        HTTPException: If connection not found or operation fails
    """
    if not hasattr(request.app.state, 'connection_pool'):
        raise HTTPException(
            status_code=400,
            detail="Connection pool not initialized"
        )
    
    pool: SSHConnectionPool = request.app.state.connection_pool
    
    # Parse connection_id
    try:
        username_host, port_str = connection_id.rsplit(":", 1)
        username, host = username_host.split("@", 1)
        port = int(port_str)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid connection_id format: {connection_id}"
        )
    
    # Get connection
    connection = pool.get_connection(host, port, username)
    if not connection or not connection.is_connected:
        raise HTTPException(
            status_code=404,
            detail=f"Connection not found or inactive: {connection_id}"
        )
    
    try:
        # Get SFTP client
        sftp = connection.get_sftp()
        
        # Expand home directory
        if path == "~" or path.startswith("~/"):
            stdout, _, _ = connection.exec_command("echo $HOME")
            home = stdout.strip()
            path = path.replace("~", home, 1)
        
        # List directory
        items = []
        for entry in sftp.listdir_attr(path):
            import stat
            items.append({
                "name": entry.filename,
                "is_dir": stat.S_ISDIR(entry.st_mode),
                "size": entry.st_size if not stat.S_ISDIR(entry.st_mode) else 0,
                "mtime": entry.st_mtime,
            })
        
        # Sort: directories first, then by name
        items.sort(key=lambda x: (not x["is_dir"], x["name"]))
        
        return {
            "path": path,
            "items": items
        }
        
    except Exception as e:
        logger.error(f"Failed to list remote directory: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list directory: {str(e)}"
        )


@router.get("/remote/fs/exists")
async def check_remote_path_exists(
    request: Request,
    connection_id: str,
    path: str
) -> Dict[str, Any]:
    """
    Check if remote path exists.
    
    Args:
        connection_id: SSH connection ID
        path: Remote path to check
        
    Returns:
        Existence check result
    """
    if not hasattr(request.app.state, 'connection_pool'):
        raise HTTPException(
            status_code=400,
            detail="Connection pool not initialized"
        )
    
    pool: SSHConnectionPool = request.app.state.connection_pool
    
    # Parse connection_id
    try:
        username_host, port_str = connection_id.rsplit(":", 1)
        username, host = username_host.split("@", 1)
        port = int(port_str)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid connection_id format: {connection_id}"
        )
    
    # Get connection
    connection = pool.get_connection(host, port, username)
    if not connection or not connection.is_connected:
        raise HTTPException(
            status_code=404,
            detail=f"Connection not found or inactive: {connection_id}"
        )
    
    try:
        # Check if path exists using test command
        stdout, stderr, exit_code = connection.exec_command(f"test -e '{path}' && echo 'exists' || echo 'not_exists'")
        exists = stdout.strip() == "exists"
        
        # Check if it's a directory
        is_dir = False
        if exists:
            stdout2, _, _ = connection.exec_command(f"test -d '{path}' && echo 'yes' || echo 'no'")
            is_dir = stdout2.strip() == "yes"
        
        return {
            "path": path,
            "exists": exists,
            "is_dir": is_dir
        }
        
    except Exception as e:
        logger.error(f"Failed to check remote path: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check path: {str(e)}"
        )


# ==================== Status ====================

@router.get("/remote/status")
async def get_remote_status(request: Request) -> Dict[str, Any]:
    """
    Get overall remote access status.
    
    Returns:
        Remote access status including connections and sessions
    """
    # Connection pool status
    connections = []
    if hasattr(request.app.state, 'connection_pool'):
        pool: SSHConnectionPool = request.app.state.connection_pool
        connections = pool.list_connections()
    
    # Remote Viewer sessions
    viewer_sessions = []
    if hasattr(request.app.state, 'viewer_manager'):
        manager: RemoteViewerManager = request.app.state.viewer_manager
        manager.cleanup_dead_sessions()
        sessions = manager.list_sessions()
        viewer_sessions = [s.to_dict() for s in sessions]
    
    return {
        "connections": connections,
        "viewer_sessions": viewer_sessions,
        "connection_count": len(connections),
        "viewer_session_count": len(viewer_sessions),
    }
