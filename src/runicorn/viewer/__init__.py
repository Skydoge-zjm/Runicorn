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
    ssh_router,
    experiments_router,
    export_router,
    projects_router,
    gpu_router,
    import_router,
    artifacts_router,
)

# Import experiment-artifacts integration router
from .api.experiment_artifacts import router as experiment_artifacts_router

# Import model lifecycle router
from .api.model_lifecycle import router as model_lifecycle_router

# Import UI preferences router
from .api.ui_preferences import router as ui_preferences_router

# Import unified SSH router
try:
    from .api.unified_ssh import router as unified_ssh_router
    HAS_UNIFIED_SSH = True
except ImportError:
    unified_ssh_router = None
    HAS_UNIFIED_SSH = False

# Import remote storage router (optional)
try:
    from .api.remote_storage import router as remote_storage_router
    HAS_REMOTE_STORAGE_API = True
except ImportError:
    remote_storage_router = None
    HAS_REMOTE_STORAGE_API = False

# Import v2 APIs for modern storage
from .api.v2 import (
    v2_experiments_router,
    v2_analytics_router
)

__version__ = "0.4.0"

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
        
        # Close remote adapter if connected
        if hasattr(app.state, 'remote_adapter') and app.state.remote_adapter:
            try:
                app.state.remote_adapter.close()
                logger.info("Closed remote storage adapter")
            except Exception as e:
                logger.warning(f"Failed to close remote adapter: {e}")
    
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
    
    # Register artifacts router
    app.include_router(artifacts_router, prefix="/api", tags=["artifacts"])
    
    # Register experiment-artifacts integration router
    app.include_router(experiment_artifacts_router, prefix="/api", tags=["experiment-artifacts"])
    
    # Register model lifecycle router
    app.include_router(model_lifecycle_router, prefix="/api", tags=["model-lifecycle"])
    
    # Register UI preferences router
    app.include_router(ui_preferences_router, prefix="/api", tags=["ui-preferences"])
    
    # Register unified SSH router (if available)
    if HAS_UNIFIED_SSH and unified_ssh_router:
        app.include_router(unified_ssh_router, prefix="/api", tags=["unified-ssh"])
        logger.info("Unified SSH API routes registered")
    
    # Register remote storage router (if available)
    if HAS_REMOTE_STORAGE_API and remote_storage_router:
        app.include_router(remote_storage_router, prefix="/api", tags=["remote-storage"])
        logger.info("Remote storage API routes registered")
    
    # Register v2 API routers (modern storage)
    app.include_router(v2_experiments_router, prefix="/api/v2", tags=["v2-experiments"])
    app.include_router(v2_analytics_router, prefix="/api/v2", tags=["v2-analytics"])
    
    # Store storage root and mode for access by routers
    app.state.storage_root = root
    app.state.storage_mode = "local"  # Default to local mode
    app.state.remote_adapter = None   # Will be set when user connects
    
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