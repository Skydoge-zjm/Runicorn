"""Tests for runicorn.storage.backends.SQLiteStorageBackend."""
from __future__ import annotations

import time
from pathlib import Path
from typing import List

import pytest

from runicorn.storage.backends import SQLiteStorageBackend
from runicorn.storage.models import ExperimentRecord, MetricRecord, QueryParams


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_experiment(
    exp_id: str = "exp_001",
    path: str = "train/cifar10",
    status: str = "running",
    **kwargs,
) -> ExperimentRecord:
    now = time.time()
    defaults = dict(
        id=exp_id,
        path=path,
        status=status,
        created_at=now,
        updated_at=now,
        run_dir=f"/tmp/runs/{exp_id}",
    )
    defaults.update(kwargs)
    return ExperimentRecord(**defaults)


def _make_metrics(exp_id: str, names: List[str], count: int = 3) -> List[MetricRecord]:
    now = time.time()
    metrics = []
    for name in names:
        for step in range(1, count + 1):
            metrics.append(MetricRecord(
                experiment_id=exp_id,
                timestamp=now + step,
                metric_name=name,
                metric_value=1.0 / step,
                step=step,
            ))
    return metrics


# ===========================================================================
# CRUD — create / get / update / list / count
# ===========================================================================

class TestCreateExperiment:

    def test_create_returns_id(self, sqlite_backend: SQLiteStorageBackend) -> None:
        exp = _make_experiment()
        result = sqlite_backend.create_experiment(exp)
        assert result == exp.id

    def test_create_duplicate_raises(self, sqlite_backend: SQLiteStorageBackend) -> None:
        exp = _make_experiment()
        sqlite_backend.create_experiment(exp)
        with pytest.raises(Exception):
            sqlite_backend.create_experiment(exp)


class TestGetExperiment:

    def test_get_existing(self, sqlite_backend: SQLiteStorageBackend) -> None:
        exp = _make_experiment(exp_id="get_001", path="eval/test")
        sqlite_backend.create_experiment(exp)

        result = sqlite_backend.get_experiment("get_001")
        assert result is not None
        assert result.id == "get_001"
        assert result.path == "eval/test"

    def test_get_nonexistent_returns_none(self, sqlite_backend: SQLiteStorageBackend) -> None:
        result = sqlite_backend.get_experiment("no_such_id")
        assert result is None


class TestUpdateExperiment:

    def test_update_status(self, sqlite_backend: SQLiteStorageBackend) -> None:
        exp = _make_experiment(exp_id="upd_001")
        sqlite_backend.create_experiment(exp)

        ok = sqlite_backend.update_experiment("upd_001", {"status": "finished"})
        assert ok is True

        updated = sqlite_backend.get_experiment("upd_001")
        assert updated.status == "finished"

    def test_update_invalid_column_ignored(self, sqlite_backend: SQLiteStorageBackend) -> None:
        exp = _make_experiment(exp_id="upd_002")
        sqlite_backend.create_experiment(exp)

        # "DROP TABLE" should be rejected by column whitelist
        result = sqlite_backend.update_experiment("upd_002", {"DROP TABLE experiments--": "x"})
        assert result is False

    def test_update_empty_dict(self, sqlite_backend: SQLiteStorageBackend) -> None:
        exp = _make_experiment(exp_id="upd_003")
        sqlite_backend.create_experiment(exp)
        assert sqlite_backend.update_experiment("upd_003", {}) is True


class TestListExperiments:

    def test_list_default_excludes_deleted(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("lst_001"))
        sqlite_backend.create_experiment(_make_experiment("lst_002"))
        sqlite_backend.soft_delete_experiments(["lst_002"])

        results = sqlite_backend.list_experiments(QueryParams())
        ids = [r.id for r in results]
        assert "lst_001" in ids
        assert "lst_002" not in ids

    def test_list_include_deleted(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("lst_003"))
        sqlite_backend.create_experiment(_make_experiment("lst_004"))
        sqlite_backend.soft_delete_experiments(["lst_004"])

        results = sqlite_backend.list_experiments(QueryParams(include_deleted=True))
        ids = [r.id for r in results]
        assert "lst_003" in ids
        assert "lst_004" in ids

    def test_filter_by_path_prefix(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("p1", path="train/cifar10"))
        sqlite_backend.create_experiment(_make_experiment("p2", path="eval/imagenet"))

        results = sqlite_backend.list_experiments(QueryParams(path="train"))
        ids = [r.id for r in results]
        assert "p1" in ids
        assert "p2" not in ids

    def test_filter_by_status(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("s1", status="running"))
        sqlite_backend.create_experiment(_make_experiment("s2", status="finished"))
        sqlite_backend.create_experiment(_make_experiment("s3", status="failed"))

        results = sqlite_backend.list_experiments(
            QueryParams(status=["running", "failed"])
        )
        ids = [r.id for r in results]
        assert "s1" in ids
        assert "s3" in ids
        assert "s2" not in ids

    def test_search_text(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("srch_1", alias="my-resnet"))
        sqlite_backend.create_experiment(_make_experiment("srch_2", alias="my-vgg"))

        results = sqlite_backend.list_experiments(QueryParams(search_text="resnet"))
        ids = [r.id for r in results]
        assert "srch_1" in ids
        assert "srch_2" not in ids

    def test_pagination(self, sqlite_backend: SQLiteStorageBackend) -> None:
        for i in range(5):
            sqlite_backend.create_experiment(
                _make_experiment(f"pg_{i}", created_at=float(i))
            )

        page = sqlite_backend.list_experiments(QueryParams(limit=2, offset=0, order_desc=False))
        assert len(page) == 2
        assert page[0].id == "pg_0"


class TestCountExperiments:

    def test_count(self, sqlite_backend: SQLiteStorageBackend) -> None:
        for i in range(4):
            sqlite_backend.create_experiment(_make_experiment(f"cnt_{i}"))
        assert sqlite_backend.count_experiments(QueryParams()) == 4

    def test_count_with_filter(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("cf1", status="running"))
        sqlite_backend.create_experiment(_make_experiment("cf2", status="finished"))
        assert sqlite_backend.count_experiments(QueryParams(status=["running"])) == 1


# ===========================================================================
# Metrics
# ===========================================================================

class TestMetrics:

    def test_log_and_retrieve(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("met_001"))
        metrics = _make_metrics("met_001", ["loss", "acc"], count=2)

        ok = sqlite_backend.log_metrics("met_001", metrics)
        assert ok is True

        retrieved = sqlite_backend.get_metrics("met_001")
        assert len(retrieved) == 4  # 2 names × 2 steps

    def test_get_metrics_filter_by_name(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("met_002"))
        sqlite_backend.log_metrics("met_002", _make_metrics("met_002", ["loss", "acc"]))

        loss_only = sqlite_backend.get_metrics("met_002", metric_names=["loss"])
        assert all(m.metric_name == "loss" for m in loss_only)
        assert len(loss_only) == 3

    def test_log_empty_metrics_returns_true(self, sqlite_backend: SQLiteStorageBackend) -> None:
        assert sqlite_backend.log_metrics("whatever", []) is True

    def test_get_metrics_nonexistent_returns_empty(self, sqlite_backend: SQLiteStorageBackend) -> None:
        result = sqlite_backend.get_metrics("no_such_exp")
        assert result == []


# ===========================================================================
# Soft-delete / Restore
# ===========================================================================

class TestSoftDelete:

    def test_soft_delete_and_restore(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("del_001"))

        deleted = sqlite_backend.soft_delete_experiments(["del_001"])
        assert deleted["del_001"] is True

        # Should be excluded from default list
        assert sqlite_backend.count_experiments(QueryParams()) == 0

        restored = sqlite_backend.restore_experiments(["del_001"])
        assert restored["del_001"] is True
        assert sqlite_backend.count_experiments(QueryParams()) == 1

    def test_delete_nonexistent(self, sqlite_backend: SQLiteStorageBackend) -> None:
        result = sqlite_backend.soft_delete_experiments(["ghost"])
        assert result["ghost"] is False

    def test_restore_non_deleted(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("nd_001"))
        result = sqlite_backend.restore_experiments(["nd_001"])
        assert result["nd_001"] is False


# ===========================================================================
# Tags
# ===========================================================================

class TestTags:

    def test_set_and_get_tags(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("tag_001"))
        sqlite_backend.set_tags("tag_001", ["baseline", "v2", "cifar"])

        tags = sqlite_backend.get_tags("tag_001")
        assert tags == ["baseline", "cifar", "v2"]  # sorted

    def test_replace_tags(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("tag_002"))
        sqlite_backend.set_tags("tag_002", ["a", "b"])
        sqlite_backend.set_tags("tag_002", ["c"])

        assert sqlite_backend.get_tags("tag_002") == ["c"]

    def test_clear_tags(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("tag_003"))
        sqlite_backend.set_tags("tag_003", ["x"])
        sqlite_backend.set_tags("tag_003", [])
        assert sqlite_backend.get_tags("tag_003") == []


# ===========================================================================
# Asset Management (RF-13)
# ===========================================================================

class TestAssets:

    def test_upsert_asset(self, sqlite_backend: SQLiteStorageBackend) -> None:
        asset_id = sqlite_backend.upsert_asset(
            asset_type="model",
            name="resnet.pth",
            source_uri="/tmp/resnet.pth",
            archive_uri=None,
            is_archived=False,
            fingerprint_kind="sha256",
            fingerprint="abc123",
            size_bytes=1024,
        )
        assert isinstance(asset_id, str) and len(asset_id) > 0

    def test_upsert_returns_existing_on_fingerprint_match(
        self, sqlite_backend: SQLiteStorageBackend
    ) -> None:
        common = dict(
            asset_type="dataset",
            name="data.csv",
            source_uri="/data.csv",
            archive_uri=None,
            is_archived=False,
            fingerprint_kind="md5",
            fingerprint="dedup_fp",
        )
        id1 = sqlite_backend.upsert_asset(**common)
        id2 = sqlite_backend.upsert_asset(**common)
        assert id1 == id2

    def test_record_asset_for_run(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("run_001"))

        asset_id = sqlite_backend.record_asset_for_run(
            run_id="run_001",
            role="checkpoint",
            asset_type="model",
            name="best.pth",
            source_uri="/best.pth",
            archive_uri=None,
            is_archived=False,
            fingerprint_kind="sha256",
            fingerprint="fp_run_001",
        )

        assets = sqlite_backend.get_assets_for_run("run_001")
        assert len(assets) == 1
        assert assets[0]["asset_id"] == asset_id

    def test_get_asset_ref_count(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("rc_001"))
        sqlite_backend.create_experiment(_make_experiment("rc_002"))

        asset_id = sqlite_backend.upsert_asset(
            asset_type="data", name="d", source_uri="s",
            archive_uri=None, is_archived=False,
            fingerprint_kind="md5", fingerprint="shared_fp",
        )
        sqlite_backend.link_run_asset(run_id="rc_001", asset_id=asset_id, role="input")
        sqlite_backend.link_run_asset(run_id="rc_002", asset_id=asset_id, role="input")

        assert sqlite_backend.get_asset_ref_count(asset_id) == 2

    def test_get_asset_by_fingerprint(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.upsert_asset(
            asset_type="model", name="m",
            source_uri="s", archive_uri=None,
            is_archived=False, fingerprint_kind="sha256", fingerprint="unique_fp",
        )
        result = sqlite_backend.get_asset_by_fingerprint("model", "unique_fp")
        assert result is not None
        assert result["fingerprint"] == "unique_fp"

    def test_get_asset_by_fingerprint_miss(self, sqlite_backend: SQLiteStorageBackend) -> None:
        assert sqlite_backend.get_asset_by_fingerprint("model", "nope") is None


# ===========================================================================
# Viewer-optimised Queries (RF-14)
# ===========================================================================

class TestViewerQueries:

    def test_list_experiments_for_viewer(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("v1", status="finished"))
        sqlite_backend.create_experiment(_make_experiment("v2"))
        sqlite_backend.soft_delete_experiments(["v2"])
        sqlite_backend.set_tags("v1", ["demo"])

        rows = sqlite_backend.list_experiments_for_viewer()
        assert len(rows) == 1
        assert rows[0]["id"] == "v1"
        assert "demo" in (rows[0]["tags_csv"] or "")

    def test_list_experiments_for_viewer_include_deleted(
        self, sqlite_backend: SQLiteStorageBackend
    ) -> None:
        sqlite_backend.create_experiment(_make_experiment("vd1"))
        sqlite_backend.create_experiment(_make_experiment("vd2"))
        sqlite_backend.soft_delete_experiments(["vd2"])

        rows = sqlite_backend.list_experiments_for_viewer(include_deleted=True)
        ids = [r["id"] for r in rows]
        assert "vd1" in ids and "vd2" in ids

    def test_list_deleted_for_viewer(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("ld1"))
        sqlite_backend.soft_delete_experiments(["ld1"], reason="user")
        sqlite_backend.create_experiment(_make_experiment("ld2"))

        rows = sqlite_backend.list_deleted_for_viewer()
        assert len(rows) == 1
        assert rows[0]["id"] == "ld1"

    def test_get_unique_paths(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("up1", path="train/a"))
        sqlite_backend.create_experiment(_make_experiment("up2", path="eval/b"))
        sqlite_backend.create_experiment(_make_experiment("up3", path="train/a"))

        paths = sqlite_backend.get_unique_paths()
        assert sorted(paths) == ["eval/b", "train/a"]

    def test_get_path_stats(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("ps1", path="train/a", status="running"))
        sqlite_backend.create_experiment(_make_experiment("ps2", path="train/a", status="finished"))
        sqlite_backend.create_experiment(_make_experiment("ps3", path="train/b", status="failed"))

        stats = sqlite_backend.get_path_stats()
        assert stats["train/a"]["total"] == 2
        assert stats["train/a"]["running"] == 1
        # ancestor "train" should accumulate
        assert stats["train"]["total"] == 3

    def test_get_running_experiments(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("rn1", status="running"))
        sqlite_backend.create_experiment(_make_experiment("rn2", status="finished"))

        rows = sqlite_backend.get_running_experiments()
        ids = [r["id"] for r in rows]
        assert "rn1" in ids
        assert "rn2" not in ids

    def test_experiment_exists(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("ex_001"))
        assert sqlite_backend.experiment_exists("ex_001") is True
        assert sqlite_backend.experiment_exists("no_such") is False


# ===========================================================================
# Storage Stats
# ===========================================================================

class TestStorageStats:

    def test_get_storage_stats(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("ss1"))
        sqlite_backend.create_experiment(_make_experiment("ss2"))
        sqlite_backend.soft_delete_experiments(["ss2"])

        stats = sqlite_backend.get_storage_stats()
        assert stats.total_experiments == 2
        assert stats.active_experiments == 1
        assert stats.deleted_experiments == 1
        assert stats.db_size_mb > 0


# ===========================================================================
# Delete with orphan asset cleanup
# ===========================================================================

class TestDeleteRunWithOrphanAssets:

    def test_orphan_assets_removed(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("orp_001"))

        asset_id = sqlite_backend.upsert_asset(
            asset_type="model", name="m",
            source_uri="/m", archive_uri=None,
            is_archived=False, fingerprint_kind="sha256", fingerprint="orp_fp",
        )
        sqlite_backend.link_run_asset(run_id="orp_001", asset_id=asset_id, role="output")

        result = sqlite_backend.delete_run_with_orphan_assets("orp_001")
        assert len(result["orphaned_assets"]) == 1
        assert len(result["kept_assets"]) == 0

        # Asset should be gone from DB
        assert sqlite_backend.get_asset_by_fingerprint("model", "orp_fp") is None

    def test_shared_asset_kept(self, sqlite_backend: SQLiteStorageBackend) -> None:
        sqlite_backend.create_experiment(_make_experiment("sh_001"))
        sqlite_backend.create_experiment(_make_experiment("sh_002"))

        asset_id = sqlite_backend.upsert_asset(
            asset_type="data", name="d",
            source_uri="/d", archive_uri=None,
            is_archived=False, fingerprint_kind="md5", fingerprint="shared_fp2",
        )
        sqlite_backend.link_run_asset(run_id="sh_001", asset_id=asset_id, role="input")
        sqlite_backend.link_run_asset(run_id="sh_002", asset_id=asset_id, role="input")

        result = sqlite_backend.delete_run_with_orphan_assets("sh_001")
        assert len(result["kept_assets"]) == 1

        # Asset still accessible
        assert sqlite_backend.get_asset_by_fingerprint("data", "shared_fp2") is not None
