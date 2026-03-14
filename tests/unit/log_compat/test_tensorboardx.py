"""Unit tests for runicorn.log_compat.tensorboardX."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runicorn.log_compat.tensorboardX import SummaryWriter


class _ScalarLike:
    def __init__(self, value):
        self._value = value

    def item(self):
        return self._value


class TestTensorboardXSummaryWriter:
    def test_logdir_argument_is_supported(self, tmp_path: Path):
        logdir = tmp_path / "tbx"
        writer = SummaryWriter(logdir=str(logdir))

        assert writer.logdir == str(logdir)
        assert writer.get_logdir() == str(logdir)
        assert logdir.exists()

    def test_log_dir_alias_is_supported(self, tmp_path: Path):
        logdir = tmp_path / "tbx_alias"
        writer = SummaryWriter(log_dir=str(logdir))

        assert writer.logdir == str(logdir)
        assert writer.get_logdir() == str(logdir)

    def test_add_scalar_accepts_tensorboardx_signature(self, tmp_path: Path):
        writer = SummaryWriter(logdir=str(tmp_path / "tbx"))
        mock_run = MagicMock()

        with patch("runicorn.sdk.get_active_run", return_value=mock_run):
            writer.add_scalar(
                "train/loss",
                _ScalarLike(0.25),
                _ScalarLike(8),
                display_name="loss curve",
                summary_description="training loss",
            )

        mock_run.log.assert_called_once_with({"train/loss": 0.25}, step=8)

    def test_add_text_forwards_to_run_logs(self, tmp_path: Path):
        writer = SummaryWriter(logdir=str(tmp_path / "tbx"))
        mock_run = MagicMock()

        with patch("runicorn.sdk.get_active_run", return_value=mock_run):
            writer.add_text("notes", "hello world", 5)

        mock_run.log_text.assert_called_once_with("[notes] hello world")

    def test_add_hparams_records_config_and_metrics(self, tmp_path: Path):
        writer = SummaryWriter(logdir=str(tmp_path / "tbx"))
        mock_run = MagicMock()

        with patch("runicorn.sdk.get_active_run", return_value=mock_run):
            writer.add_hparams(
                {"lr": 0.001, "batch_size": 32},
                {"hparam/accuracy": 0.95, "hparam/loss": 0.1},
                name="trial_1",
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

    def test_invalid_hparams_payload_raises(self, tmp_path: Path):
        writer = SummaryWriter(logdir=str(tmp_path / "tbx"))

        with pytest.raises(TypeError):
            writer.add_hparams([], {})

        with pytest.raises(TypeError):
            writer.add_hparams({}, [])

        with pytest.raises(TypeError):
            writer.add_hparams({}, {"metric": "bad"})
