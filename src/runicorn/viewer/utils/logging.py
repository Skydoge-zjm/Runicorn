"""
Logging Configuration Utilities

Centralized logging configuration for the viewer module.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from .diagnostics import DiagnosticsLogContext, build_diagnostics_context


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    *,
    session_context: Optional[DiagnosticsLogContext] = None,
) -> DiagnosticsLogContext:
    """
    Setup logging configuration for the viewer module.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If None, uses ~/.runicorn/logs/viewer.log
    """
    logger = logging.getLogger(__name__.split('.')[0])  # Get root logger for runicorn

    if session_context is None:
        session_context = build_diagnostics_context(remote_mode=False)

    # Avoid duplicate handlers if already configured
    existing_context = getattr(logger, "_runicorn_logging_context", None)
    if logger.handlers and existing_context is not None:
        return existing_context
    
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    if not session_context.remote_mode:
        # Console handler for local viewer processes.
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.set_name("runicorn-console")
        console_handler.setLevel(logger.level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler for persistent logs
    try:
        effective_global_log_file: Optional[Path]
        if log_file is not None:
            effective_global_log_file = Path(log_file)
            effective_global_log_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            effective_global_log_file = session_context.global_log_path

        if effective_global_log_file is not None:
            # Create rotating file handler (10MB max, keep 5 backups)
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                effective_global_log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.set_name("runicorn-global-file")
            file_handler.setLevel(logging.DEBUG)  # Always DEBUG level for file
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        session_context.session_log_path.parent.mkdir(parents=True, exist_ok=True)
        session_handler = logging.FileHandler(
            session_context.session_log_path,
            encoding='utf-8',
        )
        session_handler.set_name("runicorn-session-file")
        session_handler.setLevel(logging.DEBUG)
        session_handler.setFormatter(formatter)
        logger.addHandler(session_handler)

        logger._runicorn_logging_context = session_context

        if effective_global_log_file is not None:
            logger.info(f"Logging to file: {effective_global_log_file}")
        logger.info(
            "Diagnostics session started: session_id=%s remote_mode=%s session_log=%s",
            session_context.app_session_id,
            session_context.remote_mode,
            session_context.session_log_path,
        )
    except Exception as e:
        logger.warning(f"Failed to setup file logging: {e}")
    
    # Set specific levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    return session_context
