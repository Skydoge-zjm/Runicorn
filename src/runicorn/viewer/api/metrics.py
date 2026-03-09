"""
Metrics API Routes

Handles experiment metrics data retrieval and progress monitoring.

Performance Optimizations:
- Uses thread pool executor to prevent blocking the event loop during I/O
- Employs incremental caching to efficiently handle growing event files
- Supports optional downsampling for large datasets
"""
from __future__ import annotations

import asyncio
import logging
import time as time_module
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from ...storage.file_utils import find_run_dir_by_id, read_json
from ..utils.incremental_cache import get_incremental_metrics_cache
from .storage_utils import get_storage_root
from ..services.db_reader import find_run_entry_fast

logger = logging.getLogger(__name__)
router = APIRouter()

# Thread pool for blocking I/O operations
# Using a dedicated pool prevents blocking the main event loop
_metrics_executor = ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="metrics_io"
)

# Global incremental cache instance
_incremental_cache = get_incremental_metrics_cache()


def _get_metrics_sync(events_path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Synchronous function to get metrics using incremental cache.
    
    This function is designed to be run in a thread pool to avoid
    blocking the async event loop.
    
    Args:
        events_path: Path to events.jsonl file
        
    Returns:
        Tuple of (column_names, rows)
    """
    return _incremental_cache.get_or_update(events_path)


def _downsample_lttb(
    rows: List[Dict[str, Any]], 
    target_points: int,
    x_key: str = "global_step"
) -> List[Dict[str, Any]]:
    """
    Downsample data using Largest Triangle Three Buckets (LTTB) algorithm.
    
    LTTB is a time-series aware downsampling algorithm that preserves
    visual characteristics of the data while reducing point count.
    
    Args:
        rows: List of row dictionaries
        target_points: Target number of points after downsampling
        x_key: Key to use for x-axis values
        
    Returns:
        Downsampled list of rows
    """
    n = len(rows)
    if n <= target_points:
        return rows
    
    # Get numeric columns for downsampling
    numeric_cols = set()
    for row in rows[:min(100, n)]:  # Sample first 100 rows
        for key, val in row.items():
            if key != x_key and isinstance(val, (int, float)) and val is not None:
                numeric_cols.add(key)
    
    if not numeric_cols:
        # No numeric columns, use simple uniform sampling
        step = n / target_points
        indices = [int(i * step) for i in range(target_points)]
        indices[-1] = n - 1  # Ensure last point is included
        return [rows[i] for i in indices]
    
    # Use first numeric column for LTTB selection
    y_key = sorted(numeric_cols)[0]
    
    # Build (x, y) data for LTTB
    data = []
    for i, row in enumerate(rows):
        x_val = row.get(x_key, i)
        y_val = row.get(y_key)
        if y_val is None:
            y_val = 0
        data.append((float(x_val) if x_val is not None else float(i), float(y_val)))
    
    # LTTB algorithm
    sampled_indices = [0]  # Always keep first point
    bucket_size = (n - 2) / (target_points - 2)
    
    a = 0  # Index of previously selected point
    
    for i in range(target_points - 2):
        # Calculate bucket boundaries
        bucket_start = int((i + 1) * bucket_size) + 1
        bucket_end = int((i + 2) * bucket_size) + 1
        bucket_end = min(bucket_end, n)
        
        # Calculate average point of next bucket
        next_bucket_start = bucket_end
        next_bucket_end = int((i + 3) * bucket_size) + 1
        next_bucket_end = min(next_bucket_end, n)
        
        if next_bucket_end > next_bucket_start:
            avg_x = sum(data[j][0] for j in range(next_bucket_start, next_bucket_end)) / (next_bucket_end - next_bucket_start)
            avg_y = sum(data[j][1] for j in range(next_bucket_start, next_bucket_end)) / (next_bucket_end - next_bucket_start)
        else:
            avg_x, avg_y = data[-1]
        
        # Find point in current bucket with largest triangle area
        max_area = -1.0
        max_idx = bucket_start
        
        for j in range(bucket_start, bucket_end):
            # Triangle area formula (simplified)
            area = abs(
                (data[a][0] - avg_x) * (data[j][1] - data[a][1]) -
                (data[a][0] - data[j][0]) * (avg_y - data[a][1])
            )
            if area > max_area:
                max_area = area
                max_idx = j
        
        sampled_indices.append(max_idx)
        a = max_idx
    
    sampled_indices.append(n - 1)  # Always keep last point
    
    return [rows[i] for i in sampled_indices]


@router.get("/runs/{run_id}/metrics")
async def get_metrics(
    run_id: str, 
    request: Request,
    downsample: Optional[int] = Query(
        default=None,
        ge=100,
        le=50000,
        description="Target number of data points after downsampling. None means no downsampling."
    )
) -> JSONResponse:
    """
    Get metrics data for a specific run.
    
    This endpoint uses a thread pool executor to avoid blocking the event loop
    during file I/O operations, and employs incremental caching for efficient
    handling of growing event files.
    
    Args:
        run_id: The run ID to retrieve metrics for
        downsample: Optional target point count for LTTB downsampling
        
    Returns:
        JSONResponse with columns, rows, total count, and metadata headers
        
    Raises:
        HTTPException: If run is not found
    """
    entry = find_run_entry_fast(request, run_id)
    
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")
    
    events_path = entry.dir / "events.jsonl"
    
    # Execute blocking I/O in thread pool to prevent event loop blocking
    loop = asyncio.get_event_loop()
    cols, rows = await loop.run_in_executor(
        _metrics_executor,
        _get_metrics_sync,
        events_path
    )
    
    total_count = len(rows)
    
    # Apply downsampling if requested and data is large enough
    if downsample is not None and total_count > downsample:
        rows = _downsample_lttb(rows, downsample)
    
    # Build response with metadata headers for client-side optimization
    response_data = {
        "columns": cols,
        "rows": rows,
        "total": total_count,
        "sampled": len(rows) if downsample else total_count
    }
    
    response = JSONResponse(content=response_data)
    
    # Add headers for client-side cache validation
    response.headers["X-Row-Count"] = str(len(rows))
    response.headers["X-Total-Count"] = str(total_count)
    if rows:
        response.headers["X-Last-Step"] = str(rows[-1].get("global_step", 0))
    
    return response


@router.get("/runs/{run_id}/metrics_step")
async def get_metrics_step(
    run_id: str, 
    request: Request,
    downsample: Optional[int] = Query(
        default=None,
        ge=100,
        le=50000,
        description="Target number of data points after downsampling. None means no downsampling."
    )
) -> JSONResponse:
    """
    Get step-based metrics data for a specific run.
    
    This is the primary endpoint used by the frontend for chart rendering.
    It supports optional LTTB downsampling to improve performance with large datasets.
    
    Args:
        run_id: The run ID to retrieve metrics for
        downsample: Optional target point count for LTTB downsampling
        
    Returns:
        JSONResponse with columns, rows, total count, and metadata headers
        
    Raises:
        HTTPException: If run is not found
    """
    entry = find_run_entry_fast(request, run_id)
    
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")
    
    events_path = entry.dir / "events.jsonl"
    
    # Execute blocking I/O in thread pool to prevent event loop blocking
    loop = asyncio.get_event_loop()
    cols, rows = await loop.run_in_executor(
        _metrics_executor,
        _get_metrics_sync,
        events_path
    )
    
    total_count = len(rows)
    
    # Apply downsampling if requested and data is large enough
    if downsample is not None and total_count > downsample:
        rows = _downsample_lttb(rows, downsample)
    
    # Build response with metadata headers
    response_data = {
        "columns": cols,
        "rows": rows,
        "total": total_count,
        "sampled": len(rows) if downsample else total_count
    }
    
    response = JSONResponse(content=response_data)
    
    # Add headers for client-side cache validation
    response.headers["X-Row-Count"] = str(len(rows))
    response.headers["X-Total-Count"] = str(total_count)
    if rows:
        response.headers["X-Last-Step"] = str(rows[-1].get("global_step", 0))
    
    return response


@router.get("/metrics/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """
    Get metrics cache statistics for monitoring and debugging.
    
    Returns:
        Dictionary with cache statistics including hit rate and entry count
    """
    return _incremental_cache.stats()


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
    
    # Shutdown signal from app state
    shutdown_event = getattr(websocket.app.state, 'shutdown_event', None)
    
    # find_run_entry_fast works with WebSocket too (same .app.state)
    entry = find_run_entry_fast(websocket, run_id)  # type: ignore[arg-type]
    
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

    def _is_run_finished() -> bool:
        """Check if run is finished via status.json (or SQLite)."""
        status_data = read_json(entry.dir / "status.json")
        status = str(status_data.get("status", "running") or "running")
        return status != "running"

    # If log file doesn't exist, handle based on run status
    if not log_file.exists():
        # BUG-38: Finished run with no logs -> send message and close cleanly (no reconnect loop)
        if _is_run_finished():
            try:
                await websocket.send_text("[info] No logs available for this run")
                await websocket.close(code=1000)  # Normal closure
            except (WebSocketDisconnect, Exception):
                pass
            return

        # Run still running: wait for logs with timeout
        try:
            await websocket.send_text("[info] No logs available yet. Waiting for logs to be created...")
        except WebSocketDisconnect:
            logger.debug(f"WebSocket disconnected early for run {run_id}")
            return
        except Exception:
            return

        wait_interval = 5  # seconds between checks
        wait_timeout = 30  # seconds total
        waited = 0.0

        try:
            while not log_file.exists():
                if shutdown_event and shutdown_event.is_set():
                    return
                # Event-aware sleep
                if shutdown_event:
                    try:
                        await asyncio.wait_for(shutdown_event.wait(), timeout=min(2, wait_interval))
                        return
                    except asyncio.TimeoutError:
                        pass
                else:
                    await asyncio.sleep(wait_interval)

                waited += wait_interval
                if waited >= wait_timeout:
                    await websocket.send_text("[info] No logs yet. Run may not produce logs.")
                    await websocket.close(code=1000)
                    return

                # Keep-alive: ping() may not exist on all WebSocket implementations
                if not log_file.exists():
                    ping_fn = getattr(websocket, "ping", None)
                    if callable(ping_fn):
                        try:
                            await ping_fn()
                        except Exception:
                            pass
                    else:
                        try:
                            await websocket.send_text("")
                        except Exception:
                            pass
        except WebSocketDisconnect:
            logger.debug(f"WebSocket disconnected while waiting for logs for run {run_id}")
            return
        except asyncio.CancelledError:
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
        # Stream the log file content without loading all into memory
        async with aiofiles.open(log_file, mode="r", encoding="utf-8", errors="ignore") as f:
            # BUG-15: Load LAST max_initial_lines (not first) using deque for memory efficiency
            max_initial_lines = 10000  # Limit initial lines to prevent abuse
            lines_buffer = deque(maxlen=max_initial_lines)
            total_lines = 0

            async for line in f:
                total_lines += 1
                lines_buffer.append(line.rstrip("\n"))

            # Send the last N lines (skip empty when displaying)
            for line in lines_buffer:
                if line.strip():
                    await websocket.send_text(line)

            if total_lines > max_initial_lines:
                await websocket.send_text(
                    f"[info] Showing last {max_initial_lines} lines. Full log file: {log_file.name}"
                )

            # Tail for new content with dynamic polling and timeout
            start_time = time_module.time()
            last_activity = time_module.time()
            max_idle_time = 3600  # 1 hour timeout
            
            while True:
                # Check for shutdown signal
                if shutdown_event and shutdown_event.is_set():
                    break
                
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
                    
                    # Use event-aware sleep: wake immediately on shutdown
                    if shutdown_event:
                        try:
                            await asyncio.wait_for(shutdown_event.wait(), timeout=delay)
                            break  # shutdown_event was set
                        except asyncio.TimeoutError:
                            pass  # normal timeout, continue polling
                    else:
                        await asyncio.sleep(delay)
                    
    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected for run {run_id}")
        return
    except asyncio.CancelledError:
        logger.debug(f"WebSocket cancelled for run {run_id} (server shutting down)")
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
