"""
DEPRECATED: Synchronous Utility Functions for Storage Backends

After RF-06/RF-13, storage backends are fully synchronous and sdk.py
calls them directly. These wrappers are no longer used by any internal
code and are kept solely for third-party compatibility.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def create_experiment_sync(backend, experiment):
    """DEPRECATED: Call backend.create_experiment() directly."""
    return backend.create_experiment(experiment)


def log_metrics_sync(backend, exp_id: str, metrics):
    """DEPRECATED: Call backend.log_metrics() directly."""
    return backend.log_metrics(exp_id, metrics)


def update_experiment_sync(backend, exp_id: str, updates: Dict[str, Any]):
    """DEPRECATED: Call backend.update_experiment() directly."""
    return backend.update_experiment(exp_id, updates)
