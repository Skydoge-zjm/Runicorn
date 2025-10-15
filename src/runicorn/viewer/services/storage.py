"""
Storage Service Layer

Handles all file system operations for experiment data storage.
This service provides a clean interface to the underlying storage mechanism.
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

from ...config import get_user_root_dir
from ...sdk import DEFAULT_DIRNAME, _default_storage_dir

logger = logging.getLogger(__name__)


@dataclass
class RunEntry:
    """Represents a run entry with its metadata."""
    project: Optional[str]
    name: Optional[str]
    dir: Path


def get_storage_root(storage: Optional[str] = None) -> Path:
    """
    Get the storage root directory and ensure it exists.
    
    Args:
        storage: Optional storage directory override
        
    Returns:
        Path to storage root directory
    """
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
        
        pid = meta.get("pid")
        if pid and not is_process_alive(pid):
            # Process is dead, mark as failed
            status.update({
                "status": "failed",
                "ended_at": time.time(),
                "exit_reason": "process_not_found"
            })
            status_path.write_text(
                json.dumps(status, ensure_ascii=False, indent=2), 
                encoding="utf-8"
            )
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


def soft_delete_run(run_dir: Path, reason: str = "user_deleted") -> bool:
    """
    Mark a run as deleted by creating .deleted marker file.
    
    Args:
        run_dir: Path to the run directory
        reason: Reason for deletion
        
    Returns:
        True if successful, False otherwise
    """
    try:
        deleted_info = {
            "deleted_at": time.time(),
            "reason": reason,
            "original_status": read_json(run_dir / "status.json").get("status", "unknown")
        }
        deleted_file = run_dir / ".deleted"
        deleted_file.write_text(
            json.dumps(deleted_info, ensure_ascii=False, indent=2), 
            encoding="utf-8"
        )
        logger.info(f"Soft deleted run: {run_dir.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to soft delete run {run_dir.name}: {e}")
        return False


def restore_run(run_dir: Path) -> bool:
    """
    Restore a soft-deleted run by removing .deleted marker.
    
    Args:
        run_dir: Path to the run directory
        
    Returns:
        True if successful, False otherwise
    """
    try:
        deleted_file = run_dir / ".deleted"
        if deleted_file.exists():
            deleted_file.unlink()
            logger.info(f"Restored run: {run_dir.name}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to restore run {run_dir.name}: {e}")
        return False


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
    
    New layout:   root/<project>/<name>/runs/<run_id>
    Legacy layout: root/runs/<run_id>
    
    Args:
        root: Storage root directory
        include_deleted: Whether to include soft-deleted runs
        
    Returns:
        List of run entries
    """
    entries: List[RunEntry] = []
    
    # New layout: project/name/runs/*
    try:
        for proj in sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
            # Skip well-known non-project dirs
            if proj.name in {"runs", "webui"}:
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
                    entries.append(RunEntry(project=proj.name, name=name.name, dir=rd))
    except Exception as e:
        logger.debug(f"Error scanning new layout: {e}")
    
    # Legacy layout fallback
    try:
        for rd in list_run_dirs_legacy(root):
            # Filter out soft-deleted runs unless explicitly requested
            if not include_deleted and is_run_deleted(rd):
                continue
            # project/name can be inferred from meta.json if present; leave None here
            entries.append(RunEntry(project=None, name=None, dir=rd))
    except Exception as e:
        logger.debug(f"Error scanning legacy layout: {e}")
    
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


async def periodic_status_check(root: Path) -> None:
    """
    Periodically check and update status of running experiments.
    
    This runs as a background task to detect crashed/interrupted experiments.
    
    Args:
        root: Storage root directory
    """
    while True:
        try:
            # Check all running experiments
            for entry in iter_all_runs(root):
                try:
                    status = read_json(entry.dir / "status.json")
                    if status.get("status") == "running":
                        update_status_if_process_dead(entry.dir)
                except Exception as entry_error:
                    # Don't let one bad entry crash the whole checker
                    logger.debug(f"Error checking status for {entry.dir.name}: {entry_error}")
                    continue
            
            # Wait 30 seconds before next check
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            logger.info("Status check task cancelled")
            break
        except Exception as e:
            # Log but don't crash - keep checking
            logger.error(f"Status check task error: {e}", exc_info=True)
            await asyncio.sleep(30)  # Continue checking despite errors
