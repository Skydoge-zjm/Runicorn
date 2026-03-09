"""Unit tests for runicorn.log_compat.imagenet."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from runicorn.log_compat.imagenet import AverageMeter, ProgressMeter, Summary


class _ScalarLike:
    def __init__(self, value: float):
        self._value = value

    def item(self) -> float:
        return self._value


class TestAverageMeter:
    def test_update_and_basic_properties_with_legacy_signature(self):
        meter = AverageMeter("Loss", ":.4e")
        meter.update(2.0, 2)
        meter.update(4.0, 1)

        assert meter.val == 4.0
        assert meter.sum == 8.0
        assert meter.count == 3
        assert meter.avg == pytest.approx(8.0 / 3.0)

    def test_update_accepts_scalar_like_item(self):
        meter = AverageMeter("Acc@1", False, ":6.2f", Summary.AVERAGE)
        meter.update(_ScalarLike(88.5), 2)

        assert meter.val == 88.5
        assert meter.avg == 88.5

    def test_current_official_signature_is_supported(self):
        meter = AverageMeter("Time", False, ":6.3f", Summary.NONE)

        assert meter.name == "Time"
        assert meter.use_accel is False
        assert meter.fmt == ":6.3f"
        assert meter.summary_type is Summary.NONE

    def test_str_output_matches_official_style(self):
        meter = AverageMeter("Loss", ":.2f")
        meter.update(1.23)

        text = str(meter)

        assert "Loss" in text
        assert "1.23" in text

    def test_summary_variants(self):
        meter = AverageMeter("Acc@1", ":.2f", Summary.AVERAGE)
        meter.update(90.0, 2)
        meter.update(80.0, 2)
        assert meter.summary() == "Acc@1 85.000"

        meter.summary_type = Summary.SUM
        assert meter.summary() == "Acc@1 340.000"

        meter.summary_type = Summary.COUNT
        assert meter.summary() == "Acc@1 4.000"

        meter.summary_type = Summary.NONE
        assert meter.summary() == ""

    def test_update_rejects_non_numeric_values(self):
        meter = AverageMeter("Loss")

        with pytest.raises(TypeError):
            meter.update("bad-value")


class TestProgressMeter:
    def test_display_prints_expected_output(self):
        batch_time = AverageMeter("Time", ":6.3f")
        loss = AverageMeter("Loss", ":.4e")
        batch_time.update(0.1)
        loss.update(1.23)
        progress = ProgressMeter(100, [batch_time, loss], prefix="Epoch: ")

        with patch("builtins.print") as mock_print:
            progress.display(5)

        printed = mock_print.call_args[0][0]
        assert "Epoch: " in printed
        assert "[  5/100]" in printed
        assert "Time" in printed
        assert "Loss" in printed

    def test_display_logs_batched_metrics_to_active_run(self):
        batch_time = AverageMeter("Time", ":6.3f")
        loss = AverageMeter("Loss", ":.4e")
        batch_time.update(0.25)
        loss.update(0.5)
        progress = ProgressMeter(10, [batch_time, loss], prefix="Train: ")
        mock_run = MagicMock()

        with patch("runicorn.sdk.get_active_run", return_value=mock_run):
            with patch("builtins.print"):
                progress.display(1)

        mock_run.log.assert_called_once_with({"Time": 0.25, "Loss": 0.5})

    def test_display_no_run_no_error(self):
        loss = AverageMeter("Loss", ":.4e")
        loss.update(0.5)
        progress = ProgressMeter(10, [loss], prefix="Train: ")

        with patch("runicorn.sdk.get_active_run", return_value=None):
            with patch("builtins.print"):
                progress.display(1)

    def test_display_summary_uses_meter_summary(self):
        top1 = AverageMeter("Acc@1", ":6.2f", Summary.AVERAGE)
        top5 = AverageMeter("Acc@5", ":6.2f", Summary.AVERAGE)
        top1.update(80.0, 2)
        top5.update(95.0, 2)
        progress = ProgressMeter(10, [top1, top5], prefix="Test: ")

        with patch("builtins.print") as mock_print:
            progress.display_summary()

        printed = mock_print.call_args[0][0]
        assert printed.startswith(" *")
        assert "Acc@1 80.000" in printed
        assert "Acc@5 95.000" in printed
