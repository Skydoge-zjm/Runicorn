"""
Runicorn Client

Programmatic access to Runicorn Viewer REST API.

Example:
    >>> import runicorn.client as client
    >>> 
    >>> # Connect to Viewer
    >>> c = client.connect()
    >>> 
    >>> # List runs
    >>> runs = c.list_runs()
    >>> 
    >>> # Get run details
    >>> run = c.get_run(runs[0]["id"])
    >>> print(f"Run: {run['path']}, Status: {run['status']}")
    >>> 
    >>> # Get metrics
    >>> metrics = c.get_metrics(run["id"])
    >>> 
    >>> # Remote viewer
    >>> c.remote.connect(host="localhost", username="user")
    >>> session = c.remote.start_viewer(
    ...     host="localhost",
    ...     username="user",
    ...     remote_root="/data"
    ... )
    >>> print(f"Access viewer at: {session['local_url']}")
"""
from __future__ import annotations

from .http import RunicornClient
from .exceptions import (
    RunicornAPIError,
    ConnectionError,
    NotFoundError,
    BadRequestError,
    ServerError,
    AuthenticationError,
    HostKeyConfirmationRequiredError,
)
from .models import (
    RunInfo,
    Experiment,  # backward compat alias
    MetricPoint,
    MetricSeries,
    RemoteSession,
    PathInfo,
    Project,  # backward compat alias
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
    "HostKeyConfirmationRequiredError",
    # Models
    "RunInfo",
    "Experiment",
    "MetricPoint",
    "MetricSeries",
    "RemoteSession",
    "PathInfo",
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
        >>> import runicorn.client as client
        >>> c = client.connect()
        >>> runs = c.list_runs()
    """
    return RunicornClient(
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
    )
