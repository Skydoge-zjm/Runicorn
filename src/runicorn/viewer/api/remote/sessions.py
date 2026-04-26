from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, Request

from .shared import logger

router = APIRouter()


@router.get("/remote/sessions")
async def list_sessions(request: Request) -> Dict[str, Any]:
    if not hasattr(request.app.state, "connection_pool"):
        return {"sessions": []}

    pool = request.app.state.connection_pool
    try:
        connections = pool.list_connections()
    except Exception as e:
        logger.error("Failed to list sessions: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")

    return {"sessions": connections}


@router.post("/remote/disconnect")
async def disconnect_remote(
    request: Request,
    host: str = Body(..., embed=True),
    port: int = Body(22, embed=True),
    username: str = Body(..., embed=True),
) -> Dict[str, Any]:
    if not hasattr(request.app.state, "connection_pool"):
        return {"ok": False, "message": "No connection pool"}

    pool = request.app.state.connection_pool
    try:
        removed = pool.remove(host, port, username)
    except Exception as e:
        logger.error("Failed to disconnect: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to disconnect: {str(e)}")

    if removed:
        return {"ok": True, "message": "Connection removed"}
    return {"ok": False, "message": "Connection not found"}


@router.get("/remote/status")
async def get_remote_status(request: Request) -> Dict[str, Any]:
    connections = []
    if hasattr(request.app.state, "connection_pool"):
        pool = request.app.state.connection_pool
        connections = pool.list_connections()

    viewer_sessions = []
    if hasattr(request.app.state, "viewer_manager"):
        manager = request.app.state.viewer_manager
        viewer_sessions = [s.to_dict() for s in manager.list_sessions()]

    return {
        "connections": connections,
        "viewer_sessions": viewer_sessions,
        "connection_count": len(connections),
        "viewer_session_count": len(viewer_sessions),
    }
