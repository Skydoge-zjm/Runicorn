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


class TestCLIExportImport:
    """Actual execution of export → import roundtrip."""

    @staticmethod
    def _create_run(storage: "Path", run_id: str, path: str = "proj/exp"):
        import json, os, time
        run_dir = storage / "runs" / path.replace("/", os.sep) / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "meta.json").write_text(
            json.dumps({"id": run_id, "path": path, "created_at": time.time()}),
            encoding="utf-8",
        )
        (run_dir / "status.json").write_text(
            json.dumps({"status": "finished"}), encoding="utf-8"
        )
        return run_dir

    def test_export_creates_archive(self, tmp_path):
        storage = tmp_path / "storage"
        (storage / "runs").mkdir(parents=True)
        self._create_run(storage, "20250101_000000_aaaaaa")

        out = tmp_path / "export.tar.gz"
        result = main(["export", "--storage", str(storage), "--out", str(out)])
        assert result == 0
        assert out.exists()
        assert out.stat().st_size > 0

    def test_export_import_roundtrip(self, tmp_path):
        src = tmp_path / "src_storage"
        (src / "runs").mkdir(parents=True)
        self._create_run(src, "20250201_000000_bbbbbb")

        archive = tmp_path / "roundtrip.tar.gz"
        assert main(["export", "--storage", str(src), "--out", str(archive)]) == 0

        dst = tmp_path / "dst_storage"
        dst.mkdir()
        assert main(["import", "--storage", str(dst), "--archive", str(archive)]) == 0

        # Verify the run was imported
        import os
        imported = list((dst / "runs").rglob("meta.json"))
        assert len(imported) >= 1

    def test_import_missing_archive(self, tmp_path):
        result = main(["import", "--storage", str(tmp_path), "--archive", str(tmp_path / "nope.zip")])
        assert result == 1
