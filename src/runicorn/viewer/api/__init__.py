"""
API Routes Module - Exports all API routers

This module provides a centralized import point for all API routers.
Each router handles a specific domain of functionality.
"""
from __future__ import annotations

from .health import router as health_router
from .runs import router as runs_router  
from .metrics import router as metrics_router
from .config import router as config_router
from .ssh import router as ssh_router
from .experiments import router as experiments_router
from .export import router as export_router
from .projects import router as projects_router
from .gpu import router as gpu_router
from .import_ import router as import_router
from .artifacts import router as artifacts_router

__all__ = [
    "health_router",
    "runs_router", 
    "metrics_router",
    "config_router",
    "ssh_router",
    "experiments_router", 
    "export_router",
    "projects_router",
    "gpu_router",
    "import_router",
    "artifacts_router",
]
