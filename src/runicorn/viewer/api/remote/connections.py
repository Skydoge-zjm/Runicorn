from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from ....remote.host_key import HostKeyConfirmationRequiredError
from .credentials import resolve_saved_server_payload
from .shared import (
    SSHConnectRequest,
    _build_host_key_confirmation_required_detail,
    logger,
)

router = APIRouter()


@router.post("/remote/connect")
async def connect_remote(request: Request, payload: SSHConnectRequest) -> Dict[str, Any]:
    try:
        from ....remote import SSHConfig, SSHConnectionPool
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Remote module not available: {e}")

    try:
        if not hasattr(request.app.state, "connection_pool"):
            request.app.state.connection_pool = SSHConnectionPool()

        pool: SSHConnectionPool = request.app.state.connection_pool
        resolved = resolve_saved_server_payload(
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

        logger.info("SSH connection established: %s", config.get_key())
        return {
            "ok": True,
            "connection_id": config.get_key(),
            "host": resolved["host"],
            "port": resolved["port"],
            "username": resolved["username"],
            "connected": connection.is_connected,
        }
    except HostKeyConfirmationRequiredError as e:
        raise HTTPException(
            status_code=409,
            detail=_build_host_key_confirmation_required_detail(e.problem),
        )
    except Exception as e:
        logger.error("SSH connection failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")
