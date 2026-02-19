from __future__ import annotations

import threading

import pytest

from runicorn.remote.ssh_backend import OpenSSHBackend


pytestmark = pytest.mark.unit


class _Conn:
    def __init__(self, *, password: str | None = None) -> None:
        self.config = type(
            "Cfg",
            (),
            {"host": "example.com", "port": 22, "username": "u", "password": password},
        )()


def test_openssh_backend_requires_ssh(monkeypatch, tmp_path) -> None:
    import runicorn.config as cfg_mod

    monkeypatch.setattr(cfg_mod, "get_known_hosts_file_path", lambda: tmp_path / "known_hosts")
    monkeypatch.setattr(OpenSSHBackend, "_resolve_ssh_path", staticmethod(lambda *_: None))

    backend = OpenSSHBackend()
    with pytest.raises(RuntimeError):
        backend.create_tunnel(
            connection=_Conn(password=None),
            local_port=12345,
            remote_host="127.0.0.1",
            remote_port=23300,
            stop_event=threading.Event(),
        )


def test_openssh_backend_requires_ssh_keyscan(monkeypatch, tmp_path) -> None:
    import runicorn.config as cfg_mod
    import runicorn.remote.ssh_backend as backend_mod

    monkeypatch.setattr(cfg_mod, "get_known_hosts_file_path", lambda: tmp_path / "known_hosts")
    monkeypatch.setattr(OpenSSHBackend, "_resolve_ssh_path", staticmethod(lambda *_: "ssh"))
    monkeypatch.setattr(backend_mod.shutil, "which", lambda name: None)

    backend = OpenSSHBackend()
    with pytest.raises(RuntimeError):
        backend.create_tunnel(
            connection=_Conn(password=None),
            local_port=12345,
            remote_host="127.0.0.1",
            remote_port=23300,
            stop_event=threading.Event(),
        )


def test_openssh_backend_rejects_password(monkeypatch, tmp_path) -> None:
    import runicorn.config as cfg_mod
    import runicorn.remote.ssh_backend as backend_mod

    monkeypatch.setattr(cfg_mod, "get_known_hosts_file_path", lambda: tmp_path / "known_hosts")
    monkeypatch.setattr(OpenSSHBackend, "_resolve_ssh_path", staticmethod(lambda *_: "ssh"))
    monkeypatch.setattr(backend_mod.shutil, "which", lambda name: "ssh-keyscan")

    backend = OpenSSHBackend()
    with pytest.raises(RuntimeError):
        backend.create_tunnel(
            connection=_Conn(password="pw"),
            local_port=12345,
            remote_host="127.0.0.1",
            remote_port=23300,
            stop_event=threading.Event(),
        )
