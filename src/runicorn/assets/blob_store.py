"""
Blob Store - Content-Addressable Storage for files.

All files are stored by their SHA256 hash, enabling automatic deduplication
across directories and runs.

Storage structure:
    blobs/
    ├── a4/
    │   └── a47eb79188cdc67a601ebf32...  # file content (named by sha256)
    └── 3f/
        └── 3f8c2a1b9e4d7f...
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any

from .fingerprint import sha256_file


def get_blob_path(sha256: str, blob_root: Path) -> Path:
    """
    Get the storage path for a blob by its SHA256 hash.
    
    Args:
        sha256: The SHA256 hash of the file content.
        blob_root: Root directory of the blob store.
    
    Returns:
        Path where the blob is (or would be) stored.
    """
    return blob_root / sha256[:2] / sha256


def blob_exists(sha256: str, blob_root: Path) -> bool:
    """
    Check if a blob exists in the store.
    
    Args:
        sha256: The SHA256 hash to check.
        blob_root: Root directory of the blob store.
    
    Returns:
        True if the blob exists, False otherwise.
    """
    return get_blob_path(sha256, blob_root).exists()


def store_blob(src_path: Path, blob_root: Path) -> str:
    """
    Store a file in the blob store.
    
    If a blob with the same content already exists, the file is not copied
    (deduplication). Returns the SHA256 hash of the file.
    
    Args:
        src_path: Path to the source file.
        blob_root: Root directory of the blob store.
    
    Returns:
        SHA256 hash of the stored file.
    
    Raises:
        ValueError: If src_path is not a file.
    """
    src_path = Path(src_path)
    if not src_path.is_file():
        raise ValueError(f"store_blob expects a file, got: {src_path}")
    
    sha = sha256_file(src_path)
    blob_path = get_blob_path(sha, blob_root)
    
    if blob_path.exists():
        # Already stored, skip copy (deduplication)
        return sha
    
    # Atomic write: copy to temp file first, then rename
    blob_path.parent.mkdir(parents=True, exist_ok=True)
    
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=blob_path.parent,
        prefix=f".{sha[:8]}_",
        suffix=".tmp"
    )
    try:
        os.close(tmp_fd)
        shutil.copy2(src_path, tmp_path)
        Path(tmp_path).replace(blob_path)
    finally:
        # Clean up temp file if it still exists
        try:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()
        except OSError:
            pass
    
    return sha


def read_blob(sha256: str, blob_root: Path) -> bytes:
    """
    Read the content of a blob.
    
    Args:
        sha256: The SHA256 hash of the blob.
        blob_root: Root directory of the blob store.
    
    Returns:
        The file content as bytes.
    
    Raises:
        FileNotFoundError: If the blob does not exist.
    """
    blob_path = get_blob_path(sha256, blob_root)
    if not blob_path.exists():
        raise FileNotFoundError(f"Blob not found: {sha256}")
    return blob_path.read_bytes()


def get_blob_stats(blob_root: Path) -> Dict[str, Any]:
    """
    Get statistics about the blob store.
    
    Args:
        blob_root: Root directory of the blob store.
    
    Returns:
        Dictionary with blob_count and total_size_bytes.
    """
    if not blob_root.exists():
        return {"blob_count": 0, "total_size_bytes": 0}
    
    blob_count = 0
    total_size = 0
    
    for prefix_dir in blob_root.iterdir():
        if not prefix_dir.is_dir():
            continue
        for blob_file in prefix_dir.iterdir():
            if blob_file.is_file() and not blob_file.name.startswith("."):
                blob_count += 1
                try:
                    total_size += blob_file.stat().st_size
                except OSError:
                    pass
    
    return {
        "blob_count": blob_count,
        "total_size_bytes": total_size,
    }
