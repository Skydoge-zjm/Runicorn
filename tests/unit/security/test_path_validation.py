"""Unit tests for runicorn.security.path_validation."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from runicorn.security.path_validation import (
    create_safe_directory,
    sanitize_filename,
    validate_path,
)


# ---------------------------------------------------------------------------
# validate_path
# ---------------------------------------------------------------------------

class TestValidatePathNormal:
    """test_validate_path_normal — valid relative paths pass validation."""

    def test_simple_relative(self, tmp_path: Path):
        ok, resolved, err = validate_path("subdir/file.txt", tmp_path)
        assert ok is True
        assert resolved is not None
        assert err is None
        assert resolved == (tmp_path / "subdir" / "file.txt").resolve()

    def test_single_filename(self, tmp_path: Path):
        ok, resolved, err = validate_path("data.json", tmp_path)
        assert ok is True
        assert resolved == (tmp_path / "data.json").resolve()


class TestValidatePathTraversal:
    """test_validate_path_traversal_attack — '..' paths are rejected."""

    def test_dotdot_prefix(self, tmp_path: Path):
        ok, _, err = validate_path("../etc/passwd", tmp_path)
        assert ok is False
        assert err is not None

    def test_dotdot_embedded(self, tmp_path: Path):
        ok, _, err = validate_path("sub/../../../etc", tmp_path)
        assert ok is False
        assert err is not None

    def test_absolute_unix(self, tmp_path: Path):
        ok, _, err = validate_path("/etc/passwd", tmp_path)
        assert ok is False

    def test_forbidden_chars(self, tmp_path: Path):
        ok, _, err = validate_path("file<name>.txt", tmp_path)
        assert ok is False
        assert "forbidden" in (err or "").lower()

    def test_null_byte(self, tmp_path: Path):
        ok, _, err = validate_path("file\x00name", tmp_path)
        assert ok is False

    def test_long_path_rejected(self, tmp_path: Path):
        long_name = "a" * 250
        ok, _, err = validate_path(long_name, tmp_path)
        # The resolved path will be > 240 chars
        assert ok is False
        assert "long" in (err or "").lower()


class TestValidatePathSymlink:
    """test_validate_path_symlink — symlinks blocked by default, allowed if configured."""

    @pytest.mark.skipif(os.name == "nt", reason="symlink requires privileges on Windows")
    def test_symlink_rejected(self, tmp_path: Path):
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        link = tmp_path / "link"
        link.symlink_to(real_dir)

        ok, _, err = validate_path("link/file.txt", tmp_path, allow_symlinks=False)
        assert ok is False
        assert "symbolic" in (err or "").lower()

    @pytest.mark.skipif(os.name == "nt", reason="symlink requires privileges on Windows")
    def test_symlink_allowed(self, tmp_path: Path):
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        link = tmp_path / "link"
        link.symlink_to(real_dir)

        ok, resolved, err = validate_path("link/file.txt", tmp_path, allow_symlinks=True)
        assert ok is True


# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------

class TestSanitizeFilename:
    """test_sanitize_filename — special characters removed, safe output."""

    def test_normal_filename(self):
        assert sanitize_filename("report.csv") == "report.csv"

    def test_special_chars_replaced(self):
        result = sanitize_filename("my<file>:name?.txt")
        assert "<" not in result
        assert ">" not in result
        assert "?" not in result

    def test_spaces_to_dashes(self):
        result = sanitize_filename("my file name.txt")
        assert " " not in result

    def test_empty_becomes_unnamed(self):
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("***") == "unnamed"

    def test_unicode_normalized(self):
        result = sanitize_filename("café_résumé.pdf")
        # Non-ASCII stripped, but base chars survive
        assert result.endswith(".pdf")

    def test_truncation_preserves_extension(self):
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name, max_length=20)
        assert len(result) <= 20
        assert result.endswith(".txt")


class TestSanitizeWindowsReserved:
    """test_sanitize_windows_reserved — CON, PRN, NUL etc. prefixed with '_'."""

    @pytest.mark.parametrize("name", ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"])
    def test_reserved_name_prefixed(self, name: str):
        result = sanitize_filename(name)
        assert result.startswith("_")

    @pytest.mark.parametrize("name", ["CON.txt", "NUL.log"])
    def test_reserved_with_extension(self, name: str):
        result = sanitize_filename(name)
        assert result.startswith("_")

    def test_non_reserved_unchanged(self):
        result = sanitize_filename("CONSOLE.txt")
        assert not result.startswith("_")


# ---------------------------------------------------------------------------
# create_safe_directory
# ---------------------------------------------------------------------------

class TestCreateSafeDirectory:
    """test_create_safe_directory — safe creation within base dir."""

    def test_creates_subdirectory(self, tmp_path: Path):
        result = create_safe_directory(tmp_path, "runs/exp1")
        assert result is not None
        assert result.exists()
        assert result.is_dir()

    def test_traversal_rejected(self, tmp_path: Path):
        result = create_safe_directory(tmp_path, "../escape")
        assert result is None

    def test_exist_ok(self, tmp_path: Path):
        sub = tmp_path / "existing"
        sub.mkdir()
        result = create_safe_directory(tmp_path, "existing", exist_ok=True)
        assert result is not None

    def test_nested_creation(self, tmp_path: Path):
        result = create_safe_directory(tmp_path, "a/b/c/d")
        assert result is not None
        assert result.exists()
