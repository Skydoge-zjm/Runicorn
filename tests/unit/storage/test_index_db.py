"""Tests for runicorn.storage.index_db (legacy compatibility layer)."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from runicorn.storage.index_db import IndexDb


class TestIndexDbSchema:

    def test_creates_tables(self, tmp_path: Path) -> None:
        db = IndexDb(tmp_path)
        conn = db._connect()
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"runs", "assets", "run_assets"}.issubset(tables)
        db.close()


class TestIndexDbRuns:

    def test_upsert_and_get_run(self, tmp_path: Path) -> None:
        db = IndexDb(tmp_path)
        db.upsert_run(
            run_id="r1", path="train/cifar", alias=None,
            created_at=time.time(), status="running",
            run_dir="/tmp/r1", workspace_root=None,
        )
        run = db.get_run("r1")
        assert run is not None
        assert run["path"] == "train/cifar"
        db.close()

    def test_finish_run(self, tmp_path: Path) -> None:
        db = IndexDb(tmp_path)
        db.upsert_run(
            run_id="r2", path="p", alias=None,
            created_at=time.time(), status="running",
            run_dir="/tmp/r2", workspace_root=None,
        )
        db.finish_run(run_id="r2", status="finished", ended_at=time.time())
        run = db.get_run("r2")
        assert run["status"] == "finished"
        db.close()

    def test_get_nonexistent_returns_none(self, tmp_path: Path) -> None:
        db = IndexDb(tmp_path)
        assert db.get_run("ghost") is None
        db.close()


class TestIndexDbAssets:

    def test_upsert_asset_dedup(self, tmp_path: Path) -> None:
        db = IndexDb(tmp_path)
        common = dict(
            asset_type="model", name="m", source_uri="/m",
            archive_uri=None, is_archived=False,
            fingerprint_kind="sha256", fingerprint="fp_dedup",
        )
        id1 = db.upsert_asset(**common)
        id2 = db.upsert_asset(**common)
        assert id1 == id2
        db.close()

    def test_link_and_get_assets_for_run(self, tmp_path: Path) -> None:
        db = IndexDb(tmp_path)
        db.upsert_run(
            run_id="r1", path="p", alias=None,
            created_at=time.time(), status="running",
            run_dir="/tmp/r1", workspace_root=None,
        )
        aid = db.upsert_asset(
            asset_type="data", name="d", source_uri="/d",
            archive_uri=None, is_archived=False,
            fingerprint_kind="md5", fingerprint="fp1",
        )
        db.link_run_asset(run_id="r1", asset_id=aid, role="input")

        assets = db.get_assets_for_run("r1")
        assert len(assets) == 1
        assert assets[0]["asset_id"] == aid
        db.close()

    def test_get_asset_ref_count(self, tmp_path: Path) -> None:
        db = IndexDb(tmp_path)
        for rid in ("r1", "r2"):
            db.upsert_run(
                run_id=rid, path="p", alias=None,
                created_at=time.time(), status="running",
                run_dir=f"/tmp/{rid}", workspace_root=None,
            )
        aid = db.upsert_asset(
            asset_type="data", name="d", source_uri="/d",
            archive_uri=None, is_archived=False,
            fingerprint_kind="md5", fingerprint="shared",
        )
        db.link_run_asset(run_id="r1", asset_id=aid, role="input")
        db.link_run_asset(run_id="r2", asset_id=aid, role="input")

        assert db.get_asset_ref_count(aid) == 2
        db.close()

    def test_get_asset_by_fingerprint(self, tmp_path: Path) -> None:
        db = IndexDb(tmp_path)
        db.upsert_asset(
            asset_type="model", name="m", source_uri="/m",
            archive_uri=None, is_archived=False,
            fingerprint_kind="sha256", fingerprint="unique",
        )
        assert db.get_asset_by_fingerprint("model", "unique") is not None
        assert db.get_asset_by_fingerprint("model", "nope") is None
        db.close()


class TestIndexDbDelete:

    def test_delete_run_with_orphan_assets(self, tmp_path: Path) -> None:
        db = IndexDb(tmp_path)
        db.upsert_run(
            run_id="r1", path="p", alias=None,
            created_at=time.time(), status="finished",
            run_dir="/tmp/r1", workspace_root=None,
        )
        aid = db.upsert_asset(
            asset_type="model", name="m", source_uri="/m",
            archive_uri=None, is_archived=False,
            fingerprint_kind="sha256", fingerprint="orp",
        )
        db.link_run_asset(run_id="r1", asset_id=aid, role="output")

        result = db.delete_run_with_orphan_assets("r1")
        assert len(result["orphaned_assets"]) == 1
        assert db.get_asset_by_fingerprint("model", "orp") is None
        db.close()

    def test_shared_asset_kept(self, tmp_path: Path) -> None:
        db = IndexDb(tmp_path)
        for rid in ("r1", "r2"):
            db.upsert_run(
                run_id=rid, path="p", alias=None,
                created_at=time.time(), status="finished",
                run_dir=f"/tmp/{rid}", workspace_root=None,
            )
        aid = db.upsert_asset(
            asset_type="data", name="d", source_uri="/d",
            archive_uri=None, is_archived=False,
            fingerprint_kind="md5", fingerprint="shared2",
        )
        db.link_run_asset(run_id="r1", asset_id=aid, role="input")
        db.link_run_asset(run_id="r2", asset_id=aid, role="input")

        result = db.delete_run_with_orphan_assets("r1")
        assert len(result["kept_assets"]) == 1
        assert db.get_asset_by_fingerprint("data", "shared2") is not None
        db.close()


class TestIndexDbClose:

    def test_close_and_close_all(self, tmp_path: Path) -> None:
        db = IndexDb(tmp_path)
        # Force a connection
        db._connect()
        db.close()
        # close_all after close should not raise
        db.close_all()
