"""Tests for runicorn.cli — smoke tests for each subcommand."""
from __future__ import annotations

import pytest

from runicorn.cli import main


class TestCLISubcommands:
    """Each subcommand should parse --help without error (SystemExit 0)."""

    @pytest.mark.parametrize("cmd", [
        "viewer",
        "config",
        "export",
        "import",
        "export-data",
        "manage",
        "rate-limit",
        "delete",
    ])
    def test_subcommand_help(self, cmd: str):
        """``runicorn <cmd> --help`` exits with code 0."""
        with pytest.raises(SystemExit) as exc_info:
            main([cmd, "--help"])
        assert exc_info.value.code == 0

    def test_no_subcommand_shows_error(self):
        """No subcommand → argparse error (exit 2)."""
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 2

    def test_config_show(self, monkeypatch: pytest.MonkeyPatch, tmp_path):
        """``runicorn config --show`` runs without error."""
        # Patch config paths to tmp_path to avoid touching real config
        monkeypatch.setattr(
            "runicorn.cli.get_config_file_path",
            lambda: tmp_path / "config.json",
        )
        monkeypatch.setattr(
            "runicorn.cli.load_user_config",
            lambda: {},
        )
        result = main(["config", "--show"])
        assert result == 0

    def test_export_uses_iter_all_runs(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path,
    ):
        """``runicorn export`` calls iter_all_runs to discover runs (RF-15)."""
        called = []
        original = __import__("runicorn.storage.file_utils", fromlist=["iter_all_runs"]).iter_all_runs

        def spy(root, **kw):
            called.append(root)
            return original(root, **kw)

        monkeypatch.setattr("runicorn.cli.iter_all_runs", spy)

        storage = tmp_path / "storage"
        (storage / "runs").mkdir(parents=True)
        result = main(["export", "--storage", str(storage)])
        assert result == 0
        assert len(called) == 1
