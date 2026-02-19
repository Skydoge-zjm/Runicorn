"""Tests for runicorn.workspace — workspace root resolution."""
from __future__ import annotations

from pathlib import Path

import pytest

from runicorn.workspace import get_workspace_root


class TestGetWorkspaceRoot:
    def test_get_workspace_root_explicit(self, tmp_path: Path):
        """Explicit workspace_root is returned as-is (resolved)."""
        target = tmp_path / "my_project"
        target.mkdir()
        result = get_workspace_root(str(target))
        assert result == target.resolve()

    def test_get_workspace_root_finds_git(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """When cwd is inside a .git repo, the repo root is returned."""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        sub = repo / "src" / "pkg"
        sub.mkdir(parents=True)

        monkeypatch.chdir(sub)
        result = get_workspace_root()
        assert result == repo.resolve()

    def test_get_workspace_root_fallback_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """No .git anywhere → fallback to cwd."""
        no_git = tmp_path / "no_git_here"
        no_git.mkdir()
        monkeypatch.chdir(no_git)
        result = get_workspace_root()
        assert result == no_git.resolve()
