"""
Metrics API Routes

Handles experiment metrics data retrieval and progress monitoring.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import os
from typing import Any, Dict, Iterator, List, Optional, Tuple

import aiofiles
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from ..services.storage import find_run_dir_by_id
from ..utils.cache import get_metrics_cache

logger = logging.getLogger(__name__)
router = APIRouter()

# Global metrics cache instance
metrics_cache = get_metrics_cache()


def iter_events(events_path) -> Iterator[Dict[str, Any]]:
    """
    Iterate over events in a JSONL file.
    
    Args:
        events_path: Path to events.jsonl file
        
    Yields:
        Event dictionaries
    """
    if not events_path.exists():
        return
    
    try:
        with open(events_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    continue
    except Exception:
        return


def aggregate_step_metrics(events_path) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Aggregate step metrics from events file with caching, handling NaN and Inf values.
    
    Args:
        events_path: Path to events.jsonl file
        
    Returns:
        Tuple of (column_names, rows)
    """
    # Check cache first
    cached_result = metrics_cache.get(events_path)
    if cached_result is not None:
        return cached_result
    
    def sanitize_value(v):
        """Convert NaN/Inf to None for JSON compatibility."""
        if isinstance(v, float):
            if math.isnan(v) or math.isinf(v):
                return None
        return v
    
    # Use 'global_step' if present; otherwise fall back to 'step'.
    # Merge multiple events at the same step into a single row to avoid duplicate x-axis
    # categories (which can cause apparent "jumps" for dense series when sparse series are interleaved).
    step_rows: Dict[int, Dict[str, Any]] = {}
    keys: set[str] = set()
    
    for evt in iter_events(events_path):
        if not isinstance(evt, dict) or evt.get("type") != "metrics":
            continue
        data = evt.get("data") or {}
        if not isinstance(data, dict):
            continue
        
        k = "global_step" if "global_step" in data else ("step" if "step" in data else None)
        if k is None:
            continue
            
        try:
            step_val = int(data[k])
        except Exception:
            continue
            
        row = step_rows.get(step_val)
        if row is None:
            row = {"global_step": step_val}
            step_rows[step_val] = row
            
        for kk, vv in data.items():
            if kk in ("global_step", "step", "epoch"):
                continue
            if isinstance(vv, (int, float, str)) or vv is None:
                row[kk] = sanitize_value(vv)  # Sanitize NaN/Inf values
                keys.add(kk)
    
    if not step_rows:
        result = ([], [])
    else:
        rows = [step_rows[s] for s in sorted(step_rows.keys())]
        cols = ["global_step"] + sorted(list(keys))
        
        for r in rows:
            for c in cols:
                r.setdefault(c, None)
        
        result = (cols, rows)
    
    # Cache the result
    metrics_cache.set(events_path, result)
    
    return result


@router.get("/runs/{run_id}/metrics")
async def get_metrics(run_id: str, request: Request) -> Dict[str, Any]:
    """
    Get metrics data for a specific run.
    
    Args:
        run_id: The run ID to retrieve metrics for
        
    Returns:
        Dictionary with columns and rows of metrics data
        
    Raises:
        HTTPException: If run is not found
    """
    storage_root = request.app.state.storage_root
    entry = find_run_dir_by_id(storage_root, run_id)
    
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")
    
    events_path = entry.dir / "events.jsonl"
    cols, rows = aggregate_step_metrics(events_path)
    
    return {"columns": cols, "rows": rows}


@router.get("/runs/{run_id}/metrics_step")
async def get_metrics_step(run_id: str, request: Request) -> Dict[str, Any]:
    """
    Get step-based metrics data for a specific run.
    
    Args:
        run_id: The run ID to retrieve metrics for
        
    Returns:
        Dictionary with columns and rows of step metrics data
        
    Raises:
        HTTPException: If run is not found
    """
    storage_root = request.app.state.storage_root
    entry = find_run_dir_by_id(storage_root, run_id)
    
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")
    
    events_path = entry.dir / "events.jsonl"
    cols, rows = aggregate_step_metrics(events_path)
    
    return {"columns": cols, "rows": rows}


@router.get("/runs/{run_id}/progress")
async def get_progress(run_id: str, request: Request) -> Dict[str, Any]:
    """
    Get training progress information for a specific run.
    
    Note: This is a read-only viewer, so progress tracking is limited.
    Could be estimated from events, but kept simple for MVP.
    
    Args:
        run_id: The run ID to retrieve progress for
        
    Returns:
        Progress information (currently basic)
    """
    # Read-only viewer has no in-memory progress
    # Could estimate from events, but keep simple for MVP
    return {"available": False, "status": "unknown"}


@router.websocket("/runs/{run_id}/logs/ws")
async def logs_websocket(websocket: WebSocket, run_id: str) -> None:
    """
    WebSocket endpoint for real-time log streaming with memory optimization.
    
    Features:
    - Streaming read (no large file loading into memory)
    - Automatic timeout after 1 hour of inactivity
    - Dynamic polling interval based on activity
    - Line limit to prevent abuse
    
    Args:
        websocket: WebSocket connection
        run_id: The run ID to stream logs for
    """
    await websocket.accept()
    
    # Get storage root from app state
    storage_root = websocket.app.state.storage_root
    entry = find_run_dir_by_id(storage_root, run_id)
    
    if not entry:
        try:
            await websocket.send_text("[error] run not found")
            await websocket.close()
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        return
    
    log_file = entry.dir / "logs.txt"
    
    # If log file doesn't exist, wait for it to be created
    import asyncio
    if not log_file.exists():
        try:
            await websocket.send_text("[info] No logs available yet. Waiting for logs to be created...")
        except WebSocketDisconnect:
            logger.debug(f"WebSocket disconnected early for run {run_id}")
            return
        except Exception:
            return
        
        # Keep checking for log file
        try:
            while not log_file.exists():
                await asyncio.sleep(2)
                # Send periodic keep-alive to prevent timeout
                if not log_file.exists():
                    await websocket.ping()
        except WebSocketDisconnect:
            logger.debug(f"WebSocket disconnected while waiting for logs for run {run_id}")
            return
        except Exception:
            return
        
        # Log file now exists, send notification
        try:
            await websocket.send_text("[info] Logs are now available, streaming...")
        except WebSocketDisconnect:
            return
        except Exception:
            return
    
    try:
        import time as time_module
        
        # Stream the log file content without loading all into memory
        async with aiofiles.open(log_file, mode="r", encoding="utf-8", errors="ignore") as f:
            # Send existing content line by line (streaming)
            sent_lines = 0
            max_initial_lines = 10000  # Limit initial lines to prevent abuse
            
            async for line in f:
                if sent_lines >= max_initial_lines:
                    await websocket.send_text(f"[info] Showing last {max_initial_lines} lines. Full log file: {log_file.name}")
                    break
                
                line = line.rstrip("\n")
                if line.strip():  # Skip empty lines
                    await websocket.send_text(line)
                    sent_lines += 1
            
            # Tail for new content with dynamic polling and timeout
            start_time = time_module.time()
            last_activity = time_module.time()
            max_idle_time = 3600  # 1 hour timeout
            
            while True:
                # Check for timeout
                current_time = time_module.time()
                idle_time = current_time - last_activity
                
                if idle_time > max_idle_time:
                    await websocket.send_text("[info] Connection timeout after 1 hour of inactivity")
                    break
                
                # Read new line
                line = await f.readline()
                
                if line:
                    # Got new content
                    line = line.rstrip("\n")
                    if line.strip():
                        await websocket.send_text(line)
                    last_activity = current_time  # Reset idle timer
                else:
                    # No new content, use dynamic delay
                    # Start with short delay, gradually increase if no activity
                    if idle_time < 10:
                        delay = 0.2  # Very active: 200ms
                    elif idle_time < 60:
                        delay = 0.5  # Recent activity: 500ms
                    elif idle_time < 300:
                        delay = 1.0  # Some activity: 1s
                    else:
                        delay = 2.0  # Long idle: 2s
                    
                    await asyncio.sleep(delay)
                    
    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected for run {run_id}")
        return
    except Exception as e:
        logger.error(f"WebSocket error for run {run_id}: {e}")
        try:
            await websocket.send_text(f"[error] {e}")
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
