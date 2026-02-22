"""Config-related fixtures shared across test layers."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def mock_config_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect all config path helpers to a temporary directory.

    Patches ``runicorn.config.paths._config_root_dir`` so that every
    helper (``get_config_file_path``, ``get_connections_file_path``, etc.)
    resolves under *tmp_path / "config"* instead of the real user directory.

    Returns the mock config root for convenience.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    _mock = lambda: config_dir
    # Patch every known binding of _config_root_dir so all consumers
    # (paths, __init__, rate_limits, encryption, etc.) see the mock.
    monkeypatch.setattr("runicorn.config.paths._config_root_dir", _mock)
    monkeypatch.setattr("runicorn.config._config_root_dir", _mock)
    monkeypatch.setattr("runicorn.config.rate_limits._config_root_dir", _mock)
    return config_dir
