"""Tests for runicorn.cli — smoke tests for each subcommand."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import runicorn
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

    def test_version_flag(self, capsys: pytest.CaptureFixture[str]):
        """``runicorn --version`` exits with code 0 and prints the current package version."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        assert capsys.readouterr().out.strip() == f"runicorn {runicorn.__version__}"

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
    def _create_run(storage: Path, run_id: str, path: str = "proj/exp"):
        import json
        import os
        import time
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
        imported = list((dst / "runs").rglob("meta.json"))
        assert len(imported) >= 1

    def test_import_missing_archive(self, tmp_path):
        result = main(["import", "--storage", str(tmp_path), "--archive", str(tmp_path / "nope.zip")])
        assert result == 1


class TestCLIExtractedHandlers:
    def test_rate_limit_set_updates_config(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
        config = {"default": {"max_requests": 100, "window_seconds": 60}, "endpoints": {}}

        monkeypatch.setattr("runicorn.config.get_rate_limit_config", lambda: config)
        monkeypatch.setattr("runicorn.config.save_rate_limit_config", lambda updated: config.update(updated))

        result = main([
            "rate-limit",
            "--action", "set",
            "--endpoint", "/api/test",
            "--max-requests", "42",
            "--window", "30",
        ])

        assert result == 0
        assert config["endpoints"]["/api/test"]["max_requests"] == 42
        assert config["endpoints"]["/api/test"]["window_seconds"] == 30
        assert "Updated rate limit for /api/test" in capsys.readouterr().out

    def test_manage_search_uses_manager(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
        class FakeManager:
            def __init__(self, root: Path):
                self.root = root

            def search_experiments(self, project=None, tags=None, text=None):
                return [SimpleNamespace(id="r1", project=project or "proj", name="exp", tags=tags or ["demo"])]

        monkeypatch.setattr("runicorn.extensions.experiment.ExperimentManager", FakeManager)

        result = main([
            "manage",
            "--storage", str(tmp_path),
            "--action", "search",
            "--project", "proj",
            "--tags", "demo",
        ])

        assert result == 0
        output = capsys.readouterr().out
        assert "Found 1 experiments" in output
        assert "r1: proj/exp [demo]" in output

    def test_delete_dry_run_uses_cleanup_handler(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ):
        def fake_delete_run_completely(*, run_id: str, storage_root: Path, dry_run: bool):
            assert storage_root == tmp_path
            assert dry_run is True
            return {
                "success": True,
                "orphaned_assets": [{"asset_type": "code", "name": "snapshot.zip"}],
                "kept_assets": [],
                "blobs_deleted": 2,
                "bytes_freed": 2048,
            }

        monkeypatch.setattr("runicorn.assets.cleanup.delete_run_completely", fake_delete_run_completely)

        result = main([
            "delete",
            "--storage", str(tmp_path),
            "--run-id", "run-1",
            "--dry-run",
        ])

        assert result == 0
        output = capsys.readouterr().out
        assert "DRY RUN - No files will be deleted" in output
        assert "Deleting run: run-1" in output
        assert "Space: 2.0 KB" in output
