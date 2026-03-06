"""
Database Reader — Viewer-specific SQLite helper layer.

Provides high-level helpers that sit between the Viewer API routes and the
low-level ``SQLiteStorageBackend``.  Every function gracefully degrades to
``None`` / empty-list when the backend is unavailable so that routes can
fall back to the legacy file-system scan.
"""
from __future__ import annotations

import json
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


def _pick_fingerprint(fp: Any) -> Optional[str]:
    """Convert fingerprint from assets.json (str, number, or dict) to string."""
    if fp is None:
        return None
    if isinstance(fp, str):
        return fp
    if isinstance(fp, (int, float)):
        return str(fp)
    if isinstance(fp, dict):
        return json.dumps(fp, ensure_ascii=False, sort_keys=True)
    return None


def _sync_assets_from_json(
    run_id: str,
    run_dir: Path,
    backend: "SQLiteStorageBackend",
    created_at: float,
) -> int:
    """
    Sync assets from assets.json into SQLite (assets + run_assets).
    Only runs when the run has no existing run_assets (file-only/imported runs).
    Returns the number of assets synced.
    """
    try:
        existing = backend.get_assets_for_run(run_id)
        if existing:
            return 0  # Already has assets from SDK; skip to avoid duplicates
    except Exception:
        return 0

    assets_path = run_dir / "assets.json"
    if not assets_path.exists():
        return 0

    assets = read_json(assets_path)
    if not isinstance(assets, dict):
        return 0

    count = 0

    # code.snapshot
    code = assets.get("code")
    if isinstance(code, dict):
        snap = code.get("snapshot")
        if isinstance(snap, dict):
            fp = _pick_fingerprint(snap.get("fingerprint"))
            try:
                backend.record_asset_for_run(
                    run_id=run_id,
                    role="code",
                    asset_type="code_snapshot",
                    name="code_snapshot.zip",
                    source_uri=snap.get("workspace_root"),
                    archive_uri=snap.get("archive_path"),
                    is_archived=bool(snap.get("saved")),
                    fingerprint_kind=snap.get("fingerprint_kind"),
                    fingerprint=fp,
                    created_at=float(snap.get("created_at") or created_at),
                    metadata={"format": snap.get("format", "zip")},
                )
                count += 1
            except Exception as exc:
                logger.debug("Failed to sync code snapshot for %s: %s", run_id, exc)

    # config
    cfg = assets.get("config")
    if isinstance(cfg, dict) and len(cfg) > 0:
        fp = _pick_fingerprint(cfg.get("fingerprint"))
        if not fp:
            fp = json.dumps(cfg, ensure_ascii=False, sort_keys=True)
        try:
            backend.record_asset_for_run(
                run_id=run_id,
                role="config",
                asset_type="config",
                name=None,
                source_uri=None,
                archive_uri=None,
                is_archived=False,
                fingerprint_kind=cfg.get("fingerprint_kind"),
                fingerprint=fp,
                created_at=created_at,
                metadata=cfg,
            )
            count += 1
        except Exception as exc:
            logger.debug("Failed to sync config for %s: %s", run_id, exc)

    # datasets
    datasets = assets.get("datasets")
    if isinstance(datasets, list):
        for i, d in enumerate(datasets):
            if not isinstance(d, dict):
                continue
            name = d.get("name") or f"dataset_{i}"
            fp = _pick_fingerprint(d.get("fingerprint"))
            try:
                backend.record_asset_for_run(
                    run_id=run_id,
                    role="dataset",
                    asset_type="dataset",
                    name=str(name),
                    source_uri=d.get("uri"),
                    archive_uri=d.get("archive_path"),
                    is_archived=bool(d.get("saved")),
                    fingerprint_kind=d.get("fingerprint_kind"),
                    fingerprint=fp,
                    created_at=created_at,
                    metadata={"context": d.get("context"), "description": d.get("description")},
                )
                count += 1
            except Exception as exc:
                logger.debug("Failed to sync dataset %s for %s: %s", name, run_id, exc)

    # pretrained
    pretrained = assets.get("pretrained")
    if isinstance(pretrained, list):
        for i, p in enumerate(pretrained):
            if not isinstance(p, dict):
                continue
            name = p.get("name") or f"pretrained_{i}"
            path_or_uri = p.get("path_or_uri")
            source_uri = str(path_or_uri) if path_or_uri is not None else None
            try:
                backend.record_asset_for_run(
                    run_id=run_id,
                    role="pretrained",
                    asset_type="pretrained",
                    name=str(name),
                    source_uri=source_uri,
                    archive_uri=p.get("archive_path"),
                    is_archived=bool(p.get("saved")),
                    fingerprint_kind=p.get("fingerprint_kind"),
                    fingerprint=_pick_fingerprint(p.get("fingerprint")),
                    created_at=created_at,
                    metadata={"source_type": p.get("source_type"), "description": p.get("description")},
                )
                count += 1
            except Exception as exc:
                logger.debug("Failed to sync pretrained %s for %s: %s", name, run_id, exc)

    # outputs
    outputs = assets.get("outputs")
    if isinstance(outputs, list):
        for i, e in enumerate(outputs):
            if not isinstance(e, dict):
                continue
            name = e.get("name") or e.get("key") or f"output_{i}"
            try:
                backend.record_asset_for_run(
                    run_id=run_id,
                    role="output",
                    asset_type="output",
                    name=str(name),
                    source_uri=e.get("path"),
                    archive_uri=e.get("archive_path"),
                    is_archived=True,
                    fingerprint_kind=e.get("fingerprint_kind"),
                    fingerprint=_pick_fingerprint(e.get("fingerprint")),
                    created_at=created_at,
                    metadata={"key": e.get("key"), "kind": e.get("kind")},
                )
                count += 1
            except Exception as exc:
                logger.debug("Failed to sync output %s for %s: %s", name, run_id, exc)

    return count


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

            # Extract time fields from status.json
            started_at = (status_data.get("started_at") if isinstance(status_data, dict) else None)
            ended_at = (status_data.get("ended_at") if isinstance(status_data, dict) else None)
            duration_seconds = None
            if isinstance(started_at, (int, float)) and isinstance(ended_at, (int, float)):
                duration_seconds = ended_at - started_at

            exp = ExperimentRecord(
                id=run_id,
                path=run_path,
                alias=(meta.get("alias") if isinstance(meta, dict) else None),
                created_at=float(created_at),
                updated_at=float(created_at),
                started_at=started_at if isinstance(started_at, (int, float)) else None,
                ended_at=ended_at if isinstance(ended_at, (int, float)) else None,
                duration_seconds=duration_seconds,
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
                # create_experiment does not persist deleted_at; apply via
                # soft_delete_experiments so the DB record mirrors the disk state.
                if exp.deleted_at is not None:
                    try:
                        backend.soft_delete_experiments(
                            [run_id], reason=exp.delete_reason or "synced_deleted",
                        )
                    except Exception:
                        pass
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

        # Sync assets from assets.json → assets + run_assets (for file-only/imported runs)
        created_at = meta.get("created_at") if isinstance(meta, dict) else None
        if not isinstance(created_at, (int, float)):
            try:
                created_at = entry.dir.stat().st_mtime
            except Exception:
                created_at = time.time()
        try:
            synced = _sync_assets_from_json(
                run_id, entry.dir, backend, float(created_at)
            )
            if synced:
                logger.debug("Synced %d assets for run %s from assets.json", synced, run_id)
        except Exception as exc:
            logger.debug("Failed to sync assets for %s: %s", run_id, exc)

    if inserted:
        logger.info("Synced %d filesystem runs into SQLite", inserted)
    return inserted
