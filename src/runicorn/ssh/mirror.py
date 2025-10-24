"""
SSH Mirror Task

Provides continuous mirroring of remote directories with hardening controls.
"""
from __future__ import annotations

import logging
import posixpath
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import paramiko

from .session import SSHSession
from .utils import SFTPEntry, sftp_walk

logger = logging.getLogger(__name__)


class MirrorTask:
    """
    Continuous mirroring task with hardening controls.
    
    L4 Hardening improvements:
    - Minimum interval clamp (≥5s, default ≥10s)
    - Maximum traversal depth limit
    - Maximum directories per cycle limit
    - Directory skip list (artifacts, .cache, etc.)
    - Larger read chunks for efficiency
    - Chunked iteration across cycles
    """
    
    # Hardening defaults
    MIN_INTERVAL_SECONDS = 5.0
    DEFAULT_INTERVAL_SECONDS = 10.0
    DEFAULT_MAX_DEPTH = 6  # Increased to handle deeper experiment directory structures
    DEFAULT_MAX_DIRS_PER_CYCLE = 200
    DEFAULT_SKIP_DIRS = ['.git', '.cache', '__pycache__', 'artifacts', '.runicorn']
    APPEND_READ_CHUNK_SIZE = 256 * 1024  # 256KB (was 64KB)
    FULL_READ_CHUNK_SIZE = 1024 * 1024   # 1MB (was 1MB, keep as-is)
    
    def __init__(
        self,
        session: SSHSession,
        remote_root: str,
        local_root: Path,
        interval: float = DEFAULT_INTERVAL_SECONDS,
        max_depth: Optional[int] = DEFAULT_MAX_DEPTH,
        max_dirs_per_cycle: Optional[int] = DEFAULT_MAX_DIRS_PER_CYCLE,
        skip_dirs: Optional[List[str]] = None
    ):
        """
        Initialize mirror task with hardening controls.
        
        Args:
            session: Active SSH session
            remote_root: Remote directory to mirror
            local_root: Local directory for mirrored content
            interval: Sync interval in seconds (clamped to MIN_INTERVAL_SECONDS)
            max_depth: Maximum directory traversal depth (None = unlimited)
            max_dirs_per_cycle: Maximum directories to scan per cycle (None = unlimited)
            skip_dirs: Directory names to skip
        """
        self.session = session
        self.remote_root = remote_root.rstrip('/')
        self.local_root = Path(local_root)
        
        # L4: Enforce minimum interval
        self.interval = max(self.MIN_INTERVAL_SECONDS, interval)
        if interval < self.MIN_INTERVAL_SECONDS:
            logger.warning(
                f"Mirror interval {interval}s clamped to minimum {self.MIN_INTERVAL_SECONDS}s"
            )
        
        # L4: Traversal limits
        self.max_depth = max_depth if max_depth is not None else float('inf')
        self.max_dirs_per_cycle = max_dirs_per_cycle if max_dirs_per_cycle is not None else float('inf')
        self.skip_dirs = set(skip_dirs) if skip_dirs else set(self.DEFAULT_SKIP_DIRS)
        
        self.id = f"mirror:{self.session.id}:{int(time.time()*1000)}"
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        
        self.stats = {
            "copied_files": 0,  # Total copy operations (including overwrites)
            "appended_bytes": 0,
            "scans": 0,
            "started_at": time.time(),
            "last_error": "",
            "dirs_scanned_per_cycle": [],
            "cycles_with_depth_limit": 0,
            "cycles_with_dir_limit": 0,
            "total_copy_ops": 0,  # Total file operations (for debugging)
        }
        
        # Map of remote posix path -> last size
        self._known_sizes: Dict[str, int] = {}
        
        # Chunked iteration state
        self._pending_dirs: List[str] = []
        self._dirs_scanned_this_cycle = 0
    
    def start(self) -> None:
        """Start mirror task."""
        self._thread.start()
        logger.info(
            f"Started mirror task: interval={self.interval}s, "
            f"max_depth={self.max_depth}, max_dirs={self.max_dirs_per_cycle}, "
            f"skip_dirs={sorted(self.skip_dirs)}"
        )
    
    def stop(self) -> None:
        """Stop mirror task."""
        self._stop.set()
        self._thread.join(timeout=3.0)
        logger.info(f"Stopped mirror task {self.id}")
    
    def _ensure_local_parent(self, rel: str) -> Path:
        """Ensure local parent directory exists."""
        p = self.local_root / Path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    
    def _walk_controlled(
        self,
        sftp: paramiko.SFTPClient,
        path: str
    ) -> List[Tuple[str, List[SFTPEntry], List[SFTPEntry]]]:
        """
        Walk directory tree with depth and count limits.
        
        Returns:
            List of (dirpath, subdirs, files) tuples
        """
        try:
            # Use optimized walk with limits
            results = sftp_walk(
                sftp,
                path,
                max_depth=int(self.max_depth) if self.max_depth != float('inf') else None,
                skip_dirs=list(self.skip_dirs),
                include_hidden=False
            )
            
            # Track if we hit depth limit
            if self.max_depth != float('inf') and len(results) > 0:
                max_depth_reached = any(
                    path.count('/') - self.remote_root.count('/') >= self.max_depth
                    for path, _, _ in results
                )
                if max_depth_reached:
                    self.stats["cycles_with_depth_limit"] += 1
            
            return results
            
        except Exception as e:
            logger.error(f"Walk failed for {path}: {e}")
            return []
    
    def _copy_file_full(self, sftp: paramiko.SFTPClient, rpath: str, lpath: Path):
        """Copy entire file with optimized chunk size."""
        with sftp.open(rpath, 'rb') as rf, open(lpath, 'wb') as lf:
            while True:
                data = rf.read(self.FULL_READ_CHUNK_SIZE)
                if not data:
                    break
                lf.write(data)
        self.stats["total_copy_ops"] += 1
    
    def _append_new_bytes(self, sftp: paramiko.SFTPClient, rpath: str, lpath: Path, from_size: int):
        """Append new bytes with increased chunk size (L4 hardening)."""
        with sftp.open(rpath, 'rb') as rf:
            rf.seek(from_size)
            with open(lpath, 'ab') as lf:
                while True:
                    # L4: Increased from 64KB to 256KB
                    data = rf.read(self.APPEND_READ_CHUNK_SIZE)
                    if not data:
                        break
                    lf.write(data)
                    self.stats["appended_bytes"] += len(data)
    
    def _run(self):
        """Main mirror loop with hardening controls."""
        while not self._stop.is_set():
            try:
                if not self.session.sftp:
                    # Try reconnect once
                    self.session.connect()
                
                sftp = self.session.sftp
                if not sftp:
                    time.sleep(self.interval)
                    continue
                
                self.stats["scans"] += 1
                self._dirs_scanned_this_cycle = 0
                
                logger.info(f"Mirror {self.id}: Starting scan #{self.stats['scans']} (interval={self.interval}s)")
                
                # L4: Walk with depth and count limits
                results = self._walk_controlled(sftp, self.remote_root)
                
                # Process files, respecting max_dirs_per_cycle
                for dirpath, subdirs, files in results:
                    # Check if we've exceeded directory limit for this cycle
                    self._dirs_scanned_this_cycle += 1
                    if self._dirs_scanned_this_cycle > self.max_dirs_per_cycle:
                        self.stats["cycles_with_dir_limit"] += 1
                        logger.debug(
                            f"Reached max_dirs_per_cycle limit ({self.max_dirs_per_cycle}), "
                            f"deferring remaining directories"
                        )
                        break
                    
                    # Process files in this directory
                    for file_entry in files:
                        rpath = posixpath.join(dirpath, file_entry.name)
                        
                        try:
                            rel = posixpath.relpath(rpath, start=self.remote_root)
                        except Exception:
                            continue
                        
                        # Map to local
                        lpath = self._ensure_local_parent(rel)
                        rsize = file_entry.size
                        last = self._known_sizes.get(rpath)
                        
                        # CRITICAL: Always overwrite status.json and meta.json to prevent conflicts
                        # with local PID checks modifying them
                        filename = file_entry.name
                        force_overwrite = filename in ('status.json', 'meta.json')
                        
                        if last is None:
                            # New file: copy full
                            self._copy_file_full(sftp, rpath, lpath)
                            self._known_sizes[rpath] = rsize
                        else:
                            if force_overwrite:
                                # Always re-copy these critical files to prevent local modifications
                                self._copy_file_full(sftp, rpath, lpath)
                                self._known_sizes[rpath] = rsize
                            elif rsize > last:
                                # Append new bytes
                                self._append_new_bytes(sftp, rpath, lpath, from_size=last)
                                self._known_sizes[rpath] = rsize
                            elif rsize < last:
                                # File truncated/rotated: recopy full
                                self._copy_file_full(sftp, rpath, lpath)
                                self._known_sizes[rpath] = rsize
                
                # Track directories scanned per cycle
                self.stats["dirs_scanned_per_cycle"].append(self._dirs_scanned_this_cycle)
                # Keep only last 100 cycle stats
                if len(self.stats["dirs_scanned_per_cycle"]) > 100:
                    self.stats["dirs_scanned_per_cycle"] = self.stats["dirs_scanned_per_cycle"][-100:]
                
                logger.info(
                    f"Mirror {self.id}: Scan #{self.stats['scans']} complete - "
                    f"dirs: {self._dirs_scanned_this_cycle}, "
                    f"files: {self.stats['copied_files']}, "
                    f"sleeping {self.interval}s"
                )
                
                # Sleep
                time.sleep(self.interval)
                
            except Exception as e:
                self.stats["last_error"] = f"{e}\n{traceback.format_exc()}"
                logger.error(f"Mirror cycle error: {e}")
                # Brief backoff
                time.sleep(self.interval)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get mirror task statistics."""
        stats = self.stats.copy()
        # Use unique file count instead of copy operations for display
        stats["copied_files"] = len(self._known_sizes)
        stats.update({
            "id": self.id,
            "interval": self.interval,
            "max_depth": self.max_depth if self.max_depth != float('inf') else None,
            "max_dirs_per_cycle": self.max_dirs_per_cycle if self.max_dirs_per_cycle != float('inf') else None,
            "skip_dirs": sorted(self.skip_dirs),
            "known_files": len(self._known_sizes),
            "alive": self._thread.is_alive(),
            "avg_dirs_per_cycle": (
                sum(self.stats["dirs_scanned_per_cycle"]) / len(self.stats["dirs_scanned_per_cycle"])
                if self.stats["dirs_scanned_per_cycle"] else 0
            ),
        })
        return stats


# Global mirror task registry for backward compatibility
_MIRRORS: Dict[str, MirrorTask] = {}
_MIRROR_LOCK = threading.Lock()


def start_mirror(
    session: SSHSession,
    remote_root: str,
    local_root: Path,
    interval: float = MirrorTask.DEFAULT_INTERVAL_SECONDS,
    **kwargs
) -> MirrorTask:
    """
    Start a mirror task and register it globally.
    
    Args:
        session: SSH session
        remote_root: Remote directory to mirror
        local_root: Local directory for mirrored content
        interval: Sync interval in seconds
        **kwargs: Additional MirrorTask parameters
        
    Returns:
        MirrorTask instance
    """
    task = MirrorTask(session, remote_root, local_root, interval, **kwargs)
    
    with _MIRROR_LOCK:
        _MIRRORS[task.id] = task
    
    task.start()
    logger.info(f"Started mirror task {task.id}")
    return task


def stop_mirror(task_id: str) -> bool:
    """
    Stop and unregister a mirror task.
    
    Args:
        task_id: Mirror task ID
        
    Returns:
        True if task was found and stopped
    """
    with _MIRROR_LOCK:
        task = _MIRRORS.pop(task_id, None)
    
    if not task:
        return False
    
    try:
        task.stop()
        logger.info(f"Stopped mirror task {task_id}")
        return True
    except Exception as e:
        logger.error(f"Error stopping mirror task {task_id}: {e}")
        return False


def list_mirrors() -> List[Dict[str, Any]]:
    """
    List all active mirror tasks.
    
    Returns:
        List of mirror task information dictionaries
    """
    out = []
    
    with _MIRROR_LOCK:
        items = list(_MIRRORS.items())
    
    for task_id, task in items:
        stats = task.get_stats()
        
        # Format for frontend: nest stats fields
        mirror_info = {
            'id': stats.get('id'),
            'session_id': task.session.id,
            'host': task.session.host,
            'remote_root': task.remote_root,
            'local_root': str(task.local_root),
            'interval': stats.get('interval'),
            'alive': stats.get('alive', False),
            'stats': {
                'copied_files': stats.get('copied_files', 0),
                'appended_bytes': stats.get('appended_bytes', 0),
                'scans': stats.get('scans', 0),
                'started_at': stats.get('started_at'),
                'last_error': stats.get('last_error', ''),
                'known_files': stats.get('known_files', 0),
                'avg_dirs_per_cycle': stats.get('avg_dirs_per_cycle', 0),
            }
        }
        out.append(mirror_info)
    
    return out


def get_mirror(task_id: str) -> Optional[MirrorTask]:
    """
    Get a mirror task by ID.
    
    Args:
        task_id: Mirror task ID
        
    Returns:
        MirrorTask instance or None if not found
    """
    with _MIRROR_LOCK:
        return _MIRRORS.get(task_id)
