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


class _FakeConn:
    is_connected = True


class _FakePool:
    def __init__(self, *, conn=None, exc: BaseException | None = None):
        self._conn = conn
        self._exc = exc

    def get_or_create(self, config):
        if self._exc is not None:
            raise self._exc
        return self._conn


def test_remote_connect_success() -> None:
    app = _make_app()
    app.state.connection_pool = _FakePool(conn=_FakeConn())

    with TestClient(app) as client:
        r = client.post(
            "/api/remote/connect",
            json={
                "host": "example.com",
                "port": 22,
                "username": "u",
                "password": None,
                "private_key": None,
                "private_key_path": None,
                "passphrase": None,
                "use_agent": True,
            },
        )

        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["connection_id"] == "u@example.com:22"
        assert body["connected"] is True


def test_remote_connect_returns_500_on_generic_error() -> None:
    app = _make_app()
    app.state.connection_pool = _FakePool(exc=RuntimeError("boom"))

    with TestClient(app) as client:
        r = client.post(
            "/api/remote/connect",
            json={
                "host": "example.com",
                "port": 22,
                "username": "u",
                "password": None,
                "private_key": None,
                "private_key_path": None,
                "passphrase": None,
                "use_agent": True,
            },
        )

        assert r.status_code == 500
