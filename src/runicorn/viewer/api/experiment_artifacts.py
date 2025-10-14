"""
Experiment-Artifacts Integration API

Provides endpoints for better integration between experiments and artifacts.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..services.storage import find_run_dir_by_id, read_json

logger = logging.getLogger(__name__)
router = APIRouter()


class ArtifactSummary(BaseModel):
    """Summary of an artifact for display in experiment context."""
    name: str
    type: str
    version: int
    size_bytes: int
    created_at: float
    description: Optional[str] = None
    aliases: List[str] = []
    lifecycle_stage: Optional[str] = None


class ExperimentArtifacts(BaseModel):
    """Artifacts related to an experiment."""
    created: List[ArtifactSummary]
    used: List[ArtifactSummary]


class TrainingMetrics(BaseModel):
    """Training metrics for an artifact."""
    run_id: str
    run_name: str
    project: str
    metrics: Dict[str, Any]
    created_at: float
    duration_seconds: Optional[float] = None
    status: str


@router.get("/runs/{run_id}/artifacts", response_model=ExperimentArtifacts)
async def get_run_artifacts(request: Request, run_id: str) -> ExperimentArtifacts:
    """
    Get all artifacts created and used by a run.
    
    Args:
        run_id: Run ID
        
    Returns:
        Artifacts created and used by the run
    """
    storage_root = request.app.state.storage_root
    
    # Find run directory
    run_entry = find_run_dir_by_id(storage_root, run_id)
    if not run_entry:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    
    run_dir = run_entry.dir
    
    # Read artifacts created
    created_artifacts = []
    artifacts_created_path = run_dir / "artifacts_created.json"
    
    logger.info(f"Looking for artifacts_created.json at: {artifacts_created_path}")
    logger.info(f"File exists: {artifacts_created_path.exists()}")
    
    if artifacts_created_path.exists():
        try:
            data = json.loads(artifacts_created_path.read_text(encoding="utf-8"))
            artifacts_list = data.get("artifacts", [])
            logger.info(f"Found {len(artifacts_list)} created artifacts in JSON")
            
            for artifact_info in artifacts_list:
                # Try to get more details from artifact storage
                artifact_summary = await _get_artifact_summary(
                    request, 
                    artifact_info["name"], 
                    artifact_info["type"],
                    artifact_info["version"]
                )
                if artifact_summary:
                    created_artifacts.append(artifact_summary)
                else:
                    # Fallback to basic info with defaults
                    created_artifacts.append(ArtifactSummary(
                        name=artifact_info.get("name", ""),
                        type=artifact_info.get("type", "custom"),
                        version=artifact_info.get("version", 1),
                        size_bytes=artifact_info.get("size_bytes", 0),
                        created_at=artifact_info.get("created_at", 0),
                        description=artifact_info.get("description"),
                        aliases=[],
                        lifecycle_stage=None
                    ))
        except Exception as e:
            logger.warning(f"Failed to read artifacts_created.json: {e}")
    
    # Read artifacts used
    used_artifacts = []
    artifacts_used_path = run_dir / "artifacts_used.json"
    
    logger.info(f"Looking for artifacts_used.json at: {artifacts_used_path}")
    logger.info(f"File exists: {artifacts_used_path.exists()}")
    
    if artifacts_used_path.exists():
        try:
            data = json.loads(artifacts_used_path.read_text(encoding="utf-8"))
            artifacts_list = data.get("artifacts", [])
            logger.info(f"Found {len(artifacts_list)} used artifacts in JSON")
            
            for artifact_info in artifacts_list:
                artifact_summary = await _get_artifact_summary(
                    request,
                    artifact_info["name"],
                    artifact_info["type"],
                    artifact_info["version"]
                )
                if artifact_summary:
                    used_artifacts.append(artifact_summary)
                else:
                    # Fallback to basic info with defaults
                    used_artifacts.append(ArtifactSummary(
                        name=artifact_info.get("name", ""),
                        type=artifact_info.get("type", "custom"),
                        version=artifact_info.get("version", 1),
                        size_bytes=artifact_info.get("size_bytes", 0),
                        created_at=artifact_info.get("created_at", 0),
                        description=artifact_info.get("description"),
                        aliases=[],
                        lifecycle_stage=None
                    ))
        except Exception as e:
            logger.warning(f"Failed to read artifacts_used.json: {e}")
    
    result = ExperimentArtifacts(
        created=created_artifacts,
        used=used_artifacts
    )
    
    logger.info(f"Returning {len(created_artifacts)} created and {len(used_artifacts)} used artifacts for run {run_id}")
    
    return result


@router.get("/artifacts/{name}/training-metrics", response_model=Optional[TrainingMetrics])
async def get_artifact_training_metrics(
    request: Request,
    name: str,
    version: Optional[int] = None,
    type: Optional[str] = None
) -> Optional[TrainingMetrics]:
    """
    Get training metrics for an artifact.
    
    Args:
        name: Artifact name
        version: Artifact version (defaults to latest)
        type: Artifact type hint
        
    Returns:
        Training metrics from the run that created this artifact
    """
    # Determine artifact type if not provided
    if not type:
        type = await _determine_artifact_type(request, name)
        if not type:
            raise HTTPException(status_code=404, detail=f"Artifact not found: {name}")
    
    # Get artifact metadata
    artifacts_root = Path(request.app.state.storage_root) / "artifacts"
    
    # If no version specified, find latest
    if version is None:
        version_dir = artifacts_root / type / name
        if not version_dir.exists():
            raise HTTPException(status_code=404, detail=f"Artifact not found: {name}")
        
        versions = [int(d.name[1:]) for d in version_dir.iterdir() if d.is_dir() and d.name.startswith("v")]
        if not versions:
            raise HTTPException(status_code=404, detail=f"No versions found for artifact: {name}")
        version = max(versions)
    
    # Read artifact metadata
    metadata_path = artifacts_root / type / name / f"v{version}" / "metadata.json"
    if not metadata_path.exists():
        return None
    
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        created_by_run = metadata.get("created_by_run")
        
        if not created_by_run:
            return None
        
        # Find run directory
        run_entry = find_run_dir_by_id(request.app.state.storage_root, created_by_run)
        if not run_entry:
            return None
        
        run_dir = run_entry.dir
        
        # Read run details
        meta = read_json(run_dir / "meta.json") or {}
        summary = read_json(run_dir / "summary.json") or {}
        status = read_json(run_dir / "status.json") or {}
        
        # Calculate duration
        duration = None
        if meta.get("start_time") and status.get("end_time"):
            duration = status["end_time"] - meta["start_time"]
        
        return TrainingMetrics(
            run_id=created_by_run,
            run_name=meta.get("name", "default"),
            project=meta.get("project", "default"),
            metrics=summary,
            created_at=meta.get("start_time", metadata.get("created_at", 0)),
            duration_seconds=duration,
            status=status.get("status", "unknown")
        )
        
    except Exception as e:
        logger.error(f"Failed to get training metrics for {name}:v{version}: {e}")
        return None


@router.get("/artifacts/{name}/performance-history")
async def get_artifact_performance_history(
    request: Request,
    name: str,
    type: Optional[str] = None,
    metric_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get performance history across all versions of an artifact.
    
    Args:
        name: Artifact name
        type: Artifact type hint
        metric_name: Specific metric to track (e.g., "accuracy")
        
    Returns:
        Performance metrics for each version
    """
    # Determine artifact type if not provided
    if not type:
        type = await _determine_artifact_type(request, name)
        if not type:
            raise HTTPException(status_code=404, detail=f"Artifact not found: {name}")
    
    artifacts_root = Path(request.app.state.storage_root) / "artifacts"
    version_dir = artifacts_root / type / name
    
    if not version_dir.exists():
        raise HTTPException(status_code=404, detail=f"Artifact not found: {name}")
    
    performance_history = []
    
    # Iterate through all versions
    for version_path in sorted(version_dir.iterdir()):
        if not version_path.is_dir() or not version_path.name.startswith("v"):
            continue
        
        try:
            version_num = int(version_path.name[1:])
            
            # Get training metrics for this version
            training_metrics = await get_artifact_training_metrics(
                request, name, version_num, type
            )
            
            if training_metrics:
                version_data = {
                    "version": version_num,
                    "created_at": training_metrics.created_at,
                    "run_id": training_metrics.run_id,
                    "status": training_metrics.status,
                    "metrics": {}
                }
                
                # Extract specific metric or all metrics
                if metric_name and metric_name in training_metrics.metrics:
                    version_data["metrics"][metric_name] = training_metrics.metrics[metric_name]
                else:
                    # Include all numeric metrics
                    for key, value in training_metrics.metrics.items():
                        if isinstance(value, (int, float)):
                            version_data["metrics"][key] = value
                
                performance_history.append(version_data)
                
        except Exception as e:
            logger.warning(f"Failed to get metrics for {name}:v{version_path.name}: {e}")
    
    return performance_history


async def _get_artifact_summary(
    request: Request,
    name: str,
    type: str,
    version: int
) -> Optional[ArtifactSummary]:
    """Get artifact summary with additional metadata."""
    try:
        artifacts_root = Path(request.app.state.storage_root) / "artifacts"
        metadata_path = artifacts_root / type / name / f"v{version}" / "metadata.json"
        
        if not metadata_path.exists():
            return None
        
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        
        # Get aliases
        aliases = metadata.get("aliases", [])
        
        # Get lifecycle stage (future enhancement)
        lifecycle_stage = metadata.get("lifecycle_stage", "experimental")
        
        return ArtifactSummary(
            name=name,
            type=type,
            version=version,
            size_bytes=metadata.get("size_bytes", 0),
            created_at=metadata.get("created_at", 0),
            description=metadata.get("description", ""),
            aliases=aliases,
            lifecycle_stage=lifecycle_stage
        )
        
    except Exception as e:
        logger.warning(f"Failed to get artifact summary for {name}:v{version}: {e}")
        return None


async def _determine_artifact_type(request: Request, name: str) -> Optional[str]:
    """Determine artifact type by searching."""
    artifacts_root = Path(request.app.state.storage_root) / "artifacts"
    
    for type_name in ["model", "dataset", "config", "code", "custom"]:
        if (artifacts_root / type_name / name).exists():
            return type_name
    
    return None
