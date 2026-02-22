"""Tests for runicorn.config.rnconfig — project-level TOML config merging."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

import runicorn.config.rnconfig as _mod
from runicorn.config.rnconfig import load_effective_rnconfig


@pytest.fixture(autouse=True)
def _clear_rnconfig_cache():
    _mod._effective_cache.clear()
    yield
    _mod._effective_cache.clear()


class TestLoadEffectiveRnconfig:

    def test_load_user_level_only(
        self, mock_config_root: Path, tmp_path: Path
    ) -> None:
        user_cfg = mock_config_root / "rnconfig.toml"
        user_cfg.write_text('[training]\nepochs = 10\n', encoding="utf-8")

        result = load_effective_rnconfig(workspace_root=str(tmp_path))

        assert result["training"]["epochs"] == 10

    def test_load_project_level_only(
        self, mock_config_root: Path, tmp_path: Path
    ) -> None:
        proj_cfg = tmp_path / "rnconfig.toml"
        proj_cfg.write_text('[training]\nlr = 0.01\n', encoding="utf-8")

        result = load_effective_rnconfig(workspace_root=str(tmp_path))

        assert result["training"]["lr"] == 0.01

    def test_merge_project_overrides_user(
        self, mock_config_root: Path, tmp_path: Path
    ) -> None:
        (mock_config_root / "rnconfig.toml").write_text(
            '[training]\nepochs = 10\nlr = 0.1\n', encoding="utf-8"
        )
        (tmp_path / "rnconfig.toml").write_text(
            '[training]\nlr = 0.01\n', encoding="utf-8"
        )

        result = load_effective_rnconfig(workspace_root=str(tmp_path))

        assert result["training"]["epochs"] == 10   # from user
        assert result["training"]["lr"] == 0.01     # overridden by project

    def test_mtime_cache_hit(
        self, mock_config_root: Path, tmp_path: Path
    ) -> None:
        (mock_config_root / "rnconfig.toml").write_text(
            '[a]\nx = 1\n', encoding="utf-8"
        )

        first = load_effective_rnconfig(workspace_root=str(tmp_path))
        second = load_effective_rnconfig(workspace_root=str(tmp_path))

        assert first is second  # same object from cache

    def test_mtime_cache_invalidation(
        self, mock_config_root: Path, tmp_path: Path
    ) -> None:
        cfg = mock_config_root / "rnconfig.toml"
        cfg.write_text('[a]\nx = 1\n', encoding="utf-8")
        load_effective_rnconfig(workspace_root=str(tmp_path))

        time.sleep(0.05)
        cfg.write_text('[a]\nx = 2\n', encoding="utf-8")

        result = load_effective_rnconfig(workspace_root=str(tmp_path))
        assert result["a"]["x"] == 2
