"""Integration tests: SDK Run → SQLite dual-write verification.

These tests create real Run instances and verify data lands in both
the file system (events.jsonl, meta.json, etc.) and SQLite.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from runicorn.sdk import Run


def _make_run(storage_root: Path, monkeypatch: pytest.MonkeyPatch, **kw) -> Run:
    monkeypatch.delenv("RUNICORN_DISABLE_MODERN_STORAGE", raising=False)
    monkeypatch.setenv("RUNICORN_DIR", str(storage_root))
    defaults = dict(path="integ/sdk", storage=str(storage_root),
                    capture_console=False, run_id="integ_001")
    defaults.update(kw)
    return Run(**defaults)


class TestSDKStorageDualWrite:
    def test_log_creates_jsonl_and_sqlite_metrics(self, storage_root: Path, monkeypatch):
        """log() writes to both events.jsonl and SQLite metrics table."""
        run = _make_run(storage_root, monkeypatch, run_id="dual_log_001")
        try:
            assert run.storage_backend is not None

            run.log({"loss": 0.5, "acc": 0.8}, step=1)
            run.log({"loss": 0.3, "acc": 0.9}, step=2)

            # File side
            events = run._events_path.read_text(encoding="utf-8").strip().splitlines()
            assert len(events) == 2

            # SQLite side
            metrics = run.storage_backend.get_metrics(run.id)
            assert len(metrics) == 4  # 2 metrics × 2 steps
            names = {m.metric_name for m in metrics}
            assert names == {"loss", "acc"}
        finally:
            run.finish()

    def test_experiment_record_created_in_sqlite(self, storage_root: Path, monkeypatch):
        """Run.__init__ creates an ExperimentRecord in SQLite."""
        run = _make_run(storage_root, monkeypatch, run_id="exp_rec_001")
        try:
            exp = run.storage_backend.get_experiment("exp_rec_001")
            assert exp is not None
            assert exp.path == "integ/sdk"
            assert exp.status == "running"
        finally:
            run.finish()

    def test_finish_updates_sqlite_status(self, storage_root: Path, monkeypatch):
        """finish() updates the experiment status in SQLite."""
        run = _make_run(storage_root, monkeypatch, run_id="finish_sql_001")
        run.finish()

        # Re-open a fresh backend to read (the run's backend is closed after finish)
        from runicorn.storage.backends import SQLiteStorageBackend
        backend = SQLiteStorageBackend(storage_root)
        try:
            exp = backend.get_experiment("finish_sql_001")
            assert exp is not None
            assert exp.status == "finished"
            assert exp.ended_at is not None
        finally:
            backend.close()

    def test_best_metric_persisted_to_sqlite(self, storage_root: Path, monkeypatch):
        """Primary metric tracking persists to SQLite via update_experiment."""
        run = _make_run(storage_root, monkeypatch, run_id="best_sql_001")
        run.set_primary_metric("acc", mode="max")
        run.log({"acc": 0.7}, step=1)
        run.log({"acc": 0.95}, step=2)

        # Check live before finish
        exp = run.storage_backend.get_experiment("best_sql_001")
        assert exp.best_metric_value == 0.95
        assert exp.best_metric_name == "acc"
        assert exp.best_metric_step == 2

        run.finish()

    def test_log_config_records_asset_in_sqlite(self, storage_root: Path, monkeypatch):
        """log_config() creates an asset record in SQLite."""
        run = _make_run(storage_root, monkeypatch, run_id="cfg_sql_001")
        try:
            run.log_config(args={"lr": 0.01})

            assets = run.storage_backend.get_assets_for_run("cfg_sql_001")
            assert len(assets) >= 1
            config_assets = [a for a in assets if a["asset_type"] == "config"]
            assert len(config_assets) == 1
        finally:
            run.finish()

    def test_run_tags_via_set_tags(self, storage_root: Path, monkeypatch):
        """Tags set via the backend's set_tags appear in SQLite."""
        run = _make_run(storage_root, monkeypatch, run_id="tags_001")
        try:
            assert run.storage_backend is not None
            run.storage_backend.set_tags("tags_001", ["fast", "v2"])
            tags = run.storage_backend.get_tags("tags_001")
            assert set(tags) == {"fast", "v2"}
        finally:
            run.finish()

    def test_log_dataset_records_asset_in_sqlite(self, storage_root: Path, monkeypatch, tmp_path):
        """log_dataset() creates a dataset asset record in SQLite."""
        ds_dir = tmp_path / "dataset"
        ds_dir.mkdir()
        (ds_dir / "data.csv").write_text("a,b\n1,2\n")

        run = _make_run(storage_root, monkeypatch, run_id="ds_sql_001")
        try:
            run.log_dataset("cifar10", str(ds_dir))

            assets = run.storage_backend.get_assets_for_run("ds_sql_001")
            ds_assets = [a for a in assets if a["asset_type"] == "dataset"]
            assert len(ds_assets) == 1
            assert ds_assets[0]["name"] == "cifar10"
        finally:
            run.finish()
