"""Tests for the curated public surface of runicorn.security."""
from __future__ import annotations


def test_security_module_hides_legacy_credential_manager() -> None:
    import runicorn.security as security

    assert not hasattr(security, "CredentialManager")
    assert not hasattr(security, "get_credential_manager")
