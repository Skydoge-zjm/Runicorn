"""Integration tests for assets/cleanup.py — delete_run_completely."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from runicorn.storage.backends import SQLiteStorageBackend
from runicorn.storage.models import ExperimentRecord


def _create_run(storage_root: Path, backend: SQLiteStorageBackend, run_id: str, path: str = "cleanup/test") -> Path:
    """Create a run on disk and register in SQLite."""
    run_dir = storage_root / "runs" / path.replace("/", os.sep) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    now = time.time()
    (run_dir / "meta.json").write_text(
        json.dumps({"id": run_id, "path": path, "created_at": now}), encoding="utf-8"
    )
    (run_dir / "status.json").write_text(
        json.dumps({"status": "finished"}), encoding="utf-8"
    )

    exp = ExperimentRecord(
        id=run_id, path=path, created_at=now, updated_at=now,
        status="finished", pid=99999, run_dir=str(run_dir),
    )
    backend.create_experiment(exp)
    return run_dir


class TestDeleteRunCompletely:

    def test_deletes_run_dir_and_sqlite(self, tmp_path: Path) -> None:
        storage = tmp_path / "storage"
        (storage / "runs").mkdir(parents=True)
        backend = SQLiteStorageBackend(storage)
        try:
            run_id = "20250601_000000_delete"
            run_dir = _create_run(storage, backend, run_id)
            assert run_dir.exists()
            assert backend.get_experiment(run_id) is not None
            backend.close()

            from runicorn.assets.cleanup import delete_run_completely
            result = delete_run_completely(run_id, storage)

            assert result["success"] is True
            assert result["run_dir_deleted"] is True
            assert not run_dir.exists()
        finally:
            pass  # backend already closed above

    def test_dry_run_does_not_delete(self, tmp_path: Path) -> None:
        storage = tmp_path / "storage"
        (storage / "runs").mkdir(parents=True)
        backend = SQLiteStorageBackend(storage)
        try:
            run_id = "20250602_000000_dryrun"
            run_dir = _create_run(storage, backend, run_id)
            backend.close()

            from runicorn.assets.cleanup import delete_run_completely
            result = delete_run_completely(run_id, storage, dry_run=True)

            assert result["success"] is True
            # Dry run should NOT delete the directory
            assert run_dir.exists()
        finally:
            pass

    def test_nonexistent_run_returns_error(self, tmp_path: Path) -> None:
        storage = tmp_path / "storage"
        (storage / "runs").mkdir(parents=True)

        from runicorn.assets.cleanup import delete_run_completely
        result = delete_run_completely("20250603_000000_nope", storage)

        assert result["success"] is False
        assert len(result["errors"]) >= 1


class TestDeleteAssetBlobs:

    def test_deletes_stat_fingerprint_blob_under_blob_root(self, tmp_path: Path) -> None:
        from runicorn.assets.cleanup import _delete_asset_blobs

        blob_root = tmp_path / "archive" / "blobs"
        manifest_root = tmp_path / "archive" / "manifests"
        blob_path = blob_root / "ab" / "cd" / "sample.bin"
        blob_path.parent.mkdir(parents=True, exist_ok=True)
        blob_path.write_bytes(b"blob-data")

        deleted, freed, errors = _delete_asset_blobs(
            {
                "archive_uri": str(blob_path),
                "fingerprint": "stat:123:456",
                "asset_type": "output",
            },
            blob_root,
            manifest_root,
            dry_run=False,
        )

        assert deleted == 1
        assert freed == len(b"blob-data")
        assert errors == []
        assert not blob_path.exists()

    def test_does_not_delete_sibling_of_blob_root(self, tmp_path: Path) -> None:
        from runicorn.assets.cleanup import _delete_asset_blobs

        blob_root = tmp_path / "archive" / "blobs"
        manifest_root = tmp_path / "archive" / "manifests"
        sibling_path = tmp_path / "archive" / "blobs_extra" / "ab" / "cd" / "sample.bin"
        sibling_path.parent.mkdir(parents=True, exist_ok=True)
        sibling_path.write_bytes(b"blob-data")

        deleted, freed, errors = _delete_asset_blobs(
            {
                "archive_uri": str(sibling_path),
                "fingerprint": "stat:123:456",
                "asset_type": "output",
            },
            blob_root,
            manifest_root,
            dry_run=False,
        )

        assert deleted == 0
        assert freed == 0
        assert errors == []
        assert sibling_path.exists()
