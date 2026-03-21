"""API rate limit configuration management."""
from __future__ import annotations

import json
import logging
from importlib.resources import files
from pathlib import Path
from typing import Any, Dict

from .paths import _config_root_dir

logger = logging.getLogger(__name__)


def get_rate_limit_config() -> Dict[str, Any]:
    """
    Get rate limit configuration.

    Priority:
    1. User config directory (%APPDATA%/Runicorn/rate_limits.json)
    2. Package defaults directory (config/_defaults/rate_limits.json)
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

    # Priority 2: Check package defaults directory (bundled with code)
    try:
        config = json.loads(
            files("runicorn.config").joinpath("_defaults", "rate_limits.json").read_text(
                encoding="utf-8"
            )
        )

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
