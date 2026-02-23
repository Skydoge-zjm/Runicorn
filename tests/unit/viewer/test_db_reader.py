"""Tests for runicorn.viewer.services.db_reader — Viewer-specific SQLite helpers."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from runicorn.storage.models import ExperimentRecord
from runicorn.viewer.services.db_reader import (
    get_backend,
    find_run_entry_fast,
    list_runs_from_db,
    sync_filesystem_to_db,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_request(backend=None, storage_root=None):
    """Create a mock FastAPI Request with app.state."""
    req = MagicMock()
    req.app.state.storage_backend = backend
    req.app.state.storage_root = storage_root
    return req


def _populate_run(storage_root: Path, run_id: str, path: str = "train/cifar10",
                  status: str = "finished", tags: list | None = None) -> Path:
    """Create a run directory with meta.json, status.json on disk."""
    run_dir = storage_root / "runs" / path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    meta = {"id": run_id, "path": path, "created_at": time.time(),
            "hostname": "testhost", "pid": None}
    if tags:
        meta["tags"] = tags
    (run_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (run_dir / "status.json").write_text(
        json.dumps({"status": status, "started_at": time.time()}), encoding="utf-8")
    return run_dir


# ---------------------------------------------------------------------------
# get_backend
# ---------------------------------------------------------------------------

class TestGetBackend:
    def test_get_backend_present(self, sqlite_backend):
        req = _mock_request(backend=sqlite_backend)
        assert get_backend(req) is sqlite_backend

    def test_get_backend_absent(self):
        req = _mock_request(backend=None)
        assert get_backend(req) is None


# ---------------------------------------------------------------------------
# list_runs_from_db
# ---------------------------------------------------------------------------

class TestListRunsFromDb:
    def test_list_runs_from_db(self, populated_db):
        """Returns list of dicts with expected keys."""
        items = list_runs_from_db(populated_db)
        assert items is not None
        assert len(items) >= 1
        first = items[0]
        assert "id" in first
        assert "status" in first
        assert "tags" in first  # parsed from tags_csv
        assert isinstance(first["tags"], list)

    def test_list_runs_from_db_empty(self, sqlite_backend):
        """Empty DB returns None (triggers fallback)."""
        result = list_runs_from_db(sqlite_backend)
        assert result is None

    def test_list_runs_from_db_error_returns_none(self):
        """Exception from backend → None."""
        mock_backend = MagicMock()
        mock_backend.list_experiments_for_viewer.side_effect = RuntimeError("db error")
        assert list_runs_from_db(mock_backend) is None


# ---------------------------------------------------------------------------
# find_run_entry_fast
# ---------------------------------------------------------------------------

class TestFindRunEntryFast:
    def test_find_run_entry_fast_sqlite_miss_fallback(self, storage_root, sqlite_backend):
        """When SQLite has no record, falls back to file-system scan."""
        # Run exists on disk but NOT in SQLite
        _populate_run(storage_root, "run_miss_001", path="eval/resnet")

        req = _mock_request(backend=sqlite_backend, storage_root=storage_root)
        entry = find_run_entry_fast(req, "run_miss_001")
        assert entry is not None
        assert entry.dir.name == "run_miss_001"

    def test_find_run_entry_fast_sqlite_hit(self, storage_root, sqlite_backend):
        """SQLite has the record → returns RunEntry without file scan."""
        run_dir = _populate_run(storage_root, "run_fast_001")
        exp = ExperimentRecord(
            id="run_fast_001", path="train/cifar10",
            created_at=time.time(), updated_at=time.time(),
            status="finished", run_dir=str(run_dir),
        )
        sqlite_backend.create_experiment(exp)

        req = _mock_request(backend=sqlite_backend, storage_root=storage_root)
        entry = find_run_entry_fast(req, "run_fast_001")
        assert entry is not None
        assert entry.dir == run_dir

    def test_find_run_entry_fast_deleted_excluded(self, storage_root, sqlite_backend):
        """Soft-deleted run is excluded by default."""
        run_dir = _populate_run(storage_root, "run_del_001")
        exp = ExperimentRecord(
            id="run_del_001", path="train/cifar10",
            created_at=time.time(), updated_at=time.time(),
            status="finished", run_dir=str(run_dir),
        )
        sqlite_backend.create_experiment(exp)
        # deleted_at must be set via soft_delete (create_experiment ignores it)
        sqlite_backend.soft_delete_experiments(["run_del_001"])

        req = _mock_request(backend=sqlite_backend, storage_root=storage_root)
        assert find_run_entry_fast(req, "run_del_001") is None

    def test_find_run_entry_fast_deleted_included(self, storage_root, sqlite_backend):
        """include_deleted=True returns soft-deleted run."""
        run_dir = _populate_run(storage_root, "run_del_002")
        exp = ExperimentRecord(
            id="run_del_002", path="train/cifar10",
            created_at=time.time(), updated_at=time.time(),
            status="finished", run_dir=str(run_dir),
        )
        sqlite_backend.create_experiment(exp)
        sqlite_backend.soft_delete_experiments(["run_del_002"])

        req = _mock_request(backend=sqlite_backend, storage_root=storage_root)
        entry = find_run_entry_fast(req, "run_del_002", include_deleted=True)
        assert entry is not None


# ---------------------------------------------------------------------------
# sync_filesystem_to_db
# ---------------------------------------------------------------------------

class TestSyncFilesystemToDb:
    def test_sync_preserves_deleted_state(self, storage_root, sqlite_backend):
        """Soft-deleted runs synced from disk have deleted_at set in SQLite."""
        from runicorn.storage.file_utils import soft_delete_run, write_json

        run_dir = _populate_run(storage_root, "sync_del_001")
        write_json(run_dir / "status.json", {"status": "finished"})
        soft_delete_run(run_dir, storage_root=storage_root, reason="test")

        inserted = sync_filesystem_to_db(storage_root, sqlite_backend)
        assert inserted == 1

        exp = sqlite_backend.get_experiment("sync_del_001")
        assert exp is not None
        assert exp.deleted_at is not None

    def test_sync_inserts_missing_runs(self, storage_root, sqlite_backend):
        """Runs on disk but not in DB are inserted."""
        _populate_run(storage_root, "sync_001")
        _populate_run(storage_root, "sync_002", path="eval/imagenet")

        inserted = sync_filesystem_to_db(storage_root, sqlite_backend)
        assert inserted == 2

        # Verify they are now in DB
        assert sqlite_backend.experiment_exists("sync_001")
        assert sqlite_backend.experiment_exists("sync_002")

    def test_sync_idempotent(self, storage_root, sqlite_backend):
        """Running sync twice does not duplicate records."""
        _populate_run(storage_root, "sync_idem_001")

        first = sync_filesystem_to_db(storage_root, sqlite_backend)
        assert first == 1
        second = sync_filesystem_to_db(storage_root, sqlite_backend)
        assert second == 0

    def test_sync_tags_from_meta(self, storage_root, sqlite_backend):
        """Tags in meta.json are synced to experiment_tags table."""
        _populate_run(storage_root, "sync_tags_001", tags=["best", "production"])
        sync_filesystem_to_db(storage_root, sqlite_backend)

        tags = sqlite_backend.get_tags("sync_tags_001")
        assert set(tags) == {"best", "production"}
