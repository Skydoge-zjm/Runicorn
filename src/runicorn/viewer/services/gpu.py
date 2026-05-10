"""
GPU Monitoring Service

Provides GPU telemetry data through nvidia-smi integration.
"""
from __future__ import annotations

import collections
import logging
import os
import shutil
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Background GPU collector
# ---------------------------------------------------------------------------

def _max_samples(interval: float, max_duration_h: float) -> int:
    """Compute deque maxlen from interval and max duration."""
    return max(60, int(max_duration_h * 3600 / max(interval, 0.5)))


class GpuCollector:
    """Background daemon that periodically samples GPU telemetry.

    Samples are stored in a bounded deque whose size is derived from
    ``interval_sec`` and ``max_duration_h``.
    """

    def __init__(self, *, enabled: bool = True, interval_sec: float = 2.0, max_duration_h: float = 24.0):
        self._enabled = enabled
        self._interval = interval_sec
        self._max_duration_h = max_duration_h
        self._buffer: collections.deque = collections.deque(maxlen=_max_samples(interval_sec, max_duration_h))
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # -- public API --

    def start(self) -> None:
        """Start the collector thread (if enabled)."""
        if not self._enabled:
            logger.info("GPU background collector disabled by config")
            return
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("GPU background collector started (interval=%.1fs)", self._interval)

    def stop(self) -> None:
        """Stop the collector thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("GPU background collector stopped")

    def is_enabled(self) -> bool:
        return self._enabled

    def get_interval(self) -> float:
        return self._interval

    def get_max_duration_h(self) -> float:
        return self._max_duration_h

    def set_config(self, *, enabled: Optional[bool] = None,
                   interval_sec: Optional[float] = None,
                   max_duration_h: Optional[float] = None) -> None:
        """Update collector config and persist to config.json.

        Changes to interval / max_duration take effect on next app restart;
        enable/disable takes effect immediately.
        """
        from ...config import save_user_config
        patch: dict = {}
        if enabled is not None:
            self._enabled = enabled
            patch["gpu_background_collect"] = enabled
        if interval_sec is not None:
            self._interval = max(0.5, min(interval_sec, 60))
            patch["gpu_interval_sec"] = self._interval
        if max_duration_h is not None:
            self._max_duration_h = max(0.5, min(max_duration_h, 48))
            patch["gpu_max_duration_h"] = self._max_duration_h
        if interval_sec is not None or max_duration_h is not None:
            new_maxlen = _max_samples(self._interval, self._max_duration_h)
            with self._lock:
                old = list(self._buffer)
                self._buffer = collections.deque(old[-new_maxlen:], maxlen=new_maxlen)
        if patch:
            save_user_config(patch)
        # immediate start/stop based on enabled
        if enabled is True:
            self.start()
        elif enabled is False:
            self.stop()

    def get_history(self) -> List[Dict[str, Any]]:
        """Return a copy of all buffered samples."""
        with self._lock:
            return list(self._buffer)

    def get_latest(self) -> Optional[Dict[str, Any]]:
        """Return the most recent sample, or *None*."""
        with self._lock:
            return self._buffer[-1] if self._buffer else None

    # -- internals --

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                sample = get_gpu_telemetry()
                if sample.get("available"):
                    with self._lock:
                        self._buffer.append(sample)
            except Exception:
                logger.debug("GPU collector poll error", exc_info=True)
            self._stop_event.wait(self._interval)


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
    # Note: Using enforced.power.limit instead of power.limit because:
    # - power.limit: software-set limit (often N/A on laptop GPUs)
    # - enforced.power.limit: actual power ceiling used by power management
    fields = [
        "index", "name", "utilization.gpu", "utilization.memory", 
        "memory.total", "memory.used", "temperature.gpu", "power.draw", 
        "enforced.power.limit", "clocks.sm", "clocks.mem", "pstate", "fan.speed",
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
