"""
File System Utilities for Storage Operations

Provides low-level file system operations for experiment data storage.
These utilities are used by both the storage backends and the viewer services.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import psutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RunEntry:
    """Represents a run entry with its metadata."""
    path: Optional[str]  # Flexible hierarchy path (e.g., "cv/detection/yolo")
    dir: Path
    
    # Legacy compatibility - derive from path
    @property
    def project(self) -> Optional[str]:
        """Get first part of path for legacy compatibility."""
        if not self.path:
            return None
        parts = self.path.split("/")
        return parts[0] if parts else None
    
    @property
    def name(self) -> Optional[str]:
        """Get last part of path for legacy compatibility."""
        if not self.path:
            return None
        parts = self.path.split("/")
        return parts[-1] if parts else None


def get_storage_root(storage: Optional[str] = None) -> Path:
    """
    Get the storage root directory and ensure it exists.
    
    Args:
        storage: Optional storage directory override
        
    Returns:
        Path to storage root directory
    """
    from ..sdk import _default_storage_dir
    root = _default_storage_dir(storage)
    root.mkdir(parents=True, exist_ok=True)
    (root / "runs").mkdir(parents=True, exist_ok=True)
    return root


def read_json(path: Path) -> Dict[str, Any]:
    """
    Safely read a JSON file.
    
    Args:
        path: Path to JSON file
        
    Returns:
        Dictionary with file contents, empty dict if file doesn't exist or is invalid
    """
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.debug(f"Failed to read JSON file {path}: {e}")
        return {}


def write_json(path: Path, data: Dict[str, Any]) -> bool:
    """
    Safely write data to a JSON file.
    
    Args:
        path: Path to JSON file
        data: Data to write
        
    Returns:
        True if successful, False otherwise
    """
    try:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to write JSON file {path}: {e}")
        return False


def is_process_alive(pid: Optional[int]) -> bool:
    """
    Check if a process is still running.
    
    Args:
        pid: Process ID to check
        
    Returns:
        True if process is still running, False otherwise
    """
    if pid is None:
        return False
    
    try:
        return psutil.pid_exists(pid)
    except Exception:
        # Fallback to basic method if psutil is not available
        try:
            if os.name == 'nt':  # Windows
                import subprocess
                result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                      capture_output=True, text=True, timeout=5)
                return str(pid) in result.stdout
            else:  # Unix/Linux
                os.kill(pid, 0)  # Signal 0 just checks if process exists
                return True
        except (OSError, subprocess.SubprocessError, ProcessLookupError):
            return False
        except Exception:
            return False


def update_status_if_process_dead(run_dir: Path) -> None:
    """
    Update run status to 'failed' if the process is no longer running.
    
    NOTE: Only checks local processes. Skips remote runs (identified by different hostname).
    
    Args:
        run_dir: Path to the run directory
    """
    try:
        meta_path = run_dir / "meta.json"
        status_path = run_dir / "status.json"
        
        if not meta_path.exists() or not status_path.exists():
            return
        
        meta = read_json(meta_path)
        status = read_json(status_path)
        
        # Only check if status is currently "running"
        if status.get("status") != "running":
            return
        
        # Skip PID check for remote runs
        import socket
        local_hostname = socket.gethostname()
        run_hostname = meta.get("hostname")
        
        # Check if this is a remote/synced run (skip PID check)
        run_path_str = str(run_dir)
        run_path_lower = run_path_str.lower()
        
        # Check 1: Different hostname (remote machine)
        if run_hostname and run_hostname != local_hostname:
            logger.debug(f"Skipping PID check for remote run {run_dir.name} (remote host: {run_hostname})")
            return
        
        # Check 2: In a remote cache directory
        # Note: With VSCode Remote-like architecture, we only cache metadata locally
        is_remote_cache = any(marker in run_path_lower for marker in [
            '.runicorn_remote_cache',  # Remote viewer cache directory
            'remote_cache',
            '_remote_',
        ])
        
        if is_remote_cache:
            logger.debug(f"Skipping PID check for remote cached run {run_dir.name}")
            return
        
        pid = meta.get("pid")
        if pid and not is_process_alive(pid):
            # Process is dead, mark as failed
            status.update({
                "status": "failed",
                "ended_at": time.time(),
                "exit_reason": "process_not_found"
            })
            write_json(status_path, status)
            logger.info(f"Run {run_dir.name} marked as failed (PID {pid} not found)")
    except Exception as e:
        logger.debug(f"Failed to update status for {run_dir.name}: {e}")


def is_run_deleted(run_dir: Path) -> bool:
    """
    Check if a run is marked as deleted (soft delete).
    
    Args:
        run_dir: Path to the run directory
        
    Returns:
        True if run is soft deleted, False otherwise
    """
    return (run_dir / ".deleted").exists()


def soft_delete_run(
    run_dir: Path,
    storage_root: Path,
    reason: str = "user_deleted",
    original_path: str | None = None,
) -> tuple[bool, str | None, Path | None]:
    """
    Soft-delete a run by marking it and moving it to ``runs/.recycle/<run_id>``.
    
    Args:
        run_dir: Path to the run directory
        storage_root: Storage root directory
        reason: Reason for deletion
        original_path: Original path in the tree (stored for restore)
        
    Returns:
        (success, error_message, recycle_run_dir) tuple
    """
    try:
        deleted_file = run_dir / ".deleted"
        deleted_info = read_json(deleted_file) if deleted_file.exists() else {}
        if not isinstance(deleted_info, dict):
            deleted_info = {}

        # Best-effort path inference for restore
        meta = read_json(run_dir / "meta.json")
        inferred_path = (
            original_path
            or deleted_info.get("original_path")
            or (meta.get("path") if isinstance(meta, dict) else None)
        )
        if not inferred_path:
            try:
                runs_root = storage_root / "runs"
                rel_parent = run_dir.parent.relative_to(runs_root)
                rel_str = rel_parent.as_posix()
                if rel_str and rel_str not in {".", ".recycle"} and not rel_str.startswith(".recycle/"):
                    inferred_path = rel_str
            except Exception:
                pass

        # Ensure marker content exists/complete
        deleted_info.setdefault("deleted_at", time.time())
        deleted_info.setdefault("reason", reason)
        deleted_info.setdefault(
            "original_status",
            read_json(run_dir / "status.json").get("status", "unknown"),
        )
        if inferred_path:
            deleted_info["original_path"] = inferred_path

        deleted_file = run_dir / ".deleted"
        if not write_json(deleted_file, deleted_info):
            return False, "marker_write_failed", None

        # Move into recycle bin (unified delete location)
        in_recycle = ".recycle" in run_dir.parts
        if not in_recycle:
            recycle_root = storage_root / "runs" / ".recycle"
            recycle_root.mkdir(parents=True, exist_ok=True)
            target_dir = recycle_root / run_dir.name
            if target_dir.exists():
                logger.warning(f"Recycle target already exists: {target_dir}")
                return False, "conflict", None
            import shutil
            shutil.move(str(run_dir), str(target_dir))
            run_dir = target_dir

        logger.info(f"Soft deleted run to recycle: {run_dir.name}")
        return True, None, run_dir
    except Exception as e:
        logger.error(f"Failed to soft delete run {run_dir.name}: {e}")
        return False, str(e), None


def restore_run(
    run_dir: Path,
    storage_root: Path | None = None,
) -> tuple[bool, str | None, Path | None]:
    """
    Restore a soft-deleted run.

    If the run lives under ``.recycle`` (moved there by folder-delete),
    it is moved back to its original path first.

    Returns:
        (success, error_message, new_run_dir) tuple.
        *new_run_dir* is the directory the run now lives in (may differ
        from the input *run_dir* when the run was moved out of .recycle).
    """
    try:
        deleted_file = run_dir / ".deleted"
        if not deleted_file.exists():
            return False, "not_deleted", None

        deleted_info = read_json(deleted_file)

        # Unified flow: deleted runs should live in .recycle and must be moved back.
        in_recycle = ".recycle" in run_dir.parts
        if in_recycle:
            if storage_root is None:
                return False, "storage_root_required", None
            original_path = (
                deleted_info.get("original_path")
                if isinstance(deleted_info, dict)
                else None
            )
            if not original_path:
                meta = read_json(run_dir / "meta.json")
                original_path = meta.get("path") if isinstance(meta, dict) else None
            if not original_path:
                return False, "missing_original_path", None

            target_parent = storage_root / "runs" / original_path
            target_parent.mkdir(parents=True, exist_ok=True)
            target_dir = target_parent / run_dir.name
            if target_dir.exists():
                logger.warning(f"Restore target already exists: {target_dir}")
                return False, "conflict", None
            import shutil
            shutil.move(str(run_dir), str(target_dir))
            run_dir = target_dir
            logger.info(f"Moved run {run_dir.name} back from .recycle to {original_path}")

        # Remove .deleted marker
        marker = run_dir / ".deleted"
        if marker.exists():
            marker.unlink()
        logger.info(f"Restored run: {run_dir.name}")
        return True, None, run_dir
    except Exception as e:
        logger.error(f"Failed to restore run {run_dir.name}: {e}")
        return False, str(e), None


def list_run_dirs_legacy(root: Path) -> List[Path]:
    """
    List run directories in legacy layout (root/runs/*).
    
    Args:
        root: Storage root directory
        
    Returns:
        List of run directories sorted by modification time (newest first)
    """
    runs_dir = root / "runs"
    if not runs_dir.exists():
        return []
    return sorted(
        [p for p in runs_dir.iterdir() if p.is_dir()], 
        key=lambda p: p.stat().st_mtime, 
        reverse=True
    )


def iter_all_runs(root: Path, include_deleted: bool = False) -> List[RunEntry]:
    """
    Discover runs in both new and legacy layouts.
    
    New layout:   root/runs/<path>/<run_id>
    Legacy layout: root/<project>/<name>/runs/<run_id>
    
    Args:
        root: Storage root directory
        include_deleted: Whether to include soft-deleted runs
        
    Returns:
        List of run entries
    """
    entries: List[RunEntry] = []
    
    # New layout: root/runs/<path>/<run_id>
    runs_root = root / "runs"
    if runs_root.exists():
        try:
            entries.extend(_scan_runs_recursive(runs_root, "", include_deleted))
        except Exception as e:
            logger.debug(f"Error scanning new layout: {e}")
    
    # Legacy layout: root/<project>/<name>/runs/<run_id>
    try:
        for proj in sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
            # Skip well-known non-project dirs
            if proj.name in {"runs", "webui", "archive", "index"}:
                continue
            for name in sorted([n for n in proj.iterdir() if n.is_dir()], key=lambda p: p.name.lower()):
                runs_dir = name / "runs"
                if not runs_dir.exists():
                    continue
                for rd in sorted([p for p in runs_dir.iterdir() if p.is_dir()], 
                                key=lambda p: p.stat().st_mtime, reverse=True):
                    # Filter out soft-deleted runs unless explicitly requested
                    if not include_deleted and is_run_deleted(rd):
                        continue
                    # Convert legacy project/name to path
                    legacy_path = f"{proj.name}/{name.name}"
                    entries.append(RunEntry(path=legacy_path, dir=rd))
    except Exception as e:
        logger.debug(f"Error scanning legacy layout: {e}")
    
    return entries


def _scan_runs_recursive(
    current_dir: Path, 
    current_path: str, 
    include_deleted: bool
) -> List[RunEntry]:
    """
    Recursively scan for run directories.
    
    A directory is considered a run if it contains meta.json or status.json.
    Otherwise, it's treated as a path segment.
    """
    entries: List[RunEntry] = []
    
    try:
        for item in sorted(current_dir.iterdir(), key=lambda p: p.name.lower()):
            if not item.is_dir():
                continue
            # Skip .recycle for normal listing; include it when scanning deleted runs
            if item.name == ".recycle" and not include_deleted:
                continue
            
            # Check if this is a run directory (has meta.json or status.json)
            is_run = (item / "meta.json").exists() or (item / "status.json").exists()
            
            if is_run:
                # Unified model: active listing excludes .recycle entirely.
                # No per-run .deleted check is needed in the normal path.
                # This is a run directory
                entries.append(RunEntry(path=current_path or None, dir=item))
            else:
                # This is a path segment, recurse
                new_path = f"{current_path}/{item.name}" if current_path else item.name
                entries.extend(_scan_runs_recursive(item, new_path, include_deleted))
    except Exception as e:
        logger.debug(f"Error scanning {current_dir}: {e}")
    
    return entries


def find_run_dir_by_id(root: Path, run_id: str, include_deleted: bool = False) -> Optional[RunEntry]:
    """
    Find a run directory by its ID.
    
    Args:
        root: Storage root directory
        run_id: Run ID to search for
        include_deleted: Whether to include soft-deleted runs
        
    Returns:
        RunEntry if found, None otherwise
    """
    for entry in iter_all_runs(root, include_deleted=include_deleted):
        if entry.dir.name == run_id:
            return entry
    return None


async def periodic_status_check(root: Path, backend=None) -> None:
    """
    Periodically check and update status of running experiments.
    
    This runs as a background task to detect crashed/interrupted experiments.
    When *backend* (SQLiteStorageBackend) is given, only running experiments
    are queried, and status changes are dual-written to SQLite.
    
    Args:
        root: Storage root directory
        backend: Optional SQLiteStorageBackend for targeted queries
    """
    while True:
        try:
            if backend is not None:
                # SQLite fast-path: only check experiments marked as running
                try:
                    running_exps = backend.get_running_experiments()
                    for exp in running_exps:
                        try:
                            run_dir = Path(exp.run_dir) if exp.run_dir else None
                            if run_dir and run_dir.exists():
                                update_status_if_process_dead(run_dir)
                                # Check if status changed and dual-write
                                new_status = read_json(run_dir / "status.json")
                                new_val = str((new_status.get("status") if isinstance(new_status, dict) else "running") or "running")
                                if new_val != "running":
                                    try:
                                        backend.update_experiment(exp.experiment_id, {"status": new_val})
                                    except Exception:
                                        pass
                        except Exception as entry_error:
                            logger.debug(f"Error checking status for {exp.experiment_id}: {entry_error}")
                except Exception:
                    pass  # fall through; next cycle will retry
            else:
                # File-system fallback
                for entry in iter_all_runs(root):
                    try:
                        status = read_json(entry.dir / "status.json")
                        if status.get("status") == "running":
                            update_status_if_process_dead(entry.dir)
                    except Exception as entry_error:
                        logger.debug(f"Error checking status for {entry.dir.name}: {entry_error}")
                        continue
            
            # Wait 60 seconds before next check
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Status check task cancelled")
            break
        except Exception as e:
            logger.error(f"Status check task error: {e}", exc_info=True)
            await asyncio.sleep(30)
