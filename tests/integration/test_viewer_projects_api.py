"""Integration tests for /api/paths/* and legacy /api/projects/* endpoints."""
from __future__ import annotations

from typing import List

from fastapi.testclient import TestClient


class TestListPaths:

    def test_list_paths_returns_unique(
        self, viewer_client: TestClient, populated_viewer_storage: List[str]
    ) -> None:
        resp = viewer_client.get("/api/paths")
        assert resp.status_code == 200
        data = resp.json()
        paths = data["paths"]
        assert "cv/yolo" in paths
        assert "nlp/bert" in paths

    def test_list_paths_includes_tree(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/paths")
        data = resp.json()
        assert "tree" in data
        tree = data["tree"]
        assert "cv" in tree
        assert "nlp" in tree
        assert "yolo" in tree["cv"]

    def test_list_paths_with_stats(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/paths?include_stats=true")
        assert resp.status_code == 200
        data = resp.json()
        assert "stats" in data
        yolo_stat = data["stats"]["cv/yolo"]
        assert yolo_stat["total"] >= 2
        assert data["stats"]["cv"]["total"] >= 2

    def test_list_paths_empty_storage(self, viewer_client: TestClient) -> None:
        resp = viewer_client.get("/api/paths")
        assert resp.status_code == 200
        assert resp.json()["paths"] == []


class TestPathTree:

    def test_get_path_tree(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/paths/tree")
        assert resp.status_code == 200
        tree = resp.json()["tree"]
        assert "cv" in tree
        assert "nlp" in tree


class TestRunsByPath:

    def test_list_runs_by_path(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/paths/runs?path=cv/yolo")
        assert resp.status_code == 200
        runs = resp.json()
        ids = {r["id"] for r in runs}
        assert len(ids) >= 2
        assert "20250101_120000_aaaaaa" in ids
        assert "20250102_120000_bbbbbb" in ids

    def test_list_runs_by_path_no_match(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/paths/runs?path=nonexistent")
        assert resp.status_code == 200
        assert resp.json() == []


class TestLegacyProjects:

    def test_list_projects(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/projects")
        assert resp.status_code == 200
        projects = resp.json()["projects"]
        assert "cv" in projects
        assert "nlp" in projects

    def test_list_names(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/projects/cv/names")
        assert resp.status_code == 200
        names = resp.json()["names"]
        assert "yolo" in names

    def test_list_runs_by_name(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/projects/cv/names/yolo/runs")
        assert resp.status_code == 200
        runs = resp.json()
        assert len(runs) >= 2
        assert all(r["path"].startswith("cv/yolo") for r in runs)


class TestPathsRunsExact:

    def test_exact_match(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/paths/runs?path=cv/yolo&exact=true")
        assert resp.status_code == 200
        runs = resp.json()
        assert all(r["path"] == "cv/yolo" for r in runs)

    def test_prefix_match_includes_children(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/paths/runs?path=cv")
        assert resp.status_code == 200
        runs = resp.json()
        assert len(runs) >= 2


class TestPathsBatchOps:

    def test_soft_delete_by_path(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.post(
            "/api/paths/soft-delete",
            json={"path": "nlp/bert"},
        )
        assert resp.status_code == 200
        assert resp.json()["deleted_count"] >= 1

    def test_export_by_path_json(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/paths/export?path=cv/yolo&format=json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_runs"] >= 2
        assert len(data["runs"]) >= 2
