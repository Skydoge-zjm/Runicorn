"""
Unit tests for LogManager.

Tests cover:
- Thread-safe write from multiple threads
- Reference counting (get/release)
- File creation on first write
- Proper cleanup on close
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from runicorn.console.log_manager import LogManager


@pytest.fixture(autouse=True)
def cleanup_log_managers():
    """Clean up all LogManager instances after each test."""
    yield
    LogManager.clear_all()


class TestLogManagerBasic:
    """Basic functionality tests for LogManager."""

    def test_get_instance_creates_new_manager(self, tmp_path: Path) -> None:
        """Test that get_instance creates a new LogManager."""
        log_path = tmp_path / "test.log"
        
        manager = LogManager.get_instance(log_path)
        
        assert manager is not None
        assert manager.log_path == log_path.resolve()
        assert LogManager.get_ref_count(log_path) == 1

    def test_get_instance_returns_same_manager(self, tmp_path: Path) -> None:
        """Test that get_instance returns the same manager for the same path."""
        log_path = tmp_path / "test.log"
        
        manager1 = LogManager.get_instance(log_path)
        manager2 = LogManager.get_instance(log_path)
        
        assert manager1 is manager2
        assert LogManager.get_ref_count(log_path) == 2

    def test_release_instance_decrements_ref_count(self, tmp_path: Path) -> None:
        """Test that release_instance decrements the reference count."""
        log_path = tmp_path / "test.log"
        
        LogManager.get_instance(log_path)
        LogManager.get_instance(log_path)
        assert LogManager.get_ref_count(log_path) == 2
        
        LogManager.release_instance(log_path)
        assert LogManager.get_ref_count(log_path) == 1

    def test_release_instance_removes_manager_at_zero(self, tmp_path: Path) -> None:
        """Test that release_instance removes manager when ref_count reaches 0."""
        log_path = tmp_path / "test.log"
        
        LogManager.get_instance(log_path)
        assert LogManager.get_ref_count(log_path) == 1
        
        LogManager.release_instance(log_path)
        assert LogManager.get_ref_count(log_path) == 0

    def test_release_nonexistent_path_is_safe(self, tmp_path: Path) -> None:
        """Test that releasing a non-existent path doesn't raise."""
        log_path = tmp_path / "nonexistent.log"
        
        # Should not raise
        LogManager.release_instance(log_path)


class TestLogManagerWrite:
    """Tests for LogManager write functionality."""

    def test_write_creates_file(self, tmp_path: Path) -> None:
        """Test that write creates the log file on first write."""
        log_path = tmp_path / "test.log"
        
        manager = LogManager.get_instance(log_path)
        assert not log_path.exists()
        
        manager.write("Hello, world!\n")
        
        assert log_path.exists()
        assert log_path.read_text() == "Hello, world!\n"

    def test_write_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that write creates parent directories if needed."""
        log_path = tmp_path / "subdir" / "nested" / "test.log"
        
        manager = LogManager.get_instance(log_path)
        manager.write("Test\n")
        
        assert log_path.exists()
        assert log_path.read_text() == "Test\n"

    def test_write_appends_to_file(self, tmp_path: Path) -> None:
        """Test that write appends to existing content."""
        log_path = tmp_path / "test.log"
        
        manager = LogManager.get_instance(log_path)
        manager.write("Line 1\n")
        manager.write("Line 2\n")
        
        assert log_path.read_text() == "Line 1\nLine 2\n"

    def test_write_flushes_immediately(self, tmp_path: Path) -> None:
        """Test that write flushes to disk immediately."""
        log_path = tmp_path / "test.log"
        
        manager = LogManager.get_instance(log_path)
        manager.write("Immediate flush test\n")
        
        # Read directly from disk without closing
        content = log_path.read_text()
        assert content == "Immediate flush test\n"

    def test_write_empty_string(self, tmp_path: Path) -> None:
        """Test that writing empty string doesn't cause issues."""
        log_path = tmp_path / "test.log"
        
        manager = LogManager.get_instance(log_path)
        manager.write("")
        manager.write("After empty\n")
        
        assert log_path.read_text() == "After empty\n"


class TestLogManagerClose:
    """Tests for LogManager close functionality."""

    def test_close_closes_file(self, tmp_path: Path) -> None:
        """Test that close properly closes the file."""
        log_path = tmp_path / "test.log"
        
        manager = LogManager.get_instance(log_path)
        manager.write("Test\n")
        assert manager.is_open
        
        manager.close()
        assert not manager.is_open

    def test_close_is_idempotent(self, tmp_path: Path) -> None:
        """Test that close can be called multiple times safely."""
        log_path = tmp_path / "test.log"
        
        manager = LogManager.get_instance(log_path)
        manager.write("Test\n")
        
        manager.close()
        manager.close()  # Should not raise
        
        assert not manager.is_open

    def test_write_after_close_reopens_file(self, tmp_path: Path) -> None:
        """Test that write after close reopens the file."""
        log_path = tmp_path / "test.log"
        
        manager = LogManager.get_instance(log_path)
        manager.write("Before close\n")
        manager.close()
        
        manager.write("After close\n")
        
        assert log_path.read_text() == "Before close\nAfter close\n"

    def test_clear_all_closes_all_managers(self, tmp_path: Path) -> None:
        """Test that clear_all closes all managers."""
        log_path1 = tmp_path / "test1.log"
        log_path2 = tmp_path / "test2.log"
        
        manager1 = LogManager.get_instance(log_path1)
        manager2 = LogManager.get_instance(log_path2)
        manager1.write("Test1\n")
        manager2.write("Test2\n")
        
        LogManager.clear_all()
        
        assert LogManager.get_ref_count(log_path1) == 0
        assert LogManager.get_ref_count(log_path2) == 0


class TestLogManagerThreadSafety:
    """Tests for LogManager thread safety."""

    def test_concurrent_writes_no_data_loss(self, tmp_path: Path) -> None:
        """Test that concurrent writes don't lose data."""
        log_path = tmp_path / "test.log"
        manager = LogManager.get_instance(log_path)
        
        num_threads = 10
        writes_per_thread = 100
        
        def writer(thread_id: int) -> None:
            for i in range(writes_per_thread):
                manager.write(f"Thread {thread_id} Line {i}\n")
        
        threads = [
            threading.Thread(target=writer, args=(i,))
            for i in range(num_threads)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify all lines were written
        content = log_path.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == num_threads * writes_per_thread

    def test_concurrent_get_release_instance(self, tmp_path: Path) -> None:
        """Test that concurrent get/release operations are safe."""
        log_path = tmp_path / "test.log"
        
        num_threads = 20
        iterations = 50
        errors: list[Exception] = []
        
        def worker() -> None:
            try:
                for _ in range(iterations):
                    manager = LogManager.get_instance(log_path)
                    manager.write("x")
                    time.sleep(0.001)  # Small delay to increase contention
                    LogManager.release_instance(log_path)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_multiple_managers_different_paths(self, tmp_path: Path) -> None:
        """Test that different paths get different managers."""
        log_path1 = tmp_path / "test1.log"
        log_path2 = tmp_path / "test2.log"
        
        manager1 = LogManager.get_instance(log_path1)
        manager2 = LogManager.get_instance(log_path2)
        
        assert manager1 is not manager2
        
        manager1.write("File 1\n")
        manager2.write("File 2\n")
        
        assert log_path1.read_text() == "File 1\n"
        assert log_path2.read_text() == "File 2\n"


class TestLogManagerPathNormalization:
    """Tests for path normalization in LogManager."""

    def test_same_path_different_format(self, tmp_path: Path) -> None:
        """Test that different path formats resolve to the same manager."""
        log_path1 = tmp_path / "test.log"
        log_path2 = tmp_path / "." / "test.log"
        
        manager1 = LogManager.get_instance(log_path1)
        manager2 = LogManager.get_instance(log_path2)
        
        # Both should resolve to the same manager
        assert manager1 is manager2
        assert LogManager.get_ref_count(log_path1) == 2
