from __future__ import annotations

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from runicorn.remote.host_key import HostKeyConfirmationRequiredError, HostKeyProblem
from runicorn.remote.ssh_backend import AutoBackend
from runicorn.viewer.api.remote import router as remote_router


pytestmark = pytest.mark.integration


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(remote_router, prefix="/api")
    return app


class _FakeConn:
    def __init__(self, *, host: str = "example.com", port: int = 22, username: str = "u") -> None:
        self.config = type("Cfg", (), {"host": host, "port": port, "username": username})()

    @property
    def is_connected(self) -> bool:
        return True

    def exec_command(self, _cmd: str, timeout: int | None = None):
        return ("0.0.0\n", "", 0)


class _FakePool:
    def __init__(self, conn: _FakeConn, *, exc: BaseException | None = None) -> None:
        self._conn = conn
        self._exc = exc

    def get_or_create(self, _config):
        if self._exc is not None:
            raise self._exc
        return self._conn


class _BlockingTunnel:
    def __init__(self, *, stop_event, start_exc: BaseException | None = None) -> None:
        self._stop_event = stop_event
        self._start_exc = start_exc

    def start(self) -> None:
        if self._start_exc is not None:
            raise self._start_exc
        while not self._stop_event.is_set():
            time.sleep(0.01)


class _Backend:
    def __init__(self, name: str, calls: list[str], *, create_exc: BaseException | None = None, start_exc: BaseException | None = None):
        self._name = name
        self._calls = calls
        self._create_exc = create_exc
        self._start_exc = start_exc

    def create_tunnel(
        self,
        *,
        connection,
        local_port: int,
        remote_host: str,
        remote_port: int,
        stop_event,
    ):
        self._calls.append(self._name)
        if self._create_exc is not None:
            raise self._create_exc
        return _BlockingTunnel(stop_event=stop_event, start_exc=self._start_exc)


def _patch_manager_fast_paths(monkeypatch, manager):
    import runicorn.remote.viewer.manager as manager_mod

    monkeypatch.setattr(manager_mod.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(manager_mod, "find_available_port", lambda: 18080)

    monkeypatch.setattr(manager, "_find_python", lambda _conn: "python3")
    monkeypatch.setattr(manager, "_find_remote_available_port", lambda _conn, *_a, **_k: 19090)
    monkeypatch.setattr(manager, "_start_remote_viewer_process", lambda *_a, **_k: 12345)
    monkeypatch.setattr(manager, "_check_remote_viewer_health", lambda *_a, **_k: True)
    monkeypatch.setattr(manager, "_cleanup_remote_viewer", lambda *_a, **_k: None)


def test_remote_viewer_start_success_and_uses_openssh_first(monkeypatch) -> None:
    from runicorn.remote.viewer.manager import RemoteViewerManager

    calls: list[str] = []
    openssh = _Backend("openssh", calls)
    backend = AutoBackend(openssh_backend=openssh)
    backend._asyncssh = _Backend("asyncssh", calls)  # type: ignore[attr-defined]
    backend._paramiko = _Backend("paramiko", calls)  # type: ignore[attr-defined]

    manager = RemoteViewerManager(backend=backend)
    _patch_manager_fast_paths(monkeypatch, manager)

    app = _make_app()
    app.state.connection_pool = _FakePool(_FakeConn())
    app.state.viewer_manager = manager

    with TestClient(app) as client:
        r = client.post(
            "/api/remote/viewer/start",
            json={
                "host": "example.com",
                "port": 22,
                "username": "u",
                "password": None,
                "private_key": None,
                "private_key_path": None,
                "passphrase": None,
                "use_agent": True,
                "remote_root": "/tmp/runicorn",
                "local_port": None,
                "remote_port": None,
                "conda_env": None,
            },
        )

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["session"]["localPort"] == 18080
    assert body["session"]["remotePort"] == 19090
    assert body["session"]["status"] == "running"
    assert calls[:1] == ["openssh"]

    manager.stop_remote_viewer(body["session"]["sessionId"])


def test_remote_viewer_start_falls_back_to_asyncssh_when_openssh_fails(monkeypatch) -> None:
    from runicorn.remote.viewer.manager import RemoteViewerManager

    calls: list[str] = []
    openssh = _Backend("openssh", calls, create_exc=RuntimeError("no ssh"))
    backend = AutoBackend(openssh_backend=openssh)
    backend._asyncssh = _Backend("asyncssh", calls)  # type: ignore[attr-defined]
    backend._paramiko = _Backend("paramiko", calls)  # type: ignore[attr-defined]

    manager = RemoteViewerManager(backend=backend)
    _patch_manager_fast_paths(monkeypatch, manager)

    app = _make_app()
    app.state.connection_pool = _FakePool(_FakeConn())
    app.state.viewer_manager = manager

    with TestClient(app) as client:
        r = client.post(
            "/api/remote/viewer/start",
            json={
                "host": "example.com",
                "port": 22,
                "username": "u",
                "password": None,
                "private_key": None,
                "private_key_path": None,
                "passphrase": None,
                "use_agent": True,
                "remote_root": "/tmp/runicorn",
                "local_port": None,
                "remote_port": None,
                "conda_env": None,
            },
        )

    assert r.status_code == 200
    assert calls[:2] == ["openssh", "asyncssh"]

    manager.stop_remote_viewer(r.json()["session"]["sessionId"])


def test_remote_viewer_start_falls_back_to_paramiko_when_asyncssh_also_fails(monkeypatch) -> None:
    from runicorn.remote.viewer.manager import RemoteViewerManager

    calls: list[str] = []
    openssh = _Backend("openssh", calls, create_exc=RuntimeError("no ssh"))
    backend = AutoBackend(openssh_backend=openssh)
    backend._asyncssh = _Backend("asyncssh", calls, create_exc=RuntimeError("no asyncssh"))  # type: ignore[attr-defined]
    backend._paramiko = _Backend("paramiko", calls)  # type: ignore[attr-defined]

    manager = RemoteViewerManager(backend=backend)
    _patch_manager_fast_paths(monkeypatch, manager)

    app = _make_app()
    app.state.connection_pool = _FakePool(_FakeConn())
    app.state.viewer_manager = manager

    with TestClient(app) as client:
        r = client.post(
            "/api/remote/viewer/start",
            json={
                "host": "example.com",
                "port": 22,
                "username": "u",
                "password": None,
                "private_key": None,
                "private_key_path": None,
                "passphrase": None,
                "use_agent": True,
                "remote_root": "/tmp/runicorn",
                "local_port": None,
                "remote_port": None,
                "conda_env": None,
            },
        )

    assert r.status_code == 200
    assert calls[:3] == ["openssh", "asyncssh", "paramiko"]

    manager.stop_remote_viewer(r.json()["session"]["sessionId"])


def test_remote_viewer_start_returns_409_and_does_not_fallback_on_host_key_error(monkeypatch) -> None:
    from runicorn.remote.viewer.manager import RemoteViewerManager

    calls: list[str] = []
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

    openssh = _Backend("openssh", calls, create_exc=HostKeyConfirmationRequiredError(problem))
    backend = AutoBackend(openssh_backend=openssh)
    backend._asyncssh = _Backend("asyncssh", calls)  # type: ignore[attr-defined]
    backend._paramiko = _Backend("paramiko", calls)  # type: ignore[attr-defined]

    manager = RemoteViewerManager(backend=backend)
    _patch_manager_fast_paths(monkeypatch, manager)

    app = _make_app()
    app.state.connection_pool = _FakePool(_FakeConn())
    app.state.viewer_manager = manager

    with TestClient(app) as client:
        r = client.post(
            "/api/remote/viewer/start",
            json={
                "host": "example.com",
                "port": 22,
                "username": "u",
                "password": None,
                "private_key": None,
                "private_key_path": None,
                "passphrase": None,
                "use_agent": True,
                "remote_root": "/tmp/runicorn",
                "local_port": None,
                "remote_port": None,
                "conda_env": None,
            },
        )

    assert r.status_code == 409
    assert calls == ["openssh"]
    detail = r.json()["detail"]
    assert detail["code"] == "HOST_KEY_CONFIRMATION_REQUIRED"
    assert detail["host_key"]["fingerprint_sha256"] == "SHA256:abc"


def test_remote_viewer_start_returns_500_on_tunnel_start_error(monkeypatch) -> None:
    from runicorn.remote.viewer.manager import RemoteViewerManager

    calls: list[str] = []
    openssh = _Backend("openssh", calls, start_exc=RuntimeError("tunnel died"))
    backend = AutoBackend(openssh_backend=openssh)
    backend._asyncssh = _Backend("asyncssh", calls)  # type: ignore[attr-defined]
    backend._paramiko = _Backend("paramiko", calls)  # type: ignore[attr-defined]

    manager = RemoteViewerManager(backend=backend)
    _patch_manager_fast_paths(monkeypatch, manager)

    app = _make_app()
    app.state.connection_pool = _FakePool(_FakeConn())
    app.state.viewer_manager = manager

    with TestClient(app) as client:
        r = client.post(
            "/api/remote/viewer/start",
            json={
                "host": "example.com",
                "port": 22,
                "username": "u",
                "password": None,
                "private_key": None,
                "private_key_path": None,
                "passphrase": None,
                "use_agent": True,
                "remote_root": "/tmp/runicorn",
                "local_port": None,
                "remote_port": None,
                "conda_env": None,
            },
        )

    assert r.status_code == 500
    assert calls[:1] == ["openssh"]
