from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)


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


def load_user_config() -> Dict[str, Any]:
    path = get_config_file_path()
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_user_config(update: Dict[str, Any]) -> None:
    path = get_config_file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        cur = load_user_config()
        cur.update(update or {})
        path.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # Silent failure to avoid breaking training loops; user can retry via CLI
        pass


def set_user_root_dir(path_like: str) -> Path:
    p = Path(path_like).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    save_user_config({"user_root_dir": str(p)})
    return p


def get_user_root_dir() -> Optional[Path]:
    cfg = load_user_config()
    p = cfg.get("user_root_dir")
    if not p:
        return None
    try:
        return Path(p).expanduser().resolve()
    except Exception:
        try:
            return Path(p)
        except Exception:
            return None


def save_ssh_connections(connections: list[Dict[str, Any]]) -> None:
    """Save SSH connection configurations with encryption."""
    from .security.credentials import get_credential_manager
    
    manager = get_credential_manager()
    encrypted_connections = [
        manager.encrypt_config(conn) for conn in connections
    ]
    save_user_config({"ssh_connections": encrypted_connections})


def get_ssh_connections() -> list[Dict[str, Any]]:
    """Get saved SSH connection configurations with decryption."""
    from .security.credentials import get_credential_manager
    
    cfg = load_user_config()
    connections = cfg.get("ssh_connections", [])
    
    # Decrypt sensitive fields
    manager = get_credential_manager()
    return [
        manager.decrypt_config(conn) for conn in connections
    ]


def add_ssh_connection(connection: Dict[str, Any]) -> None:
    """Add or update an SSH connection configuration."""
    connections = get_ssh_connections()
    
    # Find and update if exists (by host+port+username)
    key = f"{connection.get('host')}:{connection.get('port', 22)}@{connection.get('username')}"
    connection['key'] = key
    
    # Remove existing connection with same key
    connections = [c for c in connections if c.get('key') != key]
    
    # Add new/updated connection
    connections.append(connection)
    
    # Keep only last 10 connections
    connections = connections[-10:]
    
    save_ssh_connections(connections)


def remove_ssh_connection(key: str) -> None:
    """Remove an SSH connection configuration."""
    connections = get_ssh_connections()
    connections = [c for c in connections if c.get('key') != key]
    save_ssh_connections(connections)


def get_rate_limit_config() -> Dict[str, Any]:
    """
    Get rate limit configuration.
    
    Priority:
    1. User config directory (%APPDATA%/Runicorn/rate_limits.json)
    2. Package config directory (src/runicorn/config/rate_limits.json)
    3. Fallback defaults
    """
    # Priority 1: Check user config directory (runtime, user-editable)
    user_config_dir = _config_root_dir()
    user_rate_limits_file = user_config_dir / 'rate_limits.json'
    
    if user_rate_limits_file.exists():
        try:
            with open(user_rate_limits_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load user rate limits config: {e}")
    
    # Priority 2: Check package config directory (bundled with code)
    rate_limits_file = Path(__file__).parent / 'config' / 'rate_limits.json'
    
    # If not found, try the parent directory
    if not rate_limits_file.exists():
        rate_limits_file = Path(__file__).parent / 'rate_limits.json'
    
    if rate_limits_file.exists():
        try:
            with open(rate_limits_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
                # Copy to user directory for future edits
                try:
                    user_config_dir.mkdir(parents=True, exist_ok=True)
                    with open(user_rate_limits_file, 'w', encoding='utf-8') as uf:
                        json.dump(config, uf, indent=2, ensure_ascii=False)
                    logger.info(f"Copied rate limits config to user directory: {user_rate_limits_file}")
                except Exception as copy_error:
                    logger.debug(f"Could not copy rate limits to user dir: {copy_error}")
                
                return config
        except Exception as e:
            logger.warning(f"Failed to load package rate limits config: {e}")
    
    # Priority 3: Return sensible defaults
    return {
        "_comment": "High limits for local-only API",
        "default": {
            "max_requests": 6000,
            "window_seconds": 60,
            "burst_size": None
        },
        "endpoints": {},
        "settings": {
            "enable_rate_limiting": False,
            "log_violations": True,
            "whitelist_localhost": False
        }
    }


def save_rate_limit_config(config: Dict[str, Any]) -> None:
    """
    Save rate limit configuration to user directory.
    
    This ensures the configuration is stored in a user-writable location
    and shared between command-line and desktop app.
    """
    # Save to user config directory
    user_config_dir = _config_root_dir()
    rate_limits_file = user_config_dir / 'rate_limits.json'
    
    try:
        user_config_dir.mkdir(parents=True, exist_ok=True)
        with open(rate_limits_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"Rate limit config saved to {rate_limits_file}")
    except Exception as e:
        logger.error(f"Failed to save rate limit config: {e}")
