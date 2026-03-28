"""
Runicorn Viewer Module - Modular FastAPI Application

This module provides the web interface and API for Runicorn experiment tracking.
The viewer has been refactored into a modular architecture for better maintainability.
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import time as _time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.staticfiles import StaticFiles

from .utils.logging import setup_logging
from .middleware.rate_limit import RateLimitMiddleware
from ..storage.file_utils import get_storage_root, periodic_status_check
from .api import (
    health_router,
    runs_router, 
    metrics_router,
    diagnostics_router,
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
from .utils.diagnostics import build_diagnostics_context

logger = logging.getLogger(__name__)


async def reinitialize_storage(app: FastAPI, new_root: Path) -> None:
    """
    Reinitialize storage when user switches root directory.
    Closes the old backend, creates a new one, and restarts background tasks.

    Args:
        app: FastAPI application instance
        new_root: New storage root directory path
    """
    import threading

    # Cancel and wait for the status check task
    old_task = getattr(app.state, "status_check_task", None)
    if old_task is not None and not old_task.done():
        old_task.cancel()
        try:
            await asyncio.wait_for(old_task, timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        logger.info("Stopped background process status checker for storage switch")

    # Wait for sync thread to finish before closing backend (avoids closing SQLite while sync writes)
    sync_thread = getattr(app.state, "sync_thread", None)
    if sync_thread is not None and sync_thread.is_alive():
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: sync_thread.join(timeout=5))
        if sync_thread.is_alive():
            logger.warning("Sync thread did not finish within timeout before storage switch")
        app.state.sync_thread = None

    # Close old storage backend
    old_backend = getattr(app.state, "storage_backend", None)
    if old_backend is not None:
        try:
            old_backend.close()
            logger.info("Closed SQLite storage backend for storage switch")
        except Exception as e:
            logger.warning(f"Failed to close old storage backend: {e}")

    # Create new backend and update app state
    try:
        from ..storage.backends import SQLiteStorageBackend
        app.state.storage_backend = SQLiteStorageBackend(new_root)
        app.state.storage_root = new_root
        logger.info("SQLite storage backend reinitialized for new root: %s", new_root)
    except Exception as e:
        app.state.storage_backend = None
        app.state.storage_root = new_root
        logger.warning("SQLite storage backend unavailable for new root, using file-only mode: %s", e)

    # Restart status check task with new root and backend
    new_task = asyncio.create_task(
        periodic_status_check(new_root, backend=app.state.storage_backend)
    )
    app.state.status_check_task = new_task
    logger.info("Restarted background process status checker for new storage root")

    # Sync filesystem runs into SQLite for the new backend (non-blocking)
    if app.state.storage_backend is not None:
        def _run_sync():
            try:
                from .services.db_reader import sync_filesystem_to_db
                sync_filesystem_to_db(new_root, app.state.storage_backend)
            except Exception as e:
                logger.warning("Filesystem-to-SQLite sync failed for new root: %s", e)
        new_sync_thread = threading.Thread(target=_run_sync, daemon=True)
        new_sync_thread.start()
        app.state.sync_thread = new_sync_thread


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

    remote_mode = str(os.environ.get("RUNICORN_REMOTE_MODE", "")).lower() in ("1", "true", "yes")
    log_context = build_diagnostics_context(remote_mode=remote_mode)

    # Setup logging
    log_context = setup_logging(session_context=log_context)
    
    # Create FastAPI app
    app = FastAPI(
        title="Runicorn Viewer",
        version=__version__,
        description="Local experiment tracking and visualization platform"
    )
    app.state.log_context = log_context
    app.state.remote_mode = remote_mode
    
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
    
    # Idle shutdown support (remote-mode).
    # When RUNICORN_IDLE_TIMEOUT is set, the viewer will exit after the
    # specified number of seconds with no incoming HTTP requests.
    _idle_timeout = int(os.environ.get("RUNICORN_IDLE_TIMEOUT", "0"))
    app.state.idle_timeout = _idle_timeout
    app.state.last_request_time = _time.time()
    
    if _idle_timeout > 0:
        class _IdleTrackingMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                app.state.last_request_time = _time.time()
                return await call_next(request)
        
        app.add_middleware(_IdleTrackingMiddleware)
    
    # Shutdown signal for WebSocket handlers
    app.state.shutdown_event = asyncio.Event()
    
    # Background task for status checking
    _status_check_task = None

    @app.on_event("startup")
    async def startup_event():
        """Initialize background tasks on app startup."""
        nonlocal _status_check_task
        _status_check_task = asyncio.create_task(
            periodic_status_check(root, backend=app.state.storage_backend)
        )
        app.state.status_check_task = _status_check_task
        logger.info("Started background process status checker")
        
        # Start GPU background collector
        from .services.gpu import GpuCollector
        from ..config import load_user_config
        ucfg = load_user_config()
        app.state.gpu_collector = GpuCollector(
            enabled=bool(ucfg.get("gpu_background_collect", True)),
            interval_sec=float(ucfg.get("gpu_interval_sec", 2)),
            max_duration_h=float(ucfg.get("gpu_max_duration_h", 24)),
        )
        app.state.gpu_collector.start()
        
        # Sync filesystem runs into SQLite (background, non-blocking)
        if app.state.storage_backend is not None:
            def _run_sync():
                try:
                    from .services.db_reader import sync_filesystem_to_db
                    sync_filesystem_to_db(root, app.state.storage_backend)
                except Exception as e:
                    logger.warning(f"Filesystem-to-SQLite sync failed: {e}")
            import threading
            sync_thread = threading.Thread(target=_run_sync, daemon=True)
            sync_thread.start()
            app.state.sync_thread = sync_thread
        
        # Start idle shutdown checker (remote-mode only).
        if app.state.idle_timeout > 0:
            async def _idle_shutdown_check():
                timeout = app.state.idle_timeout
                logger.info(f"Idle shutdown enabled: timeout={timeout}s")
                while True:
                    try:
                        await asyncio.sleep(60)
                        elapsed = _time.time() - app.state.last_request_time
                        if elapsed >= timeout:
                            logger.warning(
                                f"No requests for {elapsed:.0f}s (timeout={timeout}s). "
                                "Shutting down remote-mode viewer."
                            )
                            # os._exit bypasses atexit / finally, which is
                            # appropriate for a nohup-launched remote viewer.
                            os._exit(0)
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Idle shutdown check error: {e}")
                        await asyncio.sleep(30)
            
            asyncio.create_task(_idle_shutdown_check())
            logger.info("Started idle shutdown checker")
        
        # Start periodic dead session cleanup.
        # (viewer_manager is created lazily on the first remote viewer
        # request, so we always start this task and check inside the loop.)
        async def _periodic_session_cleanup():
            while True:
                try:
                    await asyncio.sleep(60)
                    mgr = getattr(app.state, 'viewer_manager', None)
                    if mgr is not None:
                        cleaned = mgr.cleanup_dead_sessions()
                        if cleaned > 0:
                            logger.info(f"Periodic cleanup: removed {cleaned} dead session(s)")
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Session cleanup error: {e}")
                    await asyncio.sleep(30)
        
        asyncio.create_task(_periodic_session_cleanup())
        logger.info("Started periodic session cleanup task")
        
        # Install a SIGINT wrapper so that shutdown_event is set BEFORE
        # uvicorn starts waiting for connections to close.  This lets
        # WebSocket handlers exit their loops promptly on Ctrl+C.
        try:
            original_sigint = signal.getsignal(signal.SIGINT)
            
            def _on_sigint(signum, frame):
                app.state.shutdown_event.set()
                # Chain to uvicorn's original handler so it proceeds with shutdown
                if callable(original_sigint) and original_sigint is not signal.SIG_DFL:
                    original_sigint(signum, frame)
                else:
                    raise KeyboardInterrupt
            
            signal.signal(signal.SIGINT, _on_sigint)
        except (OSError, ValueError):
            # signal.signal() can only be called from the main thread;
            # if we're not there, fall back to on_event("shutdown") only.
            logger.debug("Could not install SIGINT wrapper (not main thread)")
    
    @app.on_event("shutdown") 
    async def shutdown_event():
        """Cleanup background tasks and connections on app shutdown."""
        # Ensure the event is set (covers the case where signal handler
        # was not installed, e.g. non-main thread or SIGTERM shutdown).
        app.state.shutdown_event.set()
        
        # Wait for sync thread to finish before closing the backend,
        # so we don't close SQLite while sync is still writing.
        sync_thread = getattr(app.state, "sync_thread", None)
        if sync_thread is not None and sync_thread.is_alive():
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: sync_thread.join(timeout=5)
            )
            if sync_thread.is_alive():
                logger.warning("Sync thread did not finish within timeout")
        
        # Stop background status checker
        if _status_check_task:
            _status_check_task.cancel()
            try:
                await _status_check_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped background process status checker")
        
        # Stop GPU background collector
        if hasattr(app.state, 'gpu_collector'):
            app.state.gpu_collector.stop()
        
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
        
        # Close SQLite storage backend
        if getattr(app.state, 'storage_backend', None) is not None:
            try:
                app.state.storage_backend.close()
                logger.info("Closed SQLite storage backend")
            except Exception as e:
                logger.warning(f"Failed to close SQLite storage backend: {e}")
    
    # Register v1 API routers (backward compatibility)
    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(runs_router, prefix="/api", tags=["runs"])
    app.include_router(metrics_router, prefix="/api", tags=["metrics"])
    app.include_router(diagnostics_router, prefix="/api", tags=["diagnostics"])
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
    
    # Initialize SQLite storage backend for fast reads
    try:
        from ..storage.backends import SQLiteStorageBackend
        app.state.storage_backend = SQLiteStorageBackend(root)
        logger.info("SQLite storage backend initialized for Viewer reads")
    except Exception as e:
        app.state.storage_backend = None
        logger.warning(f"SQLite storage backend unavailable, using file-only mode: {e}")
    
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


class SPAStaticFiles(StaticFiles):
    """StaticFiles subclass that falls back to index.html for SPA routing."""

    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
            if response.status_code == 404:
                return await super().get_response("index.html", scope)
            return response
        except Exception:
            return await super().get_response("index.html", scope)


def _mount_static_frontend(app: FastAPI) -> None:
    """
    Mount static frontend files if available.
    Uses SPAStaticFiles to support client-side routing (serves index.html
    for any path that doesn't match a real file).
    
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
                app.mount("/", SPAStaticFiles(directory=str(env_dir), html=True), name="frontend")
                return
    except Exception as e:
        logger.debug(f"Could not mount development frontend: {e}")
    
    try:
        # Fallback: serve the packaged webui if present
        ui_dir = Path(__file__).parent.parent / "webui"
        if ui_dir.exists():
            app.mount("/", SPAStaticFiles(directory=str(ui_dir), html=True), name="frontend")
            logger.info(f"Mounted static frontend from: {ui_dir}")
    except Exception as e:
        logger.debug(f"Static frontend not available: {e}")
