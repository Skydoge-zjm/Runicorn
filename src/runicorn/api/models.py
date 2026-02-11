"""
Data models for Runicorn API responses
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class Experiment:
    """Experiment record."""
    id: str
    project: str
    name: str
    status: str
    created_at: float
    updated_at: float
    summary: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Experiment:
        """Create from API response."""
        return cls(
            id=data["id"],
            project=data.get("project", "default"),
            name=data.get("name", "default"),
            status=data.get("status", "unknown"),
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
            summary=data.get("summary", {}),
            tags=data.get("tags", []),
        )
    
    @property
    def created_datetime(self) -> datetime:
        """Convert created_at to datetime."""
        return datetime.fromtimestamp(self.created_at)
    
    @property
    def updated_datetime(self) -> datetime:
        """Convert updated_at to datetime."""
        return datetime.fromtimestamp(self.updated_at)


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
class Project:
    """Project summary."""
    name: str
    experiment_count: int
    latest_update: float
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Project:
        """Create from API response."""
        return cls(
            name=data["name"],
            experiment_count=data.get("experiment_count", 0),
            latest_update=data.get("latest_update", 0),
        )
