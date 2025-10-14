"""
Unified SSH API Routes

Provides unified SSH connection management for both smart and mirror modes.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Body
from pydantic import BaseModel, Field

from ...ssh_connection_manager import UnifiedSSHConnection
from ...ssh_sync import SSHSession, MirrorTask, list_mirrors
from ...remote_storage import RemoteStorageAdapter, RemoteConfig
from ...remote_storage.models import RemoteConnectionStatus

logger = logging.getLogger(__name__)
router = APIRouter()


class UnifiedSSHConnectRequest(BaseModel):
    """Unified SSH connection request."""
    host: str = Field(..., description="Remote server hostname or IP")
    port: int = Field(22, description="SSH port")
    username: str = Field(..., description="SSH username")
    password: Optional[str] = Field(None, description="SSH password")
    private_key: Optional[str] = Field(None, description="Private key content")
    private_key_path: Optional[str] = Field(None, description="Path to private key file")
    passphrase: Optional[str] = Field(None, description="Passphrase for private key")
    use_agent: bool = Field(True, description="Use SSH agent")


class ModeConfigRequest(BaseModel):
    """Mode-specific configuration request."""
    mode: str = Field(..., description="Mode to configure (smart/mirror)")
    # Smart mode config
    remote_root: Optional[str] = Field(None, description="Remote storage root for smart mode")
    auto_sync: Optional[bool] = Field(True, description="Enable auto sync for smart mode")
    sync_interval_minutes: Optional[int] = Field(10, description="Sync interval for smart mode")
    # Mirror mode config
    mirror_interval: Optional[float] = Field(2.0, description="Mirror interval in seconds")


@router.post("/unified/connect")
async def unified_connect(request: Request, payload: UnifiedSSHConnectRequest) -> Dict[str, Any]:
    """
    Create or reuse unified SSH connection.
    
    This endpoint creates a single SSH connection that can be shared
    between smart mode and mirror mode, avoiding duplicate connections.
    """
    try:
        # Get or create unified connection
        connection = UnifiedSSHConnection.get_or_create(
            host=payload.host.strip(),
            port=payload.port,
            username=payload.username.strip(),
            password=payload.password,
            private_key=payload.private_key,
            private_key_path=payload.private_key_path,
            passphrase=payload.passphrase,
            use_agent=payload.use_agent
        )
        
        # Connect if not already connected
        success, error = connection.connect()
        if not success:
            raise HTTPException(status_code=400, detail=error or "Connection failed")
        
        # Store connection in app state
        if not hasattr(request.app.state, 'unified_ssh_connections'):
            request.app.state.unified_ssh_connections = {}
        
        conn_key = connection.connection_id
        request.app.state.unified_ssh_connections[conn_key] = connection
        request.app.state.current_ssh_connection = connection
        
        # Get connection info
        info = connection.get_connection_info()
        
        logger.info(f"Unified SSH connection established: {conn_key}")
        
        return {
            "ok": True,
            "connection_id": conn_key,
            **info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unified connect failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unified/disconnect")
async def unified_disconnect(request: Request) -> Dict[str, Any]:
    """
    Disconnect unified SSH connection.
    
    This will only disconnect if no modes are actively using the connection.
    """
    try:
        connection = getattr(request.app.state, 'current_ssh_connection', None)
        if not connection:
            return {"ok": True, "message": "No active connection"}
        
        # Check if any modes are using the connection
        has_smart = hasattr(request.app.state, 'remote_adapter') and request.app.state.remote_adapter
        has_mirror = hasattr(request.app.state, 'mirror_tasks') and request.app.state.mirror_tasks
        
        if has_smart or has_mirror:
            return {
                "ok": False,
                "message": "Connection is in use by active modes",
                "smart_active": bool(has_smart),
                "mirror_active": bool(has_mirror)
            }
        
        # Disconnect
        connection.disconnect()
        
        # Clean up app state
        request.app.state.current_ssh_connection = None
        if hasattr(request.app.state, 'unified_ssh_connections'):
            conn_key = connection.connection_id
            request.app.state.unified_ssh_connections.pop(conn_key, None)
        
        logger.info(f"Unified SSH connection disconnected: {connection.connection_id}")
        
        return {"ok": True, "message": "Disconnected successfully"}
        
    except Exception as e:
        logger.error(f"Unified disconnect failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unified/status")
async def unified_status(request: Request) -> Dict[str, Any]:
    """Get unified SSH connection status."""
    try:
        connection = getattr(request.app.state, 'current_ssh_connection', None)
        
        if not connection:
            return {
                "connected": False,
                "connection_id": None,
                "modes": {
                    "smart": {"active": False},
                    "mirror": {"active": False}
                }
            }
        
        # Check mode status
        has_smart = hasattr(request.app.state, 'remote_adapter') and request.app.state.remote_adapter
        has_mirror = hasattr(request.app.state, 'mirror_tasks') and request.app.state.mirror_tasks
        
        # Get mirror tasks if any
        mirror_tasks = []
        if has_mirror:
            try:
                mirrors = list_mirrors()
                mirror_tasks = [
                    {
                        "id": m.id,
                        "remote_root": m.remote_root,
                        "alive": not m._stop.is_set() if hasattr(m, '_stop') else False,
                        "stats": m.stats
                    }
                    for m in mirrors
                ]
            except:
                pass
        
        return {
            "connected": connection.is_connected(),
            "connection_id": connection.connection_id,
            **connection.get_connection_info(),
            "modes": {
                "smart": {
                    "active": bool(has_smart),
                    "remote_root": getattr(request.app.state.remote_adapter, 'config', {}).get('remote_root') if has_smart else None
                },
                "mirror": {
                    "active": bool(has_mirror),
                    "tasks": mirror_tasks
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {"connected": False, "error": str(e)}


@router.post("/unified/configure_mode")
async def configure_mode(request: Request, payload: ModeConfigRequest) -> Dict[str, Any]:
    """
    Configure a specific mode using the existing SSH connection.
    
    This allows switching between modes without disconnecting.
    """
    try:
        # Get current SSH connection
        connection = getattr(request.app.state, 'current_ssh_connection', None)
        if not connection or not connection.is_connected():
            raise HTTPException(status_code=400, detail="No active SSH connection")
        
        if payload.mode == "smart":
            # Configure smart mode (RemoteStorageAdapter)
            if not payload.remote_root:
                raise HTTPException(status_code=400, detail="remote_root is required for smart mode")
            
            try:
                from ...remote_storage.adapter_unified import UnifiedRemoteStorageAdapter
            except ImportError:
                raise HTTPException(status_code=503, detail="Remote storage module not available")
            
            # Clean up existing adapter if any
            if hasattr(request.app.state, 'remote_adapter') and request.app.state.remote_adapter:
                try:
                    request.app.state.remote_adapter.close()
                except:
                    pass
            
            # Create unified adapter that reuses existing connection
            from pathlib import Path
            cache_dir = Path.home() / ".runicorn_remote_cache" / f"{connection.host}_{connection.username}"
            
            adapter = UnifiedRemoteStorageAdapter(
                unified_connection=connection,
                remote_root=payload.remote_root,
                cache_dir=cache_dir,
                auto_sync=payload.auto_sync or True,
                sync_interval_seconds=(payload.sync_interval_minutes or 10) * 60
            )
            
            # Store adapter
            request.app.state.remote_adapter = adapter
            request.app.state.storage_mode = "remote"
            
            # Acquire reference
            connection.acquire()
            
            logger.info(f"Smart mode configured with remote_root: {payload.remote_root}")
            
            # Start initial sync
            adapter.sync_metadata()
            
            return {
                "ok": True,
                "mode": "smart",
                "remote_root": payload.remote_root,
                "message": "Smart mode configured successfully"
            }
        
        elif payload.mode == "mirror":
            # Configure mirror mode
            # Mirror mode doesn't need pre-configuration, tasks are created on-demand
            
            # Initialize mirror tasks storage if not exists
            if not hasattr(request.app.state, 'mirror_tasks'):
                request.app.state.mirror_tasks = []
            
            # Store mirror interval preference
            request.app.state.mirror_interval = payload.mirror_interval or 2.0
            
            # Acquire reference
            connection.acquire()
            
            logger.info(f"Mirror mode configured with interval: {payload.mirror_interval}s")
            
            return {
                "ok": True,
                "mode": "mirror",
                "mirror_interval": payload.mirror_interval or 2.0,
                "message": "Mirror mode configured successfully"
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown mode: {payload.mode}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mode configuration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unified/listdir")
async def unified_listdir(request: Request, path: str = "") -> Dict[str, Any]:
    """
    List remote directory contents using unified SSH connection.
    
    This endpoint uses the existing unified connection to browse remote directories.
    """
    try:
        connection = getattr(request.app.state, 'current_ssh_connection', None)
        if not connection or not connection.is_connected():
            raise HTTPException(
                status_code=400,
                detail="No active SSH connection. Please connect first."
            )
        
        sftp = connection.get_sftp_client()
        if not sftp:
            raise HTTPException(
                status_code=400,
                detail="SFTP client not available"
            )
        
        # Handle path resolution
        import posixpath
        if not path or path == "~":
            # Get home directory
            try:
                stdin, stdout, stderr = connection.get_ssh_client().exec_command("echo $HOME")
                home = stdout.read().decode().strip()
                resolved_path = home if home else "/home/" + connection.username
            except:
                resolved_path = "/home/" + connection.username
        else:
            # Expand ~ if present
            if path.startswith("~"):
                try:
                    stdin, stdout, stderr = connection.get_ssh_client().exec_command("echo $HOME")
                    home = stdout.read().decode().strip()
                    resolved_path = path.replace("~", home, 1)
                except:
                    resolved_path = path.replace("~", "/home/" + connection.username, 1)
            else:
                resolved_path = path
        
        # List directory
        items = []
        import stat as statmod
        
        try:
            for name in sorted(sftp.listdir(resolved_path)):
                if name.startswith("."):
                    continue  # Skip hidden files
                
                item_path = posixpath.join(resolved_path, name)
                
                try:
                    st = sftp.stat(item_path)
                    
                    item_type = "dir" if statmod.S_ISDIR(st.st_mode) else "file"
                    
                    items.append({
                        "name": name,
                        "path": item_path,
                        "type": item_type,
                        "size": st.st_size,
                        "mtime": st.st_mtime,
                    })
                except Exception as e:
                    logger.debug(f"Failed to stat {item_path}: {e}")
                    # Still include the item with minimal info
                    items.append({
                        "name": name,
                        "path": item_path,
                        "type": "unknown",
                        "size": 0,
                        "mtime": 0,
                    })
        
        except Exception as e:
            logger.error(f"Failed to list directory {resolved_path}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list directory: {e}"
            )
        
        return {
            "items": items,
            "current_path": resolved_path,
            "ok": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Directory listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unified/deactivate_mode")
async def deactivate_mode(request: Request, mode: str = Body(..., embed=True)) -> Dict[str, Any]:
    """
    Deactivate a specific mode without disconnecting SSH.
    
    This allows switching modes without losing the connection.
    """
    try:
        connection = getattr(request.app.state, 'current_ssh_connection', None)
        
        if mode == "smart":
            # Deactivate smart mode
            if hasattr(request.app.state, 'remote_adapter') and request.app.state.remote_adapter:
                try:
                    # Don't close SSH, just clean up adapter
                    adapter = request.app.state.remote_adapter
                    # Stop auto-sync if running
                    if hasattr(adapter, '_auto_sync_task'):
                        adapter._auto_sync_task.cancel()
                    request.app.state.remote_adapter = None
                    request.app.state.storage_mode = "local"
                    
                    # Release reference
                    if connection:
                        connection.release()
                    
                    logger.info("Smart mode deactivated")
                except Exception as e:
                    logger.warning(f"Error deactivating smart mode: {e}")
            
            return {"ok": True, "mode": "smart", "message": "Smart mode deactivated"}
        
        elif mode == "mirror":
            # Deactivate mirror mode
            if hasattr(request.app.state, 'mirror_tasks'):
                # Stop all mirror tasks
                from ...ssh_sync import stop_mirror
                for task in request.app.state.mirror_tasks:
                    try:
                        stop_mirror(task.id)
                    except:
                        pass
                request.app.state.mirror_tasks = []
                
                # Release reference
                if connection:
                    connection.release()
                
                logger.info("Mirror mode deactivated")
            
            return {"ok": True, "mode": "mirror", "message": "Mirror mode deactivated"}
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown mode: {mode}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mode deactivation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
