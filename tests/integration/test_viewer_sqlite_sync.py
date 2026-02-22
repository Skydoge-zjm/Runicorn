"""Integration tests for filesystem → SQLite synchronisation."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List

from fastapi.testclient import TestClient

from runicorn.storage.backends import SQLiteStorageBackend
from runicorn.viewer.services.db_reader import sync_filesystem_to_db


def _create_run_on_disk_only(storage_root: Path, run_id: str, path: str) -> Path:
    """Create a run directory that is NOT registered in SQLite."""
    run_dir = storage_root / "runs" / path.replace("/", os.sep) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    now = time.time()
    (run_dir / "meta.json").write_text(
        json.dumps({"id": run_id, "path": path, "created_at": now, "tags": ["synced"]}),
        encoding="utf-8",
    )
    (run_dir / "status.json").write_text(
        json.dumps({"status": "finished"}), encoding="utf-8"
    )
    return run_dir


class TestSyncFilesystemToDb:

    def test_sync_inserts_new_runs(
        self,
        viewer_storage_root: Path,
        viewer_backend: SQLiteStorageBackend,
        populated_viewer_storage: List[str],
    ) -> None:
        # Create a run on disk that the DB doesn't know about
        new_id = "20250301_120000_eeeeee"
        _create_run_on_disk_only(viewer_storage_root, new_id, "sync/test")

        inserted = sync_filesystem_to_db(viewer_storage_root, viewer_backend)
        assert inserted >= 1

        # Verify it's now in SQLite
        exp = viewer_backend.get_experiment(new_id)
        assert exp is not None
        assert exp.path == "sync/test"

    def test_sync_idempotent(
        self,
        viewer_storage_root: Path,
        viewer_backend: SQLiteStorageBackend,
        populated_viewer_storage: List[str],
    ) -> None:
        # First sync should insert 0 (all 3 already registered)
        inserted = sync_filesystem_to_db(viewer_storage_root, viewer_backend)
        assert inserted == 0

    def test_sync_tags(
        self,
        viewer_storage_root: Path,
        viewer_backend: SQLiteStorageBackend,
        populated_viewer_storage: List[str],
    ) -> None:
        new_id = "20250302_120000_ffffff"
        _create_run_on_disk_only(viewer_storage_root, new_id, "sync/tags")
        sync_filesystem_to_db(viewer_storage_root, viewer_backend)

        tags = viewer_backend.get_tags(new_id)
        assert "synced" in tags


class TestFindRunEntryFastFallback:
    """When a run is on disk but not in SQLite, the viewer should
    still find it via the filesystem fallback."""

    def test_detail_endpoint_falls_back(
        self,
        viewer_client: TestClient,
        viewer_storage_root: Path,
        viewer_backend: SQLiteStorageBackend,
    ) -> None:
        # Create a run on disk only (no SQLite row)
        new_id = "20250401_120000_aabbcc"
        _create_run_on_disk_only(viewer_storage_root, new_id, "fallback/test")

        resp = viewer_client.get(f"/api/runs/{new_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == new_id


class TestSyncOnStartup:
    """Verify sync works when triggered manually (simulating startup)."""

    def test_sync_on_startup(
        self,
        viewer_storage_root: Path,
        viewer_backend: SQLiteStorageBackend,
    ) -> None:
        """Startup-equivalent sync picks up disk-only runs."""
        new_id = "20250501_120000_startup"
        _create_run_on_disk_only(viewer_storage_root, new_id, "startup/test")

        inserted = sync_filesystem_to_db(viewer_storage_root, viewer_backend)
        assert inserted >= 1
        assert viewer_backend.get_experiment(new_id) is not None


class TestSyncHandlesPartialData:

    def test_sync_with_missing_fields(
        self,
        viewer_storage_root: Path,
        viewer_backend: SQLiteStorageBackend,
    ) -> None:
        """meta.json missing optional fields should not crash sync."""
        run_id = "20250502_120000_partial"
        run_dir = viewer_storage_root / "runs" / "partial" / run_id
        run_dir.mkdir(parents=True)
        # Minimal meta: only id — no path, no created_at, no tags
        (run_dir / "meta.json").write_text(
            json.dumps({"id": run_id}), encoding="utf-8"
        )
        (run_dir / "status.json").write_text(
            json.dumps({"status": "running"}), encoding="utf-8"
        )

        # Should not raise
        inserted = sync_filesystem_to_db(viewer_storage_root, viewer_backend)
        assert inserted >= 1

        exp = viewer_backend.get_experiment(run_id)
        assert exp is not None
