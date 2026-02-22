"""Unit tests for runicorn.client.models — data model validation."""
from __future__ import annotations

import time

import pytest

from runicorn.client.models import (
    Experiment,
    MetricPoint,
    MetricSeries,
    PathInfo,
    Project,
    RemoteSession,
    RunInfo,
)


# ---------------------------------------------------------------------------
# RunInfo
# ---------------------------------------------------------------------------

class TestRunInfoFromDict:
    """test_run_info_from_dict — RunInfo dataclass creation."""

    def test_full_dict(self):
        data = {
            "id": "abc123",
            "status": "finished",
            "created_time": 1700000000.0,
            "path": "cv/yolo",
            "alias": "baseline",
            "tags": ["v1", "production"],
            "best_metric_value": 0.95,
            "best_metric_name": "accuracy",
            "assets_count": 3,
            "run_dir": "/data/runs/abc123",
            "pid": 12345,
        }
        info = RunInfo.from_dict(data)
        assert info.id == "abc123"
        assert info.status == "finished"
        assert info.created_time == 1700000000.0
        assert info.path == "cv/yolo"
        assert info.alias == "baseline"
        assert info.tags == ["v1", "production"]
        assert info.best_metric_value == 0.95
        assert info.assets_count == 3
        assert info.pid == 12345

    def test_minimal_dict(self):
        data = {"id": "r1"}
        info = RunInfo.from_dict(data)
        assert info.id == "r1"
        assert info.status == "unknown"
        assert info.tags == []
        assert info.assets_count == 0
        assert info.created_time is None

    def test_created_datetime_property(self):
        info = RunInfo(id="r1", status="ok", created_time=1700000000.0)
        dt = info.created_datetime
        assert dt is not None
        assert dt.year >= 2023

    def test_created_datetime_none(self):
        info = RunInfo(id="r1", status="ok")
        assert info.created_datetime is None


# ---------------------------------------------------------------------------
# PathInfo
# ---------------------------------------------------------------------------

class TestPathInfoFromDict:
    """test_path_info_from_dict — PathInfo dataclass creation."""

    def test_full_stats(self):
        info = PathInfo.from_dict("cv/yolo", {
            "total": 10, "running": 2, "finished": 7, "failed": 1
        })
        assert info.path == "cv/yolo"
        assert info.total == 10
        assert info.running == 2
        assert info.finished == 7
        assert info.failed == 1

    def test_empty_stats(self):
        info = PathInfo.from_dict("empty", {})
        assert info.total == 0
        assert info.running == 0


# ---------------------------------------------------------------------------
# Backward compatibility aliases
# ---------------------------------------------------------------------------

class TestLegacyAliases:
    """test_legacy_experiment_alias / test_legacy_project_alias."""

    def test_experiment_is_run_info(self):
        assert Experiment is RunInfo

    def test_project_is_path_info(self):
        assert Project is PathInfo

    def test_experiment_from_dict(self):
        data = {"id": "r1", "status": "running"}
        exp = Experiment.from_dict(data)
        assert isinstance(exp, RunInfo)
        assert exp.id == "r1"


# ---------------------------------------------------------------------------
# MetricPoint / MetricSeries
# ---------------------------------------------------------------------------

class TestMetricModels:
    """Additional model coverage for MetricPoint and MetricSeries."""

    def test_metric_point_from_dict(self):
        mp = MetricPoint.from_dict({"step": 10, "value": 0.5, "timestamp": 1000.0})
        assert mp.step == 10
        assert mp.value == 0.5
        assert mp.timestamp == 1000.0

    def test_metric_point_default_timestamp(self):
        mp = MetricPoint.from_dict({"step": 1, "value": 0.9})
        assert mp.timestamp == 0

    def test_metric_series_from_dict(self):
        points = [
            {"step": 1, "value": 0.5, "timestamp": 100},
            {"step": 2, "value": 0.3, "timestamp": 200},
        ]
        series = MetricSeries.from_dict("loss", points)
        assert series.name == "loss"
        assert len(series.points) == 2

    def test_metric_series_values_steps(self):
        points = [
            {"step": 1, "value": 0.5, "timestamp": 100},
            {"step": 2, "value": 0.3, "timestamp": 200},
        ]
        series = MetricSeries.from_dict("loss", points)
        assert series.values == [0.5, 0.3]
        assert series.steps == [1, 2]

    def test_metric_series_aggregates(self):
        points = [
            {"step": i, "value": float(i), "timestamp": 0}
            for i in range(1, 6)
        ]
        series = MetricSeries.from_dict("metric", points)
        assert series.last_value() == 5.0
        assert series.min_value() == 1.0
        assert series.max_value() == 5.0

    def test_metric_series_empty(self):
        series = MetricSeries.from_dict("empty", [])
        assert series.last_value() is None
        assert series.min_value() is None
        assert series.max_value() is None


# ---------------------------------------------------------------------------
# RemoteSession
# ---------------------------------------------------------------------------

class TestRemoteSession:
    """RemoteSession model."""

    def test_from_dict(self):
        data = {
            "session_id": "s1",
            "connection_id": "c1",
            "remote_host": "gpu-server",
            "remote_port": 22,
            "local_port": 23300,
            "remote_root": "/home/user/runs",
            "status": "active",
            "created_at": 1700000000.0,
        }
        rs = RemoteSession.from_dict(data)
        assert rs.session_id == "s1"
        assert rs.remote_host == "gpu-server"
        assert rs.local_url == "http://localhost:23300"

    def test_defaults(self):
        rs = RemoteSession.from_dict({"session_id": "s2"})
        assert rs.connection_id == ""
        assert rs.remote_port == 0
        assert rs.status == "unknown"
