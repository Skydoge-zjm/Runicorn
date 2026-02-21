"""E2E: CLI subcommand smoke tests."""
from __future__ import annotations

import subprocess
import sys

import pytest


def _run_cli(*args: str, timeout: int = 15) -> subprocess.CompletedProcess:
    """Run runicorn CLI via python -m."""
    return subprocess.run(
        [sys.executable, "-m", "runicorn.cli", *args],
        capture_output=True, text=True, timeout=timeout,
    )


class TestCliCommands:
    """Smoke test: each subcommand runs without crashing."""

    def test_config_show(self):
        r = _run_cli("config", "--show")
        assert r.returncode == 0
        assert "runicorn" in r.stdout.lower() or "config" in r.stdout.lower()

    def test_help(self):
        r = _run_cli("--help")
        assert r.returncode == 0
        assert "usage" in r.stdout.lower() or "runicorn" in r.stdout.lower()

    def test_export_no_runs(self, tmp_path):
        """export with empty storage returns 0."""
        r = _run_cli("export", "--storage", str(tmp_path))
        assert r.returncode == 0

    def test_unknown_subcommand(self):
        r = _run_cli("nonexistent_subcommand_xyz")
        assert r.returncode != 0
