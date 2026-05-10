"""
Unified Remote API Routes

Provides unified remote access via SSH for Remote Viewer mode.
"""
from __future__ import annotations

import re
import shlex
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

from .connections import router as connection_router
from .known_hosts import router as known_hosts_router
from .runtime import (
    _REMOTE_PIP_SHOW_MIN_TIMEOUT_S,
    _REMOTE_PYTHON_COMMAND_MIN_TIMEOUT_S,
    _REMOTE_RUNICORN_IMPORT_MIN_TIMEOUT_S,
    detect_remote_storage_candidates,
    get_active_connection,
    get_command_timeout,
    parse_connection_id,
    resolve_python_command,
)
from .saved_connections import router as saved_connections_router
from .sessions import router as sessions_router
from .shared import (
    KnownHostsAcceptRequest,
    KnownHostsEntry,
    KnownHostsRemoveRequest,
    RemoteViewerStartRequest,
    SSHConnectRequest,
    logger,
)
from .viewer_routes import router as viewer_router

router = APIRouter()
router.include_router(connection_router)
router.include_router(known_hosts_router)
router.include_router(sessions_router)
router.include_router(viewer_router)
router.include_router(saved_connections_router)

__all__ = [
    "KnownHostsAcceptRequest",
    "KnownHostsEntry",
    "KnownHostsRemoveRequest",
    "RemoteViewerStartRequest",
    "SSHConnectRequest",
    "detect_remote_storage_candidates",
    "get_active_connection",
    "get_command_timeout",
    "parse_connection_id",
    "resolve_python_command",
    "router",
]

# Backward-compatible aliases for existing tests/imports.
_detect_remote_storage_candidates = detect_remote_storage_candidates
_get_active_connection = get_active_connection
_get_command_timeout = get_command_timeout
_parse_connection_id = parse_connection_id
_resolve_python_command = resolve_python_command


@router.get("/remote/conda-envs")
async def list_conda_envs(request: Request, connection_id: str) -> Dict[str, Any]:
    if not hasattr(request.app.state, "connection_pool"):
        raise HTTPException(status_code=400, detail="Connection pool not initialized")

    pool = request.app.state.connection_pool
    host, port, username = _parse_connection_id(connection_id)
    connection = pool.get_connection(host, port, username)
    if not connection or not connection.is_connected:
        raise HTTPException(status_code=404, detail=f"Connection not found or inactive: {connection_id}")

    try:
        from ....remote.environment import RemoteEnvironmentDetector

        detector = RemoteEnvironmentDetector(connection)
        python_envs = detector.detect_all_environments()
        envs = [
            {
                "name": env.name,
                "type": env.type,
                "python_version": env.version,
                "path": env.python_path,
                "is_default": env.is_default,
            }
            for env in python_envs
        ]
        return {"ok": True, "envs": envs}
    except Exception as e:
        logger.error("Failed to detect environments: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to detect environments: {str(e)}")


@router.get("/remote/env-configs")
async def get_env_configs(request: Request, connection_id: str) -> Dict[str, Any]:
    if not hasattr(request.app.state, "connection_pool"):
        raise HTTPException(status_code=400, detail="Connection pool not initialized")

    pool = request.app.state.connection_pool
    host, port, username = _parse_connection_id(connection_id)
    connection = pool.get_connection(host, port, username)
    if not connection or not connection.is_connected:
        raise HTTPException(status_code=404, detail=f"Connection not found or inactive: {connection_id}")

    try:
        from ....remote.environment import RemoteEnvironmentDetector

        detector = RemoteEnvironmentDetector(connection)
        envs = detector.detect_all_environments()
        env_paths = [(env.name, env.python_path) for env in envs]
        runicorn_versions = detector.batch_check_runicorn(env_paths)
        configs = {
            env.name: {
                "pythonVersion": env.version,
                "runicornVersion": runicorn_versions.get(env.name),
            }
            for env in envs
        }
        return {"ok": True, "configs": configs}
    except Exception as e:
        logger.error("Failed to batch check env configs: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check environment configurations: {str(e)}",
        )


@router.get("/remote/config")
async def get_remote_config(
    request: Request,
    connection_id: str,
    conda_env: str = "system",
) -> Dict[str, Any]:
    connection = _get_active_connection(request, connection_id)

    try:
        cmd_prefix = _resolve_python_command(connection, conda_env)
        logger.info("Using Python command for %s: %s", conda_env or "system", cmd_prefix)

        stdout, stderr, exit_code = connection.exec_command(
            f"{cmd_prefix} --version",
            timeout=_get_command_timeout(connection, _REMOTE_PYTHON_COMMAND_MIN_TIMEOUT_S),
        )
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=f"Failed to run Python in environment: {conda_env}")

        python_version = stdout.strip() if stdout.strip() else stderr.strip()
        stdout, stderr, exit_code = connection.exec_command(
            f"{cmd_prefix} -c 'import runicorn; print(getattr(runicorn, \"__version__\", \"unknown\"))'",
            timeout=_get_command_timeout(connection, _REMOTE_RUNICORN_IMPORT_MIN_TIMEOUT_S),
        )

        logger.info(
            "Checking runicorn: exit_code=%s, stdout=%s, stderr=%s",
            exit_code,
            stdout[:100],
            stderr[:200],
        )

        runicorn_version = None
        if exit_code != 0:
            pip_stdout, _, pip_exit = connection.exec_command(
                f"{cmd_prefix} -m pip show runicorn",
                timeout=_get_command_timeout(connection, _REMOTE_PIP_SHOW_MIN_TIMEOUT_S),
            )
            if pip_exit == 0 and "editable" in pip_stdout.lower():
                logger.warning("Detected editable installation, trying to extract path")
                match = re.search(r"Location:\s*(.+)", pip_stdout)
                if match:
                    editable_path = match.group(1).strip()
                    logger.info("Found editable installation at: %s", editable_path)
                    stdout, stderr, exit_code = connection.exec_command(
                        f"PYTHONPATH={editable_path}:$PYTHONPATH {cmd_prefix} -c 'import runicorn; print(runicorn.__version__)'",
                        timeout=_get_command_timeout(connection, _REMOTE_RUNICORN_IMPORT_MIN_TIMEOUT_S),
                    )
                    if exit_code == 0:
                        logger.info("Successfully imported runicorn with PYTHONPATH")
                        cmd_prefix = f"PYTHONPATH={editable_path}:$PYTHONPATH {cmd_prefix}"
                        runicorn_version = stdout.strip() if stdout.strip() else "unknown"
                    else:
                        logger.warning(
                            "Editable installation detected but cannot be imported from %s",
                            editable_path,
                        )
                        runicorn_version = None
            if exit_code != 0 and runicorn_version is None:
                logger.info("runicorn not installed in environment '%s'", conda_env)
                runicorn_version = None
        else:
            runicorn_version = stdout.strip() if stdout.strip() else "unknown"

        stdout, _, _ = connection.exec_command("echo $HOME")
        home_dir = stdout.strip()
        stdout, _, env_exit = connection.exec_command("echo $RUNICORN_DIR")
        env_dir = stdout.strip()

        if env_exit == 0 and env_dir:
            default_root = env_dir
            logger.info("Got storage root from RUNICORN_DIR env: %s", default_root)
        elif runicorn_version is not None:
            stdout, _, config_exit = connection.exec_command(
                f"{cmd_prefix} -c 'from runicorn.config import get_user_root_dir; d=get_user_root_dir(); print(d if d else \"\")'",
                timeout=_get_command_timeout(connection, _REMOTE_RUNICORN_IMPORT_MIN_TIMEOUT_S),
            )
            if config_exit == 0 and stdout.strip():
                default_root = stdout.strip()
                logger.info("Got storage root from config file: %s", default_root)
            else:
                default_root = "~/runicorn_data"
                logger.info("No config found, using default: ~/runicorn_data")
        else:
            default_root = "~/runicorn_data"
            logger.info("Runicorn not installed, using default: ~/runicorn_data")

        stdout, _, _ = connection.exec_command(f"echo {default_root}")
        absolute_root = stdout.strip()
        stdout, _, _ = connection.exec_command(
            f"test -d {shlex.quote(absolute_root)} && echo 'exists' || echo 'not_exists'"
        )
        path_exists = stdout.strip() == "exists"

        stdout, _, port_exit = connection.exec_command(
            f"{cmd_prefix} -c 'import socket; s=socket.socket(); s.bind((\"\", 0)); print(s.getsockname()[1]); s.close()'",
            timeout=_get_command_timeout(connection, _REMOTE_PYTHON_COMMAND_MIN_TIMEOUT_S),
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
            "connectionId": connection_id,
            "homeDirectory": home_dir,
        }
        logger.info(
            "Remote config for %s: Python=%s, Runicorn=%s, Root=%s, Port=%s",
            conda_env,
            python_version,
            runicorn_version,
            absolute_root,
            suggested_port,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get remote config: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get remote configuration: {str(e)}")


@router.get("/remote/storage-candidates")
async def list_remote_storage_candidates(
    request: Request,
    connection_id: str,
    conda_env: str = "system",
    scan_root: Optional[str] = None,
    max_depth: int = 3,
) -> Dict[str, Any]:
    try:
        connection = _get_active_connection(request, connection_id)
        python_cmd = _resolve_python_command(connection, conda_env)
        effective_max_depth = max(1, min(int(max_depth), 8))
        candidates = _detect_remote_storage_candidates(
            connection,
            python_cmd,
            scan_root=scan_root,
            max_depth=effective_max_depth,
        )
        return {
            "scan_root": scan_root,
            "max_depth": effective_max_depth,
            "candidates": candidates,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to detect remote storage candidates: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to detect remote storage candidates: {str(e)}",
        )
