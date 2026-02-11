"""
Tests for Content-Addressable Storage (CAS) deduplication.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from runicorn.assets.archive import archive_dir, archive_file
from runicorn.assets.blob_store import get_blob_path, blob_exists, get_blob_stats
from runicorn.assets.restore import (
    load_manifest,
    restore_from_manifest,
    export_manifest_to_zip,
)


@pytest.fixture
def storage_root(tmp_path: Path) -> Path:
    """Create a temporary storage root."""
    root = tmp_path / "storage"
    root.mkdir()
    return root


@pytest.fixture
def sample_dir(tmp_path: Path) -> Path:
    """Create a sample directory with files."""
    d = tmp_path / "sample"
    d.mkdir()
    (d / "file1.txt").write_text("hello world")
    (d / "file2.txt").write_text("test data")
    (d / "subdir").mkdir()
    (d / "subdir" / "file3.txt").write_text("nested content")
    return d


class TestBlobStore:
    """Tests for blob store operations."""

    def test_archive_file_stores_to_blob(self, storage_root: Path, tmp_path: Path) -> None:
        """Single file archive should store to blobs directory."""
        src = tmp_path / "test.txt"
        src.write_text("hello world")
        
        result = archive_file(src, storage_root / "archive", category="test")
        
        assert result["fingerprint_kind"] == "sha256"
        assert result["fingerprint"]
        assert "blobs" in result["archive_path"]
        
        # Verify blob exists
        blob_root = storage_root / "archive" / "blobs"
        assert blob_exists(result["fingerprint"], blob_root)

    def test_archive_file_deduplication(self, storage_root: Path, tmp_path: Path) -> None:
        """Same content should not be stored twice."""
        src1 = tmp_path / "file1.txt"
        src2 = tmp_path / "file2.txt"
        src1.write_text("identical content")
        src2.write_text("identical content")
        
        result1 = archive_file(src1, storage_root / "archive", category="test")
        result2 = archive_file(src2, storage_root / "archive", category="test")
        
        # Same fingerprint
        assert result1["fingerprint"] == result2["fingerprint"]
        # Same archive path
        assert result1["archive_path"] == result2["archive_path"]
        
        # Only one blob stored
        stats = get_blob_stats(storage_root / "archive" / "blobs")
        assert stats["blob_count"] == 1


class TestDirectoryArchive:
    """Tests for directory archive with CAS."""

    def test_archive_dir_creates_manifest(self, storage_root: Path, sample_dir: Path) -> None:
        """Directory archive should create manifest and store files to blobs."""
        result = archive_dir(sample_dir, storage_root / "archive", category="datasets")
        
        assert result["fingerprint_kind"] == "sha256_manifest"
        assert result["fingerprint"]
        assert result["file_count"] == 3
        assert result["archive_path"].endswith(".json")
        
        # Verify manifest exists
        manifest_path = Path(result["archive_path"])
        assert manifest_path.exists()
        
        # Verify manifest content
        manifest = load_manifest(manifest_path)
        assert manifest["file_count"] == 3
        assert "file1.txt" in manifest["files"]
        assert "subdir/file3.txt" in manifest["files"]

    def test_archive_dir_stores_files_to_blobs(self, storage_root: Path, sample_dir: Path) -> None:
        """All files should be stored in blob store."""
        result = archive_dir(sample_dir, storage_root / "archive", category="datasets")
        
        blob_root = storage_root / "archive" / "blobs"
        manifest = load_manifest(Path(result["archive_path"]))
        
        # All files should have blobs
        for rel_path, entry in manifest["files"].items():
            assert blob_exists(entry["sha256"], blob_root), f"Blob missing for {rel_path}"

    def test_archive_dir_deduplication_same_dir(self, storage_root: Path, sample_dir: Path) -> None:
        """Archiving same directory twice should not duplicate storage."""
        result1 = archive_dir(sample_dir, storage_root / "archive", category="datasets")
        result2 = archive_dir(sample_dir, storage_root / "archive", category="datasets")
        
        # Same fingerprint and path
        assert result1["fingerprint"] == result2["fingerprint"]
        assert result1["archive_path"] == result2["archive_path"]
        
        # Only 3 blobs (one per unique file)
        stats = get_blob_stats(storage_root / "archive" / "blobs")
        assert stats["blob_count"] == 3

    def test_archive_dir_deduplication_shared_files(self, storage_root: Path, tmp_path: Path) -> None:
        """Two directories with shared files should deduplicate at file level."""
        # Create two directories with overlapping content
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        
        # Shared files (same content)
        (dir1 / "shared.txt").write_text("shared content")
        (dir2 / "shared.txt").write_text("shared content")
        
        # Unique files
        (dir1 / "unique1.txt").write_text("only in dir1")
        (dir2 / "unique2.txt").write_text("only in dir2")
        
        result1 = archive_dir(dir1, storage_root / "archive", category="datasets")
        result2 = archive_dir(dir2, storage_root / "archive", category="datasets")
        
        # Different manifests (different directory structure)
        assert result1["fingerprint"] != result2["fingerprint"]
        
        # But only 3 unique blobs (shared.txt is deduplicated)
        stats = get_blob_stats(storage_root / "archive" / "blobs")
        assert stats["blob_count"] == 3  # shared + unique1 + unique2


class TestRestore:
    """Tests for restore operations."""

    def test_restore_from_manifest(self, storage_root: Path, sample_dir: Path, tmp_path: Path) -> None:
        """Should restore directory from manifest."""
        result = archive_dir(sample_dir, storage_root / "archive", category="datasets")
        
        target = tmp_path / "restored"
        blob_root = storage_root / "archive" / "blobs"
        
        restore_result = restore_from_manifest(
            Path(result["archive_path"]),
            blob_root,
            target,
        )
        
        assert restore_result["restored_count"] == 3
        assert (target / "file1.txt").read_text() == "hello world"
        assert (target / "file2.txt").read_text() == "test data"
        assert (target / "subdir" / "file3.txt").read_text() == "nested content"

    def test_export_to_zip(self, storage_root: Path, sample_dir: Path, tmp_path: Path) -> None:
        """Should export manifest to zip file."""
        result = archive_dir(sample_dir, storage_root / "archive", category="datasets")
        
        zip_path = tmp_path / "export.zip"
        blob_root = storage_root / "archive" / "blobs"
        
        export_result = export_manifest_to_zip(
            Path(result["archive_path"]),
            blob_root,
            zip_path,
        )
        
        assert export_result["exported_count"] == 3
        assert zip_path.exists()
        
        # Verify zip content
        import zipfile
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "file1.txt" in names
            assert "subdir/file3.txt" in names
