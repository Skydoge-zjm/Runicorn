"""Unit tests for runicorn.log_compat.torchvision."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from runicorn.log_compat.torchvision import MetricLogger, SmoothedValue


class TestSmoothedValue:
    """SmoothedValue tracks windowed statistics."""

    def test_basic_properties(self):
        sv = SmoothedValue(window_size=5)
        sv.update(1.0)
        sv.update(2.0)
        sv.update(3.0)
        assert sv.value == 3.0
        assert sv.max == 3.0
        assert sv.avg == 2.0
        assert sv.global_avg == 2.0

    def test_median(self):
        sv = SmoothedValue(window_size=10)
        for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
            sv.update(v)
        assert sv.median == 3.0

    def test_empty_defaults(self):
        sv = SmoothedValue()
        assert sv.value == 0.0
        assert sv.avg == 0.0
        assert sv.global_avg == 0.0

    def test_str_format(self):
        sv = SmoothedValue(fmt="{value:.2f}")
        sv.update(3.14)
        assert str(sv) == "3.14"


class TestMetricLogger:
    """MetricLogger update and Runicorn integration."""

    def test_update_creates_meters(self):
        ml = MetricLogger()
        ml.update(loss=0.5, acc=0.9)
        assert ml.meters["loss"].value == 0.5
        assert ml.meters["acc"].value == 0.9

    def test_forwards_to_active_run(self):
        """If get_active_run() returns a run, update() calls run.log()."""
        mock_run = MagicMock()

        with patch("runicorn.log_compat.torchvision.get_active_run", return_value=mock_run, create=True):
            # We need to patch where it's imported inside the update() method
            with patch("runicorn.sdk.get_active_run", return_value=mock_run):
                ml = MetricLogger()
                ml.update(loss=0.42)

        mock_run.log.assert_called_once_with({"loss": 0.42})

    def test_no_run_no_error(self):
        """update() works fine even if no active Runicorn run exists."""
        with patch("runicorn.sdk.get_active_run", return_value=None):
            ml = MetricLogger()
            ml.update(loss=1.0)  # should not raise

    def test_log_every_yields_all_items(self):
        ml = MetricLogger()
        items = list(ml.log_every([10, 20, 30], print_freq=100, header="Test"))
        assert items == [10, 20, 30]

    def test_str_output(self):
        ml = MetricLogger(delimiter=" | ")
        ml.update(loss=0.5)
        s = str(ml)
        assert "loss" in s
