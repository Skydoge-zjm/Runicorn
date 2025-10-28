"""
Experiment Management API Routes

Handles advanced experiment operations like tagging, search, and batch delete.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, Body

logger = logging.getLogger(__name__)
router = APIRouter()

# Try to import experiment manager if available
try:
    from ...experiment import ExperimentManager
    HAS_EXPERIMENT_MANAGER = True
except ImportError:
    ExperimentManager = None
    HAS_EXPERIMENT_MANAGER = False
    logger.debug("ExperimentManager not available")


@router.post("/experiments/tag")
async def tag_experiment(request: Request, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Add tags to an experiment.
    
    Args:
        payload: Tagging parameters including run_id and tags
        
    Returns:
        Tagging operation result
        
    Raises:
        HTTPException: If experiment manager is not available or operation fails
    """
    if not HAS_EXPERIMENT_MANAGER:
        raise HTTPException(status_code=501, detail="Experiment management not available")
    
    run_id = payload.get("run_id")
    tags = payload.get("tags", [])
    append = payload.get("append", True)
    
    if not run_id:
        raise HTTPException(status_code=400, detail="run_id is required")
    
    try:
        storage_root = request.app.state.storage_root
        manager = ExperimentManager(storage_root)
        success = manager.tag_experiment(run_id, tags, append)
        return {"success": success}
    except Exception as e:
        logger.error(f"Failed to tag experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/search")
async def search_experiments(
    request: Request,
    project: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated
    text: Optional[str] = None,
    archived: bool = False
) -> Dict[str, Any]:
    """
    Search experiments by various criteria.
    
    Args:
        project: Filter by project name
        tags: Comma-separated list of tags
        text: Text search in experiment names and descriptions
        archived: Include archived experiments
        
    Returns:
        Search results
        
    Raises:
        HTTPException: If experiment manager is not available or search fails
    """
    if not HAS_EXPERIMENT_MANAGER:
        raise HTTPException(status_code=501, detail="Experiment management not available")
    
    try:
        storage_root = request.app.state.storage_root
        manager = ExperimentManager(storage_root)
        tag_list = tags.split(",") if tags else None
        results = manager.search_experiments(
            project=project,
            tags=tag_list,
            text=text,
            archived=archived
        )
        return {"experiments": [r.to_dict() for r in results]}
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/experiments/delete")
async def delete_experiments(request: Request, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Delete experiments permanently.
    
    Args:
        payload: Deletion parameters including run_ids and force flag
        
    Returns:
        Deletion results
        
    Raises:
        HTTPException: If experiment manager is not available or deletion fails
    """
    if not HAS_EXPERIMENT_MANAGER:
        raise HTTPException(status_code=501, detail="Experiment management not available")
    
    run_ids = payload.get("run_ids", [])
    force = payload.get("force", False)
    
    if not run_ids:
        raise HTTPException(status_code=400, detail="run_ids are required")
    
    try:
        storage_root = request.app.state.storage_root
        manager = ExperimentManager(storage_root)
        results = manager.delete_experiments(run_ids, force)
        return {"results": results}
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
