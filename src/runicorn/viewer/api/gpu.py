"""
GPU Monitoring API Routes

Provides GPU telemetry and monitoring endpoints.
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from ..services.gpu import get_gpu_telemetry

router = APIRouter()


@router.get("/gpu/telemetry")
async def gpu_telemetry() -> Dict[str, Any]:
    """
    Get current GPU telemetry data.
    
    Returns:
        GPU telemetry information including utilization, memory, temperature, etc.
        Returns availability status if nvidia-smi is not found.
    """
    return get_gpu_telemetry()
