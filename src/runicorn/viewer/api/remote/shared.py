"""
Shared helpers and models for the unified remote API routes.
"""
from __future__ import annotations

import json
import logging
import shlex
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field

from ....remote.host_key import HostKeyProblem

logger = logging.getLogger(__name__)

_REMOTE_PYTHON_COMMAND_MIN_TIMEOUT_S = 30
_REMOTE_RUNICORN_IMPORT_MIN_TIMEOUT_S = 120
_REMOTE_PIP_SHOW_MIN_TIMEOUT_S = 60
_REMOTE_STORAGE_SCAN_MIN_TIMEOUT_S = 120


def _mask_saved_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    masked = dict(entry)
    password = masked.pop("password", None)
    private_key = masked.pop("private_key", None)
    passphrase = masked.pop("passphrase", None)
    if masked.get("kind") == "server":
        masked["hasSavedPassword"] = bool(password)
        masked["hasSavedPrivateKey"] = bool(private_key)
        masked["hasSavedPassphrase"] = bool(passphrase)
    return masked


def _get_saved_server(server_id: str) -> Dict[str, Any]:
    from ....config import load_saved_connections

    connections = load_saved_connections()
    for entry in connections:
        if entry.get("kind") == "server" and entry.get("id") == server_id:
            return entry

    raise HTTPException(status_code=404, detail=f"Saved server not found: {server_id}")


def _resolve_saved_server_payload(
    *,
    saved_server_id: Optional[str],
    host: Optional[str],
    port: int,
    username: Optional[str],
    password: Optional[str],
    private_key: Optional[str],
    private_key_path: Optional[str],
    passphrase: Optional[str],
    use_agent: bool,
) -> Dict[str, Any]:
    resolved = {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "private_key": private_key,
        "private_key_path": private_key_path,
        "passphrase": passphrase,
        "use_agent": use_agent,
    }

    if not saved_server_id:
        return resolved

    saved = _get_saved_server(saved_server_id)

    for field in ("host", "username"):
        incoming = resolved.get(field)
        saved_value = saved.get(field)
        if incoming and saved_value and incoming != saved_value:
            raise HTTPException(
                status_code=400,
                detail=f"Saved server mismatch for field: {field}",
            )
        resolved[field] = saved_value

    incoming_port = resolved.get("port")
    saved_port = int(saved.get("port", incoming_port or 22))
    if incoming_port and incoming_port != saved_port:
        raise HTTPException(
            status_code=400,
            detail="Saved server mismatch for field: port",
        )
    resolved["port"] = saved_port

    for credential_field in ("password", "private_key", "private_key_path", "passphrase"):
        if resolved.get(credential_field) is None and saved.get(credential_field) is not None:
            resolved[credential_field] = saved.get(credential_field)

    return resolved


def _merge_saved_connection_secrets(connections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from ....config import load_saved_connections

    existing_servers = {
        entry.get("id"): entry
        for entry in load_saved_connections()
        if entry.get("kind") == "server" and entry.get("id")
    }
    merged: List[Dict[str, Any]] = []
    for entry in connections:
        if entry.get("kind") != "server":
            merged.append(entry)
            continue

        existing = existing_servers.get(entry.get("id"))
        if existing is None:
            merged.append(entry)
            continue

        merged_entry = dict(entry)
        for field in ("password", "private_key", "private_key_path", "passphrase"):
            if field not in merged_entry and existing.get(field) is not None:
                merged_entry[field] = existing.get(field)
        merged.append(merged_entry)
    return merged


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


def _parse_connection_id(connection_id: str) -> tuple[str, int, str]:
    try:
        username_host, port_str = connection_id.rsplit(":", 1)
        username, host = username_host.split("@", 1)
        return host, int(port_str), username
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid connection_id format: {connection_id}",
        ) from e


def _get_active_connection(request: Request, connection_id: str):
    if not hasattr(request.app.state, "connection_pool"):
        raise HTTPException(status_code=400, detail="Connection pool not initialized")

    pool = request.app.state.connection_pool
    host, port, username = _parse_connection_id(connection_id)
    connection = pool.get_connection(host, port, username)
    if not connection or not connection.is_connected:
        raise HTTPException(
            status_code=404,
            detail=f"Connection not found or inactive: {connection_id}",
        )
    return connection


def _resolve_python_command(connection: Any, conda_env: str) -> str:
    from ....remote.environment import RemoteEnvironmentDetector

    detector = RemoteEnvironmentDetector(connection)
    cmd_prefix = detector.get_python_command_for_env(conda_env or "system")
    if not cmd_prefix:
        raise HTTPException(
            status_code=404,
            detail=f"Environment '{conda_env}' not found. Please check the environment name.",
        )
    return cmd_prefix


def _get_command_timeout(connection: Any, minimum: int) -> int:
    configured = getattr(getattr(connection, "config", None), "timeout", 0)
    try:
        configured_timeout = int(configured)
    except (TypeError, ValueError):
        configured_timeout = 0
    return max(configured_timeout, minimum)


def _detect_remote_storage_candidates(
    connection: Any,
    python_cmd: str,
    *,
    scan_root: Optional[str],
    max_depth: int,
) -> List[Dict[str, Any]]:
    script = """
import json
import os
import sys
from pathlib import Path

COMMON_NAMES = {".runicorn", "runicorn_data"}
PRUNE = {
    ".cache", ".cargo", ".conda", ".local", ".npm", ".rustup", ".ssh",
    ".vscode-server", "__pycache__", "node_modules", "miniconda3", "anaconda3",
    "miniconda", "anaconda", "venv", ".venv", "env",
}
MAX_RUN_DEPTH = 4
MAX_CANDIDATES = 12
MAX_RUN_SCAN = 64

requested_root = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else str(Path.home())
max_depth = int(sys.argv[2]) if len(sys.argv) > 2 else 3
root = Path(requested_root).expanduser().resolve()

if not root.exists():
    raise SystemExit("Scan root does not exist")
if not root.is_dir():
    raise SystemExit("Scan root is not a directory")

candidates = []

def run_count_for(root: Path) -> int:
    runs_dir = root / "runs"
    if not runs_dir.is_dir():
        return 0

    count = 0
    for current, dirs, files in os.walk(runs_dir):
        current_path = Path(current)
        rel_depth = 0 if current_path == runs_dir else len(current_path.relative_to(runs_dir).parts)
        if rel_depth > MAX_RUN_DEPTH:
            dirs[:] = []
            continue
        if "meta.json" in files or "status.json" in files:
            count += 1
            dirs[:] = []
            if count >= MAX_RUN_SCAN:
                break
    return count

for current, dirs, files in os.walk(root):
    current_path = Path(current)
    rel_depth = 0 if current_path == root else len(current_path.relative_to(root).parts)
    if rel_depth > max_depth:
        dirs[:] = []
        continue

    dirs[:] = [
        d for d in dirs
        if d not in PRUNE and (not d.startswith(".") or d in COMMON_NAMES)
    ]

    has_runs = (current_path / "runs").is_dir()
    has_archive = (current_path / "archive").is_dir()
    has_index = (current_path / "index").is_dir()
    common_name = current_path.name in COMMON_NAMES

    if not has_runs and not has_archive and not has_index and not common_name:
        continue

    run_count = run_count_for(current_path) if has_runs else 0
    if not (run_count > 0 or has_archive or has_index or (common_name and has_runs)):
        continue

    score = 0
    if run_count > 0:
        score += 100 + min(run_count, 20)
    if has_archive:
        score += 25
    if has_index:
        score += 15
    if common_name:
        score += 10

    candidates.append({
        "path": str(current_path),
        "run_count": run_count,
        "has_archive": has_archive,
        "has_index": has_index,
        "score": score,
    })

candidates.sort(key=lambda item: (-item["score"], item["path"]))
seen = set()
deduped = []
for item in candidates:
    path = item["path"]
    if path in seen:
        continue
    seen.add(path)
    deduped.append(item)
    if len(deduped) >= MAX_CANDIDATES:
        break

print(json.dumps({"scan_root": str(root), "candidates": deduped}, ensure_ascii=False))
""".strip()

    stdout, stderr, exit_code = connection.exec_command(
        f"{python_cmd} -c {shlex.quote(script)} {shlex.quote(scan_root or '')} {int(max_depth)}",
        timeout=_get_command_timeout(connection, _REMOTE_STORAGE_SCAN_MIN_TIMEOUT_S),
    )
    if exit_code != 0:
        raise RuntimeError(stderr.strip() or "Failed to detect remote storage candidates")

    try:
        data = json.loads(stdout.strip() or "{}")
    except json.JSONDecodeError as e:
        raise RuntimeError("Invalid storage candidate payload from remote host") from e

    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        return []
    return [
        item for item in candidates
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
