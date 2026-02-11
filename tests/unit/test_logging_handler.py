"""
Unit tests for RunicornLoggingHandler.

Tests cover:
- Standard logging.Handler behavior
- Thread-safe emit via LogManager
- Lazy LogManager initialization
- Works with/without active Run
- Custom level and format
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runicorn.console.logging_handler import RunicornLoggingHandler
from runicorn.console.log_manager import LogManager


@pytest.fixture(autouse=True)
def cleanup_log_managers():
    """Clean up all LogManager instances after each test."""
    yield
    LogManager.clear_all()


class MockRun:
    """Mock Run class for testing."""
    
    def __init__(self, logs_path: Path) -> None:
        self._logs_txt_path = logs_path


class TestRunicornLoggingHandlerBasic:
    """Basic functionality tests for RunicornLoggingHandler."""

    def test_is_logging_handler_subclass(self) -> None:
        """Test that RunicornLoggingHandler is a logging.Handler subclass."""
        handler = RunicornLoggingHandler()
        assert isinstance(handler, logging.Handler)

    def test_default_level_is_info(self) -> None:
        """Test that default level is INFO."""
        handler = RunicornLoggingHandler()
        assert handler.level == logging.INFO

    def test_custom_level(self) -> None:
        """Test setting custom log level."""
        handler = RunicornLoggingHandler(level=logging.DEBUG)
        assert handler.level == logging.DEBUG

    def test_default_format(self) -> None:
        """Test default format string."""
        handler = RunicornLoggingHandler()
        assert handler.formatter is not None
        # Default format includes asctime, levelname, name, message
        fmt = handler.formatter._fmt
        assert '%(asctime)s' in fmt
        assert '%(levelname)s' in fmt
        assert '%(name)s' in fmt
        assert '%(message)s' in fmt

    def test_custom_format(self) -> None:
        """Test setting custom format string."""
        custom_fmt = '%(levelname)s - %(message)s'
        handler = RunicornLoggingHandler(fmt=custom_fmt)
        assert handler.formatter._fmt == custom_fmt


class TestRunicornLoggingHandlerEmit:
    """Tests for emit functionality."""

    def test_emit_writes_to_log_file(self, tmp_path: Path) -> None:
        """Test that emit writes formatted message to log file."""
        log_path = tmp_path / "test.log"
        mock_run = MockRun(log_path)
        
        handler = RunicornLoggingHandler(run=mock_run, fmt='%(message)s')
        
        # Create a log record
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        handler.emit(record)
        
        content = log_path.read_text()
        assert 'Test message' in content

    def test_emit_without_run_is_silent(self) -> None:
        """Test that emit without Run doesn't raise."""
        handler = RunicornLoggingHandler()
        
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        # Should not raise
        handler.emit(record)

    def test_emit_after_close_is_silent(self, tmp_path: Path) -> None:
        """Test that emit after close doesn't write."""
        log_path = tmp_path / "test.log"
        mock_run = MockRun(log_path)
        
        handler = RunicornLoggingHandler(run=mock_run, fmt='%(message)s')
        handler.close()
        
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Should not appear',
            args=(),
            exc_info=None
        )
        
        handler.emit(record)
        
        # File should not exist or be empty
        if log_path.exists():
            assert 'Should not appear' not in log_path.read_text()


class TestRunicornLoggingHandlerWithLogger:
    """Tests for integration with Python logging module."""

    def test_logger_integration(self, tmp_path: Path) -> None:
        """Test using handler with a logger."""
        log_path = tmp_path / "test.log"
        mock_run = MockRun(log_path)
        
        handler = RunicornLoggingHandler(run=mock_run, fmt='%(message)s')
        
        logger = logging.getLogger('test_logger_integration')
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        
        try:
            logger.info('Info message')
            logger.warning('Warning message')
            
            content = log_path.read_text()
            assert 'Info message' in content
            assert 'Warning message' in content
        finally:
            logger.removeHandler(handler)
            handler.close()

    def test_level_filtering(self, tmp_path: Path) -> None:
        """Test that log level filtering works."""
        log_path = tmp_path / "test.log"
        mock_run = MockRun(log_path)
        
        handler = RunicornLoggingHandler(
            run=mock_run, 
            level=logging.WARNING,
            fmt='%(message)s'
        )
        
        logger = logging.getLogger('test_level_filtering')
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        
        try:
            logger.debug('Debug message')
            logger.info('Info message')
            logger.warning('Warning message')
            logger.error('Error message')
            
            content = log_path.read_text()
            assert 'Debug message' not in content
            assert 'Info message' not in content
            assert 'Warning message' in content
            assert 'Error message' in content
        finally:
            logger.removeHandler(handler)
            handler.close()


class TestRunicornLoggingHandlerThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_emit(self, tmp_path: Path) -> None:
        """Test concurrent emit calls from multiple threads."""
        log_path = tmp_path / "test.log"
        mock_run = MockRun(log_path)
        
        handler = RunicornLoggingHandler(run=mock_run, fmt='%(message)s')
        
        num_threads = 5
        logs_per_thread = 20
        errors: list[Exception] = []
        
        def log_messages(thread_id: int) -> None:
            try:
                for i in range(logs_per_thread):
                    record = logging.LogRecord(
                        name='test',
                        level=logging.INFO,
                        pathname='test.py',
                        lineno=1,
                        msg=f'Thread {thread_id} Message {i}',
                        args=(),
                        exc_info=None
                    )
                    handler.emit(record)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=log_messages, args=(i,))
            for i in range(num_threads)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        handler.close()
        
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all threads logged
        content = log_path.read_text()
        for thread_id in range(num_threads):
            assert f'Thread {thread_id}' in content


class TestRunicornLoggingHandlerLazyInit:
    """Tests for lazy LogManager initialization."""

    def test_no_log_manager_until_emit(self, tmp_path: Path) -> None:
        """Test that LogManager is not created until emit is called."""
        log_path = tmp_path / "test.log"
        mock_run = MockRun(log_path)
        
        handler = RunicornLoggingHandler(run=mock_run)
        
        # LogManager should not exist yet
        assert LogManager.get_ref_count(log_path) == 0
        
        # Emit a record
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test',
            args=(),
            exc_info=None
        )
        handler.emit(record)
        
        # Now LogManager should exist
        assert LogManager.get_ref_count(log_path) == 1
        
        handler.close()

    def test_close_releases_log_manager(self, tmp_path: Path) -> None:
        """Test that close releases the LogManager reference."""
        log_path = tmp_path / "test.log"
        mock_run = MockRun(log_path)
        
        handler = RunicornLoggingHandler(run=mock_run)
        
        # Emit to create LogManager
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test',
            args=(),
            exc_info=None
        )
        handler.emit(record)
        
        assert LogManager.get_ref_count(log_path) == 1
        
        handler.close()
        
        assert LogManager.get_ref_count(log_path) == 0


class TestRunicornLoggingHandlerActiveRun:
    """Tests for active run fallback."""

    def test_uses_active_run_when_no_explicit_run(self, tmp_path: Path) -> None:
        """Test that handler uses active run when no explicit run provided."""
        log_path = tmp_path / "test.log"
        mock_run = MockRun(log_path)
        
        with patch('runicorn.sdk.get_active_run', return_value=mock_run):
            handler = RunicornLoggingHandler(fmt='%(message)s')
            
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg='Active run test',
                args=(),
                exc_info=None
            )
            handler.emit(record)
            
            content = log_path.read_text()
            assert 'Active run test' in content
            
            handler.close()

    def test_explicit_run_takes_precedence(self, tmp_path: Path) -> None:
        """Test that explicit run takes precedence over active run."""
        explicit_path = tmp_path / "explicit.log"
        active_path = tmp_path / "active.log"
        
        explicit_run = MockRun(explicit_path)
        active_run = MockRun(active_path)
        
        with patch('runicorn.sdk.get_active_run', return_value=active_run):
            handler = RunicornLoggingHandler(run=explicit_run, fmt='%(message)s')
            
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg='Explicit run test',
                args=(),
                exc_info=None
            )
            handler.emit(record)
            
            # Should write to explicit path, not active path
            assert explicit_path.exists()
            assert 'Explicit run test' in explicit_path.read_text()
            assert not active_path.exists()
            
            handler.close()
