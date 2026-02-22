"""Unit tests for runicorn.assets.ignore."""
from __future__ import annotations

from pathlib import Path

from runicorn.assets.ignore import (
    IgnoreMatcher,
    IgnoreRule,
    _parse_ignore_lines,
    ensure_rnignore,
    load_ignore_matcher,
)


class TestParseIgnoreLines:
    """_parse_ignore_lines handles comments, negation, anchoring, dir-only."""

    def test_basic_patterns(self):
        rules = _parse_ignore_lines(["*.pyc", "__pycache__/", "# comment", ""])
        assert len(rules) == 2
        assert rules[0] == IgnoreRule(pattern="*.pyc", negated=False, anchored=False, dir_only=False)
        assert rules[1] == IgnoreRule(pattern="__pycache__", negated=False, anchored=False, dir_only=True)

    def test_negation_and_anchored(self):
        rules = _parse_ignore_lines(["!important.log", "/root_only"])
        assert rules[0].negated is True
        assert rules[0].pattern == "important.log"
        assert rules[1].anchored is True
        assert rules[1].pattern == "root_only"


class TestIgnoreMatcher:
    """IgnoreMatcher.is_ignored — pattern matching logic."""

    def test_matches_glob(self):
        rules = _parse_ignore_lines(["*.pyc", "__pycache__/"])
        m = IgnoreMatcher(rules)
        assert m.is_ignored("foo.pyc", is_dir=False) is True
        assert m.is_ignored("src/foo.pyc", is_dir=False) is True
        assert m.is_ignored("foo.py", is_dir=False) is False

    def test_dir_only_rule(self):
        rules = _parse_ignore_lines(["__pycache__/"])
        m = IgnoreMatcher(rules)
        assert m.is_ignored("__pycache__", is_dir=True) is True
        assert m.is_ignored("__pycache__", is_dir=False) is False

    def test_negation_overrides(self):
        rules = _parse_ignore_lines(["*.log", "!important.log"])
        m = IgnoreMatcher(rules)
        assert m.is_ignored("debug.log", is_dir=False) is True
        assert m.is_ignored("important.log", is_dir=False) is False


class TestLoadIgnoreMatcher:
    """load_ignore_matcher reads .gitignore + .rnignore."""

    def test_no_files_empty_matcher(self, tmp_path: Path):
        m = load_ignore_matcher(tmp_path)
        assert m.is_ignored("anything.txt", is_dir=False) is False

    def test_reads_both_ignore_files(self, tmp_path: Path):
        (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
        (tmp_path / ".rnignore").write_text("*.tmp\n", encoding="utf-8")
        m = load_ignore_matcher(tmp_path)
        assert m.is_ignored("debug.log", is_dir=False) is True
        assert m.is_ignored("cache.tmp", is_dir=False) is True
        assert m.is_ignored("main.py", is_dir=False) is False


class TestEnsureRnignore:
    """ensure_rnignore creates default .rnignore if missing."""

    def test_creates_default(self, tmp_path: Path):
        path = ensure_rnignore(tmp_path)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "__pycache__/" in content
        assert ".git/" in content

    def test_no_overwrite_existing(self, tmp_path: Path):
        existing = tmp_path / ".rnignore"
        existing.write_text("custom\n", encoding="utf-8")
        path = ensure_rnignore(tmp_path)
        assert path.read_text(encoding="utf-8") == "custom\n"
