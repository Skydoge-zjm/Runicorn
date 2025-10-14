"""
Run Management API Routes

Handles CRUD operations for experiment runs, including soft delete and restore functionality.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, Body
from pydantic import BaseModel

from ..services.storage import (
    iter_all_runs, 
    find_run_dir_by_id, 
    read_json, 
    update_status_if_process_dead,
    is_run_deleted,
    soft_delete_run,
    restore_run
)
from ..utils.validation import validate_run_id, validate_batch_size

logger = logging.getLogger(__name__)
router = APIRouter()


class RunListItem(BaseModel):
    """Model for run list item response."""
    id: str
    run_dir: Optional[str]
    created_time: Optional[float]
    status: str
    pid: Optional[int] = None
    best_metric_value: Optional[float] = None
    best_metric_name: Optional[str] = None
    project: Optional[str] = None
    name: Optional[str] = None
    artifacts_created_count: int = 0
    artifacts_used_count: int = 0


@router.get("/runs", response_model=List[RunListItem])
async def list_runs(request: Request) -> List[RunListItem]:
    """
    List all experiment runs.
    
    Returns:
        List of run information including status and best metrics
    """
    storage_root = request.app.state.storage_root
    items: List[RunListItem] = []
    
    for entry in iter_all_runs(storage_root):
        run_dir = entry.dir
        run_id = run_dir.name
        
        # Load run metadata first
        meta = read_json(run_dir / "meta.json")
        status = read_json(run_dir / "status.json")
        summary = read_json(run_dir / "summary.json")
        
        # Only check process status if currently marked as "running"
        # This significantly improves performance for large run lists
        current_status = str((status.get("status") if isinstance(status, dict) else "finished") or "finished")
        if current_status == "running":
            update_status_if_process_dead(run_dir)
            # Re-read status after potential update
            status = read_json(run_dir / "status.json")
        
        # Extract creation time
        created = meta.get("created_at") if isinstance(meta, dict) else None
        if not isinstance(created, (int, float)):
            try:
                created = run_dir.stat().st_mtime
            except Exception:
                created = None
        
        # Get project and name (prefer from entry structure, fallback to meta)
        project = (meta.get("project") if isinstance(meta, dict) else None) or entry.project
        name = (meta.get("name") if isinstance(meta, dict) else None) or entry.name
        
        # Get best metric info from summary
        best_metric_value = None
        best_metric_name = None
        if isinstance(summary, dict):
            best_metric_value = summary.get("best_metric_value")
            best_metric_name = summary.get("best_metric_name")
        
        # Count artifacts created
        artifacts_created_count = 0
        artifacts_created_path = run_dir / "artifacts_created.json"
        if artifacts_created_path.exists():
            try:
                artifacts_data = read_json(artifacts_created_path) or {}
                artifacts_created_count = len(artifacts_data.get("artifacts", []))
            except Exception:
                pass
        
        # Count artifacts used
        artifacts_used_count = 0
        artifacts_used_path = run_dir / "artifacts_used.json"
        if artifacts_used_path.exists():
            try:
                artifacts_data = read_json(artifacts_used_path) or {}
                artifacts_used_count = len(artifacts_data.get("artifacts", []))
            except Exception:
                pass
        
        items.append(
            RunListItem(
                id=run_id,
                run_dir=str(run_dir),
                created_time=created,
                status=str((status.get("status") if isinstance(status, dict) else "finished") or "finished"),
                pid=(meta.get("pid") if isinstance(meta, dict) else None),
                best_metric_value=best_metric_value,
                best_metric_name=best_metric_name,
                project=project,
                name=name,
                artifacts_created_count=artifacts_created_count,
                artifacts_used_count=artifacts_used_count,
            )
        )
    
    return items


@router.get("/runs/{run_id}")
async def get_run_detail(run_id: str, request: Request) -> Dict[str, Any]:
    """
    Get detailed information for a specific run.
    
    Args:
        run_id: The run ID to retrieve
        
    Returns:
        Detailed run information including file paths
        
    Raises:
        HTTPException: If run is not found
    """
    storage_root = request.app.state.storage_root
    entry = find_run_dir_by_id(storage_root, run_id)
    
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run_dir = entry.dir
    
    # Check and update process status if needed
    update_status_if_process_dead(run_dir)
    
    # Load run metadata
    meta = read_json(run_dir / "meta.json")
    status = read_json(run_dir / "status.json")
    
    # Get project and name
    project = (meta.get("project") if isinstance(meta, dict) else None) or entry.project
    name = (meta.get("name") if isinstance(meta, dict) else None) or entry.name
    
    # Count artifacts created
    artifacts_created_count = 0
    artifacts_created_path = run_dir / "artifacts_created.json"
    if artifacts_created_path.exists():
        try:
            artifacts_data = read_json(artifacts_created_path) or {}
            artifacts_created_count = len(artifacts_data.get("artifacts", []))
        except Exception:
            pass
    
    # Count artifacts used
    artifacts_used_count = 0
    artifacts_used_path = run_dir / "artifacts_used.json"
    if artifacts_used_path.exists():
        try:
            artifacts_data = read_json(artifacts_used_path) or {}
            artifacts_used_count = len(artifacts_data.get("artifacts", []))
        except Exception:
            pass
    
    return {
        "id": run_id,
        "status": str((status.get("status") if isinstance(status, dict) else "finished") or "finished"),
        "pid": (meta.get("pid") if isinstance(meta, dict) else None),
        "run_dir": str(run_dir),
        "project": project,
        "name": name,
        "logs": str(run_dir / "logs.txt"),
        "metrics": str(run_dir / "events.jsonl"),
        "metrics_step": str(run_dir / "events.jsonl"),
        "artifacts_created_count": artifacts_created_count,
        "artifacts_used_count": artifacts_used_count,
    }


@router.post("/runs/soft-delete")
async def soft_delete_runs(request: Request, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Soft delete runs (move to recycle bin).
    
    Args:
        payload: Dictionary containing run_ids list
        
    Returns:
        Summary of deletion results
        
    Raises:
        HTTPException: If run_ids is invalid
    """
    storage_root = request.app.state.storage_root
    run_ids = payload.get("run_ids", [])
    
    if not run_ids or not isinstance(run_ids, list):
        raise HTTPException(
            status_code=400, 
            detail="run_ids is required and must be a list"
        )
    
    # Validate batch size
    if not validate_batch_size(len(run_ids), max_size=100):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete more than 100 runs at once"
        )
    
    # Validate each run_id format
    for run_id in run_ids:
        if not isinstance(run_id, str) or not validate_run_id(run_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid run_id format: {run_id}"
            )
    
    results = {}
    for run_id in run_ids:
        entry = find_run_dir_by_id(storage_root, run_id)
        if not entry:
            results[run_id] = {"success": False, "error": "run not found"}
            continue
        
        # Check if already deleted
        if is_run_deleted(entry.dir):
            results[run_id] = {"success": False, "error": "already deleted"}
            continue
        
        success = soft_delete_run(entry.dir, "user_deleted")
        results[run_id] = {"success": success}
    
    successful_deletes = sum(1 for r in results.values() if r["success"])
    return {
        "deleted_count": successful_deletes,
        "results": results,
        "message": f"Soft deleted {successful_deletes} of {len(run_ids)} runs"
    }


@router.get("/recycle-bin")
async def list_deleted_runs(request: Request) -> Dict[str, Any]:
    """
    List runs in recycle bin (soft deleted).
    
    Returns:
        List of deleted runs with deletion metadata
    """
    storage_root = request.app.state.storage_root
    items: List[Dict[str, Any]] = []
    
    for entry in iter_all_runs(storage_root, include_deleted=True):
        if not is_run_deleted(entry.dir):
            continue  # Only show deleted runs
        
        run_dir = entry.dir
        run_id = run_dir.name
        
        # Load metadata
        meta = read_json(run_dir / "meta.json") 
        deleted_info = read_json(run_dir / ".deleted")
        
        project = (meta.get("project") if isinstance(meta, dict) else None) or entry.project
        name = (meta.get("name") if isinstance(meta, dict) else None) or entry.name
        
        created = meta.get("created_at") if isinstance(meta, dict) else None
        if not isinstance(created, (int, float)):
            try:
                created = run_dir.stat().st_mtime
            except Exception:
                created = None
        
        items.append({
            "id": run_id,
            "project": project,
            "name": name,
            "created_time": created,
            "deleted_at": deleted_info.get("deleted_at"),
            "delete_reason": deleted_info.get("reason", "unknown"),
            "original_status": deleted_info.get("original_status", "unknown"),
            "run_dir": str(run_dir)
        })
    
    return {"deleted_runs": items}


@router.post("/recycle-bin/restore")
async def restore_runs(request: Request, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Restore runs from recycle bin.
    
    Args:
        payload: Dictionary containing run_ids list
        
    Returns:
        Summary of restoration results
        
    Raises:
        HTTPException: If run_ids is invalid
    """
    storage_root = request.app.state.storage_root
    run_ids = payload.get("run_ids", [])
    
    if not run_ids or not isinstance(run_ids, list):
        raise HTTPException(
            status_code=400, 
            detail="run_ids is required and must be a list"
        )
    
    # Validate batch size
    if not validate_batch_size(len(run_ids), max_size=100):
        raise HTTPException(
            status_code=400,
            detail="Cannot restore more than 100 runs at once"
        )
    
    # Validate each run_id format
    for run_id in run_ids:
        if not isinstance(run_id, str) or not validate_run_id(run_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid run_id format: {run_id}"
            )
    
    results = {}
    for run_id in run_ids:
        entry = find_run_dir_by_id(storage_root, run_id, include_deleted=True)
        if not entry:
            results[run_id] = {"success": False, "error": "run not found"}
            continue
        
        if not is_run_deleted(entry.dir):
            results[run_id] = {"success": False, "error": "run not deleted"}
            continue
        
        success = restore_run(entry.dir)
        results[run_id] = {"success": success}
    
    successful_restores = sum(1 for r in results.values() if r["success"])
    return {
        "restored_count": successful_restores,
        "results": results,
        "message": f"Restored {successful_restores} of {len(run_ids)} runs"
    }


@router.post("/recycle-bin/empty")
async def empty_recycle_bin(request: Request, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Permanently delete all runs in recycle bin.
    
    Args:
        payload: Dictionary with confirm flag
        
    Returns:
        Summary of permanent deletion results
        
    Raises:
        HTTPException: If confirmation is not provided
    """
    storage_root = request.app.state.storage_root
    confirm = payload.get("confirm", False)
    
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Must set confirm=true to permanently delete"
        )
    
    deleted_count = 0
    for entry in iter_all_runs(storage_root, include_deleted=True):
        if is_run_deleted(entry.dir):
            try:
                import shutil
                shutil.rmtree(entry.dir)
                deleted_count += 1
                logger.info(f"Permanently deleted run: {entry.dir.name}")
            except Exception as e:
                logger.error(f"Failed to permanently delete {entry.dir.name}: {e}")
    
    return {
        "permanently_deleted": deleted_count,
        "message": f"Permanently deleted {deleted_count} runs"
    }
