"""
Manifest Data Models

Defines the structure of sync manifests for efficient metadata synchronization.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
import time


class ManifestType(str, Enum):
    """Manifest type enumeration."""
    FULL = "full"  # Complete catalog of all experiments
    ACTIVE = "active"  # Only active/recent experiments


@dataclass
class FileEntry:
    """
    Single file entry in manifest.
    
    Represents a file that should be synchronized to client.
    """
    path: str  # Relative POSIX path from remote_root
    size: int  # File size in bytes
    mtime: float  # Modification timestamp
    
    # Optional fields for optimization
    tail_hash: Optional[str] = None  # For append-only file verification
    priority: int = 0  # Sync priority (higher = more important)
    is_append_only: bool = False  # Hint for incremental sync
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d = {
            "path": self.path,
            "size": self.size,
            "mtime": self.mtime,
        }
        if self.tail_hash:
            d["tail_hash"] = self.tail_hash
        if self.priority != 0:
            d["priority"] = self.priority
        if self.is_append_only:
            d["is_append_only"] = True
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FileEntry:
        """Create from dictionary."""
        return cls(
            path=data["path"],
            size=data["size"],
            mtime=data["mtime"],
            tail_hash=data.get("tail_hash"),
            priority=data.get("priority", 0),
            is_append_only=data.get("is_append_only", False),
        )


@dataclass
class ExperimentEntry:
    """
    Experiment metadata in manifest.
    
    Groups files belonging to a single experiment run.
    """
    run_id: str  # Unique run identifier
    project: str  # Project name
    name: str  # Experiment name
    status: str  # Status: running, completed, failed
    
    # Timestamps
    created_at: float  # Creation timestamp
    updated_at: float  # Last update timestamp
    
    # Files belonging to this run
    files: List[FileEntry] = field(default_factory=list)
    
    # Optional metadata
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "project": self.project,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "files": [f.to_dict() for f in self.files],
            "tags": self.tags if self.tags else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExperimentEntry:
        """Create from dictionary."""
        return cls(
            run_id=data["run_id"],
            project=data["project"],
            name=data["name"],
            status=data["status"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            files=[FileEntry.from_dict(f) for f in data.get("files", [])],
            tags=data.get("tags") or [],
        )


@dataclass
class ManifestFormat:
    """Manifest format version and structure."""
    version: str = "1.0"  # Manifest format version
    
    # Supported features
    supports_incremental: bool = True
    supports_compression: bool = True
    supports_tail_hash: bool = True


@dataclass
class SyncManifest:
    """
    Complete sync manifest.
    
    Contains metadata about all experiments and files to synchronize.
    """
    # Manifest metadata
    format_version: str  # Manifest format version
    manifest_type: ManifestType  # full or active
    revision: int  # Monotonic revision number
    snapshot_id: str  # Unique snapshot identifier (UUID)
    generated_at: float  # Generation timestamp
    
    # Server information
    server_hostname: str  # Server identifier
    remote_root: str  # Remote storage root path
    
    # Experiments
    experiments: List[ExperimentEntry] = field(default_factory=list)
    
    # Statistics
    total_experiments: int = 0
    total_files: int = 0
    total_bytes: int = 0
    
    # Metadata
    generator_version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "format_version": self.format_version,
            "manifest_type": self.manifest_type.value if isinstance(self.manifest_type, ManifestType) else self.manifest_type,
            "revision": self.revision,
            "snapshot_id": self.snapshot_id,
            "generated_at": self.generated_at,
            "server_hostname": self.server_hostname,
            "remote_root": self.remote_root,
            "experiments": [e.to_dict() for e in self.experiments],
            "statistics": {
                "total_experiments": self.total_experiments,
                "total_files": self.total_files,
                "total_bytes": self.total_bytes,
            },
            "generator_version": self.generator_version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SyncManifest:
        """Create from dictionary."""
        stats = data.get("statistics", {})
        return cls(
            format_version=data["format_version"],
            manifest_type=ManifestType(data["manifest_type"]),
            revision=data["revision"],
            snapshot_id=data["snapshot_id"],
            generated_at=data["generated_at"],
            server_hostname=data["server_hostname"],
            remote_root=data["remote_root"],
            experiments=[ExperimentEntry.from_dict(e) for e in data.get("experiments", [])],
            total_experiments=stats.get("total_experiments", 0),
            total_files=stats.get("total_files", 0),
            total_bytes=stats.get("total_bytes", 0),
            generator_version=data.get("generator_version", "1.0"),
        )
    
    def compute_statistics(self) -> None:
        """Compute and update statistics from experiments."""
        self.total_experiments = len(self.experiments)
        self.total_files = sum(len(e.files) for e in self.experiments)
        self.total_bytes = sum(
            sum(f.size for f in e.files)
            for e in self.experiments
        )
