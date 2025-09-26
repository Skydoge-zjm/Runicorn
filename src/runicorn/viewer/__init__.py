"""
Runicorn Viewer Module - Modular FastAPI Application

This module provides the web interface and API for Runicorn experiment tracking.
The viewer has been refactored into a modular architecture for better maintainability.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .utils.logging import setup_logging
from .services.storage import get_storage_root, periodic_status_check
from .api import (
    health_router,
    runs_router, 
    metrics_router,
    config_router,
    ssh_router,
    experiments_router,
    export_router,
    projects_router,
    gpu_router,
    import_router
)

# Import v2 APIs for modern storage
from .api.v2 import (
    v2_experiments_router,
    v2_analytics_router
)

__version__ = "0.3.1"

logger = logging.getLogger(__name__)


def create_app(storage: Optional[str] = None) -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Args:
        storage: Optional storage directory path override
        
    Returns:
        Configured FastAPI application instance
    """
    # Initialize storage root
    root = get_storage_root(storage)
    
    # Setup logging
    setup_logging()
    
    # Create FastAPI app
    app = FastAPI(
        title="Runicorn Viewer",
        version=__version__,
        description="Local experiment tracking and visualization platform"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*", "http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Background task for status checking
    _status_check_task = None
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize background tasks on app startup."""
        nonlocal _status_check_task
        _status_check_task = asyncio.create_task(periodic_status_check(root))
        logger.info("Started background process status checker")
    
    @app.on_event("shutdown") 
    async def shutdown_event():
        """Cleanup background tasks on app shutdown."""
        if _status_check_task:
            _status_check_task.cancel()
            try:
                await _status_check_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped background process status checker")
    
    # Register v1 API routers (backward compatibility)
    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(runs_router, prefix="/api", tags=["runs"])
    app.include_router(metrics_router, prefix="/api", tags=["metrics"])
    app.include_router(config_router, prefix="/api", tags=["config"])
    app.include_router(ssh_router, prefix="/api", tags=["ssh"])
    app.include_router(experiments_router, prefix="/api", tags=["experiments"])
    app.include_router(export_router, prefix="/api", tags=["export"])
    app.include_router(projects_router, prefix="/api", tags=["projects"])
    app.include_router(gpu_router, prefix="/api", tags=["gpu"])
    app.include_router(import_router, prefix="/api", tags=["import"])
    
    # Register v2 API routers (modern storage)
    app.include_router(v2_experiments_router, prefix="/api/v2", tags=["v2-experiments"])
    app.include_router(v2_analytics_router, prefix="/api/v2", tags=["v2-analytics"])
    
    # Store storage root for access by routers
    app.state.storage_root = root
    
    # Mount static frontend if available
    _mount_static_frontend(app)
    
    return app


def _mount_static_frontend(app: FastAPI) -> None:
    """
    Mount static frontend files if available.
    
    Args:
        app: FastAPI application instance
    """
    import os
    
    try:
        # Check for development frontend dist path
        env_dir_s = os.environ.get("RUNICORN_FRONTEND_DIST") or os.environ.get("RUNICORN_DESKTOP_FRONTEND")
        if env_dir_s:
            env_dir = Path(env_dir_s)
            if env_dir.exists():
                app.mount("/", StaticFiles(directory=str(env_dir), html=True), name="frontend")
                return
    except Exception as e:
        logger.debug(f"Could not mount development frontend: {e}")
    
    try:
        # Fallback: serve the packaged webui if present
        ui_dir = Path(__file__).parent.parent / "webui"
        if ui_dir.exists():
            app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="frontend")
            logger.info(f"Mounted static frontend from: {ui_dir}")
    except Exception as e:
        logger.debug(f"Static frontend not available: {e}")