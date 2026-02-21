"""Integration tests for XOR → Fernet config migration.

Validates §5.4 of the test plan: legacy XOR-encrypted SSH connections in
config.json are migrated to Fernet-encrypted connections.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import runicorn.security.encryption as _enc_mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_fernet_singleton():
    _enc_mod._fernet_instance = None
    yield
    _enc_mod._fernet_instance = None


def _prepare_legacy_config(
    mock_config_root: Path,
    connections: list,
) -> Path:
    """Write a config.json with ``ssh_connections`` using XOR encryption."""
    from runicorn.security.credentials import CredentialManager

    mgr = CredentialManager(key_file=mock_config_root / ".credential_key")

    legacy = []
    for conn in connections:
        entry = conn.copy()
        # Encrypt sensitive fields with XOR
        for field in ("password", "passphrase", "private_key", "secret", "token", "api_key"):
            if field in entry and entry[field]:
                entry[field] = mgr.encrypt_credential(entry[field])
        legacy.append(entry)

    cfg_path = mock_config_root / "config.json"
    cfg_path.write_text(
        json.dumps({"ssh_connections": legacy}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return cfg_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestXorToFernetMigration:
    """test_xor_to_fernet_migration — legacy XOR data in config.json
    gets migrated to Fernet connections.json on first read."""

    def test_migration_creates_connections_json(self, mock_config_root: Path):
        _prepare_legacy_config(mock_config_root, [
            {"host": "server1", "port": 22, "username": "admin",
             "key": "server1:22@admin", "password": "s3cret"},
        ])

        from runicorn.config.connections import load_saved_connections
        conns = load_saved_connections()

        assert len(conns) >= 1
        assert any(c["host"] == "server1" for c in conns)
        # Password should be decrypted back to plaintext
        migrated = [c for c in conns if c["host"] == "server1"][0]
        assert migrated["password"] == "s3cret"

        # connections.json should exist with Fernet-encrypted data
        conn_file = mock_config_root / "connections.json"
        assert conn_file.exists()
        raw = json.loads(conn_file.read_text("utf-8"))
        from runicorn.security.encryption import is_encrypted
        assert is_encrypted(raw[0]["password"])


class TestMigrationPreservesAllConnections:
    """test_migration_preserves_all_connections — count stays the same."""

    def test_three_connections_preserved(self, mock_config_root: Path):
        originals = [
            {"host": f"host{i}", "port": 22, "username": "u",
             "key": f"host{i}:22@u", "password": f"pw{i}"}
            for i in range(3)
        ]
        _prepare_legacy_config(mock_config_root, originals)

        from runicorn.config.connections import load_saved_connections
        conns = load_saved_connections()

        assert len(conns) == 3
        hosts = {c["host"] for c in conns}
        assert hosts == {"host0", "host1", "host2"}


class TestMigrationRemovesFromConfigJson:
    """After migration, config.json should no longer contain ``ssh_connections``."""

    def test_legacy_key_removed(self, mock_config_root: Path):
        _prepare_legacy_config(mock_config_root, [
            {"host": "h", "port": 22, "username": "u",
             "key": "h:22@u", "password": "pw"},
        ])

        from runicorn.config.connections import load_saved_connections
        load_saved_connections()  # triggers migration

        cfg = json.loads((mock_config_root / "config.json").read_text("utf-8"))
        assert "ssh_connections" not in cfg
        assert (mock_config_root / "connections.json").exists()
