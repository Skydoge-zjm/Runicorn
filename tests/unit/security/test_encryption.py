"""Unit tests for runicorn.security.encryption — RF-04 core verification."""
from __future__ import annotations

import pytest

from runicorn.security.encryption import (
    SENSITIVE_FIELDS,
    _ensure_key,
    _get_cipher,
    _get_key_path,
    decrypt_password,
    encrypt_password,
    is_encrypted,
)
import runicorn.security.encryption as _enc_mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_fernet_singleton():
    """Reset the module-level Fernet singleton between tests."""
    _enc_mod._fernet_instance = None
    yield
    _enc_mod._fernet_instance = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEncryptDecryptRoundtrip:
    """test_encrypt_decrypt_roundtrip — Fernet encrypt then decrypt returns original."""

    def test_short_password(self, mock_config_root):
        cipher_text = encrypt_password("hunter2")
        assert cipher_text != "hunter2"
        assert decrypt_password(cipher_text) == "hunter2"

    def test_unicode_password(self, mock_config_root):
        plain = "密码très_sécurisé_🔑"
        cipher_text = encrypt_password(plain)
        assert decrypt_password(cipher_text) == plain

    def test_empty_string_passthrough(self, mock_config_root):
        assert encrypt_password("") == ""
        assert decrypt_password("") == ""


class TestIsEncrypted:
    """test_is_encrypted_fernet / test_is_encrypted_plaintext."""

    def test_fernet_token_detected(self, mock_config_root):
        token = encrypt_password("secret")
        assert is_encrypted(token) is True

    def test_plaintext_not_detected(self):
        assert is_encrypted("hello world") is False

    def test_empty_not_detected(self):
        assert is_encrypted("") is False

    def test_short_gAAAAA_not_detected(self):
        # Must be >50 chars to qualify
        assert is_encrypted("gAAAAA_short") is False


class TestDecryptXorLegacy:
    """test_decrypt_xor_legacy — ENC: prefixed values via CredentialManager."""

    def test_xor_roundtrip(self, mock_config_root):
        from runicorn.security.credentials import CredentialManager

        mgr = CredentialManager(key_file=mock_config_root / ".credential_key")
        encrypted = mgr.encrypt_credential("legacy_password")
        assert encrypted.startswith("ENC:")

        # decrypt_password should auto-detect XOR format
        result = decrypt_password(encrypted)
        assert result == "legacy_password"


class TestDecryptAutoDetect:
    """test_decrypt_auto_detect — decrypt_password identifies Fernet vs XOR vs plain."""

    def test_fernet_format(self, mock_config_root):
        enc = encrypt_password("pw_fernet")
        assert decrypt_password(enc) == "pw_fernet"

    def test_xor_format(self, mock_config_root):
        from runicorn.security.credentials import CredentialManager

        mgr = CredentialManager(key_file=mock_config_root / ".credential_key")
        enc = mgr.encrypt_credential("pw_xor")
        assert decrypt_password(enc) == "pw_xor"

    def test_plain_text(self, mock_config_root):
        assert decrypt_password("just_plain") == "just_plain"


class TestDecryptPlaintextPassthrough:
    """test_decrypt_plaintext_passthrough — unrecognised format returned as-is."""

    def test_random_string(self, mock_config_root):
        assert decrypt_password("random_text_123") == "random_text_123"

    def test_numeric_string(self, mock_config_root):
        assert decrypt_password("1234567890") == "1234567890"


class TestSensitiveFields:
    """test_encrypt_all_sensitive_fields — SENSITIVE_FIELDS list completeness."""

    def test_contains_expected_fields(self):
        expected = {"password", "passphrase", "private_key", "secret", "token", "api_key"}
        assert set(SENSITIVE_FIELDS) == expected

    def test_no_duplicates(self):
        assert len(SENSITIVE_FIELDS) == len(set(SENSITIVE_FIELDS))


class TestMissingKeyFileAutoCreates:
    """test_missing_key_file_auto_creates — key file generated on first use."""

    def test_key_created_on_encrypt(self, mock_config_root):
        key_path = _get_key_path()
        assert not key_path.exists()

        encrypt_password("trigger_key_creation")

        assert key_path.exists()
        assert len(key_path.read_bytes()) > 0

    def test_key_reused_across_calls(self, mock_config_root):
        encrypt_password("first")
        key_path = _get_key_path()
        first_key = key_path.read_bytes()

        # Reset singleton but keep key file
        _enc_mod._fernet_instance = None

        encrypt_password("second")
        assert key_path.read_bytes() == first_key
