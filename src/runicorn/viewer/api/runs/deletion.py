from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, Query, Request

from ..storage_utils import get_storage_root
from ...services.db_reader import find_run_entry_fast, get_backend
from ...utils.validation import validate_batch_size, validate_run_id
from .shared import logger

router = APIRouter()


@router.delete("/runs/{run_id}/permanent")
async def permanent_delete_run(
    run_id: str,
    request: Request,
    dry_run: bool = Query(False, description="Preview deletion without actually deleting"),
) -> Dict[str, Any]:
    storage_root = get_storage_root(request)
    if not validate_run_id(run_id):
        raise HTTPException(status_code=400, detail=f"Invalid run_id format: {run_id}")

    from ....assets.cleanup import delete_run_completely

    result = delete_run_completely(run_id=run_id, storage_root=storage_root, dry_run=dry_run)
    if not result["success"]:
        detail = result["errors"][0] if result["errors"] else "Deletion partially failed"
        raise HTTPException(
            status_code=500,
            detail={
                "message": detail,
                "errors": result.get("errors", []),
                "partial_failures": result.get("partial_failures", []),
            },
        )
    return result


@router.post("/runs/permanent-delete")
async def permanent_delete_runs_batch(
    request: Request,
    payload: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    storage_root = get_storage_root(request)
    run_ids = payload.get("run_ids", [])
    dry_run = payload.get("dry_run", False)
    if not run_ids or not isinstance(run_ids, list):
        raise HTTPException(status_code=400, detail="run_ids is required and must be a list")
    if not validate_batch_size(len(run_ids), max_size=50):
        raise HTTPException(status_code=400, detail="Cannot delete more than 50 runs at once")
    for run_id in run_ids:
        if not isinstance(run_id, str) or not validate_run_id(run_id):
            raise HTTPException(status_code=400, detail=f"Invalid run_id format: {run_id}")

    from ....assets.cleanup import delete_run_completely

    results = {}
    total_blobs_deleted = 0
    total_bytes_freed = 0
    successful_deletes = 0
    for run_id in run_ids:
        result = delete_run_completely(run_id=run_id, storage_root=storage_root, dry_run=dry_run)
        results[run_id] = result
        if result["success"]:
            successful_deletes += 1
            total_blobs_deleted += result.get("blobs_deleted", 0)
            total_bytes_freed += result.get("bytes_freed", 0)

    return {
        "deleted_count": successful_deletes,
        "total_runs": len(run_ids),
        "total_blobs_deleted": total_blobs_deleted,
        "total_bytes_freed": total_bytes_freed,
        "dry_run": dry_run,
        "results": results,
    }


@router.get("/runs/{run_id}/assets/refs")
async def get_run_asset_refs(run_id: str, request: Request) -> Dict[str, Any]:
    if not validate_run_id(run_id):
        raise HTTPException(status_code=400, detail=f"Invalid run_id format: {run_id}")

    entry = find_run_entry_fast(request, run_id, include_deleted=True)
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")

    backend = get_backend(request)
    if backend is None:
        raise HTTPException(status_code=503, detail="Storage backend not available")

    try:
        assets = backend.get_assets_for_run(run_id)
        orphaned = []
        shared = []
        for asset in assets:
            asset_id = asset["asset_id"]
            ref_count = backend.get_asset_ref_count(asset_id)
            asset_info = {
                "asset_id": asset_id,
                "asset_type": asset.get("asset_type"),
                "name": asset.get("name"),
                "fingerprint": asset.get("fingerprint"),
                "role": asset.get("role"),
                "ref_count": ref_count,
            }
            if ref_count <= 1:
                orphaned.append(asset_info)
            else:
                shared.append(asset_info)

        return {
            "run_id": run_id,
            "orphaned_assets": orphaned,
            "shared_assets": shared,
            "orphaned_count": len(orphaned),
            "shared_count": len(shared),
        }
    except Exception as e:
        logger.error("Failed to get asset refs for %s: %s", run_id, e)
        raise HTTPException(status_code=500, detail=str(e))
