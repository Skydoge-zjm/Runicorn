"""
On-Demand File Fetcher

Handles on-demand downloading of artifact files with progress tracking.
"""
from __future__ import annotations

import hashlib
import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

import paramiko

from .models import DownloadTask
from .cache_manager import LocalCacheManager

logger = logging.getLogger(__name__)


class OnDemandFileFetcher:
    """
    On-demand file fetcher with progress tracking.
    
    Features:
    1. User-triggered explicit downloads
    2. Progress tracking and callbacks
    3. Resume support (future enhancement)
    4. Multiple concurrent downloads
    5. Smart caching
    """
    
    def __init__(
        self,
        sftp_client: paramiko.SFTPClient,
        remote_root: str,
        cache_manager: LocalCacheManager
    ):
        """
        Initialize file fetcher.
        
        Args:
            sftp_client: Active SFTP client
            remote_root: Remote storage root directory
            cache_manager: Local cache manager instance
        """
        self.sftp = sftp_client
        self.remote_root = remote_root.rstrip('/')
        self.cache = cache_manager
        
        # Active download tasks
        self._tasks: Dict[str, DownloadTask] = {}
        self._tasks_lock = threading.RLock()
        
        # Progress callbacks
        self._progress_callbacks: Dict[str, List[Callable[[DownloadTask], None]]] = {}
    
    def download_artifact(
        self,
        name: str,
        type: str,
        version: int,
        target_dir: Optional[Path] = None,
        on_progress: Optional[Callable[[DownloadTask], None]] = None
    ) -> str:
        """
        Download all files for an artifact.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Artifact version
            target_dir: Optional target directory (defaults to cache downloads dir)
            on_progress: Optional progress callback
            
        Returns:
            Task ID for tracking download progress
            
        Raises:
            ValueError: If artifact metadata not found in cache
            RuntimeError: If SFTP connection not available
        """
        # Verify metadata is cached
        manifest = self.cache.get_artifact_manifest(name, type, version)
        if not manifest:
            raise ValueError(
                f"Artifact metadata not found in cache: {name}:v{version}. "
                f"Please sync metadata first."
            )
        
        # Determine target directory
        if target_dir is None:
            target_dir = self.cache.downloads_dir / name / f"v{version}"
        else:
            target_dir = Path(target_dir)
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Create download task
        task_id = str(uuid.uuid4())
        files = manifest.get("files", [])
        total_size = sum(f.get("size", 0) for f in files)
        
        task = DownloadTask(
            task_id=task_id,
            artifact_name=name,
            artifact_type=type,
            artifact_version=version,
            target_dir=str(target_dir),
            total_files=len(files),
            total_bytes=total_size
        )
        
        with self._tasks_lock:
            self._tasks[task_id] = task
            if on_progress:
                self._progress_callbacks[task_id] = [on_progress]
        
        # Start download in background thread
        thread = threading.Thread(
            target=self._download_task_worker,
            args=(task_id, name, type, version, target_dir, files),
            daemon=True,
            name=f"Download-{name}-v{version}"
        )
        thread.start()
        
        logger.info(
            f"Started download task {task_id} for {name}:v{version} "
            f"({len(files)} files, {total_size / (1024*1024):.2f} MB)"
        )
        
        return task_id
    
    def _download_task_worker(
        self,
        task_id: str,
        name: str,
        type: str,
        version: int,
        target_dir: Path,
        files: List[Dict[str, Any]]
    ):
        """
        Worker thread for downloading files.
        
        Args:
            task_id: Download task ID
            name: Artifact name
            type: Artifact type
            version: Artifact version
            target_dir: Target directory
            files: List of file entries from manifest
        """
        task = self._get_task(task_id)
        if not task:
            return
        
        try:
            remote_files_root = (
                f"{self.remote_root}/artifacts/{type}/{name}/v{version}/files"
            )
            
            downloaded_files = 0
            downloaded_bytes = 0
            
            for file_entry in files:
                file_path = file_entry.get("path", "")
                file_size = file_entry.get("size", 0)
                file_digest = file_entry.get("digest", "")
                
                if not file_path:
                    continue
                
                # Remote and local paths
                remote_file = f"{remote_files_root}/{file_path}"
                local_file = target_dir / file_path
                
                # Create parent directory
                local_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Download file
                logger.debug(f"Downloading: {file_path} ({file_size} bytes)")
                self._download_file_with_progress(
                    remote_file,
                    local_file,
                    file_size,
                    file_digest,
                    task_id
                )
                
                # Update progress
                downloaded_files += 1
                downloaded_bytes += file_size
                
                task.update_progress(downloaded_files, downloaded_bytes)
                self._notify_progress(task_id)
            
            # Mark task as completed
            task.complete()
            self._notify_progress(task_id)
            
            logger.info(
                f"Download completed: {name}:v{version} "
                f"({downloaded_files} files, {downloaded_bytes / (1024*1024):.2f} MB)"
            )
            
        except Exception as e:
            logger.error(f"Download failed for {name}:v{version}: {e}", exc_info=True)
            task.fail(str(e))
            self._notify_progress(task_id)
    
    def _download_file_with_progress(
        self,
        remote_path: str,
        local_path: Path,
        expected_size: int,
        expected_digest: str,
        task_id: str
    ):
        """
        Download a single file with progress tracking.
        
        Args:
            remote_path: Remote file path
            local_path: Local file path
            expected_size: Expected file size (for validation)
            expected_digest: Expected file digest (for validation)
            task_id: Download task ID (for progress updates)
            
        Raises:
            IOError: If download fails
            ValueError: If file validation fails
        """
        try:
            # Download file
            self.sftp.get(remote_path, str(local_path))
            
            # Validate size
            actual_size = local_path.stat().st_size
            if actual_size != expected_size:
                raise ValueError(
                    f"Size mismatch: expected {expected_size}, got {actual_size}"
                )
            
            # Validate checksum if provided
            if expected_digest:
                actual_digest = self._compute_file_digest(local_path, expected_digest)
                if actual_digest != expected_digest:
                    raise ValueError(
                        f"Checksum mismatch: expected {expected_digest}, "
                        f"got {actual_digest}"
                    )
            
            logger.debug(f"Downloaded and validated: {remote_path}")
            
        except Exception as e:
            # Clean up partial download
            if local_path.exists():
                try:
                    local_path.unlink()
                except Exception:
                    pass
            raise IOError(f"Failed to download {remote_path}: {e}") from e
    
    def _compute_file_digest(self, file_path: Path, digest_format: str) -> str:
        """
        Compute file digest for validation.
        
        Args:
            file_path: Path to file
            digest_format: Expected digest format (e.g., "sha256:abc123")
            
        Returns:
            Digest string in the same format
        """
        # Parse digest format
        if ":" in digest_format:
            algo, _ = digest_format.split(":", 1)
        else:
            algo = "sha256"  # Default
        
        # Compute hash
        if algo == "sha256":
            hasher = hashlib.sha256()
        elif algo == "md5":
            hasher = hashlib.md5()
        else:
            logger.warning(f"Unsupported hash algorithm: {algo}, skipping validation")
            return digest_format  # Return expected to skip validation
        
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        
        return f"{algo}:{hasher.hexdigest()}"
    
    def download_single_file(
        self,
        name: str,
        type: str,
        version: int,
        file_path: str,
        target_path: Optional[Path] = None
    ) -> Path:
        """
        Download a single file from an artifact.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Artifact version
            file_path: File path within artifact
            target_path: Optional target file path
            
        Returns:
            Path to downloaded file
            
        Raises:
            ValueError: If file not found in manifest
            IOError: If download fails
        """
        # Get manifest
        manifest = self.cache.get_artifact_manifest(name, type, version)
        if not manifest:
            raise ValueError(
                f"Artifact metadata not found: {name}:v{version}"
            )
        
        # Find file in manifest
        files = manifest.get("files", [])
        file_entry = None
        for f in files:
            if f.get("path") == file_path:
                file_entry = f
                break
        
        if not file_entry:
            raise ValueError(
                f"File not found in manifest: {file_path}"
            )
        
        # Determine target path
        if target_path is None:
            target_path = self.cache.downloads_dir / name / f"v{version}" / file_path
        else:
            target_path = Path(target_path)
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download
        remote_file = (
            f"{self.remote_root}/artifacts/{type}/{name}/v{version}/files/{file_path}"
        )
        
        self._download_file_with_progress(
            remote_file,
            target_path,
            file_entry.get("size", 0),
            file_entry.get("digest", ""),
            ""  # No task ID for single file download
        )
        
        logger.info(f"Downloaded file: {file_path} to {target_path}")
        return target_path
    
    def get_task_status(self, task_id: str) -> Optional[DownloadTask]:
        """
        Get status of a download task.
        
        Args:
            task_id: Download task ID
            
        Returns:
            DownloadTask object or None if not found
        """
        return self._get_task(task_id)
    
    def _get_task(self, task_id: str) -> Optional[DownloadTask]:
        """Get task with thread safety."""
        with self._tasks_lock:
            return self._tasks.get(task_id)
    
    def cancel_download(self, task_id: str) -> bool:
        """
        Cancel an ongoing download.
        
        Note: This is a graceful cancellation - the current file will complete
        but subsequent files won't be downloaded.
        
        Args:
            task_id: Download task ID
            
        Returns:
            True if task was cancelled
        """
        task = self._get_task(task_id)
        if not task or not task.is_running:
            return False
        
        task.fail("Cancelled by user")
        logger.info(f"Download task {task_id} cancelled")
        return True
    
    def cleanup_completed_tasks(self, max_age_seconds: int = 3600) -> None:
        """
        Clean up completed download tasks older than specified age.
        
        Args:
            max_age_seconds: Maximum age in seconds (default: 1 hour)
        """
        with self._tasks_lock:
            current_time = time.time()
            to_remove = []
            
            for task_id, task in self._tasks.items():
                if task.completed_at:
                    age = current_time - task.completed_at
                    if age > max_age_seconds:
                        to_remove.append(task_id)
            
            for task_id in to_remove:
                del self._tasks[task_id]
                self._progress_callbacks.pop(task_id, None)
            
            if to_remove:
                logger.debug(f"Cleaned up {len(to_remove)} completed tasks")
    
    def add_progress_callback(
        self,
        task_id: str,
        callback: Callable[[DownloadTask], None]
    ) -> None:
        """
        Add progress callback for a download task.
        
        Args:
            task_id: Download task ID
            callback: Callback function
        """
        with self._tasks_lock:
            if task_id not in self._progress_callbacks:
                self._progress_callbacks[task_id] = []
            self._progress_callbacks[task_id].append(callback)
    
    def _notify_progress(self, task_id: str):
        """Notify all progress callbacks for a task."""
        task = self._get_task(task_id)
        if not task:
            return
        
        with self._tasks_lock:
            callbacks = self._progress_callbacks.get(task_id, [])
            for callback in callbacks:
                try:
                    callback(task)
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")
    
    def list_active_downloads(self) -> List[DownloadTask]:
        """
        List all active download tasks.
        
        Returns:
            List of active DownloadTask objects
        """
        with self._tasks_lock:
            return [
                task for task in self._tasks.values()
                if task.is_running
            ]
    
    def list_all_downloads(self) -> List[DownloadTask]:
        """
        List all download tasks (active and completed).
        
        Returns:
            List of all DownloadTask objects
        """
        with self._tasks_lock:
            return list(self._tasks.values())


