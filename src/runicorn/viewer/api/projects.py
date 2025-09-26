"""
Project Management API Routes

Handles project and experiment name hierarchy operations.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Request

from ..api.runs import RunListItem
from ..services.storage import iter_all_runs, read_json, update_status_if_process_dead

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/projects")
async def list_projects(request: Request) -> Dict[str, List[str]]:
    """
    List all available projects.
    
    Returns:
        Dictionary with list of project names
    """
    storage_root = request.app.state.storage_root
    projects: set[str] = set()
    
    for entry in iter_all_runs(storage_root):
        if entry.project:
            projects.add(entry.project)
        else:
            # Legacy runs: try to get project from meta.json
            meta = read_json(entry.dir / "meta.json")
            project = meta.get("project") if isinstance(meta, dict) else None
            if project:
                projects.add(str(project))
    
    return {"projects": sorted(projects)}


@router.get("/projects/{project}/names")
async def list_names(project: str, request: Request) -> Dict[str, List[str]]:
    """
    List experiment names for a specific project.
    
    Args:
        project: Project name to get experiment names for
        
    Returns:
        Dictionary with list of experiment names
    """
    storage_root = request.app.state.storage_root
    names: set[str] = set()
    
    for entry in iter_all_runs(storage_root):
        # Prefer explicit fields
        entry_project = entry.project
        entry_name = entry.name
        
        if not entry_project or entry_project != project:
            # Try to get from meta.json
            meta = read_json(entry.dir / "meta.json")
            meta_project = meta.get("project") if isinstance(meta, dict) else None
            meta_name = meta.get("name") if isinstance(meta, dict) else None
            
            if meta_project == project and meta_name:
                names.add(str(meta_name))
            continue
        
        if entry_name:
            names.add(entry_name)
    
    return {"names": sorted(names)}


@router.get("/projects/{project}/names/{name}/runs", response_model=List[RunListItem])
async def list_runs_by_name(project: str, name: str, request: Request) -> List[RunListItem]:
    """
    List runs for a specific project and experiment name.
    
    Args:
        project: Project name
        name: Experiment name
        
    Returns:
        List of runs matching the project and name
    """
    storage_root = request.app.state.storage_root
    items: List[RunListItem] = []
    
    for entry in iter_all_runs(storage_root):
        # Load metadata
        meta = read_json(entry.dir / "meta.json")
        
        # Get project and name (prefer from entry structure, fallback to meta)
        entry_project = (meta.get("project") if isinstance(meta, dict) else None) or entry.project
        entry_name = (meta.get("name") if isinstance(meta, dict) else None) or entry.name
        
        # Filter by project and name
        if entry_project != project or entry_name != name:
            continue
        
        run_dir = entry.dir
        run_id = run_dir.name
        
        # Check and update process status if needed
        update_status_if_process_dead(run_dir)
        
        # Load additional metadata
        status = read_json(run_dir / "status.json")
        summary = read_json(run_dir / "summary.json")
        
        # Extract creation time
        created = meta.get("created_at") if isinstance(meta, dict) else None
        if not isinstance(created, (int, float)):
            try:
                created = run_dir.stat().st_mtime
            except Exception:
                created = None
        
        # Get best metric info from summary
        best_metric_value = None
        best_metric_name = None
        if isinstance(summary, dict):
            best_metric_value = summary.get("best_metric_value")
            best_metric_name = summary.get("best_metric_name")
        
        items.append(
            RunListItem(
                id=run_id,
                run_dir=str(run_dir),
                created_time=created,
                status=str((status.get("status") if isinstance(status, dict) else "finished") or "finished"),
                pid=(meta.get("pid") if isinstance(meta, dict) else None),
                best_metric_value=best_metric_value,
                best_metric_name=best_metric_name,
                project=entry_project,
                name=entry_name,
            )
        )
    
    return items
