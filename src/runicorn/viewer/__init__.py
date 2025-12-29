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
from .middleware.rate_limit import RateLimitMiddleware
from .services.storage import get_storage_root, periodic_status_check
from .api import (
    health_router,
    runs_router, 
    metrics_router,
    config_router,
    experiments_router,
    export_router,
    projects_router,
    gpu_router,
    import_router,
    remote_router,
    system_router,
    storage_router,
    ui_preferences_router,
)

# Import version from main package
from .. import __version__

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
    
    # Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware)
    
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
        """Cleanup background tasks and connections on app shutdown."""
        # Stop background status checker
        if _status_check_task:
            _status_check_task.cancel()
            try:
                await _status_check_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped background process status checker")
        
        # Close Remote Viewer sessions
        if hasattr(app.state, 'viewer_manager'):
            try:
                sessions = app.state.viewer_manager.list_sessions()
                for session in sessions:
                    app.state.viewer_manager.stop_remote_viewer(session.session_id)
                logger.info("Closed all Remote Viewer sessions")
            except Exception as e:
                logger.warning(f"Failed to close Remote Viewer sessions: {e}")
        
        # Close SSH connection pool
        if hasattr(app.state, 'connection_pool'):
            try:
                app.state.connection_pool.close_all()
                logger.info("Closed all SSH connections")
            except Exception as e:
                logger.warning(f"Failed to close SSH connections: {e}")
        
        # Close storage service (CRITICAL for Windows desktop app)
        try:
            from .services.modern_storage import close_storage_service
            close_storage_service()
            logger.info("Closed storage service and database connections")
        except Exception as e:
            logger.warning(f"Failed to close storage service: {e}")
    
    # Register v1 API routers (backward compatibility)
    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(runs_router, prefix="/api", tags=["runs"])
    app.include_router(metrics_router, prefix="/api", tags=["metrics"])
    app.include_router(config_router, prefix="/api", tags=["config"])
    app.include_router(experiments_router, prefix="/api", tags=["experiments"])
    app.include_router(export_router, prefix="/api", tags=["export"])
    app.include_router(projects_router, prefix="/api", tags=["projects"])
    app.include_router(gpu_router, prefix="/api", tags=["gpu"])
    app.include_router(system_router, prefix="/api", tags=["system"])
    app.include_router(storage_router, prefix="/api", tags=["storage"])
    app.include_router(import_router, prefix="/api", tags=["import"])
    
    # Register UI preferences router
    app.include_router(ui_preferences_router, prefix="/api", tags=["ui-preferences"])
    
    # Register unified remote API
    app.include_router(remote_router, prefix="/api", tags=["remote"])
    logger.info("Remote API routes registered (Remote Viewer ready)")
    
    # Store storage root and mode for access by routers
    app.state.storage_root = root
    
    
    # Initialize Remote Viewer components
    try:
        from ..remote import SSHConnectionPool
        from ..remote.viewer import RemoteViewerManager
        app.state.connection_pool = SSHConnectionPool()
        app.state.viewer_manager = RemoteViewerManager()
        logger.info("Remote Viewer components initialized")
    except ImportError as e:
        logger.warning(f"Could not initialize Remote Viewer: {e}")
    
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