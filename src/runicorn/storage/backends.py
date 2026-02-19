"""
Storage Backend Implementations

Provides different storage backend implementations including file-based,
SQLite-based, and hybrid approaches.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Iterator
import threading
import queue

from .models import ExperimentRecord, MetricRecord, QueryParams, EnvironmentRecord, StorageStats
from .sql_utils import validate_column_name, ALLOWED_EXPERIMENT_COLUMNS

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
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        
        # Performance optimizations
        conn.execute("PRAGMA journal_mode=WAL")        # Write-Ahead Logging
        conn.execute("PRAGMA synchronous=NORMAL")      # Balance safety and speed
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
        schema_path = Path(__file__).parent / "schema.sql"
        
        try:
            schema_sql = schema_path.read_text(encoding="utf-8")
            conn = self.pool.get_connection()
            try:
                conn.executescript(schema_sql)
                conn.commit()
                logger.info("Database schema initialized successfully")
            finally:
                self.pool.return_connection(conn)
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise
    
    def create_experiment(self, experiment: ExperimentRecord) -> str:
        """Create experiment in SQLite database."""
        conn = self.pool.get_connection()
        try:
            conn.execute("""
                INSERT INTO experiments (
                    id, path, alias, created_at, updated_at, status,
                    pid, python_version, platform, hostname, run_dir,
                    workspace_root,
                    best_metric_name, best_metric_value, best_metric_step, best_metric_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                experiment.id, experiment.path, experiment.alias,
                experiment.created_at, experiment.updated_at, experiment.status,
                experiment.pid, experiment.python_version, experiment.platform, 
                experiment.hostname, experiment.run_dir,
                experiment.workspace_root,
                experiment.best_metric_name, experiment.best_metric_value,
                experiment.best_metric_step, experiment.best_metric_mode
            ))
            conn.commit()
            
            logger.debug(f"Created experiment {experiment.id} in database")
            return experiment.id
            
        except Exception as e:
            logger.error(f"Failed to create experiment {experiment.id}: {e}")
            raise
        finally:
            self.pool.return_connection(conn)
    
    def update_experiment(self, exp_id: str, updates: Dict[str, Any]) -> bool:
        """Update experiment in SQLite database."""
        if not updates:
            return True
        
        # Build dynamic UPDATE query
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            # Validate column name to prevent SQL injection
            if not validate_column_name(key, ALLOWED_EXPERIMENT_COLUMNS):
                logger.warning(f"Rejecting invalid column name in update: {key}")
                continue
            set_clauses.append(f"{key} = ?")
            params.append(value)
        
        if not set_clauses:
            logger.warning("No valid columns to update")
            return False
        
        # Always update the updated_at timestamp
        set_clauses.append("updated_at = ?")
        params.append(time.time())
        params.append(exp_id)  # For WHERE clause
        
        query = f"UPDATE experiments SET {', '.join(set_clauses)} WHERE id = ?"
        
        conn = self.pool.get_connection()
        try:
            cursor = conn.execute(query, params)
            conn.commit()
            
            success = cursor.rowcount > 0
            if success:
                logger.debug(f"Updated experiment {exp_id} with {len(updates)} fields")
            else:
                logger.warning(f"No experiment found with ID {exp_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update experiment {exp_id}: {e}")
            return False
        finally:
            self.pool.return_connection(conn)
    
    def get_experiment(self, exp_id: str) -> Optional[ExperimentRecord]:
        """Get experiment from SQLite database."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM experiments WHERE id = ?", (exp_id,))
            row = cursor.fetchone()
            
            if row:
                # Convert sqlite3.Row to dict and then to ExperimentRecord
                data = dict(row)
                return ExperimentRecord.from_dict(data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get experiment {exp_id}: {e}")
            return None
        finally:
            self.pool.return_connection(conn)
    
    def list_experiments(self, query: QueryParams) -> List[ExperimentRecord]:
        """List experiments with high-performance SQL queries."""
        sql_parts = ["SELECT * FROM experiments"]
        where_clauses = []
        params = []
        
        # Build WHERE clause dynamically
        if not query.include_deleted:
            where_clauses.append("deleted_at IS NULL")
        
        if query.path:
            if query.path_exact:
                where_clauses.append("path = ?")
                params.append(query.path)
            else:
                # Prefix match: path starts with query.path
                where_clauses.append("(path = ? OR path LIKE ?)")
                params.append(query.path)
                params.append(f"{query.path}/%")
        
        if query.alias:
            where_clauses.append("alias LIKE ?")
            params.append(f"%{query.alias}%")
        
        if query.status:
            placeholders = ",".join("?" * len(query.status))
            where_clauses.append(f"status IN ({placeholders})")
            params.extend(query.status)
        
        if query.created_after:
            where_clauses.append("created_at >= ?")
            params.append(query.created_after)
        
        if query.created_before:
            where_clauses.append("created_at <= ?")
            params.append(query.created_before)
        
        if query.search_text:
            # Search in path, alias, and id
            where_clauses.append("(path LIKE ? OR alias LIKE ? OR id LIKE ?)")
            search_pattern = f"%{query.search_text}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        
        if query.best_metric_range:
            where_clauses.append("best_metric_value BETWEEN ? AND ?")
            params.extend(query.best_metric_range)
        
        # Add WHERE clause if we have conditions
        if where_clauses:
            sql_parts.append("WHERE " + " AND ".join(where_clauses))
        
        # Add ORDER BY and LIMIT
        order_direction = "DESC" if query.order_desc else "ASC"
        sql_parts.append(f"ORDER BY {query.order_by} {order_direction}")
        sql_parts.append("LIMIT ? OFFSET ?")
        params.extend([query.limit, query.offset])
        
        # Execute query
        conn = self.pool.get_connection()
        try:
            cursor = conn.execute(" ".join(sql_parts), params)
            rows = cursor.fetchall()
            
            # Convert to ExperimentRecord objects
            return [ExperimentRecord.from_dict(dict(row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to list experiments: {e}")
            return []
        finally:
            self.pool.return_connection(conn)
    
    def count_experiments(self, query: QueryParams) -> int:
        """Count experiments matching query."""
        sql_parts = ["SELECT COUNT(*) FROM experiments"]
        where_clauses = []
        params = []
        
        # Build WHERE clause (same logic as list_experiments)
        if not query.include_deleted:
            where_clauses.append("deleted_at IS NULL")
        
        if query.path:
            if query.path_exact:
                where_clauses.append("path = ?")
                params.append(query.path)
            else:
                where_clauses.append("(path = ? OR path LIKE ?)")
                params.append(query.path)
                params.append(f"{query.path}/%")
        
        if query.alias:
            where_clauses.append("alias LIKE ?")
            params.append(f"%{query.alias}%")
        
        if query.status:
            placeholders = ",".join("?" * len(query.status))
            where_clauses.append(f"status IN ({placeholders})")
            params.extend(query.status)
        
        if query.created_after:
            where_clauses.append("created_at >= ?")
            params.append(query.created_after)
        
        if query.created_before:
            where_clauses.append("created_at <= ?")
            params.append(query.created_before)
        
        if query.search_text:
            where_clauses.append("(path LIKE ? OR alias LIKE ? OR id LIKE ?)")
            search_pattern = f"%{query.search_text}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        
        if query.best_metric_range:
            where_clauses.append("best_metric_value BETWEEN ? AND ?")
            params.extend(query.best_metric_range)
        
        if where_clauses:
            sql_parts.append("WHERE " + " AND ".join(where_clauses))
        
        conn = self.pool.get_connection()
        try:
            cursor = conn.execute(" ".join(sql_parts), params)
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            logger.error(f"Failed to count experiments: {e}")
            return 0
        finally:
            self.pool.return_connection(conn)
    
    def log_metrics(self, exp_id: str, metrics: List[MetricRecord]) -> bool:
        """Log metrics to SQLite database."""
        if not metrics:
            return True
        
        conn = self.pool.get_connection()
        try:
            # Batch insert for performance
            metric_data = [
                (m.experiment_id, m.timestamp, m.metric_name, m.metric_value, 
                 m.step, m.stage, m.recorded_at)
                for m in metrics
            ]
            
            conn.executemany("""
                INSERT OR REPLACE INTO metrics 
                (experiment_id, timestamp, metric_name, metric_value, step, stage, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, metric_data)
            
            # Update experiment metric count
            conn.execute("""
                UPDATE experiments 
                SET metric_count = (
                    SELECT COUNT(*) FROM metrics WHERE experiment_id = ?
                ), updated_at = ?
                WHERE id = ?
            """, (exp_id, time.time(), exp_id))
            
            conn.commit()
            logger.debug(f"Logged {len(metrics)} metrics for experiment {exp_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log metrics for {exp_id}: {e}")
            return False
        finally:
            self.pool.return_connection(conn)
    
    def get_metrics(self, exp_id: str, metric_names: Optional[List[str]] = None) -> List[MetricRecord]:
        """Get metrics from SQLite database."""
        sql = "SELECT * FROM metrics WHERE experiment_id = ?"
        params = [exp_id]
        
        if metric_names:
            placeholders = ",".join("?" * len(metric_names))
            sql += f" AND metric_name IN ({placeholders})"
            params.extend(metric_names)
        
        sql += " ORDER BY timestamp ASC"
        
        conn = self.pool.get_connection()
        try:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            
            return [MetricRecord.from_dict(dict(row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get metrics for {exp_id}: {e}")
            return []
        finally:
            self.pool.return_connection(conn)
    
    def soft_delete_experiments(self, exp_ids: List[str], reason: str = "user_deleted") -> Dict[str, bool]:
        """Soft delete experiments in SQLite."""
        results = {}
        conn = self.pool.get_connection()
        
        try:
            for exp_id in exp_ids:
                cursor = conn.execute("""
                    UPDATE experiments 
                    SET deleted_at = ?, delete_reason = ?, updated_at = ?
                    WHERE id = ? AND deleted_at IS NULL
                """, (time.time(), reason, time.time(), exp_id))
                
                results[exp_id] = cursor.rowcount > 0
                
                if results[exp_id]:
                    logger.info(f"Soft deleted experiment {exp_id}")
                else:
                    logger.warning(f"Experiment {exp_id} not found or already deleted")
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to soft delete experiments: {e}")
            # Mark all as failed
            for exp_id in exp_ids:
                results[exp_id] = False
        finally:
            self.pool.return_connection(conn)
        
        return results
    
    def restore_experiments(self, exp_ids: List[str]) -> Dict[str, bool]:
        """Restore soft-deleted experiments in SQLite."""
        results = {}
        conn = self.pool.get_connection()
        
        try:
            for exp_id in exp_ids:
                cursor = conn.execute("""
                    UPDATE experiments 
                    SET deleted_at = NULL, delete_reason = NULL, updated_at = ?
                    WHERE id = ? AND deleted_at IS NOT NULL
                """, (time.time(), exp_id))
                
                results[exp_id] = cursor.rowcount > 0
                
                if results[exp_id]:
                    logger.info(f"Restored experiment {exp_id}")
                else:
                    logger.warning(f"Experiment {exp_id} not found or not deleted")
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to restore experiments: {e}")
            # Mark all as failed
            for exp_id in exp_ids:
                results[exp_id] = False
        finally:
            self.pool.return_connection(conn)
        
        return results
    
    def get_storage_stats(self) -> StorageStats:
        """Get SQLite storage statistics."""
        conn = self.pool.get_connection()
        try:
            # Get experiment counts
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN deleted_at IS NULL THEN 1 END) as active,
                    COUNT(CASE WHEN deleted_at IS NOT NULL THEN 1 END) as deleted
                FROM experiments
            """)
            exp_counts = cursor.fetchone()
            
            # Get metric counts
            cursor = conn.execute("SELECT COUNT(*) FROM metrics")
            metric_count = cursor.fetchone()[0]
            
            # Get database size
            cursor = conn.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor = conn.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            db_size_bytes = page_count * page_size
            
            return StorageStats(
                total_experiments=exp_counts[0],
                active_experiments=exp_counts[1], 
                deleted_experiments=exp_counts[2],
                total_metrics_points=metric_count,
                storage_size_bytes=db_size_bytes,
                db_size_mb=db_size_bytes / (1024 * 1024),
                updated_at=time.time()
            )
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return StorageStats()
        finally:
            self.pool.return_connection(conn)

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
        conn = self.pool.get_connection()
        try:
            asset_id = str(uuid.uuid4())
            metadata_json = (
                json.dumps(metadata or {}, ensure_ascii=False)
                if metadata is not None
                else None
            )
            try:
                conn.execute(
                    """
                    INSERT INTO assets (
                        asset_id, asset_type, name, source_uri, archive_uri,
                        is_archived, fingerprint_kind, fingerprint,
                        size_bytes, mtime, created_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        asset_id, asset_type, name, source_uri, archive_uri,
                        1 if is_archived else 0,
                        fingerprint_kind, fingerprint,
                        size_bytes, mtime, created_at, metadata_json,
                    ),
                )
                conn.commit()
                return asset_id
            except sqlite3.IntegrityError:
                if fingerprint:
                    row = conn.execute(
                        "SELECT asset_id FROM assets WHERE asset_type=? AND fingerprint=?",
                        (asset_type, fingerprint),
                    ).fetchone()
                    if row:
                        return str(row["asset_id"])
                raise
        finally:
            self.pool.return_connection(conn)

    def link_run_asset(
        self,
        *,
        run_id: str,
        asset_id: str,
        role: str,
        created_at: Optional[float] = None,
    ) -> None:
        """Create a link between a run and an asset."""
        conn = self.pool.get_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO run_assets (run_id, asset_id, role, created_at) VALUES (?, ?, ?, ?)",
                (run_id, asset_id, role, created_at),
            )
            conn.commit()
        finally:
            self.pool.return_connection(conn)

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
        asset_id = self.upsert_asset(
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
        self.link_run_asset(
            run_id=run_id,
            asset_id=asset_id,
            role=role,
            created_at=created_at,
        )
        return asset_id

    def get_assets_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all assets associated with a run."""
        conn = self.pool.get_connection()
        try:
            rows = conn.execute(
                """
                SELECT a.*, ra.role, ra.created_at AS linked_at
                FROM assets a
                JOIN run_assets ra ON a.asset_id = ra.asset_id
                WHERE ra.run_id = ?
                """,
                (run_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            self.pool.return_connection(conn)

    def get_asset_ref_count(self, asset_id: str) -> int:
        """Get the number of runs referencing an asset."""
        conn = self.pool.get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM run_assets WHERE asset_id = ?",
                (asset_id,),
            ).fetchone()
            return int(row["cnt"]) if row else 0
        finally:
            self.pool.return_connection(conn)

    def get_asset_by_fingerprint(
        self, asset_type: str, fingerprint: str
    ) -> Optional[Dict[str, Any]]:
        """Get asset by type and fingerprint."""
        conn = self.pool.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM assets WHERE asset_type=? AND fingerprint=?",
                (asset_type, fingerprint),
            ).fetchone()
            return dict(row) if row else None
        finally:
            self.pool.return_connection(conn)

    # -------------------- Tag Management --------------------

    def set_tags(self, exp_id: str, tags: List[str]) -> None:
        """Replace all tags for an experiment."""
        conn = self.pool.get_connection()
        try:
            conn.execute("DELETE FROM experiment_tags WHERE experiment_id = ?", (exp_id,))
            if tags:
                conn.executemany(
                    "INSERT OR IGNORE INTO experiment_tags (experiment_id, tag) VALUES (?, ?)",
                    [(exp_id, tag) for tag in tags],
                )
            conn.commit()
        finally:
            self.pool.return_connection(conn)

    def get_tags(self, exp_id: str) -> List[str]:
        """Get all tags for an experiment."""
        conn = self.pool.get_connection()
        try:
            rows = conn.execute(
                "SELECT tag FROM experiment_tags WHERE experiment_id = ? ORDER BY tag",
                (exp_id,),
            ).fetchall()
            return [row["tag"] for row in rows]
        finally:
            self.pool.return_connection(conn)

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
        sql = """
            SELECT e.*,
                   GROUP_CONCAT(DISTINCT t.tag) AS tags_csv,
                   COUNT(DISTINCT ra.asset_id)  AS assets_count
            FROM experiments e
            LEFT JOIN experiment_tags t  ON e.id = t.experiment_id
            LEFT JOIN run_assets      ra ON e.id = ra.run_id
        """
        if not include_deleted:
            sql += " WHERE e.deleted_at IS NULL"
        sql += " GROUP BY e.id ORDER BY e.created_at DESC"

        conn = self.pool.get_connection()
        try:
            rows = conn.execute(sql).fetchall()
            return [dict(r) for r in rows]
        finally:
            self.pool.return_connection(conn)

    def list_deleted_for_viewer(self) -> List[Dict[str, Any]]:
        """Return soft-deleted experiments for recycle-bin display."""
        sql = """
            SELECT id, path, alias, created_at, status,
                   deleted_at, delete_reason, run_dir
            FROM experiments
            WHERE deleted_at IS NOT NULL
            ORDER BY deleted_at DESC
        """
        conn = self.pool.get_connection()
        try:
            rows = conn.execute(sql).fetchall()
            return [dict(r) for r in rows]
        finally:
            self.pool.return_connection(conn)

    def get_unique_paths(self) -> List[str]:
        """Return sorted list of distinct experiment paths (active only)."""
        conn = self.pool.get_connection()
        try:
            rows = conn.execute(
                "SELECT DISTINCT path FROM experiments WHERE deleted_at IS NULL ORDER BY path"
            ).fetchall()
            return [r["path"] for r in rows]
        finally:
            self.pool.return_connection(conn)

    def get_path_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Return per-path run statistics (total/running/finished/failed).

        Includes accumulated counts for ancestor paths.
        """
        conn = self.pool.get_connection()
        try:
            rows = conn.execute("""
                SELECT path,
                       COUNT(*)                                      AS total,
                       COUNT(CASE WHEN status='running'  THEN 1 END) AS running,
                       COUNT(CASE WHEN status='finished' THEN 1 END) AS finished,
                       COUNT(CASE WHEN status='failed'   THEN 1 END) AS failed
                FROM experiments
                WHERE deleted_at IS NULL
                GROUP BY path
            """).fetchall()
        finally:
            self.pool.return_connection(conn)

        path_runs: Dict[str, Dict[str, int]] = {}
        for r in rows:
            path_runs[r["path"]] = {
                "total": r["total"],
                "running": r["running"],
                "finished": r["finished"],
                "failed": r["failed"],
            }

        # Accumulate ancestor paths
        for path in list(path_runs.keys()):
            parts = path.split("/")
            for i in range(1, len(parts)):
                ancestor = "/".join(parts[:i])
                if ancestor not in path_runs:
                    path_runs[ancestor] = {"total": 0, "running": 0, "finished": 0, "failed": 0}
                for k in ("total", "running", "finished", "failed"):
                    path_runs[ancestor][k] += path_runs[path][k]

        return path_runs

    def get_running_experiments(self) -> List[Dict[str, Any]]:
        """Return id/run_dir/pid for experiments with status='running'."""
        conn = self.pool.get_connection()
        try:
            rows = conn.execute(
                "SELECT id, run_dir, pid FROM experiments WHERE status = 'running' AND deleted_at IS NULL"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            self.pool.return_connection(conn)

    def experiment_exists(self, exp_id: str) -> bool:
        """Check whether an experiment record exists."""
        conn = self.pool.get_connection()
        try:
            row = conn.execute(
                "SELECT 1 FROM experiments WHERE id = ?", (exp_id,)
            ).fetchone()
            return row is not None
        finally:
            self.pool.return_connection(conn)

    def delete_run_with_orphan_assets(self, run_id: str) -> Dict[str, Any]:
        """
        Delete a run and any assets that become orphaned.

        Returns dict with 'orphaned_assets' and 'kept_assets' lists.
        Does NOT delete actual files — caller handles that.
        """
        conn = self.pool.get_connection()
        try:
            # Get all assets for this run
            assets = conn.execute(
                """
                SELECT a.*, ra.role
                FROM assets a
                JOIN run_assets ra ON a.asset_id = ra.asset_id
                WHERE ra.run_id = ?
                """,
                (run_id,),
            ).fetchall()

            orphaned = []
            kept = []

            for asset in assets:
                asset_id = asset["asset_id"]
                row = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM run_assets WHERE asset_id=? AND run_id!=?",
                    (asset_id, run_id),
                ).fetchone()
                ref_count = int(row["cnt"]) if row else 0

                asset_dict = dict(asset)
                if ref_count == 0:
                    orphaned.append(asset_dict)
                else:
                    kept.append(asset_dict)

            # Delete experiment record (CASCADE deletes run_assets and metrics)
            conn.execute("DELETE FROM experiments WHERE id=?", (run_id,))

            # Delete orphaned assets
            for asset in orphaned:
                conn.execute(
                    "DELETE FROM assets WHERE asset_id=?", (asset["asset_id"],)
                )

            conn.commit()

            return {
                "orphaned_assets": orphaned,
                "kept_assets": kept,
            }
        finally:
            self.pool.return_connection(conn)


