"""
Console capture module for redirecting stdout/stderr to log files.

This module provides:
- TeeWriter: File-like object that writes to multiple destinations
- ConsoleCapture: Context manager for capturing console output

Features:
- Smart tqdm handling (buffer \r lines, only write final version)
- Timestamp prefixing for log entries
- ANSI escape sequence preservation
- Thread-safe writing via LogManager
- Emergency cleanup via atexit

Validates: Requirements 1.1, 1.2, 1.3, 1.6, 1.7, 1.8, 1.9, 2.1, 2.3, 2.4
"""
from __future__ import annotations

import atexit
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import ClassVar, Optional, TextIO

from .log_manager import LogManager


class TeeWriter:
    """
    A file-like object that writes to multiple destinations.
    
    Implements TextIO protocol and smart handling of carriage return for tqdm.
    Writes to both the original stream (terminal) and a log file via LogManager.
    
    Features:
        - Preserves ANSI escape sequences for color rendering
        - Smart tqdm mode: buffers \r lines, only writes final version
        - Optional timestamp prefixing
        - Thread-safe via LogManager
    
    Args:
        original: The original stream to write to (e.g., sys.stdout)
        log_manager: LogManager instance for file writing
        tqdm_mode: How to handle progress bars ("smart", "all", "none")
        add_timestamp: Whether to add timestamps to log entries
    """
    
    def __init__(
        self,
        original: TextIO,
        log_manager: LogManager,
        tqdm_mode: str = "smart",
        add_timestamp: bool = True,
    ) -> None:
        self.original = original
        self.log_manager = log_manager
        self.tqdm_mode = tqdm_mode
        self.add_timestamp = add_timestamp
        self._cr_buffer = ""  # Buffer for \r lines
        self._lock = threading.Lock()
        self._line_buffer = ""  # Buffer for incomplete lines
    
    # === Core write methods ===
    
    def write(self, text: str) -> int:
        """
        Write to both terminal and log file.
        
        Args:
            text: Text to write
            
        Returns:
            Number of characters written
        """
        if not text:
            return 0
        
        with self._lock:
            # Always write to original terminal
            self.original.write(text)
            
            # Handle tqdm mode
            if self.tqdm_mode == "none" and '\r' in text:
                return len(text)
            
            if self.tqdm_mode == "smart":
                return self._write_smart(text)
            else:  # "all"
                return self._write_all(text)
    
    def _write_smart(self, text: str) -> int:
        """
        Smart mode: buffer \r lines, only write final version.
        
        Logic:
        - Lines with \r are progress bar updates (tqdm style)
        - Buffer content after \r until we see \n
        - When \n arrives, write the final buffered content
        
        Args:
            text: Text to process
            
        Returns:
            Number of characters in original text
        """
        result_lines: list[str] = []
        
        # Process character by character for precise \r handling
        for char in text:
            if char == '\r':
                # Carriage return: clear current buffer (simulates cursor to line start)
                self._cr_buffer = ""
            elif char == '\n':
                # Newline: flush buffer as complete line
                if self._cr_buffer.strip():  # Only write non-empty lines
                    result_lines.append(self._cr_buffer)
                self._cr_buffer = ""
            else:
                self._cr_buffer += char
        
        # Write collected lines to log
        for line in result_lines:
            self._write_line(line)
        
        return len(text)
    
    def _write_all(self, text: str) -> int:
        """
        All mode: write everything including \r updates.
        
        Args:
            text: Text to write
            
        Returns:
            Number of characters in original text
        """
        # Replace \r with \n for log file
        log_text = text.replace('\r', '\n')
        for line in log_text.split('\n'):
            if line:  # Skip empty lines
                self._write_line(line)
        return len(text)
    
    def _write_line(self, line: str) -> None:
        """
        Write a single line to log file with optional timestamp.
        
        Args:
            line: Line content (without newline)
        """
        if self.add_timestamp:
            timestamp = datetime.now().strftime('%H:%M:%S')
            prefix = f"[{timestamp}] "
        else:
            prefix = ""
        
        self.log_manager.write(f"{prefix}{line}\n")
    
    def flush(self) -> None:
        """Flush both streams."""
        with self._lock:
            self.original.flush()
            # LogManager handles its own flushing
    
    # === TextIO protocol methods ===
    
    @property
    def encoding(self) -> str:
        """Return encoding of the original stream."""
        return getattr(self.original, 'encoding', 'utf-8')
    
    @property
    def errors(self) -> Optional[str]:
        """Return error handling mode of the original stream."""
        return getattr(self.original, 'errors', None)
    
    @property
    def newlines(self) -> Optional[str]:
        """Return newline mode of the original stream."""
        return getattr(self.original, 'newlines', None)
    
    def fileno(self) -> int:
        """Return file descriptor of original stream."""
        return self.original.fileno()
    
    def isatty(self) -> bool:
        """Return whether original stream is a TTY."""
        return self.original.isatty()
    
    def readable(self) -> bool:
        """Return False as this is a write-only stream."""
        return False
    
    def writable(self) -> bool:
        """Return True as this is a writable stream."""
        return True
    
    def seekable(self) -> bool:
        """Return False as this stream is not seekable."""
        return False
    
    def close(self) -> None:
        """Flush remaining buffer on close."""
        with self._lock:
            if self._cr_buffer.strip():
                self._write_line(self._cr_buffer)
                self._cr_buffer = ""
    
    # Delegate other methods to original
    def __getattr__(self, name: str):
        """Delegate unknown attributes to the original stream."""
        return getattr(self.original, name)


class ConsoleCapture:
    """
    Context manager for capturing console output.
    
    Redirects stdout and/or stderr to both the terminal and a log file.
    Supports nested captures and emergency cleanup via atexit.
    
    Features:
        - Tee mode: writes to both terminal and log file
        - Smart tqdm handling
        - Automatic stream restoration on exit
        - Emergency cleanup via atexit for abnormal termination
    
    Usage:
        with ConsoleCapture(log_path=Path("logs.txt")) as capture:
            print("This goes to both terminal and log file")
        
        # Or manual control:
        capture = ConsoleCapture(log_path=Path("logs.txt"))
        capture.start()
        print("Captured")
        capture.stop()
    
    Args:
        log_path: Path to the log file
        tqdm_mode: How to handle progress bars ("smart", "all", "none")
        capture_stdout: Whether to capture stdout
        capture_stderr: Whether to capture stderr
        add_timestamp: Whether to add timestamps to log entries
    """
    
    # Class-level tracking for cleanup
    _active_captures: ClassVar[list["ConsoleCapture"]] = []
    _atexit_registered: ClassVar[bool] = False
    _class_lock: ClassVar[threading.Lock] = threading.Lock()
    
    def __init__(
        self,
        log_path: Path,
        tqdm_mode: str = "smart",
        capture_stdout: bool = True,
        capture_stderr: bool = True,
        add_timestamp: bool = True,
    ) -> None:
        self.log_path = Path(log_path)
        self.tqdm_mode = tqdm_mode
        self.capture_stdout = capture_stdout
        self.capture_stderr = capture_stderr
        self.add_timestamp = add_timestamp
        
        self._original_stdout: Optional[TextIO] = None
        self._original_stderr: Optional[TextIO] = None
        self._stdout_tee: Optional[TeeWriter] = None
        self._stderr_tee: Optional[TeeWriter] = None
        self._log_manager: Optional[LogManager] = None
        self._started = False
    
    def start(self) -> None:
        """Start capturing console output."""
        if self._started:
            return
        
        # Register atexit handler once
        with ConsoleCapture._class_lock:
            if not ConsoleCapture._atexit_registered:
                atexit.register(ConsoleCapture._cleanup_all)
                ConsoleCapture._atexit_registered = True
        
        # Get LogManager instance
        self._log_manager = LogManager.get_instance(self.log_path)
        
        if self.capture_stdout:
            self._original_stdout = sys.stdout
            self._stdout_tee = TeeWriter(
                self._original_stdout,
                self._log_manager,
                self.tqdm_mode,
                self.add_timestamp,
            )
            sys.stdout = self._stdout_tee  # type: ignore
        
        if self.capture_stderr:
            self._original_stderr = sys.stderr
            self._stderr_tee = TeeWriter(
                self._original_stderr,
                self._log_manager,
                self.tqdm_mode,
                self.add_timestamp,
            )
            sys.stderr = self._stderr_tee  # type: ignore
        
        self._started = True
        
        with ConsoleCapture._class_lock:
            ConsoleCapture._active_captures.append(self)
    
    def stop(self) -> None:
        """Stop capturing and restore original streams."""
        if not self._started:
            return
        
        try:
            # Flush any remaining buffered content
            if self._stdout_tee is not None:
                try:
                    self._stdout_tee.close()
                except Exception:
                    pass
            if self._stderr_tee is not None:
                try:
                    self._stderr_tee.close()
                except Exception:
                    pass
        finally:
            # Always restore original streams
            if self._original_stdout is not None:
                sys.stdout = self._original_stdout
                self._original_stdout = None
            if self._original_stderr is not None:
                sys.stderr = self._original_stderr
                self._original_stderr = None
            
            self._stdout_tee = None
            self._stderr_tee = None
            
            # Release LogManager reference
            if self._log_manager is not None:
                LogManager.release_instance(self.log_path)
                self._log_manager = None
            
            self._started = False
            
            with ConsoleCapture._class_lock:
                if self in ConsoleCapture._active_captures:
                    ConsoleCapture._active_captures.remove(self)
    
    @classmethod
    def _cleanup_all(cls) -> None:
        """Emergency cleanup on process exit."""
        with cls._class_lock:
            captures = list(cls._active_captures)
        
        for capture in captures:
            try:
                capture.stop()
            except Exception:
                pass
    
    @property
    def is_capturing(self) -> bool:
        """Return whether capture is currently active."""
        return self._started
    
    def __enter__(self) -> "ConsoleCapture":
        """Start capture when entering context."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop capture when exiting context."""
        self.stop()
