"""
Modern Storage Service Integration

Integrates the new storage backends with the viewer API layer.
This service provides a high-level interface for the API routes.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...storage.backends import StorageBackend, SQLiteStorageBackend, HybridStorageBackend
from ...storage.models import ExperimentRecord, MetricRecord, QueryParams
from ...storage.migration import ensure_modern_storage, detect_storage_type

logger = logging.getLogger(__name__)


class ModernStorageService:
    """
    High-level storage service that abstracts storage backend complexity.
    
    This service provides a clean interface for the API layer while
    handling backend selection and migration automatically.
    """
    
    def __init__(self, root_dir: Path, force_backend: Optional[str] = None):
        """
        Initialize modern storage service.
        
        Args:
            root_dir: Root directory for storage
            force_backend: Force specific backend ('file', 'sqlite', 'hybrid')
        """
        self.root_dir = Path(root_dir)
        self.backend: Optional[StorageBackend] = None
        self.force_backend = force_backend
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize the storage backend.
        
        This method automatically selects the appropriate backend
        and performs migration if necessary.
        """
        if self._initialized:
            return
        
        try:
            if self.force_backend:
                self.backend = await self._create_forced_backend()
            else:
                self.backend = await ensure_modern_storage(self.root_dir)
            
            self._initialized = True
            backend_type = type(self.backend).__name__
            storage_type = detect_storage_type(self.root_dir)
            logger.info(f"Storage initialized: {backend_type} (detected: {storage_type})")
            
        except Exception as e:
            logger.error(f"Failed to initialize storage: {e}")
            # Fallback to file storage for safety
            from ...storage.backends import FileStorageBackend
            self.backend = FileStorageBackend(self.root_dir)
            self._initialized = True
    
    async def _create_forced_backend(self) -> StorageBackend:
        """Create storage backend based on force_backend setting."""
        if self.force_backend == "sqlite":
            return SQLiteStorageBackend(self.root_dir)
        elif self.force_backend == "hybrid":
            return HybridStorageBackend(self.root_dir)
        else:  # file
            from ...storage.backends import FileStorageBackend
            return FileStorageBackend(self.root_dir)
    
    async def list_experiments(self, **kwargs) -> List[Dict[str, Any]]:
        """
        List experiments with modern query capabilities.
        
        Args:
            **kwargs: Query parameters (project, status, limit, etc.)
            
        Returns:
            List of experiment dictionaries compatible with API
        """
        await self.initialize()
        
        # Convert API parameters to QueryParams
        query = QueryParams(
            project=kwargs.get('project'),
            name=kwargs.get('name'),
            status=kwargs.get('status'),
            search_text=kwargs.get('search'),
            created_after=kwargs.get('created_after'),
            created_before=kwargs.get('created_before'),
            limit=kwargs.get('limit', 100),
            offset=kwargs.get('offset', 0),
            order_by=kwargs.get('order_by', 'created_at'),
            order_desc=kwargs.get('order_desc', True),
            include_deleted=kwargs.get('include_deleted', False)
        )
        
        experiments = await self.backend.list_experiments(query)
        
        # Convert to API-compatible format
        return [self._experiment_to_api_format(exp) for exp in experiments]
    
    async def count_experiments(self, **kwargs) -> int:
        """
        Count experiments matching query parameters.
        
        Args:
            **kwargs: Query parameters for filtering
            
        Returns:
            Number of matching experiments
        """
        await self.initialize()
        
        # Convert API parameters to QueryParams
        query = QueryParams(
            project=kwargs.get('project'),
            name=kwargs.get('name'), 
            status=kwargs.get('status'),
            search_text=kwargs.get('search'),
            created_after=kwargs.get('created_after'),
            created_before=kwargs.get('created_before'),
            include_deleted=kwargs.get('include_deleted', False),
            best_metric_range=kwargs.get('best_metric_range')
        )
        
        return await self.backend.count_experiments(query)
    
    async def get_experiment_detail(self, exp_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed experiment information.
        
        Args:
            exp_id: Experiment ID
            
        Returns:
            Experiment details in API format
        """
        await self.initialize()
        
        experiment = await self.backend.get_experiment(exp_id)
        if not experiment:
            return None
        
        return self._experiment_to_api_format(experiment)
    
    async def get_experiment_metrics(self, exp_id: str, aggregation_type: str = "step") -> Dict[str, Any]:
        """
        Get experiment metrics in the format expected by the frontend.
        
        Args:
            exp_id: Experiment ID  
            aggregation_type: Type of aggregation ('step', 'time')
            
        Returns:
            Metrics data with columns and rows
        """
        await self.initialize()
        
        metrics = await self.backend.get_metrics(exp_id)
        
        if not metrics:
            return {"columns": [], "rows": []}
        
        # Group metrics by step for frontend compatibility
        step_data = {}
        metric_names = set()
        
        for metric in metrics:
            step = metric.step or 0
            if step not in step_data:
                step_data[step] = {"global_step": step}
            
            step_data[step][metric.metric_name] = metric.metric_value
            metric_names.add(metric.metric_name)
        
        # Create columns and rows format expected by frontend
        columns = ["global_step"] + sorted(list(metric_names))
        rows = []
        
        for step in sorted(step_data.keys()):
            row = step_data[step]
            # Ensure all columns are present
            for col in columns:
                if col not in row:
                    row[col] = None
            rows.append(row)
        
        return {"columns": columns, "rows": rows}
    
    async def update_experiment_status(self, exp_id: str, status: str, **kwargs) -> bool:
        """
        Update experiment status and related fields.
        
        Args:
            exp_id: Experiment ID
            status: New status value
            **kwargs: Additional fields to update
            
        Returns:
            True if successful
        """
        await self.initialize()
        
        updates = {"status": status, **kwargs}
        if status in ["finished", "failed", "interrupted"] and "ended_at" not in updates:
            updates["ended_at"] = time.time()
        
        return await self.backend.update_experiment(exp_id, updates)
    
    async def soft_delete_experiments(self, exp_ids: List[str], reason: str = "user_deleted") -> Dict[str, Any]:
        """
        Soft delete experiments.
        
        Args:
            exp_ids: List of experiment IDs
            reason: Reason for deletion
            
        Returns:
            Deletion results in API format
        """
        await self.initialize()
        
        results = await self.backend.soft_delete_experiments(exp_ids, reason)
        successful_deletes = sum(1 for success in results.values() if success)
        
        return {
            "deleted_count": successful_deletes,
            "results": {exp_id: {"success": success} for exp_id, success in results.items()},
            "message": f"Soft deleted {successful_deletes} of {len(exp_ids)} runs"
        }
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive storage statistics.
        
        Returns:
            Storage statistics in API format
        """
        await self.initialize()
        
        stats = await self.backend.get_storage_stats()
        storage_type = detect_storage_type(self.root_dir)
        
        return {
            "storage_type": storage_type,
            "backend_type": type(self.backend).__name__,
            "statistics": stats.to_dict(),
            "performance": {
                "avg_query_time_ms": stats.avg_query_time_ms,
                "cache_hit_rate": stats.cache_hit_rate
            }
        }
    
    def _experiment_to_api_format(self, experiment: ExperimentRecord) -> Dict[str, Any]:
        """
        Convert ExperimentRecord to API format expected by frontend.
        
        Args:
            experiment: ExperimentRecord to convert
            
        Returns:
            Dictionary in API format
        """
        return {
            "id": experiment.id,
            "run_dir": experiment.run_dir,
            "created_time": experiment.created_at,
            "status": experiment.status,
            "pid": experiment.pid,
            "best_metric_value": experiment.best_metric_value,
            "best_metric_name": experiment.best_metric_name,
            "project": experiment.project,
            "name": experiment.name,
            # Additional fields for API compatibility
            "logs": str(Path(experiment.run_dir) / "logs.txt"),
            "metrics": str(Path(experiment.run_dir) / "events.jsonl"),
            "metrics_step": str(Path(experiment.run_dir) / "events.jsonl"),
        }


# Global storage service instance
_storage_service: Optional[ModernStorageService] = None


def get_storage_service(root_dir: Path) -> ModernStorageService:
    """
    Get the global storage service instance.
    
    Args:
        root_dir: Root directory for storage
        
    Returns:
        ModernStorageService instance
    """
    global _storage_service
    
    if _storage_service is None:
        _storage_service = ModernStorageService(root_dir)
    
    return _storage_service


def reset_storage_service() -> None:
    """Reset the global storage service (for testing)."""
    global _storage_service
    _storage_service = None
