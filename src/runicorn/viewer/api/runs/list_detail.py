from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

from ....sdk import _normalize_status
from ....storage.file_utils import iter_all_runs, read_json, update_status_if_process_dead
from ..storage_utils import get_storage_root
from ...services.db_reader import find_run_entry_fast, get_backend, list_runs_from_db
from .models import RunListItem
from .shared import _count_assets_from_assets_json

router = APIRouter()


@router.get("/runs", response_model=List[RunListItem])
async def list_runs(request: Request) -> List[RunListItem]:
    backend = get_backend(request)
    if backend is not None:
        db_rows = list_runs_from_db(backend)
        if db_rows is not None:
            items: List[RunListItem] = []
            for r in db_rows:
                if r["status"] == "running" and r["run_dir"]:
                    run_dir = Path(r["run_dir"])
                    if run_dir.exists():
                        update_status_if_process_dead(run_dir)
                        status_data = read_json(run_dir / "status.json")
                        new_status = str(
                            (status_data.get("status") if isinstance(status_data, dict) else "running") or "running"
                        )
                        if new_status != "running":
                            r["status"] = _normalize_status(new_status)
                            try:
                                backend.update_experiment(r["id"], {"status": r["status"]})
                            except Exception:
                                pass
                items.append(RunListItem(**r))
            return items

    storage_root = get_storage_root(request)
    items = []
    for entry in iter_all_runs(storage_root):
        run_dir = entry.dir
        run_id = run_dir.name
        meta = read_json(run_dir / "meta.json")
        status = read_json(run_dir / "status.json")
        summary = read_json(run_dir / "summary.json")

        current_status = str((status.get("status") if isinstance(status, dict) else "finished") or "finished")
        if current_status == "running":
            update_status_if_process_dead(run_dir)
            status = read_json(run_dir / "status.json")

        created = meta.get("created_at") if isinstance(meta, dict) else None
        if not isinstance(created, (int, float)):
            try:
                created = run_dir.stat().st_mtime
            except Exception:
                created = None

        path = (meta.get("path") if isinstance(meta, dict) else None) or entry.project
        alias = meta.get("alias") if isinstance(meta, dict) else None
        tags = (meta.get("tags") if isinstance(meta, dict) else None) or []
        best_metric_value = summary.get("best_metric_value") if isinstance(summary, dict) else None
        best_metric_name = summary.get("best_metric_name") if isinstance(summary, dict) else None

        assets_count = 0
        assets_path = run_dir / "assets.json"
        if assets_path.exists():
            try:
                assets_data = read_json(assets_path)
                assets_count = _count_assets_from_assets_json(assets_data)
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
    entry = find_run_entry_fast(request, run_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")

    run_dir = entry.dir
    update_status_if_process_dead(run_dir)

    backend = get_backend(request)
    exp = None
    if backend is not None:
        try:
            exp = backend.get_experiment(run_id)
        except Exception:
            pass

    if exp is not None:
        status_val = exp.status or "finished"
        pid = exp.pid
        path = exp.path
        alias = exp.alias
        start_time = exp.started_at
        ended_at = exp.ended_at
        duration = exp.duration_seconds
    else:
        meta = read_json(run_dir / "meta.json")
        status_val = "finished"
        pid = meta.get("pid") if isinstance(meta, dict) else None
        path = (meta.get("path") if isinstance(meta, dict) else None) or entry.project
        alias = meta.get("alias") if isinstance(meta, dict) else None
        start_time = None
        ended_at = None
        duration = None

    if start_time is None or ended_at is None:
        status_data = read_json(run_dir / "status.json")
        if isinstance(status_data, dict):
            if exp is None:
                status_val = str(status_data.get("status") or "finished")
            if start_time is None:
                start_time = status_data.get("started_at")
            if ended_at is None:
                ended_at = status_data.get("ended_at")

    if duration is None and start_time is not None:
        if ended_at is not None:
            duration = ended_at - start_time
        elif status_val == "running":
            import time

            duration = time.time() - start_time

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

    summary: Any = {}
    summary_path = run_dir / "summary.json"
    if summary_path.exists():
        try:
            summary = read_json(summary_path)
            if not isinstance(summary, dict):
                summary = {}
        except Exception:
            summary = {}

    return {
        "id": run_id,
        "status": str(status_val),
        "pid": pid,
        "run_dir": str(run_dir),
        "path": path,
        "alias": alias,
        "start_time": start_time,
        "duration": duration,
        "logs": str(run_dir / "logs.txt"),
        "metrics": str(run_dir / "events.jsonl"),
        "metrics_step": str(run_dir / "events.jsonl"),
        "assets": assets,
        "assets_count": assets_count,
        "summary": summary,
    }
