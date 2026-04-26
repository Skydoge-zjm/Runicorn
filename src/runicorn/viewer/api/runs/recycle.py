from __future__ import annotations

import shutil
from typing import Any, Dict, List

from fastapi import APIRouter, Body, HTTPException, Request

from ....storage.file_utils import (
    find_run_dir_by_id,
    is_run_deleted,
    iter_all_runs,
    read_json,
    restore_run,
    soft_delete_run,
)
from ...services.db_reader import get_backend
from ...utils.validation import validate_batch_size, validate_run_id
from .shared import logger

router = APIRouter()


@router.post("/runs/soft-delete")
async def soft_delete_runs(request: Request, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    storage_root = request.app.state.storage_root
    run_ids = payload.get("run_ids", [])
    if not run_ids or not isinstance(run_ids, list):
        raise HTTPException(status_code=400, detail="run_ids is required and must be a list")
    if not validate_batch_size(len(run_ids), max_size=100):
        raise HTTPException(status_code=400, detail="Cannot delete more than 100 runs at once")

    for run_id in run_ids:
        if not isinstance(run_id, str) or not validate_run_id(run_id):
            raise HTTPException(status_code=400, detail=f"Invalid run_id format: {run_id}")

    backend = get_backend(request)
    results = {}
    for run_id in run_ids:
        entry = find_run_dir_by_id(storage_root, run_id)
        if not entry:
            results[run_id] = {"success": False, "error": "run not found"}
            continue
        if is_run_deleted(entry.dir):
            results[run_id] = {"success": False, "error": "already deleted"}
            continue

        run_path = entry.path
        success, error, new_dir = soft_delete_run(
            entry.dir,
            storage_root=storage_root,
            reason="user_deleted",
            original_path=run_path,
        )
        results[run_id] = {"success": success}
        if error:
            results[run_id]["error"] = error

        if success and backend is not None:
            try:
                backend.soft_delete_experiments([run_id], reason="user_deleted")
                if new_dir is not None:
                    backend.update_experiment(
                        run_id,
                        {"run_dir": str(new_dir), "path": run_path or "default"},
                    )
            except Exception:
                pass

    successful_deletes = sum(1 for r in results.values() if r["success"])
    return {
        "deleted_count": successful_deletes,
        "results": results,
        "message": f"Soft deleted {successful_deletes} of {len(run_ids)} runs",
    }


@router.get("/recycle-bin")
async def list_deleted_runs(request: Request) -> Dict[str, Any]:
    backend = get_backend(request)
    if backend is not None:
        try:
            db_rows = backend.list_deleted_for_viewer()
            if db_rows is not None:
                items: List[Dict[str, Any]] = []
                for r in db_rows:
                    items.append(
                        {
                            "id": r["id"],
                            "path": r.get("path"),
                            "alias": r.get("alias"),
                            "created_time": r.get("created_at"),
                            "deleted_at": r.get("deleted_at"),
                            "delete_reason": r.get("delete_reason", "unknown"),
                            "original_status": r.get("status", "unknown"),
                            "run_dir": r.get("run_dir", ""),
                        }
                    )
                return {"deleted_runs": items}
        except Exception:
            pass

    storage_root = request.app.state.storage_root
    items = []
    for entry in iter_all_runs(storage_root, include_deleted=True):
        if not is_run_deleted(entry.dir):
            continue

        run_dir = entry.dir
        meta = read_json(run_dir / "meta.json")
        deleted_info = read_json(run_dir / ".deleted")
        path = (meta.get("path") if isinstance(meta, dict) else None) or entry.project
        alias = meta.get("alias") if isinstance(meta, dict) else None
        created = meta.get("created_at") if isinstance(meta, dict) else None
        if not isinstance(created, (int, float)):
            try:
                created = run_dir.stat().st_mtime
            except Exception:
                created = None

        items.append(
            {
                "id": run_dir.name,
                "path": path,
                "alias": alias,
                "created_time": created,
                "deleted_at": deleted_info.get("deleted_at"),
                "delete_reason": deleted_info.get("reason", "unknown"),
                "original_status": deleted_info.get("original_status", "unknown"),
                "run_dir": str(run_dir),
            }
        )

    return {"deleted_runs": items}


@router.post("/recycle-bin/restore")
async def restore_runs(request: Request, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    storage_root = request.app.state.storage_root
    run_ids = payload.get("run_ids", [])
    if not run_ids or not isinstance(run_ids, list):
        raise HTTPException(status_code=400, detail="run_ids is required and must be a list")
    if not validate_batch_size(len(run_ids), max_size=100):
        raise HTTPException(status_code=400, detail="Cannot restore more than 100 runs at once")

    for run_id in run_ids:
        if not isinstance(run_id, str) or not validate_run_id(run_id):
            raise HTTPException(status_code=400, detail=f"Invalid run_id format: {run_id}")

    results = {}
    for run_id in run_ids:
        entry = find_run_dir_by_id(storage_root, run_id, include_deleted=True)
        if not entry:
            results[run_id] = {"success": False, "error": "run not found"}
            continue
        if not is_run_deleted(entry.dir):
            results[run_id] = {"success": False, "error": "run not deleted"}
            continue

        success, error, new_dir = restore_run(entry.dir, storage_root=storage_root)
        results[run_id] = {"success": success}
        if error:
            results[run_id]["error"] = error

        if success:
            backend = get_backend(request)
            if backend is not None:
                try:
                    backend.restore_experiments([run_id])
                    if new_dir is not None and new_dir != entry.dir:
                        meta = read_json(new_dir / "meta.json")
                        restored_path = (meta.get("path") if isinstance(meta, dict) else None) or entry.path
                        backend.update_experiment(
                            run_id,
                            {"run_dir": str(new_dir), "path": restored_path or "default"},
                        )
                except Exception:
                    pass

    successful_restores = sum(1 for r in results.values() if r["success"])
    return {
        "restored_count": successful_restores,
        "results": results,
        "message": f"Restored {successful_restores} of {len(run_ids)} runs",
    }


@router.post("/recycle-bin/empty")
async def empty_recycle_bin(request: Request, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    storage_root = request.app.state.storage_root
    confirm = payload.get("confirm", False)
    if not confirm:
        raise HTTPException(status_code=400, detail="Must set confirm=true to permanently delete")

    deleted_count = 0
    deleted_ids: list[str] = []
    for entry in iter_all_runs(storage_root, include_deleted=True):
        if is_run_deleted(entry.dir):
            try:
                run_id = entry.dir.name
                shutil.rmtree(entry.dir)
                deleted_count += 1
                deleted_ids.append(run_id)
                logger.info("Permanently deleted run: %s", run_id)
            except Exception as e:
                logger.error("Failed to permanently delete %s: %s", entry.dir.name, e)

    backend = get_backend(request)
    if backend is not None and deleted_ids:
        for run_id in deleted_ids:
            try:
                backend.delete_run_with_orphan_assets(run_id)
            except Exception as e:
                logger.debug("SQLite cleanup failed for %s: %s", run_id, e)

    return {
        "permanently_deleted": deleted_count,
        "message": f"Permanently deleted {deleted_count} runs",
    }
