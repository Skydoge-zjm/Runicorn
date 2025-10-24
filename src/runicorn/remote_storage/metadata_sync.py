"""
Metadata Synchronization Service

Handles incremental synchronization of metadata files from remote server to local cache.
Implements L5 (legacy hardening) and L7 (append-only incremental) improvements.
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
from typing import Any, Dict, List, Optional, Callable, Tuple

import paramiko

from .models import SyncProgress, SyncStatus, CachedFile
from .cache_manager import LocalCacheManager
from .manifest_sync import ManifestSyncClient

logger = logging.getLogger(__name__)


class MetadataSyncService:
    """
    Metadata synchronization service with L5 and L7 hardening.
    
    L5 Hardening improvements:
    - Only scan recently modified runs (configurable time window)
    - Option to scan active-only runs
    - Limit max experiments per cycle
    
    L7 Hardening improvements:
    - Offset-based incremental download for append-only files
    - Track file offsets to avoid re-downloading entire files
    
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
       - Offset-based for append-only files (L7)
    
    3. Background sync:
       - Auto-sync on interval
       - Event-driven sync on changes
    """
    
    # Maximum file size for metadata files (1MB)
    MAX_METADATA_FILE_SIZE = 1024 * 1024
    
    # Maximum file size for essential experiment data (100MB)
    MAX_ESSENTIAL_FILE_SIZE = 100 * 1024 * 1024
    
    # L5: Hardening defaults
    DEFAULT_RECENT_SECONDS = 3600  # 1 hour
    DEFAULT_MAX_EXPERIMENTS_PER_CYCLE = 100
    
    # L7: Append-only file patterns
    APPEND_ONLY_FILES = {'events.jsonl', 'logs.txt'}
    
    def __init__(
        self,
        ssh_session: paramiko.SSHClient,
        sftp_client: paramiko.SFTPClient,
        remote_root: str,
        cache_manager: LocalCacheManager,
        # L5: Hardening parameters
        legacy_active_only: bool = True,
        legacy_recent_seconds: int = DEFAULT_RECENT_SECONDS,
        legacy_max_experiments: int = DEFAULT_MAX_EXPERIMENTS_PER_CYCLE,
        # Manifest-based sync
        use_manifest_sync: bool = True,
        manifest_sync_jitter: float = 5.0
    ):
        """
        Initialize metadata sync service with hardening controls.
        
        Args:
            ssh_session: Active SSH session
            sftp_client: Active SFTP client
            remote_root: Remote storage root directory
            cache_manager: Local cache manager instance
            legacy_active_only: Only sync active/recent runs (L5)
            legacy_recent_seconds: Consider runs modified in last N seconds (L5)
            legacy_max_experiments: Max experiments per sync cycle (L5)
            use_manifest_sync: Try manifest-based sync first (default: True)
            manifest_sync_jitter: Random jitter for manifest sync (seconds)
        """
        self.ssh_session = ssh_session
        self.sftp = sftp_client
        self.remote_root = remote_root.rstrip('/')
        self.cache = cache_manager
        
        # L5: Hardening configuration
        self.legacy_active_only = legacy_active_only
        self.legacy_recent_seconds = legacy_recent_seconds
        self.legacy_max_experiments = legacy_max_experiments
        
        # Manifest-based sync configuration
        self.use_manifest_sync = use_manifest_sync
        self.manifest_sync_jitter = manifest_sync_jitter
        self._manifest_client: Optional[ManifestSyncClient] = None
        
        # Sync state
        self.progress = SyncProgress()
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._sync_thread: Optional[threading.Thread] = None
        
        # Callbacks
        self._progress_callbacks: List[Callable[[SyncProgress], None]] = []
        
        # L7: Track append-only file states (remote_path -> {offset, mtime})
        self._append_only_states: Dict[str, Dict[str, Any]] = {}
        self._load_append_only_states()
        
        logger.info(
            f"MetadataSyncService initialized: "
            f"active_only={legacy_active_only}, recent={legacy_recent_seconds}s, "
            f"max_exp={legacy_max_experiments}, manifest_sync={use_manifest_sync}"
        )
    
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
    
    def _load_append_only_states(self):
        """L7: Load append-only file states from cache."""
        state_file = self.cache.metadata_dir / ".append_only_states.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                self._append_only_states = data
                logger.debug(f"Loaded {len(self._append_only_states)} append-only file states")
            except Exception as e:
                logger.warning(f"Failed to load append-only states: {e}")
                self._append_only_states = {}
    
    def _save_append_only_states(self):
        """L7: Save append-only file states to cache."""
        state_file = self.cache.metadata_dir / ".append_only_states.json"
        try:
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(
                json.dumps(self._append_only_states, indent=2),
                encoding="utf-8"
            )
            logger.debug(f"Saved {len(self._append_only_states)} append-only file states")
        except Exception as e:
            logger.error(f"Failed to save append-only states: {e}")
    
    def sync_all(self) -> bool:
        """
        Synchronize all metadata from remote to local cache.
        
        Tries manifest-based sync first, falls back to legacy sync if needed.
        
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
            # Try manifest-based sync first
            if self.use_manifest_sync:
                try:
                    logger.info("Attempting manifest-based sync...")
                    success = self._sync_with_manifest()
                    if success:
                        with self._lock:
                            self.progress.complete()
                            self._notify_progress()
                        
                        logger.info(
                            f"Manifest-based sync completed: {self.progress.synced_files} files, "
                            f"{self.progress.synced_bytes / (1024*1024):.2f} MB"
                        )
                        return True
                    else:
                        logger.info("Manifest-based sync returned no changes, trying legacy sync")
                except Exception as e:
                    logger.warning(f"Manifest-based sync failed: {e}, falling back to legacy sync")
            
            # Fallback to legacy sync
            logger.info("Using legacy sync...")
            
            # Phase 1: Sync artifacts metadata
            logger.info("Syncing artifacts metadata...")
            self._sync_artifacts_metadata()
            
            # Phase 2: Sync experiments metadata
            logger.info("Syncing experiments metadata...")
            self._sync_experiments_metadata()
            
            # Phase 3: Update statistics
            self.cache.update_stat('last_sync', str(time.time()))
            
            # L7: Save append-only states
            self._save_append_only_states()
            
            with self._lock:
                self.progress.complete()
                self._notify_progress()
            
            logger.info(
                f"Legacy sync completed: {self.progress.synced_files} files, "
                f"{self.progress.synced_bytes / (1024*1024):.2f} MB"
            )
            return True
            
        except Exception as e:
            logger.error(f"Metadata sync failed: {e}", exc_info=True)
            with self._lock:
                self.progress.fail(str(e))
                self._notify_progress()
            return False
    
    def _sync_with_manifest(self) -> bool:
        """
        Perform manifest-based sync.
        
        Returns:
            True if sync completed successfully, False if skipped (no changes)
            
        Raises:
            Exception: If manifest sync fails
        """
        # Initialize manifest client if needed
        if self._manifest_client is None:
            self._manifest_client = ManifestSyncClient(
                sftp_client=self.sftp,
                remote_root=self.remote_root,
                cache_dir=self.cache.root_dir,
                jitter_max=self.manifest_sync_jitter
            )
        
        # Progress callback to update our progress
        def progress_callback(completed: int, total: int, current_file: str):
            with self._lock:
                self.progress.current_file = current_file
                # Progress percentage based on files completed
                if total > 0:
                    self.progress.progress_percent = int((completed / total) * 100)
                self._notify_progress()
        
        # Perform sync
        stats = self._manifest_client.sync(progress_callback=progress_callback)
        
        # Check if skipped
        if stats.get("skipped"):
            logger.info(f"Manifest sync skipped: {stats.get('reason')}")
            return False
        
        # Update our progress from manifest sync stats
        with self._lock:
            self.progress.synced_files = stats.get("files_synced", 0)
            self.progress.synced_bytes = stats.get("bytes_downloaded", 0)
            self.progress.progress_percent = 100
        
        # Update cache statistics
        self.cache.update_stat('last_sync', str(time.time()))
        self.cache.update_stat('last_manifest_sync', str(time.time()))
        self.cache.update_stat('manifest_revision', str(stats.get("manifest_revision", 0)))
        
        return True
    
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
        """
        Synchronize experiments metadata with L5 hardening.
        
        L5 improvements:
        - Use listdir_attr to avoid N+1 stats (L1)
        - Filter by recent modification time
        - Limit max experiments per cycle
        - Priority to active runs
        """
        try:
            # L1: Use listdir_attr instead of listdir
            from ..ssh.utils import sftp_listdir_with_attrs
            project_entries = sftp_listdir_with_attrs(self.sftp, self.remote_root)
        except IOError as e:
            logger.warning(f"Failed to list remote root: {e}")
            return
        
        experiments_synced = 0
        cutoff_time = time.time() - self.legacy_recent_seconds if self.legacy_active_only else 0
        
        for project_entry in project_entries:
            if not project_entry.is_dir:
                continue
            
            # Skip special directories
            if project_entry.name in ['artifacts', 'sweeps', '.runicorn']:
                continue
            
            remote_project_path = f"{self.remote_root}/{project_entry.name}"
            
            try:
                # L1: Use listdir_attr
                from ..ssh.utils import sftp_listdir_with_attrs
                exp_entries = sftp_listdir_with_attrs(self.sftp, remote_project_path)
                
                for exp_entry in exp_entries:
                    if not exp_entry.is_dir:
                        continue
                    
                    # L5: Check experiment limit
                    if experiments_synced >= self.legacy_max_experiments:
                        logger.warning(
                            f"Reached max experiments limit ({self.legacy_max_experiments}), "
                            f"deferring remaining experiments"
                        )
                        return
                    
                    remote_exp_path = f"{remote_project_path}/{exp_entry.name}"
                    remote_runs_path = f"{remote_exp_path}/runs"
                    
                    try:
                        # L1: Use listdir_attr for runs
                        from ..ssh.utils import sftp_listdir_with_attrs
                        run_entries = sftp_listdir_with_attrs(self.sftp, remote_runs_path)
                        
                        for run_entry in run_entries:
                            if not run_entry.is_dir:
                                continue
                            
                            # L5: Filter by recent modification time
                            if self.legacy_active_only and run_entry.mtime < cutoff_time:
                                logger.debug(f"Skipping old run: {run_entry.name} (mtime too old)")
                                continue
                            
                            self._sync_run_metadata(
                                project_entry.name,
                                exp_entry.name,
                                run_entry.name,
                                f"{remote_runs_path}/{run_entry.name}"
                            )
                        
                        experiments_synced += 1
                        
                    except IOError:
                        # No runs directory, skip
                        continue
                        
            except Exception as e:
                logger.error(f"Failed to sync project {project_entry.name}: {e}")
                with self._lock:
                    self.progress.errors.append(f"Project {project_entry.name}: {e}")
        
        logger.info(f"Synced {experiments_synced} experiments this cycle")
    
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
        
        # Sync key metadata files (small, always full download)
        metadata_files = [
            "meta.json",
            "status.json",
            "summary.json",
            "environment.json",
            "artifacts_created.json",
            "artifacts_used.json",
        ]
        
        for filename in metadata_files:
            remote_file_path = f"{remote_run_path}/{filename}"
            local_file_path = local_run_dir / filename
            self._sync_file(remote_file_path, local_file_path, required=False)
        
        # L7: Sync append-only files with incremental download
        append_only_files = ["events.jsonl", "logs.txt"]
        
        for filename in append_only_files:
            remote_file_path = f"{remote_run_path}/{filename}"
            local_file_path = local_run_dir / filename
            self._sync_file_incremental(remote_file_path, local_file_path, required=False)
        
        # Sync media directory (images, plots, etc.)
        # These are synced for preview, large files are downloaded on-demand
        remote_media_dir = f"{remote_run_path}/media"
        try:
            media_files = self.sftp.listdir(remote_media_dir)
            local_media_dir = local_run_dir / "media"
            local_media_dir.mkdir(parents=True, exist_ok=True)
            
            for media_file in media_files:
                if media_file.startswith('.'):
                    continue
                remote_media_path = f"{remote_media_dir}/{media_file}"
                local_media_path = local_media_dir / media_file
                # Media files use metadata size limit (1MB) for thumbnails/previews
                self._sync_file(remote_media_path, local_media_path, required=False)
        except IOError:
            # No media directory, skip
            pass
    
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
            
            # Determine size limit based on file type
            # Essential experiment data files can be larger
            filename = remote_path.split('/')[-1]
            is_essential = filename in ['events.jsonl', 'logs.txt']
            max_size = self.MAX_ESSENTIAL_FILE_SIZE if is_essential else self.MAX_METADATA_FILE_SIZE
            
            # Skip files exceeding size limit
            if remote_size > max_size:
                logger.debug(f"Skipping large file: {remote_path} ({remote_size} bytes, limit: {max_size})")
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
    
    def _sync_file_incremental(
        self,
        remote_path: str,
        local_path: Path,
        required: bool = True
    ) -> bool:
        """
        L7: Synchronize append-only file with incremental download.
        
        Only downloads new bytes appended since last sync, avoiding
        re-downloading the entire file.
        
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
            
            # Check size limit
            if remote_size > self.MAX_ESSENTIAL_FILE_SIZE:
                logger.debug(f"Skipping large file: {remote_path} ({remote_size} bytes)")
                return False
            
            # Get cached state
            cached_state = self._append_only_states.get(remote_path, {})
            cached_offset = cached_state.get('offset', 0)
            cached_mtime = cached_state.get('mtime', 0)
            
            # Check if file exists locally
            local_exists = local_path.exists()
            try:
                local_size = local_path.stat().st_size if local_exists else 0
            except (OSError, IOError):
                # File might have been deleted after exists check
                local_exists = False
                local_size = 0
            
            # Determine sync strategy
            need_full_download = False
            need_append = False
            
            if not local_exists:
                # New file: full download
                need_full_download = True
            elif remote_size < local_size:
                # File was truncated: full download
                logger.info(f"File truncated: {remote_path} (remote={remote_size}, local={local_size})")
                need_full_download = True
            elif remote_size == local_size:
                # No change
                if remote_mtime <= cached_mtime:
                    logger.debug(f"File unchanged: {remote_path}")
                    return False
                # Size same but mtime changed - might be rewritten
                need_full_download = True
            else:
                # File grew: append new bytes
                need_append = True
            
            # Update progress
            with self._lock:
                self.progress.current_file = str(remote_path)
                self._notify_progress()
            
            # Ensure parent directory
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            if need_full_download:
                # Full download
                self.sftp.get(remote_path, str(local_path))
                bytes_downloaded = remote_size
                logger.debug(f"Full download: {remote_path} ({bytes_downloaded} bytes)")
                
            elif need_append:
                # Incremental download: only new bytes
                bytes_to_download = remote_size - local_size
                
                with self.sftp.open(remote_path, 'rb') as rf:
                    rf.seek(local_size)  # Seek to end of local file
                    
                    with open(local_path, 'ab') as lf:
                        bytes_downloaded = 0
                        chunk_size = 64 * 1024  # 64KB chunks
                        
                        while bytes_downloaded < bytes_to_download:
                            chunk = rf.read(min(chunk_size, bytes_to_download - bytes_downloaded))
                            if not chunk:
                                break
                            lf.write(chunk)
                            bytes_downloaded += len(chunk)
                
                logger.debug(
                    f"Incremental append: {remote_path} "
                    f"(+{bytes_downloaded} bytes, total={remote_size})"
                )
            else:
                return False
            
            # Set local file mtime
            os.utime(str(local_path), (remote_mtime, remote_mtime))
            
            # Update append-only state
            self._append_only_states[remote_path] = {
                'offset': remote_size,
                'mtime': remote_mtime,
            }
            
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
                self.progress.synced_bytes += bytes_downloaded
                self._notify_progress()
            
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


