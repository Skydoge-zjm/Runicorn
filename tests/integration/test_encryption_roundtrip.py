"""Integration tests for encryption roundtrip.

Validates §5.4 of the test plan: sensitive fields survive a full
save → disk → load cycle regardless of the original encryption format.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import runicorn.security.encryption as _enc_mod
from runicorn.security.encryption import SENSITIVE_FIELDS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_fernet_singleton():
    _enc_mod._fernet_instance = None
    yield
    _enc_mod._fernet_instance = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSaveLoadRoundtripAllFields:
    """test_save_load_roundtrip_all_fields — every SENSITIVE_FIELDS value
    survives save → connections.json (Fernet) → load → plaintext."""

    def test_all_fields_roundtrip(self, mock_config_root: Path):
        from runicorn.config.connections import save_connections, load_saved_connections
        from runicorn.security.encryption import is_encrypted

        conn = {"host": "myhost", "port": 22, "username": "deploy"}
        expected = {}
        for field in SENSITIVE_FIELDS:
            plain = f"value_of_{field}"
            conn[field] = plain
            expected[field] = plain

        save_connections([conn])

        # Verify on-disk values are encrypted
        raw = json.loads((mock_config_root / "connections.json").read_text("utf-8"))
        for field in SENSITIVE_FIELDS:
            assert is_encrypted(raw[0][field]), f"{field} not encrypted on disk"

        # Verify loaded values are plaintext
        loaded = load_saved_connections()
        assert len(loaded) == 1
        for field in SENSITIVE_FIELDS:
            assert loaded[0][field] == expected[field], (
                f"{field}: expected {expected[field]!r}, got {loaded[0][field]!r}"
            )


class TestMixedFormatConnections:
    """test_mixed_format_connections — connections.json with a mix of
    Fernet, XOR (ENC:), and plaintext values all load correctly."""

    def test_mixed_formats_decode(self, mock_config_root: Path):
        from runicorn.config.connections import load_saved_connections
        from runicorn.security.encryption import encrypt_password
        from runicorn.security.credentials import CredentialManager

        # Prepare three connections with different encryption formats
        mgr = CredentialManager(key_file=mock_config_root / ".credential_key")

        fernet_pw = encrypt_password("fernet_secret")   # Fernet
        xor_pw = mgr.encrypt_credential("xor_secret")   # XOR (ENC:)
        plain_pw = "plain_secret"                        # plaintext

        connections = [
            {"host": "h1", "key": "h1:22@u", "password": fernet_pw},
            {"host": "h2", "key": "h2:22@u", "password": xor_pw},
            {"host": "h3", "key": "h3:22@u", "password": plain_pw},
        ]

        conn_path = mock_config_root / "connections.json"
        conn_path.write_text(
            json.dumps(connections, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        loaded = load_saved_connections()
        pw_map = {c["host"]: c.get("password") for c in loaded}

        assert pw_map["h1"] == "fernet_secret"
        assert pw_map["h2"] == "xor_secret"
        # Plain text passes through as-is
        assert pw_map["h3"] == "plain_secret"
