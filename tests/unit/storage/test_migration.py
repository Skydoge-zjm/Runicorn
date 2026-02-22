"""Tests for runicorn.storage.migration."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from runicorn.storage.models import ExperimentRecord, MetricRecord, QueryParams, MigrationStatus
from runicorn.storage.migration import (
    StorageMigrator,
    FilesToSQLiteFileReader,
    detect_storage_type,
    migrate_index_to_unified,
)
from runicorn.storage.file_utils import write_json


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_file_run(root: Path, path: str, run_id: str, *, status: str = "finished") -> Path:
    """Create a run directory in new layout with meta/status/events files."""
    run_dir = root / "runs" / path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    now = time.time()
    write_json(run_dir / "meta.json", {"id": run_id, "path": path, "created_at": now})
    write_json(run_dir / "status.json", {"status": status, "started_at": now})
    # events.jsonl with typed metrics
    events = [
        json.dumps({"type": "metrics", "ts": now, "data": {"loss": 0.5, "step": 1}}),
        json.dumps({"type": "metrics", "ts": now + 1, "data": {"loss": 0.3, "step": 2}}),
    ]
    (run_dir / "events.jsonl").write_text("\n".join(events) + "\n", encoding="utf-8")
    return run_dir


# ===========================================================================
# StorageMigrator (with mock backends)
# ===========================================================================

class TestStorageMigrator:

    def test_migrate_all_success(self) -> None:
        source = MagicMock()
        target = MagicMock()

        exp = ExperimentRecord(id="e1", path="p", run_dir="/r")
        source.list_experiments.return_value = [exp]
        source.get_metrics.return_value = [
            MetricRecord(experiment_id="e1", timestamp=1.0, metric_name="loss", metric_value=0.5)
        ]

        migrator = StorageMigrator(source, target)
        status = migrator.migrate_all()

        assert status.status == "completed"
        assert status.processed_items == 1
        target.create_experiment.assert_called_once_with(exp)
        target.log_metrics.assert_called_once()

    def test_migrate_records_failures(self) -> None:
        source = MagicMock()
        target = MagicMock()

        exp = ExperimentRecord(id="e1", path="p", run_dir="/r")
        source.list_experiments.return_value = [exp]
        source.get_metrics.return_value = []
        target.create_experiment.side_effect = RuntimeError("db error")

        migrator = StorageMigrator(source, target)
        status = migrator.migrate_all()

        assert status.status == "completed"  # overall completed, but has failures
        assert status.failed_items == 1
        assert len(status.errors) == 1


# ===========================================================================
# FilesToSQLiteFileReader
# ===========================================================================

class TestFilesToSQLiteFileReader:

    def test_list_experiments_from_files(self, tmp_path: Path) -> None:
        (tmp_path / "runs").mkdir()
        _make_file_run(tmp_path, "train/cifar", "run_001")
        _make_file_run(tmp_path, "eval", "run_002")

        reader = FilesToSQLiteFileReader(tmp_path)
        exps = reader.list_experiments(QueryParams(include_deleted=True))

        assert len(exps) == 2
        ids = {e.id for e in exps}
        assert ids == {"run_001", "run_002"}

    def test_get_metrics_from_events(self, tmp_path: Path) -> None:
        (tmp_path / "runs").mkdir()
        _make_file_run(tmp_path, "train", "run_m")

        reader = FilesToSQLiteFileReader(tmp_path)
        reader.list_experiments(QueryParams(include_deleted=True))
        metrics = reader.get_metrics("run_m")

        assert len(metrics) >= 1
        assert all(m.metric_name == "loss" for m in metrics)

    def test_stubs_raise(self, tmp_path: Path) -> None:
        reader = FilesToSQLiteFileReader(tmp_path)
        with pytest.raises(NotImplementedError):
            reader.create_experiment(ExperimentRecord(id="x", path="p", run_dir="r"))
        with pytest.raises(NotImplementedError):
            reader.log_metrics("x", [])


# ===========================================================================
# detect_storage_type
# ===========================================================================

class TestDetectStorageType:

    def test_empty(self, tmp_path: Path) -> None:
        assert detect_storage_type(tmp_path) == "empty"

    def test_sqlite_only(self, tmp_path: Path) -> None:
        (tmp_path / "runicorn.db").write_text("")
        (tmp_path / "runs").mkdir()  # empty runs
        assert detect_storage_type(tmp_path) == "sqlite_only"

    def test_file_only(self, tmp_path: Path) -> None:
        _make_file_run(tmp_path, "train", "run_fo")
        assert detect_storage_type(tmp_path) == "file_only"

    def test_hybrid(self, tmp_path: Path) -> None:
        (tmp_path / "runicorn.db").write_text("")
        # Create a legacy layout dir so detect_storage_type sees files
        proj = tmp_path / "proj" / "exp" / "runs" / "r1"
        proj.mkdir(parents=True)
        write_json(proj / "meta.json", {"id": "r1"})
        assert detect_storage_type(tmp_path) == "hybrid"


# ===========================================================================
# migrate_index_to_unified
# ===========================================================================

class TestMigrateIndexToUnified:

    def test_skips_when_no_index_db(self, sqlite_backend, storage_root: Path) -> None:
        assert migrate_index_to_unified(storage_root, sqlite_backend) is False

    def test_migrates_assets(self, sqlite_backend, storage_root: Path) -> None:
        # Create a legacy index DB with one asset
        import sqlite3

        index_dir = storage_root / "index"
        index_dir.mkdir()
        index_db = index_dir / "runicorn.db"
        conn = sqlite3.connect(str(index_db))
        conn.execute("CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, asset_type TEXT, name TEXT, source_uri TEXT, archive_uri TEXT, is_archived INTEGER, fingerprint_kind TEXT, fingerprint TEXT, size_bytes INTEGER, mtime REAL, created_at REAL, metadata_json TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS run_assets (run_id TEXT, asset_id TEXT, role TEXT, created_at REAL, PRIMARY KEY(run_id, asset_id, role))")
        conn.execute(
            "INSERT INTO assets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("a1", "model", "m", "/m", None, 0, "sha256", "fp1", 100, None, time.time(), None),
        )
        conn.commit()
        conn.close()

        result = migrate_index_to_unified(storage_root, sqlite_backend)
        assert result is True

        # Asset should now exist in unified DB
        asset = sqlite_backend.get_asset_by_fingerprint("model", "fp1")
        assert asset is not None

    def test_idempotent(self, sqlite_backend, storage_root: Path) -> None:
        import sqlite3

        index_dir = storage_root / "index"
        index_dir.mkdir()
        index_db = index_dir / "runicorn.db"
        conn = sqlite3.connect(str(index_db))
        conn.execute("CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, asset_type TEXT, name TEXT, source_uri TEXT, archive_uri TEXT, is_archived INTEGER, fingerprint_kind TEXT, fingerprint TEXT, size_bytes INTEGER, mtime REAL, created_at REAL, metadata_json TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS run_assets (run_id TEXT, asset_id TEXT, role TEXT, created_at REAL, PRIMARY KEY(run_id, asset_id, role))")
        conn.commit()
        conn.close()

        assert migrate_index_to_unified(storage_root, sqlite_backend) is True
        # Second call should be skipped
        assert migrate_index_to_unified(storage_root, sqlite_backend) is False
