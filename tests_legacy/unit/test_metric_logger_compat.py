"""
Unit tests for MetricLogger compatibility layer.

Tests cover:
- SmoothedValue: median/avg/max calculations, pure Python fallback
- MetricLogger: update(), log_every(), run.log() integration
- Graceful behavior without active Run
- Distributed sync no-op without torch.distributed
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runicorn.log_compat.torchvision import SmoothedValue, MetricLogger


class TestSmoothedValueBasic:
    """Basic functionality tests for SmoothedValue."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        sv = SmoothedValue()
        assert sv.count == 0
        assert sv.total == 0.0
        assert len(sv.deque) == 0

    def test_custom_window_size(self) -> None:
        """Test custom window size."""
        sv = SmoothedValue(window_size=5)
        for i in range(10):
            sv.update(i)
        # Only last 5 values should be in deque
        assert len(sv.deque) == 5
        assert list(sv.deque) == [5, 6, 7, 8, 9]

    def test_custom_format(self) -> None:
        """Test custom format string."""
        sv = SmoothedValue(fmt="{value:.2f}")
        sv.update(3.14159)
        assert str(sv) == "3.14"


class TestSmoothedValueUpdate:
    """Tests for SmoothedValue.update()."""

    def test_update_single_value(self) -> None:
        """Test updating with a single value."""
        sv = SmoothedValue()
        sv.update(5.0)
        
        assert sv.count == 1
        assert sv.total == 5.0
        assert sv.value == 5.0

    def test_update_with_n(self) -> None:
        """Test updating with n parameter."""
        sv = SmoothedValue()
        sv.update(5.0, n=3)
        
        assert sv.count == 3
        assert sv.total == 15.0  # 5.0 * 3

    def test_update_multiple_values(self) -> None:
        """Test updating with multiple values."""
        sv = SmoothedValue()
        sv.update(1.0)
        sv.update(2.0)
        sv.update(3.0)
        
        assert sv.count == 3
        assert sv.total == 6.0


class TestSmoothedValueProperties:
    """Tests for SmoothedValue properties."""

    def test_median_odd_count(self) -> None:
        """Test median with odd number of values."""
        sv = SmoothedValue()
        sv.update(1.0)
        sv.update(2.0)
        sv.update(3.0)
        
        assert sv.median == 2.0

    def test_median_even_count(self) -> None:
        """Test median with even number of values."""
        sv = SmoothedValue()
        sv.update(1.0)
        sv.update(2.0)
        sv.update(3.0)
        sv.update(4.0)
        
        assert sv.median == 2.5

    def test_median_empty(self) -> None:
        """Test median with no values."""
        sv = SmoothedValue()
        assert sv.median == 0.0

    def test_avg(self) -> None:
        """Test average calculation."""
        sv = SmoothedValue()
        sv.update(1.0)
        sv.update(2.0)
        sv.update(3.0)
        
        assert sv.avg == 2.0

    def test_avg_empty(self) -> None:
        """Test average with no values."""
        sv = SmoothedValue()
        assert sv.avg == 0.0

    def test_global_avg(self) -> None:
        """Test global average calculation."""
        sv = SmoothedValue(window_size=2)
        sv.update(1.0)
        sv.update(2.0)
        sv.update(3.0)  # Window now has [2, 3]
        
        # Global avg should consider all values
        assert sv.global_avg == 2.0  # (1+2+3)/3

    def test_global_avg_empty(self) -> None:
        """Test global average with no values."""
        sv = SmoothedValue()
        assert sv.global_avg == 0.0

    def test_max(self) -> None:
        """Test max calculation."""
        sv = SmoothedValue()
        sv.update(1.0)
        sv.update(5.0)
        sv.update(3.0)
        
        assert sv.max == 5.0

    def test_max_empty(self) -> None:
        """Test max with no values."""
        sv = SmoothedValue()
        assert sv.max == 0.0

    def test_value(self) -> None:
        """Test most recent value."""
        sv = SmoothedValue()
        sv.update(1.0)
        sv.update(2.0)
        sv.update(3.0)
        
        assert sv.value == 3.0

    def test_value_empty(self) -> None:
        """Test value with no values."""
        sv = SmoothedValue()
        assert sv.value == 0.0


class TestSmoothedValueSync:
    """Tests for SmoothedValue.synchronize_between_processes()."""

    def test_sync_without_torch_is_noop(self) -> None:
        """Test that sync is no-op without torch."""
        sv = SmoothedValue()
        sv.update(5.0)
        
        # Should not raise
        sv.synchronize_between_processes()
        
        # Values should be unchanged
        assert sv.count == 1
        assert sv.total == 5.0


class TestMetricLoggerBasic:
    """Basic functionality tests for MetricLogger."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        ml = MetricLogger()
        assert ml.delimiter == "\t"
        assert len(ml.meters) == 0

    def test_custom_delimiter(self) -> None:
        """Test custom delimiter."""
        ml = MetricLogger(delimiter="  ")
        assert ml.delimiter == "  "


class TestMetricLoggerUpdate:
    """Tests for MetricLogger.update()."""

    def test_update_creates_meters(self) -> None:
        """Test that update creates meters for new keys."""
        ml = MetricLogger()
        ml.update(loss=0.5, acc=0.9)
        
        assert "loss" in ml.meters
        assert "acc" in ml.meters

    def test_update_updates_existing_meters(self) -> None:
        """Test that update updates existing meters."""
        ml = MetricLogger()
        ml.update(loss=0.5)
        ml.update(loss=0.3)
        
        assert ml.meters["loss"].count == 2

    def test_update_with_int(self) -> None:
        """Test update with integer values."""
        ml = MetricLogger()
        ml.update(epoch=1)
        
        assert ml.meters["epoch"].value == 1

    def test_update_with_invalid_type_warns(self) -> None:
        """Test that update warns for invalid types."""
        ml = MetricLogger()
        
        with pytest.warns(UserWarning, match="non-numeric value"):
            ml.update(invalid="string")
        
        # Invalid key should not be in meters
        assert "invalid" not in ml.meters

    def test_update_without_run_is_silent(self) -> None:
        """Test that update without active run doesn't raise."""
        ml = MetricLogger()
        
        # Should not raise
        ml.update(loss=0.5)
        
        assert ml.meters["loss"].value == 0.5


class TestMetricLoggerRunIntegration:
    """Tests for MetricLogger integration with Runicorn Run."""

    def test_update_calls_run_log(self) -> None:
        """Test that update calls run.log() when run is active."""
        mock_run = MagicMock()
        
        with patch('runicorn.sdk.get_active_run', return_value=mock_run):
            ml = MetricLogger()
            ml.update(loss=0.5, acc=0.9)
        
        mock_run.log.assert_called_once()
        call_args = mock_run.log.call_args[0][0]
        assert call_args["loss"] == 0.5
        assert call_args["acc"] == 0.9

    def test_update_without_run_still_updates_meters(self) -> None:
        """Test that meters are updated even without active run."""
        with patch('runicorn.sdk.get_active_run', return_value=None):
            ml = MetricLogger()
            ml.update(loss=0.5)
        
        assert ml.meters["loss"].value == 0.5


class TestMetricLoggerAttributes:
    """Tests for MetricLogger attribute access."""

    def test_getattr_returns_meter(self) -> None:
        """Test that attribute access returns meter."""
        ml = MetricLogger()
        ml.update(loss=0.5)
        
        assert ml.loss.value == 0.5

    def test_getattr_raises_for_unknown(self) -> None:
        """Test that attribute access raises for unknown keys."""
        ml = MetricLogger()
        
        with pytest.raises(AttributeError):
            _ = ml.unknown_metric


class TestMetricLoggerStr:
    """Tests for MetricLogger string representation."""

    def test_str_format(self) -> None:
        """Test string format."""
        ml = MetricLogger(delimiter=" | ")
        ml.update(loss=0.5)
        ml.update(acc=0.9)
        
        s = str(ml)
        assert "loss:" in s
        assert "acc:" in s
        assert " | " in s


class TestMetricLoggerAddMeter:
    """Tests for MetricLogger.add_meter()."""

    def test_add_meter(self) -> None:
        """Test adding a custom meter."""
        ml = MetricLogger()
        custom_meter = SmoothedValue(window_size=10, fmt="{value:.2f}")
        
        ml.add_meter("custom", custom_meter)
        
        assert ml.meters["custom"] is custom_meter


class TestMetricLoggerLogEvery:
    """Tests for MetricLogger.log_every()."""

    def test_log_every_yields_all_items(self) -> None:
        """Test that log_every yields all items."""
        ml = MetricLogger()
        items = [1, 2, 3, 4, 5]
        
        # Capture stdout
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        
        try:
            result = list(ml.log_every(items, print_freq=10, header="Test"))
        finally:
            sys.stdout = old_stdout
        
        assert result == items

    def test_log_every_prints_progress(self) -> None:
        """Test that log_every prints progress."""
        ml = MetricLogger()
        items = [1, 2, 3]
        
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        
        try:
            list(ml.log_every(items, print_freq=1, header="Test"))
        finally:
            sys.stdout = old_stdout
        
        output = captured.getvalue()
        assert "Test" in output
        assert "Total time" in output

    def test_log_every_prints_total_time_on_exception(self) -> None:
        """Test that log_every prints total time even on exception."""
        ml = MetricLogger()
        
        def failing_iterator():
            yield 1
            yield 2
            raise ValueError("Test error")
        
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        
        try:
            with pytest.raises(ValueError):
                for _ in ml.log_every(failing_iterator(), print_freq=1, header="Test"):
                    pass
        finally:
            sys.stdout = old_stdout
        
        output = captured.getvalue()
        assert "Total time" in output

    def test_log_every_handles_unknown_length(self) -> None:
        """Test that log_every handles iterables without __len__."""
        ml = MetricLogger()
        
        def generator():
            yield 1
            yield 2
            yield 3
        
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        
        try:
            result = list(ml.log_every(generator(), print_freq=1, header="Test"))
        finally:
            sys.stdout = old_stdout
        
        assert result == [1, 2, 3]


class TestMetricLoggerSync:
    """Tests for MetricLogger.synchronize_between_processes()."""

    def test_sync_calls_meter_sync(self) -> None:
        """Test that sync calls sync on all meters."""
        ml = MetricLogger()
        ml.update(loss=0.5)
        ml.update(acc=0.9)
        
        # Mock the meter sync methods
        ml.meters["loss"].synchronize_between_processes = MagicMock()
        ml.meters["acc"].synchronize_between_processes = MagicMock()
        
        ml.synchronize_between_processes()
        
        ml.meters["loss"].synchronize_between_processes.assert_called_once()
        ml.meters["acc"].synchronize_between_processes.assert_called_once()


class TestImports:
    """Tests for module imports."""

    def test_import_from_log_compat(self) -> None:
        """Test importing from runicorn.log_compat."""
        from runicorn.log_compat import MetricLogger, SmoothedValue, TorchvisionMetricLogger
        
        assert MetricLogger is not None
        assert SmoothedValue is not None
        assert TorchvisionMetricLogger is MetricLogger

    def test_import_from_torchvision_module(self) -> None:
        """Test importing from runicorn.log_compat.torchvision."""
        from runicorn.log_compat.torchvision import MetricLogger, SmoothedValue
        
        assert MetricLogger is not None
        assert SmoothedValue is not None
