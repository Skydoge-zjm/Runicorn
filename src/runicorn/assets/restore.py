"""
Restore utilities for CAS-based archives.

Provides functions to restore directories from manifests and export to zip files.
"""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict

from .blob_store import get_blob_path


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    """
    Load a manifest file.
    
    Args:
        manifest_path: Path to the manifest JSON file.
    
    Returns:
        Parsed manifest dictionary.
    
    Raises:
        FileNotFoundError: If manifest file does not exist.
        json.JSONDecodeError: If manifest is not valid JSON.
    """
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def restore_from_manifest(
    manifest_path: Path,
    blob_root: Path,
    target_dir: Path,
    *,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Restore a directory from a manifest file.
    
    Args:
        manifest_path: Path to the manifest JSON file.
        blob_root: Root directory of the blob store.
        target_dir: Directory to restore files into.
        overwrite: If True, overwrite existing files.
    
    Returns:
        Dictionary with restore statistics.
    
    Raises:
        FileNotFoundError: If manifest or required blobs are missing.
        FileExistsError: If target_dir exists and overwrite is False.
    """
    if target_dir.exists() and not overwrite:
        raise FileExistsError(f"Target directory already exists: {target_dir}")
    
    manifest = load_manifest(manifest_path)
    files = manifest.get("files", {})
    
    restored_count = 0
    total_bytes = 0
    missing_blobs = []
    
    target_dir.mkdir(parents=True, exist_ok=True)
    
    for rel_path, entry in files.items():
        sha256 = entry["sha256"]
        blob_path = get_blob_path(sha256, blob_root)
        
        if not blob_path.exists():
            missing_blobs.append(sha256)
            continue
        
        target_path = target_dir / rel_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(blob_path, target_path)
        
        restored_count += 1
        total_bytes += entry.get("size_bytes", 0)
    
    result = {
        "restored_count": restored_count,
        "total_bytes": total_bytes,
        "target_dir": str(target_dir),
    }
    
    if missing_blobs:
        result["missing_blobs"] = missing_blobs
        result["error"] = f"Missing {len(missing_blobs)} blob(s)"
    
    return result


def export_manifest_to_zip(
    manifest_path: Path,
    blob_root: Path,
    zip_path: Path,
) -> Dict[str, Any]:
    """
    Export a manifest-based archive to a zip file.
    
    Args:
        manifest_path: Path to the manifest JSON file.
        blob_root: Root directory of the blob store.
        zip_path: Path for the output zip file.
    
    Returns:
        Dictionary with export statistics.
    
    Raises:
        FileNotFoundError: If manifest or required blobs are missing.
    """
    manifest = load_manifest(manifest_path)
    files = manifest.get("files", {})
    
    exported_count = 0
    total_bytes = 0
    missing_blobs = []
    
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_path, entry in files.items():
            sha256 = entry["sha256"]
            blob_path = get_blob_path(sha256, blob_root)
            
            if not blob_path.exists():
                missing_blobs.append(sha256)
                continue
            
            zf.write(blob_path, rel_path)
            exported_count += 1
            total_bytes += entry.get("size_bytes", 0)
    
    result = {
        "exported_count": exported_count,
        "total_bytes": total_bytes,
        "zip_path": str(zip_path),
    }
    
    if missing_blobs:
        result["missing_blobs"] = missing_blobs
        result["error"] = f"Missing {len(missing_blobs)} blob(s)"
    
    return result


def get_file_from_manifest(
    manifest_path: Path,
    blob_root: Path,
    rel_path: str,
) -> Path:
    """
    Get the blob path for a specific file in a manifest.
    
    Args:
        manifest_path: Path to the manifest JSON file.
        blob_root: Root directory of the blob store.
        rel_path: Relative path of the file within the manifest.
    
    Returns:
        Path to the blob file.
    
    Raises:
        FileNotFoundError: If manifest or blob is missing.
        KeyError: If rel_path is not in the manifest.
    """
    manifest = load_manifest(manifest_path)
    files = manifest.get("files", {})
    
    if rel_path not in files:
        raise KeyError(f"File not found in manifest: {rel_path}")
    
    sha256 = files[rel_path]["sha256"]
    blob_path = get_blob_path(sha256, blob_root)
    
    if not blob_path.exists():
        raise FileNotFoundError(f"Blob not found: {sha256}")
    
    return blob_path
