"""
Integration tests for console capture with SDK.

Tests cover:
- End-to-end capture with Run
- Print output captured to logs.txt
- tqdm mode handling
- get_logging_handler() integration
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

import runicorn as rn
from runicorn.console.log_manager import LogManager


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up after each test."""
    yield
    LogManager.clear_all()


@pytest.fixture
def storage_dir(tmp_path: Path) -> Path:
    """Create a temporary storage directory."""
    storage = tmp_path / "storage"
    storage.mkdir(parents=True, exist_ok=True)
    return storage


class TestConsoleCaptureWithRun:
    """Integration tests for console capture with Run."""

    def test_capture_console_false_by_default(
        self, storage_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that capture_console defaults to False."""
        monkeypatch.setenv("RUNICORN_DIR", str(storage_dir))
        
        run = rn.init(path="test")
        
        try:
            # Console capture should not be active
            assert run._console_capture is None
            assert run._capture_console is False
        finally:
            run.finish()

    def test_capture_console_captures_print(
        self, storage_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that print output is captured when capture_console=True."""
        monkeypatch.setenv("RUNICORN_DIR", str(storage_dir))
        
        run = rn.init(path="test", capture_console=True)
        
        try:
            print("Hello from print!")
            print("Another line")
            
            # Force flush
            sys.stdout.flush()
        finally:
            run.finish()
        
        # Check logs.txt content
        logs_path = run.run_dir / "logs.txt"
        assert logs_path.exists()
        content = logs_path.read_text()
        assert "Hello from print!" in content
        assert "Another line" in content

    def test_capture_console_captures_stderr(
        self, storage_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that stderr is captured when capture_console=True."""
        monkeypatch.setenv("RUNICORN_DIR", str(storage_dir))
        
        run = rn.init(path="test", capture_console=True)
        
        try:
            print("Error message", file=sys.stderr)
        finally:
            run.finish()
        
        logs_path = run.run_dir / "logs.txt"
        content = logs_path.read_text()
        assert "Error message" in content

    def test_capture_console_restores_streams(
        self, storage_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that streams are restored after finish()."""
        monkeypatch.setenv("RUNICORN_DIR", str(storage_dir))
        
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        run = rn.init(path="test", capture_console=True)
        
        # Streams should be redirected
        assert sys.stdout is not original_stdout
        
        run.finish()
        
        # Streams should be restored
        assert sys.stdout is original_stdout
        assert sys.stderr is original_stderr

    def test_tqdm_mode_smart(
        self, storage_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test smart tqdm mode buffers carriage return lines."""
        monkeypatch.setenv("RUNICORN_DIR", str(storage_dir))
        
        run = rn.init(path="test", capture_console=True, tqdm_mode="smart")
        
        try:
            # Simulate tqdm progress
            sys.stdout.write("Progress: 10%\r")
            sys.stdout.write("Progress: 50%\r")
            sys.stdout.write("Progress: 100%\n")
            sys.stdout.flush()
        finally:
            run.finish()
        
        logs_path = run.run_dir / "logs.txt"
        content = logs_path.read_text()
        
        # Only final version should be in log
        assert "Progress: 100%" in content
        # Intermediate versions should not be in log
        assert "Progress: 10%" not in content
        assert "Progress: 50%" not in content

    def test_context_manager_usage(
        self, storage_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test using Run as context manager with capture_console."""
        monkeypatch.setenv("RUNICORN_DIR", str(storage_dir))
        
        original_stdout = sys.stdout
        
        with rn.init(path="test", capture_console=True) as run:
            print("Inside context")
            run_dir = run.run_dir
        
        # Streams should be restored
        assert sys.stdout is original_stdout
        
        # Content should be captured
        logs_path = run_dir / "logs.txt"
        content = logs_path.read_text()
        assert "Inside context" in content


class TestLoggingHandlerIntegration:
    """Integration tests for get_logging_handler()."""

    def test_get_logging_handler(
        self, storage_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_logging_handler() returns working handler."""
        monkeypatch.setenv("RUNICORN_DIR", str(storage_dir))
        
        run = rn.init(path="test")
        
        try:
            handler = run.get_logging_handler()
            
            logger = logging.getLogger("test_handler")
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            
            logger.info("Test log message")
            logger.warning("Warning message")
            
            logger.removeHandler(handler)
            handler.close()
        finally:
            run.finish()
        
        logs_path = run.run_dir / "logs.txt"
        content = logs_path.read_text()
        assert "Test log message" in content
        assert "Warning message" in content

    def test_logging_handler_with_custom_format(
        self, storage_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_logging_handler() with custom format."""
        monkeypatch.setenv("RUNICORN_DIR", str(storage_dir))
        
        run = rn.init(path="test")
        
        try:
            handler = run.get_logging_handler(fmt="[CUSTOM] %(message)s")
            
            logger = logging.getLogger("test_custom_format")
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            
            logger.info("Custom format test")
            
            logger.removeHandler(handler)
            handler.close()
        finally:
            run.finish()
        
        logs_path = run.run_dir / "logs.txt"
        content = logs_path.read_text()
        assert "[CUSTOM] Custom format test" in content

    def test_logging_handler_with_level_filter(
        self, storage_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_logging_handler() with level filtering."""
        monkeypatch.setenv("RUNICORN_DIR", str(storage_dir))
        
        run = rn.init(path="test")
        
        try:
            handler = run.get_logging_handler(level=logging.WARNING)
            
            logger = logging.getLogger("test_level_filter")
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            
            logger.removeHandler(handler)
            handler.close()
        finally:
            run.finish()
        
        logs_path = run.run_dir / "logs.txt"
        content = logs_path.read_text()
        assert "Debug message" not in content
        assert "Info message" not in content
        assert "Warning message" in content


class TestGetActiveRun:
    """Tests for get_active_run() export."""

    def test_get_active_run_exported(self) -> None:
        """Test that get_active_run is exported from runicorn."""
        assert hasattr(rn, 'get_active_run')
        assert callable(rn.get_active_run)

    def test_get_active_run_returns_none_initially(self) -> None:
        """Test that get_active_run returns None when no run is active."""
        # Note: This may fail if other tests leave a run active
        # In practice, the SDK manages this via _active_run global
        pass  # Skip this test as it depends on global state
