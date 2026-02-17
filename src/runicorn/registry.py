"""Compatibility shim — real implementation lives in config.registry."""
from __future__ import annotations

from .config.registry import get_config, clear_registry_cache

__all__ = ["get_config", "clear_registry_cache"]
