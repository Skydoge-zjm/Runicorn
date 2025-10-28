"""
Runicorn API Client Exceptions
"""
from __future__ import annotations


class RunicornAPIError(Exception):
    """Base exception for Runicorn API errors."""
    pass


class ConnectionError(RunicornAPIError):
    """Failed to connect to Runicorn Viewer."""
    pass


class NotFoundError(RunicornAPIError):
    """Resource not found."""
    pass


class BadRequestError(RunicornAPIError):
    """Invalid request parameters."""
    pass


class ServerError(RunicornAPIError):
    """Server-side error."""
    pass


class AuthenticationError(RunicornAPIError):
    """Authentication failed (for remote connections)."""
    pass
