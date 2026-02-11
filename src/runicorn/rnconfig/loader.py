from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..config import get_rnconfig_file_path
from ..workspace import get_workspace_root

try:
    import tomllib as _toml
except ModuleNotFoundError:
    import tomli as _toml


_cache_lock = threading.Lock()
_effective_cache: Dict[Tuple[Path, Path], Tuple[Tuple[int, int], Dict[str, Any]]] = {}


def _load_toml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as f:
        data = _toml.load(f)
    if isinstance(data, dict):
        return data
    return {}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = dict(base)
    for k, v in (override or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_effective_rnconfig(workspace_root: Optional[str] = None) -> Dict[str, Any]:
    ws_root = get_workspace_root(workspace_root)
    user_path = get_rnconfig_file_path()
    project_path = ws_root / "rnconfig.toml"

    user_mtime = user_path.stat().st_mtime_ns if user_path.exists() else 0
    project_mtime = project_path.stat().st_mtime_ns if project_path.exists() else 0

    key = (user_path, project_path)
    stamp = (user_mtime, project_mtime)

    with _cache_lock:
        cached = _effective_cache.get(key)
        if cached and cached[0] == stamp:
            return cached[1]

    user_cfg = _load_toml(user_path)
    project_cfg = _load_toml(project_path)
    merged = _deep_merge(user_cfg, project_cfg)

    with _cache_lock:
        _effective_cache[key] = (stamp, merged)

    return merged


def get_effective_rnconfig(workspace_root: Optional[str] = None) -> Dict[str, Any]:
    return load_effective_rnconfig(workspace_root)
