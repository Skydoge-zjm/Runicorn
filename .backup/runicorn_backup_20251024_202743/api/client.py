"""
Runicorn API Client

Provides programmatic access to Runicorn Viewer REST API.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import (
    ConnectionError as APIConnectionError,
    NotFoundError,
    BadRequestError,
    ServerError,
)

if TYPE_CHECKING:
    from .artifacts import ArtifactsAPI
    from .remote import RemoteAPI

logger = logging.getLogger(__name__)


class RunicornClient:
    """
    Client for programmatic access to Runicorn Viewer API.
    
    Example:
        >>> import runicorn.api as api
        >>> client = api.connect("http://localhost:23300")
        >>> experiments = client.list_experiments()
        >>> run = client.get_run(experiments[0]["id"])
    """
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:23300",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize Runicorn API client.
        
        Args:
            base_url: Viewer base URL (default: http://127.0.0.1:23300)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum retry attempts (default: 3)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        
        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Verify connection
        self._verify_connection()
    
    def _verify_connection(self) -> None:
        """Verify connection to Viewer."""
        try:
            resp = self.session.get(
                urljoin(self.base_url, "/api/health"),
                timeout=5
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "healthy":
                raise APIConnectionError(f"Viewer is not healthy: {data}")
            logger.info(f"Connected to Runicorn Viewer at {self.base_url}")
        except requests.RequestException as e:
            raise APIConnectionError(
                f"Failed to connect to Runicorn Viewer at {self.base_url}: {e}"
            ) from e
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request to API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/api/experiments")
            params: Query parameters
            json: JSON body
            **kwargs: Additional requests parameters
            
        Returns:
            Response JSON data
            
        Raises:
            NotFoundError: 404 error
            BadRequestError: 400 error
            ServerError: 500+ error
            APIConnectionError: Connection failed
        """
        url = urljoin(self.base_url, endpoint)
        
        try:
            resp = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                timeout=self.timeout,
                **kwargs
            )
            
            # Handle errors
            if resp.status_code == 404:
                raise NotFoundError(f"Resource not found: {endpoint}")
            elif resp.status_code == 400:
                raise BadRequestError(f"Bad request: {resp.text}")
            elif resp.status_code >= 500:
                raise ServerError(f"Server error: {resp.text}")
            
            resp.raise_for_status()
            return resp.json()
            
        except requests.RequestException as e:
            if isinstance(e, (NotFoundError, BadRequestError, ServerError)):
                raise
            raise APIConnectionError(f"Request failed: {e}") from e
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET request."""
        return self._request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, json: Optional[Dict] = None) -> Dict[str, Any]:
        """POST request."""
        return self._request("POST", endpoint, json=json)
    
    def put(self, endpoint: str, json: Optional[Dict] = None) -> Dict[str, Any]:
        """PUT request."""
        return self._request("PUT", endpoint, json=json)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request."""
        return self._request("DELETE", endpoint)
    
    # ==================== Experiments API ====================
    
    def list_experiments(
        self,
        project: Optional[str] = None,
        name: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List experiments.
        
        Args:
            project: Filter by project name
            name: Filter by experiment name
            status: Filter by status (running, finished, failed)
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of experiment records
        """
        params = {}
        if project:
            params["project"] = project
        if name:
            params["name"] = name
        if status:
            params["status"] = status
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset
        
        data = self.get("/api/experiments", params=params)
        return data.get("experiments", [])
    
    def get_experiment(self, run_id: str) -> Dict[str, Any]:
        """
        Get experiment details.
        
        Args:
            run_id: Run ID
            
        Returns:
            Experiment record
        """
        return self.get(f"/api/runs/{run_id}")
    
    # ==================== Runs API ====================
    
    def get_run(self, run_id: str) -> Dict[str, Any]:
        """Get run details (alias for get_experiment)."""
        return self.get_experiment(run_id)
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """
        List all projects.
        
        Returns:
            List of projects with experiment counts
        """
        data = self.get("/api/projects")
        return data.get("projects", [])
    
    # ==================== Metrics API ====================
    
    def get_metrics(
        self,
        run_id: str,
        metric_names: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get run metrics.
        
        Args:
            run_id: Run ID
            metric_names: Filter by metric names
            limit: Maximum number of data points
            
        Returns:
            Metrics data with time series
        """
        params = {}
        if metric_names:
            params["metrics"] = ",".join(metric_names)
        if limit:
            params["limit"] = limit
        
        return self.get(f"/api/metrics/{run_id}", params=params)
    
    # ==================== Export API ====================
    
    def export_experiment(
        self,
        run_id: str,
        format: str = "json",
        include_media: bool = False,
    ) -> bytes:
        """
        Export experiment data.
        
        Args:
            run_id: Run ID
            format: Export format (json, csv)
            include_media: Include media files
            
        Returns:
            Exported data (binary)
        """
        payload = {
            "run_id": run_id,
            "format": format,
            "include_media": include_media,
        }
        
        # This returns raw bytes, not JSON
        url = urljoin(self.base_url, "/api/export")
        resp = self.session.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.content
    
    # ==================== Config API ====================
    
    def get_config(self) -> Dict[str, Any]:
        """Get Viewer configuration."""
        return self.get("/api/config")
    
    def update_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update Viewer configuration."""
        return self.put("/api/config", json=config)
    
    # ==================== GPU API ====================
    
    def get_gpu_info(self) -> Dict[str, Any]:
        """Get GPU information."""
        return self.get("/api/gpu")
    
    # ==================== Health API ====================
    
    def health_check(self) -> Dict[str, Any]:
        """Check Viewer health status."""
        return self.get("/api/health")
    
    def close(self) -> None:
        """Close client session."""
        self.session.close()
        logger.info("Closed Runicorn API client")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    # ==================== Extended API Properties ====================
    
    @property
    def artifacts(self) -> "ArtifactsAPI":
        """Access Artifacts API."""
        if not hasattr(self, "_artifacts_api"):
            from .artifacts import ArtifactsAPI
            self._artifacts_api = ArtifactsAPI(self)
        return self._artifacts_api
    
    @property
    def remote(self) -> "RemoteAPI":
        """Access Remote API."""
        if not hasattr(self, "_remote_api"):
            from .remote import RemoteAPI
            self._remote_api = RemoteAPI(self)
        return self._remote_api
