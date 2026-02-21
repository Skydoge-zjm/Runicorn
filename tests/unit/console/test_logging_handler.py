"""Unit tests for runicorn.console.logging_handler (migrated from tests_legacy)."""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from runicorn.console.log_manager import LogManager
from runicorn.console.logging_handler import RunicornLoggingHandler


@pytest.fixture(autouse=True)
def _cleanup_log_manager():
    yield
    LogManager.clear_all()


class _MockRun:
    """Minimal mock Run with _logs_txt_path."""

    def __init__(self, logs_path: Path) -> None:
        self._logs_txt_path = logs_path


# === Basic ===

class TestBasic:
    def test_is_handler_subclass(self):
        assert isinstance(RunicornLoggingHandler(), logging.Handler)

    def test_default_level_info(self):
        assert RunicornLoggingHandler().level == logging.INFO

    def test_custom_level(self):
        assert RunicornLoggingHandler(level=logging.DEBUG).level == logging.DEBUG

    def test_default_format(self):
        h = RunicornLoggingHandler()
        fmt = h.formatter._fmt
        assert "%(asctime)s" in fmt
        assert "%(levelname)s" in fmt
        assert "%(message)s" in fmt

    def test_custom_format(self):
        h = RunicornLoggingHandler(fmt="%(levelname)s - %(message)s")
        assert h.formatter._fmt == "%(levelname)s - %(message)s"


# === Emit ===

def _make_record(msg: str) -> logging.LogRecord:
    return logging.LogRecord("test", logging.INFO, "test.py", 1, msg, (), None)


class TestEmit:
    def test_writes_to_log_file(self, tmp_path: Path):
        p = tmp_path / "test.log"
        h = RunicornLoggingHandler(run=_MockRun(p), fmt="%(message)s")
        h.emit(_make_record("hello"))
        assert "hello" in p.read_text()

    def test_without_run_is_silent(self):
        h = RunicornLoggingHandler()
        h.emit(_make_record("no run"))  # should not raise

    def test_after_close_is_silent(self, tmp_path: Path):
        p = tmp_path / "test.log"
        h = RunicornLoggingHandler(run=_MockRun(p), fmt="%(message)s")
        h.close()
        h.emit(_make_record("gone"))
        assert not p.exists() or "gone" not in p.read_text()


# === Logger integration ===

class TestLoggerIntegration:
    def test_logger_writes(self, tmp_path: Path):
        p = tmp_path / "test.log"
        h = RunicornLoggingHandler(run=_MockRun(p), fmt="%(message)s")
        logger = logging.getLogger("test_logger_writes")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(h)
        try:
            logger.info("Info msg")
            logger.warning("Warn msg")
            content = p.read_text()
            assert "Info msg" in content
            assert "Warn msg" in content
        finally:
            logger.removeHandler(h)
            h.close()

    def test_level_filtering(self, tmp_path: Path):
        p = tmp_path / "test.log"
        h = RunicornLoggingHandler(run=_MockRun(p), level=logging.WARNING, fmt="%(message)s")
        logger = logging.getLogger("test_level_filtering")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(h)
        try:
            logger.debug("dbg")
            logger.info("inf")
            logger.warning("wrn")
            logger.error("err")
            content = p.read_text()
            assert "dbg" not in content
            assert "inf" not in content
            assert "wrn" in content
            assert "err" in content
        finally:
            logger.removeHandler(h)
            h.close()


# === Thread safety ===

class TestThreadSafety:
    def test_concurrent_emit(self, tmp_path: Path):
        p = tmp_path / "test.log"
        h = RunicornLoggingHandler(run=_MockRun(p), fmt="%(message)s")
        errors: list[Exception] = []

        def _log(tid: int):
            try:
                for i in range(20):
                    h.emit(_make_record(f"T{tid}-{i}"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_log, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        h.close()

        assert not errors
        content = p.read_text()
        for tid in range(5):
            assert f"T{tid}" in content


# === Lazy init ===

class TestLazyInit:
    def test_no_manager_until_emit(self, tmp_path: Path):
        p = tmp_path / "test.log"
        h = RunicornLoggingHandler(run=_MockRun(p))
        assert LogManager.get_ref_count(p) == 0
        h.emit(_make_record("init"))
        assert LogManager.get_ref_count(p) == 1
        h.close()

    def test_close_releases_manager(self, tmp_path: Path):
        p = tmp_path / "test.log"
        h = RunicornLoggingHandler(run=_MockRun(p))
        h.emit(_make_record("x"))
        assert LogManager.get_ref_count(p) == 1
        h.close()
        assert LogManager.get_ref_count(p) == 0


# === Active run fallback ===

class TestActiveRunFallback:
    def test_uses_active_run(self, tmp_path: Path):
        p = tmp_path / "test.log"
        with patch("runicorn.sdk.get_active_run", return_value=_MockRun(p)):
            h = RunicornLoggingHandler(fmt="%(message)s")
            h.emit(_make_record("active"))
            assert "active" in p.read_text()
            h.close()

    def test_explicit_run_takes_precedence(self, tmp_path: Path):
        explicit = tmp_path / "explicit.log"
        active = tmp_path / "active.log"
        with patch("runicorn.sdk.get_active_run", return_value=_MockRun(active)):
            h = RunicornLoggingHandler(run=_MockRun(explicit), fmt="%(message)s")
            h.emit(_make_record("priority"))
            assert "priority" in explicit.read_text()
            assert not active.exists()
            h.close()
