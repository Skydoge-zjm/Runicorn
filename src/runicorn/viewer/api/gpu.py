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
    if collector is None:
        return {"enabled": False, "interval_sec": 2, "max_duration_h": 24}
    return {
        "enabled": collector.is_enabled(),
        "interval_sec": collector.get_interval(),
        "max_duration_h": collector.get_max_duration_h(),
    }


@router.post("/gpu/telemetry/config")
async def set_gpu_telemetry_config(
    request: Request,
    payload: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """
    Update GPU background collector configuration.
    Accepts: enabled (bool), interval_sec (float), max_duration_h (float).
    Persists to config.json; enable/disable takes effect immediately,
    interval/duration changes take full effect after restart.
    """
    collector = getattr(request.app.state, "gpu_collector", None)
    if collector is None:
        return {"ok": False, "error": "GPU collector not initialized"}
    kwargs: Dict[str, Any] = {}
    if "enabled" in payload:
        kwargs["enabled"] = bool(payload["enabled"])
    if "interval_sec" in payload:
        kwargs["interval_sec"] = float(payload["interval_sec"])
    if "max_duration_h" in payload:
        kwargs["max_duration_h"] = float(payload["max_duration_h"])
    collector.set_config(**kwargs)
    return {
        "ok": True,
        "enabled": collector.is_enabled(),
        "interval_sec": collector.get_interval(),
        "max_duration_h": collector.get_max_duration_h(),
    }
