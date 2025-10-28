"""
Storage Migration Tools

Provides tools for migrating between different storage backends,
particularly from file-based storage to SQLite.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterator

from .models import ExperimentRecord, MetricRecord, EnvironmentRecord, MigrationStatus, QueryParams
from .backends import StorageBackend, FileStorageBackend, SQLiteStorageBackend

logger = logging.getLogger(__name__)


class StorageMigrator:
    """
    Handles migration between different storage backends.
    """
    
    def __init__(self, source_backend: StorageBackend, target_backend: StorageBackend):
        """
        Initialize migrator.
        
        Args:
            source_backend: Source storage backend
            target_backend: Target storage backend
        """
        self.source = source_backend
        self.target = target_backend
        self.status = MigrationStatus(
            migration_type=f"{type(source_backend).__name__}_to_{type(target_backend).__name__}",
            status="pending"
        )
    
    async def migrate_all(self, batch_size: int = 100) -> MigrationStatus:
        """
        Migrate all experiments from source to target backend.
        
        Args:
            batch_size: Number of experiments to process in each batch
            
        Returns:
            Migration status with results
        """
        self.status.status = "in_progress"
        self.status.started_at = time.time()
        
        try:
            # Get total count for progress tracking
            total_query = QueryParams(limit=999999, include_deleted=True)
            all_experiments = await self.source.list_experiments(total_query)
            self.status.total_items = len(all_experiments)
            
            logger.info(f"Starting migration of {self.status.total_items} experiments")
            
            # Process in batches
            for i in range(0, len(all_experiments), batch_size):
                batch = all_experiments[i:i + batch_size]
                
                for experiment in batch:
                    try:
                        await self._migrate_experiment(experiment)
                        self.status.processed_items += 1
                    except Exception as e:
                        self.status.failed_items += 1
                        self.status.errors.append(f"Failed to migrate {experiment.id}: {e}")
                        logger.error(f"Migration failed for {experiment.id}: {e}")
                
                # Log progress
                progress = (self.status.processed_items / self.status.total_items) * 100
                logger.info(f"Migration progress: {progress:.1f}% ({self.status.processed_items}/{self.status.total_items})")
                
                # Small delay to avoid overwhelming the system
                await asyncio.sleep(0.1)
            
            # Mark as completed
            self.status.status = "completed"
            self.status.completed_at = time.time()
            
            logger.info(f"Migration completed: {self.status.processed_items} success, {self.status.failed_items} failed")
            
        except Exception as e:
            self.status.status = "failed"
            self.status.errors.append(f"Migration failed: {e}")
            logger.error(f"Migration failed: {e}")
        
        return self.status
    
    async def _migrate_experiment(self, experiment: ExperimentRecord) -> None:
        """
        Migrate a single experiment with all its data.
        
        Args:
            experiment: Experiment record to migrate
        """
        # 1. Create experiment record in target
        await self.target.create_experiment(experiment)
        
        # 2. Migrate metrics data
        metrics = await self.source.get_metrics(experiment.id)
        if metrics:
            await self.target.log_metrics(experiment.id, metrics)
        
        # 3. Copy any additional metadata if needed
        # This could include environment data, tags, etc.


class FilesToSQLiteMigrator(StorageMigrator):
    """
    Specialized migrator for file-based to SQLite migration.
    """
    
    def __init__(self, root_dir: Path):
        """
        Initialize file to SQLite migrator.
        
        Args:
            root_dir: Root directory containing file-based experiments
        """
        self.root_dir = Path(root_dir)
        
        # We'll create a temporary file backend to read existing data
        # and a SQLite backend as the target
        file_backend = FilesToSQLiteFileReader(root_dir)
        sqlite_backend = SQLiteStorageBackend(root_dir)
        
        super().__init__(file_backend, sqlite_backend)
    
    async def migrate_with_verification(self) -> MigrationStatus:
        """
        Migrate with data verification.
        
        Returns:
            Migration status with verification results
        """
        # Perform migration
        status = await self.migrate_all()
        
        if status.status == "completed":
            # Verify migration integrity
            verification_result = await self._verify_migration()
            if not verification_result["success"]:
                status.status = "failed"
                status.errors.extend(verification_result["errors"])
        
        return status
    
    async def _verify_migration(self) -> Dict[str, Any]:
        """
        Verify migration integrity by comparing file and SQLite data.
        
        Returns:
            Verification results
        """
        errors = []
        
        try:
            # Compare experiment counts
            file_query = QueryParams(limit=999999, include_deleted=True)
            file_experiments = await self.source.list_experiments(file_query)
            sqlite_experiments = await self.target.list_experiments(file_query)
            
            if len(file_experiments) != len(sqlite_experiments):
                errors.append(f"Experiment count mismatch: {len(file_experiments)} file vs {len(sqlite_experiments)} SQLite")
            
            # Sample verification: check a few experiments in detail
            for experiment in file_experiments[:10]:  # Check first 10
                sqlite_exp = await self.target.get_experiment(experiment.id)
                if not sqlite_exp:
                    errors.append(f"Experiment {experiment.id} missing in SQLite")
                    continue
                
                # Verify key fields
                if sqlite_exp.project != experiment.project:
                    errors.append(f"Project mismatch for {experiment.id}")
                if sqlite_exp.best_metric_value != experiment.best_metric_value:
                    errors.append(f"Best metric mismatch for {experiment.id}")
        
        except Exception as e:
            errors.append(f"Verification failed: {e}")
        
        return {
            "success": len(errors) == 0,
            "errors": errors
        }


class FilesToSQLiteFileReader(FileStorageBackend):
    """
    Specialized file reader for migration purposes.
    
    This class reads existing file-based experiments and converts them
    to the new data model format.
    """
    
    def __init__(self, root_dir: Path):
        """Initialize file reader for migration."""
        super().__init__(root_dir)
    
    async def list_experiments(self, query: QueryParams) -> List[ExperimentRecord]:
        """
        Read all file-based experiments and convert to ExperimentRecord format.
        """
        experiments = []
        
        # Import the existing storage utilities
        from ..viewer.services.storage import iter_all_runs, read_json
        
        for entry in iter_all_runs(self.root_dir, include_deleted=query.include_deleted):
            try:
                experiment = await self._load_experiment_from_files(entry)
                if experiment:
                    experiments.append(experiment)
            except Exception as e:
                logger.warning(f"Failed to load experiment from {entry.dir}: {e}")
        
        return experiments
    
    async def _load_experiment_from_files(self, entry) -> Optional[ExperimentRecord]:
        """
        Load experiment data from file system and convert to ExperimentRecord.
        
        Args:
            entry: RunEntry from the file scanner
            
        Returns:
            ExperimentRecord if successful, None otherwise
        """
        try:
            run_dir = entry.dir
            
            # Load metadata files
            meta = self._read_json_safe(run_dir / "meta.json")
            status = self._read_json_safe(run_dir / "status.json")
            summary = self._read_json_safe(run_dir / "summary.json")
            
            # Extract core information
            exp_id = meta.get("id") or run_dir.name
            project = meta.get("project") or entry.project or "unknown"
            name = meta.get("name") or entry.name or "default"
            
            # Handle timestamps
            created_at = meta.get("created_at") or run_dir.stat().st_ctime
            updated_at = status.get("ended_at") or meta.get("created_at") or created_at
            started_at = status.get("started_at")
            ended_at = status.get("ended_at")
            
            # Get status information
            exp_status = status.get("status", "finished")
            exit_reason = status.get("exit_reason")
            
            # Extract best metric information
            best_metric_name = summary.get("best_metric_name")
            best_metric_value = summary.get("best_metric_value")
            best_metric_step = summary.get("best_metric_step")
            best_metric_mode = summary.get("best_metric_mode")
            
            # Check for soft delete
            deleted_at = None
            delete_reason = None
            deleted_file = run_dir / ".deleted"
            if deleted_file.exists():
                deleted_info = self._read_json_safe(deleted_file)
                deleted_at = deleted_info.get("deleted_at")
                delete_reason = deleted_info.get("reason")
            
            # Create ExperimentRecord
            return ExperimentRecord(
                id=exp_id,
                project=project,
                name=name,
                created_at=created_at,
                updated_at=updated_at,
                started_at=started_at,
                ended_at=ended_at,
                status=exp_status,
                exit_reason=exit_reason,
                pid=meta.get("pid"),
                python_version=meta.get("python"),
                platform=meta.get("platform"),
                hostname=meta.get("hostname"),
                best_metric_name=best_metric_name,
                best_metric_value=best_metric_value,
                best_metric_step=best_metric_step,
                best_metric_mode=best_metric_mode,
                deleted_at=deleted_at,
                delete_reason=delete_reason,
                run_dir=str(run_dir),
                duration_seconds=None,  # Will be computed
                metric_count=0  # Will be computed
            )
            
        except Exception as e:
            logger.error(f"Failed to load experiment from {entry.dir}: {e}")
            return None
    
    async def get_metrics(self, exp_id: str, metric_names: Optional[List[str]] = None) -> List[MetricRecord]:
        """
        Load metrics from events.jsonl file and convert to MetricRecord format.
        """
        try:
            experiment = await self.get_experiment(exp_id)
            if not experiment:
                return []
            
            events_path = Path(experiment.run_dir) / "events.jsonl"
            if not events_path.exists():
                return []
            
            metrics = []
            
            # Parse events.jsonl
            with open(events_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        event = json.loads(line)
                        if event.get("type") == "metrics":
                            data = event.get("data", {})
                            timestamp = event.get("ts", time.time())
                            step = data.get("global_step") or data.get("step")
                            stage = data.get("stage")
                            
                            # Extract all numeric metrics from the data
                            for key, value in data.items():
                                if key in ("global_step", "step", "time", "stage"):
                                    continue
                                
                                if isinstance(value, (int, float)):
                                    # Filter by metric names if specified
                                    if metric_names and key not in metric_names:
                                        continue
                                    
                                    metrics.append(MetricRecord(
                                        experiment_id=exp_id,
                                        timestamp=timestamp,
                                        metric_name=key,
                                        metric_value=value,
                                        step=step,
                                        stage=stage,
                                        recorded_at=timestamp
                                    ))
                    
                    except json.JSONDecodeError:
                        continue
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to load metrics for {exp_id}: {e}")
            return []
    
    def _read_json_safe(self, path: Path) -> Dict[str, Any]:
        """Safely read JSON file with error handling."""
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.debug(f"Failed to read {path}: {e}")
        return {}


async def migrate_storage_system(root_dir: Path, backup: bool = True) -> MigrationStatus:
    """
    High-level function to migrate from file storage to SQLite.
    
    Args:
        root_dir: Root directory containing experiments
        backup: Whether to create backup before migration
        
    Returns:
        Migration status and results
    """
    logger.info("Starting storage system migration")
    
    if backup:
        await _create_backup(root_dir)
    
    migrator = FilesToSQLiteMigrator(root_dir)
    status = await migrator.migrate_with_verification()
    
    if status.status == "completed":
        logger.info("Storage migration completed successfully")
    else:
        logger.error(f"Storage migration failed: {status.errors}")
    
    return status


async def _create_backup(root_dir: Path) -> Path:
    """
    Create backup of existing storage before migration.
    
    Args:
        root_dir: Root directory to backup
        
    Returns:
        Path to backup directory
    """
    import shutil
    
    backup_name = f"runicorn_backup_{int(time.time())}"
    backup_path = root_dir.parent / backup_name
    
    logger.info(f"Creating backup at {backup_path}")
    shutil.copytree(root_dir, backup_path)
    
    logger.info(f"Backup created successfully: {backup_path}")
    return backup_path


def detect_storage_type(root_dir: Path) -> str:
    """
    Detect the current storage type in use.
    
    Args:
        root_dir: Root directory to inspect
        
    Returns:
        Storage type: 'file_only', 'sqlite_only', or 'hybrid'
    """
    db_path = root_dir / "runicorn.db"
    has_sqlite = db_path.exists()
    
    # Check for file-based experiments
    has_files = False
    
    # Check new layout
    for item in root_dir.iterdir():
        if item.is_dir() and item.name not in {"runs", "webui"}:
            # Look for project directories
            for project_item in item.iterdir():
                if project_item.is_dir():
                    runs_dir = project_item / "runs"
                    if runs_dir.exists() and any(runs_dir.iterdir()):
                        has_files = True
                        break
            if has_files:
                break
    
    # Check legacy layout
    if not has_files:
        runs_dir = root_dir / "runs"
        if runs_dir.exists() and any(runs_dir.iterdir()):
            has_files = True
    
    if has_sqlite and has_files:
        return "hybrid"
    elif has_sqlite:
        return "sqlite_only"
    elif has_files:
        return "file_only"
    else:
        return "empty"


async def ensure_modern_storage(root_dir: Path) -> StorageBackend:
    """
    Ensure modern storage is available, migrating if necessary.
    
    Args:
        root_dir: Root directory for storage
        
    Returns:
        Appropriate storage backend for current state
    """
    storage_type = detect_storage_type(root_dir)
    
    if storage_type == "file_only":
        logger.info("Detected file-only storage, starting migration to hybrid")
        # Start migration process
        status = await migrate_storage_system(root_dir)
        if status.status == "completed":
            logger.info("Migration to hybrid storage completed")
            return SQLiteStorageBackend(root_dir)
        else:
            logger.warning("Migration failed, falling back to file storage")
            return FileStorageBackend(root_dir)
    
    elif storage_type == "sqlite_only":
        logger.info("Using SQLite storage backend")
        return SQLiteStorageBackend(root_dir)
    
    elif storage_type == "hybrid":
        logger.info("Using hybrid storage backend")
        from .backends import HybridStorageBackend
        return HybridStorageBackend(root_dir)
    
    else:  # empty
        logger.info("Initializing new SQLite storage")
        return SQLiteStorageBackend(root_dir)
