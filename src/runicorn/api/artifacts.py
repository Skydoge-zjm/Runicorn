"""
Artifacts API Extension for RunicornClient
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import RunicornClient


class ArtifactsAPI:
    """Artifacts API methods."""
    
    def __init__(self, client: RunicornClient):
        self.client = client
    
    def list_artifacts(
        self,
        type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all artifacts.
        
        Args:
            type: Filter by artifact type (model, dataset, config, code)
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of artifacts
        """
        params = {}
        if type:
            params["type"] = type
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset
        
        data = self.client.get("/api/artifacts", params=params)
        return data.get("artifacts", [])
    
    def get_artifact(self, artifact_id: str) -> Dict[str, Any]:
        """
        Get artifact details.
        
        Args:
            artifact_id: Artifact ID (name:version)
            
        Returns:
            Artifact record
        """
        return self.client.get(f"/api/artifacts/{artifact_id}")
    
    def list_versions(self, artifact_name: str) -> List[Dict[str, Any]]:
        """
        List all versions of an artifact.
        
        Args:
            artifact_name: Artifact name
            
        Returns:
            List of versions
        """
        data = self.client.get(f"/api/artifacts/{artifact_name}/versions")
        return data.get("versions", [])
    
    def download_artifact(self, artifact_id: str, output_path: str) -> str:
        """
        Download artifact files.
        
        Args:
            artifact_id: Artifact ID (name:version)
            output_path: Local path to save files
            
        Returns:
            Path to downloaded files
        """
        # TODO: Implement file download
        raise NotImplementedError("Download not yet implemented in API client")
    
    def get_artifact_lineage(self, artifact_id: str) -> Dict[str, Any]:
        """
        Get artifact lineage (dependencies and usage).
        
        Args:
            artifact_id: Artifact ID
            
        Returns:
            Lineage graph
        """
        data = self.client.get(f"/api/artifacts/{artifact_id}/lineage")
        return data
    
    def list_experiment_artifacts(
        self,
        run_id: str,
        relation: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List artifacts related to an experiment.
        
        Args:
            run_id: Experiment run ID
            relation: Filter by relation (created, used)
            
        Returns:
            List of artifacts
        """
        params = {}
        if relation:
            params["relation"] = relation
        
        data = self.client.get(
            f"/api/experiments/{run_id}/artifacts",
            params=params
        )
        return data.get("artifacts", [])
