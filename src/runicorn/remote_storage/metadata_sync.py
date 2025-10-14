"""
Metadata Synchronization Service

Handles incremental synchronization of metadata files from remote server to local cache.
"""
from __future__ import annotations

import json
import logging
import os
import posixpath
import stat as statmod
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

import paramiko

from .models import SyncProgress, SyncStatus, CachedFile
from .cache_manager import LocalCacheManager

logger = logging.getLogger(__name__)


class MetadataSyncService:
    """
    Metadata synchronization service.
    
    Strategy:
    1. Only sync small files (<1MB):
       - artifacts/*/versions.json
       - artifacts/*/*/*/metadata.json
       - artifacts/*/*/*/manifest.json
       - <project>/<name>/runs/*/meta.json
       - <project>/<name>/runs/*/status.json
       - <project>/<name>/runs/*/summary.json
    
    2. Incremental sync:
       - Compare mtime (modification time)
       - Only download changed files
       - Use SFTP stat() for efficiency
    
    3. Background sync:
       - Run in separate thread
       - Auto-sync at configurable interval
       - Progress tracking
    """
    
    # Maximum file size to sync (1MB)
    MAX_FILE_SIZE = 1024 * 1024
    
    def __init__(
        self,
        ssh_session: paramiko.SSHClient,
        sftp_client: paramiko.SFTPClient,
        remote_root: str,
        cache_manager: LocalCacheManager
    ):
        """
        Initialize metadata sync service.
        
        Args:
            ssh_session: Active SSH session
            sftp_client: Active SFTP client
            remote_root: Remote storage root directory
            cache_manager: Local cache manager instance
        """
        self.ssh_session = ssh_session
        self.sftp = sftp_client
        self.remote_root = remote_root.rstrip('/')
        self.cache = cache_manager
        
        # Sync state
        self.progress = SyncProgress()
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._sync_thread: Optional[threading.Thread] = None
        
        # Callbacks
        self._progress_callbacks: List[Callable[[SyncProgress], None]] = []
    
    def add_progress_callback(self, callback: Callable[[SyncProgress], None]) -> None:
        """
        Add progress callback for monitoring.
        
        Args:
            callback: Function to call with SyncProgress updates
        """
        with self._lock:
            self._progress_callbacks.append(callback)
    
    def _notify_progress(self):
        """Notify all progress callbacks."""
        with self._lock:
            for callback in self._progress_callbacks:
                try:
                    callback(self.progress)
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")
    
    def sync_all(self) -> bool:
        """
        Synchronize all metadata from remote to local cache.
        
        Returns:
            True if sync completed successfully
        """
        with self._lock:
            if self.progress.is_running:
                logger.warning("Sync already in progress")
                return False
            
            self.progress.start()
            self._notify_progress()
        
        try:
            # Phase 1: Sync artifacts metadata
            logger.info("Syncing artifacts metadata...")
            self._sync_artifacts_metadata()
            
            # Phase 2: Sync experiments metadata
            logger.info("Syncing experiments metadata...")
            self._sync_experiments_metadata()
            
            # Phase 3: Update statistics
            self.cache.update_stat('last_sync', str(time.time()))
            
            with self._lock:
                self.progress.complete()
                self._notify_progress()
            
            logger.info(
                f"Metadata sync completed: {self.progress.synced_files} files, "
                f"{self.progress.synced_bytes / (1024*1024):.2f} MB"
            )
            return True
            
        except Exception as e:
            logger.error(f"Metadata sync failed: {e}", exc_info=True)
            with self._lock:
                self.progress.fail(str(e))
                self._notify_progress()
            return False
    
    def _sync_artifacts_metadata(self):
        """Synchronize artifacts metadata."""
        remote_artifacts_root = f"{self.remote_root}/artifacts"
        
        try:
            # List artifact types (model, dataset, config, etc.)
            type_dirs = self.sftp.listdir(remote_artifacts_root)
        except IOError as e:
            logger.warning(f"Artifacts directory not found: {e}")
            return
        
        for type_name in type_dirs:
            if type_name.startswith('.'):
                continue  # Skip hidden directories
            
            remote_type_path = f"{remote_artifacts_root}/{type_name}"
            
            try:
                # Check if it's a directory
                stat_info = self.sftp.stat(remote_type_path)
                if not statmod.S_ISDIR(stat_info.st_mode):
                    continue
                
                # List artifacts in this type
                artifact_names = self.sftp.listdir(remote_type_path)
                
                for artifact_name in artifact_names:
                    if artifact_name.startswith('.'):
                        continue  # Skip hidden directories
                    
                    self._sync_artifact_versions(
                        type_name,
                        artifact_name,
                        f"{remote_type_path}/{artifact_name}"
                    )
                    
            except Exception as e:
                logger.error(f"Failed to sync type {type_name}: {e}")
                with self._lock:
                    self.progress.errors.append(f"Type {type_name}: {e}")
    
    def _sync_artifact_versions(self, type_name: str, artifact_name: str, remote_artifact_path: str):
        """
        Synchronize all versions of an artifact.
        
        Args:
            type_name: Artifact type (model, dataset, etc.)
            artifact_name: Artifact name
            remote_artifact_path: Remote path to artifact directory
        """
        # Sync versions.json
        versions_json_path = f"{remote_artifact_path}/versions.json"
        local_versions_path = (
            self.cache.metadata_dir / "artifacts" / type_name / 
            artifact_name / "versions.json"
        )
        
        self._sync_file(versions_json_path, local_versions_path)
        
        # Read versions.json to get version numbers
        if not local_versions_path.exists():
            return
        
        try:
            versions_data = json.loads(local_versions_path.read_text(encoding="utf-8"))
            version_list = versions_data.get("versions", [])
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read {local_versions_path}: {e}")
            return
        
        # Sync each version's metadata
        for version_info in version_list:
            version = version_info.get("version")
            if not version:
                continue
            
            version_remote_path = f"{remote_artifact_path}/v{version}"
            
            # Sync metadata.json
            metadata_remote_path = f"{version_remote_path}/metadata.json"
            local_metadata_path = (
                self.cache.metadata_dir / "artifacts" / type_name / 
                artifact_name / f"v{version}" / "metadata.json"
            )
            self._sync_file(metadata_remote_path, local_metadata_path)
            
            # Sync manifest.json
            manifest_remote_path = f"{version_remote_path}/manifest.json"
            local_manifest_path = (
                self.cache.metadata_dir / "artifacts" / type_name / 
                artifact_name / f"v{version}" / "manifest.json"
            )
            self._sync_file(manifest_remote_path, local_manifest_path)
            
            # Update cache index
            if local_metadata_path.exists():
                try:
                    metadata = json.loads(local_metadata_path.read_text(encoding="utf-8"))
                    manifest = None
                    if local_manifest_path.exists():
                        manifest = json.loads(local_manifest_path.read_text(encoding="utf-8"))
                    
                    self.cache.cache_artifact_metadata(
                        name=artifact_name,
                        type=type_name,
                        version=version,
                        metadata=metadata,
                        manifest=manifest
                    )
                except Exception as e:
                    logger.error(f"Failed to cache metadata for {artifact_name}:v{version}: {e}")
    
    def _sync_experiments_metadata(self):
        """Synchronize experiments metadata."""
        # This syncs the new hierarchy: <project>/<name>/runs/<run_id>
        
        try:
            # List projects
            project_dirs = self.sftp.listdir(self.remote_root)
        except IOError as e:
            logger.warning(f"Failed to list remote root: {e}")
            return
        
        for project_name in project_dirs:
            if project_name.startswith('.') or project_name in ['artifacts', 'sweeps']:
                continue  # Skip hidden and special directories
            
            remote_project_path = f"{self.remote_root}/{project_name}"
            
            try:
                # Check if it's a directory
                stat_info = self.sftp.stat(remote_project_path)
                if not statmod.S_ISDIR(stat_info.st_mode):
                    continue
                
                # List experiment names
                exp_names = self.sftp.listdir(remote_project_path)
                
                for exp_name in exp_names:
                    if exp_name.startswith('.'):
                        continue
                    
                    remote_exp_path = f"{remote_project_path}/{exp_name}"
                    
                    # Check for runs directory
                    remote_runs_path = f"{remote_exp_path}/runs"
                    try:
                        run_ids = self.sftp.listdir(remote_runs_path)
                        
                        for run_id in run_ids:
                            if run_id.startswith('.'):
                                continue
                            
                            self._sync_run_metadata(
                                project_name,
                                exp_name,
                                run_id,
                                f"{remote_runs_path}/{run_id}"
                            )
                            
                    except IOError:
                        # No runs directory, skip
                        continue
                        
            except Exception as e:
                logger.error(f"Failed to sync project {project_name}: {e}")
                with self._lock:
                    self.progress.errors.append(f"Project {project_name}: {e}")
    
    def _sync_run_metadata(
        self,
        project_name: str,
        exp_name: str,
        run_id: str,
        remote_run_path: str
    ):
        """
        Synchronize metadata for a single run.
        
        Args:
            project_name: Project name
            exp_name: Experiment name
            run_id: Run ID
            remote_run_path: Remote path to run directory
        """
        local_run_dir = (
            self.cache.metadata_dir / "experiments" / 
            project_name / exp_name / "runs" / run_id
        )
        
        # Sync key metadata files
        metadata_files = [
            "meta.json",
            "status.json",
            "summary.json",
            "environment.json",
            "artifacts_created.json",
            "artifacts_used.json"
        ]
        
        for filename in metadata_files:
            remote_file_path = f"{remote_run_path}/{filename}"
            local_file_path = local_run_dir / filename
            self._sync_file(remote_file_path, local_file_path, required=False)
    
    def _sync_file(
        self,
        remote_path: str,
        local_path: Path,
        required: bool = True
    ) -> bool:
        """
        Synchronize a single file if it's new or modified.
        
        Args:
            remote_path: Remote file path (POSIX)
            local_path: Local file path
            required: If False, skip if file doesn't exist remotely
            
        Returns:
            True if file was synced
        """
        try:
            # Get remote file stat
            remote_stat = self.sftp.stat(remote_path)
            remote_mtime = remote_stat.st_mtime
            remote_size = remote_stat.st_size
            
            # Skip large files
            if remote_size > self.MAX_FILE_SIZE:
                logger.debug(f"Skipping large file: {remote_path} ({remote_size} bytes)")
                return False
            
            # Check if local file is up to date
            if local_path.exists():
                local_mtime = local_path.stat().st_mtime
                if local_mtime >= remote_mtime:
                    # Local file is already up to date
                    logger.debug(f"File already up to date: {remote_path}")
                    return False
            
            # Download file
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Update progress
            with self._lock:
                self.progress.current_file = str(remote_path)
                self._notify_progress()
            
            # Download via SFTP
            self.sftp.get(remote_path, str(local_path))
            
            # Set local file mtime to match remote (for incremental sync)
            os.utime(str(local_path), (remote_mtime, remote_mtime))
            
            # Register in cache
            cached_file = CachedFile(
                remote_path=remote_path,
                local_path=str(local_path),
                size_bytes=remote_size,
                remote_mtime=remote_mtime
            )
            self.cache.cache_file(cached_file)
            
            # Update progress
            with self._lock:
                self.progress.synced_files += 1
                self.progress.synced_bytes += remote_size
                self._notify_progress()
            
            logger.debug(f"Synced file: {remote_path} ({remote_size} bytes)")
            return True
            
        except IOError as e:
            if required:
                logger.error(f"Failed to sync required file {remote_path}: {e}")
                with self._lock:
                    self.progress.errors.append(f"File {remote_path}: {e}")
            else:
                logger.debug(f"Optional file not found: {remote_path}")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error syncing {remote_path}: {e}")
            with self._lock:
                self.progress.errors.append(f"File {remote_path}: {e}")
            return False
    
    def start_background_sync(self, interval_seconds: int = 600) -> None:
        """
        Start background auto-sync thread.
        
        Args:
            interval_seconds: Sync interval in seconds (default: 10 minutes)
        """
        if self._sync_thread and self._sync_thread.is_alive():
            logger.warning("Background sync already running")
            return
        
        self._stop_event.clear()
        self._sync_thread = threading.Thread(
            target=self._background_sync_loop,
            args=(interval_seconds,),
            daemon=True,
            name="MetadataSyncThread"
        )
        self._sync_thread.start()
        logger.info(f"Started background sync (interval: {interval_seconds}s)")
    
    def _background_sync_loop(self, interval_seconds: int):
        """
        Background sync loop.
        
        Args:
            interval_seconds: Sync interval in seconds
        """
        while not self._stop_event.is_set():
            try:
                logger.info("Background sync: starting...")
                self.sync_all()
                logger.info("Background sync: completed")
            except Exception as e:
                logger.error(f"Background sync error: {e}", exc_info=True)
            
            # Wait for next sync (or stop event)
            self._stop_event.wait(interval_seconds)
    
    def stop_background_sync(self) -> None:
        """Stop background auto-sync thread."""
        if not self._sync_thread or not self._sync_thread.is_alive():
            return
        
        logger.info("Stopping background sync...")
        self._stop_event.set()
        self._sync_thread.join(timeout=10)
        
        if self._sync_thread.is_alive():
            logger.warning("Background sync thread did not stop cleanly")
        else:
            logger.info("Background sync stopped")
    
    def get_progress(self) -> SyncProgress:
        """
        Get current sync progress.
        
        Returns:
            Copy of current sync progress
        """
        with self._lock:
            # Return a copy to avoid thread safety issues
            return SyncProgress(
                status=self.progress.status,
                started_at=self.progress.started_at,
                completed_at=self.progress.completed_at,
                total_files=self.progress.total_files,
                synced_files=self.progress.synced_files,
                total_bytes=self.progress.total_bytes,
                synced_bytes=self.progress.synced_bytes,
                current_file=self.progress.current_file,
                errors=self.progress.errors.copy()
            )


