"""
Unit tests for run deletion with asset cleanup.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


class TestIndexDbQueries:
    """Test IndexDb query and delete methods."""

    def test_get_assets_for_run(self, tmp_path: Path) -> None:
        """Test querying assets for a run."""
        from runicorn.index import IndexDb

        db = IndexDb(tmp_path)

        # Create a run
        db.upsert_run(
            run_id="run1",
            project="proj",
            name="exp",
            created_at=1000.0,
            status="finished",
            run_dir=str(tmp_path / "runs" / "run1"),
            workspace_root=str(tmp_path),
        )

        # Record some assets
        db.record_asset_for_run(
            run_id="run1",
            role="dataset",
            asset_type="dataset",
            name="ds1",
            source_uri="/data/ds1",
            archive_uri=None,
            is_archived=False,
            fingerprint_kind="stat",
            fingerprint="fp1",
        )
        db.record_asset_for_run(
            run_id="run1",
            role="pretrained",
            asset_type="pretrained",
            name="model1",
            source_uri="/models/m1",
            archive_uri=str(tmp_path / "archive" / "m1.zip"),
            is_archived=True,
            fingerprint_kind="sha256",
            fingerprint="abc123",
        )

        assets = db.get_assets_for_run("run1")
        assert len(assets) == 2
        names = {a["name"] for a in assets}
        assert names == {"ds1", "model1"}

        db.close()

    def test_get_runs_for_asset(self, tmp_path: Path) -> None:
        """Test querying runs that reference an asset."""
        from runicorn.index import IndexDb

        db = IndexDb(tmp_path)

        # Create two runs
        for i in [1, 2]:
            db.upsert_run(
                run_id=f"run{i}",
                project="proj",
                name="exp",
                created_at=1000.0 + i,
                status="finished",
                run_dir=str(tmp_path / "runs" / f"run{i}"),
                workspace_root=str(tmp_path),
            )

        # Both runs reference the same dataset
        for run_id in ["run1", "run2"]:
            db.record_asset_for_run(
                run_id=run_id,
                role="dataset",
                asset_type="dataset",
                name="shared_ds",
                source_uri="/data/shared",
                archive_uri=None,
                is_archived=False,
                fingerprint_kind="stat",
                fingerprint="shared_fp",
            )

        # Get the asset_id
        assets = db.get_assets_for_run("run1")
        asset_id = assets[0]["asset_id"]

        runs = db.get_runs_for_asset(asset_id)
        assert set(runs) == {"run1", "run2"}

        db.close()

    def test_get_asset_ref_count(self, tmp_path: Path) -> None:
        """Test counting asset references."""
        from runicorn.index import IndexDb

        db = IndexDb(tmp_path)

        # Create three runs
        for i in [1, 2, 3]:
            db.upsert_run(
                run_id=f"run{i}",
                project="proj",
                name="exp",
                created_at=1000.0 + i,
                status="finished",
                run_dir=str(tmp_path / "runs" / f"run{i}"),
                workspace_root=str(tmp_path),
            )

        # All three runs reference the same asset
        for run_id in ["run1", "run2", "run3"]:
            db.record_asset_for_run(
                run_id=run_id,
                role="dataset",
                asset_type="dataset",
                name="popular_ds",
                source_uri="/data/popular",
                archive_uri=None,
                is_archived=False,
                fingerprint_kind="stat",
                fingerprint="popular_fp",
            )

        assets = db.get_assets_for_run("run1")
        asset_id = assets[0]["asset_id"]

        ref_count = db.get_asset_ref_count(asset_id)
        assert ref_count == 3

        db.close()

    def test_delete_run_with_orphan_assets(self, tmp_path: Path) -> None:
        """Test deleting a run and identifying orphaned assets."""
        from runicorn.index import IndexDb

        db = IndexDb(tmp_path)

        # Create two runs
        for i in [1, 2]:
            db.upsert_run(
                run_id=f"run{i}",
                project="proj",
                name="exp",
                created_at=1000.0 + i,
                status="finished",
                run_dir=str(tmp_path / "runs" / f"run{i}"),
                workspace_root=str(tmp_path),
            )

        # Shared asset (both runs)
        for run_id in ["run1", "run2"]:
            db.record_asset_for_run(
                run_id=run_id,
                role="dataset",
                asset_type="dataset",
                name="shared_ds",
                source_uri="/data/shared",
                archive_uri=None,
                is_archived=False,
                fingerprint_kind="stat",
                fingerprint="shared_fp",
            )

        # Unique asset (only run1)
        db.record_asset_for_run(
            run_id="run1",
            role="config",
            asset_type="config",
            name="run1_config",
            source_uri=None,
            archive_uri=None,
            is_archived=False,
            fingerprint_kind=None,
            fingerprint=None,
        )

        # Delete run1
        result = db.delete_run_with_orphan_assets("run1")

        orphaned = result["orphaned_assets"]
        kept = result["kept_assets"]

        # Config should be orphaned (only run1 had it)
        assert len(orphaned) == 1
        assert orphaned[0]["name"] == "run1_config"

        # Shared dataset should be kept (run2 still references it)
        assert len(kept) == 1
        assert kept[0]["name"] == "shared_ds"

        # Verify run1 is deleted
        assert db.get_run("run1") is None

        # Verify run2 still exists
        assert db.get_run("run2") is not None

        # Verify shared asset still exists
        run2_assets = db.get_assets_for_run("run2")
        assert len(run2_assets) == 1
        assert run2_assets[0]["name"] == "shared_ds"

        db.close()


class TestDeleteRunCompletely:
    """Test the complete run deletion with file cleanup."""

    def test_delete_run_removes_directory(self, tmp_path: Path) -> None:
        """Test that run directory is deleted."""
        from runicorn.assets.cleanup import delete_run_completely

        storage_root = tmp_path / "storage"
        storage_root.mkdir()

        # Create run directory structure
        run_dir = storage_root / "proj" / "exp" / "runs" / "20240101_120000_abc123"
        run_dir.mkdir(parents=True)
        (run_dir / "meta.json").write_text('{"project": "proj", "name": "exp"}')
        (run_dir / "status.json").write_text('{"status": "finished"}')

        # Create index
        from runicorn.index import IndexDb
        db = IndexDb(storage_root)
        db.upsert_run(
            run_id="20240101_120000_abc123",
            project="proj",
            name="exp",
            created_at=1000.0,
            status="finished",
            run_dir=str(run_dir),
            workspace_root=str(tmp_path),
        )
        db.close()

        result = delete_run_completely(
            run_id="20240101_120000_abc123",
            storage_root=storage_root,
            dry_run=False,
        )

        assert result["success"]
        assert result["run_dir_deleted"]
        assert not run_dir.exists()

    def test_delete_run_dry_run(self, tmp_path: Path) -> None:
        """Test dry run mode doesn't delete anything."""
        from runicorn.assets.cleanup import delete_run_completely

        storage_root = tmp_path / "storage"
        storage_root.mkdir()

        # Create run directory
        run_dir = storage_root / "proj" / "exp" / "runs" / "20240101_120000_abc123"
        run_dir.mkdir(parents=True)
        (run_dir / "meta.json").write_text('{"project": "proj", "name": "exp"}')
        (run_dir / "status.json").write_text('{"status": "finished"}')

        # Create index
        from runicorn.index import IndexDb
        db = IndexDb(storage_root)
        db.upsert_run(
            run_id="20240101_120000_abc123",
            project="proj",
            name="exp",
            created_at=1000.0,
            status="finished",
            run_dir=str(run_dir),
            workspace_root=str(tmp_path),
        )
        db.close()

        result = delete_run_completely(
            run_id="20240101_120000_abc123",
            storage_root=storage_root,
            dry_run=True,
        )

        assert result["success"]
        assert result["run_dir_deleted"]  # Would be deleted
        assert run_dir.exists()  # But still exists

    def test_delete_run_not_found(self, tmp_path: Path) -> None:
        """Test deleting non-existent run."""
        from runicorn.assets.cleanup import delete_run_completely

        storage_root = tmp_path / "storage"
        storage_root.mkdir()

        result = delete_run_completely(
            run_id="nonexistent",
            storage_root=storage_root,
            dry_run=False,
        )

        assert not result["success"]
        assert "not found" in result["errors"][0].lower()
