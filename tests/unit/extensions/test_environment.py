"""Unit tests for runicorn.extensions.environment."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from runicorn.extensions.environment import EnvironmentCapture


class TestGetGitInfo:
    """EnvironmentCapture.get_git_info — mocked subprocess."""

    def test_returns_git_info(self, tmp_path: Path):
        cap = EnvironmentCapture(tmp_path)

        def _mock_run(args, **kwargs):
            m = MagicMock(returncode=0)
            cmd = " ".join(args)
            if "--is-inside-work-tree" in cmd:
                m.stdout = "true\n"
            elif "rev-parse HEAD" in cmd:
                m.stdout = "abc1234\n"
            elif "--abbrev-ref HEAD" in cmd:
                m.stdout = "main\n"
            elif "--porcelain" in cmd:
                m.stdout = ""
            elif "get-url" in cmd:
                m.stdout = "https://example.com/repo.git\n"
            elif "--pretty=%B" in cmd:
                m.stdout = "initial commit\n"
            elif "--pretty=%an" in cmd:
                m.stdout = "Alice <a@b.com>\n"
            else:
                m.stdout = ""
            return m

        with patch("runicorn.extensions.environment.subprocess.run", side_effect=_mock_run):
            info = cap.get_git_info()

        assert info is not None
        assert info["commit"] == "abc1234"
        assert info["branch"] == "main"

    def test_no_git_returns_none(self, tmp_path: Path):
        cap = EnvironmentCapture(tmp_path)
        mock_result = MagicMock(returncode=128, stdout="", stderr="not a git repo")

        with patch("runicorn.extensions.environment.subprocess.run", return_value=mock_result):
            assert cap.get_git_info() is None


class TestGetPipPackages:
    """EnvironmentCapture.get_pip_packages — mocked subprocess."""

    def test_returns_packages(self, tmp_path: Path):
        cap = EnvironmentCapture(tmp_path)
        mock_result = MagicMock(returncode=0, stdout="torch==2.0\nnumpy==1.24\n")

        with patch("runicorn.extensions.environment.subprocess.run", return_value=mock_result):
            pkgs = cap.get_pip_packages()

        assert pkgs == ["torch==2.0", "numpy==1.24"]

    def test_failure_returns_none(self, tmp_path: Path):
        cap = EnvironmentCapture(tmp_path)

        with patch(
            "runicorn.extensions.environment.subprocess.run",
            side_effect=subprocess.SubprocessError("timeout"),
        ):
            assert cap.get_pip_packages() is None


class TestGetPlatformDetails:
    """EnvironmentCapture.get_platform_details — no mocking needed."""

    def test_returns_expected_keys(self):
        cap = EnvironmentCapture()
        details = cap.get_platform_details()
        assert "system" in details
        assert "machine" in details
        assert "python_implementation" in details
