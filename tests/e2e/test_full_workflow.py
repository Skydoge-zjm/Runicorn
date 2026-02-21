"""E2E: Full SDK workflow — init → log → finish → verify storage."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def isolated_env(tmp_path: Path, monkeypatch):
    """Isolate storage and config to tmp_path."""
    storage = tmp_path / "storage"
    storage.mkdir()
    monkeypatch.setenv("RUNICORN_DIR", str(storage))
    monkeypatch.setenv("RUNICORN_DISABLE_MODERN_STORAGE", "1")
    return storage


class TestFullWorkflow:
    """SDK init → log metrics → finish → verify files on disk."""

    def test_training_loop(self, isolated_env: Path):
        """Simulate a minimal training loop and verify artifacts."""
        import runicorn

        run = runicorn.init(
            path="test_proj/test_exp",
            storage=str(isolated_env),
        )
        assert run is not None
        assert run.id is not None

        # Log metrics like a training loop
        for step in range(5):
            run.log({"loss": 1.0 - step * 0.1, "acc": step * 0.2}, step=step)

        run.set_primary_metric("loss", mode="min")
        run.finish(status="completed")

        # Verify run directory exists with expected files
        run_dir = Path(run.run_dir)
        assert run_dir.exists()
        assert (run_dir / "meta.json").exists()

        meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
        assert "test_proj" in meta.get("path", "") or "test_proj" in meta.get("project", "")

        # Verify events.jsonl has metric entries
        events_path = run_dir / "events.jsonl"
        assert events_path.exists()
        lines = [l for l in events_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) >= 5

    def test_context_manager_auto_finish(self, isolated_env: Path):
        """Run as context manager auto-finishes."""
        import runicorn

        with runicorn.init(
            path="ctx_proj/ctx_exp",
            storage=str(isolated_env),
        ) as run:
            run.log({"val": 42})
            run_dir = Path(run.run_dir)

        # After exit, status should be written
        status_path = run_dir / "status.json"
        assert status_path.exists()
        status = json.loads(status_path.read_text(encoding="utf-8"))
        assert status["status"] in ("completed", "finished")

    def test_failed_run(self, isolated_env: Path):
        """Run that encounters error records failure status."""
        import runicorn

        run = runicorn.init(
            path="fail_proj/fail_exp",
            storage=str(isolated_env),
        )
        run.log({"loss": float("nan")})
        run.finish(status="failed")

        status_path = Path(run.run_dir) / "status.json"
        assert status_path.exists()
        status = json.loads(status_path.read_text(encoding="utf-8"))
        assert status["status"] == "failed"
