"""
Storage Utilities

Helper functions for determining correct storage root path
based on storage mode (local vs remote).
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request


def get_storage_root(request: Request) -> Path:
    """
    Get the appropriate storage root.
    
    Args:
        request: FastAPI request object with app state
        
    Returns:
        Path to storage root directory
    """
    return request.app.state.storage_root
