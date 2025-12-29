"""
Archive utilities for content-addressable storage.

Provides functions to archive files and directories using SHA256-based
deduplication. Files are stored in a blob store, directories are stored
as manifests pointing to blobs.

Storage structure:
    archive/
    ├── blobs/                    # Content-addressable file storage
    │   └── {sha256[:2]}/{sha256}
    ├── manifests/                # Directory manifests
    │   └── {category}/{fp[:2]}/{fp}.json
    └── outputs/
        └── rolling/              # Rolling mode (per-run, no dedup)
            └── {run_id}/...
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .fingerprint import sha256_file
from .blob_store import store_blob, get_blob_path


def _hash_manifest(entries: List[Tuple[str, str]]) -> str:
    """
    Compute a hash for a list of (rel_path, sha256) entries.
    
    This creates a deterministic fingerprint for a directory based on
    its file contents and structure.
    """
    h = hashlib.sha256()
    for rel, sha in sorted(entries):
        h.update(rel.encode("utf-8"))
        h.update(b"\x00")
        h.update(sha.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def archive_file(src: Path, archive_root: Path, *, category: str) -> Dict[str, Any]:
    """
    Archive a single file using content-addressable storage.
    
    The file is stored in the blob store by its SHA256 hash. If a file
    with the same content already exists, no copy is made (deduplication).
    
    Args:
        src: Path to the source file.
        archive_root: Root directory for archives.
        category: Category name (e.g., "code", "datasets", "pretrained").
    
    Returns:
        Dictionary with fingerprint info and blob path.
    
    Raises:
        ValueError: If src is not a file.
    """
    src = Path(src)
    if not src.is_file():
        raise ValueError(f"archive_file expects a file, got: {src}")
    
    blob_root = archive_root / "blobs"
    sha = store_blob(src, blob_root)
    blob_path = get_blob_path(sha, blob_root)
    
    return {
        "fingerprint_kind": "sha256",
        "fingerprint": sha,
        "archive_path": str(blob_path),
    }


def archive_dir(src: Path, archive_root: Path, *, category: str) -> Dict[str, Any]:
    """
    Archive a directory using content-addressable storage.
    
    All files are stored in the blob store (deduplicated). A manifest file
    is created that maps relative paths to blob hashes.
    
    Args:
        src: Path to the source directory.
        archive_root: Root directory for archives.
        category: Category name (e.g., "datasets", "pretrained", "outputs").
    
    Returns:
        Dictionary with fingerprint info and manifest path.
    
    Raises:
        ValueError: If src is not a directory.
    """
    src = Path(src)
    if not src.is_dir():
        raise ValueError(f"archive_dir expects a directory, got: {src}")
    
    blob_root = archive_root / "blobs"
    manifest_root = archive_root / "manifests"
    
    # Scan directory and store files to blob store
    files: Dict[str, Dict[str, Any]] = {}
    entries_for_hash: List[Tuple[str, str]] = []
    total_size = 0
    
    for dirpath, _, filenames in os.walk(src):
        dp = Path(dirpath)
        for fn in filenames:
            file_path = dp / fn
            rel_path = file_path.relative_to(src).as_posix()
            
            try:
                sha = store_blob(file_path, blob_root)
                size = file_path.stat().st_size
            except OSError:
                continue
            
            files[rel_path] = {
                "sha256": sha,
                "size_bytes": size,
            }
            entries_for_hash.append((rel_path, sha))
            total_size += size
    
    # Compute manifest fingerprint
    fingerprint = _hash_manifest(entries_for_hash)
    
    # Save manifest if not exists
    manifest_path = manifest_root / category / fingerprint[:2] / f"{fingerprint}.json"
    if not manifest_path.exists():
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_data = {
            "created_at": time.time(),
            "source_path": str(src),
            "fingerprint": fingerprint,
            "total_size_bytes": total_size,
            "file_count": len(files),
            "files": files,
        }
        
        # Atomic write
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=manifest_path.parent,
            prefix=f".{fingerprint[:8]}_",
            suffix=".json.tmp"
        )
        try:
            os.close(tmp_fd)
            Path(tmp_path).write_text(
                json.dumps(manifest_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            Path(tmp_path).replace(manifest_path)
        finally:
            try:
                if Path(tmp_path).exists():
                    Path(tmp_path).unlink()
            except OSError:
                pass
    
    return {
        "fingerprint_kind": "sha256_manifest",
        "fingerprint": fingerprint,
        "archive_path": str(manifest_path),  # For API compatibility
        "manifest_path": str(manifest_path),
        "file_count": len(files),
        "total_size_bytes": total_size,
    }


# =============================================================================
# Rolling mode functions (no cross-run deduplication)
# =============================================================================

def _safe_leaf(name: str) -> str:
    """Sanitize a name for use as a filename component."""
    s = "".join((c if c.isalnum() or c in "-_." else "_") for c in (name or ""))
    return s[:80] if len(s) > 80 else s


def archive_file_overwrite(
    src: Path,
    archive_root: Path,
    *,
    category: str,
    run_id: str,
    key: str,
) -> Dict[str, Any]:
    """
    Archive a file in rolling mode (overwrites previous version).
    
    Used for files like `last.pth` that are repeatedly overwritten during
    training. Each run has its own copy, no cross-run deduplication.
    
    Args:
        src: Path to the source file.
        archive_root: Root directory for archives.
        category: Category name (e.g., "outputs").
        run_id: Run identifier.
        key: Unique key for this file within the run.
    
    Returns:
        Dictionary with fingerprint info and archive path.
    """
    src = Path(src)
    if not src.is_file():
        raise ValueError(f"archive_file_overwrite expects a file, got: {src}")
    
    sha = sha256_file(src)
    
    hid = hashlib.sha1(key.encode("utf-8")).hexdigest()
    dst_dir = archive_root / category / "rolling" / _safe_leaf(run_id)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"{hid}_{_safe_leaf(src.name)}"
    
    # Atomic write
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=dst_dir,
        prefix=f".{dst.name}_",
        suffix=".tmp"
    )
    try:
        os.close(tmp_fd)
        shutil.copy2(src, tmp_path)
        Path(tmp_path).replace(dst)
    finally:
        try:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()
        except OSError:
            pass
    
    return {
        "fingerprint_kind": "sha256",
        "fingerprint": sha,
        "archive_path": str(dst),
    }


def archive_file_overwrite_stat(
    src: Path,
    archive_root: Path,
    *,
    category: str,
    run_id: str,
    key: str,
) -> Dict[str, Any]:
    """
    Archive a file in rolling mode with stat-based fingerprint.
    
    Used for log files where content hash is expensive. Uses size/mtime
    as a lightweight fingerprint.
    
    Args:
        src: Path to the source file.
        archive_root: Root directory for archives.
        category: Category name (e.g., "outputs").
        run_id: Run identifier.
        key: Unique key for this file within the run.
    
    Returns:
        Dictionary with fingerprint info and archive path.
    """
    src = Path(src)
    if not src.is_file():
        raise ValueError(f"archive_file_overwrite_stat expects a file, got: {src}")
    
    st = src.stat()
    fp = json.dumps(
        {"size_bytes": int(st.st_size), "mtime": float(st.st_mtime)},
        ensure_ascii=False,
        sort_keys=True,
    )
    
    hid = hashlib.sha1(key.encode("utf-8")).hexdigest()
    dst_dir = archive_root / category / "rolling" / _safe_leaf(run_id)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"{hid}_{_safe_leaf(src.name)}"
    
    # Atomic write
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=dst_dir,
        prefix=f".{dst.name}_",
        suffix=".tmp"
    )
    try:
        os.close(tmp_fd)
        shutil.copy2(src, tmp_path)
        Path(tmp_path).replace(dst)
    finally:
        try:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()
        except OSError:
            pass
    
    return {
        "fingerprint_kind": "stat",
        "fingerprint": fp,
        "archive_path": str(dst),
        "size_bytes": int(st.st_size),
        "mtime": float(st.st_mtime),
    }


def archive_dir_overwrite(
    src: Path,
    archive_root: Path,
    *,
    category: str,
    run_id: str,
    key: str,
) -> Dict[str, Any]:
    """
    Archive a directory in rolling mode (overwrites previous version).
    
    Used for checkpoint directories that are repeatedly overwritten.
    Each run has its own copy, no cross-run deduplication.
    
    Args:
        src: Path to the source directory.
        archive_root: Root directory for archives.
        category: Category name (e.g., "outputs").
        run_id: Run identifier.
        key: Unique key for this directory within the run.
    
    Returns:
        Dictionary with fingerprint info and archive path.
    """
    src = Path(src)
    if not src.is_dir():
        raise ValueError(f"archive_dir_overwrite expects a directory, got: {src}")
    
    # Compute manifest hash for fingerprint
    entries: List[Tuple[str, str]] = []
    total_size = 0
    file_count = 0
    
    for dirpath, _, filenames in os.walk(src):
        dp = Path(dirpath)
        for fn in filenames:
            fp = dp / fn
            rel = fp.relative_to(src).as_posix()
            try:
                sha = sha256_file(fp)
                total_size += fp.stat().st_size
            except OSError:
                continue
            entries.append((rel, sha))
            file_count += 1
    
    manifest_hash = _hash_manifest(entries)
    
    hid = hashlib.sha1(key.encode("utf-8")).hexdigest()
    dst_parent = archive_root / category / "rolling" / _safe_leaf(run_id)
    dst_parent.mkdir(parents=True, exist_ok=True)
    dst_root = dst_parent / f"{hid}_{_safe_leaf(src.name)}"
    
    # Copy to temp dir first, then atomic rename
    tmp_dir = Path(tempfile.mkdtemp(dir=dst_parent, prefix=f".{dst_root.name}_tmp_"))
    try:
        for rel, _ in entries:
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
        except OSError:
            pass
    
    return {
        "fingerprint_kind": "sha256_manifest",
        "fingerprint": manifest_hash,
        "archive_path": str(dst_root),
        "file_count": file_count,
        "total_size_bytes": total_size,
    }
