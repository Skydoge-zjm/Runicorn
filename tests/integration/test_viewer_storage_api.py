"""Integration tests for /api/storage/stats endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient


class TestStorageStats:

    def test_returns_expected_structure(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/storage/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "storage_root" in data
        assert "total" in data
        assert "archive" in data
        assert "runs" in data
        assert "index" in data

    def test_runs_count_matches(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/storage/stats")
        data = resp.json()
        assert data["runs"]["runs_count"] == 3

    def test_size_fields_are_numeric(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/storage/stats")
        data = resp.json()
        assert isinstance(data["total"]["size_bytes"], int)
        assert isinstance(data["total"]["size_human"], str)
