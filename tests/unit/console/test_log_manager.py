"""Unit tests for runicorn.console.log_manager."""
from __future__ import annotations

from pathlib import Path

import pytest

from runicorn.console.log_manager import LogManager


@pytest.fixture(autouse=True)
def _cleanup_log_manager():
    """Ensure LogManager singleton state is clean between tests."""
    yield
    LogManager.clear_all()


class TestLogManagerSingleton:
    """LogManager returns same instance for same path."""

    def test_same_path_same_instance(self, tmp_path: Path):
        p = tmp_path / "log.txt"
        a = LogManager.get_instance(p)
        b = LogManager.get_instance(p)
        assert a is b


class TestLogManagerRefCounting:
    """Reference counting controls instance lifecycle."""

    def test_ref_count_increments(self, tmp_path: Path):
        p = tmp_path / "log.txt"
        LogManager.get_instance(p)
        LogManager.get_instance(p)
        assert LogManager.get_ref_count(p) == 2

    def test_release_decrements(self, tmp_path: Path):
        p = tmp_path / "log.txt"
        LogManager.get_instance(p)
        LogManager.get_instance(p)
        LogManager.release_instance(p)
        assert LogManager.get_ref_count(p) == 1

    def test_release_to_zero_removes(self, tmp_path: Path):
        p = tmp_path / "log.txt"
        LogManager.get_instance(p)
        LogManager.release_instance(p)
        assert LogManager.get_ref_count(p) == 0


class TestLogManagerWrite:
    """LogManager.write flushes immediately."""

    def test_write_creates_file(self, tmp_path: Path):
        p = tmp_path / "out.txt"
        mgr = LogManager.get_instance(p)
        mgr.write("hello\n")
        # Immediate flush means file should exist and contain text
        assert p.exists()
        assert p.read_text(encoding="utf-8") == "hello\n"

    def test_multiple_writes_append(self, tmp_path: Path):
        p = tmp_path / "out.txt"
        mgr = LogManager.get_instance(p)
        mgr.write("a")
        mgr.write("b")
        assert p.read_text(encoding="utf-8") == "ab"
