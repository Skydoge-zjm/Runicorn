"""
Unit tests for TeeWriter and ConsoleCapture.

Tests cover:
- TeeWriter: write to both destinations, tqdm modes, TextIO protocol
- ConsoleCapture: start/stop lifecycle, stream restoration, atexit cleanup
"""
from __future__ import annotations

import io
import sys
import threading
from pathlib import Path

import pytest

from runicorn.console.capture import TeeWriter, ConsoleCapture
from runicorn.console.log_manager import LogManager


@pytest.fixture(autouse=True)
def cleanup_log_managers():
    """Clean up all LogManager instances after each test."""
    yield
    LogManager.clear_all()


class TestTeeWriterBasic:
    """Basic functionality tests for TeeWriter."""

    def test_write_to_both_destinations(self, tmp_path: Path) -> None:
        """Test that write goes to both original and log file."""
        log_path = tmp_path / "test.log"
        original = io.StringIO()
        log_manager = LogManager.get_instance(log_path)
        
        tee = TeeWriter(original, log_manager, tqdm_mode="all", add_timestamp=False)
        tee.write("Hello\n")
        
        assert original.getvalue() == "Hello\n"
        assert "Hello" in log_path.read_text()

    def test_write_returns_length(self, tmp_path: Path) -> None:
        """Test that write returns the number of characters."""
        log_path = tmp_path / "test.log"
        original = io.StringIO()
        log_manager = LogManager.get_instance(log_path)
        
        tee = TeeWriter(original, log_manager, tqdm_mode="all", add_timestamp=False)
        result = tee.write("Hello")
        
        assert result == 5

    def test_write_empty_string(self, tmp_path: Path) -> None:
        """Test that writing empty string returns 0."""
        log_path = tmp_path / "test.log"
        original = io.StringIO()
        log_manager = LogManager.get_instance(log_path)
        
        tee = TeeWriter(original, log_manager, tqdm_mode="all", add_timestamp=False)
        result = tee.write("")
        
        assert result == 0


class TestTeeWriterTimestamp:
    """Tests for TeeWriter timestamp functionality."""

    def test_timestamp_added_when_enabled(self, tmp_path: Path) -> None:
        """Test that timestamps are added when enabled."""
        log_path = tmp_path / "test.log"
        original = io.StringIO()
        log_manager = LogManager.get_instance(log_path)
        
        tee = TeeWriter(original, log_manager, tqdm_mode="all", add_timestamp=True)
        tee.write("Test message\n")
        
        content = log_path.read_text()
        # Should have format [HH:MM:SS] message
        assert content.startswith("[")
        assert "] Test message" in content

    def test_no_timestamp_when_disabled(self, tmp_path: Path) -> None:
        """Test that timestamps are not added when disabled."""
        log_path = tmp_path / "test.log"
        original = io.StringIO()
        log_manager = LogManager.get_instance(log_path)
        
        tee = TeeWriter(original, log_manager, tqdm_mode="all", add_timestamp=False)
        tee.write("Test message\n")
        
        content = log_path.read_text()
        assert content == "Test message\n"


class TestTeeWriterTqdmModes:
    """Tests for TeeWriter tqdm handling modes."""

    def test_smart_mode_buffers_cr_lines(self, tmp_path: Path) -> None:
        """Test that smart mode buffers carriage return lines."""
        log_path = tmp_path / "test.log"
        original = io.StringIO()
        log_manager = LogManager.get_instance(log_path)
        
        tee = TeeWriter(original, log_manager, tqdm_mode="smart", add_timestamp=False)
        
        # Simulate tqdm progress: multiple \r updates followed by \n
        tee.write("Progress: 10%\r")
        tee.write("Progress: 50%\r")
        tee.write("Progress: 100%\n")
        
        content = log_path.read_text()
        # Only the final version should be in the log
        assert "Progress: 100%" in content
        assert "Progress: 10%" not in content
        assert "Progress: 50%" not in content

    def test_smart_mode_handles_mixed_content(self, tmp_path: Path) -> None:
        """Test smart mode with mixed regular and progress content."""
        log_path = tmp_path / "test.log"
        original = io.StringIO()
        log_manager = LogManager.get_instance(log_path)
        
        tee = TeeWriter(original, log_manager, tqdm_mode="smart", add_timestamp=False)
        
        tee.write("Starting...\n")
        tee.write("Progress: 50%\r")
        tee.write("Progress: 100%\n")
        tee.write("Done!\n")
        
        content = log_path.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 3
        assert "Starting..." in lines[0]
        assert "Progress: 100%" in lines[1]
        assert "Done!" in lines[2]

    def test_all_mode_writes_everything(self, tmp_path: Path) -> None:
        """Test that all mode writes every update."""
        log_path = tmp_path / "test.log"
        original = io.StringIO()
        log_manager = LogManager.get_instance(log_path)
        
        tee = TeeWriter(original, log_manager, tqdm_mode="all", add_timestamp=False)
        
        tee.write("Progress: 10%\r")
        tee.write("Progress: 50%\r")
        tee.write("Progress: 100%\n")
        
        content = log_path.read_text()
        # All updates should be in the log
        assert "Progress: 10%" in content
        assert "Progress: 50%" in content
        assert "Progress: 100%" in content

    def test_none_mode_skips_cr_lines(self, tmp_path: Path) -> None:
        """Test that none mode skips lines with carriage return."""
        log_path = tmp_path / "test.log"
        original = io.StringIO()
        log_manager = LogManager.get_instance(log_path)
        
        tee = TeeWriter(original, log_manager, tqdm_mode="none", add_timestamp=False)
        
        tee.write("Regular line\n")
        tee.write("Progress: 50%\r")
        tee.write("Another regular\n")
        
        content = log_path.read_text()
        assert "Regular line" in content
        assert "Another regular" in content
        assert "Progress" not in content


class TestTeeWriterAnsiPreservation:
    """Tests for ANSI escape sequence preservation."""

    def test_ansi_colors_preserved(self, tmp_path: Path) -> None:
        """Test that ANSI color codes are preserved in log file."""
        log_path = tmp_path / "test.log"
        original = io.StringIO()
        log_manager = LogManager.get_instance(log_path)
        
        tee = TeeWriter(original, log_manager, tqdm_mode="all", add_timestamp=False)
        
        # ANSI red color
        ansi_text = "\033[31mRed text\033[0m\n"
        tee.write(ansi_text)
        
        content = log_path.read_text()
        assert "\033[31m" in content
        assert "\033[0m" in content


class TestTeeWriterTextIOProtocol:
    """Tests for TextIO protocol implementation."""

    def test_encoding_property(self, tmp_path: Path) -> None:
        """Test encoding property returns original's encoding."""
        log_path = tmp_path / "test.log"
        original = io.StringIO()
        log_manager = LogManager.get_instance(log_path)
        
        tee = TeeWriter(original, log_manager)
        
        assert tee.encoding == original.encoding

    def test_writable_returns_true(self, tmp_path: Path) -> None:
        """Test writable() returns True."""
        log_path = tmp_path / "test.log"
        original = io.StringIO()
        log_manager = LogManager.get_instance(log_path)
        
        tee = TeeWriter(original, log_manager)
        
        assert tee.writable() is True

    def test_readable_returns_false(self, tmp_path: Path) -> None:
        """Test readable() returns False."""
        log_path = tmp_path / "test.log"
        original = io.StringIO()
        log_manager = LogManager.get_instance(log_path)
        
        tee = TeeWriter(original, log_manager)
        
        assert tee.readable() is False

    def test_seekable_returns_false(self, tmp_path: Path) -> None:
        """Test seekable() returns False."""
        log_path = tmp_path / "test.log"
        original = io.StringIO()
        log_manager = LogManager.get_instance(log_path)
        
        tee = TeeWriter(original, log_manager)
        
        assert tee.seekable() is False

    def test_flush_flushes_original(self, tmp_path: Path) -> None:
        """Test flush() flushes the original stream."""
        log_path = tmp_path / "test.log"
        original = io.StringIO()
        log_manager = LogManager.get_instance(log_path)
        
        tee = TeeWriter(original, log_manager)
        tee.write("Test")
        tee.flush()
        
        # Should not raise
        assert True

    def test_close_flushes_buffer(self, tmp_path: Path) -> None:
        """Test close() flushes remaining buffer."""
        log_path = tmp_path / "test.log"
        original = io.StringIO()
        log_manager = LogManager.get_instance(log_path)
        
        tee = TeeWriter(original, log_manager, tqdm_mode="smart", add_timestamp=False)
        
        # Write without newline (stays in buffer)
        tee.write("Buffered content\r")
        tee.write("Final content")
        
        # Close should flush the buffer
        tee.close()
        
        content = log_path.read_text()
        assert "Final content" in content


class TestConsoleCaptureLifecycle:
    """Tests for ConsoleCapture lifecycle management."""

    def test_start_redirects_stdout(self, tmp_path: Path) -> None:
        """Test that start() redirects stdout."""
        log_path = tmp_path / "test.log"
        original_stdout = sys.stdout
        
        capture = ConsoleCapture(log_path)
        capture.start()
        
        try:
            assert sys.stdout is not original_stdout
            assert capture.is_capturing
        finally:
            capture.stop()

    def test_stop_restores_stdout(self, tmp_path: Path) -> None:
        """Test that stop() restores original stdout."""
        log_path = tmp_path / "test.log"
        original_stdout = sys.stdout
        
        capture = ConsoleCapture(log_path)
        capture.start()
        capture.stop()
        
        assert sys.stdout is original_stdout
        assert not capture.is_capturing

    def test_context_manager(self, tmp_path: Path) -> None:
        """Test context manager usage."""
        log_path = tmp_path / "test.log"
        original_stdout = sys.stdout
        
        with ConsoleCapture(log_path) as capture:
            assert sys.stdout is not original_stdout
            assert capture.is_capturing
        
        assert sys.stdout is original_stdout

    def test_captures_print_output(self, tmp_path: Path) -> None:
        """Test that print output is captured to log file."""
        log_path = tmp_path / "test.log"
        
        with ConsoleCapture(log_path, add_timestamp=False):
            print("Hello from print!")
        
        content = log_path.read_text()
        assert "Hello from print!" in content

    def test_captures_stderr(self, tmp_path: Path) -> None:
        """Test that stderr is captured."""
        log_path = tmp_path / "test.log"
        
        with ConsoleCapture(log_path, add_timestamp=False):
            print("Error message", file=sys.stderr)
        
        content = log_path.read_text()
        assert "Error message" in content

    def test_stdout_only_capture(self, tmp_path: Path) -> None:
        """Test capturing only stdout."""
        log_path = tmp_path / "test.log"
        original_stderr = sys.stderr
        
        with ConsoleCapture(log_path, capture_stdout=True, capture_stderr=False):
            assert sys.stderr is original_stderr

    def test_stderr_only_capture(self, tmp_path: Path) -> None:
        """Test capturing only stderr."""
        log_path = tmp_path / "test.log"
        original_stdout = sys.stdout
        
        with ConsoleCapture(log_path, capture_stdout=False, capture_stderr=True):
            assert sys.stdout is original_stdout

    def test_start_is_idempotent(self, tmp_path: Path) -> None:
        """Test that calling start() twice is safe."""
        log_path = tmp_path / "test.log"
        
        capture = ConsoleCapture(log_path)
        capture.start()
        capture.start()  # Should not raise
        
        try:
            assert capture.is_capturing
        finally:
            capture.stop()

    def test_stop_is_idempotent(self, tmp_path: Path) -> None:
        """Test that calling stop() twice is safe."""
        log_path = tmp_path / "test.log"
        
        capture = ConsoleCapture(log_path)
        capture.start()
        capture.stop()
        capture.stop()  # Should not raise
        
        assert not capture.is_capturing


class TestConsoleCaptureThreadSafety:
    """Tests for ConsoleCapture thread safety."""

    def test_concurrent_prints_no_crash(self, tmp_path: Path) -> None:
        """Test concurrent print calls don't crash or corrupt the log file.
        
        Note: We don't check exact line count because print() itself is not
        atomic and can interleave between threads. The important thing is
        that the capture doesn't crash and all content is eventually written.
        """
        log_path = tmp_path / "test.log"
        num_threads = 5
        prints_per_thread = 20
        errors: list[Exception] = []
        
        with ConsoleCapture(log_path, add_timestamp=False):
            def printer(thread_id: int) -> None:
                try:
                    for i in range(prints_per_thread):
                        print(f"Thread {thread_id} Line {i}")
                except Exception as e:
                    errors.append(e)
            
            threads = [
                threading.Thread(target=printer, args=(i,))
                for i in range(num_threads)
            ]
            
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        
        # No errors should have occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Log file should exist and have content
        content = log_path.read_text()
        assert len(content) > 0
        
        # All thread IDs should appear in the log
        for thread_id in range(num_threads):
            assert f"Thread {thread_id}" in content


class TestConsoleCaptureGracefulDegradation:
    """Tests for graceful degradation scenarios."""

    def test_exception_in_context_restores_streams(self, tmp_path: Path) -> None:
        """Test that streams are restored even if exception occurs."""
        log_path = tmp_path / "test.log"
        original_stdout = sys.stdout
        
        try:
            with ConsoleCapture(log_path):
                print("Before exception")
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        assert sys.stdout is original_stdout

    def test_stop_without_start(self, tmp_path: Path) -> None:
        """Test that stop() without start() is safe."""
        log_path = tmp_path / "test.log"
        
        capture = ConsoleCapture(log_path)
        capture.stop()  # Should not raise
        
        assert not capture.is_capturing
