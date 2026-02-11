"""
Storage Statistics API Routes

Provides storage usage statistics for the Runicorn data directory.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Request

from .storage_utils import get_storage_root

router = APIRouter()


def _get_dir_size(path: Path) -> int:
    """
    Calculate total size of a directory recursively.
    
    Args:
        path: Directory path to calculate size for.
    
    Returns:
        Total size in bytes.
    """
    if not path.exists():
        return 0
    
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _count_files(path: Path) -> int:
    """Count files in a directory recursively."""
    if not path.exists():
        return 0
    
    count = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                count += 1
    except OSError:
        pass
    return count


def _format_size(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def get_storage_stats(storage_root: Path) -> Dict[str, Any]:
    """
    Get comprehensive storage statistics.
    
    Args:
        storage_root: Root directory of Runicorn storage.
    
    Returns:
        Dictionary with storage statistics.
    """
    archive_root = storage_root / "archive"
    blobs_root = archive_root / "blobs"
    manifests_root = archive_root / "manifests"
    outputs_root = archive_root / "outputs"
    
    # CAS blob store stats
    blobs_size = _get_dir_size(blobs_root)
    blobs_count = _count_files(blobs_root)
    
    # Manifests stats
    manifests_size = _get_dir_size(manifests_root)
    manifests_count = _count_files(manifests_root)
    
    # Outputs stats (rolling outputs)
    outputs_size = _get_dir_size(outputs_root)
    outputs_count = _count_files(outputs_root)
    
    # Total archive size
    archive_size = blobs_size + manifests_size + outputs_size
    
    # Run directories (project/experiment/runs/*)
    runs_size = 0
    runs_count = 0
    projects_count = 0
    experiments_count = 0
    
    for project_dir in storage_root.iterdir():
        if not project_dir.is_dir():
            continue
        # Skip special directories
        if project_dir.name in ("archive", "index", ".dedup", "artifacts"):
            continue
        
        projects_count += 1
        for exp_dir in project_dir.iterdir():
            if not exp_dir.is_dir():
                continue
            experiments_count += 1
            runs_dir = exp_dir / "runs"
            if runs_dir.exists():
                for run_dir in runs_dir.iterdir():
                    if run_dir.is_dir():
                        runs_count += 1
                        runs_size += _get_dir_size(run_dir)
    
    # Index database
    index_dir = storage_root / "index"
    index_size = _get_dir_size(index_dir)
    
    # Total storage
    total_size = archive_size + runs_size + index_size
    
    # Breakdown by archive category
    category_breakdown = {}
    if manifests_root.exists():
        for cat_dir in manifests_root.iterdir():
            if cat_dir.is_dir():
                cat_size = _get_dir_size(cat_dir)
                cat_count = _count_files(cat_dir)
                category_breakdown[cat_dir.name] = {
                    "size_bytes": cat_size,
                    "size_human": _format_size(cat_size),
                    "file_count": cat_count,
                }
    
    return {
        "storage_root": str(storage_root),
        "total": {
            "size_bytes": total_size,
            "size_human": _format_size(total_size),
        },
        "archive": {
            "size_bytes": archive_size,
            "size_human": _format_size(archive_size),
            "blobs": {
                "size_bytes": blobs_size,
                "size_human": _format_size(blobs_size),
                "file_count": blobs_count,
            },
            "manifests": {
                "size_bytes": manifests_size,
                "size_human": _format_size(manifests_size),
                "file_count": manifests_count,
                "by_category": category_breakdown,
            },
            "outputs": {
                "size_bytes": outputs_size,
                "size_human": _format_size(outputs_size),
                "file_count": outputs_count,
            },
        },
        "runs": {
            "size_bytes": runs_size,
            "size_human": _format_size(runs_size),
            "projects_count": projects_count,
            "experiments_count": experiments_count,
            "runs_count": runs_count,
        },
        "index": {
            "size_bytes": index_size,
            "size_human": _format_size(index_size),
        },
    }


@router.get("/storage/stats")
async def storage_stats(request: Request) -> Dict[str, Any]:
    """
    Get storage usage statistics.
    
    Returns comprehensive breakdown of disk usage including:
    - Total storage size
    - Archive (CAS blobs, manifests, outputs)
    - Run directories
    - Index database
    """
    storage_root = get_storage_root(request)
    return get_storage_stats(storage_root)
