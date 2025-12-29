from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .fingerprint import sha256_file


def _hash_manifest(entries: List[Tuple[str, str]]) -> str:
    import hashlib

    h = hashlib.sha256()
    for rel, sha in entries:
        h.update(rel.encode("utf-8"))
        h.update(b"\x00")
        h.update(sha.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def archive_file(src: Path, archive_root: Path, *, category: str) -> Dict[str, Any]:
    src = Path(src)
    if not src.is_file():
        raise ValueError("archive_file expects a file")

    sha = sha256_file(src)
    dst = archive_root / category / sha[:2] / sha
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not dst.exists():
        shutil.copy2(src, dst)

    return {
        "fingerprint_kind": "sha256",
        "fingerprint": sha,
        "archive_path": str(dst),
    }


def archive_dir(src: Path, archive_root: Path, *, category: str) -> Dict[str, Any]:
    src = Path(src)
    if not src.is_dir():
        raise ValueError("archive_dir expects a directory")

    entries: List[Tuple[str, str]] = []
    total_bytes = 0
    file_count = 0

    for dirpath, _, filenames in os.walk(src):
        dp = Path(dirpath)
        for fn in filenames:
            fp = dp / fn
            rel = fp.relative_to(src).as_posix()
            sha = sha256_file(fp)
            entries.append((rel, sha))
            try:
                total_bytes += int(fp.stat().st_size)
            except OSError:
                pass
            file_count += 1

    entries.sort(key=lambda x: x[0])
    manifest_hash = _hash_manifest(entries)

    dst_root = archive_root / category / manifest_hash[:2] / manifest_hash
    dst_root.mkdir(parents=True, exist_ok=True)

    marker = dst_root / ".complete"
    if not marker.exists():
        for rel, _sha in entries:
            src_fp = src / rel
            dst_fp = dst_root / rel
            dst_fp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_fp, dst_fp)
        marker.write_text("ok\n", encoding="utf-8")

    return {
        "fingerprint_kind": "sha256_manifest",
        "fingerprint": manifest_hash,
        "archive_path": str(dst_root),
        "file_count": int(file_count),
        "total_size_bytes": int(total_bytes),
    }


def _safe_leaf(name: str) -> str:
    s = "".join((c if c.isalnum() or c in "-_." else "_") for c in (name or ""))
    return s[:80] if len(s) > 80 else s


def archive_file_overwrite(src: Path, archive_root: Path, *, category: str, run_id: str, key: str) -> Dict[str, Any]:
    import hashlib

    src = Path(src)
    if not src.is_file():
        raise ValueError("archive_file_overwrite expects a file")

    sha = sha256_file(src)

    hid = hashlib.sha1(key.encode("utf-8")).hexdigest()
    dst_dir = archive_root / category / "rolling" / _safe_leaf(run_id)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"{hid}_{_safe_leaf(src.name)}"

    tmp_fd, tmp_path = tempfile.mkstemp(dir=dst_dir, prefix=f".{dst.name}_", suffix=".tmp", text=False)
    try:
        os.close(tmp_fd)
        shutil.copy2(src, tmp_path)
        Path(tmp_path).replace(dst)
    finally:
        try:
            p = Path(tmp_path)
            if p.exists():
                p.unlink()
        except Exception:
            pass

    return {
        "fingerprint_kind": "sha256",
        "fingerprint": sha,
        "archive_path": str(dst),
    }


def archive_file_overwrite_stat(src: Path, archive_root: Path, *, category: str, run_id: str, key: str) -> Dict[str, Any]:
    import hashlib
    import json

    src = Path(src)
    if not src.is_file():
        raise ValueError("archive_file_overwrite_stat expects a file")

    st = src.stat()
    fp = json.dumps(
        {
            "size_bytes": int(st.st_size),
            "mtime": float(st.st_mtime),
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    hid = hashlib.sha1(key.encode("utf-8")).hexdigest()
    dst_dir = archive_root / category / "rolling" / _safe_leaf(run_id)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"{hid}_{_safe_leaf(src.name)}"

    tmp_fd, tmp_path = tempfile.mkstemp(dir=dst_dir, prefix=f".{dst.name}_", suffix=".tmp", text=False)
    try:
        os.close(tmp_fd)
        shutil.copy2(src, tmp_path)
        Path(tmp_path).replace(dst)
    finally:
        try:
            p = Path(tmp_path)
            if p.exists():
                p.unlink()
        except Exception:
            pass

    return {
        "fingerprint_kind": "stat",
        "fingerprint": fp,
        "archive_path": str(dst),
        "size_bytes": int(st.st_size),
        "mtime": float(st.st_mtime),
    }


def archive_dir_overwrite(src: Path, archive_root: Path, *, category: str, run_id: str, key: str) -> Dict[str, Any]:
    import hashlib

    src = Path(src)
    if not src.is_dir():
        raise ValueError("archive_dir_overwrite expects a directory")

    entries: List[Tuple[str, str]] = []
    total_bytes = 0
    file_count = 0

    for dirpath, _, filenames in os.walk(src):
        dp = Path(dirpath)
        for fn in filenames:
            fp = dp / fn
            rel = fp.relative_to(src).as_posix()
            sha = sha256_file(fp)
            entries.append((rel, sha))
            try:
                total_bytes += int(fp.stat().st_size)
            except OSError:
                pass
            file_count += 1

    entries.sort(key=lambda x: x[0])
    manifest_hash = _hash_manifest(entries)

    hid = hashlib.sha1(key.encode("utf-8")).hexdigest()
    dst_parent = archive_root / category / "rolling" / _safe_leaf(run_id)
    dst_parent.mkdir(parents=True, exist_ok=True)
    dst_root = dst_parent / f"{hid}_{_safe_leaf(src.name)}"

    tmp_dir = Path(tempfile.mkdtemp(dir=dst_parent, prefix=f".{dst_root.name}_tmp_"))
    try:
        for rel, _sha in entries:
            src_fp = src / rel
            dst_fp = tmp_dir / rel
            dst_fp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_fp, dst_fp)
        (tmp_dir / ".complete").write_text("ok\n", encoding="utf-8")

        if dst_root.exists():
            shutil.rmtree(dst_root, ignore_errors=True)
        shutil.move(str(tmp_dir), str(dst_root))
    finally:
        try:
            if tmp_dir.exists() and tmp_dir != dst_root:
                shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    return {
        "fingerprint_kind": "sha256_manifest",
        "fingerprint": manifest_hash,
        "archive_path": str(dst_root),
        "file_count": int(file_count),
        "total_size_bytes": int(total_bytes),
    }
