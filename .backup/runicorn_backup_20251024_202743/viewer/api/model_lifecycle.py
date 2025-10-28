"""
Model Lifecycle Management API

Provides endpoints for managing model lifecycle stages and promotion workflow.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Body
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


class PromoteModelRequest(BaseModel):
    """Request to promote a model to a different stage."""
    to_stage: str = Field(..., description="Target lifecycle stage")
    notes: Optional[str] = Field(None, description="Promotion notes")
    evaluator_run_id: Optional[str] = Field(None, description="Run ID that evaluated the model")


class ModelEvaluation(BaseModel):
    """Model evaluation record."""
    model_name: str
    model_version: int
    evaluation_date: float
    evaluator_run_id: Optional[str] = None
    metrics: Dict[str, float]
    test_dataset: Optional[str] = None
    status: str  # passed/failed/pending
    notes: Optional[str] = None


class LifecycleTransition(BaseModel):
    """Record of a lifecycle stage transition."""
    from_stage: str
    to_stage: str
    timestamp: float
    user: Optional[str] = None
    notes: Optional[str] = None
    evaluator_run_id: Optional[str] = None


# Valid lifecycle stages and transitions
LIFECYCLE_STAGES = ["experimental", "staging", "production", "archived"]
VALID_TRANSITIONS = {
    "experimental": ["staging", "archived"],
    "staging": ["production", "experimental", "archived"],
    "production": ["staging", "archived"],
    "archived": ["experimental"]  # Allow restoring from archive
}


@router.post("/artifacts/{name}/v{version}/promote")
async def promote_model(
    request: Request,
    name: str,
    version: int,
    payload: PromoteModelRequest
) -> Dict[str, Any]:
    """
    Promote a model to a different lifecycle stage.
    
    Args:
        name: Model name
        version: Model version
        payload: Promotion details
        
    Returns:
        Success response with updated lifecycle stage
    """
    # Validate target stage
    if payload.to_stage not in LIFECYCLE_STAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid target stage: {payload.to_stage}. Must be one of {LIFECYCLE_STAGES}"
        )
    
    # Find artifact
    storage_root = Path(request.app.state.storage_root)
    artifacts_root = storage_root / "artifacts"
    
    # Determine type (assuming model for now, could be made more flexible)
    artifact_type = "model"
    artifact_dir = artifacts_root / artifact_type / name / f"v{version}"
    
    if not artifact_dir.exists():
        # Try other types
        for type_name in ["dataset", "config", "code", "custom"]:
            test_dir = artifacts_root / type_name / name / f"v{version}"
            if test_dir.exists():
                artifact_type = type_name
                artifact_dir = test_dir
                break
        
        if not artifact_dir.exists():
            raise HTTPException(status_code=404, detail=f"Artifact not found: {name}:v{version}")
    
    # Read current metadata
    metadata_path = artifact_dir / "metadata.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="Artifact metadata not found")
    
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        
        # Get current stage
        current_stage = metadata.get("lifecycle_stage", "experimental")
        
        # Validate transition
        if current_stage not in VALID_TRANSITIONS:
            current_stage = "experimental"  # Default if invalid
        
        if payload.to_stage not in VALID_TRANSITIONS.get(current_stage, []):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transition from {current_stage} to {payload.to_stage}"
            )
        
        # Update lifecycle stage
        metadata["lifecycle_stage"] = payload.to_stage
        metadata["lifecycle_updated_at"] = time.time()
        
        # Add transition record
        if "stage_transitions" not in metadata:
            metadata["stage_transitions"] = []
        
        metadata["stage_transitions"].append({
            "from_stage": current_stage,
            "to_stage": payload.to_stage,
            "timestamp": time.time(),
            "notes": payload.notes,
            "evaluator_run_id": payload.evaluator_run_id
        })
        
        # Handle special stage actions
        if payload.to_stage == "production":
            # Set "production" alias
            if "aliases" not in metadata:
                metadata["aliases"] = []
            if "production" not in metadata["aliases"]:
                metadata["aliases"].append("production")
            
            # Remove "production" alias from other versions
            _remove_alias_from_other_versions(
                artifacts_root / artifact_type / name,
                version,
                "production"
            )
        
        elif current_stage == "production" and payload.to_stage != "production":
            # Remove "production" alias when demoting
            if "aliases" in metadata and "production" in metadata["aliases"]:
                metadata["aliases"].remove("production")
        
        # Save updated metadata
        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        logger.info(f"Promoted {name}:v{version} from {current_stage} to {payload.to_stage}")
        
        return {
            "ok": True,
            "artifact": f"{name}:v{version}",
            "from_stage": current_stage,
            "to_stage": payload.to_stage,
            "message": f"Successfully promoted to {payload.to_stage}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to promote {name}:v{version}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/artifacts/{name}/v{version}/evaluate")
async def evaluate_model(
    request: Request,
    name: str,
    version: int,
    payload: ModelEvaluation
) -> Dict[str, Any]:
    """
    Record evaluation results for a model.
    
    Args:
        name: Model name
        version: Model version
        payload: Evaluation details
        
    Returns:
        Success response
    """
    # Find artifact
    storage_root = Path(request.app.state.storage_root)
    evaluations_dir = storage_root / "evaluations"
    evaluations_dir.mkdir(parents=True, exist_ok=True)
    
    # Create evaluation file
    eval_id = f"{name}_v{version}_{int(time.time() * 1000)}"
    eval_file = evaluations_dir / f"{eval_id}.json"
    
    evaluation_data = {
        "id": eval_id,
        "model_name": name,
        "model_version": version,
        "evaluation_date": time.time(),
        "evaluator_run_id": payload.evaluator_run_id,
        "metrics": payload.metrics,
        "test_dataset": payload.test_dataset,
        "status": payload.status,
        "notes": payload.notes
    }
    
    try:
        eval_file.write_text(
            json.dumps(evaluation_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        # Also update artifact metadata with latest evaluation
        artifacts_root = storage_root / "artifacts"
        
        # Find artifact type
        artifact_dir = None
        for type_name in ["model", "dataset", "config", "code", "custom"]:
            test_dir = artifacts_root / type_name / name / f"v{version}"
            if test_dir.exists():
                artifact_dir = test_dir
                break
        
        if artifact_dir:
            metadata_path = artifact_dir / "metadata.json"
            if metadata_path.exists():
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                
                # Add evaluation reference
                if "evaluations" not in metadata:
                    metadata["evaluations"] = []
                
                metadata["evaluations"].append({
                    "eval_id": eval_id,
                    "date": evaluation_data["evaluation_date"],
                    "status": payload.status,
                    "metrics_summary": {
                        k: v for k, v in list(payload.metrics.items())[:5]  # Top 5 metrics
                    }
                })
                
                # Keep only last 10 evaluations
                metadata["evaluations"] = metadata["evaluations"][-10:]
                
                metadata_path.write_text(
                    json.dumps(metadata, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
        
        logger.info(f"Recorded evaluation {eval_id} for {name}:v{version}")
        
        return {
            "ok": True,
            "eval_id": eval_id,
            "message": "Evaluation recorded successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to record evaluation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifacts/{name}/evaluations")
async def get_model_evaluations(
    request: Request,
    name: str,
    version: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get evaluation history for a model.
    
    Args:
        name: Model name
        version: Optional specific version
        
    Returns:
        List of evaluation records
    """
    storage_root = Path(request.app.state.storage_root)
    evaluations_dir = storage_root / "evaluations"
    
    if not evaluations_dir.exists():
        return []
    
    evaluations = []
    
    try:
        # Read all evaluation files for this model
        for eval_file in evaluations_dir.glob(f"{name}_*.json"):
            try:
                data = json.loads(eval_file.read_text(encoding="utf-8"))
                
                # Filter by version if specified
                if version is not None and data.get("model_version") != version:
                    continue
                
                evaluations.append(data)
                
            except Exception as e:
                logger.warning(f"Failed to read evaluation file {eval_file}: {e}")
        
        # Sort by date, newest first
        evaluations.sort(key=lambda x: x.get("evaluation_date", 0), reverse=True)
        
        return evaluations
        
    except Exception as e:
        logger.error(f"Failed to get evaluations for {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _remove_alias_from_other_versions(
    artifact_base_dir: Path,
    current_version: int,
    alias: str
) -> None:
    """Remove an alias from all other versions of an artifact."""
    try:
        for version_dir in artifact_base_dir.iterdir():
            if not version_dir.is_dir() or not version_dir.name.startswith("v"):
                continue
            
            version_num = int(version_dir.name[1:])
            if version_num == current_version:
                continue
            
            metadata_path = version_dir / "metadata.json"
            if metadata_path.exists():
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                
                if "aliases" in metadata and alias in metadata["aliases"]:
                    metadata["aliases"].remove(alias)
                    
                    metadata_path.write_text(
                        json.dumps(metadata, indent=2, ensure_ascii=False),
                        encoding="utf-8"
                    )
                    
                    logger.info(f"Removed alias '{alias}' from v{version_num}")
                    
    except Exception as e:
        logger.warning(f"Failed to remove alias from other versions: {e}")
