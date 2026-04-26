from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from .credentials import mask_saved_entry, merge_saved_connection_secrets
from .shared import logger

router = APIRouter()


@router.get("/remote/connections/saved")
async def get_saved_connections() -> Dict[str, Any]:
    try:
        from ....config import load_saved_connections

        connections = load_saved_connections()
        valid = [
            mask_saved_entry(c)
            for c in connections
            if c.get("kind") in ("server", "connection")
        ]
        return {"ok": True, "connections": valid}
    except Exception as e:
        logger.error("Failed to load saved connections: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to load connections: {str(e)}")


@router.post("/remote/connections/saved")
async def save_connection_config(connections: list = Body(...)) -> Dict[str, Any]:
    try:
        from ....config import save_connections

        save_connections(merge_saved_connection_secrets(connections))
        return {"ok": True, "message": "Connections saved successfully"}
    except Exception as e:
        logger.error("Failed to save connections: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to save connections: {str(e)}")
