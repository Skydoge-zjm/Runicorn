"""Runicorn Client

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
    HostKeyConfirmationRequiredError,
)

if TYPE_CHECKING:
    from .remote import RemoteAPI

logger = logging.getLogger(__name__)


class RunicornClient:
    """
    Client for programmatic access to Runicorn Viewer API.
    
    Example:
        >>> import runicorn.client as client_mod
        >>> client = client_mod.connect("http://localhost:23300")
        >>> runs = client.list_runs()
        >>> run = client.get_run(runs[0]["id"])
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
            if data.get("status") != "ok":
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
            elif resp.status_code == 409:
                try:
                    data = resp.json()
                    detail = data.get("detail", data)
                    if isinstance(detail, dict) and detail.get("code") == "HOST_KEY_CONFIRMATION_REQUIRED":
                        raise HostKeyConfirmationRequiredError(detail)
                except ValueError:
                    pass
                raise APIConnectionError(f"Conflict: {resp.text}")
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
    
    # ==================== Runs API ====================
    
    def list_runs(self) -> List[Dict[str, Any]]:
        """
        List all experiment runs.
        
        Returns:
            List of run records (each with id, status, path, alias, etc.)
        """
        return self.get("/api/runs")
    
    def get_run(self, run_id: str) -> Dict[str, Any]:
        """
        Get run details.
        
        Args:
            run_id: Run ID
            
        Returns:
            Run record
        """
        return self.get(f"/api/runs/{run_id}")
    
    # ==================== Paths API ====================
    
    def list_paths(self, include_stats: bool = False) -> Dict[str, Any]:
        """
        List all experiment paths.
        
        Args:
            include_stats: Include run count statistics per path
            
        Returns:
            Dictionary with paths list, tree structure, and optionally stats
        """
        params = {}
        if include_stats:
            params["include_stats"] = "true"
        return self.get("/api/paths", params=params)
    
    def list_runs_by_path(
        self,
        path: Optional[str] = None,
        exact: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        List runs filtered by path.
        
        Args:
            path: Path prefix to filter by (e.g., "cv/yolo")
            exact: If true, match exact path only
            
        Returns:
            List of runs matching the path filter
        """
        params = {}
        if path:
            params["path"] = path
        if exact:
            params["exact"] = "true"
        return self.get("/api/paths/runs", params=params)
    
    # ==================== Metrics API ====================
    
    def get_metrics(
        self,
        run_id: str,
        downsample: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get run metrics.
        
        Args:
            run_id: Run ID
            downsample: Target number of data points (100-50000, None = no downsampling)
            
        Returns:
            Dict with columns, rows, total, and sampled counts
        """
        params = {}
        if downsample is not None:
            params["downsample"] = downsample
        
        return self.get(f"/api/runs/{run_id}/metrics", params=params)
    
    # ==================== Export API ====================
    
    def export_csv(self, run_id: str) -> bytes:
        """
        Export run metrics as CSV.
        
        Args:
            run_id: Run ID
            
        Returns:
            CSV content (binary)
        """
        url = urljoin(self.base_url, f"/api/export/{run_id}/csv")
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.content
    
    def export_report(self, run_id: str, format: str = "markdown") -> bytes:
        """
        Generate experiment report.
        
        Args:
            run_id: Run ID
            format: Report format (markdown or html)
            
        Returns:
            Report content (binary)
        """
        url = urljoin(self.base_url, f"/api/export/{run_id}/report")
        resp = self.session.get(url, params={"format": format}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.content
    
    # ==================== Config API ====================
    
    def get_config(self) -> Dict[str, Any]:
        """Get Viewer configuration."""
        return self.get("/api/config")
    
    def set_user_root_dir(self, path: str) -> Dict[str, Any]:
        """
        Set user root directory for experiment storage.
        
        Args:
            path: New storage root directory path
            
        Returns:
            Updated config with new storage path
        """
        return self.post("/api/config/user_root_dir", json={"path": path})
    
    # ==================== GPU API ====================
    
    def get_gpu_info(self) -> Dict[str, Any]:
        """Get GPU telemetry data."""
        return self.get("/api/gpu/telemetry")
    
    # ==================== Health API ====================
    
    def health_check(self) -> Dict[str, Any]:
        """Check Viewer health status."""
        return self.get("/api/health")
    
    # ==================== Storage API ====================
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage usage statistics."""
        return self.get("/api/storage/stats")
    
    # ==================== Status API ====================
    
    def check_status(self) -> Dict[str, Any]:
        """Manually trigger status check for all running experiments."""
        return self.post("/api/status/check")
    
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
    def remote(self) -> "RemoteAPI":
        """Access Remote API."""
        if not hasattr(self, "_remote_api"):
            from .remote import RemoteAPI
            self._remote_api = RemoteAPI(self)
        return self._remote_api
