"""Integration tests for /api/runs/* endpoints."""
from __future__ import annotations

from typing import List

from fastapi.testclient import TestClient


# Convenient aliases for the run IDs used in the viewer fixture.
RUN_A = "20250101_120000_aaaaaa"  # cv/yolo
RUN_B = "20250102_120000_bbbbbb"  # cv/yolo, tag=baseline
RUN_C = "20250103_120000_cccccc"  # nlp/bert


class TestListRuns:

    def test_list_runs_from_sqlite(
        self, viewer_client: TestClient, populated_viewer_storage: List[str]
    ) -> None:
        resp = viewer_client.get("/api/runs")
        assert resp.status_code == 200
        runs = resp.json()
        ids = {r["id"] for r in runs}
        assert RUN_A in ids
        assert RUN_B in ids
        assert RUN_C in ids

    def test_list_runs_has_expected_fields(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/runs")
        run = resp.json()[0]
        for key in ("id", "status", "path", "created_time"):
            assert key in run

    def test_list_runs_empty_storage(self, viewer_client: TestClient) -> None:
        """Empty DB → fallback to file scan → empty list."""
        resp = viewer_client.get("/api/runs")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetRunDetail:

    def test_get_existing_run(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get(f"/api/runs/{RUN_A}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == RUN_A
        assert "status" in data

    def test_get_nonexistent_run(self, viewer_client: TestClient) -> None:
        resp = viewer_client.get("/api/runs/20250101_000000_ffffff")
        assert resp.status_code == 404


class TestSoftDeleteAndRestore:

    def test_soft_delete_removes_from_list(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.post(
            "/api/runs/soft-delete",
            json={"run_ids": [RUN_B]},
        )
        assert resp.status_code == 200

        runs = viewer_client.get("/api/runs").json()
        ids = {r["id"] for r in runs}
        assert RUN_B not in ids

    def test_deleted_appears_in_recycle_bin(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        viewer_client.post(
            "/api/runs/soft-delete",
            json={"run_ids": [RUN_B]},
        )
        resp = viewer_client.get("/api/recycle-bin")
        assert resp.status_code == 200
        deleted_ids = {r["id"] for r in resp.json()["deleted_runs"]}
        assert RUN_B in deleted_ids

    def test_restore_run(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        viewer_client.post(
            "/api/runs/soft-delete",
            json={"run_ids": [RUN_B]},
        )
        resp = viewer_client.post(
            "/api/recycle-bin/restore",
            json={"run_ids": [RUN_B]},
        )
        assert resp.status_code == 200

        runs = viewer_client.get("/api/runs").json()
        ids = {r["id"] for r in runs}
        assert RUN_B in ids


class TestUpdateRun:

    def test_update_alias(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.patch(
            f"/api/runs/{RUN_A}",
            json={"alias": "best-run"},
        )
        assert resp.status_code == 200
        assert resp.json()["alias"] == "best-run"

    def test_update_tags(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.patch(
            f"/api/runs/{RUN_A}",
            json={"tags": ["v1", "production"]},
        )
        assert resp.status_code == 200
        assert set(resp.json()["tags"]) == {"v1", "production"}


class TestEmptyRecycleBin:

    def test_empty_recycle_bin(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        """Soft-delete a run, then permanently empty the recycle bin."""
        # Soft-delete first
        viewer_client.post(
            "/api/runs/soft-delete",
            json={"run_ids": [RUN_B]},
        )
        # Permanently delete
        resp = viewer_client.post(
            "/api/recycle-bin/empty",
            json={"confirm": True},
        )
        assert resp.status_code == 200
        assert resp.json()["permanently_deleted"] >= 1

        # Recycle bin should now be empty
        resp = viewer_client.get("/api/recycle-bin")
        assert resp.status_code == 200
        assert len(resp.json()["deleted_runs"]) == 0


class TestGetRunAssets:

    def test_get_run_assets(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get(f"/api/runs/{RUN_A}/assets")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == RUN_A
        assert "assets" in data

    def test_get_run_assets_not_found(
        self, viewer_client: TestClient,
    ) -> None:
        resp = viewer_client.get("/api/runs/20250101_000000_ffffff/assets")
        assert resp.status_code == 404
