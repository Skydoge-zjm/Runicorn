"""
Shared models and host-key helpers for unified remote API routes.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from ....remote.host_key import HostKeyProblem

logger = logging.getLogger(__name__)

def _build_host_key_confirmation_required_detail(problem: HostKeyProblem) -> Dict[str, Any]:
    host_key: Dict[str, Any] = {
        "host": problem.host,
        "port": problem.port,
        "known_hosts_host": problem.known_hosts_host,
        "key_type": problem.key_type,
        "fingerprint_sha256": problem.fingerprint_sha256,
        "public_key": problem.public_key,
        "reason": problem.reason,
    }

    if problem.expected_fingerprint_sha256 is not None:
        host_key["expected_fingerprint_sha256"] = problem.expected_fingerprint_sha256
    if problem.expected_public_key is not None:
        host_key["expected_public_key"] = problem.expected_public_key

    return {
        "code": "HOST_KEY_CONFIRMATION_REQUIRED",
        "message": "Host key verification failed",
        "host_key": host_key,
    }


class SSHConnectRequest(BaseModel):
    host: Optional[str] = Field(None, description="Remote server hostname or IP")
    port: int = Field(22, description="SSH port")
    username: Optional[str] = Field(None, description="SSH username")
    password: Optional[str] = Field(None, description="SSH password")
    private_key: Optional[str] = Field(None, description="Private key content")
    private_key_path: Optional[str] = Field(None, description="Path to private key file")
    passphrase: Optional[str] = Field(None, description="Passphrase for private key")
    use_agent: bool = Field(True, description="Use SSH agent")
    saved_server_id: Optional[str] = Field(None, description="Saved server ID for server-side credential lookup")


class RemoteViewerStartRequest(BaseModel):
    host: Optional[str] = Field(None, description="Remote server hostname or IP")
    port: int = Field(22, description="SSH port")
    username: Optional[str] = Field(None, description="SSH username")
    password: Optional[str] = Field(None, description="SSH password")
    private_key: Optional[str] = Field(None, description="Private key content")
    private_key_path: Optional[str] = Field(None, description="Path to private key file")
    passphrase: Optional[str] = Field(None, description="Passphrase for private key")
    use_agent: bool = Field(True, description="Use SSH agent")
    remote_root: str = Field(..., description="Remote storage root directory")
    local_port: Optional[int] = Field(None, description="Local port (auto-detect if None)")
    remote_port: Optional[int] = Field(None, description="Remote port (auto-detect if None)")
    conda_env: Optional[str] = Field(None, description="Conda environment name")
    saved_server_id: Optional[str] = Field(None, description="Saved server ID for server-side credential lookup")


class KnownHostsAcceptRequest(BaseModel):
    host: str
    port: int = Field(..., ge=1, le=65535)
    key_type: str
    public_key: str = Field(..., min_length=1, max_length=8192)
    fingerprint_sha256: str


class KnownHostsRemoveRequest(BaseModel):
    host: str
    port: int = Field(..., ge=1, le=65535)
    key_type: str


class KnownHostsEntry(BaseModel):
    host: str
    port: int
    known_hosts_host: str
    key_type: str
    key_base64: str
    fingerprint_sha256: str
