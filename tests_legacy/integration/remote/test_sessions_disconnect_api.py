from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from runicorn.viewer.api.remote import router as remote_router


pytestmark = pytest.mark.integration


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(remote_router, prefix="/api")
    return app


class _FakePool:
    def __init__(
        self,
        *,
        connections: list[dict] | None = None,
        removed: bool = False,
        list_exc: BaseException | None = None,
        remove_exc: BaseException | None = None,
    ):
        self._connections = connections or []
        self._removed = removed
        self._list_exc = list_exc
        self._remove_exc = remove_exc

    def list_connections(self):
        if self._list_exc is not None:
            raise self._list_exc
        return self._connections

    def remove(self, host: str, port: int, username: str) -> bool:
        if self._remove_exc is not None:
            raise self._remove_exc
        return self._removed


def test_remote_sessions_returns_empty_when_no_pool() -> None:
    app = _make_app()

    with TestClient(app) as client:
        r = client.get("/api/remote/sessions")

    assert r.status_code == 200
    assert r.json() == {"sessions": []}


def test_remote_sessions_returns_list_from_pool() -> None:
    app = _make_app()
    app.state.connection_pool = _FakePool(
        connections=[
            {"key": "u@example.com:22", "host": "example.com", "port": 22, "username": "u", "connected": True},
            {"key": "v@foo:2222", "host": "foo", "port": 2222, "username": "v", "connected": False},
        ]
    )

    with TestClient(app) as client:
        r = client.get("/api/remote/sessions")

    assert r.status_code == 200
    body = r.json()
    assert "sessions" in body
    assert body["sessions"][0]["key"] == "u@example.com:22"


def test_remote_sessions_returns_500_when_pool_raises() -> None:
    app = _make_app()
    app.state.connection_pool = _FakePool(list_exc=RuntimeError("boom"))

    with TestClient(app) as client:
        r = client.get("/api/remote/sessions")

    assert r.status_code == 500


def test_remote_disconnect_returns_false_when_no_pool() -> None:
    app = _make_app()

    with TestClient(app) as client:
        r = client.post(
            "/api/remote/disconnect",
            json={"host": "example.com", "port": 22, "username": "u"},
        )

    assert r.status_code == 200
    assert r.json()["ok"] is False


def test_remote_disconnect_success() -> None:
    app = _make_app()
    app.state.connection_pool = _FakePool(removed=True)

    with TestClient(app) as client:
        r = client.post(
            "/api/remote/disconnect",
            json={"host": "example.com", "port": 22, "username": "u"},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "removed" in body["message"].lower()


def test_remote_disconnect_not_found() -> None:
    app = _make_app()
    app.state.connection_pool = _FakePool(removed=False)

    with TestClient(app) as client:
        r = client.post(
            "/api/remote/disconnect",
            json={"host": "example.com", "port": 22, "username": "u"},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert "not found" in body["message"].lower()


def test_remote_disconnect_returns_500_when_pool_raises() -> None:
    app = _make_app()
    app.state.connection_pool = _FakePool(remove_exc=RuntimeError("boom"))

    with TestClient(app) as client:
        r = client.post(
            "/api/remote/disconnect",
            json={"host": "example.com", "port": 22, "username": "u"},
        )

    assert r.status_code == 500
