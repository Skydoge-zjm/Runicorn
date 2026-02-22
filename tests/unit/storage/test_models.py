"""Tests for runicorn.storage.models — data model classes."""
from __future__ import annotations

import time

import pytest

from runicorn.storage.models import (
    ExperimentRecord,
    MetricRecord,
    QueryParams,
    EnvironmentRecord,
    StorageStats,
    MigrationStatus,
)


class TestExperimentRecord:

    def test_from_dict_basic(self) -> None:
        data = {"id": "abc", "path": "train/cifar", "status": "running"}
        rec = ExperimentRecord.from_dict(data)

        assert rec.id == "abc"
        assert rec.path == "train/cifar"
        assert rec.status == "running"

    def test_from_dict_legacy_project_name(self) -> None:
        """Legacy data with project/name should be converted to path."""
        data = {"id": "x", "project": "cv", "name": "yolo", "status": "finished"}
        rec = ExperimentRecord.from_dict(data)

        assert rec.path == "cv/yolo"

    def test_to_dict(self) -> None:
        rec = ExperimentRecord(id="abc", path="p", run_dir="/tmp/r")
        d = rec.to_dict()

        assert d["id"] == "abc"
        assert d["path"] == "p"
        assert isinstance(d, dict)

    def test_is_active(self) -> None:
        active = ExperimentRecord(id="a", path="p", run_dir="")
        deleted = ExperimentRecord(id="b", path="p", run_dir="", deleted_at=1.0)

        assert active.is_active() is True
        assert deleted.is_active() is False

    def test_is_running(self) -> None:
        running = ExperimentRecord(id="a", path="p", run_dir="", status="running")
        finished = ExperimentRecord(id="b", path="p", run_dir="", status="finished")
        deleted_running = ExperimentRecord(
            id="c", path="p", run_dir="", status="running", deleted_at=1.0
        )

        assert running.is_running() is True
        assert finished.is_running() is False
        assert deleted_running.is_running() is False

    def test_compute_duration(self) -> None:
        now = time.time()
        rec = ExperimentRecord(
            id="a", path="p", run_dir="",
            started_at=now - 100, ended_at=now,
        )
        assert abs(rec.compute_duration() - 100) < 1

    def test_short_id(self) -> None:
        rec = ExperimentRecord(id="20260101_120000_abcdef", path="p", run_dir="")
        assert rec.short_id == "abcdef"

    def test_path_parts(self) -> None:
        rec = ExperimentRecord(id="a", path="cv/detection/yolo", run_dir="")
        assert rec.path_parts() == ["cv", "detection", "yolo"]

    def test_path_parts_empty(self) -> None:
        rec = ExperimentRecord(id="a", path="/", run_dir="")
        assert rec.path_parts() == []


class TestMetricRecord:

    def test_creation(self) -> None:
        rec = MetricRecord(
            experiment_id="exp1", timestamp=1.0,
            metric_name="loss", metric_value=0.5, step=10,
        )
        assert rec.metric_name == "loss"
        assert rec.metric_value == 0.5
        assert rec.recorded_at is not None


class TestQueryParams:

    def test_defaults(self) -> None:
        q = QueryParams()
        assert q.limit == 100
        assert q.offset == 0
        assert q.order_desc is True
        assert q.include_deleted is False

    def test_with_filters(self) -> None:
        q = QueryParams(path="cv", status=["running", "finished"], created_after=1.0)
        assert q.path == "cv"
        assert len(q.status) == 2


class TestEnvironmentRecord:

    def test_creation(self) -> None:
        rec = EnvironmentRecord(experiment_id="e1", git_branch="main", cpu_count=8)
        assert rec.git_branch == "main"
        assert rec.captured_at is not None


class TestStorageStats:

    def test_fields(self) -> None:
        st = StorageStats(total_experiments=10, active_experiments=8, deleted_experiments=2)
        d = st.to_dict()
        assert d["total_experiments"] == 10


class TestMigrationStatus:

    def test_progress_percent(self) -> None:
        m = MigrationStatus(migration_type="t", status="in_progress",
                            total_items=200, processed_items=50)
        assert m.progress_percent == 25.0

    def test_progress_percent_zero_total(self) -> None:
        m = MigrationStatus(migration_type="t", status="pending", total_items=0)
        assert m.progress_percent == 0.0

    def test_is_complete(self) -> None:
        m = MigrationStatus(migration_type="t", status="completed")
        assert m.is_complete is True

    def test_has_errors(self) -> None:
        m = MigrationStatus(migration_type="t", status="failed", failed_items=3)
        assert m.has_errors is True

        ok = MigrationStatus(migration_type="t", status="completed")
        assert ok.has_errors is False
