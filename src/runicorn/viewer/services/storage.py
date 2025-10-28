"""Storage Service Layer (Compatibility Wrapper)

This module provides backward compatibility by re-exporting storage utilities
from the main storage.file_utils module.

For new code, prefer importing directly from storage.file_utils:
    from runicorn.storage.file_utils import get_storage_root, iter_all_runs, ...
"""
from __future__ import annotations

import logging

# Re-export all utilities from the unified storage module
from ...storage.file_utils import (
    RunEntry,
    get_storage_root,
    read_json,
    write_json,
    is_process_alive,
    update_status_if_process_dead,
    is_run_deleted,
    soft_delete_run,
    restore_run,
    list_run_dirs_legacy,
    iter_all_runs,
    find_run_dir_by_id,
    periodic_status_check
)

logger = logging.getLogger(__name__)

# All implementations have been moved to storage.file_utils
# This file now serves as a compatibility layer

__all__ = [
    "RunEntry",
    "get_storage_root",
    "read_json",
    "write_json",
    "is_process_alive",
    "update_status_if_process_dead",
    "is_run_deleted",
    "soft_delete_run",
    "restore_run",
    "list_run_dirs_legacy",
    "iter_all_runs",
    "find_run_dir_by_id",
    "periodic_status_check"
]
