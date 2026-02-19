"""Unit tests for runicorn.assets.archive."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from runicorn.assets.archive import archive_dir, archive_file, archive_file_overwrite
from runicorn.assets.blob_store import blob_exists, get_blob_path
from runicorn.assets.fingerprint import sha256_file


class TestArchiveFile:
    """archive_file stores blob and returns fingerprint."""

    def test_stores_blob_by_sha256(self, tmp_path: Path):
        src = tmp_path / "data.txt"
        src.write_text("hello blob")
        archive_root = tmp_path / "archive"

        result = archive_file(src, archive_root, category="code")

        assert result["fingerprint_kind"] == "sha256"
        sha = result["fingerprint"]
        assert sha == sha256_file(src)
        assert blob_exists(sha, archive_root / "blobs")
        # blob content matches
        blob = get_blob_path(sha, archive_root / "blobs")
        assert blob.read_bytes() == src.read_bytes()

    def test_dedup_skips_existing(self, tmp_path: Path):
        """Same content archived twice → blob written once (dedup)."""
        archive_root = tmp_path / "archive"
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("same content")
        b.write_text("same content")

        r1 = archive_file(a, archive_root, category="c")
        blob_path = get_blob_path(r1["fingerprint"], archive_root / "blobs")
        mtime_after_first = blob_path.stat().st_mtime

        r2 = archive_file(b, archive_root, category="c")
        assert r1["fingerprint"] == r2["fingerprint"]
        # blob not overwritten — mtime unchanged
        assert blob_path.stat().st_mtime == mtime_after_first


class TestArchiveDir:
    """archive_dir stores all files and creates manifest."""

    def test_creates_manifest(self, tmp_path: Path):
        src = tmp_path / "mydir"
        src.mkdir()
        (src / "a.txt").write_text("aaa")
        (src / "sub").mkdir()
        (src / "sub" / "b.txt").write_text("bbb")

        archive_root = tmp_path / "archive"
        result = archive_dir(src, archive_root, category="datasets")

        assert result["fingerprint_kind"] == "sha256_manifest"
        assert result["file_count"] == 2
        manifest_path = Path(result["manifest_path"])
        assert manifest_path.exists()

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "a.txt" in manifest["files"]
        assert "sub/b.txt" in manifest["files"]


class TestArchiveFileOverwrite:
    """archive_file_overwrite in rolling mode."""

    def test_overwrites_previous(self, tmp_path: Path):
        archive_root = tmp_path / "archive"
        src = tmp_path / "ckpt.pth"

        src.write_text("v1")
        r1 = archive_file_overwrite(
            src, archive_root, category="outputs", run_id="run-1", key="last"
        )
        dst = Path(r1["archive_path"])
        assert dst.read_text() == "v1"

        src.write_text("v2")
        r2 = archive_file_overwrite(
            src, archive_root, category="outputs", run_id="run-1", key="last"
        )
        # Same path, new content
        dst2 = Path(r2["archive_path"])
        assert dst2.read_text() == "v2"
        assert r1["archive_path"] == r2["archive_path"]
