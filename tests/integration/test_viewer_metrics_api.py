"""Integration tests for /api/runs/{id}/metrics* endpoints."""
from __future__ import annotations

from typing import List

from fastapi.testclient import TestClient


RUN_A = "20250101_120000_aaaaaa"


class TestGetMetrics:

    def test_metrics_returns_columns_and_rows(
        self, viewer_client: TestClient, populated_viewer_storage: List[str]
    ) -> None:
        resp = viewer_client.get(f"/api/runs/{RUN_A}/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "columns" in data
        assert "rows" in data
        assert "global_step" in data["columns"]
        assert "loss" in data["columns"]
        assert "acc" in data["columns"]
        # RUN_A has 2 metrics events
        assert data["total"] == 2

    def test_metrics_rows_ordered_by_step(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        rows = viewer_client.get(f"/api/runs/{RUN_A}/metrics").json()["rows"]
        steps = [r["global_step"] for r in rows]
        assert steps == sorted(steps)

    def test_metrics_nonexistent_run(self, viewer_client: TestClient) -> None:
        resp = viewer_client.get("/api/runs/no_such/metrics")
        assert resp.status_code == 404


class TestGetMetricsStep:

    def test_metrics_step_same_shape(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get(f"/api/runs/{RUN_A}/metrics_step")
        assert resp.status_code == 200
        data = resp.json()
        assert "columns" in data and "rows" in data
        assert data["total"] == 2


class TestProgress:

    def test_progress_endpoint(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get(f"/api/runs/{RUN_A}/progress")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is False


class TestMetricsHeaders:

    def test_response_has_metadata_headers(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get(f"/api/runs/{RUN_A}/metrics")
        assert resp.status_code == 200
        assert "X-Row-Count" in resp.headers
        assert "X-Total-Count" in resp.headers
        assert int(resp.headers["X-Total-Count"]) == 2


class TestMetricsDownsample:

    def test_downsample_not_applied_when_data_small(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        """With only 2 rows, downsample=100 should return all rows."""
        resp = viewer_client.get(f"/api/runs/{RUN_A}/metrics?downsample=100")
        assert resp.status_code == 200
        data = resp.json()
        # 2 rows < 100 target, no downsampling applied
        assert data["total"] == data["sampled"]


class TestCacheStats:

    def test_cache_stats(self, viewer_client: TestClient) -> None:
        resp = viewer_client.get("/api/metrics/cache/stats")
        assert resp.status_code == 200
        data = resp.json()
        for key in ("size", "max_size", "hits", "misses"):
            assert key in data
