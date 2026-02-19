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


def test_known_hosts_accept_list_remove_roundtrip(tmp_path, monkeypatch) -> None:
    import runicorn.remote.known_hosts as known_hosts_mod

    monkeypatch.setattr(known_hosts_mod, "get_known_hosts_file_path", lambda: tmp_path / "known_hosts")

    key_bytes = b"abc"
    key_base64 = base64.b64encode(key_bytes).decode("ascii")
    public_key = f"ssh-ed25519 {key_base64}"

    payload = {
        "host": "example.com",
        "port": 22,
        "key_type": "ssh-ed25519",
        "public_key": public_key,
        "fingerprint_sha256": compute_fingerprint_sha256(key_bytes),
    }

    app = _make_app()
    with TestClient(app) as client:
        r = client.post("/api/remote/known-hosts/accept", json=payload)
        assert r.status_code == 200
        assert r.json() == {"ok": True}

        r = client.get("/api/remote/known-hosts/list")
        assert r.status_code == 200
        body = r.json()
        assert "entries" in body
        assert len(body["entries"]) == 1
        entry = body["entries"][0]
        assert entry["host"] == "example.com"
        assert entry["port"] == 22
        assert entry["key_type"] == "ssh-ed25519"
        assert entry["key_base64"] == key_base64
        assert entry["fingerprint_sha256"] == payload["fingerprint_sha256"]

        r = client.post(
            "/api/remote/known-hosts/remove",
            json={"host": "example.com", "port": 22, "key_type": "ssh-ed25519"},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert r.json()["changed"] is True

        r = client.get("/api/remote/known-hosts/list")
        assert r.status_code == 200
        assert r.json()["entries"] == []


def test_known_hosts_accept_rejects_key_type_mismatch(tmp_path, monkeypatch) -> None:
    import runicorn.remote.known_hosts as known_hosts_mod

    monkeypatch.setattr(known_hosts_mod, "get_known_hosts_file_path", lambda: tmp_path / "known_hosts")

    key_bytes = b"abc"
    key_base64 = base64.b64encode(key_bytes).decode("ascii")

    app = _make_app()
    with TestClient(app) as client:
        r = client.post(
            "/api/remote/known-hosts/accept",
            json={
                "host": "example.com",
                "port": 22,
                "key_type": "ssh-rsa",
                "public_key": f"ssh-ed25519 {key_base64}",
                "fingerprint_sha256": compute_fingerprint_sha256(key_bytes),
            },
        )
        assert r.status_code == 400


def test_known_hosts_accept_rejects_host_with_whitespace(tmp_path, monkeypatch) -> None:
    import runicorn.remote.known_hosts as known_hosts_mod

    monkeypatch.setattr(known_hosts_mod, "get_known_hosts_file_path", lambda: tmp_path / "known_hosts")

    key_bytes = b"abc"
    key_base64 = base64.b64encode(key_bytes).decode("ascii")

    app = _make_app()
    with TestClient(app) as client:
        r = client.post(
            "/api/remote/known-hosts/accept",
            json={
                "host": "bad host",
                "port": 22,
                "key_type": "ssh-ed25519",
                "public_key": f"ssh-ed25519 {key_base64}",
                "fingerprint_sha256": compute_fingerprint_sha256(key_bytes),
            },
        )
        assert r.status_code == 400
