"""User configuration (config.json) read/write."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .paths import get_config_file_path

logger = logging.getLogger(__name__)


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
        for key, value in (update or {}).items():
            if value is None:
                cur.pop(key, None)
            else:
                cur[key] = value
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
