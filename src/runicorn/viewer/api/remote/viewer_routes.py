from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, Request

from ....remote.host_key import HostKeyConfirmationRequiredError
from .shared import (
    RemoteViewerStartRequest,
    _build_host_key_confirmation_required_detail,
    _resolve_saved_server_payload,
    logger,
)

router = APIRouter()


@router.post("/remote/viewer/start")
async def start_remote_viewer(request: Request, payload: RemoteViewerStartRequest) -> Dict[str, Any]:
    try:
        from ....remote import SSHConfig, SSHConnectionPool
        from ....remote.viewer import RemoteViewerManager
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Remote Viewer module not available: {e}")

    try:
        resolved = _resolve_saved_server_payload(
            saved_server_id=payload.saved_server_id,
            host=payload.host,
            port=payload.port,
            username=payload.username,
            password=payload.password,
            private_key=payload.private_key,
            private_key_path=payload.private_key_path,
            passphrase=payload.passphrase,
            use_agent=payload.use_agent,
        )
        if not resolved["host"] or not resolved["username"]:
            raise HTTPException(
                status_code=400,
                detail="host and username are required unless saved_server_id resolves them",
            )

        if not hasattr(request.app.state, "connection_pool"):
            request.app.state.connection_pool = SSHConnectionPool()
        if not hasattr(request.app.state, "viewer_manager"):
            request.app.state.viewer_manager = RemoteViewerManager()

        pool: SSHConnectionPool = request.app.state.connection_pool
        manager: RemoteViewerManager = request.app.state.viewer_manager
        config = SSHConfig(
            host=resolved["host"],
            port=resolved["port"],
            username=resolved["username"],
            password=resolved["password"],
            private_key=resolved["private_key"],
            private_key_path=resolved["private_key_path"],
            passphrase=resolved["passphrase"],
            use_agent=resolved["use_agent"],
        )
        connection = pool.get_or_create(config)
        logger.info("Using SSH connection: %s", config.get_key())

        python_cmd = None
        if payload.conda_env:
            from ....remote.environment import RemoteEnvironmentDetector

            detector = RemoteEnvironmentDetector(connection)
            python_cmd = detector.get_python_command_for_env(payload.conda_env)
            if python_cmd:
                logger.info("Using Python from environment '%s': %s", payload.conda_env, python_cmd)
            else:
                logger.warning("Environment '%s' not found, using default Python", payload.conda_env)

        session = manager.start_remote_viewer(
            connection=connection,
            remote_root=payload.remote_root,
            local_port=payload.local_port,
            remote_port=payload.remote_port,
            python_cmd=python_cmd,
        )
        logger.info("Remote Viewer started: %s", session.session_id)
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
        logger.error("Failed to start Remote Viewer: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start Remote Viewer: {str(e)}")


@router.post("/remote/viewer/stop")
async def stop_remote_viewer(request: Request, session_id: str = Body(..., embed=True)) -> Dict[str, Any]:
    if not hasattr(request.app.state, "viewer_manager"):
        raise HTTPException(status_code=400, detail="Remote Viewer manager not initialized")

    manager = request.app.state.viewer_manager
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    conn = session.connection

    success = manager.stop_remote_viewer(session_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to stop session: {session_id}")

    remaining = manager.list_sessions()
    still_used = any(s.connection is conn for s in remaining)
    if not still_used:
        pool = getattr(request.app.state, "connection_pool", None)
        if pool is not None:
            pool.remove(conn.config.host, conn.config.port, conn.config.username)
            logger.info("Auto-disconnected SSH %s (no remaining sessions)", conn.config.get_key())

    return {"ok": True, "message": f"Session {session_id} stopped"}


@router.get("/remote/viewer/sessions")
async def list_remote_viewer_sessions(request: Request) -> Dict[str, Any]:
    if not hasattr(request.app.state, "viewer_manager"):
        return {"sessions": []}

    manager = request.app.state.viewer_manager
    return {"sessions": [session.to_dict() for session in manager.list_sessions()]}


@router.get("/remote/viewer/status/{session_id}")
async def get_viewer_session_status(request: Request, session_id: str) -> Dict[str, Any]:
    if not hasattr(request.app.state, "viewer_manager"):
        raise HTTPException(status_code=400, detail="Remote Viewer manager not initialized")

    manager = request.app.state.viewer_manager
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return session.to_dict()
