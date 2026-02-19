"""
Database Reader — Viewer-specific SQLite helper layer.

Provides high-level helpers that sit between the Viewer API routes and the
low-level ``SQLiteStorageBackend``.  Every function gracefully degrades to
``None`` / empty-list when the backend is unavailable so that routes can
fall back to the legacy file-system scan.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ...storage.file_utils import (
    RunEntry,
    iter_all_runs,
    find_run_dir_by_id,
    read_json,
    is_run_deleted,
)
from ...storage.models import ExperimentRecord

if TYPE_CHECKING:
    from fastapi import Request
    from ...storage.backends import SQLiteStorageBackend

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Accessor
# ---------------------------------------------------------------------------

def get_backend(request: "Request") -> Optional["SQLiteStorageBackend"]:
    """Return the ``SQLiteStorageBackend`` stored in *app.state*, or *None*."""
    return getattr(request.app.state, "storage_backend", None)


# ---------------------------------------------------------------------------
# Fast single-run lookup  (O(1) via SQLite index, fallback O(n) file scan)
# ---------------------------------------------------------------------------

def find_run_entry_fast(
    request: "Request",
    run_id: str,
    *,
    include_deleted: bool = False,
) -> Optional[RunEntry]:
    """Look up a run by ID — SQLite first, file-system fallback."""
    backend = get_backend(request)
    if backend is not None:
        try:
            exp = backend.get_experiment(run_id)
            if exp is not None:
                # Honour include_deleted flag
                if not include_deleted and exp.deleted_at is not None:
                    return None
                run_dir = Path(exp.run_dir)
                if run_dir.exists():
                    return RunEntry(path=exp.path, dir=run_dir)
        except Exception as exc:
            logger.debug("SQLite lookup failed for %s: %s", run_id, exc)

    # Fallback to file scan
    storage_root = request.app.state.storage_root
    return find_run_dir_by_id(storage_root, run_id, include_deleted=include_deleted)


# ---------------------------------------------------------------------------
# list_runs helper (returns dicts ready for RunListItem construction)
# ---------------------------------------------------------------------------

def list_runs_from_db(
    backend: "SQLiteStorageBackend",
) -> Optional[List[Dict[str, Any]]]:
    """
    Return the full run list from SQLite, or *None* on failure.

    Each dict contains the fields expected by ``RunListItem``:
    id, run_dir, created_time, status, pid, best_metric_value,
    best_metric_name, path, alias, tags (list), assets_count (int).
    """
    try:
        rows = backend.list_experiments_for_viewer(include_deleted=False)
    except Exception as exc:
        logger.warning("list_experiments_for_viewer failed: %s", exc)
        return None

    if not rows:
        return None  # empty DB → let caller fall back to files

    items: List[Dict[str, Any]] = []
    for r in rows:
        tags_csv = r.get("tags_csv")
        tags = tags_csv.split(",") if tags_csv else []
        items.append({
            "id": r["id"],
            "run_dir": r.get("run_dir", ""),
            "created_time": r.get("created_at"),
            "status": r.get("status") or "finished",
            "pid": r.get("pid"),
            "best_metric_value": r.get("best_metric_value"),
            "best_metric_name": r.get("best_metric_name"),
            "path": r.get("path"),
            "alias": r.get("alias"),
            "tags": tags,
            "assets_count": r.get("assets_count", 0),
        })
    return items


# ---------------------------------------------------------------------------
# Filesystem → SQLite synchronisation
# ---------------------------------------------------------------------------

def sync_filesystem_to_db(
    storage_root: Path,
    backend: "SQLiteStorageBackend",
) -> int:
    """
    Scan the file system and insert any runs that are missing from SQLite.

    Also syncs ``meta.json`` tags → ``experiment_tags`` table.

    Returns the number of newly inserted experiments.
    """
    inserted = 0

    for entry in iter_all_runs(storage_root, include_deleted=True):
        run_id = entry.dir.name
        try:
            exists = backend.experiment_exists(run_id)
        except Exception:
            continue

        meta = read_json(entry.dir / "meta.json")
        status_data = read_json(entry.dir / "status.json")
        summary = read_json(entry.dir / "summary.json")

        if not exists:
            # Build ExperimentRecord from files
            created_at = (meta.get("created_at") if isinstance(meta, dict) else None)
            if not isinstance(created_at, (int, float)):
                try:
                    created_at = entry.dir.stat().st_mtime
                except Exception:
                    created_at = time.time()

            status_val = "finished"
            if isinstance(status_data, dict):
                status_val = status_data.get("status") or "finished"

            run_path = (meta.get("path") if isinstance(meta, dict) else None) or entry.path or "default"

            exp = ExperimentRecord(
                id=run_id,
                path=run_path,
                alias=(meta.get("alias") if isinstance(meta, dict) else None),
                created_at=float(created_at),
                updated_at=float(created_at),
                status=str(status_val),
                pid=(meta.get("pid") if isinstance(meta, dict) else None),
                python_version=(meta.get("python_version") if isinstance(meta, dict) else None),
                platform=(meta.get("platform") if isinstance(meta, dict) else None),
                hostname=(meta.get("hostname") if isinstance(meta, dict) else None),
                run_dir=str(entry.dir),
                best_metric_name=(summary.get("best_metric_name") if isinstance(summary, dict) else None),
                best_metric_value=(summary.get("best_metric_value") if isinstance(summary, dict) else None),
                best_metric_step=(summary.get("best_metric_step") if isinstance(summary, dict) else None),
                best_metric_mode=(summary.get("best_metric_mode") if isinstance(summary, dict) else None),
            )

            # Honour soft-deleted state
            if is_run_deleted(entry.dir):
                deleted_info = read_json(entry.dir / ".deleted")
                exp.deleted_at = deleted_info.get("deleted_at", time.time())
                exp.delete_reason = deleted_info.get("reason", "unknown")

            try:
                backend.create_experiment(exp)
                inserted += 1
            except Exception as exc:
                logger.debug("Failed to sync run %s to SQLite: %s", run_id, exc)
                continue

        # Sync tags from meta.json → experiment_tags (always, cheap upsert)
        if isinstance(meta, dict):
            tags = meta.get("tags")
            if isinstance(tags, list) and tags:
                try:
                    backend.set_tags(run_id, [str(t) for t in tags if t])
                except Exception:
                    pass

    if inserted:
        logger.info("Synced %d filesystem runs into SQLite", inserted)
    return inserted
