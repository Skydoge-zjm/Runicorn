"""Tests for runicorn.config.registry — TOML key-value registry."""
from __future__ import annotations

from pathlib import Path

import pytest

from runicorn.config._toml import clear_toml_cache
from runicorn.config.registry import get_config, clear_registry_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_toml_cache()
    yield
    clear_toml_cache()


class TestGetConfig:

    def test_existing_key(self, mock_config_root: Path) -> None:
        reg_dir = mock_config_root / "registry"
        reg_dir.mkdir(parents=True, exist_ok=True)
        (reg_dir / "my_key.toml").write_text('value = "hello"\n', encoding="utf-8")

        assert get_config("my_key") == "hello"

    def test_nested_key(self, mock_config_root: Path) -> None:
        reg_dir = mock_config_root / "registry"
        reg_dir.mkdir(parents=True, exist_ok=True)
        (reg_dir / "ns.toml").write_text('[sub]\nval = 42\n', encoding="utf-8")

        assert get_config("ns/sub/val") == 42

    def test_missing_key_raises(self, mock_config_root: Path) -> None:
        with pytest.raises(KeyError, match="Registry key not found"):
            get_config("nonexistent/key")

    def test_clear_registry_cache(self, mock_config_root: Path) -> None:
        reg_dir = mock_config_root / "registry"
        reg_dir.mkdir(parents=True, exist_ok=True)
        toml_file = reg_dir / "cached_key.toml"
        toml_file.write_text('value = 1\n', encoding="utf-8")

        first = get_config("cached_key")
        clear_registry_cache()
        second = get_config("cached_key")

        assert first == second == 1
