"""
Asset Cleanup - Delete runs and their associated assets.

Handles the complex logic of:
1. Determining which assets are orphaned (only referenced by the deleted run)
2. Deleting blob files for orphaned assets
3. Deleting manifest files for orphaned assets
4. Cleaning up the index database
"""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .blob_store import get_blob_path

logger = logging.getLogger(__name__)


def delete_run_completely(
    run_id: str,
    storage_root: Path,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Permanently delete a run and all its orphaned assets.
    
    This function:
    1. Queries the index for all assets linked to the run
    2. Identifies orphaned assets (only referenced by this run)
    3. Deletes blob files for orphaned assets
    4. Deletes manifest files for orphaned assets
    5. Deletes rolling outputs for this run
    6. Removes database records
    7. Deletes the run directory
    
    Args:
        run_id: The run ID to delete.
        storage_root: Root directory of the storage.
        dry_run: If True, only report what would be deleted without actually deleting.
    
    Returns:
        Dict with deletion summary:
        - success: bool
        - run_id: str
        - run_dir_deleted: bool
        - orphaned_assets: list of deleted asset info
        - kept_assets: list of assets still referenced by other runs
        - blobs_deleted: int
        - manifests_deleted: int
        - outputs_deleted: int
        - bytes_freed: int
        - errors: list of error messages
    """
    from ..index import IndexDb
    from ..viewer.services.storage import find_run_dir_by_id
    
    result: Dict[str, Any] = {
        "success": False,
        "run_id": run_id,
        "run_dir_deleted": False,
        "orphaned_assets": [],
        "kept_assets": [],
        "blobs_deleted": 0,
        "manifests_deleted": 0,
        "outputs_deleted": 0,
        "bytes_freed": 0,
        "errors": [],
    }
    
    storage_root = Path(storage_root)
    archive_root = storage_root / "archive"
    blob_root = archive_root / "blobs"
    manifest_root = archive_root / "manifests"
    outputs_root = archive_root / "outputs"
    
    # Find run directory (include_deleted=True to find soft-deleted runs)
    entry = find_run_dir_by_id(storage_root, run_id, include_deleted=True)
    if not entry:
        result["errors"].append(f"Run not found: {run_id}")
        return result
    
    run_dir = entry.dir
    
    # Open index database
    try:
        index_db = IndexDb(storage_root)
    except Exception as e:
        result["errors"].append(f"Failed to open index database: {e}")
        # Even without index, we can still delete the run directory and outputs
        if not dry_run:
            try:
                shutil.rmtree(run_dir)
                result["run_dir_deleted"] = True
            except Exception as e2:
                result["errors"].append(f"Failed to delete run directory: {e2}")
            # Also try to delete rolling outputs
            deleted, freed = _delete_rolling_outputs(run_id, outputs_root, dry_run=False)
            result["outputs_deleted"] += deleted
            result["bytes_freed"] += freed
            result["success"] = True
        return result
    
    try:
        # Get orphaned assets info from index
        db_result = index_db.delete_run_with_orphan_assets(run_id) if not dry_run else _preview_orphaned_assets(index_db, run_id)
        
        orphaned_assets = db_result.get("orphaned_assets", [])
        kept_assets = db_result.get("kept_assets", [])
        
        result["orphaned_assets"] = [_asset_summary(a) for a in orphaned_assets]
        result["kept_assets"] = [_asset_summary(a) for a in kept_assets]
        
        # Delete blob files for orphaned assets
        for asset in orphaned_assets:
            deleted_blobs, freed_bytes = _delete_asset_blobs(
                asset, blob_root, manifest_root, dry_run
            )
            result["blobs_deleted"] += deleted_blobs
            result["bytes_freed"] += freed_bytes
        
        # Delete manifest files for orphaned assets
        for asset in orphaned_assets:
            if _delete_asset_manifest(asset, manifest_root, dry_run):
                result["manifests_deleted"] += 1
        
        # Delete rolling outputs for this run
        deleted_outputs, freed_outputs = _delete_rolling_outputs(run_id, outputs_root, dry_run)
        result["outputs_deleted"] += deleted_outputs
        result["bytes_freed"] += freed_outputs
        
        # Delete run directory
        if not dry_run:
            try:
                shutil.rmtree(run_dir)
                result["run_dir_deleted"] = True
            except Exception as e:
                result["errors"].append(f"Failed to delete run directory: {e}")
            
            # Clean up empty parent directories
            _cleanup_empty_dirs(run_dir.parent, storage_root)
            
            # Clean up empty archive directories
            _cleanup_empty_dirs(archive_root, storage_root)
        else:
            result["run_dir_deleted"] = True  # Would be deleted
        
        result["success"] = True
        
    except Exception as e:
        result["errors"].append(f"Deletion failed: {e}")
        logger.exception(f"Failed to delete run {run_id}")
    finally:
        try:
            index_db.close()
        except Exception:
            pass
    
    return result


def _delete_rolling_outputs(run_id: str, outputs_root: Path, dry_run: bool) -> tuple[int, int]:
    """
    Delete rolling outputs directory for a run.
    
    Rolling outputs are stored in: archive/outputs/rolling/{run_id}/
    
    Args:
        run_id: The run ID.
        outputs_root: Path to archive/outputs directory.
        dry_run: If True, only count without deleting.
    
    Returns:
        Tuple of (files_deleted, bytes_freed)
    """
    deleted_count = 0
    freed_bytes = 0
    
    # Check rolling outputs directory
    rolling_dir = outputs_root / "rolling" / run_id
    if rolling_dir.exists() and rolling_dir.is_dir():
        try:
            # Count files and sizes
            for f in rolling_dir.rglob("*"):
                if f.is_file():
                    try:
                        freed_bytes += f.stat().st_size
                        deleted_count += 1
                    except OSError:
                        pass
            
            # Delete the directory
            if not dry_run:
                shutil.rmtree(rolling_dir)
                logger.info(f"Deleted rolling outputs for run {run_id}: {deleted_count} files, {freed_bytes} bytes")
        except Exception as e:
            logger.warning(f"Failed to delete rolling outputs for {run_id}: {e}")
    
    return deleted_count, freed_bytes


def _cleanup_empty_dirs(start_dir: Path, stop_at: Path) -> int:
    """
    Remove empty directories from start_dir up to (but not including) stop_at.
    
    Also cleans up empty subdirectories within archive structure.
    
    Args:
        start_dir: Directory to start cleaning from.
        stop_at: Stop when reaching this directory (don't delete it).
    
    Returns:
        Number of directories removed.
    """
    removed = 0
    
    # First, clean up empty subdirectories within archive structure
    if start_dir.exists() and start_dir.is_dir():
        # Clean empty subdirs recursively (bottom-up)
        for subdir in sorted(start_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if subdir.is_dir() and subdir != stop_at:
                try:
                    # Check if directory is empty
                    if not any(subdir.iterdir()):
                        subdir.rmdir()
                        removed += 1
                        logger.debug(f"Removed empty directory: {subdir}")
                except OSError:
                    pass
    
    # Then clean up parent directories up to stop_at
    current = start_dir
    while current.exists() and current != stop_at and current.is_relative_to(stop_at):
        try:
            # Check if directory is empty
            if not any(current.iterdir()):
                current.rmdir()
                removed += 1
                logger.debug(f"Removed empty directory: {current}")
                current = current.parent
            else:
                break
        except OSError:
            break
    
    return removed


def _preview_orphaned_assets(index_db: Any, run_id: str) -> Dict[str, Any]:
    """Preview which assets would be orphaned without actually deleting."""
    assets = index_db.get_assets_for_run(run_id)
    
    orphaned = []
    kept = []
    
    for asset in assets:
        asset_id = asset["asset_id"]
        ref_count = index_db.get_asset_ref_count(asset_id)
        
        # ref_count includes current run, so orphaned if ref_count == 1
        if ref_count <= 1:
            orphaned.append(asset)
        else:
            kept.append(asset)
    
    return {
        "orphaned_assets": orphaned,
        "kept_assets": kept,
    }


def _asset_summary(asset: Dict[str, Any]) -> Dict[str, Any]:
    """Create a summary of an asset for the result."""
    return {
        "asset_id": asset.get("asset_id"),
        "asset_type": asset.get("asset_type"),
        "name": asset.get("name"),
        "fingerprint": asset.get("fingerprint"),
        "archive_uri": asset.get("archive_uri"),
        "role": asset.get("role"),
    }


def _delete_asset_blobs(
    asset: Dict[str, Any],
    blob_root: Path,
    manifest_root: Path,
    dry_run: bool,
) -> tuple[int, int]:
    """
    Delete blob files for an asset.
    
    For manifest-based assets (directories), reads the manifest to find all blobs.
    For single-file assets, deletes the blob directly.
    
    Returns:
        Tuple of (blobs_deleted, bytes_freed)
    """
    deleted_count = 0
    freed_bytes = 0
    
    archive_uri = asset.get("archive_uri")
    fingerprint = asset.get("fingerprint")
    asset_type = asset.get("asset_type")
    
    if not archive_uri:
        return 0, 0
    
    archive_path = Path(archive_uri)
    
    # Check if this is a manifest-based asset
    if archive_path.suffix == ".json" and "manifests" in str(archive_path):
        # Directory asset - read manifest to get blob list
        try:
            if archive_path.exists():
                manifest = json.loads(archive_path.read_text(encoding="utf-8"))
                files = manifest.get("files", {})
                
                for rel_path, entry in files.items():
                    sha256 = entry.get("sha256")
                    if not sha256:
                        continue
                    
                    blob_path = get_blob_path(sha256, blob_root)
                    if blob_path.exists():
                        try:
                            size = blob_path.stat().st_size
                            if not dry_run:
                                blob_path.unlink()
                            deleted_count += 1
                            freed_bytes += size
                        except Exception as e:
                            logger.warning(f"Failed to delete blob {sha256}: {e}")
        except Exception as e:
            logger.warning(f"Failed to read manifest {archive_path}: {e}")
    
    elif fingerprint and len(fingerprint) == 64:
        # Single file asset - fingerprint is the SHA256
        blob_path = get_blob_path(fingerprint, blob_root)
        if blob_path.exists():
            try:
                size = blob_path.stat().st_size
                if not dry_run:
                    blob_path.unlink()
                deleted_count += 1
                freed_bytes += size
            except Exception as e:
                logger.warning(f"Failed to delete blob {fingerprint}: {e}")
    
    return deleted_count, freed_bytes


def _delete_asset_manifest(
    asset: Dict[str, Any],
    manifest_root: Path,
    dry_run: bool,
) -> bool:
    """Delete the manifest file for an asset if it exists."""
    archive_uri = asset.get("archive_uri")
    if not archive_uri:
        return False
    
    archive_path = Path(archive_uri)
    
    # Only delete if it's a manifest file
    if archive_path.suffix == ".json" and "manifests" in str(archive_path):
        if archive_path.exists():
            try:
                if not dry_run:
                    archive_path.unlink()
                return True
            except Exception as e:
                logger.warning(f"Failed to delete manifest {archive_path}: {e}")
    
    return False


def cleanup_orphaned_blobs(storage_root: Path, dry_run: bool = False) -> Dict[str, Any]:
    """
    Scan for and remove orphaned blobs not referenced by any manifest.
    
    This is a maintenance function to clean up blobs that may have been
    left behind due to incomplete deletions or bugs.
    
    Args:
        storage_root: Root directory of the storage.
        dry_run: If True, only report what would be deleted.
    
    Returns:
        Dict with cleanup summary.
    """
    from ..index import IndexDb
    
    result: Dict[str, Any] = {
        "success": False,
        "blobs_scanned": 0,
        "orphaned_blobs": 0,
        "bytes_freed": 0,
        "errors": [],
    }
    
    storage_root = Path(storage_root)
    blob_root = storage_root / "archive" / "blobs"
    
    if not blob_root.exists():
        result["success"] = True
        return result
    
    # Collect all referenced blobs from index
    referenced_blobs: set[str] = set()
    
    try:
        index_db = IndexDb(storage_root)
        conn = index_db._connect()
        
        # Get all archived assets with fingerprints
        rows = conn.execute(
            "SELECT fingerprint, archive_uri FROM assets WHERE is_archived=1 AND fingerprint IS NOT NULL"
        ).fetchall()
        
        for row in rows:
            fp = row["fingerprint"]
            archive_uri = row["archive_uri"]
            
            # Single file: fingerprint is the blob hash
            if fp and len(fp) == 64:
                referenced_blobs.add(fp)
            
            # Manifest: read to get all blob hashes
            if archive_uri and ".json" in archive_uri:
                try:
                    manifest_path = Path(archive_uri)
                    if manifest_path.exists():
                        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                        for entry in manifest.get("files", {}).values():
                            sha = entry.get("sha256")
                            if sha:
                                referenced_blobs.add(sha)
                except Exception:
                    pass
        
        index_db.close()
    except Exception as e:
        result["errors"].append(f"Failed to scan index: {e}")
        return result
    
    # Scan blob directory
    for prefix_dir in blob_root.iterdir():
        if not prefix_dir.is_dir():
            continue
        for blob_file in prefix_dir.iterdir():
            if not blob_file.is_file() or blob_file.name.startswith("."):
                continue
            
            result["blobs_scanned"] += 1
            blob_hash = blob_file.name
            
            if blob_hash not in referenced_blobs:
                result["orphaned_blobs"] += 1
                try:
                    size = blob_file.stat().st_size
                    result["bytes_freed"] += size
                    if not dry_run:
                        blob_file.unlink()
                except Exception as e:
                    result["errors"].append(f"Failed to delete {blob_hash}: {e}")
    
    result["success"] = True
    return result
