"""
Storage Data Models

Defines data structures for the modern storage system.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict, fields as dataclass_fields


@dataclass
class ExperimentRecord:
    """
    Core experiment record structure.
    
    This represents all metadata about an experiment run.
    """
    # Primary identification
    id: str
    path: str  # Flexible hierarchy path (e.g., "cv/detection/yolo")
    alias: Optional[str] = None  # Optional user-friendly alias (can be repeated)
    
    # Timestamps
    created_at: float = 0.0
    updated_at: float = 0.0
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    
    # Status management
    status: str = "running"  # 'running', 'finished', 'failed', 'interrupted'
    exit_reason: Optional[str] = None
    
    # Process information
    pid: Optional[int] = None
    python_version: Optional[str] = None
    platform: Optional[str] = None
    hostname: Optional[str] = None
    
    # Best metric tracking
    best_metric_name: Optional[str] = None
    best_metric_value: Optional[float] = None
    best_metric_step: Optional[int] = None
    best_metric_mode: Optional[str] = None  # 'max' or 'min'
    
    # Soft delete support
    deleted_at: Optional[float] = None
    delete_reason: Optional[str] = None
    
    # File system integration
    run_dir: str = ""
    
    # Computed fields
    duration_seconds: Optional[float] = None
    metric_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperimentRecord':
        """Create from dictionary."""
        # Handle legacy data with project/name fields
        if 'project' in data and 'name' in data and 'path' not in data:
            data['path'] = f"{data.pop('project')}/{data.pop('name')}"
        elif 'project' in data:
            data.pop('project', None)
        if 'name' in data:
            data.pop('name', None)
        
        # Filter to only known fields
        known_fields = {f.name for f in dataclass_fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered_data)
    
    def is_active(self) -> bool:
        """Check if experiment is active (not deleted)."""
        return self.deleted_at is None
    
    def is_running(self) -> bool:
        """Check if experiment is currently running."""
        return self.status == "running" and self.is_active()
    
    def compute_duration(self) -> Optional[float]:
        """Compute experiment duration in seconds."""
        if self.started_at and self.ended_at:
            return self.ended_at - self.started_at
        elif self.started_at and self.status == "running":
            return time.time() - self.started_at
        return None
    
    @property
    def short_id(self) -> str:
        """Get short ID (last 6 characters of run_id)."""
        return self.id[-6:] if len(self.id) >= 6 else self.id
    
    def path_parts(self) -> List[str]:
        """Split path into parts."""
        if not self.path or self.path == "/":
            return []
        return [p for p in self.path.split("/") if p]


@dataclass
class MetricRecord:
    """
    Individual metric data point structure.
    """
    experiment_id: str
    timestamp: float
    metric_name: str
    metric_value: Optional[float]  # None for NaN/Inf values
    step: Optional[int] = None
    stage: Optional[str] = None  # 'warmup', 'train', 'eval'
    recorded_at: float = None
    
    def __post_init__(self):
        if self.recorded_at is None:
            self.recorded_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetricRecord':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class QueryParams:
    """
    Parameters for experiment queries.
    """
    # Filters
    path: Optional[str] = None  # Filter by path prefix
    path_exact: bool = False  # If True, match exact path; if False, match prefix
    alias: Optional[str] = None  # Filter by alias (fuzzy match)
    status: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    created_after: Optional[float] = None
    created_before: Optional[float] = None
    best_metric_range: Optional[Tuple[float, float]] = None
    search_text: Optional[str] = None
    include_deleted: bool = False
    
    # Pagination and sorting
    limit: int = 100
    offset: int = 0
    order_by: str = "created_at"
    order_desc: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def cache_key(self) -> str:
        """Generate cache key for this query."""
        import hashlib
        import json
        
        # Create deterministic cache key
        data = self.to_dict()
        # Convert any datetime objects to timestamps for consistency
        if isinstance(data.get('created_after'), datetime):
            data['created_after'] = data['created_after'].timestamp()
        if isinstance(data.get('created_before'), datetime):
            data['created_before'] = data['created_before'].timestamp()
        
        content = json.dumps(data, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class EnvironmentRecord:
    """
    Environment information for reproducibility.
    """
    experiment_id: str
    
    # Git information
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    git_dirty: Optional[bool] = None
    git_remote: Optional[str] = None
    git_last_commit_message: Optional[str] = None
    
    # Python environment
    python_executable: Optional[str] = None
    pip_packages: Optional[List[str]] = None
    conda_env: Optional[str] = None
    conda_packages: Optional[List[str]] = None
    
    # System information
    cpu_count: Optional[int] = None
    memory_total_gb: Optional[float] = None
    gpu_info: Optional[List[Dict[str, Any]]] = None
    
    # Environment variables
    env_variables: Optional[Dict[str, str]] = None
    
    # Metadata
    captured_at: float = None
    
    def __post_init__(self):
        if self.captured_at is None:
            self.captured_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod  
    def from_dict(cls, data: Dict[str, Any]) -> 'EnvironmentRecord':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class StorageStats:
    """
    Storage system statistics and health metrics.
    """
    total_experiments: int = 0
    active_experiments: int = 0
    deleted_experiments: int = 0
    total_metrics_points: int = 0
    storage_size_bytes: int = 0
    
    # Performance metrics
    avg_query_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    
    # Database health
    db_size_mb: float = 0.0
    db_fragmentation_pct: float = 0.0
    
    # Last updated
    updated_at: float = None
    
    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass 
class MigrationStatus:
    """
    Status information for storage migration.
    """
    migration_type: str  # 'file_to_sqlite', 'sqlite_to_hybrid'
    status: str         # 'pending', 'in_progress', 'completed', 'failed'
    
    # Progress tracking
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    
    # Timing
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    estimated_completion_at: Optional[float] = None
    
    # Error tracking
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def progress_percent(self) -> float:
        """Calculate migration progress percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100.0
    
    @property
    def is_complete(self) -> bool:
        """Check if migration is complete."""
        return self.status == 'completed'
    
    @property
    def has_errors(self) -> bool:
        """Check if migration has errors."""
        return len(self.errors) > 0 or self.failed_items > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
