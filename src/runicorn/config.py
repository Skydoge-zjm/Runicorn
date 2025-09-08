from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


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
