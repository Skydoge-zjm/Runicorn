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
        self, viewer_client: TestClient, tmp_path: Path
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
