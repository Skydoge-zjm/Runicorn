from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, Tuple


def stat_fingerprint(path: Path) -> Dict[str, Any]:
    st = path.stat()
    return {
        "size_bytes": int(st.st_size),
        "mtime": float(st.st_mtime),
    }


def dir_stat_fingerprint(path: Path) -> Dict[str, Any]:
    st = path.stat()
    file_count = 0
    total_size = 0

    for root, _, files in os.walk(path):
        for fn in files:
            fp = Path(root) / fn
            try:
                s = fp.stat()
            except OSError:
                continue
            file_count += 1
            total_size += int(s.st_size)

    return {
        "mtime": float(st.st_mtime),
        "file_count": int(file_count),
        "total_size_bytes": int(total_size),
    }


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_fingerprint(path: Path) -> Tuple[str, str]:
    if path.is_file():
        return "sha256", sha256_file(path)
    raise ValueError("content_fingerprint supports files only")
