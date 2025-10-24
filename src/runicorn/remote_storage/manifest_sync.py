"""
Manifest-Based Sync Client

Client-side implementation for efficient manifest-based synchronization.
Downloads and parses server-generated manifests to sync only changed files.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import paramiko

from ..manifest.models import SyncManifest, FileEntry, ExperimentEntry

logger = logging.getLogger(__name__)


class SyncCursor:
    """
    Tracks synchronization state and progress.
    
    Maintains revision numbers, snapshot IDs, and sync correlation IDs.
    """
    
    def __init__(self, cache_dir: Path):
        """
        Initialize sync cursor.
        
        Args:
            cache_dir: Directory to store cursor state
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.cache_dir / ".sync_cursor.json"
        self._state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load cursor state from file."""
        if not self.state_file.exists():
            return {
                "version": "1.0",
                "last_revision": 0,
                "last_snapshot_id": None,
                "last_sync_time": 0,
                "sync_count": 0,
            }
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cursor state: {e}, resetting")
            return {
                "version": "1.0",
                "last_revision": 0,
                "last_snapshot_id": None,
                "last_sync_time": 0,
                "sync_count": 0,
            }
    
    def _save_state(self) -> None:
        """Save cursor state to file atomically."""
        try:
            # Write to temp file
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, indent=2)
            
            # Atomic rename
            os.replace(str(temp_file), str(self.state_file))
        except Exception as e:
            logger.error(f"Failed to save cursor state: {e}")
    
    def get_last_revision(self) -> int:
        """Get last synced revision number."""
        return self._state.get("last_revision", 0)
    
    def get_last_snapshot_id(self) -> Optional[str]:
        """Get last synced snapshot ID."""
        return self._state.get("last_snapshot_id")
    
    def update(self, revision: int, snapshot_id: str) -> None:
        """
        Update cursor with new sync information.
        
        Args:
            revision: New revision number
            snapshot_id: New snapshot ID
        """
        self._state["last_revision"] = revision
        self._state["last_snapshot_id"] = snapshot_id
        self._state["last_sync_time"] = time.time()
        self._state["sync_count"] = self._state.get("sync_count", 0) + 1
        self._save_state()
        logger.debug(f"Cursor updated: revision={revision}, snapshot={snapshot_id}")


class ManifestSyncClient:
    """
    Manifest-based synchronization client.
    
    Downloads server-generated manifests and syncs only changed files.
    Supports incremental downloads with offset-based resume for append-only files.
    """
    
    # File priorities for sync ordering
    PRIORITY_CRITICAL = 1  # meta.json, status.json
    PRIORITY_HIGH = 2      # summary.json
    PRIORITY_MEDIUM = 3    # events.jsonl, logs.txt
    PRIORITY_LOW = 4       # media files
    
    # Concurrency settings
    MAX_WORKERS = 3
    BATCH_SIZE = 5
    
    # Retry settings
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0  # seconds
    
    def __init__(
        self,
        sftp_client: paramiko.SFTPClient,
        remote_root: str,
        cache_dir: Path,
        jitter_max: float = 5.0
    ):
        """
        Initialize manifest sync client.
        
        Args:
            sftp_client: Active SFTP client
            remote_root: Remote storage root path
            cache_dir: Local cache directory
            jitter_max: Maximum random delay before sync (seconds)
        """
        self.sftp = sftp_client
        self.remote_root = remote_root.rstrip('/')
        self.cache_dir = cache_dir
        self.jitter_max = jitter_max
        
        # Initialize cursor
        self.cursor = SyncCursor(cache_dir)
        
        # State file for tracking synced files
        self.state_file = cache_dir / ".sync_state.json"
        self.local_state: Dict[str, Any] = {}
        
        # Statistics
        self.stats = {
            "files_synced": 0,
            "bytes_downloaded": 0,
            "incremental_count": 0,
            "full_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
        }
        
        logger.info(
            f"ManifestSyncClient initialized: "
            f"remote_root={remote_root}, cache_dir={cache_dir}"
        )
    
    def sync(self, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Perform manifest-based synchronization.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            Statistics dictionary
            
        Raises:
            IOError: If manifest download fails
            ValueError: If manifest validation fails
        """
        start_time = time.time()
        
        # Apply jitter to avoid thundering herd
        if self.jitter_max > 0:
            jitter = random.uniform(0, self.jitter_max)
            logger.debug(f"Applying jitter: {jitter:.2f}s")
            time.sleep(jitter)
        
        try:
            # Download manifest
            manifest = self._download_manifest()
            logger.info(
                f"Downloaded manifest: revision={manifest.revision}, "
                f"experiments={manifest.total_experiments}, files={manifest.total_files}"
            )
            
            # Check if sync needed
            last_revision = self.cursor.get_last_revision()
            if manifest.revision <= last_revision:
                logger.info(f"Manifest not changed (revision {manifest.revision}), skipping sync")
                return {"skipped": True, "reason": "no_changes"}
            
            # Load local state
            self.local_state = self._load_local_state()
            
            # Compute diff
            files_to_sync = self._compute_diff(manifest)
            logger.info(f"Diff computed: {len(files_to_sync)} files to sync")
            
            if not files_to_sync:
                # Update cursor even if no files to sync
                self.cursor.update(manifest.revision, manifest.snapshot_id)
                return {"skipped": True, "reason": "no_file_changes"}
            
            # Sync files
            self._sync_files(files_to_sync, progress_callback)
            
            # Save state
            self._save_local_state()
            
            # Update cursor
            self.cursor.update(manifest.revision, manifest.snapshot_id)
            
            # Compute statistics
            duration = time.time() - start_time
            self.stats["duration"] = duration
            self.stats["manifest_revision"] = manifest.revision
            self.stats["manifest_snapshot_id"] = manifest.snapshot_id
            
            logger.info(
                f"Sync complete: {self.stats['files_synced']} files, "
                f"{self.stats['bytes_downloaded'] / (1024*1024):.2f} MB, "
                f"{duration:.2f}s"
            )
            
            return self.stats
        
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise
    
    def _download_manifest(self) -> SyncManifest:
        """
        Download and parse manifest from server.
        
        Tries active manifest first, falls back to full manifest.
        Prefers gzip compressed version.
        
        Returns:
            Parsed manifest
            
        Raises:
            IOError: If manifest not found
            ValueError: If manifest invalid
        """
        # Manifest files to try (in order)
        manifest_files = [
            "active_manifest.json.gz",
            "active_manifest.json",
            "full_manifest.json.gz",
            "full_manifest.json",
        ]
        
        manifest_dir = f"{self.remote_root}/.runicorn"
        
        for filename in manifest_files:
            manifest_path = f"{manifest_dir}/{filename}"
            
            try:
                logger.debug(f"Trying to download: {manifest_path}")
                
                # Download to temp file
                temp_file = self.cache_dir / f".{filename}.tmp"
                self.sftp.get(manifest_path, str(temp_file))
                
                # Parse manifest
                if filename.endswith('.gz'):
                    with gzip.open(temp_file, 'rt', encoding='utf-8') as f:
                        data = json.load(f)
                else:
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                
                # Validate and parse
                manifest = self._validate_manifest(data)
                
                # Clean up temp file
                temp_file.unlink()
                
                logger.info(f"Successfully downloaded manifest: {filename}")
                return manifest
            
            except FileNotFoundError:
                logger.debug(f"Manifest not found: {manifest_path}")
                continue
            except Exception as e:
                logger.warning(f"Failed to download {manifest_path}: {e}")
                continue
        
        raise IOError("No valid manifest found on server")
    
    def _validate_manifest(self, data: Dict[str, Any]) -> SyncManifest:
        """
        Validate and parse manifest data.
        
        Args:
            data: Raw manifest JSON data
            
        Returns:
            Validated manifest
            
        Raises:
            ValueError: If validation fails
        """
        # Check format version
        format_version = data.get("format_version")
        if not format_version:
            raise ValueError("Missing format_version in manifest")
        
        # Check required fields
        required_fields = ["manifest_type", "revision", "snapshot_id", "experiments"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Check revision
        revision = data.get("revision", 0)
        if not isinstance(revision, int) or revision < 1:
            raise ValueError(f"Invalid revision: {revision}")
        
        # Parse manifest
        try:
            manifest = SyncManifest.from_dict(data)
            return manifest
        except Exception as e:
            raise ValueError(f"Failed to parse manifest: {e}")
    
    def _load_local_state(self) -> Dict[str, Any]:
        """
        Load local sync state.
        
        Returns:
            State dictionary with file tracking information
        """
        if not self.state_file.exists():
            return {"version": "1.0", "files": {}}
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load local state: {e}, resetting")
            return {"version": "1.0", "files": {}}
    
    def _save_local_state(self) -> None:
        """Save local sync state atomically."""
        try:
            # Write to temp file
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.local_state, f, indent=2)
            
            # Atomic rename
            os.replace(str(temp_file), str(self.state_file))
        except Exception as e:
            logger.error(f"Failed to save local state: {e}")
    
    def _compute_diff(self, manifest: SyncManifest) -> List[Tuple[FileEntry, ExperimentEntry, str]]:
        """
        Compute files that need to be synced.
        
        Args:
            manifest: Server manifest
            
        Returns:
            List of (file_entry, experiment_entry, sync_reason) tuples
        """
        files_to_sync = []
        local_files = self.local_state.get("files", {})
        
        for exp in manifest.experiments:
            for file_entry in exp.files:
                # Build local path
                local_path = self.cache_dir / file_entry.path
                
                # Get local file info
                local_info = local_files.get(file_entry.path, {})
                local_size = local_info.get("size", 0)
                local_mtime = local_info.get("mtime", 0)
                
                # Determine if sync needed
                sync_reason = None
                
                if not local_path.exists():
                    sync_reason = "new_file"
                elif file_entry.size != local_size:
                    if file_entry.is_append_only and file_entry.size > local_size:
                        sync_reason = "append_only_grow"
                    else:
                        sync_reason = "size_changed"
                elif file_entry.mtime > local_mtime:
                    sync_reason = "mtime_changed"
                
                if sync_reason:
                    files_to_sync.append((file_entry, exp, sync_reason))
        
        # Sort by priority and size
        files_to_sync.sort(key=lambda x: (x[0].priority, x[0].size))
        
        logger.info(
            f"Diff summary: "
            f"new={sum(1 for _, _, r in files_to_sync if r == 'new_file')}, "
            f"modified={sum(1 for _, _, r in files_to_sync if r != 'new_file')}"
        )
        
        return files_to_sync
    
    def _sync_files(
        self,
        files_to_sync: List[Tuple[FileEntry, ExperimentEntry, str]],
        progress_callback: Optional[callable] = None
    ) -> None:
        """
        Sync files with concurrency control.
        
        Args:
            files_to_sync: List of files to sync
            progress_callback: Optional progress callback
        """
        total_files = len(files_to_sync)
        completed = 0
        
        # Process in batches
        for i in range(0, total_files, self.BATCH_SIZE):
            batch = files_to_sync[i:i + self.BATCH_SIZE]
            
            # Use thread pool for concurrent downloads
            with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
                futures = {
                    executor.submit(self._sync_file, file_entry, exp, reason): (file_entry, exp, reason)
                    for file_entry, exp, reason in batch
                }
                
                for future in as_completed(futures):
                    file_entry, exp, reason = futures[future]
                    
                    try:
                        bytes_downloaded, is_incremental = future.result()
                        
                        self.stats["files_synced"] += 1
                        self.stats["bytes_downloaded"] += bytes_downloaded
                        
                        if is_incremental:
                            self.stats["incremental_count"] += 1
                        else:
                            self.stats["full_count"] += 1
                        
                        # Update local state
                        self.local_state.setdefault("files", {})[file_entry.path] = {
                            "size": file_entry.size,
                            "mtime": file_entry.mtime,
                            "synced_at": time.time(),
                        }
                        
                    except Exception as e:
                        logger.error(f"Failed to sync {file_entry.path}: {e}")
                        self.stats["failed_count"] += 1
                    
                    completed += 1
                    
                    # Progress callback
                    if progress_callback:
                        progress_callback(completed, total_files, file_entry.path)
            
            # Save state periodically
            if i % 50 == 0:
                self._save_local_state()
    
    def _sync_file(
        self,
        file_entry: FileEntry,
        exp: ExperimentEntry,
        reason: str
    ) -> Tuple[int, bool]:
        """
        Sync a single file with retry logic.
        
        Args:
            file_entry: File to sync
            exp: Parent experiment
            reason: Sync reason
            
        Returns:
            Tuple of (bytes_downloaded, is_incremental)
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                return self._sync_file_once(file_entry, exp, reason)
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        f"Retry {attempt + 1}/{self.MAX_RETRIES} for {file_entry.path} "
                        f"after {delay:.1f}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    raise
    
    def _sync_file_once(
        self,
        file_entry: FileEntry,
        exp: ExperimentEntry,
        reason: str
    ) -> Tuple[int, bool]:
        """
        Sync a single file (no retry).
        
        Args:
            file_entry: File to sync
            exp: Parent experiment
            reason: Sync reason
            
        Returns:
            Tuple of (bytes_downloaded, is_incremental)
        """
        # Build paths
        remote_path = f"{self.remote_root}/{file_entry.path}"
        local_path = self.cache_dir / file_entry.path
        
        # Ensure parent directory
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check for incremental download
        is_incremental = False
        bytes_downloaded = 0
        
        if (file_entry.is_append_only and 
            local_path.exists() and 
            reason == "append_only_grow"):
            
            # Incremental download
            local_size = local_path.stat().st_size
            bytes_to_download = file_entry.size - local_size
            
            with self.sftp.open(remote_path, 'rb') as rf:
                rf.seek(local_size)  # Seek to end of local file
                
                with open(local_path, 'ab') as lf:
                    while bytes_downloaded < bytes_to_download:
                        chunk_size = min(256 * 1024, bytes_to_download - bytes_downloaded)
                        chunk = rf.read(chunk_size)
                        if not chunk:
                            break
                        lf.write(chunk)
                        bytes_downloaded += len(chunk)
            
            is_incremental = True
            logger.debug(f"Incremental sync: {file_entry.path} (+{bytes_downloaded} bytes)")
        
        else:
            # Full download
            temp_path = local_path.with_suffix('.tmp')
            self.sftp.get(remote_path, str(temp_path))
            
            # Atomic rename
            os.replace(str(temp_path), str(local_path))
            
            bytes_downloaded = file_entry.size
            logger.debug(f"Full sync: {file_entry.path} ({bytes_downloaded} bytes)")
        
        # Set mtime to match remote
        os.utime(str(local_path), (file_entry.mtime, file_entry.mtime))
        
        return bytes_downloaded, is_incremental
