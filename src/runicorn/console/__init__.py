"""
Console capture module for Runicorn.

This module provides:
- LogManager: Centralized log file manager with thread-safe writing
- TeeWriter: File-like object that writes to multiple destinations
- ConsoleCapture: Context manager for capturing stdout/stderr
- RunicornLoggingHandler: Python logging handler for Runicorn integration

Usage:
    from runicorn.console import ConsoleCapture, LogManager

    # Capture console output
    with ConsoleCapture(log_path=Path("logs.txt")) as capture:
        print("This goes to both terminal and log file")

    # Use logging handler
    from runicorn.console import RunicornLoggingHandler
    handler = RunicornLoggingHandler(run=my_run)
    logger.addHandler(handler)
"""
from __future__ import annotations

from .log_manager import LogManager
from .capture import TeeWriter, ConsoleCapture
from .logging_handler import RunicornLoggingHandler

__all__ = [
    "LogManager",
    "TeeWriter",
    "ConsoleCapture",
    "RunicornLoggingHandler",
]
