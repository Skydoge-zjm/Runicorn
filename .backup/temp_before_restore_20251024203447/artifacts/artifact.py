"""
Artifact Class

Core class for creating and managing versioned artifacts (models, datasets, etc.).
"""
from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

from .models import (
    ArtifactType, 
    ArtifactStatus, 
    FileEntry, 
    ReferenceEntry,
    ArtifactMetadata,
    ArtifactManifest
)

if TYPE_CHECKING:
    from .storage import ArtifactStorage

logger = logging.getLogger(__name__)


class Artifact:
    """
    Artifact for versioned storage of models, datasets, and files.
    
    Artifacts provide version control for ML assets with automatic tracking,
    content deduplication, and lineage management.
    
    Usage:
        # Create and save
        artifact = Artifact("my-model", type="model")
        artifact.add_file("model.pth")
        artifact.add_metadata({"accuracy": 0.95})
        run.log_artifact(artifact)
        
        # Load and use
        artifact = run.use_artifact("my-model:latest")
        model_path = artifact.download()
    
    Attributes:
        name: Artifact name (unique within type)
        type: Artifact type (model, dataset, config, etc.)
        description: Optional description
        metadata: User-defined metadata dictionary
        version: Version number (set after saving)
    """
    
    def __init__(
        self,
        name: str,
        type: Union[str, ArtifactType] = ArtifactType.MODEL,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a new artifact.
        
        Args:
            name: Artifact name (must be valid filename)
            type: Artifact type ('model', 'dataset', 'config', 'custom')
            description: Optional description
            metadata: Optional metadata dictionary
            
        Raises:
            ValueError: If name is invalid
        """
        # Validate name
        if not name or not isinstance(name, str):
            raise ValueError("Artifact name must be a non-empty string")
        
        if any(c in name for c in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
            raise ValueError(f"Artifact name contains invalid characters: {name}")
        
        self.name = name
        self.type = type if isinstance(type, str) else type.value
        self.description = description
        self.metadata = metadata or {}
        self._tags: List[str] = []  # Initialize tags list
        
        # Internal state
        self._staged_files: List[tuple[Path, str]] = []  # (source_path, artifact_path)
        self._staged_file_paths: set[str] = set()  # Track to prevent duplicates
        self._staged_references: List[ReferenceEntry] = []
        self._manifest: Optional[ArtifactManifest] = None
        self._artifact_metadata: Optional[ArtifactMetadata] = None
        
        # Set after saving or loading
        self._version: Optional[int] = None
        self._storage: Optional[ArtifactStorage] = None
        self._is_loaded = False
    
    @property
    def version(self) -> Optional[int]:
        """Get artifact version number."""
        return self._version
    
    @property
    def is_loaded(self) -> bool:
        """Check if artifact is loaded from storage."""
        return self._is_loaded
    
    @property
    def full_name(self) -> str:
        """Get full artifact name with version."""
        if self._version is not None:
            return f"{self.name}:v{self._version}"
        return f"{self.name}:unstaged"
    
    def add_file(self, path: Union[str, Path], name: Optional[str] = None) -> Artifact:
        """
        Add a file to the artifact.
        
        Args:
            path: Path to the file to add
            name: Optional name for the file within artifact (defaults to filename)
            
        Returns:
            Self for method chaining
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path is a directory
        """
        file_path = Path(path).resolve()
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        if not file_path.is_file():
            raise ValueError(f"Not a file (use add_dir for directories): {path}")
        
        # Determine artifact path
        artifact_path = name if name else file_path.name
        
        # Check for duplicates
        if artifact_path in self._staged_file_paths:
            logger.warning(f"File {artifact_path} already staged, skipping duplicate")
            return self
        
        # Stage for later upload
        self._staged_files.append((file_path, artifact_path))
        self._staged_file_paths.add(artifact_path)
        
        file_size = file_path.stat().st_size
        logger.info(f"Staged file for {self.name}: {artifact_path} ({file_size:,} bytes)")
        
        return self
    
    def add_dir(
        self, 
        path: Union[str, Path], 
        name: Optional[str] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> Artifact:
        """
        Add a directory recursively to the artifact.
        
        Args:
            path: Path to the directory to add
            name: Optional prefix for files within artifact
            exclude_patterns: Optional list of glob patterns to exclude
            
        Returns:
            Self for method chaining
            
        Raises:
            FileNotFoundError: If directory doesn't exist
            ValueError: If path is not a directory
        """
        dir_path = Path(path).resolve()
        
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        
        if not dir_path.is_dir():
            raise ValueError(f"Not a directory: {path}")
        
        exclude_patterns = exclude_patterns or []
        added_count = 0
        total_size = 0
        
        # Add all files in directory
        for file_path in sorted(dir_path.rglob("*")):
            if not file_path.is_file():
                continue
            
            # Check exclude patterns
            should_exclude = False
            for pattern in exclude_patterns:
                if file_path.match(pattern):
                    should_exclude = True
                    break
            
            if should_exclude:
                continue
            
            # Calculate relative path
            rel_path = file_path.relative_to(dir_path)
            artifact_path = str(Path(name) / rel_path) if name else str(rel_path)
            
            # Check for duplicates
            if artifact_path in self._staged_file_paths:
                continue
            
            self._staged_files.append((file_path, artifact_path))
            self._staged_file_paths.add(artifact_path)
            added_count += 1
            total_size += file_path.stat().st_size
        
        if added_count == 0:
            logger.warning(f"No files found in directory: {path}")
        else:
            logger.info(f"Staged directory for {self.name}: {path} ({added_count} files, {total_size:,} bytes)")
        
        return self
    
    def add_reference(
        self,
        uri: str,
        checksum: Optional[str] = None,
        size: Optional[int] = None,
        name: Optional[str] = None,
        **metadata
    ) -> Artifact:
        """
        Add a reference to external data (e.g., S3, HTTP URL).
        
        This is useful for very large datasets that shouldn't be copied locally.
        
        Args:
            uri: URI to external resource (s3://..., https://..., etc.)
            checksum: Optional checksum for verification (format: "sha256:hash")
            size: Optional size hint in bytes
            name: Optional name for the reference
            **metadata: Additional metadata for the reference
            
        Returns:
            Self for method chaining
        """
        reference = ReferenceEntry(
            uri=uri,
            checksum=checksum,
            size=size,
            metadata=metadata
        )
        
        self._staged_references.append(reference)
        
        ref_name = name or Path(uri).name
        logger.info(f"Staged reference for {self.name}: {ref_name} → {uri}")
        
        return self
    
    def add_metadata(self, metadata: Dict[str, Any]) -> Artifact:
        """
        Add or update metadata.
        
        Args:
            metadata: Dictionary of metadata to add/update
            
        Returns:
            Self for method chaining
        """
        self.metadata.update(metadata)
        return self
    
    def add_tags(self, *tags: str) -> Artifact:
        """
        Add tags to artifact.
        
        Args:
            *tags: Tag strings to add
            
        Returns:
            Self for method chaining
        """
        for tag in tags:
            if tag and isinstance(tag, str) and tag not in self._tags:
                self._tags.append(tag)
        
        return self
    
    def get_manifest(self) -> Optional[ArtifactManifest]:
        """
        Get artifact manifest.
        
        Returns:
            Manifest if artifact is loaded, None otherwise
        """
        return self._manifest
    
    def get_metadata(self) -> Optional[ArtifactMetadata]:
        """
        Get artifact metadata.
        
        Returns:
            Metadata if artifact is loaded, None otherwise
        """
        return self._artifact_metadata
    
    def download(self, target_dir: Optional[Union[str, Path]] = None) -> Path:
        """
        Download artifact files to local directory.
        
        Args:
            target_dir: Optional target directory (defaults to temp dir)
            
        Returns:
            Path to downloaded files directory
            
        Raises:
            RuntimeError: If artifact is not loaded from storage
        """
        if not self._is_loaded or not self._storage:
            raise RuntimeError(f"Artifact {self.name} is not loaded. Use run.use_artifact() first.")
        
        return self._storage.download_artifact(self.name, self.type, self._version, target_dir)
    
    def get_file_path(self, file_path: str) -> Optional[Path]:
        """
        Get path to a specific file in the artifact.
        
        Args:
            file_path: Relative path of file within artifact
            
        Returns:
            Absolute path to file if found, None otherwise
        """
        if not self._is_loaded or not self._storage:
            raise RuntimeError(f"Artifact {self.name} is not loaded")
        
        return self._storage.get_artifact_file_path(self.name, self.type, self._version, file_path)
    
    def get_references(self) -> List[ReferenceEntry]:
        """
        Get all external references in this artifact.
        
        Returns:
            List of reference entries
        """
        if self._manifest:
            return self._manifest.references
        return self._staged_references
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """
        Compute SHA256 hash of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hexadecimal SHA256 hash
        """
        sha256 = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def __repr__(self) -> str:
        """String representation."""
        if self._version is not None:
            return f"<Artifact {self.name}:v{self._version} type={self.type}>"
        return f"<Artifact {self.name} type={self.type} (unstaged)>"
    
    def __str__(self) -> str:
        """String representation."""
        return self.full_name
