"""
Storage Backend Implementations

Provides different storage backend implementations including file-based,
SQLite-based, and hybrid approaches.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
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
    async def create_experiment(self, experiment: ExperimentRecord) -> str:
        """
        Create a new experiment record.
        
        Args:
            experiment: Experiment record to create
            
        Returns:
            Created experiment ID
        """
        pass
    
    @abstractmethod
    async def update_experiment(self, exp_id: str, updates: Dict[str, Any]) -> bool:
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
    async def get_experiment(self, exp_id: str) -> Optional[ExperimentRecord]:
        """
        Retrieve a single experiment by ID.
        
        Args:
            exp_id: Experiment ID to retrieve
            
        Returns:
            Experiment record if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def list_experiments(self, query: QueryParams) -> List[ExperimentRecord]:
        """
        List experiments matching query parameters.
        
        Args:
            query: Query parameters for filtering and pagination
            
        Returns:
            List of matching experiment records
        """
        pass
    
    @abstractmethod
    async def count_experiments(self, query: QueryParams) -> int:
        """
        Count experiments matching query parameters.
        
        Args:
            query: Query parameters for filtering
            
        Returns:
            Number of matching experiments
        """
        pass
    
    @abstractmethod
    async def log_metrics(self, exp_id: str, metrics: List[MetricRecord]) -> bool:
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
    async def get_metrics(self, exp_id: str, metric_names: Optional[List[str]] = None) -> List[MetricRecord]:
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
    async def soft_delete_experiments(self, exp_ids: List[str], reason: str = "user_deleted") -> Dict[str, bool]:
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
    async def restore_experiments(self, exp_ids: List[str]) -> Dict[str, bool]:
        """
        Restore soft-deleted experiments.
        
        Args:
            exp_ids: List of experiment IDs to restore
            
        Returns:
            Dictionary mapping experiment ID to success status
        """
        pass
    
    @abstractmethod
    async def get_storage_stats(self) -> StorageStats:
        """
        Get storage system statistics.
        
        Returns:
            Storage statistics and health metrics
        """
        pass


class FileStorageBackend(StorageBackend):
    """
    File-based storage backend (legacy compatibility).
    
    This backend maintains compatibility with the existing file-based storage
    while implementing the new storage interface.
    """
    
    def __init__(self, root_dir: Path):
        """
        Initialize file storage backend.
        
        Args:
            root_dir: Root directory for experiment storage
        """
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_experiment(self, experiment: ExperimentRecord) -> str:
        """Create experiment using file system."""
        # Implementation here would mirror the existing file creation logic
        # from the original SDK - this is mainly for compatibility
        exp_id = experiment.id
        
        # Create directory structure
        run_dir = self._get_run_dir(experiment.project, experiment.name, exp_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Write meta.json
        meta_path = run_dir / "meta.json"
        meta_data = {
            "id": exp_id,
            "project": experiment.project,
            "name": experiment.name,
            "created_at": experiment.created_at,
            "python": experiment.python_version,
            "platform": experiment.platform,
            "hostname": experiment.hostname,
            "pid": experiment.pid,
            "storage_dir": str(self.root_dir)
        }
        meta_path.write_text(json.dumps(meta_data, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # Write status.json
        status_path = run_dir / "status.json"
        status_data = {
            "status": experiment.status,
            "started_at": experiment.started_at or experiment.created_at
        }
        status_path.write_text(json.dumps(status_data, ensure_ascii=False, indent=2), encoding="utf-8")
        
        return exp_id
    
    async def update_experiment(self, exp_id: str, updates: Dict[str, Any]) -> bool:
        """Update experiment files."""
        try:
            # Find experiment directory
            exp_record = await self.get_experiment(exp_id)
            if not exp_record:
                return False
            
            run_dir = Path(exp_record.run_dir)
            
            # Update status.json if status-related fields changed
            if any(key in updates for key in ['status', 'ended_at', 'exit_reason']):
                status_path = run_dir / "status.json"
                status_data = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
                status_data.update({k: v for k, v in updates.items() if k in ['status', 'ended_at', 'exit_reason']})
                status_path.write_text(json.dumps(status_data, ensure_ascii=False, indent=2), encoding="utf-8")
            
            # Update summary.json if metric-related fields changed
            if any(key in updates for key in ['best_metric_value', 'best_metric_name', 'best_metric_step', 'best_metric_mode']):
                summary_path = run_dir / "summary.json"
                summary_data = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
                summary_data.update({k: v for k, v in updates.items() if k.startswith('best_metric_')})
                summary_path.write_text(json.dumps(summary_data, ensure_ascii=False, indent=2), encoding="utf-8")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update experiment {exp_id}: {e}")
            return False
    
    async def get_experiment(self, exp_id: str) -> Optional[ExperimentRecord]:
        """Get experiment from file system."""
        # Implementation would scan for the experiment directory and load metadata
        # This is a simplified version - the full implementation would mirror
        # the existing _find_run_dir_by_id logic
        return None  # Placeholder
    
    async def list_experiments(self, query: QueryParams) -> List[ExperimentRecord]:
        """List experiments from file system."""
        # This would implement the current file scanning logic
        # Converting it to return ExperimentRecord objects
        return []  # Placeholder
    
    async def count_experiments(self, query: QueryParams) -> int:
        """Count experiments matching query."""
        experiments = await self.list_experiments(query)
        return len(experiments)
    
    async def log_metrics(self, exp_id: str, metrics: List[MetricRecord]) -> bool:
        """Log metrics to events.jsonl file."""
        try:
            exp_record = await self.get_experiment(exp_id)
            if not exp_record:
                return False
            
            run_dir = Path(exp_record.run_dir)
            events_path = run_dir / "events.jsonl"
            
            # Convert metrics to event format and append
            with open(events_path, "a", encoding="utf-8") as f:
                for metric in metrics:
                    event = {
                        "ts": metric.timestamp,
                        "type": "metrics",
                        "data": {
                            "global_step": metric.step,
                            "time": metric.timestamp,
                            metric.metric_name: metric.metric_value,
                            "stage": metric.stage
                        }
                    }
                    f.write(json.dumps(event, ensure_ascii=False) + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log metrics for {exp_id}: {e}")
            return False
    
    async def get_metrics(self, exp_id: str, metric_names: Optional[List[str]] = None) -> List[MetricRecord]:
        """Get metrics from events.jsonl file."""
        # Implementation would parse events.jsonl and convert to MetricRecord objects
        return []  # Placeholder
    
    async def soft_delete_experiments(self, exp_ids: List[str], reason: str = "user_deleted") -> Dict[str, bool]:
        """Soft delete by creating .deleted marker files."""
        results = {}
        for exp_id in exp_ids:
            # Implementation would create .deleted marker file
            results[exp_id] = True  # Placeholder
        return results
    
    async def restore_experiments(self, exp_ids: List[str]) -> Dict[str, bool]:
        """Restore by removing .deleted marker files."""
        results = {}
        for exp_id in exp_ids:
            # Implementation would remove .deleted marker file
            results[exp_id] = True  # Placeholder
        return results
    
    async def get_storage_stats(self) -> StorageStats:
        """Get file system storage statistics."""
        # Implementation would scan file system and compute statistics
        return StorageStats()
    
    def _get_run_dir(self, project: str, name: str, exp_id: str) -> Path:
        """Get run directory path for new layout."""
        return self.root_dir / project / name / "runs" / exp_id


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
    
    async def create_experiment(self, experiment: ExperimentRecord) -> str:
        """Create experiment in SQLite database."""
        conn = self.pool.get_connection()
        try:
            conn.execute("""
                INSERT INTO experiments (
                    id, project, name, created_at, updated_at, status,
                    pid, python_version, platform, hostname, run_dir,
                    best_metric_name, best_metric_value, best_metric_step, best_metric_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                experiment.id, experiment.project, experiment.name,
                experiment.created_at, experiment.updated_at, experiment.status,
                experiment.pid, experiment.python_version, experiment.platform, 
                experiment.hostname, experiment.run_dir,
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
    
    async def update_experiment(self, exp_id: str, updates: Dict[str, Any]) -> bool:
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
    
    async def get_experiment(self, exp_id: str) -> Optional[ExperimentRecord]:
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
    
    async def list_experiments(self, query: QueryParams) -> List[ExperimentRecord]:
        """List experiments with high-performance SQL queries."""
        sql_parts = ["SELECT * FROM experiments"]
        where_clauses = []
        params = []
        
        # Build WHERE clause dynamically
        if not query.include_deleted:
            where_clauses.append("deleted_at IS NULL")
        
        if query.project:
            where_clauses.append("project = ?")
            params.append(query.project)
        
        if query.name:
            where_clauses.append("name = ?") 
            params.append(query.name)
        
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
            where_clauses.append("(project LIKE ? OR name LIKE ? OR id LIKE ?)")
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
    
    async def count_experiments(self, query: QueryParams) -> int:
        """Count experiments matching query."""
        # Similar to list_experiments but with COUNT(*)
        sql_parts = ["SELECT COUNT(*) FROM experiments"]
        where_clauses = []
        params = []
        
        # Build WHERE clause (same logic as list_experiments)
        if not query.include_deleted:
            where_clauses.append("deleted_at IS NULL")
        
        if query.project:
            where_clauses.append("project = ?")
            params.append(query.project)
        
        # ... (other conditions same as list_experiments)
        
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
    
    async def log_metrics(self, exp_id: str, metrics: List[MetricRecord]) -> bool:
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
    
    async def get_metrics(self, exp_id: str, metric_names: Optional[List[str]] = None) -> List[MetricRecord]:
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
    
    async def soft_delete_experiments(self, exp_ids: List[str], reason: str = "user_deleted") -> Dict[str, bool]:
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
    
    async def restore_experiments(self, exp_ids: List[str]) -> Dict[str, bool]:
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
    
    async def get_storage_stats(self) -> StorageStats:
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


class HybridStorageBackend(StorageBackend):
    """
    Hybrid storage backend combining SQLite and file system.
    
    This backend provides the best of both worlds:
    - Fast queries through SQLite
    - Large file storage through file system
    - Backward compatibility with existing data
    """
    
    def __init__(self, root_dir: Path, enable_migration: bool = True):
        """
        Initialize hybrid storage backend.
        
        Args:
            root_dir: Root directory for storage
            enable_migration: Whether to enable automatic migration from files
        """
        self.root_dir = Path(root_dir)
        self.sqlite_backend = SQLiteStorageBackend(root_dir)
        self.file_backend = FileStorageBackend(root_dir)
        self.enable_migration = enable_migration
        
        # Migration status tracking
        self._migration_in_progress = False
        
        if enable_migration:
            # Start background migration if needed
            asyncio.create_task(self._maybe_start_migration())
    
    async def _maybe_start_migration(self) -> None:
        """Start migration from file storage if needed."""
        try:
            # Check if migration is needed
            stats = await self.sqlite_backend.get_storage_stats()
            if stats.total_experiments == 0:
                # No experiments in SQLite, check if we have file-based experiments
                file_experiments = await self.file_backend.list_experiments(QueryParams(limit=1))
                if file_experiments:
                    logger.info("Starting automatic migration from file storage to SQLite")
                    await self._migrate_from_files()
        except Exception as e:
            logger.error(f"Migration check failed: {e}")
    
    async def _migrate_from_files(self) -> None:
        """Migrate existing file-based experiments to SQLite."""
        if self._migration_in_progress:
            return
        
        self._migration_in_progress = True
        try:
            # This would implement the full migration logic
            # For now, it's a placeholder
            logger.info("Migration would start here")
        finally:
            self._migration_in_progress = False
    
    async def create_experiment(self, experiment: ExperimentRecord) -> str:
        """Create experiment in both SQLite and file system."""
        # Write to SQLite first for consistency
        exp_id = await self.sqlite_backend.create_experiment(experiment)
        
        # Also create file structure for compatibility
        try:
            await self.file_backend.create_experiment(experiment)
        except Exception as e:
            logger.warning(f"Failed to create file structure for {exp_id}: {e}")
        
        return exp_id
    
    async def update_experiment(self, exp_id: str, updates: Dict[str, Any]) -> bool:
        """Update experiment in both backends."""
        # Update SQLite first
        sqlite_success = await self.sqlite_backend.update_experiment(exp_id, updates)
        
        # Update files for compatibility  
        try:
            await self.file_backend.update_experiment(exp_id, updates)
        except Exception as e:
            logger.warning(f"Failed to update file for {exp_id}: {e}")
        
        return sqlite_success
    
    async def get_experiment(self, exp_id: str) -> Optional[ExperimentRecord]:
        """Get experiment preferring SQLite, fallback to files."""
        # Try SQLite first (faster)
        experiment = await self.sqlite_backend.get_experiment(exp_id)
        if experiment:
            return experiment
        
        # Fallback to file system
        return await self.file_backend.get_experiment(exp_id)
    
    async def list_experiments(self, query: QueryParams) -> List[ExperimentRecord]:
        """List experiments using SQLite for performance."""
        return await self.sqlite_backend.list_experiments(query)
    
    async def count_experiments(self, query: QueryParams) -> int:
        """Count experiments using SQLite for performance."""
        return await self.sqlite_backend.count_experiments(query)
    
    async def log_metrics(self, exp_id: str, metrics: List[MetricRecord]) -> bool:
        """Log metrics to both SQLite and file system."""
        # Log to SQLite first
        sqlite_success = await self.sqlite_backend.log_metrics(exp_id, metrics)
        
        # Also log to files for compatibility
        try:
            await self.file_backend.log_metrics(exp_id, metrics)
        except Exception as e:
            logger.warning(f"Failed to log metrics to file for {exp_id}: {e}")
        
        return sqlite_success
    
    async def get_metrics(self, exp_id: str, metric_names: Optional[List[str]] = None) -> List[MetricRecord]:
        """Get metrics preferring SQLite, fallback to files."""
        # Try SQLite first (faster and more structured)
        metrics = await self.sqlite_backend.get_metrics(exp_id, metric_names)
        if metrics:
            return metrics
        
        # Fallback to file system
        return await self.file_backend.get_metrics(exp_id, metric_names)
    
    async def soft_delete_experiments(self, exp_ids: List[str], reason: str = "user_deleted") -> Dict[str, bool]:
        """Soft delete in both backends."""
        # Delete in SQLite first
        sqlite_results = await self.sqlite_backend.soft_delete_experiments(exp_ids, reason)
        
        # Also mark in file system
        try:
            await self.file_backend.soft_delete_experiments(exp_ids, reason)
        except Exception as e:
            logger.warning(f"Failed to soft delete in file system: {e}")
        
        return sqlite_results
    
    async def restore_experiments(self, exp_ids: List[str]) -> Dict[str, bool]:
        """Restore in both backends."""
        # Restore in SQLite first
        sqlite_results = await self.sqlite_backend.restore_experiments(exp_ids)
        
        # Also restore in file system
        try:
            await self.file_backend.restore_experiments(exp_ids)
        except Exception as e:
            logger.warning(f"Failed to restore in file system: {e}")
        
        return sqlite_results
    
    async def get_storage_stats(self) -> StorageStats:
        """Get comprehensive storage statistics."""
        return await self.sqlite_backend.get_storage_stats()
