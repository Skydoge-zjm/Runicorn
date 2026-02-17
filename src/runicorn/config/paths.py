"""Cross-platform configuration path resolution.

All functions that determine *where* config files live on disk.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _config_root_dir() -> Path:
    """Return the per-user configuration directory for Runicorn.

    - Windows: %APPDATA%/Runicorn
    - macOS  : ~/Library/Application Support/Runicorn
    - Linux  : ~/.config/runicorn
    """
    try:
        if os.name == "nt":
            base = os.environ.get("APPDATA")
            if not base:
                base = str(Path.home() / "AppData" / "Roaming")
            return Path(base) / "Runicorn"
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "Runicorn"
        # Linux or others
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else (Path.home() / ".config")
        return base / "runicorn"
    except Exception:
        # Best-effort fallback
        return Path.home() / ".runicorn_config"


def get_config_file_path() -> Path:
    return _config_root_dir() / "config.json"


def get_rnconfig_file_path() -> Path:
    return _config_root_dir() / "rnconfig.toml"


def get_registry_dir() -> Path:
    path = _config_root_dir() / "registry"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return path


def get_connections_file_path() -> Path:
    """Return path to saved connections file."""
    return _config_root_dir() / "connections.json"


def get_known_hosts_file_path() -> Path:
    """Return path to the Runicorn-managed OpenSSH known_hosts file."""
    path = _config_root_dir() / "known_hosts"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return path
