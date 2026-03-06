"""
Health Check API Routes

Provides system health and status monitoring endpoints.
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Request, HTTPException
from ...storage.file_utils import iter_all_runs, read_json, update_status_if_process_dead
from ...sdk import _normalize_status
from ..utils.incremental_cache import get_incremental_metrics_cache
from ..services.db_reader import get_backend

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> Dict[str, Any]:
    """
    Get system health status.
    
    Returns:
        System health information including storage path and cache stats
    """
    storage_root = request.app.state.storage_root
    cache = get_incremental_metrics_cache()
    cache_stats = cache.stats()
    
    # Get version from viewer module
    from .. import __version__
    
    return {
        "status": "ok", 
        "storage": str(storage_root),
        "version": __version__,
        "cache": {
            "enabled": True,
            "type": "incremental",
            "hit_rate": f"{cache_stats['hit_rate']:.1%}",
            "hits": cache_stats['hits'],
            "misses": cache_stats['misses'],
            "incremental_updates": cache_stats.get('incremental_updates', 0),
            "size": cache_stats['size'],
            "max_size": cache_stats['max_size'],
        }
    }


@router.post("/status/check")
async def check_all_status(request: Request) -> Dict[str, Any]:
    """
    Manually trigger status check for all running experiments.
    
    This endpoint scans all experiments and updates their status
    if the associated process is no longer running.
    
    Returns:
        Summary of status check results
    """
    storage_root = request.app.state.storage_root
    backend = get_backend(request)
    checked_count = 0
    updated_count = 0
    
    # --- SQLite fast-path: only query running experiments ---
    if backend is not None:
        try:
            from pathlib import Path
            running_exps = backend.get_running_experiments()
            for exp in running_exps:
                run_dir = Path(exp["run_dir"]) if exp.get("run_dir") else None
                if run_dir and run_dir.exists():
                    checked_count += 1
                    update_status_if_process_dead(run_dir)
                    new_status = read_json(run_dir / "status.json")
                    new_status_val = str((new_status.get("status") if isinstance(new_status, dict) else "running") or "running")
                    if new_status_val != "running":
                        updated_count += 1
                        try:
                            backend.update_experiment(exp["id"], {"status": _normalize_status(new_status_val)})
                        except Exception:
                            pass
            return {
                "checked": checked_count,
                "updated": updated_count,
                "message": f"Checked {checked_count} running experiments, updated {updated_count} statuses"
            }
        except Exception:
            checked_count = 0
            updated_count = 0
    
    # --- File-system fallback ---
    for entry in iter_all_runs(storage_root):
        run_dir = entry.dir
        status = read_json(run_dir / "status.json")
        
        if status.get("status") == "running":
            checked_count += 1
            original_status = status.copy()
            update_status_if_process_dead(run_dir)
            
            new_status = read_json(run_dir / "status.json")
            if new_status.get("status") != original_status.get("status"):
                updated_count += 1
    
    return {
        "checked": checked_count,
        "updated": updated_count,
        "message": f"Checked {checked_count} running experiments, updated {updated_count} statuses"
    }
