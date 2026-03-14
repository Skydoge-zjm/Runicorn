"""Unit tests for runicorn.log_compat.tensorboard."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runicorn.log_compat.tensorboard import SummaryWriter


class _ScalarLike:
    def __init__(self, value):
        self._value = value

    def item(self):
        return self._value


class TestSummaryWriter:
    def test_explicit_log_dir_and_get_logdir(self, tmp_path: Path):
        log_dir = tmp_path / "tb_logs"
        writer = SummaryWriter(log_dir=str(log_dir))

        assert writer.get_logdir() == str(log_dir)
        assert log_dir.exists()

    def test_default_log_dir_uses_runs_prefix(self):
        writer = SummaryWriter(comment="_demo")
        try:
            assert writer.log_dir.startswith("runs")
            assert writer.log_dir.endswith("_demo")
        finally:
            writer.close()

    def test_add_scalar_forwards_to_active_run(self, tmp_path: Path):
        writer = SummaryWriter(log_dir=str(tmp_path / "tb"))
        mock_run = MagicMock()

        with patch("runicorn.sdk.get_active_run", return_value=mock_run):
            writer.add_scalar("train/loss", 0.25, 7)

        mock_run.log.assert_called_once_with({"train/loss": 0.25}, step=7)

    def test_add_scalar_accepts_scalar_like_values(self, tmp_path: Path):
        writer = SummaryWriter(log_dir=str(tmp_path / "tb"))
        mock_run = MagicMock()

        with patch("runicorn.sdk.get_active_run", return_value=mock_run):
            writer.add_scalar("acc", _ScalarLike(91.5), _ScalarLike(3))

        mock_run.log.assert_called_once_with({"acc": 91.5}, step=3)

    def test_add_scalars_joins_main_tag_and_subtags(self, tmp_path: Path):
        writer = SummaryWriter(log_dir=str(tmp_path / "tb"))
        mock_run = MagicMock()

        with patch("runicorn.sdk.get_active_run", return_value=mock_run):
            writer.add_scalars("train", {"loss": 0.2, "acc": 0.9}, 10)

        mock_run.log.assert_called_once_with(
            {"train/loss": 0.2, "train/acc": 0.9},
            step=10,
        )

    def test_no_active_run_is_allowed(self, tmp_path: Path):
        writer = SummaryWriter(log_dir=str(tmp_path / "tb"))

        with patch("runicorn.sdk.get_active_run", return_value=None):
            writer.add_scalar("train/loss", 0.1, 1)
            writer.add_scalars("train", {"acc": 0.8}, 1)
            writer.add_text("notes", "hello", 1)
            writer.add_hparams({"lr": 0.001}, {"metric": 0.9}, global_step=1)

    def test_add_text_forwards_to_run_log_text(self, tmp_path: Path):
        writer = SummaryWriter(log_dir=str(tmp_path / "tb"))
        mock_run = MagicMock()

        with patch("runicorn.sdk.get_active_run", return_value=mock_run):
            writer.add_text("notes", "hello world", 5)

        mock_run.log_text.assert_called_once_with("[notes] hello world")

    def test_add_hparams_records_config_metrics_and_summary(self, tmp_path: Path):
        writer = SummaryWriter(log_dir=str(tmp_path / "tb"))
        mock_run = MagicMock()

        with patch("runicorn.sdk.get_active_run", return_value=mock_run):
            writer.add_hparams(
                {"lr": 0.001, "batch_size": 32},
                {"hparam/accuracy": 0.95, "hparam/loss": 0.1},
                global_step=10,
            )

        mock_run.log_config.assert_called_once_with(
            extra={"hparams": {"lr": 0.001, "batch_size": 32}}
        )
        mock_run.log.assert_called_once_with(
            {"hparam/accuracy": 0.95, "hparam/loss": 0.1},
            step=10,
        )
        mock_run.summary.assert_called_once_with(
            {"hparam/accuracy": 0.95, "hparam/loss": 0.1}
        )

    def test_invalid_scalar_raises_type_error(self, tmp_path: Path):
        writer = SummaryWriter(log_dir=str(tmp_path / "tb"))

        with pytest.raises(TypeError):
            writer.add_scalar("bad", "oops", 1)

    def test_invalid_scalars_payload_raises_type_error(self, tmp_path: Path):
        writer = SummaryWriter(log_dir=str(tmp_path / "tb"))

        with pytest.raises(TypeError):
            writer.add_scalars("train", ["not", "mapping"], 1)

        with pytest.raises(TypeError):
            writer.add_scalars("train", {"loss": "oops"}, 1)

        with pytest.raises(TypeError):
            writer.add_text("notes", 123, 1)

        with pytest.raises(TypeError):
            writer.add_hparams([], {})

        with pytest.raises(TypeError):
            writer.add_hparams({}, [])

        with pytest.raises(TypeError):
            writer.add_hparams({}, {"metric": "bad"})

    def test_close_is_idempotent_and_add_after_close_reopens(self, tmp_path: Path):
        writer = SummaryWriter(log_dir=str(tmp_path / "tb"))
        mock_run = MagicMock()
        writer.close()
        writer.close()

        with patch("runicorn.sdk.get_active_run", return_value=mock_run):
            writer.add_scalar("loss", 0.4, 2)

        mock_run.log.assert_called_once_with({"loss": 0.4}, step=2)

    def test_context_manager_closes_cleanly(self, tmp_path: Path):
        with SummaryWriter(log_dir=str(tmp_path / "tb")) as writer:
            assert writer.get_logdir() == str(tmp_path / "tb")
