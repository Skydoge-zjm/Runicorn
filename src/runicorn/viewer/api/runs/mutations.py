from __future__ import annotations

import json
import shutil
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

from ....security.path_validation import validate_path as validate_relative_path
from ....storage.file_utils import find_run_dir_by_id, read_json
from ..storage_utils import get_storage_root
from ...services.db_reader import get_backend
from ...utils.validation import validate_batch_size, validate_run_id
from .models import MoveRunsPayload, RunUpdatePayload
from .shared import logger

router = APIRouter()


@router.patch("/runs/{run_id}")
async def update_run(run_id: str, request: Request, payload: RunUpdatePayload) -> Dict[str, Any]:
    storage_root = get_storage_root(request)
    if not validate_run_id(run_id):
        raise HTTPException(status_code=400, detail=f"Invalid run_id format: {run_id}")

    entry = find_run_dir_by_id(storage_root, run_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")

    run_dir = entry.dir
    meta_path = run_dir / "meta.json"
    meta = read_json(meta_path)
    if not isinstance(meta, dict):
        meta = {}

    if payload.alias is not None:
        alias_value = payload.alias.strip() if payload.alias else None
        meta["alias"] = alias_value if alias_value else None
    if payload.tags is not None:
        tags_value = [t.strip() for t in payload.tags if t and t.strip()]
        meta["tags"] = tags_value if tags_value else []

    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("Failed to update meta.json for %s: %s", run_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to update run: {e}")

    backend = get_backend(request)
    if backend is not None:
        try:
            if payload.alias is not None:
                backend.update_experiment(run_id, {"alias": meta.get("alias")})
            if payload.tags is not None:
                backend.set_tags(run_id, meta.get("tags", []))
        except Exception as e:
            logger.debug("SQLite dual-write failed for update_run %s: %s", run_id, e)

    return {"ok": True, "alias": meta.get("alias"), "tags": meta.get("tags", [])}


@router.post("/runs/move")
async def move_runs(request: Request, payload: MoveRunsPayload) -> Dict[str, Any]:
    storage_root = get_storage_root(request)
    target_path = payload.target_path.strip().strip("/")
    runs_root = storage_root / "runs"

    if not target_path:
        raise HTTPException(status_code=400, detail="target_path is required")
    valid_target, target_dir, target_error = validate_relative_path(target_path, runs_root)
    if not valid_target or target_dir is None:
        raise HTTPException(status_code=400, detail=target_error or "target_path is invalid")
    if not payload.run_ids:
        raise HTTPException(status_code=400, detail="run_ids is required")
    if not validate_batch_size(len(payload.run_ids), max_size=100):
        raise HTTPException(status_code=400, detail="Cannot move more than 100 runs at once")

    backend = get_backend(request)
    moved: List[Dict[str, str]] = []
    failed: List[Dict[str, str]] = []
    for run_id in payload.run_ids:
        if not validate_run_id(run_id):
            failed.append({"run_id": run_id, "error": "invalid run_id format"})
            continue

        entry = find_run_dir_by_id(storage_root, run_id)
        if not entry:
            failed.append({"run_id": run_id, "error": "run not found"})
            continue

        old_dir = entry.dir
        old_path = entry.path or "default"
        new_dir = target_dir / run_id
        if old_dir == new_dir:
            moved.append({"run_id": run_id, "old_path": old_path, "new_path": target_path})
            continue
        if new_dir.exists():
            failed.append({"run_id": run_id, "error": "target directory already exists"})
            continue

        try:
            new_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_dir), str(new_dir))

            meta_path = new_dir / "meta.json"
            meta = read_json(meta_path)
            if isinstance(meta, dict):
                meta["path"] = target_path
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2, ensure_ascii=False)

            if backend is not None:
                try:
                    backend.update_experiment(run_id, {"path": target_path, "run_dir": str(new_dir)})
                except Exception as e:
                    logger.debug("DB update failed for moved run %s: %s", run_id, e)

            moved.append({"run_id": run_id, "old_path": old_path, "new_path": target_path})
            logger.info("Moved run %s: %s -> %s", run_id, old_path, target_path)
        except Exception as e:
            logger.error("Failed to move run %s: %s", run_id, e)
            failed.append({"run_id": run_id, "error": str(e)})

    return {
        "ok": True,
        "moved_count": len(moved),
        "failed_count": len(failed),
        "moved": moved,
        "failed": failed,
    }
