"""
Manifest Generator

Server-side component that generates sync manifests by scanning the experiment directory.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import platform
import socket
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import (
    ExperimentEntry,
    FileEntry,
    ManifestType,
    SyncManifest
)

logger = logging.getLogger(__name__)


class ManifestGenerator:
    """
    Generates sync manifests by scanning experiment directories.
    
    Features:
    - Dual-layer manifests (active/full)
    - Incremental generation
    - Atomic writes
    - Security validation
    - Compression support
    """
    
    # Format version
    FORMAT_VERSION = "1.0"
    GENERATOR_VERSION = "1.0"
    
    # File size limits
    MAX_MANIFEST_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_METADATA_FILE_SIZE = 1 * 1024 * 1024  # 1MB
    
    # Metadata file patterns (small files to include)
    METADATA_FILES = {
        "meta.json",
        "status.json",
        "summary.json",
        "environment.json",
        "artifacts_created.json",
        "artifacts_used.json",
    }
    
    # Essential data files (may be large, but important)
    ESSENTIAL_FILES = {
        "events.jsonl",  # Metrics data
        "logs.txt",  # Training logs
    }
    
    # Append-only file patterns
    APPEND_ONLY_FILES = {
        "events.jsonl",
        "logs.txt",
    }
    
    # Directories to skip
    SKIP_DIRS = {
        '.git',
        '.cache',
        '__pycache__',
        'node_modules',
        '.runicorn',
    }
    
    def __init__(
        self,
        remote_root: Path,
        output_dir: Optional[Path] = None,
        active_window_seconds: int = 3600,  # 1 hour
        incremental: bool = True
    ):
        """
        Initialize manifest generator.
        
        Args:
            remote_root: Root directory of experiments
            output_dir: Directory to write manifests (default: remote_root/.runicorn)
            active_window_seconds: Time window for "active" experiments
            incremental: Use incremental generation
        """
        self.remote_root = remote_root.resolve()
        self.output_dir = output_dir or (remote_root / ".runicorn")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.active_window_seconds = active_window_seconds
        self.incremental = incremental
        
        # State
        self.server_hostname = socket.gethostname()
        self._current_revision = self._load_revision()
        self._previous_manifest: Optional[SyncManifest] = None
        
        logger.info(
            f"ManifestGenerator initialized: "
            f"root={self.remote_root}, "
            f"active_window={active_window_seconds}s, "
            f"incremental={incremental}"
        )
    
    def _load_revision(self) -> int:
        """Load last revision number from state file."""
        state_file = self.output_dir / ".manifest_state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                return data.get("last_revision", 0)
            except Exception as e:
                logger.warning(f"Failed to load revision state: {e}")
        return 0
    
    def _save_revision(self, revision: int) -> None:
        """Save current revision number to state file."""
        state_file = self.output_dir / ".manifest_state.json"
        try:
            data = {
                "last_revision": revision,
                "last_generated": time.time(),
            }
            state_file.write_text(
                json.dumps(data, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save revision state: {e}")
    
    def generate(
        self,
        manifest_type: ManifestType = ManifestType.FULL,
        output_path: Optional[Path] = None
    ) -> Tuple[SyncManifest, Path]:
        """
        Generate sync manifest.
        
        Args:
            manifest_type: Type of manifest to generate (full/active)
            output_path: Custom output path (optional)
            
        Returns:
            Tuple of (manifest, output_file_path)
        """
        start_time = time.time()
        snapshot_id = str(uuid.uuid4())
        
        logger.info(
            f"Starting manifest generation: "
            f"type={manifest_type.value}, snapshot={snapshot_id}"
        )
        
        # Scan experiments
        experiments = self._scan_experiments(manifest_type)
        
        # Create manifest
        manifest = SyncManifest(
            format_version=self.FORMAT_VERSION,
            manifest_type=manifest_type,
            revision=self._current_revision + 1,
            snapshot_id=snapshot_id,
            generated_at=time.time(),
            server_hostname=self.server_hostname,
            remote_root=str(self.remote_root),
            experiments=experiments,
            generator_version=self.GENERATOR_VERSION,
        )
        
        # Compute statistics
        manifest.compute_statistics()
        
        # Determine output path
        if output_path is None:
            filename = f"{manifest_type.value}_manifest.json"
            output_path = self.output_dir / filename
        
        # Write manifest
        self._write_manifest(manifest, output_path)
        
        # Update revision
        self._current_revision += 1
        self._save_revision(self._current_revision)
        
        duration = time.time() - start_time
        logger.info(
            f"Manifest generation complete: "
            f"experiments={manifest.total_experiments}, "
            f"files={manifest.total_files}, "
            f"bytes={manifest.total_bytes}, "
            f"duration={duration:.2f}s"
        )
        
        return manifest, output_path
    
    def _scan_experiments(
        self,
        manifest_type: ManifestType
    ) -> List[ExperimentEntry]:
        """
        Scan experiment directories and collect metadata.
        
        Args:
            manifest_type: Type of manifest being generated
            
        Returns:
            List of experiment entries
        """
        experiments = []
        cutoff_time = time.time() - self.active_window_seconds
        
        # Walk through project/experiment/runs structure
        try:
            for project_dir in self.remote_root.iterdir():
                if not project_dir.is_dir():
                    continue
                if project_dir.name.startswith('.') or project_dir.name in self.SKIP_DIRS:
                    continue
                
                project_name = project_dir.name
                
                # Special directories to skip
                if project_name in ['artifacts', 'sweeps']:
                    continue
                
                # Scan experiments in project
                for exp_dir in project_dir.iterdir():
                    if not exp_dir.is_dir():
                        continue
                    if exp_dir.name.startswith('.'):
                        continue
                    
                    exp_name = exp_dir.name
                    runs_dir = exp_dir / "runs"
                    
                    if not runs_dir.exists():
                        continue
                    
                    # Scan runs
                    for run_dir in runs_dir.iterdir():
                        if not run_dir.is_dir():
                            continue
                        if run_dir.name.startswith('.'):
                            continue
                        
                        run_id = run_dir.name
                        
                        # Check if active (for active manifest)
                        if manifest_type == ManifestType.ACTIVE:
                            try:
                                dir_mtime = run_dir.stat().st_mtime
                                if dir_mtime < cutoff_time:
                                    continue  # Skip old runs
                            except OSError:
                                continue
                        
                        # Scan run files
                        entry = self._scan_run(
                            project_name,
                            exp_name,
                            run_id,
                            run_dir
                        )
                        
                        if entry and entry.files:
                            experiments.append(entry)
        
        except Exception as e:
            logger.error(f"Failed to scan experiments: {e}")
        
        return experiments
    
    def _scan_run(
        self,
        project: str,
        name: str,
        run_id: str,
        run_dir: Path
    ) -> Optional[ExperimentEntry]:
        """
        Scan a single run directory.
        
        Args:
            project: Project name
            name: Experiment name
            run_id: Run ID
            run_dir: Run directory path
            
        Returns:
            ExperimentEntry or None if invalid
        """
        try:
            # Read metadata if available
            meta_file = run_dir / "meta.json"
            status_file = run_dir / "status.json"
            
            created_at = run_dir.stat().st_ctime
            updated_at = run_dir.stat().st_mtime
            status = "unknown"
            
            # Try to read status
            if status_file.exists():
                try:
                    status_data = json.loads(status_file.read_text(encoding="utf-8"))
                    status = status_data.get("status", "unknown")
                except:
                    pass
            
            # Collect files
            files = []
            
            # Metadata files
            for filename in self.METADATA_FILES:
                file_path = run_dir / filename
                if file_path.exists() and file_path.is_file():
                    file_entry = self._create_file_entry(
                        project, name, run_id, filename, file_path, priority=1
                    )
                    if file_entry:
                        files.append(file_entry)
            
            # Essential data files
            for filename in self.ESSENTIAL_FILES:
                file_path = run_dir / filename
                if file_path.exists() and file_path.is_file():
                    is_append_only = filename in self.APPEND_ONLY_FILES
                    file_entry = self._create_file_entry(
                        project, name, run_id, filename, file_path,
                        priority=2,
                        is_append_only=is_append_only
                    )
                    if file_entry:
                        files.append(file_entry)
            
            # Create experiment entry
            return ExperimentEntry(
                run_id=run_id,
                project=project,
                name=name,
                status=status,
                created_at=created_at,
                updated_at=updated_at,
                files=files,
            )
        
        except Exception as e:
            logger.error(f"Failed to scan run {run_id}: {e}")
            return None
    
    def _create_file_entry(
        self,
        project: str,
        name: str,
        run_id: str,
        filename: str,
        file_path: Path,
        priority: int = 0,
        is_append_only: bool = False
    ) -> Optional[FileEntry]:
        """
        Create file entry for manifest.
        
        Args:
            project: Project name
            name: Experiment name
            run_id: Run ID
            filename: File name
            file_path: Absolute file path
            priority: Sync priority
            is_append_only: Whether file is append-only
            
        Returns:
            FileEntry or None if invalid
        """
        try:
            stat_info = file_path.stat()
            size = stat_info.st_size
            mtime = stat_info.st_mtime
            
            # Skip oversized metadata files
            if filename in self.METADATA_FILES and size > self.MAX_METADATA_FILE_SIZE:
                logger.warning(f"Skipping oversized metadata file: {file_path} ({size} bytes)")
                return None
            
            # Build relative path
            rel_path = f"{project}/{name}/runs/{run_id}/{filename}"
            
            # Calculate tail hash for append-only files
            tail_hash = None
            if is_append_only and size > 0:
                tail_hash = self._calculate_tail_hash(file_path)
            
            return FileEntry(
                path=rel_path,
                size=size,
                mtime=mtime,
                tail_hash=tail_hash,
                priority=priority,
                is_append_only=is_append_only,
            )
        
        except Exception as e:
            logger.error(f"Failed to create file entry for {file_path}: {e}")
            return None
    
    def _calculate_tail_hash(self, file_path: Path, tail_size: int = 4096) -> str:
        """
        Calculate hash of file tail for append-only validation.
        
        Args:
            file_path: File to hash
            tail_size: Number of bytes from end to hash
            
        Returns:
            Hex digest of tail hash
        """
        try:
            file_size = file_path.stat().st_size
            if file_size == 0:
                return hashlib.md5(b"").hexdigest()
            
            read_size = min(tail_size, file_size)
            
            with open(file_path, 'rb') as f:
                f.seek(-read_size, 2)  # Seek from end
                tail_data = f.read(read_size)
                return hashlib.md5(tail_data).hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate tail hash for {file_path}: {e}")
            return ""
    
    def _write_manifest(
        self,
        manifest: SyncManifest,
        output_path: Path
    ) -> None:
        """
        Write manifest to file with atomic operation.
        
        Args:
            manifest: Manifest to write
            output_path: Output file path
        """
        try:
            # Validate manifest
            self._validate_manifest(manifest)
            
            # Serialize to JSON
            manifest_json = json.dumps(
                manifest.to_dict(),
                indent=2,
                ensure_ascii=False
            )
            
            # Check size
            manifest_size = len(manifest_json.encode('utf-8'))
            if manifest_size > self.MAX_MANIFEST_SIZE:
                raise ValueError(
                    f"Manifest size ({manifest_size} bytes) exceeds limit "
                    f"({self.MAX_MANIFEST_SIZE} bytes)"
                )
            
            # Atomic write: write to temp file first
            temp_path = output_path.with_suffix('.tmp')
            temp_path.write_text(manifest_json, encoding='utf-8')
            
            # Atomic rename
            if os.name == 'nt':  # Windows
                # Windows: os.replace works if on same volume
                try:
                    os.replace(str(temp_path), str(output_path))
                except OSError:
                    # Fallback: remove target and rename
                    if output_path.exists():
                        output_path.unlink()
                    temp_path.rename(output_path)
            else:  # Unix/Linux/macOS
                # POSIX: os.replace is atomic
                os.replace(str(temp_path), str(output_path))
            
            # Write compressed version
            gz_path = output_path.with_suffix('.json.gz')
            with gzip.open(gz_path, 'wt', encoding='utf-8') as f:
                f.write(manifest_json)
            
            logger.info(
                f"Manifest written: {output_path} "
                f"({manifest_size} bytes, compressed: {gz_path.stat().st_size} bytes)"
            )
        
        except Exception as e:
            logger.error(f"Failed to write manifest: {e}")
            raise
    
    def _validate_manifest(self, manifest: SyncManifest) -> None:
        """
        Validate manifest structure and security.
        
        Args:
            manifest: Manifest to validate
            
        Raises:
            ValueError: If validation fails
        """
        # Check required fields
        if not manifest.format_version:
            raise ValueError("Missing format_version")
        if not manifest.snapshot_id:
            raise ValueError("Missing snapshot_id")
        if manifest.revision < 1:
            raise ValueError("Invalid revision number")
        
        # Validate paths
        for exp in manifest.experiments:
            for file_entry in exp.files:
                self._validate_path(file_entry.path)
    
    def _validate_path(self, path: str) -> None:
        """
        Validate file path for security.
        
        Args:
            path: Path to validate
            
        Raises:
            ValueError: If path is invalid
        """
        # No absolute paths
        if os.path.isabs(path):
            raise ValueError(f"Absolute path not allowed: {path}")
        
        # No parent directory references
        if '..' in path.split('/'):
            raise ValueError(f"Parent directory reference not allowed: {path}")
        
        # Must follow expected pattern
        parts = path.split('/')
        if len(parts) < 5:  # project/name/runs/run_id/filename
            raise ValueError(f"Invalid path structure: {path}")
        
        if parts[2] != 'runs':
            raise ValueError(f"Invalid path structure (expected 'runs'): {path}")
