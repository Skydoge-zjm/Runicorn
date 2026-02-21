"""Viewer-related fixtures shared across test layers.

Provides a FastAPI TestClient wired to a real SQLiteStorageBackend
and a temporary storage_root.  Background tasks (periodic_status_check,
sync_filesystem_to_db) are monkey-patched out so tests run deterministically.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from runicorn.storage.backends import SQLiteStorageBackend
from runicorn.storage.models import ExperimentRecord


# ---------------------------------------------------------------------------
# Helpers – populate storage with sample runs on the filesystem + SQLite
# ---------------------------------------------------------------------------

def _create_run_on_disk(
    storage_root: Path,
    run_id: str,
    path: str = "test/unit",
    status: str = "finished",
    metrics: Optional[List[Dict[str, Any]]] = None,
    tags: Optional[List[str]] = None,
    alias: Optional[str] = None,
) -> Path:
    """Create a minimal run directory with meta/status/events files."""
    run_dir = storage_root / "runs" / path.replace("/", os.sep) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    now = time.time()

    meta: Dict[str, Any] = {
        "id": run_id,
        "path": path,
        "alias": alias,
        "created_at": now,
        "python": "3.13",
        "platform": "Windows",
        "hostname": "test-host",
        "pid": 99999,
        "storage_dir": str(storage_root),
        "workspace_root": str(storage_root),
    }
    if tags:
        meta["tags"] = tags
    (run_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    status_data: Dict[str, Any] = {"status": status, "started_at": now}
    if status != "running":
        status_data["ended_at"] = now + 10
    (run_dir / "status.json").write_text(json.dumps(status_data), encoding="utf-8")

    (run_dir / "assets.json").write_text("{}", encoding="utf-8")

    if metrics:
        lines = []
        for i, m in enumerate(metrics, 1):
            row = {"type": "metrics", "timestamp": now + i, "data": {**m, "global_step": i}}
            lines.append(json.dumps(row))
        (run_dir / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return run_dir


def populate_storage(storage_root: Path, backend: SQLiteStorageBackend) -> List[str]:
    """Create 3 sample runs on disk and register them in SQLite.

    Returns the list of run IDs created.
    """
    runs: List[Dict[str, Any]] = [
        {"run_id": "20250101_120000_aaaaaa", "path": "cv/yolo", "status": "finished",
         "metrics": [{"loss": 0.5, "acc": 0.8}, {"loss": 0.3, "acc": 0.9}]},
        {"run_id": "20250102_120000_bbbbbb", "path": "cv/yolo", "status": "finished",
         "metrics": [{"loss": 0.7}], "tags": ["baseline"]},
        {"run_id": "20250103_120000_cccccc", "path": "nlp/bert", "status": "finished",
         "metrics": [{"loss": 0.2, "acc": 0.95}]},
    ]

    ids: List[str] = []
    for r in runs:
        run_dir = _create_run_on_disk(
            storage_root, r["run_id"], r.get("path", "default"),
            r.get("status", "finished"), r.get("metrics"), r.get("tags"), r.get("alias"),
        )
        now = time.time()
        exp = ExperimentRecord(
            id=r["run_id"],
            path=r.get("path", "default"),
            alias=r.get("alias"),
            created_at=now,
            updated_at=now,
            status=r.get("status", "finished"),
            pid=99999,
            run_dir=str(run_dir),
        )
        try:
            backend.create_experiment(exp)
        except Exception:
            pass
        tags = r.get("tags")
        if tags:
            backend.set_tags(r["run_id"], tags)
        ids.append(r["run_id"])
    return ids


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def viewer_storage_root(tmp_path: Path) -> Path:
    """Fresh temporary storage root for viewer tests."""
    root = tmp_path / "storage"
    (root / "runs").mkdir(parents=True)
    return root


@pytest.fixture()
def viewer_backend(viewer_storage_root: Path) -> Generator[SQLiteStorageBackend, None, None]:
    """SQLiteStorageBackend wired to *viewer_storage_root*."""
    backend = SQLiteStorageBackend(viewer_storage_root)
    yield backend
    backend.close()


@pytest.fixture()
def populated_viewer_storage(
    viewer_storage_root: Path,
    viewer_backend: SQLiteStorageBackend,
) -> List[str]:
    """Populate storage with 3 sample runs.  Returns list of run IDs."""
    return populate_storage(viewer_storage_root, viewer_backend)


@pytest.fixture()
def viewer_app(
    viewer_storage_root: Path,
    viewer_backend: SQLiteStorageBackend,
    monkeypatch: pytest.MonkeyPatch,
) -> FastAPI:
    """Create a FastAPI app with storage wired, background tasks disabled."""
    # Patch out periodic_status_check to avoid asyncio background task
    async def _noop_status_check(*a, **kw):  # noqa: ARG001
        import asyncio
        await asyncio.sleep(999999)  # will be cancelled immediately

    monkeypatch.setattr(
        "runicorn.viewer.periodic_status_check",
        _noop_status_check,
    )

    # Disable rate limiter so tests aren't throttled
    class _AlwaysAllowLimiter:
        def is_allowed(self, *a, **kw):  # noqa: ARG002
            return True, 0
        def get_limiter(self, *a, **kw):  # noqa: ARG002
            return type("L", (), {"max_requests": 9999, "get_usage": lambda self, *a, **kw: {"limit": 9999, "remaining": 9999, "reset_in": 0}})()
        def get_settings(self):  # noqa: ARG001
            return {"custom_headers": {}}

    monkeypatch.setattr(
        "runicorn.viewer.middleware.rate_limit.get_rate_limiter",
        lambda: _AlwaysAllowLimiter(),
    )

    from runicorn.viewer import create_app

    app = create_app(storage=str(viewer_storage_root))

    # Override storage_backend with the one from fixture (shared connection)
    app.state.storage_backend = viewer_backend

    return app


@pytest.fixture()
def viewer_client(viewer_app: FastAPI) -> Generator[TestClient, None, None]:
    """TestClient that triggers startup/shutdown events."""
    with TestClient(viewer_app, raise_server_exceptions=False) as client:
        yield client
