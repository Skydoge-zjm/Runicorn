from __future__ import annotations

import base64

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from runicorn.remote.known_hosts import compute_fingerprint_sha256
from runicorn.viewer.api.remote import router as remote_router


pytestmark = pytest.mark.integration


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(remote_router, prefix="/api")
    return app


def _monkeypatch_known_hosts(tmp_path, monkeypatch) -> None:
    import runicorn.remote.known_hosts as known_hosts_mod

    monkeypatch.setattr(known_hosts_mod, "get_known_hosts_file_path", lambda: tmp_path / "known_hosts")


def test_known_hosts_accept_rejects_public_key_with_newline(tmp_path, monkeypatch) -> None:
    _monkeypatch_known_hosts(tmp_path, monkeypatch)

    key_base64 = base64.b64encode(b"abc").decode("ascii")
    app = _make_app()

    with TestClient(app) as client:
        r = client.post(
            "/api/remote/known-hosts/accept",
            json={
                "host": "example.com",
                "port": 22,
                "key_type": "ssh-ed25519",
                "public_key": f"ssh-ed25519 {key_base64}\n",
                "fingerprint_sha256": compute_fingerprint_sha256(b"abc"),
            },
        )
        assert r.status_code == 400


def test_known_hosts_accept_rejects_host_with_comma(tmp_path, monkeypatch) -> None:
    _monkeypatch_known_hosts(tmp_path, monkeypatch)

    key_base64 = base64.b64encode(b"abc").decode("ascii")
    app = _make_app()

    with TestClient(app) as client:
        r = client.post(
            "/api/remote/known-hosts/accept",
            json={
                "host": "example.com,evil.com",
                "port": 22,
                "key_type": "ssh-ed25519",
                "public_key": f"ssh-ed25519 {key_base64}",
                "fingerprint_sha256": compute_fingerprint_sha256(b"abc"),
            },
        )
        assert r.status_code == 400


def test_known_hosts_accept_rejects_fingerprint_mismatch(tmp_path, monkeypatch) -> None:
    _monkeypatch_known_hosts(tmp_path, monkeypatch)

    key_base64 = base64.b64encode(b"abc").decode("ascii")
    app = _make_app()

    with TestClient(app) as client:
        r = client.post(
            "/api/remote/known-hosts/accept",
            json={
                "host": "example.com",
                "port": 22,
                "key_type": "ssh-ed25519",
                "public_key": f"ssh-ed25519 {key_base64}",
                "fingerprint_sha256": "SHA256:not-real",
            },
        )
        assert r.status_code == 400


def test_known_hosts_accept_rejects_invalid_base64_public_key(tmp_path, monkeypatch) -> None:
    _monkeypatch_known_hosts(tmp_path, monkeypatch)

    app = _make_app()

    with TestClient(app) as client:
        r = client.post(
            "/api/remote/known-hosts/accept",
            json={
                "host": "example.com",
                "port": 22,
                "key_type": "ssh-ed25519",
                "public_key": "ssh-ed25519 !!!not-base64!!!",
                "fingerprint_sha256": "SHA256:any",
            },
        )
        assert r.status_code == 400
