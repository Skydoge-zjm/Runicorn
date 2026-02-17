"""Compatibility shim — real implementation lives in config.rnconfig."""
from __future__ import annotations

from ..config.rnconfig import get_effective_rnconfig, load_effective_rnconfig

__all__ = [
    "get_effective_rnconfig",
    "load_effective_rnconfig",
]
