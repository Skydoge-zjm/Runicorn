"""
GPU Monitoring Service

Provides GPU telemetry data through nvidia-smi integration.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def find_nvidia_smi() -> Optional[str]:
    """
    Find the nvidia-smi executable path.
    
    Returns:
        Path to nvidia-smi if found, None otherwise
    """
    try:
        # First try to find it in PATH
        found = shutil.which("nvidia-smi")
        if found:
            return found
        
        # Windows-specific common locations
        if os.name == "nt":
            candidates = [
                r"C:\Windows\System32\nvidia-smi.exe",
                r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
            ]
            for path in candidates:
                if os.path.exists(path):
                    return path
        
        return None
    except Exception as e:
        logger.debug(f"Error finding nvidia-smi: {e}")
        return None


def to_float(val: str) -> Optional[float]:
    """
    Safely convert a string value to float.
    
    Args:
        val: String value to convert
        
    Returns:
        Float value or None if conversion fails
    """
    try:
        x = val.strip()
        if not x or x.upper() == "N/A":
            return None
        return float(x)
    except Exception:
        return None


def get_gpu_telemetry() -> Dict[str, Any]:
    """
    Read GPU telemetry data using nvidia-smi.
    
    Returns:
        Dictionary containing GPU telemetry information
    """
    nvidia_smi_path = find_nvidia_smi()
    if not nvidia_smi_path:
        return {"available": False, "reason": "nvidia-smi not found in PATH"}
    
    # Fields to query from nvidia-smi
    fields = [
        "index", "name", "utilization.gpu", "utilization.memory", 
        "memory.total", "memory.used", "temperature.gpu", "power.draw", 
        "power.limit", "clocks.sm", "clocks.mem", "pstate", "fan.speed",
    ]
    
    cmd = [nvidia_smi_path, f"--query-gpu={','.join(fields)}", "--format=csv,noheader,nounits"]
    
    try:
        # Execute nvidia-smi command
        out = os.popen(" ".join(cmd)).read()
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        gpus: List[Dict[str, Any]] = []
        
        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            
            # Handle GPU names that contain commas
            if len(parts) != len(fields):
                if len(parts) > len(fields):
                    # Reconstruct GPU name that was split by commas
                    idx = parts[0]
                    name = ",".join(parts[1 : len(parts) - (len(fields) - 2)])
                    tail = parts[len(parts) - (len(fields) - 2) :]
                    parts = [idx, name] + tail
                else:
                    # Skip malformed lines
                    continue
            
            # Parse GPU data
            gpu_data = {
                "index": int(to_float(parts[0]) or 0),
                "name": parts[1],
                "util_gpu": to_float(parts[2]),
                "util_mem": to_float(parts[3]),
                "mem_total_mib": to_float(parts[4]),
                "mem_used_mib": to_float(parts[5]),
                "temp_c": to_float(parts[6]),
                "power_w": to_float(parts[7]),
                "power_limit_w": to_float(parts[8]),
                "clock_sm_mhz": to_float(parts[9]),
                "clock_mem_mhz": to_float(parts[10]),
                "pstate": parts[11],
                "fan_speed_pct": to_float(parts[12]),
            }
            
            # Calculate memory usage percentage
            try:
                if gpu_data.get("mem_total_mib") and gpu_data.get("mem_used_mib") is not None:
                    mem_used = gpu_data["mem_used_mib"] or 0.0
                    mem_total = max(1.0, gpu_data["mem_total_mib"])
                    gpu_data["mem_used_pct"] = max(0.0, min(100.0, mem_used * 100.0 / mem_total))
            except Exception:
                pass
            
            gpus.append(gpu_data)
        
        return {
            "available": True, 
            "ts": time.time(), 
            "gpus": gpus
        }
        
    except Exception as e:
        logger.debug(f"GPU telemetry error: {e}")
        return {"available": False, "reason": str(e)}
