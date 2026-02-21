"""Integration tests for /api/health and /api/status/check endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient


class TestHealthEndpoint:

    def test_returns_ok(self, viewer_client: TestClient) -> None:
        resp = viewer_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "storage" in data
        assert "version" in data

    def test_cache_stats_present(self, viewer_client: TestClient) -> None:
        resp = viewer_client.get("/api/health")
        data = resp.json()
        cache = data["cache"]
        assert cache["enabled"] is True
        assert "hits" in cache
        assert "misses" in cache
        assert "size" in cache


class TestStatusCheck:

    def test_check_no_running(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        """With all runs finished, check returns 0 updated."""
        resp = viewer_client.post("/api/status/check")
        assert resp.status_code == 200
        data = resp.json()
        assert data["checked"] == 0
        assert data["updated"] == 0
