"""
Helper Utilities

Common utility functions used across the viewer module.
"""
from __future__ import annotations

import logging
from pathlib import Path

from ...security.path_validation import validate_resolved_path

logger = logging.getLogger(__name__)


def is_within_directory(base: Path, target: Path) -> bool:
    """
    Check if target path is within base directory (security check).
    
    This function prevents path traversal attacks by ensuring that
    the target path resolves to a location within the base directory.
    
    Args:
        base: Base directory path
        target: Target path to check
        
    Returns:
        True if target is within base directory, False otherwise
    """
    try:
        ok, error = validate_resolved_path(target, base)
        if not ok:
            logger.debug(f"Path resolution failed: {error}")
        return ok
    except Exception as e:
        logger.debug(f"Path resolution failed: {e}")
        return False


