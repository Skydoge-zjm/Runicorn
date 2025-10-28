"""
System Monitoring Service

Provides system metrics (CPU, memory, disk) using psutil.
Cross-platform compatible (Windows, Linux, macOS).
"""
from __future__ import annotations

import logging
import platform
import time
from typing import Any, Dict, List, Optional

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger(__name__)


def get_system_metrics() -> Dict[str, Any]:
    """
    Get current system metrics including CPU, memory, and disk usage.
    
    Returns:
        Dictionary containing system metrics
    """
    if not psutil:
        return {"available": False, "reason": "psutil not installed"}
    
    try:
        metrics = {
            "available": True,
            "ts": time.time(),
            "cpu": _get_cpu_metrics(),
            "memory": _get_memory_metrics(),
            "disk": _get_disk_metrics(),
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
            }
        }
        return metrics
    except Exception as e:
        logger.debug(f"System metrics error: {e}")
        return {"available": False, "reason": str(e)}


def _get_cpu_metrics() -> Dict[str, Any]:
    """Get CPU metrics."""
    # Try to get CPU metrics with individual error handling for WSL compatibility
    cpu_data = {}
    
    # Basic CPU usage - critical
    try:
        # Initialize psutil CPU measurement with non-blocking call first
        # This ensures subsequent calls have baseline data
        _ = psutil.cpu_percent(interval=None)  # Initialize
        
        # Then use blocking measurement for accurate reading
        # WSL environments may need longer interval for stable readings
        cpu_percent = psutil.cpu_percent(interval=1.0)
        cpu_count = psutil.cpu_count(logical=False) or psutil.cpu_count()
        logical_count = psutil.cpu_count(logical=True)
        
        logger.debug(f"CPU metrics: percent={cpu_percent}%, count={cpu_count}, logical={logical_count}")
        
        cpu_data.update({
            "percent": cpu_percent,
            "count": cpu_count,
            "logical_count": logical_count,
        })
    except Exception as e:
        logger.warning(f"Failed to get basic CPU metrics: {e}")
        # Return None to indicate CPU monitoring unavailable
        return None
    
    # Per-core usage - optional
    try:
        # Use same interval as overall CPU for consistency
        per_core = psutil.cpu_percent(interval=0.5, percpu=True)
        logger.debug(f"Per-core CPU usage: {per_core}")
        cpu_data["per_core"] = per_core
    except Exception as e:
        logger.debug(f"Failed to get per-core CPU usage: {e}")
        cpu_data["per_core"] = None
    
    # CPU frequency - optional
    try:
        freq = psutil.cpu_freq()
        if freq:
            cpu_data["frequency"] = {
                "current": freq.current,
                "min": freq.min,
                "max": freq.max,
            }
        else:
            cpu_data["frequency"] = None
    except Exception as e:
        logger.debug(f"Failed to get CPU frequency: {e}")
        cpu_data["frequency"] = None
    
    # Load average (Unix only) - optional
    load_avg = None
    if hasattr(psutil, "getloadavg"):
        try:
            load_avg = psutil.getloadavg()
        except (AttributeError, OSError) as e:
            logger.debug(f"Failed to get load average: {e}")
    cpu_data["load_avg"] = load_avg
    
    return cpu_data


def _get_memory_metrics() -> Dict[str, Any]:
    """Get memory metrics."""
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_percent": swap.percent,
        }
    except Exception as e:
        logger.debug(f"Memory metrics error: {e}")
        return {}


def _get_disk_metrics() -> Dict[str, Any]:
    """Get disk metrics for the root partition."""
    try:
        # Get disk usage for root/main partition
        if platform.system() == "Windows":
            disk_path = "C:\\"
        else:
            disk_path = "/"
        
        disk = psutil.disk_usage(disk_path)
        
        # Disk IO statistics
        io_counters = None
        try:
            io = psutil.disk_io_counters()
            if io:
                io_counters = {
                    "read_bytes": io.read_bytes,
                    "write_bytes": io.write_bytes,
                    "read_count": io.read_count,
                    "write_count": io.write_count,
                }
        except (AttributeError, RuntimeError):
            pass
        
        return {
            "path": disk_path,
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
            "io": io_counters,
        }
    except Exception as e:
        logger.debug(f"Disk metrics error: {e}")
        return {}


def get_system_temperatures() -> Optional[Dict[str, Any]]:
    """
    Get system temperature sensors (if available).
    This is platform-dependent and may not work on all systems.
    
    Returns:
        Dictionary of temperature sensors or None
    """
    if not psutil or not hasattr(psutil, "sensors_temperatures"):
        return None
    
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return None
        
        # Parse temperatures
        temp_data = {}
        for name, entries in temps.items():
            if entries:
                temp_data[name] = [
                    {
                        "label": entry.label or name,
                        "current": entry.current,
                        "high": entry.high,
                        "critical": entry.critical,
                    }
                    for entry in entries
                ]
        return temp_data
    except Exception as e:
        logger.debug(f"Temperature sensors error: {e}")
        return None
