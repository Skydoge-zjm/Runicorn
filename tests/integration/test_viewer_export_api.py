"""Integration tests for /api/export/* and /api/environment/* endpoints."""
from __future__ import annotations

from typing import List

from fastapi.testclient import TestClient

RUN_A = "20250101_120000_aaaaaa"


class TestExportCsv:

    def test_export_csv_or_501(
        self, viewer_client: TestClient, populated_viewer_storage: List[str]
    ) -> None:
        """CSV export returns 200 (data) or 501 (exporter not installed)."""
        resp = viewer_client.get(f"/api/export/{RUN_A}/csv")
        assert resp.status_code in (200, 501)

    def test_export_csv_nonexistent_run(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/export/20250101_000000_ffffff/csv")
        # 404 (run not found) or 501 (exporter missing)
        assert resp.status_code in (404, 501)


class TestExportReport:

    def test_bad_format_rejected(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get(f"/api/export/{RUN_A}/report?format=pdf")
        # 400 (bad format) or 501 (exporter missing)
        assert resp.status_code in (400, 501)


class TestEnvironment:

    def test_environment_endpoint(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get(f"/api/environment/{RUN_A}")
        assert resp.status_code == 200
        data = resp.json()
        # No environment.json in fixture → available: false
        assert data["available"] is False

    def test_environment_nonexistent_run(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/environment/20250101_000000_ffffff")
        assert resp.status_code == 404
