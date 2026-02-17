"""
Synchronous Utility Functions for Storage Backends

After RF-06, storage backends are fully synchronous.
These thin wrappers are kept for backward compatibility with sdk.py
call-sites and will be inlined in a future cleanup.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def create_experiment_sync(backend, experiment):
    """Create experiment (direct call, backends are now sync)."""
    return backend.create_experiment(experiment)


def log_metrics_sync(backend, exp_id: str, metrics):
    """Log metrics (direct call, backends are now sync)."""
    return backend.log_metrics(exp_id, metrics)


def update_experiment_sync(backend, exp_id: str, updates: Dict[str, Any]):
    """Update experiment (direct call, backends are now sync)."""
    return backend.update_experiment(exp_id, updates)
