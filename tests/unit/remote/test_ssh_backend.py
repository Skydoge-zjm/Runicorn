"""Unit tests for runicorn.remote.ssh_backend (migrated from tests_legacy)."""
from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

from runicorn.remote.host_key import HostKeyConfirmationRequiredError, HostKeyProblem
from runicorn.remote.ssh_backend import AutoBackend, OpenSSHBackend


# === Helpers ===

class _DummyConnection:
    def __init__(self, *, password=None):
        self.config = type("Cfg", (), {
            "host": "example.com", "port": 22, "username": "u", "password": password,
        })()


class _Backend:
    def __init__(self, *, exc=None, tunnel=None):
        self.exc = exc
        self.tunnel = tunnel if tunnel is not None else object()
        self.called = 0

    def create_tunnel(self, **kwargs):
        self.called += 1
        if self.exc is not None:
            raise self.exc
        return self.tunnel


def _host_key_error():
    problem = HostKeyProblem(
        host="example.com", port=22, known_hosts_host="example.com",
        key_type="ssh-ed25519", fingerprint_sha256="SHA256:abc",
        public_key="ssh-ed25519 AAAA", reason="unknown",
    )
    return HostKeyConfirmationRequiredError(problem)


_TUNNEL_KWARGS = dict(
    connection=_DummyConnection(),
    local_port=12345, remote_host="127.0.0.1", remote_port=23300,
    stop_event=threading.Event(),
)


# === AutoBackend fallback chain ===

class TestAutoBackendFallback:
    def test_falls_back_to_asyncssh(self):
        ab = AutoBackend()
        ab._openssh = _Backend(exc=RuntimeError("no openssh"))
        ab._asyncssh = _Backend(tunnel="async")
        ab._paramiko = _Backend(tunnel="paramiko")

        assert ab.create_tunnel(**_TUNNEL_KWARGS) == "async"
        assert ab._openssh.called == 1
        assert ab._asyncssh.called == 1
        assert ab._paramiko.called == 0

    def test_falls_back_to_paramiko(self):
        ab = AutoBackend()
        ab._openssh = _Backend(exc=RuntimeError("no"))
        ab._asyncssh = _Backend(exc=RuntimeError("no"))
        ab._paramiko = _Backend(tunnel="paramiko")

        assert ab.create_tunnel(**_TUNNEL_KWARGS) == "paramiko"
        assert ab._paramiko.called == 1

    def test_no_fallback_on_host_key_confirmation(self):
        ab = AutoBackend()
        ab._openssh = _Backend(exc=_host_key_error())
        ab._asyncssh = _Backend(tunnel="async")
        ab._paramiko = _Backend(tunnel="paramiko")

        with pytest.raises(HostKeyConfirmationRequiredError):
            ab.create_tunnel(**_TUNNEL_KWARGS)
        assert ab._asyncssh.called == 0
        assert ab._paramiko.called == 0


# === OpenSSH preconditions ===

class TestOpenSSHPreconditions:
    def test_requires_ssh(self, monkeypatch, tmp_path):
        import runicorn.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "get_known_hosts_file_path", lambda: tmp_path / "known_hosts")
        monkeypatch.setattr(OpenSSHBackend, "_resolve_ssh_path", staticmethod(lambda *_: None))

        with pytest.raises(RuntimeError):
            OpenSSHBackend().create_tunnel(
                connection=_DummyConnection(), local_port=1, remote_host="x",
                remote_port=2, stop_event=threading.Event(),
            )

    def test_requires_ssh_keyscan(self, monkeypatch, tmp_path):
        import runicorn.config as cfg_mod
        import runicorn.remote.ssh_backend as bmod
        monkeypatch.setattr(cfg_mod, "get_known_hosts_file_path", lambda: tmp_path / "known_hosts")
        monkeypatch.setattr(OpenSSHBackend, "_resolve_ssh_path", staticmethod(lambda *_: "ssh"))
        monkeypatch.setattr(bmod.shutil, "which", lambda name: None)

        with pytest.raises(RuntimeError):
            OpenSSHBackend().create_tunnel(
                connection=_DummyConnection(), local_port=1, remote_host="x",
                remote_port=2, stop_event=threading.Event(),
            )

    def test_rejects_password(self, monkeypatch, tmp_path):
        import runicorn.config as cfg_mod
        import runicorn.remote.ssh_backend as bmod
        monkeypatch.setattr(cfg_mod, "get_known_hosts_file_path", lambda: tmp_path / "known_hosts")
        monkeypatch.setattr(OpenSSHBackend, "_resolve_ssh_path", staticmethod(lambda *_: "ssh"))
        monkeypatch.setattr(bmod.shutil, "which", lambda name: "ssh-keyscan")

        with pytest.raises(RuntimeError):
            OpenSSHBackend().create_tunnel(
                connection=_DummyConnection(password="pw"), local_port=1,
                remote_host="x", remote_port=2, stop_event=threading.Event(),
            )


# === resolve_ssh_path ===

class TestResolveSshPath:
    def test_uses_explicit_path(self, tmp_path, monkeypatch):
        fake = tmp_path / "ssh"
        fake.write_text("x", encoding="utf-8")
        monkeypatch.setattr(
            "runicorn.remote.ssh_backend.subprocess.run",
            lambda *a, **kw: SimpleNamespace(returncode=0, stderr="OpenSSH_9.0"),
        )
        assert OpenSSHBackend._resolve_ssh_path(str(fake)) == str(fake)

    def test_uses_env_var(self, tmp_path, monkeypatch):
        fake = tmp_path / "ssh"
        fake.write_text("x", encoding="utf-8")
        monkeypatch.setenv("RUNICORN_SSH_PATH", str(fake))
        monkeypatch.setattr(
            "runicorn.remote.ssh_backend.subprocess.run",
            lambda *a, **kw: SimpleNamespace(returncode=0, stderr="OpenSSH_9.0"),
        )
        monkeypatch.setattr("runicorn.remote.ssh_backend.shutil.which", lambda n: None)
        assert OpenSSHBackend._resolve_ssh_path(None) == str(fake)

    def test_falls_back_to_which(self, monkeypatch):
        monkeypatch.delenv("RUNICORN_SSH_PATH", raising=False)
        monkeypatch.setattr("runicorn.remote.ssh_backend.shutil.which", lambda n: "ssh")
        monkeypatch.setattr(
            "runicorn.remote.ssh_backend.subprocess.run",
            lambda *a, **kw: SimpleNamespace(returncode=255, stderr="OpenSSH"),
        )
        assert OpenSSHBackend._resolve_ssh_path(None) == "ssh"

    def test_returns_none_when_all_fail(self, monkeypatch):
        monkeypatch.delenv("RUNICORN_SSH_PATH", raising=False)
        monkeypatch.setattr("runicorn.remote.ssh_backend.shutil.which", lambda n: None)
        monkeypatch.setattr(
            "runicorn.remote.ssh_backend.subprocess.run",
            lambda *a, **kw: SimpleNamespace(returncode=1, stderr=""),
        )
        assert OpenSSHBackend._resolve_ssh_path(None) is None
