"""
Run Management API Routes

Handles CRUD operations for experiment runs, including soft delete and restore functionality.
"""
from __future__ import annotations

import logging
import os
import tempfile
import mimetypes
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, Body, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from ..services.storage import (
    iter_all_runs, 
    find_run_dir_by_id, 
    read_json, 
    update_status_if_process_dead,
    is_run_deleted,
    soft_delete_run,
    restore_run,
)
from .storage_utils import get_storage_root
from ..utils.validation import validate_run_id, validate_batch_size
from ..utils.helpers import is_within_directory

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
    path: Optional[str] = None  # Flexible hierarchy path
    alias: Optional[str] = None  # User-friendly alias
    tags: List[str] = []  # User-defined tags
    assets_count: int = 0


def _count_assets_from_assets_json(assets: Any) -> int:
    if not isinstance(assets, dict):
        return 0
    n = 0
    code = assets.get("code")
    if isinstance(code, dict) and isinstance(code.get("snapshot"), dict):
        n += 1
    config = assets.get("config")
    if isinstance(config, dict) and len(config) > 0:
        n += 1
    datasets = assets.get("datasets")
    if isinstance(datasets, list):
        n += len(datasets)
    pretrained = assets.get("pretrained")
    if isinstance(pretrained, list):
        n += len(pretrained)
    outputs = assets.get("outputs")
    if isinstance(outputs, list):
        n += len(outputs)
    return int(n)


@router.get("/runs", response_model=List[RunListItem])
async def list_runs(request: Request) -> List[RunListItem]:
    """
    List all experiment runs.
    
    Supports both local and remote storage modes:
    - local mode: reads from local storage_root
    - remote mode: reads from remote cache metadata directory
    
    Returns:
        List of run information including status and best metrics
    """
    storage_root = get_storage_root(request)
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
        
        # Get path and alias from meta (new model)
        path = (meta.get("path") if isinstance(meta, dict) else None) or entry.project
        alias = (meta.get("alias") if isinstance(meta, dict) else None)
        tags = (meta.get("tags") if isinstance(meta, dict) else None) or []
        
        # Get best metric info from summary
        best_metric_value = None
        best_metric_name = None
        if isinstance(summary, dict):
            best_metric_value = summary.get("best_metric_value")
            best_metric_name = summary.get("best_metric_name")
        
        assets_count = 0
        assets_path = run_dir / "assets.json"
        if assets_path.exists():
            try:
                assets = read_json(assets_path)
                assets_count = _count_assets_from_assets_json(assets)
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
                path=path,
                alias=alias,
                tags=tags,
                assets_count=assets_count,
            )
        )
    
    return items


@router.get("/runs/{run_id}")
async def get_run_detail(run_id: str, request: Request) -> Dict[str, Any]:
    """
    Get detailed information for a specific run.
    
    Supports both local and remote storage modes.
    
    Args:
        run_id: The run ID to retrieve
        
    Returns:
        Detailed run information including file paths
        
    Raises:
        HTTPException: If run is not found
    """
    storage_root = get_storage_root(request)
    entry = find_run_dir_by_id(storage_root, run_id)
    
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run_dir = entry.dir
    
    # Check and update process status if needed
    update_status_if_process_dead(run_dir)
    
    # Load run metadata
    meta = read_json(run_dir / "meta.json")
    status = read_json(run_dir / "status.json")
    
    # Get path and alias
    path = (meta.get("path") if isinstance(meta, dict) else None) or entry.project
    alias = (meta.get("alias") if isinstance(meta, dict) else None)

    assets: Any = {}
    assets_count = 0
    assets_path = run_dir / "assets.json"
    if assets_path.exists():
        try:
            assets = read_json(assets_path)
            assets_count = _count_assets_from_assets_json(assets)
        except Exception:
            assets = {}
            assets_count = 0
    
    return {
        "id": run_id,
        "status": str((status.get("status") if isinstance(status, dict) else "finished") or "finished"),
        "pid": (meta.get("pid") if isinstance(meta, dict) else None),
        "run_dir": str(run_dir),
        "path": path,
        "alias": alias,
        "logs": str(run_dir / "logs.txt"),
        "metrics": str(run_dir / "events.jsonl"),
        "metrics_step": str(run_dir / "events.jsonl"),
        "assets": assets,
        "assets_count": assets_count,
    }


class RunUpdatePayload(BaseModel):
    """Model for run update request."""
    alias: Optional[str] = None
    tags: Optional[List[str]] = None


@router.patch("/runs/{run_id}")
async def update_run(run_id: str, request: Request, payload: RunUpdatePayload) -> Dict[str, Any]:
    """
    Update run metadata (alias, tags).
    
    Args:
        run_id: The run ID to update
        payload: Update payload containing alias and/or tags
        
    Returns:
        Updated run information
        
    Raises:
        HTTPException: If run is not found
    """
    import json
    
    storage_root = get_storage_root(request)
    
    if not validate_run_id(run_id):
        raise HTTPException(status_code=400, detail=f"Invalid run_id format: {run_id}")
    
    entry = find_run_dir_by_id(storage_root, run_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run_dir = entry.dir
    meta_path = run_dir / "meta.json"
    
    # Load existing metadata
    meta = read_json(meta_path)
    if not isinstance(meta, dict):
        meta = {}
    
    # Update alias if provided
    if payload.alias is not None:
        # Allow empty string to clear alias, strip whitespace
        alias_value = payload.alias.strip() if payload.alias else None
        meta["alias"] = alias_value if alias_value else None
    
    # Update tags if provided
    if payload.tags is not None:
        # Filter out empty strings and strip whitespace
        tags_value = [t.strip() for t in payload.tags if t and t.strip()]
        meta["tags"] = tags_value if tags_value else []
    
    # Write updated metadata
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to update meta.json for {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update run: {e}")
    
    return {
        "ok": True,
        "alias": meta.get("alias"),
        "tags": meta.get("tags", []),
    }


@router.get("/runs/{run_id}/assets")
async def get_run_assets(run_id: str, request: Request) -> Dict[str, Any]:
    storage_root = get_storage_root(request)
    entry = find_run_dir_by_id(storage_root, run_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")
    run_dir = entry.dir
    assets_path = run_dir / "assets.json"
    assets = read_json(assets_path) if assets_path.exists() else {}
    return {
        "run_id": run_id,
        "assets": assets,
        "assets_count": _count_assets_from_assets_json(assets),
    }


@router.get("/runs/{run_id}/assets/download")
async def download_run_asset(
    run_id: str,
    request: Request,
    path: str = Query(..., description="Absolute file/directory path under storage_root"),
    filename: Optional[str] = Query(None, description="Optional download filename override"),
) -> FileResponse:
    storage_root = get_storage_root(request)
    entry = find_run_dir_by_id(storage_root, run_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")

    target = Path(path)
    if not is_within_directory(storage_root, target):
        raise HTTPException(status_code=403, detail="Unsafe path")
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")

    download_name: Optional[str] = None
    if filename is not None:
        name = os.path.basename(filename)
        name = name.replace("\\", "_").replace("/", "_")
        if name.strip():
            download_name = name

    # Check if this is a manifest file (CAS directory archive)
    if target.is_file() and target.suffix == ".json" and "manifests" in str(target):
        return await _download_from_manifest(target, storage_root, download_name)

    if target.is_file():
        final_name = download_name or target.name
        media_type, _ = mimetypes.guess_type(final_name)
        return FileResponse(path=str(target), filename=final_name, media_type=media_type or "application/octet-stream")

    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Unsupported target")

    tmp_fd, tmp_path = tempfile.mkstemp(prefix="runicorn_asset_", suffix=".zip", text=False)
    os.close(tmp_fd)
    tmp_zip = Path(tmp_path)

    def _cleanup() -> None:
        try:
            if tmp_zip.exists():
                tmp_zip.unlink()
        except Exception:
            pass

    try:
        with zipfile.ZipFile(str(tmp_zip), "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for dirpath, _, filenames in os.walk(target):
                dp = Path(dirpath)
                for fn in filenames:
                    fp = dp / fn
                    try:
                        rel = fp.relative_to(target).as_posix()
                    except Exception:
                        rel = fp.name
                    zf.write(str(fp), arcname=rel)
    except Exception:
        _cleanup()
        raise

    final_name = download_name or f"{target.name}.zip"
    if not final_name.lower().endswith(".zip"):
        final_name = f"{final_name}.zip"

    return FileResponse(
        path=str(tmp_zip),
        filename=final_name,
        media_type="application/zip",
        background=BackgroundTask(_cleanup),
    )


async def _download_from_manifest(
    manifest_path: Path,
    storage_root: Path,
    download_name: Optional[str],
) -> FileResponse:
    """
    Download a CAS-archived directory by generating zip from manifest + blobs.
    """
    import json
    
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read manifest: {e}")
    
    files = manifest.get("files", {})
    if not files:
        raise HTTPException(status_code=404, detail="Manifest contains no files")
    
    blob_root = storage_root / "archive" / "blobs"
    
    # Create temp zip
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="runicorn_manifest_", suffix=".zip", text=False)
    os.close(tmp_fd)
    tmp_zip = Path(tmp_path)
    
    def _cleanup() -> None:
        try:
            if tmp_zip.exists():
                tmp_zip.unlink()
        except Exception:
            pass
    
    try:
        with zipfile.ZipFile(str(tmp_zip), "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for rel_path, entry in files.items():
                sha256 = entry.get("sha256")
                if not sha256:
                    continue
                blob_path = blob_root / sha256[:2] / sha256
                if not blob_path.exists():
                    logger.warning(f"Blob not found: {sha256} for {rel_path}")
                    continue
                zf.write(str(blob_path), arcname=rel_path)
    except Exception as e:
        _cleanup()
        raise HTTPException(status_code=500, detail=f"Failed to create zip: {e}")
    
    # Determine filename
    if download_name:
        final_name = download_name
    else:
        # Use source_path from manifest or fingerprint
        source_path = manifest.get("source_path", "")
        if source_path:
            final_name = Path(source_path).name
        else:
            final_name = manifest.get("fingerprint", "archive")[:16]
    
    if not final_name.lower().endswith(".zip"):
        final_name = f"{final_name}.zip"
    
    return FileResponse(
        path=str(tmp_zip),
        filename=final_name,
        media_type="application/zip",
        background=BackgroundTask(_cleanup),
    )


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
        
        path = (meta.get("path") if isinstance(meta, dict) else None) or entry.project
        alias = (meta.get("alias") if isinstance(meta, dict) else None)
        
        created = meta.get("created_at") if isinstance(meta, dict) else None
        if not isinstance(created, (int, float)):
            try:
                created = run_dir.stat().st_mtime
            except Exception:
                created = None
        
        items.append({
            "id": run_id,
            "path": path,
            "alias": alias,
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


# -------------------- Permanent Delete with Assets --------------------

@router.delete("/runs/{run_id}/permanent")
async def permanent_delete_run(
    run_id: str,
    request: Request,
    dry_run: bool = Query(False, description="Preview deletion without actually deleting"),
) -> Dict[str, Any]:
    """
    Permanently delete a run and its orphaned assets.
    
    This will:
    1. Delete the run directory
    2. Delete any assets only referenced by this run (orphaned assets)
    3. Keep assets that are shared with other runs
    4. Clean up blob files for orphaned assets
    
    Args:
        run_id: The run ID to delete
        dry_run: If true, only preview what would be deleted
        
    Returns:
        Deletion summary including orphaned vs kept assets
    """
    storage_root = get_storage_root(request)
    
    if not validate_run_id(run_id):
        raise HTTPException(status_code=400, detail=f"Invalid run_id format: {run_id}")
    
    from ...assets.cleanup import delete_run_completely
    
    result = delete_run_completely(
        run_id=run_id,
        storage_root=storage_root,
        dry_run=dry_run,
    )
    
    if not result["success"] and result["errors"]:
        raise HTTPException(status_code=500, detail=result["errors"][0])
    
    return result


@router.post("/runs/permanent-delete")
async def permanent_delete_runs_batch(
    request: Request,
    payload: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """
    Permanently delete multiple runs and their orphaned assets.
    
    Args:
        payload: Dictionary containing:
            - run_ids: list of run IDs to delete
            - dry_run: optional, preview without deleting
        
    Returns:
        Summary of deletion results for each run
    """
    storage_root = get_storage_root(request)
    run_ids = payload.get("run_ids", [])
    dry_run = payload.get("dry_run", False)
    
    if not run_ids or not isinstance(run_ids, list):
        raise HTTPException(
            status_code=400,
            detail="run_ids is required and must be a list"
        )
    
    if not validate_batch_size(len(run_ids), max_size=50):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete more than 50 runs at once"
        )
    
    for run_id in run_ids:
        if not isinstance(run_id, str) or not validate_run_id(run_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid run_id format: {run_id}"
            )
    
    from ...assets.cleanup import delete_run_completely
    
    results = {}
    total_blobs_deleted = 0
    total_bytes_freed = 0
    successful_deletes = 0
    
    for run_id in run_ids:
        result = delete_run_completely(
            run_id=run_id,
            storage_root=storage_root,
            dry_run=dry_run,
        )
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
    """
    Get asset reference information for a run.
    
    Shows which assets are shared with other runs and which are unique to this run.
    Useful for previewing what would be deleted.
    
    Returns:
        Dict with orphaned_assets (unique to this run) and shared_assets
    """
    storage_root = get_storage_root(request)
    
    if not validate_run_id(run_id):
        raise HTTPException(status_code=400, detail=f"Invalid run_id format: {run_id}")
    
    # Include deleted runs so we can preview assets before permanent deletion
    entry = find_run_dir_by_id(storage_root, run_id, include_deleted=True)
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")
    
    try:
        from ...index import IndexDb
        index_db = IndexDb(storage_root)
        
        assets = index_db.get_assets_for_run(run_id)
        
        orphaned = []
        shared = []
        
        for asset in assets:
            asset_id = asset["asset_id"]
            ref_count = index_db.get_asset_ref_count(asset_id)
            
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
                # Get other runs that reference this asset
                other_runs = [r for r in index_db.get_runs_for_asset(asset_id) if r != run_id]
                asset_info["other_runs"] = other_runs
                shared.append(asset_info)
        
        index_db.close()
        
        return {
            "run_id": run_id,
            "orphaned_assets": orphaned,
            "shared_assets": shared,
            "orphaned_count": len(orphaned),
            "shared_count": len(shared),
        }
        
    except Exception as e:
        logger.error(f"Failed to get asset refs for {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
