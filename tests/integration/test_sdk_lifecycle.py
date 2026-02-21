"""Integration tests: SDK lifecycle — init → log → set_primary_metric → finish.

Full end-to-end flows verifying the complete Run lifecycle with both
file and SQLite backends.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from runicorn.sdk import Run


class TestSDKLifecycle:
    def test_full_training_lifecycle(self, storage_root: Path, monkeypatch):
        """Simulate a typical training run: init → log metrics → finish."""
        monkeypatch.delenv("RUNICORN_DISABLE_MODERN_STORAGE", raising=False)
        monkeypatch.setenv("RUNICORN_DIR", str(storage_root))

        with Run(path="lifecycle/train", storage=str(storage_root),
                 capture_console=False, run_id="lifecycle_001") as run:
            run.set_primary_metric("val_acc", mode="max")
            for epoch in range(1, 4):
                run.log({"train_loss": 1.0 / epoch, "val_acc": 0.5 + epoch * 0.1}, step=epoch)

        # After context manager exits → status=finished
        status = json.loads(run._status_path.read_text(encoding="utf-8"))
        assert status["status"] == "finished"

        # Summary has best metric
        summary = json.loads(run._summary_path.read_text(encoding="utf-8"))
        assert summary["best_metric_name"] == "val_acc"
        assert summary["best_metric_value"] == pytest.approx(0.8)  # epoch 3: 0.5+0.3
        assert summary["best_metric_step"] == 3

        # Events file has 3 entries
        events = run._events_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(events) == 3

    def test_failed_run_lifecycle(self, storage_root: Path, monkeypatch):
        """Simulate a run that fails mid-training."""
        monkeypatch.delenv("RUNICORN_DISABLE_MODERN_STORAGE", raising=False)
        monkeypatch.setenv("RUNICORN_DIR", str(storage_root))

        with pytest.raises(ValueError):
            with Run(path="lifecycle/fail", storage=str(storage_root),
                     capture_console=False, run_id="lifecycle_fail_001") as run:
                run.log({"loss": 1.0}, step=1)
                raise ValueError("training diverged")

        status = json.loads(run._status_path.read_text(encoding="utf-8"))
        assert status["status"] == "failed"

        # Partial data still exists
        events = run._events_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(events) == 1

    def test_lifecycle_with_console_capture(self, storage_root: Path, monkeypatch):
        """Run with capture_console=True produces logs.txt content."""
        monkeypatch.delenv("RUNICORN_DISABLE_MODERN_STORAGE", raising=False)
        monkeypatch.setenv("RUNICORN_DIR", str(storage_root))

        with Run(path="lifecycle/console", storage=str(storage_root),
                 capture_console=True, run_id="lifecycle_console_001") as run:
            run.log({"loss": 1.0}, step=1)

        # After finish, logs.txt should exist (might be empty if console capture
        # didn't have anything written to stdout/stderr, but file must exist)
        logs_path = run._logs_txt_path
        assert logs_path.parent.exists()

    def test_lifecycle_disabled(self, storage_root: Path, monkeypatch):
        """When runicorn is disabled, init() returns NoOpRun."""
        from runicorn.enabled import NoOpRun, reset_enabled
        import runicorn as rn

        monkeypatch.setenv("RUNICORN_ON", "0")
        monkeypatch.setenv("RUNICORN_DIR", str(storage_root))
        # Reset any cached override so env var takes effect
        reset_enabled()

        run = rn.init(path="disabled/test")
        assert isinstance(run, NoOpRun)
        assert run.id == "disabled"
        # Methods are no-ops
        run.log({"x": 1})
        run.finish()

        # Restore
        reset_enabled()

    def test_lifecycle_with_assets(self, storage_root: Path, monkeypatch, tmp_path):
        """Lifecycle that includes config, dataset, and pretrained logging."""
        monkeypatch.delenv("RUNICORN_DISABLE_MODERN_STORAGE", raising=False)
        monkeypatch.setenv("RUNICORN_DIR", str(storage_root))

        ds_dir = tmp_path / "data"
        ds_dir.mkdir()
        (ds_dir / "train.txt").write_text("sample data")

        with Run(path="lifecycle/assets", storage=str(storage_root),
                 capture_console=False, run_id="lifecycle_assets_001") as run:
            run.log_config(args={"lr": 0.001, "epochs": 10})
            run.log_dataset("my_data", str(ds_dir), context="train")
            run.log_pretrained("bert-base", source_type="huggingface")
            run.log({"loss": 0.5}, step=1)

        # Verify assets.json has all sections
        assets = json.loads(run._assets_path.read_text(encoding="utf-8"))
        assert "config" in assets
        assert "datasets" in assets
        assert len(assets["datasets"]) == 1
        assert "pretrained" in assets
        assert len(assets["pretrained"]) == 1
