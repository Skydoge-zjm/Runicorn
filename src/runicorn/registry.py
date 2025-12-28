from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .config import get_registry_dir

try:
    import tomllib as _toml
except ModuleNotFoundError:
    import tomli as _toml


_cache_lock = threading.Lock()
_toml_cache: Dict[Path, Tuple[int, Dict[str, Any]]] = {}


def clear_registry_cache() -> None:
    with _cache_lock:
        _toml_cache.clear()


def _load_toml_file(path: Path) -> Dict[str, Any]:
    with path.open("rb") as f:
        data = _toml.load(f)
    if isinstance(data, dict):
        return data
    return {}


def _get_toml_cached(path: Path) -> Dict[str, Any]:
    mtime_ns = path.stat().st_mtime_ns
    with _cache_lock:
        cached = _toml_cache.get(path)
        if cached and cached[0] == mtime_ns:
            return cached[1]

    data = _load_toml_file(path)
    with _cache_lock:
        _toml_cache[path] = (mtime_ns, data)
    return data


def _split_key(key: str) -> List[str]:
    parts = [p for p in (key or "").split("/") if p]
    if not parts:
        raise ValueError("key must be non-empty")
    return parts


def _resolve_registry_file(
    key: str, registry_root: Path
) -> Tuple[Path, List[str], List[Path]]:
    parts = _split_key(key)

    searched: List[Path] = []
    for i in range(len(parts), 0, -1):
        file_path = registry_root.joinpath(*parts[:i]).with_suffix(".toml")
        searched.append(file_path)
        if file_path.exists():
            return file_path, parts[i:], searched

    create_path = registry_root.joinpath(*parts).with_suffix(".toml")
    searched_display = "\n".join(f"- {p}" for p in searched)
    msg = (
        f"Registry key not found: '{key}'\n"
        f"Registry root: {registry_root}\n"
        f"Searched:\n{searched_display}\n"
        f"Create: {create_path}\n"
        f"Minimal template:\nvalue = \"<YOUR_VALUE>\"\n"
    )
    raise KeyError(msg)


def _lookup_subkeys(data: Any, subkeys: List[str], file_path: Path, full_key: str) -> Any:
    cur: Any = data
    for k in subkeys:
        if not isinstance(cur, dict) or k not in cur:
            raise KeyError(
                f"Registry key not found: '{full_key}'\n"
                f"File: {file_path}\n"
                f"Missing subkey: {k}"
            )
        cur = cur[k]
    return cur


def get_config(key: str) -> Any:
    registry_root = get_registry_dir()
    file_path, rest, _searched = _resolve_registry_file(key, registry_root)
    data = _get_toml_cached(file_path)

    if not rest:
        if "value" not in data:
            raise KeyError(
                f"Registry key resolved but missing default field 'value': '{key}'\n"
                f"File: {file_path}\n"
                f"Add a line like: value = \"<YOUR_VALUE>\"\n"
            )
        return data["value"]

    return _lookup_subkeys(data, rest, file_path, key)
