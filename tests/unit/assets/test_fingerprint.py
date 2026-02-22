"""Unit tests for runicorn.assets.fingerprint."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from runicorn.assets.fingerprint import (
    content_fingerprint,
    dir_stat_fingerprint,
    sha256_bytes,
    sha256_file,
    stat_fingerprint,
)


class TestStatFingerprint:
    """stat_fingerprint — same/different file produce same/different results."""

    def test_same_file_same_fingerprint(self, tmp_path: Path):
        f = tmp_path / "a.txt"
        f.write_text("hello")
        fp1 = stat_fingerprint(f)
        fp2 = stat_fingerprint(f)
        assert fp1 == fp2

    def test_different_file_different_fingerprint(self, tmp_path: Path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("hello")
        b.write_text("world" * 100)
        assert stat_fingerprint(a) != stat_fingerprint(b)

    def test_returns_size_and_mtime(self, tmp_path: Path):
        f = tmp_path / "x.bin"
        f.write_bytes(b"\x00" * 42)
        fp = stat_fingerprint(f)
        assert fp["size_bytes"] == 42
        assert isinstance(fp["mtime"], float)


class TestDirStatFingerprint:
    """dir_stat_fingerprint — deterministic for same dir."""

    def test_deterministic(self, tmp_path: Path):
        d = tmp_path / "mydir"
        d.mkdir()
        (d / "a.txt").write_text("aa")
        (d / "b.txt").write_text("bb")

        fp1 = dir_stat_fingerprint(d)
        fp2 = dir_stat_fingerprint(d)
        assert fp1 == fp2
        assert fp1["file_count"] == 2
        assert fp1["total_size_bytes"] == 4

    def test_empty_dir(self, tmp_path: Path):
        d = tmp_path / "empty"
        d.mkdir()
        fp = dir_stat_fingerprint(d)
        assert fp["file_count"] == 0
        assert fp["total_size_bytes"] == 0


class TestSha256:
    """sha256_file and sha256_bytes."""

    def test_file_hash_deterministic(self, tmp_path: Path):
        f = tmp_path / "data.bin"
        f.write_bytes(b"deterministic content")
        h1 = sha256_file(f)
        h2 = sha256_file(f)
        assert h1 == h2
        assert len(h1) == 64  # hex digest

    def test_bytes_matches_file(self, tmp_path: Path):
        data = b"same content"
        f = tmp_path / "c.bin"
        f.write_bytes(data)
        assert sha256_file(f) == sha256_bytes(data)

    def test_content_fingerprint(self, tmp_path: Path):
        f = tmp_path / "f.txt"
        f.write_text("abc")
        kind, digest = content_fingerprint(f)
        assert kind == "sha256"
        assert digest == sha256_file(f)

    def test_content_fingerprint_dir_raises(self, tmp_path: Path):
        with pytest.raises(ValueError, match="files only"):
            content_fingerprint(tmp_path)
