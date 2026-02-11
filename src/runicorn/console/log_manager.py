"""
Centralized log file manager with thread-safe writing.

This module provides LogManager, which handles:
- Thread-safe writing to log files
- Reference counting for shared file handles
- Immediate flush after each write for real-time streaming

Validates: Requirements 1.8, 1.9, 3.2
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import ClassVar, Optional, TextIO


class LogManager:
    """
    Centralized log file manager with thread-safe writing.
    Uses reference counting to share file handles across components.
    
    This class implements a singleton-per-path pattern where multiple
    components (TeeWriter, RunicornLoggingHandler) can share the same
    file handle for a given log path.
    
    Thread Safety:
        - All public methods are thread-safe
        - Uses a global lock for instance management
        - Uses per-instance locks for file operations
    
    Usage:
        # Get or create a LogManager for a path
        manager = LogManager.get_instance(Path("logs.txt"))
        
        # Write to the log file (thread-safe, immediate flush)
        manager.write("Hello, world!\\n")
        
        # Release when done (decrements ref count)
        LogManager.release_instance(Path("logs.txt"))
    """
    
    # Class-level registry of LogManager instances by path
    _instances: ClassVar[dict[Path, "LogManager"]] = {}
    
    # Global lock for managing the instances registry
    _global_lock: ClassVar[threading.Lock] = threading.Lock()
    
    def __init__(self, log_path: Path) -> None:
        """
        Initialize a LogManager for the given path.
        
        Note: Use get_instance() instead of direct instantiation
        to ensure proper reference counting.
        
        Args:
            log_path: Path to the log file
        """
        self.log_path = log_path
        self._file: Optional[TextIO] = None
        self._lock = threading.Lock()
        self._ref_count = 0
    
    @classmethod
    def get_instance(cls, log_path: Path) -> "LogManager":
        """
        Get or create a LogManager for the given path.
        Increments reference count.
        
        Args:
            log_path: Path to the log file
            
        Returns:
            LogManager instance for the path
        """
        with cls._global_lock:
            path_key = log_path.resolve()
            if path_key not in cls._instances:
                cls._instances[path_key] = cls(path_key)
            instance = cls._instances[path_key]
            instance._ref_count += 1
            return instance
    
    @classmethod
    def release_instance(cls, log_path: Path) -> None:
        """
        Release a reference to a LogManager.
        Closes file and removes instance when ref_count reaches 0.
        
        Args:
            log_path: Path to the log file
        """
        with cls._global_lock:
            path_key = log_path.resolve()
            if path_key in cls._instances:
                instance = cls._instances[path_key]
                instance._ref_count -= 1
                if instance._ref_count <= 0:
                    instance.close()
                    del cls._instances[path_key]
    
    @classmethod
    def get_ref_count(cls, log_path: Path) -> int:
        """
        Get the current reference count for a log path.
        
        Args:
            log_path: Path to the log file
            
        Returns:
            Current reference count, or 0 if no instance exists
        """
        with cls._global_lock:
            path_key = log_path.resolve()
            if path_key in cls._instances:
                return cls._instances[path_key]._ref_count
            return 0
    
    @classmethod
    def clear_all(cls) -> None:
        """
        Close and remove all LogManager instances.
        Useful for testing cleanup.
        """
        with cls._global_lock:
            for instance in list(cls._instances.values()):
                instance.close()
            cls._instances.clear()
    
    def write(self, text: str) -> None:
        """
        Thread-safe write to log file with immediate flush.
        
        Creates parent directories and opens the file on first write.
        Each write is immediately flushed to disk to support real-time
        streaming via WebSocket.
        
        Args:
            text: Text to write to the log file
        """
        with self._lock:
            if self._file is None:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                self._file = open(self.log_path, 'a', encoding='utf-8')
            self._file.write(text)
            self._file.flush()
    
    def close(self) -> None:
        """
        Close the log file.
        
        Safe to call multiple times. Errors during close are silently ignored.
        """
        with self._lock:
            if self._file is not None:
                try:
                    self._file.close()
                except Exception:
                    pass
                self._file = None
    
    @property
    def is_open(self) -> bool:
        """Check if the log file is currently open."""
        with self._lock:
            return self._file is not None
