"""
Storage Backend Implementations

Provides different storage backend implementations including file-based,
SQLite-based, and hybrid approaches.
"""
from __future__ import annotations

import logging
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
import threading
import queue

from ._sqlite_backend import assets as asset_ops
from ._sqlite_backend import experiments as experiment_ops
from ._sqlite_backend import metrics as metric_ops
from ._sqlite_backend import schema as schema_ops
from ._sqlite_backend import viewer_queries as viewer_query_ops
from .models import ExperimentRecord, MetricRecord, QueryParams, StorageStats

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.

    This defines the interface that all storage backends must implement.
    """

    @abstractmethod
    def create_experiment(self, experiment: ExperimentRecord) -> str:
        """
        Create a new experiment record.

        Args:
            experiment: Experiment record to create

        Returns:
            Created experiment ID
        """
        pass

    @abstractmethod
    def update_experiment(self, exp_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update experiment metadata.

        Args:
            exp_id: Experiment ID to update
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_experiment(self, exp_id: str) -> Optional[ExperimentRecord]:
        """
        Retrieve a single experiment by ID.

        Args:
            exp_id: Experiment ID to retrieve

        Returns:
            Experiment record if found, None otherwise
        """
        pass

    @abstractmethod
    def list_experiments(self, query: QueryParams) -> List[ExperimentRecord]:
        """
        List experiments matching query parameters.

        Args:
            query: Query parameters for filtering and pagination

        Returns:
            List of matching experiment records
        """
        pass

    @abstractmethod
    def count_experiments(self, query: QueryParams) -> int:
        """
        Count experiments matching query parameters.

        Args:
            query: Query parameters for filtering

        Returns:
            Number of matching experiments
        """
        pass

    @abstractmethod
    def log_metrics(self, exp_id: str, metrics: List[MetricRecord]) -> bool:
        """
        Log metric data points for an experiment.

        Args:
            exp_id: Experiment ID
            metrics: List of metric records to store

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_metrics(self, exp_id: str, metric_names: Optional[List[str]] = None) -> List[MetricRecord]:
        """
        Retrieve metric data for an experiment.

        Args:
            exp_id: Experiment ID
            metric_names: Optional list of specific metrics to retrieve

        Returns:
            List of metric records
        """
        pass

    @abstractmethod
    def soft_delete_experiments(self, exp_ids: List[str], reason: str = "user_deleted") -> Dict[str, bool]:
        """
        Soft delete experiments.

        Args:
            exp_ids: List of experiment IDs to delete
            reason: Reason for deletion

        Returns:
            Dictionary mapping experiment ID to success status
        """
        pass

    @abstractmethod
    def restore_experiments(self, exp_ids: List[str]) -> Dict[str, bool]:
        """
        Restore soft-deleted experiments.

        Args:
            exp_ids: List of experiment IDs to restore

        Returns:
            Dictionary mapping experiment ID to success status
        """
        pass

    @abstractmethod
    def get_storage_stats(self) -> StorageStats:
        """
        Get storage system statistics.

        Returns:
            Storage statistics and health metrics
        """
        pass


class ConnectionPool:
    """
    SQLite connection pool for concurrent access.
    """

    def __init__(self, db_path: Path, pool_size: int = 10):
        """
        Initialize connection pool.

        Args:
            db_path: Path to SQLite database file
            pool_size: Maximum number of connections in pool
        """
        self.db_path = db_path
        self.pool = queue.Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        self.all_connections = []  # Track all connections for cleanup

        # Create connections
        for _ in range(pool_size):
            conn = self._create_connection()
            self.all_connections.append(conn)
            self.pool.put(conn)

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with optimizations."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Enable dict-like access

        # Performance optimizations
        conn.execute("PRAGMA journal_mode=WAL")        # Write-Ahead Logging
        conn.execute("PRAGMA synchronous=NORMAL")      # Balance safety and speed
        conn.execute("PRAGMA busy_timeout=10000")      # Wait up to 10s on lock
        conn.execute("PRAGMA temp_store=memory")       # Store temp data in memory
        conn.execute("PRAGMA mmap_size=268435456")     # 256MB memory mapping
        conn.execute("PRAGMA cache_size=10000")        # 10MB cache

        return conn

    def get_connection(self) -> sqlite3.Connection:
        """Get connection from pool."""
        return self.pool.get()

    def return_connection(self, conn: sqlite3.Connection) -> None:
        """Return connection to pool."""
        self.pool.put(conn)

    def close_all(self) -> None:
        """
        Close all connections in pool.

        This forcibly closes ALL connections, including those currently in use.
        Should only be called when shutting down.
        """
        with self.lock:
            # Close all tracked connections
            for conn in self.all_connections:
                try:
                    conn.close()
                except Exception as e:
                    logger.debug(f"Failed to close connection: {e}")

            # Clear the pool
            while not self.pool.empty():
                try:
                    self.pool.get_nowait()
                except queue.Empty:
                    break

            # Clear the list
            self.all_connections.clear()


class SQLiteStorageBackend(StorageBackend):
    """
    High-performance SQLite storage backend.

    This backend provides fast queries and analytics capabilities
    while maintaining compatibility with the file-based approach.
    """

    def __init__(self, root_dir: Path):
        """
        Initialize SQLite storage backend.

        Args:
            root_dir: Root directory containing the database
        """
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.root_dir / "runicorn.db"
        self.pool = ConnectionPool(self.db_path)

        # Initialize database schema
        self._initialize_schema()

    def close(self) -> None:
        """Close all database connections and WAL files."""
        if hasattr(self, 'pool') and self.pool:
            try:
                self.pool.close_all()
                logger.debug("Closed all database connections")

                # Force checkpoint to close WAL file (Windows critical)
                if self.db_path.exists():
                    try:
                        import sqlite3
                        temp_conn = sqlite3.connect(str(self.db_path))
                        temp_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                        temp_conn.close()
                    except Exception as e:
                        logger.debug(f"Failed to checkpoint WAL: {e}")

            except Exception as e:
                logger.warning(f"Failed to close database pool: {e}")

    def __del__(self):
        """Destructor to ensure connections are closed."""
        try:
            self.close()
        except Exception:
            pass

    def _initialize_schema(self) -> None:
        """Initialize database schema from SQL file."""
        schema_ops.initialize_schema(self)

    def _migrate_legacy_schema(self) -> None:
        """Migrate old schema (project/name) to new schema (path/alias/workspace_root).

        Old schema had 'project' and 'name' columns on the experiments table.
        New schema replaced them with 'path' (flexible hierarchy), 'alias', and
        'workspace_root'.  Since CREATE TABLE IF NOT EXISTS won't alter an
        existing table, the views in schema.sql that reference 'path' would fail
        on an old DB.  This method detects the old layout and upgrades it
        in-place before schema.sql runs.
        """
        schema_ops.migrate_legacy_schema(self)

    def _migrate_metrics_identity_schema(self) -> None:
        """Upgrade legacy metrics table to use an independent row identity.

        Older schemas used ``(experiment_id, timestamp, metric_name)`` as the
        primary key. Combined with ``INSERT OR REPLACE``, that could overwrite
        rapid consecutive writes of the same metric. The new schema keeps the
        query-facing columns unchanged and adds an internal autoincrement key.
        """
        schema_ops.migrate_metrics_identity_schema(self)

    def create_experiment(self, experiment: ExperimentRecord) -> str:
        """Create experiment in SQLite database."""
        return experiment_ops.create_experiment(self, experiment)

    def update_experiment(self, exp_id: str, updates: Dict[str, Any]) -> bool:
        """Update experiment in SQLite database."""
        return experiment_ops.update_experiment(self, exp_id, updates)

    def get_experiment(self, exp_id: str) -> Optional[ExperimentRecord]:
        """Get experiment from SQLite database."""
        return experiment_ops.get_experiment(self, exp_id)

    def list_experiments(self, query: QueryParams) -> List[ExperimentRecord]:
        """List experiments with high-performance SQL queries."""
        return experiment_ops.list_experiments(self, query)

    def count_experiments(self, query: QueryParams) -> int:
        """Count experiments matching query."""
        return experiment_ops.count_experiments(self, query)

    def log_metrics(self, exp_id: str, metrics: List[MetricRecord]) -> bool:
        """Log metrics to SQLite database."""
        return metric_ops.log_metrics(self, exp_id, metrics)

    def get_metrics(self, exp_id: str, metric_names: Optional[List[str]] = None) -> List[MetricRecord]:
        """Get metrics from SQLite database."""
        return metric_ops.get_metrics(self, exp_id, metric_names)

    def soft_delete_experiments(self, exp_ids: List[str], reason: str = "user_deleted") -> Dict[str, bool]:
        """Soft delete experiments in SQLite."""
        return experiment_ops.soft_delete_experiments(self, exp_ids, reason)

    def restore_experiments(self, exp_ids: List[str]) -> Dict[str, bool]:
        """Restore soft-deleted experiments in SQLite."""
        return experiment_ops.restore_experiments(self, exp_ids)

    def get_storage_stats(self) -> StorageStats:
        """Get SQLite storage statistics."""
        return metric_ops.get_storage_stats(self)

    # -------------------- Asset Management --------------------

    def upsert_asset(
        self,
        *,
        asset_type: str,
        name: Optional[str],
        source_uri: Optional[str],
        archive_uri: Optional[str],
        is_archived: bool,
        fingerprint_kind: Optional[str],
        fingerprint: Optional[str],
        size_bytes: Optional[int] = None,
        mtime: Optional[float] = None,
        created_at: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Insert an asset or return existing asset_id if fingerprint matches."""
        return asset_ops.upsert_asset(
            self,
            asset_type=asset_type,
            name=name,
            source_uri=source_uri,
            archive_uri=archive_uri,
            is_archived=is_archived,
            fingerprint_kind=fingerprint_kind,
            fingerprint=fingerprint,
            size_bytes=size_bytes,
            mtime=mtime,
            created_at=created_at,
            metadata=metadata,
        )

    def link_run_asset(
        self,
        *,
        run_id: str,
        asset_id: str,
        role: str,
        created_at: Optional[float] = None,
    ) -> None:
        """Create a link between a run and an asset."""
        asset_ops.link_run_asset(
            self,
            run_id=run_id,
            asset_id=asset_id,
            role=role,
            created_at=created_at,
        )

    def record_asset_for_run(
        self,
        *,
        run_id: str,
        role: str,
        asset_type: str,
        name: Optional[str],
        source_uri: Optional[str],
        archive_uri: Optional[str],
        is_archived: bool,
        fingerprint_kind: Optional[str],
        fingerprint: Optional[str],
        size_bytes: Optional[int] = None,
        mtime: Optional[float] = None,
        created_at: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Upsert an asset and link it to a run (convenience combo)."""
        return asset_ops.record_asset_for_run(
            self,
            run_id=run_id,
            role=role,
            asset_type=asset_type,
            name=name,
            source_uri=source_uri,
            archive_uri=archive_uri,
            is_archived=is_archived,
            fingerprint_kind=fingerprint_kind,
            fingerprint=fingerprint,
            size_bytes=size_bytes,
            mtime=mtime,
            created_at=created_at,
            metadata=metadata,
        )

    def get_assets_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all assets associated with a run."""
        return asset_ops.get_assets_for_run(self, run_id)

    def get_asset_ref_count(self, asset_id: str) -> int:
        """Get the number of runs referencing an asset."""
        return asset_ops.get_asset_ref_count(self, asset_id)

    def count_runs_referencing_fingerprint(
        self, fingerprint: str, exclude_run_id: Optional[str] = None
    ) -> int:
        """
        BUG-28: Count how many runs have assets with this fingerprint.
        Used to avoid deleting shared manifests/blobs when one run is removed.
        When exclude_run_id is set (e.g. dry_run), exclude that run from the count.
        """
        return asset_ops.count_runs_referencing_fingerprint(self, fingerprint, exclude_run_id)

    def unlink_run_asset(self, run_id: str, asset_id: str) -> None:
        """Remove the link between a run and an asset (BUG-30: rolling outputs)."""
        asset_ops.unlink_run_asset(self, run_id, asset_id)

    def get_asset_by_fingerprint(
        self, asset_type: str, fingerprint: str
    ) -> Optional[Dict[str, Any]]:
        """Get asset by type and fingerprint."""
        return asset_ops.get_asset_by_fingerprint(self, asset_type, fingerprint)

    # -------------------- Tag Management --------------------

    def set_tags(self, exp_id: str, tags: List[str]) -> None:
        """Replace all tags for an experiment."""
        viewer_query_ops.set_tags(self, exp_id, tags)

    def get_tags(self, exp_id: str) -> List[str]:
        """Get all tags for an experiment."""
        return viewer_query_ops.get_tags(self, exp_id)

    # -------------------- Viewer-optimised Queries --------------------

    def list_experiments_for_viewer(
        self, *, include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Return experiments enriched with tags and assets_count in one query.

        Each returned dict contains all experiments columns plus:
          - tags_csv  (str | None) – comma-separated tags
          - assets_count (int)
        """
        return viewer_query_ops.list_experiments_for_viewer(self, include_deleted=include_deleted)

    def list_deleted_for_viewer(self) -> List[Dict[str, Any]]:
        """Return soft-deleted experiments for recycle-bin display."""
        return viewer_query_ops.list_deleted_for_viewer(self)

    def get_unique_paths(self) -> List[str]:
        """Return sorted list of distinct experiment paths (active only)."""
        return viewer_query_ops.get_unique_paths(self)

    def get_path_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Return per-path run statistics (total/running/finished/failed).

        Includes accumulated counts for ancestor paths.
        """
        return viewer_query_ops.get_path_stats(self)

    def get_running_experiments(self) -> List[Dict[str, Any]]:
        """Return id/run_dir/pid for experiments with status='running'."""
        return viewer_query_ops.get_running_experiments(self)

    def experiment_exists(self, exp_id: str) -> bool:
        """Check whether an experiment record exists."""
        return viewer_query_ops.experiment_exists(self, exp_id)

    def delete_run_with_orphan_assets(self, run_id: str) -> Dict[str, Any]:
        """
        Delete a run and any assets that become orphaned.

        Returns dict with 'orphaned_assets' and 'kept_assets' lists.
        Does NOT delete actual files — caller handles that.
        """
        return asset_ops.delete_run_with_orphan_assets(self, run_id)


