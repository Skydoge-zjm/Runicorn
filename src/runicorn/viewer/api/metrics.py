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

logger = logging.getLogger(__name__)
router = APIRouter()


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
    Aggregate step metrics from events file, handling NaN and Inf values.
    
    Args:
        events_path: Path to events.jsonl file
        
    Returns:
        Tuple of (column_names, rows)
    """
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
        return [], []
    
    rows = [step_rows[s] for s in sorted(step_rows.keys())]
    cols = ["global_step"] + sorted(list(keys))
    
    for r in rows:
        for c in cols:
            r.setdefault(c, None)
    
    return cols, rows


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
    WebSocket endpoint for real-time log streaming.
    
    Args:
        websocket: WebSocket connection
        run_id: The run ID to stream logs for
    """
    await websocket.accept()
    
    # Get storage root from app state
    storage_root = websocket.app.state.storage_root
    entry = find_run_dir_by_id(storage_root, run_id)
    
    if not entry:
        await websocket.send_text("[error] run not found")
        await websocket.close()
        return
    
    log_file = entry.dir / "logs.txt"
    if not log_file.exists():
        await websocket.send_text("[info] logs.txt not found yet")
        await websocket.close()
        return
    
    try:
        # Stream the log file content
        async with aiofiles.open(log_file, mode="r", encoding="utf-8", errors="ignore") as f:
            # First, send existing content
            existing_content = await f.read()
            if existing_content:
                for line in existing_content.splitlines():
                    if line.strip():  # Skip empty lines
                        await websocket.send_text(line)
            
            # Then tail for new content
            while True:
                line = await f.readline()
                if line:
                    await websocket.send_text(line.rstrip("\n"))
                else:
                    # No new content, wait a bit
                    await asyncio.sleep(0.5)
                    
    except WebSocketDisconnect:
        return
    except Exception as e:
        try:
            await websocket.send_text(f"[error] {e}")
        except Exception:
            pass
        finally:
            await websocket.close()
