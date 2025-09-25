"""
Enhanced experiment management for Runicorn.
Provides tagging, searching, and batch operations.
"""
from __future__ import annotations

import json
import logging
import shutil
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)


@dataclass
class ExperimentMetadata:
    """Extended metadata for experiments."""
    id: str
    project: str
    name: str
    tags: List[str]
    description: Optional[str]
    created_at: float
    updated_at: float
    archived: bool = False
    pinned: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperimentMetadata':
        """Create from dictionary."""
        return cls(**data)


class ExperimentManager:
    """Manage experiments with enhanced features."""
    
    def __init__(self, storage_root: Path):
        """
        Initialize experiment manager.
        
        Args:
            storage_root: Root directory for storage
        """
        self.storage_root = Path(storage_root)
        self.metadata_file = self.storage_root / ".experiments_metadata.json"
        self._load_metadata()
    
    def _load_metadata(self) -> None:
        """Load experiment metadata from disk."""
        self.metadata: Dict[str, ExperimentMetadata] = {}
        
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for exp_id, exp_data in data.items():
                        self.metadata[exp_id] = ExperimentMetadata.from_dict(exp_data)
            except Exception as e:
                logger.error(f"Failed to load experiment metadata: {e}")
    
    def _save_metadata(self) -> None:
        """Save experiment metadata to disk."""
        try:
            data = {exp_id: meta.to_dict() for exp_id, meta in self.metadata.items()}
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save experiment metadata: {e}")
    
    def add_experiment(self, run_id: str, project: str, name: str, 
                      tags: Optional[List[str]] = None,
                      description: Optional[str] = None) -> ExperimentMetadata:
        """Add or update experiment metadata."""
        now = time.time()
        
        if run_id in self.metadata:
            # Update existing
            meta = self.metadata[run_id]
            meta.updated_at = now
            if tags is not None:
                meta.tags = tags
            if description is not None:
                meta.description = description
        else:
            # Create new
            meta = ExperimentMetadata(
                id=run_id,
                project=project,
                name=name,
                tags=tags or [],
                description=description,
                created_at=now,
                updated_at=now
            )
            self.metadata[run_id] = meta
        
        self._save_metadata()
        return meta
    
    def tag_experiment(self, run_id: str, tags: List[str], append: bool = True) -> bool:
        """
        Add tags to an experiment.
        
        Args:
            run_id: Experiment run ID
            tags: Tags to add
            append: If True, append to existing tags; if False, replace
            
        Returns:
            True if successful
        """
        if run_id not in self.metadata:
            logger.warning(f"Experiment {run_id} not found")
            return False
        
        meta = self.metadata[run_id]
        if append:
            # Append unique tags
            existing_tags = set(meta.tags)
            new_tags = existing_tags.union(set(tags))
            meta.tags = list(new_tags)
        else:
            meta.tags = tags
        
        meta.updated_at = time.time()
        self._save_metadata()
        return True
    
    def search_experiments(self, 
                          project: Optional[str] = None,
                          tags: Optional[List[str]] = None,
                          text: Optional[str] = None,
                          archived: Optional[bool] = False,
                          pinned: Optional[bool] = None) -> List[ExperimentMetadata]:
        """
        Search experiments by various criteria.
        
        Args:
            project: Filter by project name
            tags: Filter by tags (experiments must have all specified tags)
            text: Search in name and description
            archived: Include archived experiments
            pinned: Filter by pinned status
            
        Returns:
            List of matching experiments
        """
        results = []
        
        for meta in self.metadata.values():
            # Skip archived unless explicitly requested
            if not archived and meta.archived:
                continue
            
            # Project filter
            if project and meta.project != project:
                continue
            
            # Tags filter (must have all specified tags)
            if tags:
                experiment_tags = set(meta.tags)
                required_tags = set(tags)
                if not required_tags.issubset(experiment_tags):
                    continue
            
            # Text search
            if text:
                text_lower = text.lower()
                searchable = [
                    meta.name.lower(),
                    meta.project.lower(),
                    (meta.description or "").lower(),
                    " ".join(meta.tags).lower()
                ]
                if not any(text_lower in s for s in searchable):
                    continue
            
            # Pinned filter
            if pinned is not None and meta.pinned != pinned:
                continue
            
            results.append(meta)
        
        # Sort by updated time (most recent first)
        results.sort(key=lambda x: x.updated_at, reverse=True)
        return results
    
    def archive_experiment(self, run_id: str, archive: bool = True) -> bool:
        """Archive or unarchive an experiment."""
        if run_id not in self.metadata:
            logger.warning(f"Experiment {run_id} not found")
            return False
        
        self.metadata[run_id].archived = archive
        self.metadata[run_id].updated_at = time.time()
        self._save_metadata()
        return True
    
    def pin_experiment(self, run_id: str, pin: bool = True) -> bool:
        """Pin or unpin an experiment."""
        if run_id not in self.metadata:
            logger.warning(f"Experiment {run_id} not found")
            return False
        
        self.metadata[run_id].pinned = pin
        self.metadata[run_id].updated_at = time.time()
        self._save_metadata()
        return True
    
    def delete_experiments(self, run_ids: List[str], force: bool = False) -> Dict[str, bool]:
        """
        Delete experiments and their data.
        
        Args:
            run_ids: List of run IDs to delete
            force: If True, delete even if pinned
            
        Returns:
            Dictionary of run_id -> success status
        """
        results = {}
        
        for run_id in run_ids:
            try:
                if run_id not in self.metadata:
                    results[run_id] = False
                    continue
                
                meta = self.metadata[run_id]
                
                # Don't delete pinned unless forced
                if meta.pinned and not force:
                    logger.warning(f"Skipping pinned experiment {run_id}")
                    results[run_id] = False
                    continue
                
                # Find and delete the run directory
                run_path = self._find_run_path(meta.project, meta.name, run_id)
                if run_path and run_path.exists():
                    shutil.rmtree(run_path)
                    logger.info(f"Deleted run directory: {run_path}")
                
                # Remove from metadata
                del self.metadata[run_id]
                results[run_id] = True
                
            except Exception as e:
                logger.error(f"Failed to delete {run_id}: {e}")
                results[run_id] = False
        
        self._save_metadata()
        return results
    
    def _find_run_path(self, project: str, name: str, run_id: str) -> Optional[Path]:
        """Find the path to a run directory."""
        # New layout: storage_root/project/name/runs/run_id
        run_path = self.storage_root / project / name / "runs" / run_id
        if run_path.exists():
            return run_path
        
        # Legacy layout: storage_root/runs/run_id
        legacy_path = self.storage_root / "runs" / run_id
        if legacy_path.exists():
            return legacy_path
        
        return None
    
    def cleanup_old_experiments(self, days: int = 30, dry_run: bool = True) -> List[str]:
        """
        Clean up experiments older than specified days.
        
        Args:
            days: Delete experiments older than this many days
            dry_run: If True, only return what would be deleted
            
        Returns:
            List of deleted (or to-be-deleted) run IDs
        """
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        to_delete = []
        
        for run_id, meta in self.metadata.items():
            # Skip pinned and already archived
            if meta.pinned or meta.archived:
                continue
            
            if meta.updated_at < cutoff_time:
                to_delete.append(run_id)
        
        if not dry_run and to_delete:
            self.delete_experiments(to_delete)
            logger.info(f"Cleaned up {len(to_delete)} old experiments")
        
        return to_delete
    
    def get_experiment_stats(self) -> Dict[str, Any]:
        """Get statistics about experiments."""
        total = len(self.metadata)
        if total == 0:
            return {
                "total": 0,
                "projects": [],
                "tags": []
            }
        
        projects = {}
        all_tags = set()
        archived_count = 0
        pinned_count = 0
        
        for meta in self.metadata.values():
            # Count by project
            if meta.project not in projects:
                projects[meta.project] = 0
            projects[meta.project] += 1
            
            # Collect tags
            all_tags.update(meta.tags)
            
            # Count special states
            if meta.archived:
                archived_count += 1
            if meta.pinned:
                pinned_count += 1
        
        return {
            "total": total,
            "archived": archived_count,
            "pinned": pinned_count,
            "projects": projects,
            "tags": sorted(list(all_tags)),
            "active": total - archived_count
        }
