"""
GPU Monitoring API Routes

Provides GPU telemetry and monitoring endpoints.
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, Request

from ..services.gpu import get_gpu_telemetry

router = APIRouter()


@router.get("/gpu/telemetry")
async def gpu_telemetry() -> Dict[str, Any]:
    """
    Get current GPU telemetry data (single snapshot).
    """
    return get_gpu_telemetry()


@router.get("/gpu/telemetry/history")
async def gpu_telemetry_history(request: Request) -> Dict[str, Any]:
    """
    Get buffered GPU telemetry history from the background collector.
    Returns up to 24 h of samples collected since the server started.
    """
    collector = getattr(request.app.state, "gpu_collector", None)
    if collector is None:
        return {"available": False, "enabled": False, "samples": []}
    samples = collector.get_history()
    return {
        "available": len(samples) > 0,
        "enabled": collector.is_enabled(),
        "samples": samples,
    }


@router.get("/gpu/telemetry/config")
async def gpu_telemetry_config(request: Request) -> Dict[str, Any]:
    """
    Get GPU background collector configuration.
    """
    collector = getattr(request.app.state, "gpu_collector", None)
    return {"enabled": collector.is_enabled() if collector else False}


@router.post("/gpu/telemetry/config")
async def set_gpu_telemetry_config(
    request: Request,
    payload: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """
    Enable or disable GPU background collection.
    Persists to config.json and immediately starts/stops the collector.
    """
    collector = getattr(request.app.state, "gpu_collector", None)
    if collector is None:
        return {"ok": False, "error": "GPU collector not initialized"}
    enabled = bool(payload.get("enabled", True))
    collector.set_enabled(enabled)
    return {"ok": True, "enabled": collector.is_enabled()}
