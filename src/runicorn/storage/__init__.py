"""
Modern Storage System for Runicorn

This module implements a hybrid SQLite + file storage architecture
that provides high-performance queries while maintaining data transparency.

The storage system supports:
- High-speed metadata queries (SQLite)
- Large file storage (file system)
- Backward compatibility with existing data
- Gradual migration from file-only storage
"""
from __future__ import annotations

from .backends import StorageBackend, FileStorageBackend, SQLiteStorageBackend, HybridStorageBackend
from .models import ExperimentRecord, MetricRecord, QueryParams
from .migration import StorageMigrator
from .file_utils import (
    RunEntry,
    get_storage_root,
    read_json,
    write_json,
    is_process_alive,
    update_status_if_process_dead,
    is_run_deleted,
    soft_delete_run,
    restore_run,
    iter_all_runs,
    find_run_dir_by_id,
    periodic_status_check
)

__all__ = [
    # Storage backends
    "StorageBackend",
    "FileStorageBackend", 
    "SQLiteStorageBackend",
    "HybridStorageBackend",
    # Models
    "ExperimentRecord",
    "MetricRecord", 
    "QueryParams",
    "RunEntry",
    # Migration
    "StorageMigrator",
    # File utilities
    "get_storage_root",
    "read_json",
    "write_json",
    "is_process_alive",
    "update_status_if_process_dead",
    "is_run_deleted",
    "soft_delete_run",
    "restore_run",
    "iter_all_runs",
    "find_run_dir_by_id",
    "periodic_status_check"
]
