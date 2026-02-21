"""Unit tests for runicorn.remote.known_hosts (migrated from tests_legacy)."""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import pytest

from runicorn.remote.known_hosts import (
    KnownHostsLockTimeout,
    KnownHostsStore,
    KnownHostsWriteError,
    compute_fingerprint_sha256,
    format_known_hosts_host,
    parse_known_hosts_host,
    parse_openssh_public_key,
)


class TestFormatAndParse:
    """format_known_hosts_host / parse_known_hosts_host round-trip."""

    def test_default_port(self):
        assert format_known_hosts_host("example.com", 22) == "example.com"
        assert parse_known_hosts_host("example.com") == ("example.com", 22)

    def test_custom_port(self):
        assert format_known_hosts_host("example.com", 2222) == "[example.com]:2222"
        assert parse_known_hosts_host("[example.com]:2222") == ("example.com", 2222)


class TestParseOpensshPublicKey:
    """parse_openssh_public_key valid/invalid inputs."""

    def test_valid(self):
        key_bytes = b"abc"
        key_b64 = base64.b64encode(key_bytes).decode("ascii")
        parsed = parse_openssh_public_key(f"ssh-ed25519 {key_b64} comment")
        assert parsed.key_type == "ssh-ed25519"
        assert parsed.key_base64 == key_b64
        assert parsed.key_bytes == key_bytes

    def test_too_few_fields(self):
        with pytest.raises(ValueError):
            parse_openssh_public_key("ssh-ed25519")

    def test_invalid_base64(self):
        with pytest.raises(ValueError):
            parse_openssh_public_key("ssh-ed25519 !!!not-base64!!!")


class TestComputeFingerprint:
    def test_matches_reference(self):
        key_bytes = b"abc"
        expected = base64.b64encode(hashlib.sha256(key_bytes).digest()).decode("ascii").rstrip("=")
        assert compute_fingerprint_sha256(key_bytes) == f"SHA256:{expected}"


class TestKnownHostsStore:
    """KnownHostsStore CRUD operations."""

    def test_upsert_list_remove(self, tmp_path: Path):
        store = KnownHostsStore(tmp_path / "known_hosts")
        key_b64 = base64.b64encode(b"abc").decode("ascii")

        # Insert
        assert store.upsert_host_key(host="example.com", port=22, key_type="ssh-ed25519", key_base64=key_b64)
        # Duplicate → no-op
        assert not store.upsert_host_key(host="example.com", port=22, key_type="ssh-ed25519", key_base64=key_b64)

        entries = store.list_host_keys()
        assert len(entries) == 1
        assert entries[0]["host"] == "example.com"
        assert entries[0]["key_type"] == "ssh-ed25519"
        assert entries[0]["fingerprint_sha256"] == compute_fingerprint_sha256(b"abc")

        # Update key
        key_b64_2 = base64.b64encode(b"def").decode("ascii")
        assert store.upsert_host_key(host="example.com", port=22, key_type="ssh-ed25519", key_base64=key_b64_2)
        assert store.list_host_keys()[0]["key_base64"] == key_b64_2

        # Remove
        assert store.remove_host_key(host="example.com", port=22, key_type="ssh-ed25519")
        assert not store.remove_host_key(host="example.com", port=22, key_type="ssh-ed25519")
        assert store.list_host_keys() == []


class TestKnownHostsStoreErrors:
    """Error scenarios: lock timeout, write error."""

    def test_lock_timeout(self, tmp_path: Path, monkeypatch):
        import runicorn.remote.known_hosts as mod

        class _FakeLock:
            def __init__(self, *a, **kw):
                pass
            def __enter__(self):
                raise mod.Timeout("timeout")
            def __exit__(self, *a):
                return False

        monkeypatch.setattr(mod, "FileLock", _FakeLock)
        store = KnownHostsStore(tmp_path / "known_hosts", lock_timeout_seconds=0.01)
        with pytest.raises(KnownHostsLockTimeout):
            store.list_host_keys()

    def test_write_error(self, tmp_path: Path, monkeypatch):
        import runicorn.remote.known_hosts as mod

        monkeypatch.setattr(mod.os, "replace", lambda *a, **kw: (_ for _ in ()).throw(OSError("fail")))
        store = KnownHostsStore(tmp_path / "known_hosts")
        with pytest.raises(KnownHostsWriteError):
            store.upsert_host_key(host="example.com", port=22, key_type="ssh-ed25519", key_base64="AAAA")
