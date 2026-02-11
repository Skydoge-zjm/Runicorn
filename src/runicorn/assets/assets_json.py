from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from filelock import FileLock


def ensure_assets_file(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    data: Dict[str, Any] = {
        "code": {},
        "config": {},
        "datasets": [],
        "pretrained": [],
        "outputs": [],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_assets(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def update_assets_atomic(path: Path, lock: FileLock, updater) -> Dict[str, Any]:
    import os
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)

    with lock:
        data: Dict[str, Any]
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        else:
            data = {}

        new_data = updater(data) or data

        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.stem}_",
            suffix=".json.tmp",
            text=False,
        )
        try:
            os.close(tmp_fd)
            Path(tmp_path).write_text(json.dumps(new_data, ensure_ascii=False, indent=2), encoding="utf-8")
            Path(tmp_path).replace(path)
        finally:
            try:
                p = Path(tmp_path)
                if p.exists():
                    p.unlink()
            except Exception:
                pass

        return new_data


def write_assets_atomic(path: Path, lock: FileLock, data: Dict[str, Any]) -> None:
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)

    with lock:
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.stem}_",
            suffix=".json.tmp",
            text=False,
        )
        try:
            import os

            os.close(tmp_fd)
            Path(tmp_path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            Path(tmp_path).replace(path)
        finally:
            try:
                p = Path(tmp_path)
                if p.exists():
                    p.unlink()
            except Exception:
                pass
