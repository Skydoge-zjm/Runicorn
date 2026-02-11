from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

HostKeyVerificationReason = Literal["unknown", "changed"]


@dataclass(frozen=True)
class HostKeyProblem:
    """A normalized representation of an SSH host key verification problem."""

    host: str
    port: int
    known_hosts_host: str
    key_type: str
    fingerprint_sha256: str
    public_key: str
    reason: HostKeyVerificationReason
    expected_fingerprint_sha256: Optional[str] = None
    expected_public_key: Optional[str] = None


class HostKeyConfirmationRequiredError(Exception):
    """Raised when host key verification requires explicit user confirmation."""

    def __init__(self, problem: HostKeyProblem):
        super().__init__("Host key verification failed")
        self.problem = problem


class UnknownHostKeyError(HostKeyConfirmationRequiredError):
    """Raised when the host key is not present in known_hosts."""


class HostKeyChangedError(HostKeyConfirmationRequiredError):
    """Raised when the host key does not match the entry in known_hosts."""
