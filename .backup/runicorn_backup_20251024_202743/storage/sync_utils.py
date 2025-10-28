"""
Synchronous Utility Functions for Storage Backends

Provides synchronous wrappers for async storage operations to avoid
event loop issues in synchronous contexts like SDK initialization.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def run_async_safe(coro):
    """
    Safely run an async coroutine in a synchronous context.
    
    This handles various event loop scenarios:
    1. No event loop: Create a new one
    2. Event loop exists but not running: Use it
    3. Event loop running: Cannot run synchronously (returns None and logs warning)
    
    Args:
        coro: Async coroutine to run
        
    Returns:
        Result of the coroutine, or None if cannot run synchronously
    """
    try:
        # Try to get existing event loop
        try:
            loop = asyncio.get_running_loop()
            # We're already in an async context, cannot run synchronously
            logger.warning("Cannot run async operation synchronously within running event loop")
            return None
        except RuntimeError:
            # No running loop, safe to proceed
            pass
        
        # Create new event loop and run
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(coro)
            return result
        finally:
            loop.close()
            asyncio.set_event_loop(None)
            
    except Exception as e:
        logger.error(f"Failed to run async operation synchronously: {e}")
        return None


def create_experiment_sync(backend, experiment):
    """Synchronous wrapper for create_experiment."""
    from .models import ExperimentRecord
    
    async def _create():
        return await backend.create_experiment(experiment)
    
    return run_async_safe(_create())


def log_metrics_sync(backend, exp_id: str, metrics):
    """Synchronous wrapper for log_metrics."""
    async def _log():
        return await backend.log_metrics(exp_id, metrics)
    
    return run_async_safe(_log())


def update_experiment_sync(backend, exp_id: str, updates: Dict[str, Any]):
    """Synchronous wrapper for update_experiment."""
    async def _update():
        return await backend.update_experiment(exp_id, updates)
    
    return run_async_safe(_update())
