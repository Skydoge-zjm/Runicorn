from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from filelock import FileLock, Timeout

from ..config import get_known_hosts_file_path


@dataclass(frozen=True)
class ParsedPublicKey:
    """A parsed OpenSSH public key string."""

    key_type: str
    key_base64: str
    key_bytes: bytes


class KnownHostsError(Exception):
    """Base error for known_hosts operations."""


class KnownHostsLockTimeout(KnownHostsError):
    """Raised when known_hosts file lock cannot be acquired within timeout."""


class KnownHostsWriteError(KnownHostsError):
    """Raised when known_hosts cannot be written atomically."""


def format_known_hosts_host(host: str, port: int) -> str:
    """Format host field in OpenSSH known_hosts style."""
    if port == 22:
        return host
    return f"[{host}]:{port}"


def parse_openssh_public_key(public_key: str) -> ParsedPublicKey:
    """Parse an OpenSSH public key line like '<type> <base64> [comment]' into components."""
    stripped = public_key.strip()
    parts = stripped.split()
    if len(parts) < 2:
        raise ValueError("Invalid public key format")

    key_type = parts[0]
    key_base64 = parts[1]

    padding = "=" * ((4 - (len(key_base64) % 4)) % 4)
    try:
        key_bytes = base64.b64decode(key_base64 + padding, validate=True)
    except Exception as e:
        raise ValueError("Invalid base64 public key") from e

    return ParsedPublicKey(key_type=key_type, key_base64=key_base64, key_bytes=key_bytes)


def compute_fingerprint_sha256(key_bytes: bytes) -> str:
    """Compute OpenSSH-compatible SHA256 fingerprint for a public key blob."""
    digest = hashlib.sha256(key_bytes).digest()
    fp = base64.b64encode(digest).decode("ascii").rstrip("=")
    return f"SHA256:{fp}"


class KnownHostsStore:
    """A concurrency-safe OpenSSH known_hosts store managed by Runicorn."""

    def __init__(self, known_hosts_path: Path, lock_timeout_seconds: float = 10.0):
        self._known_hosts_path = known_hosts_path
        self._lock_path = Path(f"{known_hosts_path}.lock")
        self._lock_timeout_seconds = lock_timeout_seconds

    @classmethod
    def from_runicorn_config(cls, lock_timeout_seconds: float = 10.0) -> "KnownHostsStore":
        return cls(get_known_hosts_file_path(), lock_timeout_seconds=lock_timeout_seconds)

    def list_host_keys(self) -> List[dict]:
        """List all host key entries with parsed host/port and fingerprint."""
        try:
            with FileLock(str(self._lock_path), timeout=self._lock_timeout_seconds):
                lines = self._read_lines_unlocked()
        except Timeout as e:
            raise KnownHostsLockTimeout(
                f"Timeout acquiring known_hosts lock: {self._lock_path}"
            ) from e

        entries: List[dict] = []
        for raw in lines:
            parsed = self._parse_entry_line(raw)
            if not parsed:
                continue

            hosts, key_type, key_base64, _comment = parsed
            for host_field in hosts:
                host, port = parse_known_hosts_host(host_field)
                fingerprint = compute_fingerprint_sha256(
                    base64.b64decode(_pad_base64(key_base64), validate=False)
                )
                entries.append(
                    {
                        "host": host,
                        "port": port,
                        "known_hosts_host": host_field,
                        "key_type": key_type,
                        "key_base64": key_base64,
                        "fingerprint_sha256": fingerprint,
                    }
                )
        return entries

    def remove_host_key(self, host: str, port: int, key_type: str) -> bool:
        """Remove a host key entry. Returns True if file content changed."""
        known_hosts_host = format_known_hosts_host(host, port)

        try:
            with FileLock(str(self._lock_path), timeout=self._lock_timeout_seconds):
                original_lines = self._read_lines_unlocked()
                new_lines: List[str] = []
                removed = False

                for raw in original_lines:
                    parsed = self._parse_entry_line(raw)
                    if not parsed:
                        new_lines.append(raw)
                        continue

                    hosts, existing_key_type, existing_key_base64, comment = parsed
                    if existing_key_type != key_type or known_hosts_host not in hosts:
                        new_lines.append(raw)
                        continue

                    remaining_hosts = [h for h in hosts if h != known_hosts_host]
                    if remaining_hosts:
                        new_lines.append(
                            self._format_entry_line(
                                remaining_hosts, existing_key_type, existing_key_base64, comment
                            )
                        )
                    removed = True

                if not removed:
                    return False

                self._write_lines_atomic_unlocked(new_lines)
                return True
        except Timeout as e:
            raise KnownHostsLockTimeout(
                f"Timeout acquiring known_hosts lock: {self._lock_path}"
            ) from e

    def upsert_host_key(self, host: str, port: int, key_type: str, key_base64: str) -> bool:
        """Add or update a host key entry.

        Returns:
            True if the known_hosts file content was changed.
        """
        known_hosts_host = format_known_hosts_host(host, port)

        try:
            with FileLock(str(self._lock_path), timeout=self._lock_timeout_seconds):
                original_lines = self._read_lines_unlocked()
                new_lines = self._upsert_lines(
                    lines=original_lines,
                    known_hosts_host=known_hosts_host,
                    key_type=key_type,
                    key_base64=key_base64,
                )

                if new_lines == original_lines:
                    return False

                self._write_lines_atomic_unlocked(new_lines)
                return True
        except Timeout as e:
            raise KnownHostsLockTimeout(
                f"Timeout acquiring known_hosts lock: {self._lock_path}"
            ) from e

    def _read_lines_unlocked(self) -> List[str]:
        try:
            if not self._known_hosts_path.exists():
                return []
            return self._known_hosts_path.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            raise KnownHostsError(f"Failed to read known_hosts: {self._known_hosts_path}") from e

    @staticmethod
    def _parse_entry_line(line: str) -> Optional[Tuple[List[str], str, str, str]]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            return None

        parts = stripped.split()
        if len(parts) < 3:
            return None

        hosts_field, key_type, key_base64 = parts[0], parts[1], parts[2]
        comment = " ".join(parts[3:]) if len(parts) > 3 else ""
        hosts = hosts_field.split(",")
        return hosts, key_type, key_base64, comment

    @staticmethod
    def _format_entry_line(hosts: List[str], key_type: str, key_base64: str, comment: str) -> str:
        hosts_field = ",".join(hosts)
        if comment:
            return f"{hosts_field} {key_type} {key_base64} {comment}"
        return f"{hosts_field} {key_type} {key_base64}"

    @classmethod
    def _upsert_lines(
        cls,
        *,
        lines: List[str],
        known_hosts_host: str,
        key_type: str,
        key_base64: str,
    ) -> List[str]:
        new_line = f"{known_hosts_host} {key_type} {key_base64}"

        out: List[str] = []
        inserted = False

        for raw in lines:
            parsed = cls._parse_entry_line(raw)
            if not parsed:
                out.append(raw)
                continue

            hosts, existing_key_type, existing_key_base64, comment = parsed
            if existing_key_type != key_type or known_hosts_host not in hosts:
                out.append(raw)
                continue

            remaining_hosts = [h for h in hosts if h != known_hosts_host]

            if not inserted and remaining_hosts:
                out.append(cls._format_entry_line(remaining_hosts, existing_key_type, existing_key_base64, comment))
                out.append(new_line)
                inserted = True
                continue

            if not inserted and not remaining_hosts:
                out.append(new_line)
                inserted = True
                continue

            if remaining_hosts:
                out.append(cls._format_entry_line(remaining_hosts, existing_key_type, existing_key_base64, comment))
            # Drop the entry if it only contained the target host and we already inserted.

        if not inserted:
            out.append(new_line)

        return out

    def _write_lines_atomic_unlocked(self, lines: List[str]) -> None:
        try:
            self._known_hosts_path.parent.mkdir(parents=True, exist_ok=True)

            tmp_path = self._known_hosts_path.parent / (
                f".{self._known_hosts_path.name}.tmp.{os.getpid()}"
            )
            tmp_text = "\n".join(lines) + "\n" if lines else ""
            tmp_path.write_text(tmp_text, encoding="utf-8")
            os.replace(tmp_path, self._known_hosts_path)
        except Exception as e:
            try:
                if "tmp_path" in locals() and isinstance(tmp_path, Path) and tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise KnownHostsWriteError(
                f"Failed to write known_hosts atomically: {self._known_hosts_path}"
            ) from e


def parse_known_hosts_host(host_field: str) -> Tuple[str, int]:
    """Parse OpenSSH known_hosts host field into (host, port)."""
    if host_field.startswith("[") and "]" in host_field:
        host_part, _, port_part = host_field[1:].partition("]")
        port = 22
        if port_part.startswith(":"):
            try:
                port = int(port_part[1:])
            except ValueError:
                port = 22
        return host_part, port

    # Default port 22 when no explicit port is present
    return host_field, 22


def find_known_host_key_base64(*, host: str, port: int, key_type: str) -> Optional[str]:
    """Find the expected host key (base64) for (host, port, key_type) from Runicorn known_hosts.

    This helper is intentionally small and dependency-free so that different SSH backends
    (OpenSSH / AsyncSSH / Paramiko) can reuse the same expected-key lookup logic.

    Returns:
        The base64-encoded public key blob if found, otherwise None.
    """

    store = KnownHostsStore.from_runicorn_config()
    known_hosts_host = format_known_hosts_host(host, port)

    try:
        entries = store.list_host_keys()
    except Exception:
        # Best-effort: host key lookup should not crash the caller.
        return None

    for entry in entries:
        try:
            if entry.get("known_hosts_host") != known_hosts_host:
                continue
            if entry.get("key_type") != key_type:
                continue
            key_base64 = entry.get("key_base64")
            if isinstance(key_base64, str) and key_base64:
                return key_base64
        except Exception:
            continue

    return None


def _pad_base64(data: str) -> str:
    """Pad base64 string to valid length."""
    padding = "=" * ((4 - (len(data) % 4)) % 4)
    return data + padding
