"""
Runicorn Viewer - Legacy Compatibility Module

This module provides backward compatibility with the old viewer.py interface
while using the new modular architecture internally.
"""
from __future__ import annotations

from typing import Optional
from fastapi import FastAPI

# Import the new modular viewer
from .viewer import create_app as _create_app


def create_app(storage: Optional[str] = None) -> FastAPI:
    """
    Create FastAPI app using the new modular architecture.
    
    This function provides backward compatibility with the old viewer.py interface.
    
    Args:
        storage: Optional storage directory path override
        
    Returns:
        Configured FastAPI application instance
    """
    return _create_app(storage)


# For backward compatibility - make the function available at module level
__all__ = ["create_app"]
