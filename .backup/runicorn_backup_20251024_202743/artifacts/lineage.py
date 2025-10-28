"""
Artifact Lineage Tracking

Tracks dependencies between artifacts and runs to build lineage graphs.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .models import LineageGraph, LineageNode, LineageEdge

logger = logging.getLogger(__name__)


class LineageTracker:
    """
    Tracks and builds artifact lineage graphs.
    
    Lineage shows the complete history of how artifacts were created and used:
    - Which artifacts were used to create this artifact
    - Which runs used this artifact
    - Complete dependency chain
    """
    
    def __init__(self, storage_root: Path):
        """
        Initialize lineage tracker.
        
        Args:
            storage_root: Storage root directory
        """
        self.storage_root = Path(storage_root)
        self.artifacts_root = self.storage_root / "artifacts"
    
    def build_lineage_graph(
        self,
        artifact_name: str,
        artifact_type: str,
        version: int,
        max_depth: int = 3
    ) -> LineageGraph:
        """
        Build complete lineage graph for an artifact.
        
        Args:
            artifact_name: Name of the artifact
            artifact_type: Type of the artifact
            version: Version number
            max_depth: Maximum depth to traverse (default: 3, max: 10)
            
        Returns:
            LineageGraph with all dependencies
        """
        # Limit max_depth to prevent excessive traversal
        max_depth = min(max_depth, 10)
        
        root_id = f"{artifact_name}:v{version}"
        graph = LineageGraph(root_artifact=root_id)
        
        # Track visited nodes to prevent cycles
        visited_artifacts = set()
        visited_runs = set()
        
        # Add root artifact node
        try:
            root_metadata = self._load_artifact_metadata(artifact_name, artifact_type, version)
            root_node = LineageNode(
                node_type="artifact",
                node_id=root_id,
                label=f"{artifact_name} v{version}",
                metadata={
                    "type": artifact_type,
                    "size": root_metadata.get("size_bytes", 0),
                    "created_at": root_metadata.get("created_at"),
                }
            )
            graph.add_node(root_node)
        except Exception as e:
            logger.error(f"Failed to load root artifact {root_id}: {e}")
            return graph  # Return empty graph rather than fail
        
        # Traverse upstream (what was used to create this)
        self._traverse_upstream(
            graph, artifact_name, artifact_type, version, 
            depth=0, max_depth=max_depth,
            visited_artifacts=visited_artifacts,
            visited_runs=visited_runs
        )
        
        # Traverse downstream (what uses this)
        self._traverse_downstream(
            graph, artifact_name, artifact_type, version, 
            depth=0, max_depth=max_depth,
            visited_artifacts=visited_artifacts,
            visited_runs=visited_runs
        )
        
        return graph
    
    def _traverse_upstream(
        self,
        graph: LineageGraph,
        artifact_name: str,
        artifact_type: str,
        version: int,
        depth: int,
        max_depth: int,
        visited_artifacts: set,
        visited_runs: set
    ) -> None:
        """Traverse upstream dependencies (inputs) with cycle detection."""
        if depth >= max_depth:
            return
        
        # Prevent cycles: check if artifact already visited
        artifact_id = f"{artifact_name}:v{version}"
        if artifact_id in visited_artifacts:
            logger.debug(f"Cycle detected or already visited: {artifact_id}")
            return
        visited_artifacts.add(artifact_id)
        
        # Load metadata
        try:
            metadata = self._load_artifact_metadata(artifact_name, artifact_type, version)
        except Exception as e:
            logger.debug(f"Failed to load metadata for {artifact_id}: {e}")
            return
        
        run_id = metadata.get("created_by_run")
        
        if not run_id:
            return
        
        # Prevent cycles: check if run already visited
        if run_id in visited_runs:
            logger.debug(f"Cycle detected or already visited: run {run_id}")
            return
        visited_runs.add(run_id)
        
        # Add run node
        run_node_id = f"run:{run_id}"
        run_node = LineageNode(
            node_type="run",
            node_id=run_node_id,
            label=f"Run {run_id[:16]}...",
            metadata={"run_id": run_id}
        )
        graph.add_node(run_node)
        
        # Add edge: run → artifact
        graph.add_edge(LineageEdge(
            source=run_node_id,
            target=f"{artifact_name}:v{version}",
            edge_type="produces"
        ))
        
        # Find artifacts used by this run
        used_artifacts = self._get_artifacts_used_by_run(run_id)
        
        for used_artifact in used_artifacts:
            used_name = used_artifact["name"]
            used_type = used_artifact["type"]
            used_version = used_artifact["version"]
            used_id = f"{used_name}:v{used_version}"
            
            # Add artifact node
            try:
                used_metadata = self._load_artifact_metadata(used_name, used_type, used_version)
                used_node = LineageNode(
                    node_type="artifact",
                    node_id=used_id,
                    label=f"{used_name} v{used_version}",
                    metadata={
                        "type": used_type,
                        "size": used_metadata.get("size_bytes", 0)
                    }
                )
                graph.add_node(used_node)
                
                # Add edge: artifact → run
                graph.add_edge(LineageEdge(
                    source=used_id,
                    target=run_node_id,
                    edge_type="uses"
                ))
                
                # Recursively traverse (with visited tracking)
                self._traverse_upstream(
                    graph, used_name, used_type, used_version, 
                    depth + 1, max_depth,
                    visited_artifacts, visited_runs
                )
                
            except Exception as e:
                logger.debug(f"Failed to load used artifact {used_id}: {e}")
    
    def _traverse_downstream(
        self,
        graph: LineageGraph,
        artifact_name: str,
        artifact_type: str,
        version: int,
        depth: int,
        max_depth: int,
        visited_artifacts: set,
        visited_runs: set
    ) -> None:
        """Traverse downstream dependencies (consumers) with cycle detection."""
        if depth >= max_depth:
            return
        
        # Prevent cycles
        artifact_id = f"{artifact_name}:v{version}"
        if artifact_id in visited_artifacts:
            return
        # Note: artifact may already be in visited from upstream, but we still want downstream
        # So we don't add to visited here, let downstream add if needed
        
        # Find runs that used this artifact
        using_runs = self._find_runs_using_artifact(artifact_name, version)
        
        for run_id in using_runs:
            # Prevent cycles
            if run_id in visited_runs:
                continue
            visited_runs.add(run_id)
            
            run_node_id = f"run:{run_id}"
            
            # Add run node
            run_node = LineageNode(
                node_type="run",
                node_id=run_node_id,
                label=f"Run {run_id[:16]}...",
                metadata={"run_id": run_id}
            )
            graph.add_node(run_node)
            
            # Add edge: artifact → run
            graph.add_edge(LineageEdge(
                source=f"{artifact_name}:v{version}",
                target=run_node_id,
                edge_type="uses"
            ))
            
            # Find artifacts created by this run
            created_artifacts = self._get_artifacts_created_by_run(run_id)
            
            for created_artifact in created_artifacts:
                created_name = created_artifact["name"]
                created_type = created_artifact["type"]
                created_version = created_artifact["version"]
                created_id = f"{created_name}:v{created_version}"
                
                # Add artifact node
                try:
                    created_metadata = self._load_artifact_metadata(created_name, created_type, created_version)
                    created_node = LineageNode(
                        node_type="artifact",
                        node_id=created_id,
                        label=f"{created_name} v{created_version}",
                        metadata={
                            "type": created_type,
                            "size": created_metadata.get("size_bytes", 0)
                        }
                    )
                    graph.add_node(created_node)
                    
                    # Add edge: run → artifact
                    graph.add_edge(LineageEdge(
                        source=run_node_id,
                        target=created_id,
                        edge_type="produces"
                    ))
                    
                    # Recursively traverse (with visited tracking)
                    self._traverse_downstream(
                        graph, created_name, created_type, created_version, 
                        depth + 1, max_depth,
                        visited_artifacts, visited_runs
                    )
                    
                except Exception as e:
                    logger.debug(f"Failed to load created artifact {created_id}: {e}")
    
    def _load_artifact_metadata(self, name: str, type: str, version: int) -> Dict[str, Any]:
        """Load artifact metadata."""
        metadata_path = self.artifacts_root / type / name / f"v{version}" / "metadata.json"
        
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata not found for {name}:v{version}")
        
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    
    def _get_artifacts_used_by_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Get list of artifacts used by a run."""
        # Find run directory
        run_dir = self._find_run_dir(run_id)
        
        if not run_dir:
            return []
        
        artifacts_used_path = run_dir / "artifacts_used.json"
        
        if not artifacts_used_path.exists():
            return []
        
        try:
            data = json.loads(artifacts_used_path.read_text(encoding="utf-8"))
            return data.get("artifacts", [])
        except Exception as e:
            logger.warning(f"Failed to load artifacts_used.json for run {run_id}: {e}")
            return []
    
    def _get_artifacts_created_by_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Get list of artifacts created by a run."""
        run_dir = self._find_run_dir(run_id)
        
        if not run_dir:
            return []
        
        artifacts_created_path = run_dir / "artifacts_created.json"
        
        if not artifacts_created_path.exists():
            return []
        
        try:
            data = json.loads(artifacts_created_path.read_text(encoding="utf-8"))
            return data.get("artifacts", [])
        except Exception as e:
            logger.warning(f"Failed to load artifacts_created.json for run {run_id}: {e}")
            return []
    
    def _find_runs_using_artifact(self, artifact_name: str, version: int, max_results: int = 100) -> List[str]:
        """
        Find runs that used this artifact.
        
        Performance note: This is O(n) where n = total runs.
        For large deployments, consider building an index.
        
        Args:
            artifact_name: Artifact name
            version: Version number
            max_results: Maximum number of results to return (for performance)
            
        Returns:
            List of run IDs (limited to max_results)
        """
        using_runs = []
        checked_count = 0
        max_check = 10000  # Safety limit: don't check more than 10k runs
        
        # Search through all runs
        for project_dir in self.storage_root.iterdir():
            if not project_dir.is_dir() or project_dir.name in {"artifacts", "sweeps", "runs"}:
                continue
            
            for exp_dir in project_dir.iterdir():
                if not exp_dir.is_dir():
                    continue
                
                runs_dir = exp_dir / "runs"
                if not runs_dir.exists():
                    continue
                
                for run_dir in runs_dir.iterdir():
                    if not run_dir.is_dir():
                        continue
                    
                    checked_count += 1
                    
                    # Safety: stop if checked too many runs
                    if checked_count > max_check:
                        logger.warning(f"Lineage search stopped after checking {max_check} runs")
                        return using_runs
                    
                    # Early exit if found enough
                    if len(using_runs) >= max_results:
                        logger.debug(f"Lineage search stopped after finding {max_results} using runs")
                        return using_runs
                    
                    artifacts_used_path = run_dir / "artifacts_used.json"
                    if artifacts_used_path.exists():
                        try:
                            data = json.loads(artifacts_used_path.read_text(encoding="utf-8"))
                            for artifact in data.get("artifacts", []):
                                if artifact["name"] == artifact_name and artifact["version"] == version:
                                    using_runs.append(run_dir.name)
                                    break  # Found in this run, move to next
                        except Exception as e:
                            logger.debug(f"Failed to read artifacts_used.json in {run_dir.name}: {e}")
        
        logger.debug(f"Checked {checked_count} runs, found {len(using_runs)} using {artifact_name}:v{version}")
        return using_runs
    
    def _find_run_dir(self, run_id: str) -> Optional[Path]:
        """Find run directory by ID."""
        # Search through all projects
        for project_dir in self.storage_root.iterdir():
            if not project_dir.is_dir() or project_dir.name in {"artifacts", "sweeps", "runs"}:
                continue
            
            for exp_dir in project_dir.iterdir():
                if not exp_dir.is_dir():
                    continue
                
                runs_dir = exp_dir / "runs"
                if not runs_dir.exists():
                    continue
                
                run_dir = runs_dir / run_id
                if run_dir.exists():
                    return run_dir
        
        # Try legacy layout
        legacy_runs = self.storage_root / "runs"
        if legacy_runs.exists():
            run_dir = legacy_runs / run_id
            if run_dir.exists():
                return run_dir
        
        return None
