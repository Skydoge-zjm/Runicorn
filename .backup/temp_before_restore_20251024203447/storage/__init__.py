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

__all__ = [
    "StorageBackend",
    "FileStorageBackend", 
    "SQLiteStorageBackend",
    "HybridStorageBackend",
    "ExperimentRecord",
    "MetricRecord", 
    "QueryParams",
    "StorageMigrator"
]
