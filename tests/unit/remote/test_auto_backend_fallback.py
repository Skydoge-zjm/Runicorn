from __future__ import annotations

import threading

import pytest

from runicorn.remote.host_key import HostKeyConfirmationRequiredError, HostKeyProblem
from runicorn.remote.ssh_backend import AutoBackend


pytestmark = pytest.mark.unit


class _DummyConnection:
    def __init__(self) -> None:
        self.config = type(
            "Cfg",
            (),
            {"host": "example.com", "port": 22, "username": "u"},
        )()


class _Backend:
    def __init__(self, *, exc: BaseException | None = None, tunnel: object | None = None):
        self.exc = exc
        self.tunnel = tunnel if tunnel is not None else object()
        self.called = 0

    def create_tunnel(self, **kwargs):
        self.called += 1
        if self.exc is not None:
            raise self.exc
        return self.tunnel


def _host_key_error() -> HostKeyConfirmationRequiredError:
    problem = HostKeyProblem(
        host="example.com",
        port=22,
        known_hosts_host="example.com",
        key_type="ssh-ed25519",
        fingerprint_sha256="SHA256:abc",
        public_key="ssh-ed25519 AAAA",
        reason="unknown",
    )
    return HostKeyConfirmationRequiredError(problem)


def test_auto_backend_falls_back_to_asyncssh() -> None:
    backend = AutoBackend()

    openssh = _Backend(exc=RuntimeError("no openssh"))
    asyncssh = _Backend(tunnel="async")
    paramiko = _Backend(tunnel="paramiko")

    backend._openssh = openssh
    backend._asyncssh = asyncssh
    backend._paramiko = paramiko

    tunnel = backend.create_tunnel(
        connection=_DummyConnection(),
        local_port=12345,
        remote_host="127.0.0.1",
        remote_port=23300,
        stop_event=threading.Event(),
    )

    assert tunnel == "async"
    assert openssh.called == 1
    assert asyncssh.called == 1
    assert paramiko.called == 0


def test_auto_backend_falls_back_to_paramiko() -> None:
    backend = AutoBackend()

    openssh = _Backend(exc=RuntimeError("no openssh"))
    asyncssh = _Backend(exc=RuntimeError("no asyncssh"))
    paramiko = _Backend(tunnel="paramiko")

    backend._openssh = openssh
    backend._asyncssh = asyncssh
    backend._paramiko = paramiko

    tunnel = backend.create_tunnel(
        connection=_DummyConnection(),
        local_port=12345,
        remote_host="127.0.0.1",
        remote_port=23300,
        stop_event=threading.Event(),
    )

    assert tunnel == "paramiko"
    assert openssh.called == 1
    assert asyncssh.called == 1
    assert paramiko.called == 1


def test_auto_backend_does_not_fallback_on_host_key_confirmation() -> None:
    backend = AutoBackend()

    openssh = _Backend(exc=_host_key_error())
    asyncssh = _Backend(tunnel="async")
    paramiko = _Backend(tunnel="paramiko")

    backend._openssh = openssh
    backend._asyncssh = asyncssh
    backend._paramiko = paramiko

    with pytest.raises(HostKeyConfirmationRequiredError):
        backend.create_tunnel(
            connection=_DummyConnection(),
            local_port=12345,
            remote_host="127.0.0.1",
            remote_port=23300,
            stop_event=threading.Event(),
        )

    assert openssh.called == 1
    assert asyncssh.called == 0
    assert paramiko.called == 0
