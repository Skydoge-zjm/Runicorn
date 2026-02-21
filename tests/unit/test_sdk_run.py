"""Tests for runicorn.sdk — _normalize_path, helpers, and Run class core."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, Any

import pytest

from runicorn.sdk import _normalize_path, _default_storage_dir, _gen_run_id, Run


# ===================================================================
# T2.2 — Pure function tests
# ===================================================================


class TestNormalizePath:
    def test_normalize_path_default(self):
        """None → 'default'."""
        assert _normalize_path(None) == "default"

    def test_normalize_path_strips_root(self):
        """'/' → '' (empty string for root-level runs)."""
        assert _normalize_path("/") == ""
        assert _normalize_path("") == ""

    def test_normalize_path_traversal_rejected(self):
        """Paths containing '..' are rejected.

        Note: '..' is caught by the character regex *before* the explicit '..' check,
        because '.' is not in the allowed charset.  Both code paths raise ValueError.
        """
        with pytest.raises(ValueError):
            _normalize_path("foo/../bar")
        # Pure '..' with only allowed chars around slashes
        with pytest.raises(ValueError):
            _normalize_path("a/b/../c")

    def test_normalize_path_invalid_chars_rejected(self):
        """Special characters raise ValueError."""
        with pytest.raises(ValueError, match="Invalid path"):
            _normalize_path("foo bar")
        with pytest.raises(ValueError, match="Invalid path"):
            _normalize_path("foo@bar")

    def test_normalize_path_max_length(self):
        """Paths longer than 200 chars are rejected."""
        with pytest.raises(ValueError, match="Path too long"):
            _normalize_path("a" * 201)

    def test_normalize_path_valid_hierarchy(self):
        """Normal hierarchical path is preserved."""
        assert _normalize_path("cv/detection/yolo") == "cv/detection/yolo"

    def test_normalize_path_backslash_converted(self):
        """Backslashes are converted to forward slashes."""
        assert _normalize_path("cv\\detection\\yolo") == "cv/detection/yolo"

    def test_normalize_path_strips_slashes(self):
        """Leading/trailing slashes are stripped."""
        assert _normalize_path("/cv/detection/") == "cv/detection"


class TestGenRunId:
    def test_gen_run_id_format(self):
        """Run ID has expected format: YYYYMMDD_HHMMSS_<hex6>."""
        rid = _gen_run_id()
        assert re.match(r"^\d{8}_\d{6}_[0-9a-f]{6}$", rid)

    def test_gen_run_id_unique(self):
        """Two consecutive IDs are different."""
        assert _gen_run_id() != _gen_run_id()


class TestDefaultStorageDir:
    def test_explicit_storage(self, tmp_path: Path):
        """Explicit storage argument takes priority."""
        result = _default_storage_dir(str(tmp_path))
        assert result == tmp_path.resolve()

    def test_env_variable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """RUNICORN_DIR env var is used when no explicit arg."""
        monkeypatch.setenv("RUNICORN_DIR", str(tmp_path))
        result = _default_storage_dir(None)
        assert result == tmp_path.resolve()

    def test_fallback_to_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """With nothing configured, falls back to ./.runicorn."""
        monkeypatch.delenv("RUNICORN_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        # Patch get_user_root_dir to return None (no user config)
        monkeypatch.setattr("runicorn.sdk.get_user_root_dir", lambda: None)
        result = _default_storage_dir(None)
        assert result == (tmp_path / ".runicorn").resolve()


# ===================================================================
# T2.3 — Run class core
# ===================================================================


def _make_run(storage_root: Path, monkeypatch: pytest.MonkeyPatch, **kwargs) -> Run:
    """Helper: create a Run with sane defaults for testing."""
    monkeypatch.delenv("RUNICORN_DISABLE_MODERN_STORAGE", raising=False)
    monkeypatch.setenv("RUNICORN_DIR", str(storage_root))
    defaults = dict(
        path="test/unit",
        storage=str(storage_root),
        capture_console=False,
        run_id="test_run_001",
    )
    defaults.update(kwargs)
    return Run(**defaults)


class TestRunInit:
    def test_run_creates_directory_structure(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """Run.__init__ creates run_dir with meta.json, status.json, assets.json."""
        run = _make_run(storage_root, monkeypatch)
        try:
            assert run.run_dir.exists()
            assert (run.run_dir / "meta.json").exists()
            assert (run.run_dir / "status.json").exists()
            assert (run.run_dir / "assets.json").exists()
            assert run.media_dir.exists()

            meta = json.loads((run.run_dir / "meta.json").read_text(encoding="utf-8"))
            assert meta["id"] == "test_run_001"
            assert meta["path"] == "test/unit"

            status = json.loads((run.run_dir / "status.json").read_text(encoding="utf-8"))
            assert status["status"] == "running"
        finally:
            run.finish()

    def test_run_init_with_alias(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """Alias is recorded in meta.json."""
        run = _make_run(storage_root, monkeypatch, alias="my-experiment", run_id="test_alias_001")
        try:
            meta = json.loads((run.run_dir / "meta.json").read_text(encoding="utf-8"))
            assert meta["alias"] == "my-experiment"
        finally:
            run.finish()


class TestRunLog:
    def test_run_log_writes_events_jsonl(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """run.log() appends a line to events.jsonl."""
        run = _make_run(storage_root, monkeypatch, run_id="test_log_001")
        try:
            run.log({"loss": 0.5}, step=1)
            events = run._events_path.read_text(encoding="utf-8").strip().splitlines()
            assert len(events) == 1
            evt = json.loads(events[0])
            assert evt["type"] == "metrics"
            assert evt["data"]["loss"] == 0.5
            assert evt["data"]["global_step"] == 1
        finally:
            run.finish()

    def test_run_log_auto_step_increment(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """Without explicit step, global_step auto-increments."""
        run = _make_run(storage_root, monkeypatch, run_id="test_autostep_001")
        try:
            run.log({"loss": 0.5})
            run.log({"loss": 0.4})
            run.log({"loss": 0.3})
            events = run._events_path.read_text(encoding="utf-8").strip().splitlines()
            steps = [json.loads(e)["data"]["global_step"] for e in events]
            assert steps == [1, 2, 3]
        finally:
            run.finish()

    def test_run_log_multiple_metrics(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """Single log call records multiple metrics."""
        run = _make_run(storage_root, monkeypatch, run_id="test_multi_001")
        try:
            run.log({"loss": 0.5, "acc": 0.9, "lr": 0.001}, step=1)
            events = run._events_path.read_text(encoding="utf-8").strip().splitlines()
            data = json.loads(events[0])["data"]
            assert data["loss"] == 0.5
            assert data["acc"] == 0.9
            assert data["lr"] == 0.001
        finally:
            run.finish()


class TestRunPrimaryMetric:
    def test_run_set_primary_metric(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """set_primary_metric stores internal state."""
        run = _make_run(storage_root, monkeypatch, run_id="test_primary_001")
        try:
            run.set_primary_metric("loss", mode="min")
            assert run._primary_metric_name == "loss"
            assert run._primary_metric_mode == "min"
        finally:
            run.finish()

    def test_run_set_primary_metric_invalid_mode(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """Invalid mode raises ValueError."""
        run = _make_run(storage_root, monkeypatch, run_id="test_invalid_mode_001")
        try:
            with pytest.raises(ValueError, match="Mode must be"):
                run.set_primary_metric("loss", mode="avg")
        finally:
            run.finish()

    def test_run_best_metric_tracking_max(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """mode='max' tracks the highest value."""
        run = _make_run(storage_root, monkeypatch, run_id="test_max_001")
        try:
            run.set_primary_metric("acc", mode="max")
            run.log({"acc": 0.8}, step=1)
            run.log({"acc": 0.9}, step=2)
            run.log({"acc": 0.85}, step=3)  # lower → not new best
            assert run._best_metric_value == 0.9
            assert run._best_metric_step == 2
        finally:
            run.finish()

    def test_run_best_metric_tracking_min(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """mode='min' tracks the lowest value."""
        run = _make_run(storage_root, monkeypatch, run_id="test_min_001")
        try:
            run.set_primary_metric("loss", mode="min")
            run.log({"loss": 0.5}, step=1)
            run.log({"loss": 0.3}, step=2)
            run.log({"loss": 0.4}, step=3)  # higher → not new best
            assert run._best_metric_value == 0.3
            assert run._best_metric_step == 2
        finally:
            run.finish()

    def test_best_metric_in_summary_after_finish(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """After finish(), summary.json contains best metric info."""
        run = _make_run(storage_root, monkeypatch, run_id="test_summary_best_001")
        run.set_primary_metric("acc", mode="max")
        run.log({"acc": 0.8}, step=1)
        run.log({"acc": 0.95}, step=2)
        run.finish()

        summary = json.loads(run._summary_path.read_text(encoding="utf-8"))
        assert summary["best_metric_name"] == "acc"
        assert summary["best_metric_value"] == 0.95
        assert summary["best_metric_step"] == 2
        assert summary["best_metric_mode"] == "max"


class TestRunFinish:
    def test_run_finish_writes_status(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """finish() sets status='finished' in status.json."""
        run = _make_run(storage_root, monkeypatch, run_id="test_finish_001")
        run.finish()
        status = json.loads(run._status_path.read_text(encoding="utf-8"))
        assert status["status"] == "finished"
        assert "ended_at" in status

    def test_run_finish_failed_status(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """finish(status='failed') writes 'failed'."""
        run = _make_run(storage_root, monkeypatch, run_id="test_failed_001")
        run.finish(status="failed")
        status = json.loads(run._status_path.read_text(encoding="utf-8"))
        assert status["status"] == "failed"

    def test_run_double_finish_idempotent(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """Calling finish() twice does not raise.

        Previously deadlocked because close() emptied the ConnectionPool but
        storage_backend was not set to None.  Fixed by adding
        ``self.storage_backend = None`` after close().
        """
        run = _make_run(storage_root, monkeypatch, run_id="test_double_001")
        assert run.storage_backend is not None, "Should test with modern storage enabled"
        run.finish()
        run.finish()  # should not raise or deadlock


class TestRunContextManager:
    def test_run_context_manager_success(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """Normal exit via `with` → status='finished'."""
        monkeypatch.delenv("RUNICORN_DISABLE_MODERN_STORAGE", raising=False)
        monkeypatch.setenv("RUNICORN_DIR", str(storage_root))
        with Run(path="test/ctx", storage=str(storage_root), capture_console=False,
                 run_id="test_ctx_ok_001") as run:
            run.log({"x": 1}, step=1)

        status = json.loads(run._status_path.read_text(encoding="utf-8"))
        assert status["status"] == "finished"

    def test_run_context_manager_exception(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """Exception inside `with` → status='failed'."""
        monkeypatch.delenv("RUNICORN_DISABLE_MODERN_STORAGE", raising=False)
        monkeypatch.setenv("RUNICORN_DIR", str(storage_root))
        with pytest.raises(RuntimeError):
            with Run(path="test/ctx", storage=str(storage_root), capture_console=False,
                     run_id="test_ctx_err_001") as run:
                raise RuntimeError("boom")

        status = json.loads(run._status_path.read_text(encoding="utf-8"))
        assert status["status"] == "failed"


class TestRunSummary:
    def test_run_summary_writes_file(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """summary() merges data into summary.json."""
        run = _make_run(storage_root, monkeypatch, run_id="test_summary_001")
        try:
            run.summary({"final_loss": 0.01, "epochs": 10})
            data = json.loads(run._summary_path.read_text(encoding="utf-8"))
            assert data["final_loss"] == 0.01
            assert data["epochs"] == 10

            # Second call merges, not overwrites
            run.summary({"final_acc": 0.99})
            data = json.loads(run._summary_path.read_text(encoding="utf-8"))
            assert data["final_loss"] == 0.01
            assert data["final_acc"] == 0.99
        finally:
            run.finish()


class TestRunSQLite:
    def test_run_sqlite_dual_write(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """When modern storage is enabled, log() writes to both JSONL and SQLite."""
        run = _make_run(storage_root, monkeypatch, run_id="test_dual_001")
        try:
            assert run.storage_backend is not None, "Modern storage should be initialized"

            run.log({"loss": 0.5, "acc": 0.8}, step=1)

            # Verify JSONL side
            events = run._events_path.read_text(encoding="utf-8").strip().splitlines()
            assert len(events) == 1

            # Verify SQLite side
            metrics = run.storage_backend.get_metrics(run.id)
            metric_names = {m.metric_name for m in metrics}
            assert "loss" in metric_names
            assert "acc" in metric_names
        finally:
            run.finish()

    def test_run_sqlite_disabled_via_env(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """RUNICORN_DISABLE_MODERN_STORAGE=1 → no SQLite backend."""
        monkeypatch.setenv("RUNICORN_DISABLE_MODERN_STORAGE", "1")
        monkeypatch.setenv("RUNICORN_DIR", str(storage_root))
        run = Run(
            path="test/no_sqlite",
            storage=str(storage_root),
            capture_console=False,
            run_id="test_nosql_001",
        )
        try:
            assert run.storage_backend is None

            # Should still work for file-only mode
            run.log({"loss": 0.5}, step=1)
            events = run._events_path.read_text(encoding="utf-8").strip().splitlines()
            assert len(events) == 1
        finally:
            run.finish()
