"""Unit tests for runicorn.console.capture."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

from runicorn.console.capture import ConsoleCapture, TeeWriter
from runicorn.console.log_manager import LogManager


@pytest.fixture(autouse=True)
def _cleanup_log_manager():
    """Clean LogManager singletons between tests."""
    yield
    LogManager.clear_all()


class TestTeeWriter:
    """TeeWriter writes to both terminal and log."""

    def test_writes_to_both(self, tmp_path: Path):
        original = io.StringIO()
        mgr = LogManager.get_instance(tmp_path / "log.txt")
        tee = TeeWriter(original, mgr, tqdm_mode="all", add_timestamp=False)
        tee.write("hello\n")
        assert "hello" in original.getvalue()
        log_content = (tmp_path / "log.txt").read_text(encoding="utf-8")
        assert "hello" in log_content

    def test_smart_mode_buffers_cr(self, tmp_path: Path):
        """Smart mode: \\r lines are buffered, only final version written."""
        original = io.StringIO()
        mgr = LogManager.get_instance(tmp_path / "log.txt")
        tee = TeeWriter(original, mgr, tqdm_mode="smart", add_timestamp=False)
        # Simulate tqdm: progress 50%, then 100%
        tee.write("\rprogress 50%")
        tee.write("\rprogress 100%\n")

        log_content = (tmp_path / "log.txt").read_text(encoding="utf-8")
        assert "progress 100%" in log_content
        # 50% should NOT appear — was overwritten by \r
        assert "progress 50%" not in log_content

    def test_none_mode_skips_cr(self, tmp_path: Path):
        """tqdm_mode='none' skips \\r content entirely."""
        original = io.StringIO()
        mgr = LogManager.get_instance(tmp_path / "log.txt")
        tee = TeeWriter(original, mgr, tqdm_mode="none", add_timestamp=False)
        tee.write("\rprogress\n")
        # Still writes to original
        assert "\rprogress\n" in original.getvalue()
        # But log file should be empty (the \r triggers skip)
        log = tmp_path / "log.txt"
        assert not log.exists() or log.read_text(encoding="utf-8").strip() == ""

    def test_empty_write_returns_zero(self, tmp_path: Path):
        original = io.StringIO()
        mgr = LogManager.get_instance(tmp_path / "log.txt")
        tee = TeeWriter(original, mgr)
        assert tee.write("") == 0


class TestConsoleCapture:
    """ConsoleCapture replaces and restores sys.stdout/stderr."""

    def test_replaces_stdout(self, tmp_path: Path):
        orig_stdout = sys.stdout
        cap = ConsoleCapture(tmp_path / "log.txt")
        cap.start()
        assert sys.stdout is not orig_stdout
        assert isinstance(sys.stdout, TeeWriter)
        cap.stop()
        assert sys.stdout is orig_stdout

    def test_context_manager(self, tmp_path: Path):
        orig_stdout = sys.stdout
        with ConsoleCapture(tmp_path / "log.txt"):
            assert sys.stdout is not orig_stdout
        assert sys.stdout is orig_stdout

    def test_captures_print_output(self, tmp_path: Path):
        log = tmp_path / "log.txt"
        with ConsoleCapture(log, add_timestamp=False):
            print("captured line")

        content = log.read_text(encoding="utf-8")
        assert "captured line" in content

    def test_cleanup_all(self, tmp_path: Path):
        """_cleanup_all stops all active captures."""
        cap = ConsoleCapture(tmp_path / "log.txt")
        cap.start()
        assert cap.is_capturing
        ConsoleCapture._cleanup_all()
        assert not cap.is_capturing
