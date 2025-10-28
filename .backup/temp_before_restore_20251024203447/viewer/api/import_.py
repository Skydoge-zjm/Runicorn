"""
Import/Export Archive API Routes

Handles import of experiment archives (zip/tar.gz) into the storage system.
"""
from __future__ import annotations

import logging
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from ..services.storage import iter_all_runs
from ..utils.helpers import is_within_directory

logger = logging.getLogger(__name__)
router = APIRouter()

# Check if multipart support is available
try:
    import multipart  # type: ignore
    HAS_MULTIPART = True
except ImportError:
    HAS_MULTIPART = False
    logger.debug("python-multipart not available, file upload disabled")


def safe_extract_tar(tar: tarfile.TarFile, dest: Path) -> List[Path]:
    """
    Safely extract tar archive with path traversal protection.
    
    Args:
        tar: TarFile object to extract
        dest: Destination directory
        
    Returns:
        List of extracted file paths
    """
    extracted: List[Path] = []
    
    for member in tar.getmembers():
        if not member.name or member.name.strip() == "":
            continue
        
        # Skip symlinks/hardlinks for security
        try:
            if member.issym() or member.islnk():
                continue
        except Exception:
            pass
        
        # Prevent path traversal attacks
        target_path = dest / member.name
        if not is_within_directory(dest, target_path):
            logger.warning(f"Skipping unsafe path: {member.name}")
            continue
        
        try:
            tar.extract(member, path=str(dest))
            if not member.isdir():
                extracted.append(target_path)
        except Exception as e:
            logger.warning(f"Failed to extract {member.name}: {e}")
            continue
    
    return extracted


def safe_extract_zip(zf: zipfile.ZipFile, dest: Path) -> List[Path]:
    """
    Safely extract zip archive with path traversal protection.
    
    Args:
        zf: ZipFile object to extract
        dest: Destination directory
        
    Returns:
        List of extracted file paths
    """
    extracted: List[Path] = []
    
    for name in zf.namelist():
        if not name or name.endswith("/"):
            # Handle directories
            try:
                (dest / name).mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            continue
        
        target_path = dest / name
        if not is_within_directory(dest, target_path):
            logger.warning(f"Skipping unsafe path: {name}")
            continue
        
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(name) as src, open(target_path, "wb") as out:
                out.write(src.read())
            extracted.append(target_path)
        except Exception as e:
            logger.warning(f"Failed to extract {name}: {e}")
            continue
    
    return extracted


if HAS_MULTIPART:
    @router.post("/import/archive")
    async def import_archive(request: Request, file: UploadFile = File(...)) -> Dict[str, Any]:
        """
        Import a packaged archive (.zip or .tar.gz/.tgz) of runs into the current storage root.
        
        Expected layout inside archive: either the storage root itself (project/name/runs/<id>)
        or any subset of that hierarchy. Files will be merged into the active storage root.
        
        Args:
            file: Archive file to import
            
        Returns:
            Import results including number of files and new runs
            
        Raises:
            HTTPException: If archive is invalid or import fails
        """
        storage_root = request.app.state.storage_root
        
        # Snapshot existing run dirs for delta reporting
        before = {entry.dir for entry in iter_all_runs(storage_root)}
        
        # Determine file type from filename
        try:
            suffix = ".zip" if file.filename and file.filename.lower().endswith(".zip") else ".tar.gz"
        except Exception:
            suffix = ".zip"
        
        # Save uploaded file to temporary location
        tmp = tempfile.NamedTemporaryFile(prefix="runicorn_import_", suffix=suffix, delete=False)
        tmp_path = Path(tmp.name)
        
        try:
            # Read uploaded file content
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                tmp.write(chunk)
        finally:
            tmp.close()
        
        # Extract archive
        imported_files: List[Path] = []
        try:
            filename = (file.filename or "").lower()
            
            if filename.endswith(".zip"):
                with zipfile.ZipFile(tmp_path, "r") as zf:
                    imported_files = safe_extract_zip(zf, storage_root)
            elif filename.endswith(".tar.gz") or filename.endswith(".tgz"):
                with tarfile.open(tmp_path, "r:gz") as tf:
                    imported_files = safe_extract_tar(tf, storage_root)
            else:
                # Try zip first, then tar.gz
                try:
                    with zipfile.ZipFile(tmp_path, "r") as zf:
                        imported_files = safe_extract_zip(zf, storage_root)
                except Exception:
                    try:
                        with tarfile.open(tmp_path, "r:gz") as tf:
                            imported_files = safe_extract_tar(tf, storage_root)
                    except Exception as e:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Unsupported or corrupted archive: {e}"
                        )
        finally:
            # Clean up temporary file
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
        
        # Compute imported runs delta
        after_entries = iter_all_runs(storage_root)
        after = {entry.dir for entry in after_entries}
        new_dirs = sorted([str(p) for p in (after - before)])
        
        # Map run_ids for quick display
        new_ids: List[str] = []
        for entry in after_entries:
            if entry.dir in (after - before):
                new_ids.append(entry.dir.name)
        
        logger.info(f"Import completed: {len(imported_files)} files, {len(new_ids)} new runs")
        
        return {
            "ok": True,
            "imported_files": len(imported_files),
            "new_run_dirs": new_dirs,
            "new_run_ids": sorted(new_ids),
            "storage": str(storage_root),
        }

else:
    @router.post("/import/archive")
    async def import_archive_unavailable() -> Dict[str, Any]:
        """
        Stub endpoint when file upload is not available.
        
        Returns error indicating multipart support is not available.
        """
        raise HTTPException(
            status_code=503, 
            detail="File upload not available: python-multipart not bundled in this build"
        )
