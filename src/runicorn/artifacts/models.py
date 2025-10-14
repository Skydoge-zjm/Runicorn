"""
Artifact Data Models

Defines core data structures for the artifact versioning system.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ArtifactType(str, Enum):
    """Artifact type enumeration."""
    MODEL = "model"
    DATASET = "dataset"
    CONFIG = "config"
    CODE = "code"
    CUSTOM = "custom"


class ArtifactStatus(str, Enum):
    """Artifact status enumeration."""
    PENDING = "pending"
    UPLOADING = "uploading"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


@dataclass
class FileEntry:
    """
    File entry in an artifact.
    
    Represents a single file with its metadata and content hash.
    """
    path: str          # Relative path within artifact
    size: int          # File size in bytes
    digest: str        # SHA256 hash for content addressing
    modified_at: Optional[float] = None  # Original file modification time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FileEntry:
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ReferenceEntry:
    """
    External reference entry (e.g., S3, HTTP).
    
    Used for large datasets that are stored externally.
    """
    uri: str           # External URI (s3://bucket/path, https://...)
    checksum: Optional[str] = None  # Optional checksum for verification
    size: Optional[int] = None      # Optional size hint
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ReferenceEntry:
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ArtifactMetadata:
    """
    Artifact version metadata.
    
    Contains all information about a specific version of an artifact.
    """
    # Core identification
    name: str
    type: str  # ArtifactType
    version: int
    
    # Timestamps
    created_at: float
    updated_at: float
    
    # Ownership
    created_by_run: str
    created_by_user: Optional[str] = None
    
    # Size and content
    size_bytes: int = 0
    num_files: int = 0
    num_references: int = 0
    
    # Status
    status: str = ArtifactStatus.READY.value
    
    # User metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Aliases
    aliases: List[str] = field(default_factory=list)
    
    # Lineage tracking
    parent_artifacts: List[str] = field(default_factory=list)  # Artifacts used to create this
    
    # Checksum for integrity
    manifest_digest: Optional[str] = None  # Hash of manifest file
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ArtifactMetadata:
        """Create from dictionary."""
        return cls(**data)
    
    def add_alias(self, alias: str) -> None:
        """Add an alias to this version."""
        if alias not in self.aliases:
            self.aliases.append(alias)
            self.updated_at = time.time()
    
    def remove_alias(self, alias: str) -> None:
        """Remove an alias from this version."""
        if alias in self.aliases:
            self.aliases.remove(alias)
            self.updated_at = time.time()


@dataclass
class ArtifactManifest:
    """
    Artifact manifest containing all files and references.
    
    The manifest is a complete inventory of the artifact's contents.
    """
    files: List[FileEntry] = field(default_factory=list)
    references: List[ReferenceEntry] = field(default_factory=list)
    total_size: int = 0
    total_files: int = 0
    total_references: int = 0
    created_at: float = field(default_factory=time.time)
    
    def add_file(self, file_entry: FileEntry) -> None:
        """Add a file entry."""
        self.files.append(file_entry)
        self.total_files += 1
        self.total_size += file_entry.size
    
    def add_reference(self, reference_entry: ReferenceEntry) -> None:
        """Add a reference entry."""
        self.references.append(reference_entry)
        self.total_references += 1
        if reference_entry.size:
            self.total_size += reference_entry.size
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "files": [f.to_dict() for f in self.files],
            "references": [r.to_dict() for r in self.references],
            "total_size": self.total_size,
            "total_files": self.total_files,
            "total_references": self.total_references,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ArtifactManifest:
        """Create from dictionary."""
        manifest = cls(
            total_size=data.get("total_size", 0),
            total_files=data.get("total_files", 0),
            total_references=data.get("total_references", 0),
            created_at=data.get("created_at", time.time())
        )
        
        for file_data in data.get("files", []):
            manifest.files.append(FileEntry.from_dict(file_data))
        
        for ref_data in data.get("references", []):
            manifest.references.append(ReferenceEntry.from_dict(ref_data))
        
        return manifest


@dataclass
class ArtifactVersionInfo:
    """
    Lightweight version information for listing.
    
    Used in versions index for quick lookup.
    """
    version: int
    created_at: float
    created_by_run: str
    size_bytes: int
    num_files: int
    status: str = ArtifactStatus.READY.value
    aliases: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ArtifactVersionInfo:
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ArtifactIndex:
    """
    Artifact index containing all versions.
    
    Stored in versions.json at artifact root.
    """
    artifact_name: str
    artifact_type: str
    versions: List[ArtifactVersionInfo] = field(default_factory=list)
    aliases: Dict[str, int] = field(default_factory=dict)  # alias_name -> version_number
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    def add_version(self, version_info: ArtifactVersionInfo) -> None:
        """
        Add a new version.
        
        Args:
            version_info: Version information to add
            
        Raises:
            ValueError: If version already exists
        """
        # Check for duplicate versions
        if any(v.version == version_info.version for v in self.versions):
            raise ValueError(f"Version {version_info.version} already exists")
        
        self.versions.append(version_info)
        self.updated_at = time.time()
        
        # Update "latest" alias to point to this version
        self.aliases["latest"] = version_info.version
        
        # Add other aliases from version info
        for alias in version_info.aliases:
            if alias != "latest":  # "latest" is auto-managed
                self.aliases[alias] = version_info.version
    
    def get_version_by_alias(self, alias: str) -> Optional[int]:
        """Get version number by alias."""
        return self.aliases.get(alias)
    
    def get_latest_version(self) -> Optional[ArtifactVersionInfo]:
        """Get the latest version info."""
        if not self.versions:
            return None
        return self.versions[-1]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "artifact_name": self.artifact_name,
            "artifact_type": self.artifact_type,
            "versions": [v.to_dict() for v in self.versions],
            "aliases": self.aliases,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ArtifactIndex:
        """Create from dictionary."""
        index = cls(
            artifact_name=data["artifact_name"],
            artifact_type=data["artifact_type"],
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            aliases=data.get("aliases", {})
        )
        
        for version_data in data.get("versions", []):
            index.versions.append(ArtifactVersionInfo.from_dict(version_data))
        
        return index


@dataclass
class LineageNode:
    """
    Node in artifact lineage graph.
    
    Represents an artifact or run in the dependency graph.
    """
    node_type: str  # "artifact" or "run"
    node_id: str    # artifact_name:version or run_id
    label: str      # Display label
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class LineageEdge:
    """
    Edge in artifact lineage graph.
    
    Represents a dependency relationship.
    """
    source: str  # Source node ID
    target: str  # Target node ID
    edge_type: str  # "uses" or "produces"
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class LineageGraph:
    """
    Complete lineage graph for an artifact.
    
    Contains nodes (artifacts and runs) and edges (dependencies).
    """
    root_artifact: str  # The artifact we're analyzing
    nodes: List[LineageNode] = field(default_factory=list)
    edges: List[LineageEdge] = field(default_factory=list)
    
    def add_node(self, node: LineageNode) -> None:
        """Add a node to the graph."""
        # Avoid duplicates
        if not any(n.node_id == node.node_id for n in self.nodes):
            self.nodes.append(node)
    
    def add_edge(self, edge: LineageEdge) -> None:
        """Add an edge to the graph."""
        # Avoid duplicates
        if not any(e.source == edge.source and e.target == edge.target for e in self.edges):
            self.edges.append(edge)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "root_artifact": self.root_artifact,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LineageGraph:
        """Create from dictionary."""
        graph = cls(root_artifact=data["root_artifact"])
        
        for node_data in data.get("nodes", []):
            graph.nodes.append(LineageNode(**node_data))
        
        for edge_data in data.get("edges", []):
            graph.edges.append(LineageEdge(**edge_data))
        
        return graph
