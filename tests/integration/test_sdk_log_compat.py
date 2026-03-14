"""Integration tests for Runicorn logging compatibility layers.

These tests verify that compat helpers write through the real Run lifecycle and
land in both file storage and SQLite, not just in isolated unit tests.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import runicorn as rn
from runicorn.log_compat.imagenet import AverageMeter, ProgressMeter, Summary
from runicorn.log_compat.tensorboard import SummaryWriter
from runicorn.log_compat.tensorboardX import SummaryWriter as TensorboardXSummaryWriter
from runicorn.log_compat.torchvision import MetricLogger


def _make_active_run(
    storage_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    run_id: str,
):
    monkeypatch.delenv("RUNICORN_DISABLE_MODERN_STORAGE", raising=False)
    monkeypatch.setenv("RUNICORN_DIR", str(storage_root))
    return rn.init(
        path="integ/log_compat",
        storage=str(storage_root),
        capture_console=False,
        run_id=run_id,
    )


def _read_events(run) -> list[dict]:
    return [
        json.loads(line)
        for line in run._events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class TestCompatIntegration:
    def test_torchvision_metric_logger_writes_events_and_sqlite(
        self,
        storage_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        run = _make_active_run(
            storage_root,
            monkeypatch,
            run_id="compat_tv_001",
        )
        try:
            assert run.storage_backend is not None

            logger = MetricLogger(delimiter="  ")
            logger.update(loss=0.5, acc=0.8)
            logger.update(loss=0.3, acc=0.9)

            events = _read_events(run)
            assert len(events) == 2
            assert events[0]["data"]["loss"] == 0.5
            assert events[0]["data"]["acc"] == 0.8
            assert events[1]["data"]["loss"] == 0.3
            assert events[1]["data"]["acc"] == 0.9

            metrics = run.storage_backend.get_metrics(run.id)
            assert len(metrics) == 4
            assert {m.metric_name for m in metrics} == {"loss", "acc"}
        finally:
            run.finish()

    def test_imagenet_progress_meter_writes_events_and_sqlite(
        self,
        storage_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        run = _make_active_run(
            storage_root,
            monkeypatch,
            run_id="compat_imagenet_001",
        )
        try:
            assert run.storage_backend is not None

            batch_time = AverageMeter("Time", False, ":6.3f", Summary.NONE)
            loss = AverageMeter("Loss", False, ":.4e", Summary.NONE)
            top1 = AverageMeter("Acc@1", False, ":6.2f", Summary.AVERAGE)
            progress = ProgressMeter(10, [batch_time, loss, top1], prefix="Train: ")

            batch_time.update(0.12)
            loss.update(1.5, 16)
            top1.update(72.5, 16)
            with patch("builtins.print"):
                progress.display(1)

            batch_time.update(0.09)
            loss.update(1.1, 16)
            top1.update(78.0, 16)
            with patch("builtins.print"):
                progress.display(2)

            events = _read_events(run)
            assert len(events) == 2
            assert events[0]["data"]["Time"] == 0.12
            assert events[0]["data"]["Loss"] == 1.5
            assert events[0]["data"]["Acc@1"] == 72.5
            assert events[1]["data"]["Time"] == 0.09
            assert events[1]["data"]["Loss"] == 1.1
            assert events[1]["data"]["Acc@1"] == 78.0

            metrics = run.storage_backend.get_metrics(run.id)
            assert len(metrics) == 6
            assert {m.metric_name for m in metrics} == {"Time", "Loss", "Acc@1"}
        finally:
            run.finish()

    def test_tensorboard_summary_writer_writes_events_and_sqlite(
        self,
        storage_root: Path,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        run = _make_active_run(
            storage_root,
            monkeypatch,
            run_id="compat_tb_001",
        )
        try:
            assert run.storage_backend is not None

            log_dir = tmp_path / "tb_logs"
            with SummaryWriter(log_dir=str(log_dir)) as writer:
                writer.add_scalar("train/loss", 0.25, 7)
                writer.add_scalars("train", {"acc": 0.91, "lr": 0.001}, 7)

            assert log_dir.exists()

            events = _read_events(run)
            assert len(events) == 2
            assert events[0]["data"]["train/loss"] == 0.25
            assert events[0]["data"]["global_step"] == 7
            assert events[1]["data"]["train/acc"] == 0.91
            assert events[1]["data"]["train/lr"] == 0.001
            assert events[1]["data"]["global_step"] == 7

            metrics = run.storage_backend.get_metrics(run.id)
            assert len(metrics) == 3
            assert {m.metric_name for m in metrics} == {
                "train/loss",
                "train/acc",
                "train/lr",
            }
        finally:
            run.finish()

    def test_tensorboardx_summary_writer_writes_metrics_text_and_hparams(
        self,
        storage_root: Path,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        run = _make_active_run(
            storage_root,
            monkeypatch,
            run_id="compat_tbx_001",
        )
        try:
            assert run.storage_backend is not None

            log_dir = tmp_path / "tbx_logs"
            with TensorboardXSummaryWriter(logdir=str(log_dir)) as writer:
                writer.add_scalar("train/loss", 0.2, 3, display_name="loss")
                writer.add_text("notes", "compat text")
                writer.add_hparams(
                    {"lr": 0.001, "batch_size": 16},
                    {"hparam/accuracy": 0.94, "hparam/loss": 0.08},
                    global_step=3,
                )

            assert log_dir.exists()

            events = _read_events(run)
            assert len(events) == 2
            assert events[0]["data"]["train/loss"] == 0.2
            assert events[0]["data"]["global_step"] == 3
            assert events[1]["data"]["hparam/accuracy"] == 0.94
            assert events[1]["data"]["hparam/loss"] == 0.08
            assert events[1]["data"]["global_step"] == 3

            logs_text = run._logs_txt_path.read_text(encoding="utf-8")
            assert "[notes] compat text" in logs_text

            assets = json.loads(run._assets_path.read_text(encoding="utf-8"))
            assert assets["config"]["extra"]["hparams"]["lr"] == 0.001
            assert assets["config"]["extra"]["hparams"]["batch_size"] == 16

            summary = json.loads(run._summary_path.read_text(encoding="utf-8"))
            assert summary["hparam/accuracy"] == 0.94
            assert summary["hparam/loss"] == 0.08

            metrics = run.storage_backend.get_metrics(run.id)
            assert {m.metric_name for m in metrics} == {
                "train/loss",
                "hparam/accuracy",
                "hparam/loss",
            }
        finally:
            run.finish()
