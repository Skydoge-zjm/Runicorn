"""Tests for runicorn.config.paths — cross-platform path resolution.

Note: _config_root_dir creates pathlib.Path objects, and Python 3.12+
pathlib checks os.name at instantiation.  Monkeypatching os.name to a
foreign platform (e.g. "posix" on Windows) causes PosixPath to be
constructed, which raises UnsupportedOperation.  Therefore the
platform-specific branch tests are guarded with ``skipif``.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from runicorn.config import paths


# ---------------------------------------------------------------------------
# _config_root_dir — platform-specific tests
# ---------------------------------------------------------------------------

class TestConfigRootDir:

    @pytest.mark.skipif(os.name != "nt", reason="Windows-only test")
    def test_windows(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        appdata = str(tmp_path / "AppData" / "Roaming")
        monkeypatch.setenv("APPDATA", appdata)

        result = paths._config_root_dir()

        assert result == Path(appdata) / "Runicorn"

    @pytest.mark.skipif(os.name != "nt", reason="Windows-only test")
    def test_windows_no_appdata(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("APPDATA", raising=False)

        result = paths._config_root_dir()

        assert result.name == "Runicorn"
        assert "AppData" in str(result)

    @pytest.mark.skipif(
        os.name == "nt" or sys.platform == "darwin",
        reason="Linux-only test",
    )
    def test_linux(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

        result = paths._config_root_dir()

        assert result == Path.home() / ".config" / "runicorn"

    @pytest.mark.skipif(
        os.name == "nt" or sys.platform == "darwin",
        reason="Linux-only test",
    )
    def test_linux_xdg(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

        result = paths._config_root_dir()

        assert result == tmp_path / "xdg" / "runicorn"

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only test")
    def test_macos(self) -> None:
        result = paths._config_root_dir()

        assert result == Path.home() / "Library" / "Application Support" / "Runicorn"


# ---------------------------------------------------------------------------
# Helper path functions — these use mock_config_root so work on all platforms
# ---------------------------------------------------------------------------

class TestHelperPaths:

    def test_get_config_file_path(self, mock_config_root: Path) -> None:
        assert paths.get_config_file_path() == mock_config_root / "config.json"

    def test_get_connections_file_path(self, mock_config_root: Path) -> None:
        assert paths.get_connections_file_path() == mock_config_root / "connections.json"

    def test_get_known_hosts_file_path(self, mock_config_root: Path) -> None:
        assert paths.get_known_hosts_file_path() == mock_config_root / "known_hosts"

    def test_get_registry_dir(self, mock_config_root: Path) -> None:
        result = paths.get_registry_dir()
        assert result == mock_config_root / "registry"
        assert result.is_dir()

    def test_get_rnconfig_file_path(self, mock_config_root: Path) -> None:
        assert paths.get_rnconfig_file_path() == mock_config_root / "rnconfig.toml"
