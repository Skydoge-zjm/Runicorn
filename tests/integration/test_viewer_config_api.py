"""Integration tests for /api/config endpoints."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


class TestGetConfig:

    def test_returns_config(self, viewer_client: TestClient) -> None:
        resp = viewer_client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "storage" in data
        assert "config_file" in data

    def test_storage_matches_root(
        self, viewer_client: TestClient, viewer_storage_root: Path
    ) -> None:
        resp = viewer_client.get("/api/config")
        data = resp.json()
        assert str(viewer_storage_root) in data["storage"]


class TestSetUserRootDir:

    def test_set_valid_path(
        self, viewer_client: TestClient, tmp_path: Path, mock_config_root
    ) -> None:
        target = tmp_path / "new_storage"
        resp = viewer_client.post(
            "/api/config/user_root_dir",
            json={"path": str(target)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "user_root_dir" in data


class TestLocalStorageCandidates:

    def test_returns_storage_candidates(
        self, viewer_client: TestClient, monkeypatch
    ) -> None:
        import runicorn.viewer.api.config as config_api

        monkeypatch.setattr(
            config_api,
            "_detect_local_storage_candidates",
            lambda **kwargs: {
                "scan_root": "C:\\Users\\Lenovo",
                "max_depth": 2,
                "candidates": [
                    {
                        "path": "C:\\Users\\Lenovo\\runicorn_data",
                        "run_count": 4,
                        "has_archive": True,
                        "has_index": True,
                        "score": 144,
                    }
                ],
            },
        )

        resp = viewer_client.get(
            "/api/config/storage-candidates",
            params={"scan_root": "C:\\Users\\Lenovo", "max_depth": 2},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["scan_root"] == "C:\\Users\\Lenovo"
        assert data["max_depth"] == 2
        assert len(data["candidates"]) == 1


class TestSSHConnectionsCRUD:

    def test_get_empty_connections(
        self, viewer_client: TestClient, mock_config_root
    ) -> None:
        resp = viewer_client.get("/api/config/ssh_connections")
        assert resp.status_code == 200
        assert resp.json()["connections"] == []

    def test_save_and_list_connection(
        self, viewer_client: TestClient, mock_config_root
    ) -> None:
        conn = {
            "host": "test-host", "port": 22, "username": "admin",
            "remember_password": True, "password": "secret",
        }
        resp = viewer_client.post("/api/config/ssh_connections", json=conn)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        resp = viewer_client.get("/api/config/ssh_connections")
        conns = resp.json()["connections"]
        assert len(conns) >= 1
        assert conns[0]["host"] == "test-host"
        # Password should be masked
        assert "password" not in conns[0]
        assert conns[0]["has_password"] is True

    def test_delete_connection(
        self, viewer_client: TestClient, mock_config_root
    ) -> None:
        conn = {"host": "del-host", "port": 22, "username": "u"}
        viewer_client.post("/api/config/ssh_connections", json=conn)

        key = "del-host:22@u"
        resp = viewer_client.delete(f"/api/config/ssh_connections/{key}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


class TestUIPreferences:

    def test_get_empty_column_widths(
        self, viewer_client: TestClient, mock_config_root
    ) -> None:
        resp = viewer_client.get("/api/config/column-widths?table=runs&size=1920x1080")
        assert resp.status_code == 200
        data = resp.json()
        assert data["table"] == "runs"
        assert data["widths"] == {}

    def test_save_and_load_column_widths(
        self, viewer_client: TestClient, mock_config_root
    ) -> None:
        payload = {
            "table": "runs", "size": "1920x1080",
            "widths": {"name": 200, "status": 100},
        }
        resp = viewer_client.post("/api/config/column-widths", json=payload)
        assert resp.status_code == 200

        resp = viewer_client.get("/api/config/column-widths?table=runs&size=1920x1080")
        assert resp.json()["widths"] == {"name": 200, "status": 100}

    def test_reset_column_widths(
        self, viewer_client: TestClient, mock_config_root
    ) -> None:
        payload = {
            "table": "runs", "size": "1920x1080",
            "widths": {"name": 200},
        }
        viewer_client.post("/api/config/column-widths", json=payload)

        resp = viewer_client.delete("/api/config/column-widths?table=runs&size=1920x1080")
        assert resp.status_code == 200

        resp = viewer_client.get("/api/config/column-widths?table=runs&size=1920x1080")
        assert resp.json()["widths"] == {}
