"""
Path Tree API Routes

Handles path hierarchy operations for the flexible path-based experiment structure.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Set

from fastapi import APIRouter, Request, Query, Body, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from ..api.runs import RunListItem
from ...storage.file_utils import (
    iter_all_runs, 
    read_json,
    update_status_if_process_dead,
    soft_delete_run,
    is_run_deleted,
)
from ..services.db_reader import get_backend, list_runs_from_db

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_path_tree(paths: List[str]) -> Dict[str, Any]:
    """
    Build a tree structure from a list of paths.
    
    Args:
        paths: List of path strings (e.g., ["cv/yolo", "cv/resnet", "nlp/bert"])
        
    Returns:
        Nested dict representing the tree structure
    """
    tree: Dict[str, Any] = {}
    
    for path in paths:
        if not path:
            continue
        parts = path.split("/")
        current = tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]
    
    return tree


def _scan_empty_dir_paths(runs_root: Path, prefix: str = "") -> Set[str]:
    """Recursively discover directory paths under runs/, including empty ones."""
    paths: Set[str] = set()
    if not runs_root.exists():
        return paths
    try:
        for item in sorted(runs_root.iterdir()):
            if not item.is_dir() or item.name == ".recycle":
                continue
            current_path = f"{prefix}/{item.name}" if prefix else item.name
            is_run = (item / "meta.json").exists() or (item / "status.json").exists()
            if not is_run:
                paths.add(current_path)
                paths.update(_scan_empty_dir_paths(item, current_path))
    except Exception:
        pass
    return paths


def _get_unique_paths(storage_root, backend=None) -> Set[str]:
    """Get all unique paths from runs + empty directories. Uses SQLite when available."""
    # Paths from runs
    run_paths: Set[str] = set()
    if backend is not None:
        try:
            result = backend.get_unique_paths()
            if result is not None:
                run_paths = set(result)
        except Exception:
            pass
    if not run_paths:
        for entry in iter_all_runs(storage_root):
            if entry.path:
                run_paths.add(entry.path)
            else:
                meta = read_json(entry.dir / "meta.json")
                path = meta.get("path") if isinstance(meta, dict) else None
                if path:
                    run_paths.add(str(path))

    # Also discover empty directories under runs/
    dir_paths = _scan_empty_dir_paths(storage_root / "runs")
    return run_paths | dir_paths


def _get_path_stats(storage_root, backend=None) -> Dict[str, Dict[str, int]]:
    """
    Get run statistics for each path and its ancestors.
    Uses SQLite when available.
    
    Returns:
        Dictionary mapping path to stats dict with total/running/finished/failed counts
    """
    if backend is not None:
        try:
            result = backend.get_path_stats()
            if result is not None:
                return result
        except Exception:
            pass
    
    # File-system fallback
    path_runs: Dict[str, Dict[str, int]] = {}
    
    for entry in iter_all_runs(storage_root):
        meta = read_json(entry.dir / "meta.json")
        run_path = entry.path or (meta.get("path") if isinstance(meta, dict) else None)
        
        if not run_path:
            continue
        
        status_data = read_json(entry.dir / "status.json")
        status = str((status_data.get("status") if isinstance(status_data, dict) else "finished") or "finished")
        
        if run_path not in path_runs:
            path_runs[run_path] = {"total": 0, "running": 0, "finished": 0, "failed": 0}
        
        path_runs[run_path]["total"] += 1
        if status == "running":
            path_runs[run_path]["running"] += 1
        elif status == "finished":
            path_runs[run_path]["finished"] += 1
        elif status == "failed":
            path_runs[run_path]["failed"] += 1
    
    # Aggregate stats for parent paths
    all_paths = set(path_runs.keys())
    for path in list(all_paths):
        parts = path.split("/")
        for i in range(1, len(parts)):
            ancestor = "/".join(parts[:i])
            if ancestor not in path_runs:
                path_runs[ancestor] = {"total": 0, "running": 0, "finished": 0, "failed": 0}
            path_runs[ancestor]["total"] += path_runs[path]["total"]
            path_runs[ancestor]["running"] += path_runs[path]["running"]
            path_runs[ancestor]["finished"] += path_runs[path]["finished"]
            path_runs[ancestor]["failed"] += path_runs[path]["failed"]
    
    return path_runs


@router.get("/paths")
async def list_paths(
    request: Request,
    include_stats: bool = Query(False, description="Include run statistics per path"),
) -> Dict[str, Any]:
    """
    List all unique experiment paths.
    
    Args:
        include_stats: If true, include run count statistics per path
    
    Returns:
        Dictionary with list of paths, tree structure, and optionally stats
    """
    storage_root = request.app.state.storage_root
    backend = get_backend(request)
    
    if include_stats:
        stats = _get_path_stats(storage_root, backend=backend)
        # Also include empty directories so newly-created folders are visible
        empty_dirs = _scan_empty_dir_paths(storage_root / "runs")
        for d in empty_dirs:
            if d not in stats:
                stats[d] = {"total": 0, "running": 0, "finished": 0, "failed": 0}
        paths = sorted(set(stats.keys()))
        return {
            "paths": paths,
            "tree": _build_path_tree(paths),
            "stats": stats,
        }
    else:
        paths = _get_unique_paths(storage_root, backend=backend)
        return {
            "paths": sorted(paths),
            "tree": _build_path_tree(sorted(paths)),
        }


@router.get("/paths/tree")
async def get_path_tree(request: Request) -> Dict[str, Any]:
    """
    Get the path tree structure.
    
    Returns:
        Nested tree structure of all paths
    """
    storage_root = request.app.state.storage_root
    backend = get_backend(request)
    paths = _get_unique_paths(storage_root, backend=backend)
    
    return {"tree": _build_path_tree(sorted(paths))}


@router.get("/paths/runs")
async def list_runs_by_path(
    request: Request,
    path: str = Query(None, description="Path prefix to filter by"),
    exact: bool = Query(False, description="If true, match exact path only"),
) -> List[RunListItem]:
    """
    List runs filtered by path.
    
    Args:
        path: Path prefix to filter by (e.g., "cv/yolo")
        exact: If true, only return runs with exact path match
        
    Returns:
        List of runs matching the path filter
    """
    storage_root = request.app.state.storage_root
    backend = get_backend(request)
    
    # --- SQLite fast-path ---
    if backend is not None:
        db_rows = list_runs_from_db(backend)
        if db_rows is not None:
            items: List[RunListItem] = []
            for r in db_rows:
                run_path = r.get("path")
                if path:
                    if exact:
                        if run_path != path:
                            continue
                    else:
                        if not run_path or (run_path != path and not run_path.startswith(f"{path}/")):
                            continue
                items.append(RunListItem(**r))
            return items
    
    # --- File-system fallback ---
    items = []
    
    for entry in iter_all_runs(storage_root):
        meta = read_json(entry.dir / "meta.json")
        run_path = entry.path or (meta.get("path") if isinstance(meta, dict) else None)
        alias = meta.get("alias") if isinstance(meta, dict) else None
        
        if path:
            if exact:
                if run_path != path:
                    continue
            else:
                if not run_path or (run_path != path and not run_path.startswith(f"{path}/")):
                    continue
        
        run_dir = entry.dir
        run_id = run_dir.name
        
        update_status_if_process_dead(run_dir)
        
        status = read_json(run_dir / "status.json")
        summary = read_json(run_dir / "summary.json")
        
        created = meta.get("created_at") if isinstance(meta, dict) else None
        if not isinstance(created, (int, float)):
            try:
                created = run_dir.stat().st_mtime
            except Exception:
                created = None
        
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
                path=run_path,
                alias=alias,
            )
        )
    
    return items


_SAFE_PATH_RE = re.compile(r'^[a-zA-Z0-9_/\-. ]+$')


@router.post("/paths/create")
async def create_path(request: Request, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Create an empty path (folder) in the storage tree.

    Args:
        payload: { path: string } — the path to create

    Returns:
        { ok, path }
    """
    storage_root = request.app.state.storage_root
    target = str(payload.get("path", "")).strip().strip("/")

    if not target:
        raise HTTPException(status_code=400, detail="path is required")
    if ".." in target:
        raise HTTPException(status_code=400, detail="path must not contain '..'")
    if not _SAFE_PATH_RE.match(target):
        raise HTTPException(status_code=400, detail="path contains invalid characters")

    dir_path = storage_root / "runs" / target
    if dir_path.exists():
        raise HTTPException(status_code=409, detail="Path already exists")

    try:
        dir_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create path: {e}")

    return {"ok": True, "path": target}


# Legacy compatibility endpoints (redirect to new path-based API)

@router.get("/projects")
async def list_projects(request: Request) -> Dict[str, List[str]]:
    """
    List all top-level path segments (legacy compatibility).
    
    Returns:
        Dictionary with list of top-level path segments as "projects"
    """
    storage_root = request.app.state.storage_root
    backend = get_backend(request)
    paths = _get_unique_paths(storage_root, backend=backend)
    
    projects: Set[str] = set()
    for path in paths:
        if path:
            first_segment = path.split("/")[0]
            projects.add(first_segment)
    
    return {"projects": sorted(projects)}


@router.get("/projects/{project}/names")
async def list_names(project: str, request: Request) -> Dict[str, List[str]]:
    """
    List second-level path segments for a given first segment (legacy compatibility).
    
    Args:
        project: First path segment
        
    Returns:
        Dictionary with list of second-level segments as "names"
    """
    storage_root = request.app.state.storage_root
    backend = get_backend(request)
    paths = _get_unique_paths(storage_root, backend=backend)
    
    names: Set[str] = set()
    for path in paths:
        if path and path.startswith(f"{project}/"):
            parts = path.split("/")
            if len(parts) >= 2:
                names.add(parts[1])
    
    return {"names": sorted(names)}


@router.get("/projects/{project}/names/{name}/runs")
async def list_runs_by_name(
    project: str,
    name: str,
    request: Request,
) -> List[Dict[str, Any]]:
    """
    List runs for a given project/name combination (legacy compatibility).
    
    This maps to paths starting with "{project}/{name}".
    
    Args:
        project: First path segment
        name: Second path segment
        
    Returns:
        List of runs matching the path prefix
    """
    storage_root = request.app.state.storage_root
    backend = get_backend(request)
    path_prefix = f"{project}/{name}"
    
    # --- SQLite fast-path ---
    if backend is not None:
        db_rows = list_runs_from_db(backend)
        if db_rows is not None:
            items: List[Dict[str, Any]] = []
            for r in db_rows:
                run_path = r.get("path")
                if not run_path:
                    continue
                if run_path != path_prefix and not run_path.startswith(f"{path_prefix}/"):
                    continue
                items.append({
                    "run_id": r["id"],
                    "path": run_path,
                    "alias": r.get("alias"),
                    "status": r.get("status", "finished"),
                    "start_time": r.get("created_time"),
                })
            return items
    
    # --- File-system fallback ---
    items = []
    
    for entry in iter_all_runs(storage_root):
        meta = read_json(entry.dir / "meta.json")
        run_path = entry.path or (meta.get("path") if isinstance(meta, dict) else None)
        
        if not run_path:
            continue
        if run_path != path_prefix and not run_path.startswith(f"{path_prefix}/"):
            continue
        
        run_dir = entry.dir
        run_id = run_dir.name
        
        status = read_json(run_dir / "status.json")
        
        created = meta.get("created_at") if isinstance(meta, dict) else None
        if not isinstance(created, (int, float)):
            try:
                created = run_dir.stat().st_mtime
            except Exception:
                created = None
        
        items.append({
            "run_id": run_id,
            "path": run_path,
            "alias": meta.get("alias") if isinstance(meta, dict) else None,
            "status": str((status.get("status") if isinstance(status, dict) else "finished") or "finished"),
            "start_time": created,
        })
    
    return items


# -------------------- Batch Operations by Path --------------------

@router.post("/paths/soft-delete")
async def soft_delete_by_path(
    request: Request,
    payload: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """
    Delete a path folder.

    1. Soft-delete every run under the path (mark + DB).
    2. Move each run directory to ``runs/.recycle/<run_id>/``.
    3. Remove the original folder tree from disk.
    """
    storage_root = request.app.state.storage_root
    path = payload.get("path")
    exact = payload.get("exact", False)

    if not path or not isinstance(path, str):
        raise HTTPException(status_code=400, detail="path is required")

    backend = get_backend(request)

    deleted_count = 0
    errors: List[str] = []

    # include_deleted=True keeps backward compatibility with legacy in-place
    # deleted runs that may still exist outside .recycle.
    for entry in iter_all_runs(storage_root, include_deleted=True):
        meta = read_json(entry.dir / "meta.json")
        run_path = entry.path or (meta.get("path") if isinstance(meta, dict) else None)
        # Already in recycle => already deleted, nothing to do.
        if ".recycle" in entry.dir.parts:
            continue

        if not run_path:
            continue
        if exact:
            if run_path != path:
                continue
        else:
            if run_path != path and not run_path.startswith(f"{path}/"):
                continue

        try:
            was_deleted = is_run_deleted(entry.dir)
            success, error, new_dir = soft_delete_run(
                entry.dir,
                storage_root=storage_root,
                reason="path_batch_delete",
                original_path=run_path,
            )
            if not success:
                errors.append(f"Failed to delete {entry.dir.name}: {error or 'unknown'}")
                continue

            if not was_deleted:
                deleted_count += 1
                if backend is not None:
                    try:
                        backend.soft_delete_experiments(
                            [entry.dir.name], reason="path_batch_delete",
                        )
                    except Exception:
                        pass

            if backend is not None and new_dir is not None:
                try:
                    backend.update_experiment(entry.dir.name, {
                        "run_dir": str(new_dir),
                        "path": run_path or "default",
                    })
                except Exception:
                    pass
        except Exception as e:
            errors.append(f"Error deleting {entry.dir.name}: {e}")

    # Remove the now-empty folder tree from disk
    target_dir = storage_root / "runs" / path
    if target_dir.exists():
        try:
            shutil.rmtree(target_dir)
        except Exception as e:
            errors.append(f"Failed to remove folder: {e}")

    return {
        "path": path,
        "deleted_count": deleted_count,
        "errors": errors if errors else None,
    }


@router.get("/paths/export")
async def export_by_path(
    request: Request,
    path: str = Query(..., description="Path prefix to export"),
    exact: bool = Query(False, description="If true, only match exact path"),
    format: str = Query("json", description="Export format: json or zip"),
) -> Any:
    """
    Export all runs under a path.
    
    Args:
        path: Path prefix to match
        exact: If true, only match exact path
        format: Export format (json for metadata, zip for full data)
        
    Returns:
        JSON data or ZIP file download
    """
    storage_root = request.app.state.storage_root
    
    if not path:
        raise HTTPException(status_code=400, detail="path is required")
    
    runs_data: List[Dict[str, Any]] = []
    run_dirs: List[Path] = []
    
    for entry in iter_all_runs(storage_root):
        meta = read_json(entry.dir / "meta.json")
        run_path = entry.path or (meta.get("path") if isinstance(meta, dict) else None)
        
        # Check path match
        if not run_path:
            continue
        if exact:
            if run_path != path:
                continue
        else:
            if run_path != path and not run_path.startswith(f"{path}/"):
                continue
        
        run_dir = entry.dir
        run_id = run_dir.name
        run_dirs.append(run_dir)
        
        # Load metadata
        status = read_json(run_dir / "status.json")
        summary = read_json(run_dir / "summary.json")
        
        created = meta.get("created_at") if isinstance(meta, dict) else None
        if not isinstance(created, (int, float)):
            try:
                created = run_dir.stat().st_mtime
            except Exception:
                created = None
        
        runs_data.append({
            "run_id": run_id,
            "path": run_path,
            "alias": meta.get("alias") if isinstance(meta, dict) else None,
            "status": str((status.get("status") if isinstance(status, dict) else "finished") or "finished"),
            "created_time": created,
            "summary": summary if isinstance(summary, dict) else {},
            "meta": meta if isinstance(meta, dict) else {},
        })
    
    if format == "json":
        return {
            "path": path,
            "exact": exact,
            "total_runs": len(runs_data),
            "runs": runs_data,
        }
    
    elif format == "zip":
        if not run_dirs:
            raise HTTPException(status_code=404, detail="No runs found for this path")
        
        # Create temp zip file
        tmp_fd, tmp_path = tempfile.mkstemp(prefix="runicorn_export_", suffix=".zip")
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
                # Add metadata index
                zf.writestr("index.json", json.dumps({
                    "path": path,
                    "total_runs": len(runs_data),
                    "runs": runs_data,
                }, indent=2, ensure_ascii=False))
                
                # Add run directories
                for run_dir in run_dirs:
                    run_id = run_dir.name
                    for dirpath, _, filenames in os.walk(run_dir):
                        dp = Path(dirpath)
                        for fn in filenames:
                            fp = dp / fn
                            try:
                                rel = fp.relative_to(run_dir).as_posix()
                                arcname = f"{run_id}/{rel}"
                            except Exception:
                                arcname = f"{run_id}/{fn}"
                            zf.write(str(fp), arcname=arcname)
        except Exception as e:
            _cleanup()
            raise HTTPException(status_code=500, detail=f"Failed to create zip: {e}")
        
        # Sanitize path for filename
        safe_path = path.replace("/", "_").replace("\\", "_")
        filename = f"runicorn_export_{safe_path}.zip"
        
        return FileResponse(
            path=str(tmp_zip),
            filename=filename,
            media_type="application/zip",
            background=BackgroundTask(_cleanup),
        )
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
