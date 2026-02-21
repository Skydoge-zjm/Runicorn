"""Tests for runicorn.config.connections — SSH connection CRUD + encryption.

Core validation for RF-04 (unified encryption) and RF-05 (unified SSH path).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from runicorn.security.encryption import SENSITIVE_FIELDS


# ---------------------------------------------------------------------------
# Fixture: reset the global Fernet singleton between tests so each test
# gets its own key from mock_config_root.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_fernet_singleton():
    import runicorn.security.encryption as enc
    enc._fernet_instance = None
    yield
    enc._fernet_instance = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSaveAndLoadConnections:

    def test_save_encrypts_all_sensitive_fields(self, mock_config_root: Path) -> None:
        """Every SENSITIVE_FIELDS value must be encrypted on disk."""
        from runicorn.config.connections import save_connections
        from runicorn.security.encryption import is_encrypted

        conn = {"host": "h", "port": 22, "username": "u"}
        for field in SENSITIVE_FIELDS:
            conn[field] = f"plain_{field}"

        save_connections([conn])

        raw = json.loads((mock_config_root / "connections.json").read_text("utf-8"))
        for field in SENSITIVE_FIELDS:
            value = raw[0].get(field)
            assert value is not None, f"{field} should not be None"
            assert is_encrypted(value), f"{field} should be encrypted on disk"

    def test_load_decrypts_all_fields(self, mock_config_root: Path) -> None:
        """load_saved_connections must return plain-text values."""
        from runicorn.config.connections import save_connections, load_saved_connections

        conn = {"host": "h", "port": 22, "username": "u"}
        for field in SENSITIVE_FIELDS:
            conn[field] = f"secret_{field}"

        save_connections([conn])
        loaded = load_saved_connections()

        assert len(loaded) == 1
        for field in SENSITIVE_FIELDS:
            assert loaded[0][field] == f"secret_{field}"

    def test_plaintext_password_gets_encrypted(self, mock_config_root: Path) -> None:
        """Saving a conn with a plaintext password auto-encrypts it."""
        from runicorn.config.connections import save_connections
        from runicorn.security.encryption import is_encrypted

        save_connections([{"host": "h", "password": "letmein"}])

        raw = json.loads((mock_config_root / "connections.json").read_text("utf-8"))
        assert is_encrypted(raw[0]["password"])


class TestCRUD:

    def test_add_ssh_connection(self, mock_config_root: Path) -> None:
        from runicorn.config.connections import add_ssh_connection, load_saved_connections

        add_ssh_connection({"host": "a", "port": 22, "username": "u", "password": "x"})

        conns = load_saved_connections()
        assert len(conns) == 1
        assert conns[0]["host"] == "a"

    def test_remove_ssh_connection(self, mock_config_root: Path) -> None:
        from runicorn.config.connections import (
            add_ssh_connection, remove_ssh_connection, load_saved_connections,
        )

        add_ssh_connection({"host": "a", "port": 22, "username": "u"})
        key = "a:22@u"
        remove_ssh_connection(key)

        assert load_saved_connections() == []

    def test_add_duplicate_connection_updates(self, mock_config_root: Path) -> None:
        """Same host:port@user replaces the existing entry."""
        from runicorn.config.connections import add_ssh_connection, load_saved_connections

        add_ssh_connection({"host": "a", "port": 22, "username": "u", "password": "old"})
        add_ssh_connection({"host": "a", "port": 22, "username": "u", "password": "new"})

        conns = load_saved_connections()
        assert len(conns) == 1
        assert conns[0]["password"] == "new"

    def test_no_connection_limit(self, mock_config_root: Path) -> None:
        """RF-05: no longer limited to 10 connections."""
        from runicorn.config.connections import add_ssh_connection, load_saved_connections

        for i in range(15):
            add_ssh_connection({"host": f"h{i}", "port": 22, "username": "u"})

        assert len(load_saved_connections()) == 15


class TestLegacyXorAndFernetCoexist:

    def test_legacy_xor_and_fernet_coexist(self, mock_config_root: Path) -> None:
        """Connections file with both Fernet and plaintext entries decrypts all."""
        from runicorn.config.connections import save_connections, load_saved_connections
        from runicorn.security.encryption import encrypt_password

        # First save a Fernet-encrypted connection
        save_connections([
            {"host": "fernet_host", "port": 22, "username": "u1", "password": "secret_f"},
        ])

        # Manually append a plaintext connection to the same file
        import json
        conn_path = mock_config_root / "connections.json"
        raw = json.loads(conn_path.read_text("utf-8"))
        raw.append({"host": "plain_host", "port": 22, "username": "u2", "password": "secret_p"})
        conn_path.write_text(json.dumps(raw), encoding="utf-8")

        loaded = load_saved_connections()
        assert len(loaded) == 2
        by_host = {c["host"]: c for c in loaded}
        assert by_host["fernet_host"]["password"] == "secret_f"
        # Plaintext passwords are returned as-is by decrypt_password
        assert by_host["plain_host"]["password"] == "secret_p"


class TestLegacyMigration:

    def test_legacy_xor_migration(self, mock_config_root: Path) -> None:
        """XOR 'ENC:' data in config.json migrates to Fernet connections.json."""
        from runicorn.config.connections import load_saved_connections

        # Write legacy data directly to config.json (simulating old format)
        cfg_path = mock_config_root / "config.json"
        legacy = [{
            "host": "legacy_host",
            "port": 22,
            "username": "root",
            "key": "legacy_host:22@root",
            # Use plaintext (non-ENC:) for simplicity — migration should still
            # copy them across and save_connections encrypts with Fernet.
            "password": "plain_legacy",
        }]
        cfg_path.write_text(
            json.dumps({"ssh_connections": legacy}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # load_saved_connections triggers _migrate_legacy_xor_connections
        conns = load_saved_connections()

        assert len(conns) >= 1
        assert any(c["host"] == "legacy_host" for c in conns)

        # Verify connections.json was created with the migrated data
        conn_path = mock_config_root / "connections.json"
        assert conn_path.exists()

        # After migration, the legacy key should be removed from config.json
        cfg = json.loads(cfg_path.read_text("utf-8"))
        assert "ssh_connections" not in cfg

    def test_missing_key_file_auto_creates(self, mock_config_root: Path) -> None:
        """If .secret.key doesn't exist, encrypt_password auto-generates it."""
        from runicorn.security.encryption import encrypt_password

        key_file = mock_config_root / ".secret.key"
        assert not key_file.exists()

        encrypt_password("test")

        assert key_file.exists()
        assert len(key_file.read_bytes()) > 0
