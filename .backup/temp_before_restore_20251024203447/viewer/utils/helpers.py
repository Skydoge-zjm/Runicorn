"""
Helper Utilities

Common utility functions used across the viewer module.
"""
from __future__ import annotations

import logging
from pathlib import Path

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
        base_resolved = base.resolve()
        target_resolved = target.resolve()
        return str(target_resolved).startswith(str(base_resolved))
    except Exception as e:
        logger.debug(f"Path resolution failed: {e}")
        return False


def format_bytes(bytes_value: int) -> str:
    """
    Format byte count as human-readable string.
    
    Args:
        bytes_value: Number of bytes
        
    Returns:
        Formatted string (e.g., "1.2 MB", "500 KB")
    """
    if bytes_value == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(bytes_value)
    
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def safe_filename(filename: str, max_length: int = 255) -> str:
    """
    Create a safe filename by removing/replacing unsafe characters.
    
    Args:
        filename: Original filename
        max_length: Maximum allowed filename length
        
    Returns:
        Safe filename string
    """
    import re
    
    # Remove unsafe characters
    safe = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    safe = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', safe)
    
    # Trim to max length
    if len(safe) > max_length:
        name, ext = safe.rsplit('.', 1) if '.' in safe else (safe, '')
        max_name_length = max_length - len(ext) - 1 if ext else max_length
        safe = name[:max_name_length] + ('.' + ext if ext else '')
    
    return safe.strip() or "untitled"
