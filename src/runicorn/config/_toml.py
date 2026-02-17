"""Shared TOML loading utilities with mtime-based caching.

Used by config/registry.py and config/rnconfig.py to avoid duplicating
TOML load + thread-safe cache logic.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, Tuple

try:
    import tomllib as _toml
except ModuleNotFoundError:
    import tomli as _toml


_cache_lock = threading.Lock()
_toml_cache: Dict[Path, Tuple[int, Dict[str, Any]]] = {}


def load_toml(path: Path) -> Dict[str, Any]:
    """Load a TOML file, returning empty dict if file doesn't exist."""
    if not path.exists():
        return {}
    with path.open("rb") as f:
        data = _toml.load(f)
    return data if isinstance(data, dict) else {}


def load_toml_cached(path: Path) -> Dict[str, Any]:
    """Load a TOML file with mtime-based cache (thread-safe)."""
    if not path.exists():
        return {}
    mtime_ns = path.stat().st_mtime_ns
    with _cache_lock:
        cached = _toml_cache.get(path)
        if cached and cached[0] == mtime_ns:
            return cached[1]

    data = load_toml(path)
    with _cache_lock:
        _toml_cache[path] = (mtime_ns, data)
    return data


def clear_toml_cache() -> None:
    """Clear all cached TOML data."""
    with _cache_lock:
        _toml_cache.clear()
