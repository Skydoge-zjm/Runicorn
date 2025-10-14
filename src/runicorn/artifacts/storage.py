"""
Artifact Storage Manager

Handles physical storage, versioning, and retrieval of artifacts.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from filelock import FileLock

from .models import (
    ArtifactType,
    ArtifactStatus,
    FileEntry,
    ArtifactMetadata,
    ArtifactManifest,
    ArtifactVersionInfo,
    ArtifactIndex
)

logger = logging.getLogger(__name__)


class ArtifactStorage:
    """
    Manages artifact storage with versioning and deduplication.
    
    Handles:
    - Version management
    - File storage with optional deduplication
    - Metadata management
    - Manifest generation
    """
    
    def __init__(self, storage_root: Path, enable_dedup: bool = True):
        """
        Initialize artifact storage.
        
        Args:
            storage_root: Root directory for all storage
            enable_dedup: Enable content deduplication (default: True)
        """
        self.storage_root = Path(storage_root)
        self.artifacts_root = self.storage_root / "artifacts"
        self.dedup_pool = self.artifacts_root / ".dedup" if enable_dedup else None
        self.enable_dedup = enable_dedup
        
        # Create directories
        self.artifacts_root.mkdir(parents=True, exist_ok=True)
        if self.dedup_pool:
            self.dedup_pool.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Artifact storage initialized: {self.artifacts_root} (dedup={enable_dedup})")
    
    def save_artifact(
        self,
        artifact: 'Artifact',
        run_id: str,
        staged_files: List[Tuple[Path, str]],
        staged_references: List,
        user: Optional[str] = None
    ) -> int:
        """
        Save an artifact to storage and assign version number.
        
        Args:
            artifact: Artifact object to save
            run_id: Run ID that created this artifact
            staged_files: List of (source_path, artifact_path) tuples
            staged_references: List of external references
            user: Optional user identifier
            
        Returns:
            Version number assigned to this artifact
            
        Raises:
            ValueError: If artifact validation fails
        """
        # Get artifact directory
        artifact_dir = self._get_artifact_dir(artifact.name, artifact.type)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate that there's something to save
        if not staged_files and not staged_references:
            raise ValueError("Artifact has no files or references to save")
        
        # Use file lock for thread-safety
        lock_path = artifact_dir / ".lock"
        lock = FileLock(str(lock_path), timeout=30)
        
        try:
            lock.acquire()
            
            try:
                # Load or create index
                index = self._load_or_create_index(artifact.name, artifact.type)
                
                # Determine next version
                next_version = len(index.versions) + 1
                
                # Create version directory
                version_dir = artifact_dir / f"v{next_version}"
                
                # Safety check: version dir should not exist
                if version_dir.exists():
                    logger.error(f"Version directory already exists: {version_dir}")
                    raise RuntimeError(f"Version v{next_version} already exists for {artifact.name}")
                
                files_dir = version_dir / "files"
                files_dir.mkdir(parents=True, exist_ok=True)
                
                # Build manifest and copy files
                manifest = ArtifactManifest()
                
                # Process files
                for source_path, artifact_path in staged_files:
                    try:
                        # Verify source file still exists
                        if not source_path.exists():
                            raise FileNotFoundError(f"Source file not found: {source_path}")
                        
                        file_entry = self._store_file(source_path, artifact_path, files_dir)
                        manifest.add_file(file_entry)
                    except Exception as e:
                        logger.error(f"Failed to store file {artifact_path}: {e}")
                        # Clean up partially created version
                        if version_dir.exists():
                            shutil.rmtree(version_dir)
                        raise
                
                # Process references
                for ref in staged_references:
                    manifest.add_reference(ref)
                
                # Save manifest
                manifest_path = version_dir / "manifest.json"
                manifest_path.write_text(
                    json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                
                # Compute manifest digest
                manifest_digest = self._compute_string_hash(manifest_path.read_text())
                
                # Create metadata
                metadata = ArtifactMetadata(
                    name=artifact.name,
                    type=artifact.type,
                    version=next_version,
                    created_at=time.time(),
                    updated_at=time.time(),
                    created_by_run=run_id,
                    created_by_user=user,
                    size_bytes=manifest.total_size,
                    num_files=manifest.total_files,
                    num_references=manifest.total_references,
                    status=ArtifactStatus.READY.value,
                    metadata=artifact.metadata,
                    description=artifact.description,
                    tags=getattr(artifact, '_tags', []),
                    aliases=["latest"],  # New versions get "latest"
                    manifest_digest=manifest_digest
                )
                
                # Save metadata
                metadata_path = version_dir / "metadata.json"
                metadata_path.write_text(
                    json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                
                # Update index
                version_info = ArtifactVersionInfo(
                    version=next_version,
                    created_at=metadata.created_at,
                    created_by_run=run_id,
                    size_bytes=metadata.size_bytes,
                    num_files=metadata.num_files,
                    status=metadata.status,
                    aliases=metadata.aliases
                )
                index.add_version(version_info)
                
                # Save index
                self._save_index(artifact.name, artifact.type, index)
                
                logger.info(
                    f"Saved artifact {artifact.name}:v{next_version} "
                    f"({metadata.size_bytes:,} bytes, {metadata.num_files} files, "
                    f"{metadata.num_references} references)"
                )
                
                return next_version
                
            finally:
                # Ensure lock is released
                lock.release()
                
        except Exception as e:
            # Clean up lock file on error
            try:
                if lock_path.exists():
                    lock_path.unlink()
            except Exception:
                pass
            raise
    
    def load_artifact(
        self,
        name: str,
        type: str,
        version: Optional[int] = None,
        alias: Optional[str] = None
    ) -> Tuple[ArtifactMetadata, ArtifactManifest]:
        """
        Load artifact metadata and manifest.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Optional version number
            alias: Optional alias (e.g., "latest", "production")
            
        Returns:
            Tuple of (metadata, manifest)
            
        Raises:
            FileNotFoundError: If artifact or version not found
            ValueError: If both version and alias are specified or version invalid
        """
        if version is not None and alias is not None:
            raise ValueError("Cannot specify both version and alias")
        
        artifact_dir = self._get_artifact_dir(name, type)
        
        if not artifact_dir.exists():
            raise FileNotFoundError(f"Artifact not found: {name} (type={type})")
        
        # Determine version number
        if alias:
            index = self._load_index(name, type)
            version = index.get_version_by_alias(alias)
            if version is None:
                available = list(index.aliases.keys())
                raise ValueError(
                    f"Alias '{alias}' not found for artifact {name}. "
                    f"Available aliases: {available}"
                )
        elif version is None:
            # Default to latest
            index = self._load_index(name, type)
            latest = index.get_latest_version()
            if not latest:
                raise FileNotFoundError(f"No versions found for artifact: {name}")
            version = latest.version
        else:
            # Validate version number
            if not isinstance(version, int) or version <= 0:
                raise ValueError(f"Invalid version number: {version}")
        
        # Load metadata and manifest
        version_dir = artifact_dir / f"v{version}"
        
        if not version_dir.exists():
            raise FileNotFoundError(f"Version not found: {name}:v{version}")
        
        # Check if soft deleted
        if (version_dir / ".deleted").exists():
            logger.warning(f"Loading soft-deleted artifact: {name}:v{version}")
            # Continue loading but log warning
        
        metadata_path = version_dir / "metadata.json"
        manifest_path = version_dir / "manifest.json"
        
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata not found for {name}:v{version}")
        
        try:
            metadata = ArtifactMetadata.from_dict(
                json.loads(metadata_path.read_text(encoding="utf-8"))
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid metadata JSON for {name}:v{version}: {e}")
        
        if manifest_path.exists():
            try:
                manifest = ArtifactManifest.from_dict(
                    json.loads(manifest_path.read_text(encoding="utf-8"))
                )
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid manifest JSON for {name}:v{version}: {e}")
                manifest = ArtifactManifest()
        else:
            logger.debug(f"No manifest found for {name}:v{version}, using empty manifest")
            manifest = ArtifactManifest()
        
        return metadata, manifest
    
    def download_artifact(
        self,
        name: str,
        type: str,
        version: int,
        target_dir: Optional[Path] = None
    ) -> Path:
        """
        Download artifact files to target directory.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Version number
            target_dir: Optional target directory (defaults to temp)
            
        Returns:
            Path to downloaded files directory
            
        Note:
            If using temp directory (default), the directory will persist until
            Python process exits or system cleans temp files. User should copy
            files if needed for long-term storage.
        """
        version_dir = self._get_artifact_dir(name, type) / f"v{version}"
        files_dir = version_dir / "files"
        
        if not version_dir.exists():
            raise FileNotFoundError(f"Artifact version not found: {name}:v{version}")
        
        if not files_dir.exists():
            logger.warning(f"No files directory for {name}:v{version}, creating empty directory")
            # Artifact might only have references, not files
        
        # Determine target directory
        if target_dir:
            dest = Path(target_dir)
            dest.mkdir(parents=True, exist_ok=True)
        else:
            # Use temp directory with descriptive name
            dest = Path(tempfile.mkdtemp(prefix=f"runicorn_{name}_v{version}_"))
        
        # Copy all files (if any exist)
        if files_dir.exists() and list(files_dir.iterdir()):
            # Copy contents, not the files_dir itself
            for item in files_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, dest / item.name)
                elif item.is_dir():
                    shutil.copytree(item, dest / item.name, dirs_exist_ok=True)
        
        logger.info(f"Downloaded {name}:v{version} to {dest}")
        return dest
    
    def get_artifact_file_path(
        self,
        name: str,
        type: str,
        version: int,
        file_path: str
    ) -> Optional[Path]:
        """
        Get absolute path to a specific file in artifact.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Version number
            file_path: Relative path within artifact
            
        Returns:
            Absolute path if file exists, None otherwise
            
        Raises:
            ValueError: If file_path contains path traversal
        """
        # Security: Prevent path traversal
        if '..' in file_path or file_path.startswith('/') or file_path.startswith('\\'):
            raise ValueError(f"Invalid file path (path traversal detected): {file_path}")
        
        version_dir = self._get_artifact_dir(name, type) / f"v{version}"
        full_path = version_dir / "files" / file_path
        
        # Additional security: ensure the resolved path is within version_dir
        try:
            full_path_resolved = full_path.resolve()
            version_dir_resolved = version_dir.resolve()
            
            if not str(full_path_resolved).startswith(str(version_dir_resolved)):
                raise ValueError(f"Path escape detected: {file_path}")
        except Exception:
            return None
        
        return full_path if full_path.exists() else None
    
    def list_artifacts(self, type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all artifacts, optionally filtered by type.
        
        Args:
            type: Optional artifact type filter
            
        Returns:
            List of artifact summary dictionaries
        """
        results = []
        
        # Build type directories list
        if type:
            type_dir = self.artifacts_root / type
            if not type_dir.exists():
                logger.debug(f"Artifact type directory does not exist: {type}")
                return []  # Return empty list if type doesn't exist
            type_dirs = [type_dir]
        else:
            if not self.artifacts_root.exists():
                return []  # No artifacts at all
            type_dirs = list(self.artifacts_root.iterdir())
        
        for type_dir in type_dirs:
            if not type_dir.is_dir() or type_dir.name.startswith('.'):
                continue
            
            for artifact_dir in type_dir.iterdir():
                if not artifact_dir.is_dir():
                    continue
                
                try:
                    index = self._load_index(artifact_dir.name, type_dir.name)
                    latest = index.get_latest_version()
                    
                    if latest:
                        results.append({
                            "name": index.artifact_name,
                            "type": index.artifact_type,
                            "num_versions": len(index.versions),
                            "latest_version": latest.version,
                            "size_bytes": latest.size_bytes,
                            "created_at": index.created_at,
                            "updated_at": index.updated_at,
                            "aliases": index.aliases
                        })
                except Exception as e:
                    logger.warning(f"Failed to load index for {artifact_dir.name}: {e}")
        
        return sorted(results, key=lambda x: x["updated_at"], reverse=True)
    
    def list_versions(self, name: str, type: Optional[str] = None) -> List[ArtifactVersionInfo]:
        """
        List all versions of an artifact.
        
        Args:
            name: Artifact name
            type: Optional artifact type (if known)
            
        Returns:
            List of version information
            
        Raises:
            FileNotFoundError: If artifact not found
        """
        # If type not specified, search all types
        if type:
            try:
                index = self._load_index(name, type)
                return index.versions
            except FileNotFoundError:
                raise FileNotFoundError(f"Artifact not found: {name} (type={type})")
        
        # Search all types
        for type_dir in self.artifacts_root.iterdir():
            if not type_dir.is_dir() or type_dir.name.startswith('.'):
                continue
            
            try:
                index = self._load_index(name, type_dir.name)
                return index.versions
            except FileNotFoundError:
                continue
        
        raise FileNotFoundError(f"Artifact not found: {name}")
    
    def delete_artifact_version(
        self,
        name: str,
        type: str,
        version: int,
        soft_delete: bool = True
    ) -> bool:
        """
        Delete an artifact version.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Version number
            soft_delete: If True, mark as deleted; if False, permanently delete
            
        Returns:
            True if successful
        """
        version_dir = self._get_artifact_dir(name, type) / f"v{version}"
        
        if not version_dir.exists():
            logger.warning(f"Version directory not found: {name}:v{version}")
            return False
        
        # Check if already deleted
        if (version_dir / ".deleted").exists() and soft_delete:
            logger.warning(f"Version already soft deleted: {name}:v{version}")
            return True
        
        if soft_delete:
            # Mark as deleted
            deleted_marker = version_dir / ".deleted"
            try:
                deleted_marker.write_text(json.dumps({
                    "deleted_at": time.time(),
                    "deleted_by": "user",
                    "version": version,
                    "artifact_name": name
                }, ensure_ascii=False), encoding="utf-8")
                
                logger.info(f"Soft deleted {name}:v{version}")
            except Exception as e:
                logger.error(f"Failed to soft delete {name}:v{version}: {e}")
                return False
        else:
            # Permanently delete
            try:
                # Windows compatibility: retry deletion with delay
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        shutil.rmtree(version_dir)
                        break
                    except PermissionError as e:
                        if retry < max_retries - 1:
                            logger.debug(f"Retry {retry+1}/{max_retries} for deletion: {e}")
                            time.sleep(0.1)  # Brief delay for Windows
                        else:
                            raise
                
                # Update index to remove this version
                try:
                    index = self._load_index(name, type)
                    index.versions = [v for v in index.versions if v.version != version]
                    
                    # Update aliases that pointed to this version
                    aliases_to_remove = [
                        alias for alias, v in index.aliases.items()
                        if v == version
                    ]
                    for alias in aliases_to_remove:
                        del index.aliases[alias]
                    
                    # If "latest" was removed, reassign to new latest
                    if "latest" not in index.aliases and index.versions:
                        latest_v = index.versions[-1].version
                        index.aliases["latest"] = latest_v
                    
                    self._save_index(name, type, index)
                    logger.debug(f"Updated index after deleting v{version}")
                    
                except Exception as e:
                    logger.warning(f"Failed to update index after deletion: {e}")
                
                logger.info(f"Permanently deleted {name}:v{version}")
                
            except Exception as e:
                logger.error(f"Failed to permanently delete {name}:v{version}: {e}")
                return False
        
        return True
    
    def _store_file(
        self,
        source_path: Path,
        artifact_path: str,
        dest_dir: Path
    ) -> FileEntry:
        """
        Store a file and return its entry.
        
        Args:
            source_path: Source file path
            artifact_path: Path within artifact
            dest_dir: Destination directory for files
            
        Returns:
            FileEntry with file metadata
        """
        # Compute hash
        file_hash = self._compute_file_hash(source_path)
        file_size = source_path.stat().st_size
        modified_at = source_path.stat().st_mtime
        
        # Security: Validate artifact_path doesn't escape dest_dir
        if '..' in artifact_path:
            raise ValueError(f"Invalid artifact path (contains '..'): {artifact_path}")
        
        # Windows: Check total path length (Windows has 260 char limit)
        dest_path_full = dest_dir / artifact_path
        
        # Calculate total path length including all parent directories
        total_path_len = len(str(dest_path_full.resolve()))
        
        if total_path_len > 240:  # Leave margin below 260
            # Try to provide helpful error
            raise ValueError(
                f"File path too long for Windows filesystem: {total_path_len} chars (limit ~240).\n"
                f"Path: {str(dest_path_full)[:100]}...\n"
                f"Solution: Use shorter artifact names or file names."
            )
        
        # Destination path
        dest_path = dest_dir / artifact_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.enable_dedup and self.dedup_pool:
            # Use deduplication
            dedup_saved = self._store_with_dedup(source_path, file_hash, dest_path)
            if dedup_saved:
                logger.debug(f"Deduplicated {artifact_path} (saved {file_size:,} bytes)")
        else:
            # Direct copy
            shutil.copy2(source_path, dest_path)
        
        return FileEntry(
            path=artifact_path,
            size=file_size,
            digest=f"sha256:{file_hash}",
            modified_at=modified_at
        )
    
    def _store_with_dedup(
        self,
        source_path: Path,
        file_hash: str,
        dest_path: Path
    ) -> bool:
        """
        Store file with deduplication using hardlinks.
        
        Strategy:
        1. Check if file exists in dedup pool
        2. If yes: use hardlink (or copy if cross-filesystem)
        3. If no: copy to pool, then hardlink to dest
        
        Args:
            source_path: Source file
            file_hash: File content hash (pre-computed)
            dest_path: Destination path
            
        Returns:
            True if deduplicated (space saved), False if new file
            
        Raises:
            IOError: If file operations fail critically
        """
        # Dedup pool path (shard by first 2 chars for filesystem performance)
        dedup_path = self.dedup_pool / file_hash[:2] / file_hash
        
        # Ensure dest parent exists
        # Windows: Check path length limit (260 chars)
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            if "too long" in str(e).lower() or len(str(dest_path)) > 250:
                raise ValueError(
                    f"Path too long for Windows (limit ~260 chars): {len(str(dest_path))} chars. "
                    f"Consider using shorter artifact or file names."
                ) from e
            raise
        
        if dedup_path.exists():
            # File exists in dedup pool - reuse it
            # Performance: Skip hash verification (trust the pool)
            # Future: Add periodic integrity check job instead
            return self._create_link_or_copy(dedup_path, dest_path, is_dedup=True)
        else:
            # First time - create new dedup entry
            return self._create_new_dedup_entry(source_path, dedup_path, dest_path)
    
    def _create_link_or_copy(self, source: Path, dest: Path, is_dedup: bool) -> bool:
        """
        Create hardlink or copy as fallback.
        
        Args:
            source: Source file path
            dest: Destination file path
            is_dedup: Whether this is a dedup operation
            
        Returns:
            True if dedup succeeded, False otherwise
        """
        # Remove existing dest if present
        if dest.exists():
            try:
                dest.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove existing dest: {e}")
        
        # Try hardlink first (zero space cost)
        try:
            dest.hardlink_to(source)
            if is_dedup:
                logger.debug(f"Deduplicated via hardlink: {dest.name}")
            return is_dedup
        except OSError as e:
            # Hardlink failed (cross-filesystem, permissions, etc.)
            logger.debug(f"Hardlink failed ({e}), falling back to copy")
            try:
                shutil.copy2(source, dest)
                return False  # Copy succeeded but no dedup benefit
            except Exception as e:
                logger.error(f"Failed to copy file: {e}")
                raise IOError(f"Cannot create file {dest}: {e}") from e
    
    def _create_new_dedup_entry(self, source: Path, dedup_path: Path, dest: Path) -> bool:
        """
        Create new dedup pool entry.
        
        Args:
            source: Source file
            dedup_path: Dedup pool path
            dest: Destination path
            
        Returns:
            False (new file, no dedup)
        """
        # Ensure dedup directory exists
        dedup_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Copy source to dedup pool
            shutil.copy2(source, dedup_path)
            
            # Create link from dest to dedup pool
            return self._create_link_or_copy(dedup_path, dest, is_dedup=False)
            
        except Exception as e:
            logger.error(f"Failed to create dedup entry: {e}")
            # Fallback: direct copy without dedup
            try:
                if not dest.exists():
                    shutil.copy2(source, dest)
                return False
            except Exception as e2:
                raise IOError(f"Cannot store file {dest}: {e2}") from e2
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file."""
        sha256 = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):  # 64KB chunks
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def _compute_string_hash(self, content: str) -> str:
        """Compute SHA256 hash of string."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _get_artifact_dir(self, name: str, type: str) -> Path:
        """Get artifact directory path."""
        return self.artifacts_root / type / name
    
    def _load_index(self, name: str, type: str) -> ArtifactIndex:
        """Load artifact index from storage."""
        index_path = self._get_artifact_dir(name, type) / "versions.json"
        
        if not index_path.exists():
            raise FileNotFoundError(f"Artifact index not found: {name}")
        
        data = json.loads(index_path.read_text(encoding="utf-8"))
        return ArtifactIndex.from_dict(data)
    
    def _load_or_create_index(self, name: str, type: str) -> ArtifactIndex:
        """Load existing index or create new one."""
        try:
            return self._load_index(name, type)
        except FileNotFoundError:
            return ArtifactIndex(
                artifact_name=name,
                artifact_type=type
            )
    
    def _save_index(self, name: str, type: str, index: ArtifactIndex) -> None:
        """
        Save artifact index to storage with atomic write.
        
        Uses write-to-temp-then-rename pattern for atomicity.
        """
        index_path = self._get_artifact_dir(name, type) / "versions.json"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomic write: write to temp file then rename
        import tempfile
        
        # Create temp file but close it immediately for Windows compatibility
        temp_fd, temp_path = tempfile.mkstemp(
            dir=index_path.parent,
            prefix=".versions_",
            suffix=".json.tmp",
            text=False  # Binary mode for Windows
        )
        
        try:
            # Close the file descriptor immediately (Windows requirement)
            os.close(temp_fd)
            
            # Write to temp file
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(index.to_dict(), f, indent=2, ensure_ascii=False)
            
            # Atomic rename (POSIX atomic, Windows best-effort)
            temp_path_obj = Path(temp_path)
            
            # On Windows, remove target first if exists
            if os.name == 'nt' and index_path.exists():
                try:
                    index_path.unlink()
                except Exception:
                    pass
            
            temp_path_obj.replace(index_path)
            
        except Exception as e:
            # Clean up temp file on failure
            try:
                if Path(temp_path).exists():
                    Path(temp_path).unlink()
            except Exception:
                pass
            raise IOError(f"Failed to save index for {name}: {e}") from e
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        stats = {
            "total_artifacts": 0,
            "total_versions": 0,
            "total_size_bytes": 0,
            "total_files": 0,
            "dedup_enabled": self.enable_dedup,
            "by_type": {}
        }
        
        for type_dir in self.artifacts_root.iterdir():
            if not type_dir.is_dir() or type_dir.name.startswith('.'):
                continue
            
            type_name = type_dir.name
            type_stats = {
                "count": 0,
                "versions": 0,
                "size_bytes": 0
            }
            
            for artifact_dir in type_dir.iterdir():
                if not artifact_dir.is_dir():
                    continue
                
                try:
                    index = self._load_index(artifact_dir.name, type_name)
                    type_stats["count"] += 1
                    type_stats["versions"] += len(index.versions)
                    
                    for v in index.versions:
                        type_stats["size_bytes"] += v.size_bytes
                    
                except Exception:
                    pass
            
            if type_stats["count"] > 0:
                stats["by_type"][type_name] = type_stats
                stats["total_artifacts"] += type_stats["count"]
                stats["total_versions"] += type_stats["versions"]
                stats["total_size_bytes"] += type_stats["size_bytes"]
        
        # Count dedup pool if enabled
        if self.dedup_pool and self.dedup_pool.exists():
            dedup_size = sum(
                f.stat().st_size 
                for f in self.dedup_pool.rglob("*") 
                if f.is_file()
            )
            stats["dedup_pool_size_bytes"] = dedup_size
            stats["space_saved_bytes"] = stats["total_size_bytes"] - dedup_size
            stats["dedup_ratio"] = 1 - (dedup_size / stats["total_size_bytes"]) if stats["total_size_bytes"] > 0 else 0
        
        return stats
    
    def cleanup_orphaned_dedup(self) -> int:
        """
        Clean up orphaned files in dedup pool.
        
        Returns:
            Number of files cleaned up
        """
        if not self.enable_dedup or not self.dedup_pool:
            return 0
        
        # Build set of all referenced hashes
        referenced_hashes = set()
        
        for type_dir in self.artifacts_root.iterdir():
            if not type_dir.is_dir() or type_dir.name.startswith('.'):
                continue
            
            for artifact_dir in type_dir.iterdir():
                if not artifact_dir.is_dir():
                    continue
                
                for version_dir in artifact_dir.iterdir():
                    if not version_dir.is_dir() or not version_dir.name.startswith('v'):
                        continue
                    
                    manifest_path = version_dir / "manifest.json"
                    if manifest_path.exists():
                        try:
                            manifest = ArtifactManifest.from_dict(
                                json.loads(manifest_path.read_text())
                            )
                            for file_entry in manifest.files:
                                # Extract hash from digest (format: "sha256:hash")
                                if ':' in file_entry.digest:
                                    hash_value = file_entry.digest.split(':', 1)[1]
                                    referenced_hashes.add(hash_value)
                        except Exception as e:
                            logger.warning(f"Failed to load manifest {manifest_path}: {e}")
        
        # Find orphaned files
        cleaned = 0
        for dedup_file in self.dedup_pool.rglob("*"):
            if not dedup_file.is_file():
                continue
            
            file_hash = dedup_file.name
            if file_hash not in referenced_hashes:
                # Orphaned file
                try:
                    dedup_file.unlink()
                    cleaned += 1
                    logger.debug(f"Cleaned orphaned dedup file: {file_hash}")
                except Exception as e:
                    logger.warning(f"Failed to delete orphaned file: {e}")
        
        logger.info(f"Cleaned {cleaned} orphaned dedup files")
        return cleaned


def create_artifact_storage(storage_root: Path) -> ArtifactStorage:
    """
    Factory function to create artifact storage.
    
    Args:
        storage_root: Storage root directory
        
    Returns:
        ArtifactStorage instance
    """
    return ArtifactStorage(storage_root, enable_dedup=True)
