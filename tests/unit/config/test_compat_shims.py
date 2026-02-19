"""Tests for backward-compatible import shims.

Verifies that old-style imports still work after the config refactor (RF-03).
"""
from __future__ import annotations


class TestCompatShims:

    def test_import_from_runicorn_config(self) -> None:
        from runicorn.config import load_user_config
        assert callable(load_user_config)

    def test_import_from_runicorn_registry(self) -> None:
        """``from runicorn.config import get_config`` (registry function)."""
        from runicorn.config import get_config
        assert callable(get_config)

    def test_import_from_runicorn_rnconfig(self) -> None:
        from runicorn.config import get_effective_rnconfig
        assert callable(get_effective_rnconfig)

    def test_import_private_config_root_dir(self) -> None:
        """security/encryption.py depends on this import path."""
        from runicorn.config import _config_root_dir
        assert callable(_config_root_dir)
