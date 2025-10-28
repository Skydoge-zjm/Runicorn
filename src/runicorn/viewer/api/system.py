"""
System Monitoring API Routes

Provides system metrics endpoints for CPU, memory, and disk monitoring.
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from ..services.system_monitor import get_system_metrics, get_system_temperatures

router = APIRouter()


@router.get("/system/monitor")
async def system_monitor() -> Dict[str, Any]:
    """
    Get current system metrics including CPU, memory, and disk usage.
    
    Returns:
        System metrics information including:
        - CPU: usage percentage, core count, frequency, per-core usage
        - Memory: total, used, available, swap usage
        - Disk: total, used, free space
        - Platform: OS information
    """
    return get_system_metrics()


@router.get("/system/temperatures")
async def system_temperatures() -> Dict[str, Any]:
    """
    Get system temperature sensors (if available).
    
    Returns:
        Temperature sensor data or None if not available
    """
    temps = get_system_temperatures()
    if temps is None:
        return {"available": False, "reason": "Temperature sensors not available"}
    return {"available": True, "sensors": temps}
