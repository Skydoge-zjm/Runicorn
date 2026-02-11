"""
Unified Remote API Routes

Provides unified remote access via SSH for Remote Viewer mode.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, HTTPException, Request, Body
from pydantic import BaseModel, Field

from ...remote.host_key import HostKeyConfirmationRequiredError, HostKeyProblem

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_host_key_confirmation_required_detail(problem: HostKeyProblem) -> Dict[str, Any]:
    """Build a stable 409 payload for host key confirmation."""

    host_key: Dict[str, Any] = {
        "host": problem.host,
        "port": problem.port,
        "known_hosts_host": problem.known_hosts_host,
        "key_type": problem.key_type,
        "fingerprint_sha256": problem.fingerprint_sha256,
        "public_key": problem.public_key,
        "reason": problem.reason,
    }

    if problem.expected_fingerprint_sha256 is not None:
        host_key["expected_fingerprint_sha256"] = problem.expected_fingerprint_sha256
    if problem.expected_public_key is not None:
        host_key["expected_public_key"] = problem.expected_public_key

    return {
        "code": "HOST_KEY_CONFIRMATION_REQUIRED",
        "message": "Host key verification failed",
        "host_key": host_key,
    }


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
    conda_env: Optional[str] = Field(None, description="Conda environment name")


class KnownHostsAcceptRequest(BaseModel):
    host: str
    port: int = Field(..., ge=1, le=65535)
    key_type: str
    public_key: str = Field(..., min_length=1, max_length=8192)
    fingerprint_sha256: str


class KnownHostsRemoveRequest(BaseModel):
    host: str
    port: int = Field(..., ge=1, le=65535)
    key_type: str


class KnownHostsEntry(BaseModel):
    host: str
    port: int
    known_hosts_host: str
    key_type: str
    key_base64: str
    fingerprint_sha256: str


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
        
    except HostKeyConfirmationRequiredError as e:
        raise HTTPException(
            status_code=409,
            detail=_build_host_key_confirmation_required_detail(e.problem),
        )
        
    except Exception as e:
        logger.error(f"SSH connection failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Connection failed: {str(e)}"
        )


@router.post("/remote/known-hosts/accept")
async def accept_known_host(payload: KnownHostsAcceptRequest) -> Dict[str, Any]:
    try:
        from ...remote.known_hosts import (
            KnownHostsStore,
            compute_fingerprint_sha256,
            parse_openssh_public_key,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Remote module not available: {e}",
        )

    if not payload.host:
        raise HTTPException(status_code=400, detail="Invalid host")
    if not payload.key_type:
        raise HTTPException(status_code=400, detail="Invalid key_type")
    if not payload.fingerprint_sha256:
        raise HTTPException(status_code=400, detail="Invalid fingerprint_sha256")

    if "\n" in payload.public_key or "\r" in payload.public_key:
        raise HTTPException(status_code=400, detail="Invalid public_key")
    if "\n" in payload.host or "\r" in payload.host or any(ch.isspace() for ch in payload.host):
        raise HTTPException(status_code=400, detail="Invalid host")
    if "," in payload.host:
        raise HTTPException(status_code=400, detail="Invalid host")
    if "\n" in payload.key_type or "\r" in payload.key_type or any(ch.isspace() for ch in payload.key_type):
        raise HTTPException(status_code=400, detail="Invalid key_type")
    if (
        "\n" in payload.fingerprint_sha256
        or "\r" in payload.fingerprint_sha256
        or any(ch.isspace() for ch in payload.fingerprint_sha256)
    ):
        raise HTTPException(status_code=400, detail="Invalid fingerprint_sha256")

    try:
        parsed_key = parse_openssh_public_key(payload.public_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid public_key: {str(e)}")

    if parsed_key.key_type != payload.key_type:
        raise HTTPException(status_code=400, detail="key_type does not match public_key")

    computed_fingerprint = compute_fingerprint_sha256(parsed_key.key_bytes)
    if computed_fingerprint != payload.fingerprint_sha256:
        raise HTTPException(
            status_code=400,
            detail="fingerprint_sha256 does not match public_key",
        )

    store = KnownHostsStore.from_runicorn_config()
    try:
        store.upsert_host_key(
            host=payload.host,
            port=payload.port,
            key_type=payload.key_type,
            key_base64=parsed_key.key_base64,
        )
    except Exception as e:
        logger.error(f"Failed to write known_hosts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to write known_hosts: {str(e)}",
        )

    return {"ok": True}


@router.get("/remote/known-hosts/list")
async def list_known_hosts() -> Dict[str, List[KnownHostsEntry]]:
    try:
        from ...remote.known_hosts import KnownHostsStore
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Remote module not available: {e}",
        )

    store = KnownHostsStore.from_runicorn_config()
    try:
        entries = store.list_host_keys()
    except Exception as e:
        logger.error(f"Failed to list known_hosts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list known_hosts: {str(e)}",
        )

    return {"entries": [KnownHostsEntry(**entry) for entry in entries]}


@router.post("/remote/known-hosts/remove")
async def remove_known_host(payload: KnownHostsRemoveRequest) -> Dict[str, Any]:
    try:
        from ...remote.known_hosts import KnownHostsStore
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Remote module not available: {e}",
        )

    if not payload.host:
        raise HTTPException(status_code=400, detail="Invalid host")
    if not payload.key_type:
        raise HTTPException(status_code=400, detail="Invalid key_type")

    store = KnownHostsStore.from_runicorn_config()
    try:
        changed = store.remove_host_key(
            host=payload.host, port=payload.port, key_type=payload.key_type
        )
    except Exception as e:
        logger.error(f"Failed to remove known_hosts entry: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove known_hosts entry: {str(e)}",
        )

    return {"ok": True, "changed": changed}


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
    try:
        connections = pool.list_connections()
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sessions: {str(e)}",
        )
    
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
    try:
        removed = pool.remove(host, port, username)
    except Exception as e:
        logger.error(f"Failed to disconnect: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect: {str(e)}",
        )
    
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
        
        # Get Python command for the specified conda environment
        python_cmd = None
        if payload.conda_env:
            from ...remote.environment import RemoteEnvironmentDetector
            detector = RemoteEnvironmentDetector(connection)
            python_cmd = detector.get_python_command_for_env(payload.conda_env)
            if python_cmd:
                logger.info(f"Using Python from environment '{payload.conda_env}': {python_cmd}")
            else:
                logger.warning(f"Environment '{payload.conda_env}' not found, using default Python")
        
        # Start remote viewer session
        session = manager.start_remote_viewer(
            connection=connection,
            remote_root=payload.remote_root,
            local_port=payload.local_port,
            remote_port=payload.remote_port,
            python_cmd=python_cmd,
        )
        
        logger.info(f"Remote Viewer started: {session.session_id}")
        
        return {
            "ok": True,
            "session": session.to_dict(),
            "message": f"Remote Viewer ready at http://localhost:{session.local_port}",
        }
        
    except HostKeyConfirmationRequiredError as e:
        raise HTTPException(
            status_code=409,
            detail=_build_host_key_confirmation_required_detail(e.problem),
        )
        
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


@router.get("/remote/viewer/status/{session_id}")
async def get_viewer_session_status(
    request: Request,
    session_id: str
) -> Dict[str, Any]:
    """
    Get Remote Viewer session status by ID.
    
    Args:
        session_id: Session ID to query
        
    Returns:
        Session status information
        
    Raises:
        HTTPException: If session not found
    """
    if not hasattr(request.app.state, 'viewer_manager'):
        raise HTTPException(
            status_code=400,
            detail="Remote Viewer manager not initialized"
        )
    
    manager: RemoteViewerManager = request.app.state.viewer_manager
    session = manager.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )
    
    return session.to_dict()


@router.get("/remote/conda-envs")
async def list_conda_envs(
    request: Request,
    connection_id: str
) -> Dict[str, Any]:
    """
    List all Python environments on remote server.
    
    Uses RemoteEnvironmentDetector for robust environment detection.
    
    Args:
        connection_id: SSH connection ID (format: user@host:port)
        
    Returns:
        List of detected Python environments
        
    Raises:
        HTTPException: If connection not found
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
        from ...remote.environment import RemoteEnvironmentDetector
        
        # Use the new environment detector
        detector = RemoteEnvironmentDetector(connection)
        python_envs = detector.detect_all_environments()
        
        # Convert to API response format
        envs = []
        for env in python_envs:
            envs.append({
                "name": env.name,
                "type": env.type,
                "python_version": env.version,
                "path": env.python_path,
                "is_default": env.is_default
            })
        
        return {"ok": True, "envs": envs}
        
    except Exception as e:
        logger.error(f"Failed to detect environments: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to detect environments: {str(e)}"
        )


@router.get("/remote/config")
async def get_remote_config(
    request: Request,
    connection_id: str,
    conda_env: str = "system"
) -> Dict[str, Any]:
    """
    Get runicorn configuration from remote server.
    
    This endpoint:
    1. Checks if runicorn is installed
    2. Gets default storage root path
    3. Checks if path exists
    4. Returns configuration for user confirmation
    
    Args:
        connection_id: SSH connection ID (format: user@host:port)
        
    Returns:
        Remote runicorn configuration
        
    Raises:
        HTTPException: If connection not found or runicorn not available
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
        from ...remote.environment import RemoteEnvironmentDetector
        
        # Use environment detector to get Python command
        detector = RemoteEnvironmentDetector(connection)
        
        if conda_env and conda_env != "system":
            # Get the Python command for this environment
            cmd_prefix = detector.get_python_command_for_env(conda_env)
            
            if not cmd_prefix:
                raise HTTPException(
                    status_code=404,
                    detail=f"Environment '{conda_env}' not found. Please check the environment name."
                )
            
            logger.info(f"Using Python command for {conda_env}: {cmd_prefix}")
        else:
            cmd_prefix = "python3"
        
        # Get Python version
        stdout, stderr, exit_code = connection.exec_command(f"{cmd_prefix} --version")
        if exit_code != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to run Python in environment: {conda_env}"
            )
        
        python_version = stdout.strip() if stdout.strip() else stderr.strip()
        
        # Check runicorn installation
        # Use getattr to safely get version, fallback to "unknown"
        stdout, stderr, exit_code = connection.exec_command(
            f"{cmd_prefix} -c 'import runicorn; print(getattr(runicorn, \"__version__\", \"unknown\"))'"
        )
        
        logger.info(f"Checking runicorn: exit_code={exit_code}, stdout={stdout[:100]}, stderr={stderr[:200]}")
        
        runicorn_version = None  # Default to None if not installed
        
        if exit_code != 0:
            # Try to get more information from pip
            pip_stdout, _, pip_exit = connection.exec_command(
                f"{cmd_prefix} -m pip show runicorn"
            )
            
            # Check if it's an editable installation
            if pip_exit == 0 and "editable" in pip_stdout.lower():
                logger.warning("Detected editable installation, trying to extract path")
                
                # Extract the editable location
                import re
                match = re.search(r'Location:\s*(.+)', pip_stdout)
                if match:
                    editable_path = match.group(1).strip()
                    logger.info(f"Found editable installation at: {editable_path}")
                    
                    # Try again with PYTHONPATH
                    stdout, stderr, exit_code = connection.exec_command(
                        f"PYTHONPATH={editable_path}:$PYTHONPATH {cmd_prefix} -c 'import runicorn; print(runicorn.__version__)'"
                    )
                    
                    if exit_code == 0:
                        logger.info("Successfully imported runicorn with PYTHONPATH")
                        # Update cmd_prefix to include PYTHONPATH for future commands
                        cmd_prefix = f"PYTHONPATH={editable_path}:$PYTHONPATH {cmd_prefix}"
                        runicorn_version = stdout.strip() if stdout.strip() else "unknown"
                    else:
                        logger.warning(f"Editable installation detected but cannot be imported from {editable_path}")
                        runicorn_version = None
            
            if exit_code != 0 and runicorn_version is None:
                # Runicorn is not installed - this is OK, just log it
                logger.info(f"runicorn not installed in environment '{conda_env}'")
                runicorn_version = None
        else:
            # Get version from the earlier check
            runicorn_version = stdout.strip() if stdout.strip() else "unknown"
        
        # Get storage root from remote server's configuration
        # Priority: 1) RUNICORN_DIR env var, 2) user config file (only if runicorn installed), 3) reasonable default
        
        # First, check environment variable
        stdout, stderr, env_exit = connection.exec_command("echo $RUNICORN_DIR")
        env_dir = stdout.strip()
        
        if env_dir and env_dir != "":
            default_root = env_dir
            logger.info(f"Got storage root from RUNICORN_DIR env: {default_root}")
        elif runicorn_version is not None:
            # Second, try config file (only if runicorn is installed)
            stdout, stderr, config_exit = connection.exec_command(
                f"{cmd_prefix} -c 'from runicorn.config import get_user_root_dir; d=get_user_root_dir(); print(d if d else \"\")'"
            )
            
            if config_exit == 0 and stdout.strip():
                default_root = stdout.strip()
                logger.info(f"Got storage root from config file: {default_root}")
            else:
                # Third, use reasonable default for remote server
                default_root = "~/runicorn_data"
                logger.info("No config found, using default: ~/runicorn_data")
        else:
            # Runicorn not installed, use default
            default_root = "~/runicorn_data"
            logger.info("Runicorn not installed, using default: ~/runicorn_data")
        
        # Expand ~ to absolute path
        stdout, stderr, _ = connection.exec_command(f"echo {default_root}")
        absolute_root = stdout.strip()
        
        # Check if path exists
        stdout, stderr, _ = connection.exec_command(f"test -d '{absolute_root}' && echo 'exists' || echo 'not_exists'")
        path_exists = stdout.strip() == "exists"
        
        # Get available ports
        stdout, stderr, port_exit = connection.exec_command(
            "python3 -c 'import socket; s=socket.socket(); s.bind((\"\", 0)); print(s.getsockname()[1]); s.close()'"
        )
        suggested_port = int(stdout.strip()) if port_exit == 0 and stdout.strip().isdigit() else 23300
        
        result = {
            "ok": True,
            "condaEnv": conda_env,
            "pythonVersion": python_version,
            "runicornVersion": runicorn_version,
            "defaultStorageRoot": absolute_root,
            "storageRootExists": path_exists,
            "suggestedRemotePort": suggested_port,
            "connectionId": connection_id
        }
        
        logger.info(f"Remote config for {conda_env}: Python={python_version}, Runicorn={runicorn_version}, Root={absolute_root}, Port={suggested_port}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get remote config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get remote configuration: {str(e)}"
        )


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


# ==================== Saved Connections Management ====================

@router.get("/remote/connections/saved")
async def get_saved_connections() -> Dict[str, Any]:
    """
    Get all saved SSH connections from config file.
    
    Returns:
        List of saved connections
    """
    try:
        from ...config import load_saved_connections
        connections = load_saved_connections()
        return {
            "ok": True,
            "connections": connections
        }
    except Exception as e:
        logger.error(f"Failed to load saved connections: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load connections: {str(e)}"
        )


@router.post("/remote/connections/saved")
async def save_connection_config(connections: list = Body(...)) -> Dict[str, Any]:
    """
    Save SSH connections to config file.
    
    Args:
        connections: List of connection configurations
        
    Returns:
        Success status
    """
    try:
        from ...config import save_connections
        save_connections(connections)
        return {
            "ok": True,
            "message": "Connections saved successfully"
        }
    except Exception as e:
        logger.error(f"Failed to save connections: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save connections: {str(e)}"
        )
