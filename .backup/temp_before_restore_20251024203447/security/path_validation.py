"""
Path Validation Module

Provides secure path validation to prevent directory traversal attacks.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def validate_path(
    user_path: str,
    base_dir: Path,
    allow_symlinks: bool = False
) -> Tuple[bool, Optional[Path], Optional[str]]:
    """
    Validate that a user-provided path is safe and within the base directory.
    
    Args:
        user_path: User-provided path (can be relative or absolute)
        base_dir: Base directory that the path must be within
        allow_symlinks: Whether to allow symbolic links
        
    Returns:
        Tuple of (is_valid, resolved_path, error_message)
    """
    try:
        # Convert to Path objects
        base_dir = Path(base_dir).resolve()
        
        # Check for obvious path traversal attempts
        if '..' in user_path or user_path.startswith('/') or ':' in user_path[1:]:
            return False, None, "Path contains invalid characters or patterns"
        
        # Resolve the path relative to base_dir
        target_path = (base_dir / user_path).resolve()
        
        # Check if resolved path is within base directory
        try:
            target_path.relative_to(base_dir)
        except ValueError:
            return False, None, f"Path escapes base directory: {user_path}"
        
        # Check for symlinks if not allowed
        if not allow_symlinks:
            # Check each component of the path
            current = base_dir
            for part in Path(user_path).parts:
                current = current / part
                if current.exists() and current.is_symlink():
                    return False, None, f"Path contains symbolic link: {part}"
        
        # Additional security checks
        
        # Check path length (Windows compatibility)
        if len(str(target_path)) > 240:  # Leave margin for Windows 260 char limit
            return False, None, f"Path too long: {len(str(target_path))} characters"
        
        # Check for special characters that might cause issues
        forbidden_chars = ['<', '>', '|', '\x00', '*', '?']
        if any(char in str(user_path) for char in forbidden_chars):
            return False, None, "Path contains forbidden characters"
        
        return True, target_path, None
        
    except Exception as e:
        logger.error(f"Path validation error: {e}")
        return False, None, f"Path validation failed: {e}"


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize a filename to be safe for filesystem operations.
    
    Args:
        filename: Original filename
        max_length: Maximum allowed length
        
    Returns:
        Sanitized filename
    """
    import re
    import unicodedata
    
    # Normalize unicode characters
    filename = unicodedata.normalize('NFKD', filename)
    
    # Remove non-ASCII characters
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    # Replace spaces and special characters
    filename = re.sub(r'[^\w\s\-\.]', '_', filename)
    filename = re.sub(r'[-\s]+', '-', filename)
    
    # Remove leading/trailing special characters
    filename = filename.strip('-_. ')
    
    # Ensure filename is not empty
    if not filename:
        filename = 'unnamed'
    
    # Truncate if too long (preserve extension if present)
    if len(filename) > max_length:
        name_parts = filename.rsplit('.', 1)
        if len(name_parts) == 2:
            name, ext = name_parts
            max_name_length = max_length - len(ext) - 1
            if max_name_length > 0:
                filename = f"{name[:max_name_length]}.{ext}"
            else:
                filename = filename[:max_length]
        else:
            filename = filename[:max_length]
    
    # Prevent reserved names on Windows
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    name_without_ext = filename.split('.')[0].upper()
    if name_without_ext in reserved_names:
        filename = f"_{filename}"
    
    return filename


def create_safe_directory(
    base_dir: Path,
    sub_path: str,
    exist_ok: bool = True
) -> Optional[Path]:
    """
    Safely create a directory within a base directory.
    
    Args:
        base_dir: Base directory
        sub_path: Subdirectory path to create
        exist_ok: Whether it's okay if directory already exists
        
    Returns:
        Created directory path or None if failed
    """
    is_valid, target_dir, error = validate_path(sub_path, base_dir)
    
    if not is_valid:
        logger.error(f"Invalid directory path: {error}")
        return None
    
    try:
        target_dir.mkdir(parents=True, exist_ok=exist_ok)
        return target_dir
    except Exception as e:
        logger.error(f"Failed to create directory: {e}")
        return None


def get_safe_download_path(
    requested_path: Optional[str],
    default_dir: Path,
    filename: str
) -> Tuple[bool, Optional[Path], Optional[str]]:
    """
    Get a safe download path for a file.
    
    Args:
        requested_path: User-requested download path (optional)
        default_dir: Default download directory
        filename: Filename to download
        
    Returns:
        Tuple of (is_valid, safe_path, error_message)
    """
    # Sanitize the filename
    safe_filename = sanitize_filename(filename)
    
    if requested_path:
        # User specified a path
        requested = Path(requested_path)
        
        if requested.is_absolute():
            # Absolute path - validate it's in an allowed location
            # For now, reject all absolute paths for security
            return False, None, "Absolute paths are not allowed"
        
        # Validate relative path
        is_valid, safe_dir, error = validate_path(str(requested), default_dir)
        if not is_valid:
            return False, None, error
        
        safe_path = safe_dir / safe_filename
    else:
        # Use default directory
        safe_path = default_dir / safe_filename
    
    # Final validation
    is_valid, final_path, error = validate_path(
        safe_path.relative_to(default_dir),
        default_dir
    )
    
    return is_valid, final_path, error
