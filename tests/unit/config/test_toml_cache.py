"""Tests for runicorn.config._toml — shared TOML loading + mtime cache."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from runicorn.config._toml import load_toml, load_toml_cached, clear_toml_cache


@pytest.fixture(autouse=True)
def _reset_cache():
    """Ensure TOML cache is clean before and after every test."""
    clear_toml_cache()
    yield
    clear_toml_cache()


# -- load_toml ---------------------------------------------------------------

class TestLoadToml:

    def test_load_valid_toml(self, tmp_path: Path) -> None:
        f = tmp_path / "valid.toml"
        f.write_text('[section]\nkey = "value"\n', encoding="utf-8")

        result = load_toml(f)

        assert result == {"section": {"key": "value"}}

    def test_load_missing_file_returns_empty(self, tmp_path: Path) -> None:
        result = load_toml(tmp_path / "nonexistent.toml")

        assert result == {}


# -- load_toml_cached ---------------------------------------------------------

class TestLoadTomlCached:

    def test_cached_same_mtime_no_reread(self, tmp_path: Path) -> None:
        """Second call with unchanged file must return the cached dict."""
        f = tmp_path / "cfg.toml"
        f.write_text('[a]\nx = 1\n', encoding="utf-8")

        first = load_toml_cached(f)
        second = load_toml_cached(f)

        assert first == second == {"a": {"x": 1}}
        # Identity check: same dict object means it was served from cache
        assert first is second

    def test_cached_invalidated_on_change(self, tmp_path: Path) -> None:
        """Modifying the file must cause a cache refresh."""
        f = tmp_path / "cfg.toml"
        f.write_text('[a]\nx = 1\n', encoding="utf-8")
        load_toml_cached(f)

        # Ensure mtime_ns differs (Windows has ~100 ns resolution, but
        # write_text will update mtime)
        time.sleep(0.05)
        f.write_text('[a]\nx = 2\n', encoding="utf-8")

        refreshed = load_toml_cached(f)
        assert refreshed == {"a": {"x": 2}}

    def test_cached_missing_file_returns_empty(self, tmp_path: Path) -> None:
        result = load_toml_cached(tmp_path / "gone.toml")
        assert result == {}


# -- clear_toml_cache ---------------------------------------------------------

class TestClearTomlCache:

    def test_clear_forces_reload(self, tmp_path: Path) -> None:
        f = tmp_path / "cfg.toml"
        f.write_text('[b]\ny = 10\n', encoding="utf-8")

        first = load_toml_cached(f)
        clear_toml_cache()
        second = load_toml_cached(f)

        assert first == second
        # After clearing, the dict object must be a fresh load
        assert first is not second
