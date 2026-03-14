from __future__ import annotations

from fastapi.testclient import TestClient


class _FakeConnection:
    def __init__(self) -> None:
        self.is_connected = True


class _FakePool:
    def __init__(self, connection: _FakeConnection) -> None:
        self._connection = connection
        self.last_lookup = None

    def get_connection(self, host: str, port: int, username: str):
        self.last_lookup = (host, port, username)
        return self._connection

    def close_all(self) -> None:
        return None


class TestRemoteStorageCandidates:

    def test_returns_detected_storage_candidates(
        self,
        viewer_client: TestClient,
        monkeypatch,
    ) -> None:
        import runicorn.viewer.api.remote as remote_api

        connection = _FakeConnection()
        pool = _FakePool(connection)
        viewer_client.app.state.connection_pool = pool

        monkeypatch.setattr(remote_api, "_resolve_python_command", lambda conn, env: "python3")
        monkeypatch.setattr(
            remote_api,
            "_detect_remote_storage_candidates",
            lambda conn, python_cmd, **kwargs: [
                {
                    "path": "/home/test/runicorn_data",
                    "run_count": 3,
                    "has_archive": True,
                    "has_index": True,
                    "score": 143,
                }
            ],
        )

        resp = viewer_client.get(
            "/api/remote/storage-candidates",
            params={"connection_id": "user@example.com:22", "conda_env": "system"},
        )

        assert resp.status_code == 200
        assert pool.last_lookup == ("example.com", 22, "user")
        assert resp.json()["candidates"] == [
            {
                "path": "/home/test/runicorn_data",
                "run_count": 3,
                "has_archive": True,
                "has_index": True,
                "score": 143,
            }
        ]

    def test_returns_404_for_inactive_connection(
        self,
        viewer_client: TestClient,
    ) -> None:
        viewer_client.app.state.connection_pool = _FakePool(connection=None)

        resp = viewer_client.get(
            "/api/remote/storage-candidates",
            params={"connection_id": "user@example.com:22"},
        )

        assert resp.status_code == 404
