"""TOML key-value registry.

Reads values from TOML files under the registry directory.
Migrated from the top-level registry.py into the unified config package.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, List, Tuple

from .paths import get_registry_dir
from ._toml import load_toml_cached, clear_toml_cache


def clear_registry_cache() -> None:
    clear_toml_cache()


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
    data = load_toml_cached(file_path)

    if not rest:
        if "value" not in data:
            raise KeyError(
                f"Registry key resolved but missing default field 'value': '{key}'\n"
                f"File: {file_path}\n"
                f"Add a line like: value = \"<YOUR_VALUE>\"\n"
            )
        return data["value"]

    return _lookup_subkeys(data, rest, file_path, key)
