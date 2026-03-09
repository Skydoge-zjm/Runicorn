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


class HostKeyConfirmationRequiredError(RunicornAPIError):
    """
    Raised when connecting to a new SSH host and host key verification is required.
    
    The server returns 409 with HOST_KEY_CONFIRMATION_REQUIRED. Call
    client.remote.confirm_host_key() with the host_key details, then retry
    the original operation.
    
    Attributes:
        detail: Full 409 response detail (dict with code, message, host_key)
        host_key: Parsed host_key dict (host, port, key_type, public_key, fingerprint_sha256, etc.)
    """
    def __init__(self, detail: dict, message: str | None = None):
        self.detail = detail
        self.host_key = detail.get("host_key", {}) if isinstance(detail, dict) else {}
        msg = message or (detail.get("message", "Host key confirmation required") if isinstance(detail, dict) else "Host key confirmation required")
        super().__init__(msg)
