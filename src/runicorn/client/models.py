"""
Data models for Runicorn API client responses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class RunInfo:
    """Run record (corresponds to server-side RunListItem)."""
    id: str
    status: str
    created_time: Optional[float] = None
    path: Optional[str] = None
    alias: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    best_metric_value: Optional[float] = None
    best_metric_name: Optional[str] = None
    assets_count: int = 0
    run_dir: Optional[str] = None
    pid: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RunInfo:
        """Create from API response."""
        return cls(
            id=data["id"],
            status=data.get("status", "unknown"),
            created_time=data.get("created_time"),
            path=data.get("path"),
            alias=data.get("alias"),
            tags=data.get("tags", []),
            best_metric_value=data.get("best_metric_value"),
            best_metric_name=data.get("best_metric_name"),
            assets_count=data.get("assets_count", 0),
            run_dir=data.get("run_dir"),
            pid=data.get("pid"),
        )
    
    @property
    def created_datetime(self) -> Optional[datetime]:
        """Convert created_time to datetime."""
        if self.created_time is not None:
            return datetime.fromtimestamp(self.created_time)
        return None


# Backward compatibility
Experiment = RunInfo


@dataclass
class MetricPoint:
    """Single metric data point."""
    step: int
    value: float
    timestamp: float
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MetricPoint:
        """Create from API response."""
        return cls(
            step=data["step"],
            value=data["value"],
            timestamp=data.get("timestamp", 0),
        )


@dataclass
class MetricSeries:
    """Time series for a single metric."""
    name: str
    points: List[MetricPoint]
    
    @classmethod
    def from_dict(cls, name: str, points_data: List[Dict]) -> MetricSeries:
        """Create from API response."""
        points = [MetricPoint.from_dict(p) for p in points_data]
        return cls(name=name, points=points)
    
    @property
    def values(self) -> List[float]:
        """Get all values."""
        return [p.value for p in self.points]
    
    @property
    def steps(self) -> List[int]:
        """Get all steps."""
        return [p.step for p in self.points]
    
    def last_value(self) -> Optional[float]:
        """Get last value."""
        return self.points[-1].value if self.points else None
    
    def min_value(self) -> Optional[float]:
        """Get minimum value."""
        return min(self.values) if self.values else None
    
    def max_value(self) -> Optional[float]:
        """Get maximum value."""
        return max(self.values) if self.values else None


@dataclass
class RemoteSession:
    """Remote viewer session."""
    session_id: str
    connection_id: str
    remote_host: str
    remote_port: int
    local_port: int
    remote_root: str
    status: str
    created_at: float
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RemoteSession:
        """Create from API response."""
        return cls(
            session_id=data["session_id"],
            connection_id=data.get("connection_id", ""),
            remote_host=data.get("remote_host", ""),
            remote_port=data.get("remote_port", 0),
            local_port=data.get("local_port", 0),
            remote_root=data.get("remote_root", ""),
            status=data.get("status", "unknown"),
            created_at=data.get("created_at", 0),
        )
    
    @property
    def local_url(self) -> str:
        """Get local access URL."""
        return f"http://localhost:{self.local_port}"


@dataclass
class PathInfo:
    """Path statistics (corresponds to server-side path stats)."""
    path: str
    total: int = 0
    running: int = 0
    finished: int = 0
    failed: int = 0
    
    @classmethod
    def from_dict(cls, path: str, data: Dict[str, Any]) -> PathInfo:
        """Create from API response."""
        return cls(
            path=path,
            total=data.get("total", 0),
            running=data.get("running", 0),
            finished=data.get("finished", 0),
            failed=data.get("failed", 0),
        )


# Backward compatibility
Project = PathInfo
