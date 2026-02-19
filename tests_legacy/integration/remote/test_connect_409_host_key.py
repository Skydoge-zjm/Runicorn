from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from runicorn.remote.host_key import HostKeyConfirmationRequiredError, HostKeyProblem
from runicorn.viewer.api.remote import router as remote_router


pytestmark = pytest.mark.integration


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(remote_router, prefix="/api")
    return app


class _FakePool:
    def __init__(self, exc: BaseException):
        self._exc = exc

    def get_or_create(self, _config):
        raise self._exc


def test_remote_connect_returns_409_with_payload() -> None:
    problem = HostKeyProblem(
        host="example.com",
        port=22,
        known_hosts_host="example.com",
        key_type="ssh-ed25519",
        fingerprint_sha256="SHA256:abc",
        public_key="ssh-ed25519 AAAA",
        reason="unknown",
        expected_fingerprint_sha256=None,
        expected_public_key=None,
    )

    app = _make_app()
    app.state.connection_pool = _FakePool(HostKeyConfirmationRequiredError(problem))

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

        assert r.status_code == 409
        detail = r.json()["detail"]
        assert detail["code"] == "HOST_KEY_CONFIRMATION_REQUIRED"
        assert detail["message"]
        host_key = detail["host_key"]
        assert host_key["host"] == "example.com"
        assert host_key["port"] == 22
        assert host_key["known_hosts_host"] == "example.com"
        assert host_key["key_type"] == "ssh-ed25519"
        assert host_key["fingerprint_sha256"] == "SHA256:abc"
        assert host_key["public_key"] == "ssh-ed25519 AAAA"
        assert host_key["reason"] == "unknown"


def test_remote_connect_409_changed_includes_expected_fields() -> None:
    problem = HostKeyProblem(
        host="example.com",
        port=22,
        known_hosts_host="example.com",
        key_type="ssh-ed25519",
        fingerprint_sha256="SHA256:new",
        public_key="ssh-ed25519 BBBB",
        reason="changed",
        expected_fingerprint_sha256="SHA256:old",
        expected_public_key="ssh-ed25519 AAAA",
    )

    app = _make_app()
    app.state.connection_pool = _FakePool(HostKeyConfirmationRequiredError(problem))

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

        assert r.status_code == 409
        detail = r.json()["detail"]
        host_key = detail["host_key"]
        assert host_key["reason"] == "changed"
        assert host_key["expected_fingerprint_sha256"] == "SHA256:old"
        assert host_key["expected_public_key"] == "ssh-ed25519 AAAA"
