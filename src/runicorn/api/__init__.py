"""
Runicorn API Client

Programmatic access to Runicorn Viewer REST API.

Example:
    >>> import runicorn.api as api
    >>> 
    >>> # Connect to Viewer
    >>> client = api.connect()
    >>> 
    >>> # List experiments
    >>> experiments = client.list_experiments(project="vision")
    >>> 
    >>> # Get run details
    >>> run = client.get_run(experiments[0]["id"])
    >>> print(f"Run: {run['name']}, Status: {run['status']}")
    >>> 
    >>> # Get metrics
    >>> metrics = client.get_metrics(run["id"])
    >>> 
    >>> # Remote viewer
    >>> client.remote.connect(host="localhost", username="user")
    >>> session = client.remote.start_viewer(
    ...     connection_id="localhost",
    ...     remote_root="/data"
    ... )
    >>> print(f"Access viewer at: {session['local_url']}")
"""
from __future__ import annotations

from .client import RunicornClient
from .exceptions import (
    RunicornAPIError,
    ConnectionError,
    NotFoundError,
    BadRequestError,
    ServerError,
    AuthenticationError,
)
from .models import (
    Experiment,
    MetricPoint,
    MetricSeries,
    RemoteSession,
    Project,
)

__all__ = [
    # Client
    "RunicornClient",
    "connect",
    # Exceptions
    "RunicornAPIError",
    "ConnectionError",
    "NotFoundError",
    "BadRequestError",
    "ServerError",
    "AuthenticationError",
    # Models
    "Experiment",
    "MetricPoint",
    "MetricSeries",
    "RemoteSession",
    "Project",
]


def connect(
    base_url: str = "http://127.0.0.1:23300",
    timeout: int = 30,
    max_retries: int = 3,
) -> RunicornClient:
    """
    Connect to Runicorn Viewer.
    
    Args:
        base_url: Viewer base URL (default: http://127.0.0.1:23300)
        timeout: Request timeout in seconds (default: 30)
        max_retries: Maximum retry attempts (default: 3)
        
    Returns:
        RunicornClient instance
        
    Example:
        >>> import runicorn.api as api
        >>> client = api.connect()
        >>> experiments = client.list_experiments()
    """
    return RunicornClient(
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
    )
