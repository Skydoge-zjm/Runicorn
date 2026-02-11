"""
Python logging handler for Runicorn integration.

This module provides RunicornLoggingHandler, a standard Python logging.Handler
that writes log records to Runicorn's log file via LogManager.

Features:
- Thread-safe logging via LogManager
- Lazy initialization (works even without active Run)
- Configurable log level and format
- Works independently of console capture

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .log_manager import LogManager

if TYPE_CHECKING:
    from ..sdk import Run


class RunicornLoggingHandler(logging.Handler):
    """
    A thread-safe logging handler that writes log records to Runicorn's log file.
    
    Uses LogManager for efficient file handling. Can be used with or without
    an active Run - if no Run is available, log records are silently dropped.
    
    Features:
        - Standard Python logging.Handler subclass
        - Thread-safe via LogManager
        - Lazy initialization of LogManager
        - Configurable log level and format
        - Works independently of console capture
    
    Usage:
        # With explicit Run
        run = runicorn.init()
        handler = RunicornLoggingHandler(run=run)
        logger.addHandler(handler)
        
        # Or get from Run
        handler = run.get_logging_handler()
        logger.addHandler(handler)
        
        # Without Run (uses active run if available)
        handler = RunicornLoggingHandler()
        logger.addHandler(handler)
    
    Args:
        run: Optional Run instance. If not provided, uses get_active_run().
        level: Minimum log level (default: logging.INFO)
        fmt: Custom format string (optional)
    """
    
    # Default format string
    DEFAULT_FORMAT = '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    DEFAULT_DATEFMT = '%H:%M:%S'
    
    def __init__(
        self,
        run: Optional["Run"] = None,
        level: int = logging.INFO,
        fmt: Optional[str] = None,
    ) -> None:
        """
        Initialize the logging handler.
        
        Args:
            run: Optional Run instance. If not provided, uses get_active_run().
            level: Minimum log level (default: logging.INFO)
            fmt: Custom format string (optional)
        """
        super().__init__(level)
        self._run = run
        self._log_manager: Optional[LogManager] = None
        self._log_path: Optional[Path] = None
        self._lock = threading.Lock()
        self._closed = False
        
        # Set formatter
        if fmt:
            self.setFormatter(logging.Formatter(fmt))
        else:
            self.setFormatter(logging.Formatter(
                self.DEFAULT_FORMAT,
                datefmt=self.DEFAULT_DATEFMT
            ))
    
    @property
    def run(self) -> Optional["Run"]:
        """
        Get the associated Run, falling back to active run.
        
        Returns:
            The Run instance, or None if no run is available.
        """
        if self._run is not None:
            return self._run
        
        # Try to get active run
        try:
            from ..sdk import get_active_run
            return get_active_run()
        except ImportError:
            return None
    
    def _ensure_log_manager(self) -> Optional[LogManager]:
        """
        Lazily initialize LogManager when first needed.
        
        Returns:
            LogManager instance, or None if no Run is available.
        """
        run = self.run
        if run is None:
            return None
        
        # Get log path from run
        log_path = getattr(run, '_logs_txt_path', None)
        if log_path is None:
            return None
        
        with self._lock:
            # Check if path changed (different run)
            if self._log_path != log_path:
                # Release old manager
                if self._log_manager is not None and self._log_path is not None:
                    LogManager.release_instance(self._log_path)
                
                # Get new manager
                self._log_path = log_path
                self._log_manager = LogManager.get_instance(log_path)
            
            return self._log_manager
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to the run's log file.
        
        Args:
            record: The log record to emit.
        """
        if self._closed:
            return
        
        try:
            log_manager = self._ensure_log_manager()
            if log_manager is None:
                return
            
            msg = self.format(record)
            log_manager.write(msg + '\n')
        except Exception:
            self.handleError(record)
    
    def close(self) -> None:
        """
        Release LogManager reference and close handler.
        """
        with self._lock:
            self._closed = True
            if self._log_manager is not None and self._log_path is not None:
                LogManager.release_instance(self._log_path)
                self._log_manager = None
                self._log_path = None
        super().close()
