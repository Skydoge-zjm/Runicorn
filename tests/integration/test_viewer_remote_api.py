from __future__ import annotations

import json
from fastapi.testclient import TestClient


class _FakeConnection:
    def __init__(self) -> None:
        self.is_connected = True
        self.config = type("Config", (), {"timeout": 0})()


class _FakePool:
    def __init__(self, connection: _FakeConnection) -> None:
        self._connection = connection
        self.last_lookup = None

    def get_connection(self, host: str, port: int, username: str):
        self.last_lookup = (host, port, username)
        return self._connection

    def close_all(self) -> None:
        return None

    def get_or_create(self, config):
        self.last_config = config
        return self._connection


class _FakeSession:
    def __init__(self, connection) -> None:
        self.connection = connection
        self.session_id = "sess_1"
        self.local_port = 8765

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "local_port": self.local_port,
        }


class _FakeViewerManager:
    def __init__(self) -> None:
        self.last_start_kwargs = None

    def start_remote_viewer(self, **kwargs):
        self.last_start_kwargs = kwargs
        return _FakeSession(kwargs["connection"])


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


class TestSavedServerCredentialFlow:

    def test_saved_connections_endpoint_masks_server_credentials(
        self,
        viewer_client: TestClient,
        mock_config_root,
    ) -> None:
        payload = [
            {
                "kind": "server",
                "id": "srv_admin_example_22",
                "name": "admin@example:22",
                "host": "example",
                "port": 22,
                "username": "admin",
                "authMethod": "password",
                "password": "secret",
                "passphrase": "phrase",
                "createdAt": 1,
            }
        ]

        resp = viewer_client.post("/api/remote/connections/saved", json=payload)
        assert resp.status_code == 200

        resp = viewer_client.get("/api/remote/connections/saved")
        assert resp.status_code == 200
        server = resp.json()["connections"][0]
        assert "password" not in server
        assert "passphrase" not in server
        assert server["hasSavedPassword"] is True
        assert server["hasSavedPassphrase"] is True

    def test_saved_connections_round_trip_preserves_existing_password(
        self,
        viewer_client: TestClient,
        mock_config_root,
    ) -> None:
        initial = [
            {
                "kind": "server",
                "id": "srv_admin_example_22",
                "name": "admin@example:22",
                "host": "example",
                "port": 22,
                "username": "admin",
                "authMethod": "password",
                "password": "secret",
                "createdAt": 1,
            },
            {
                "kind": "connection",
                "id": "profile1",
                "serverId": "srv_admin_example_22",
                "name": "Profile",
                "createdAt": 1,
            },
        ]
        masked_update = [
            {
                "kind": "server",
                "id": "srv_admin_example_22",
                "name": "renamed",
                "host": "example",
                "port": 22,
                "username": "admin",
                "authMethod": "password",
                "hasSavedPassword": True,
                "createdAt": 1,
            },
            initial[1],
        ]

        assert viewer_client.post("/api/remote/connections/saved", json=initial).status_code == 200
        assert viewer_client.post("/api/remote/connections/saved", json=masked_update).status_code == 200

        connections_path = mock_config_root / "connections.json"
        persisted = json.loads(connections_path.read_text(encoding="utf-8"))
        server = next(item for item in persisted if item.get("kind") == "server")
        assert server["password"]

    def test_saved_connections_can_clear_existing_password_and_passphrase(
        self,
        viewer_client: TestClient,
        mock_config_root,
    ) -> None:
        initial = [
            {
                "kind": "server",
                "id": "srv_admin_example_22",
                "name": "admin@example:22",
                "host": "example",
                "port": 22,
                "username": "admin",
                "authMethod": "key",
                "password": "secret",
                "privateKeyPath": "~/.ssh/id_ed25519",
                "passphrase": "phrase",
                "hasSavedPassword": True,
                "hasSavedPassphrase": True,
                "createdAt": 1,
            }
        ]
        cleared = [
            {
                "kind": "server",
                "id": "srv_admin_example_22",
                "name": "admin@example:22",
                "host": "example",
                "port": 22,
                "username": "admin",
                "authMethod": "key",
                "password": None,
                "privateKeyPath": "~/.ssh/id_ed25519",
                "passphrase": None,
                "hasSavedPassword": False,
                "hasSavedPassphrase": False,
                "createdAt": 1,
            }
        ]

        assert viewer_client.post("/api/remote/connections/saved", json=initial).status_code == 200
        assert viewer_client.post("/api/remote/connections/saved", json=cleared).status_code == 200

        connections_path = mock_config_root / "connections.json"
        persisted = json.loads(connections_path.read_text(encoding="utf-8"))
        server = next(item for item in persisted if item.get("kind") == "server")
        assert "password" not in server or server["password"] is None
        assert "passphrase" not in server or server["passphrase"] is None

    def test_saved_connections_can_clear_password_when_switching_to_key_auth(
        self,
        viewer_client: TestClient,
        mock_config_root,
    ) -> None:
        initial = [
            {
                "kind": "server",
                "id": "srv_admin_example_22",
                "name": "admin@example:22",
                "host": "example",
                "port": 22,
                "username": "admin",
                "authMethod": "password",
                "password": "secret",
                "hasSavedPassword": True,
                "createdAt": 1,
            }
        ]
        switched = [
            {
                "kind": "server",
                "id": "srv_admin_example_22",
                "name": "admin@example:22",
                "host": "example",
                "port": 22,
                "username": "admin",
                "authMethod": "key",
                "password": None,
                "privateKeyPath": "~/.ssh/id_ed25519",
                "hasSavedPassword": False,
                "hasSavedPrivateKey": True,
                "createdAt": 1,
            }
        ]

        assert viewer_client.post("/api/remote/connections/saved", json=initial).status_code == 200
        assert viewer_client.post("/api/remote/connections/saved", json=switched).status_code == 200

        connections_path = mock_config_root / "connections.json"
        persisted = json.loads(connections_path.read_text(encoding="utf-8"))
        server = next(item for item in persisted if item.get("kind") == "server")
        assert "password" not in server or server["password"] is None
        assert server["privateKeyPath"] == "~/.ssh/id_ed25519"

    def test_connect_remote_can_use_saved_server_credentials(
        self,
        viewer_client: TestClient,
        mock_config_root,
    ) -> None:
        viewer_client.post(
            "/api/remote/connections/saved",
            json=[
                {
                    "kind": "server",
                    "id": "srv_admin_example_22",
                    "name": "admin@example:22",
                    "host": "example.com",
                    "port": 22,
                    "username": "admin",
                    "authMethod": "password",
                    "password": "secret",
                    "createdAt": 1,
                }
            ],
        )
        pool = _FakePool(_FakeConnection())
        viewer_client.app.state.connection_pool = pool

        resp = viewer_client.post(
            "/api/remote/connect",
            json={
                "host": "example.com",
                "port": 22,
                "username": "admin",
                "saved_server_id": "srv_admin_example_22",
            },
        )

        assert resp.status_code == 200
        assert pool.last_config.password == "secret"

    def test_start_remote_viewer_can_use_saved_server_credentials(
        self,
        viewer_client: TestClient,
        mock_config_root,
    ) -> None:
        viewer_client.post(
            "/api/remote/connections/saved",
            json=[
                {
                    "kind": "server",
                    "id": "srv_admin_example_22",
                    "name": "admin@example:22",
                    "host": "example.com",
                    "port": 22,
                    "username": "admin",
                    "authMethod": "password",
                    "password": "secret",
                    "createdAt": 1,
                }
            ],
        )
        pool = _FakePool(_FakeConnection())
        manager = _FakeViewerManager()
        viewer_client.app.state.connection_pool = pool
        viewer_client.app.state.viewer_manager = manager

        resp = viewer_client.post(
            "/api/remote/viewer/start",
            json={
                "host": "example.com",
                "port": 22,
                "username": "admin",
                "saved_server_id": "srv_admin_example_22",
                "remote_root": "/tmp/runicorn",
            },
        )

        assert resp.status_code == 200
        assert pool.last_config.password == "secret"
        assert manager.last_start_kwargs is not None
        assert manager.last_start_kwargs["remote_root"] == "/tmp/runicorn"

    def test_connect_remote_can_use_saved_server_private_key_path(
        self,
        viewer_client: TestClient,
        mock_config_root,
    ) -> None:
        viewer_client.post(
            "/api/remote/connections/saved",
            json=[
                {
                    "kind": "server",
                    "id": "srv_admin_example_22",
                    "name": "admin@example:22",
                    "host": "example.com",
                    "port": 22,
                    "username": "admin",
                    "authMethod": "key",
                    "privateKeyPath": "~/.ssh/id_ed25519",
                    "createdAt": 1,
                }
            ],
        )
        pool = _FakePool(_FakeConnection())
        viewer_client.app.state.connection_pool = pool

        resp = viewer_client.post(
            "/api/remote/connect",
            json={
                "host": "example.com",
                "port": 22,
                "username": "admin",
                "saved_server_id": "srv_admin_example_22",
            },
        )

        assert resp.status_code == 200
        assert pool.last_config.private_key_path == "~/.ssh/id_ed25519"

    def test_get_saved_connections_normalizes_private_key_path_field(
        self,
        viewer_client: TestClient,
        mock_config_root,
    ) -> None:
        connections_path = mock_config_root / "connections.json"
        connections_path.write_text(
            json.dumps(
                [
                    {
                        "kind": "server",
                        "id": "srv_admin_example_22",
                        "name": "admin@example:22",
                        "host": "example.com",
                        "port": 22,
                        "username": "admin",
                        "authMethod": "key",
                        "private_key_path": "~/.ssh/id_ed25519",
                        "createdAt": 1,
                    }
                ]
            ),
            encoding="utf-8",
        )

        resp = viewer_client.get("/api/remote/connections/saved")

        assert resp.status_code == 200
        server = resp.json()["connections"][0]
        assert server["privateKeyPath"] == "~/.ssh/id_ed25519"
        assert "private_key_path" not in server
