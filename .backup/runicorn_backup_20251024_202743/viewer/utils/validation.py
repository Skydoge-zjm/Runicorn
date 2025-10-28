"""
Input Validation Utilities

Provides validation functions for API inputs to prevent security issues.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


def validate_run_id(run_id: str) -> bool:
    """
    Validate run ID format.
    
    Expected format: YYYYMMDD_HHMMSS_XXXXXX (e.g., 20250930_123456_abc123)
    
    Args:
        run_id: Run ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not run_id or not isinstance(run_id, str):
        return False
    
    # Pattern: 8 digits (date) + _ + 6 digits (time) + _ + 6 hex chars
    pattern = r'^[0-9]{8}_[0-9]{6}_[a-f0-9]{6}$'
    return bool(re.match(pattern, run_id))


def validate_project_name(project: str) -> bool:
    """
    Validate project name.
    
    Args:
        project: Project name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not project or not isinstance(project, str):
        return False
    
    # Disallow path traversal and special characters
    if '..' in project or '/' in project or '\\' in project:
        return False
    
    # Allow alphanumeric, underscore, hyphen, and Chinese characters
    # Maximum length: 100 characters
    if len(project) > 100:
        return False
    
    return True


def validate_experiment_name(name: str) -> bool:
    """
    Validate experiment name.
    
    Args:
        name: Experiment name to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Same validation as project name
    return validate_project_name(name)


def validate_path(path: str, base_dir: Optional[Path] = None) -> bool:
    """
    Validate that a path doesn't escape the base directory.
    
    Args:
        path: Path to validate
        base_dir: Base directory that path must be within
        
    Returns:
        True if valid and safe, False otherwise
    """
    if not path or not isinstance(path, str):
        return False
    
    # Check for path traversal attempts
    if '..' in path:
        return False
    
    # If base_dir provided, ensure path is within it
    if base_dir:
        try:
            full_path = (base_dir / path).resolve()
            base_resolved = base_dir.resolve()
            # Check if the path starts with base_dir
            return str(full_path).startswith(str(base_resolved))
        except Exception:
            return False
    
    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing dangerous characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path separators and dangerous characters
    sanitized = re.sub(r'[/\\<>:"|?*\x00-\x1f]', '_', filename)
    
    # Limit length
    max_length = 255
    if len(sanitized) > max_length:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        sanitized = name[:max_length - len(ext) - 1] + ('.' + ext if ext else '')
    
    return sanitized


def validate_batch_size(size: int, max_size: int = 100) -> bool:
    """
    Validate batch operation size.
    
    Args:
        size: Batch size to validate
        max_size: Maximum allowed size
        
    Returns:
        True if valid, False otherwise
    """
    return isinstance(size, int) and 0 < size <= max_size
