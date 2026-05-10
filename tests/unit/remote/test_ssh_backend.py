"""Unit tests for runicorn.remote.ssh_backend (migrated from tests_legacy)."""
from __future__ import annotations

import os
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from runicorn.remote.connection import SSHConfig, SSHConnectionPool
from runicorn.remote.host_key import HostKeyConfirmationRequiredError, HostKeyProblem
from runicorn.remote.ssh_backend import (
    AutoBackend,
    OpenSSHBackend,
    OpenSSHCommandConnection,
    OpenSSHFallbackError,
    _OpenSSHAskpassHelper,
)


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
        self.kwargs = None

    def create_tunnel(self, **kwargs):
        self.called += 1
        self.kwargs = kwargs
        if self.exc is not None:
            raise self.exc
        return self.tunnel


class _ConnectBackend:
    def __init__(self, *, exc=None, connection=None):
        self.exc = exc
        self.connection = connection if connection is not None else object()
        self.called = 0
        self.config = None

    def connect(self, config):
        self.called += 1
        self.config = config
        if self.exc is not None:
            raise self.exc
        return self.connection


class _PoolConnection:
    def __init__(self, config):
        self.config = config
        self.env_cache = {}
        self._connected = True
        self.disconnected = False

    def connect(self):
        self._connected = True
        return True

    def disconnect(self):
        self.disconnected = True
        self._connected = False

    def exec_command(self, command, timeout=None):
        return "", "", 0

    def get_sftp(self):
        return object()

    @property
    def is_connected(self):
        return self._connected


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
        ab._openssh = _Backend(exc=OpenSSHFallbackError("no openssh"))
        ab._asyncssh = _Backend(tunnel="async")
        ab._paramiko = _Backend(tunnel="paramiko")

        assert ab.create_tunnel(**_TUNNEL_KWARGS) == "async"
        assert ab._openssh.called == 1
        assert ab._asyncssh.called == 1
        assert ab._paramiko.called == 0

    def test_falls_back_to_paramiko(self):
        ab = AutoBackend()
        ab._openssh = _Backend(exc=OpenSSHFallbackError("no"))
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

    def test_paramiko_tunnel_fallback_uses_connection_fallback(self):
        ab = AutoBackend()
        paramiko_connection = _DummyConnection()
        connection = _DummyConnection()
        connection.get_paramiko_fallback_connection = lambda: paramiko_connection
        tunnel_kwargs = dict(_TUNNEL_KWARGS, connection=connection)

        ab._openssh = _Backend(exc=OpenSSHFallbackError("no openssh"))
        ab._asyncssh = _Backend(exc=RuntimeError("no asyncssh"))
        ab._paramiko = _Backend(tunnel="paramiko")

        assert ab.create_tunnel(**tunnel_kwargs) == "paramiko"
        assert ab._paramiko.kwargs["connection"] is paramiko_connection


class TestAutoBackendConnect:
    def test_prefers_openssh_connection(self):
        cfg = SSHConfig(host="example.com", username="u")
        openssh_conn = object()
        ab = AutoBackend()
        ab._openssh = _ConnectBackend(connection=openssh_conn)
        ab._paramiko = _ConnectBackend(connection=object())

        assert ab.connect(cfg) is openssh_conn
        assert ab._openssh.called == 1
        assert ab._paramiko.called == 0

    def test_falls_back_to_paramiko_when_openssh_connect_fails(self):
        cfg = SSHConfig(host="example.com", username="u")
        paramiko_conn = object()
        ab = AutoBackend()
        ab._openssh = _ConnectBackend(exc=OpenSSHFallbackError("unsupported"))
        ab._paramiko = _ConnectBackend(connection=paramiko_conn)

        assert ab.connect(cfg) is paramiko_conn
        assert ab._openssh.called == 1
        assert ab._paramiko.called == 1

    def test_no_connect_fallback_on_openssh_connection_error(self):
        cfg = SSHConfig(host="example.com", username="u", password="pw")
        ab = AutoBackend()
        ab._openssh = _ConnectBackend(exc=RuntimeError("Permission denied"))
        ab._paramiko = _ConnectBackend(connection=object())

        with pytest.raises(RuntimeError):
            ab.connect(cfg)
        assert ab._paramiko.called == 0

    def test_no_connect_fallback_on_host_key_confirmation(self):
        cfg = SSHConfig(host="example.com", username="u")
        ab = AutoBackend()
        ab._openssh = _ConnectBackend(exc=_host_key_error())
        ab._paramiko = _ConnectBackend(connection=object())

        with pytest.raises(HostKeyConfirmationRequiredError):
            ab.connect(cfg)
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

    def test_allows_password(self, monkeypatch, tmp_path):
        import runicorn.config as cfg_mod
        import runicorn.remote.ssh_backend as bmod
        monkeypatch.setattr(cfg_mod, "get_known_hosts_file_path", lambda: tmp_path / "known_hosts")
        monkeypatch.setattr(OpenSSHBackend, "_resolve_ssh_path", staticmethod(lambda *_: "ssh"))
        monkeypatch.setattr(bmod.shutil, "which", lambda name: "ssh-keyscan")

        tunnel = OpenSSHBackend().create_tunnel(
            connection=_DummyConnection(password="pw"), local_port=1,
            remote_host="x", remote_port=2, stop_event=threading.Event(),
        )
        assert tunnel is not None


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


class TestOpenSSHCommandConnection:
    def test_exec_command_uses_system_ssh(self, monkeypatch, tmp_path):
        import runicorn.config as cfg_mod

        calls = []
        key_path = tmp_path / "id_ed25519"

        monkeypatch.setattr(cfg_mod, "get_known_hosts_file_path", lambda: tmp_path / "known_hosts")
        monkeypatch.setattr(OpenSSHBackend, "_resolve_ssh_path", staticmethod(lambda *_: "ssh"))
        monkeypatch.setattr(
            "runicorn.remote.ssh_backend.shutil.which",
            lambda name: "ssh-keyscan" if name == "ssh-keyscan" else None,
        )

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            if cmd[-1] == "exit 0":
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            return SimpleNamespace(returncode=7, stdout="hello\n", stderr="warn\n")

        monkeypatch.setattr("runicorn.remote.ssh_backend.subprocess.run", fake_run)

        conn = OpenSSHCommandConnection(
            SSHConfig(
                host="example.com",
                port=2222,
                username="alice",
                private_key_path=str(key_path),
                use_agent=False,
            )
        )

        assert conn.connect() is True
        stdout, stderr, exit_code = conn.exec_command("echo hi", timeout=12)

        assert (stdout, stderr, exit_code) == ("hello\n", "warn\n", 7)
        assert len(calls) == 2

        exec_cmd, exec_kwargs = calls[1]
        assert exec_cmd[:4] == ["ssh", "-T", "-p", "2222"]
        assert "StrictHostKeyChecking=yes" in exec_cmd
        assert f"UserKnownHostsFile={tmp_path / 'known_hosts'}" in exec_cmd
        assert "-i" in exec_cmd
        assert str(key_path) in exec_cmd
        assert "IdentitiesOnly=yes" in exec_cmd
        assert "IdentityAgent=none" in exec_cmd
        assert exec_cmd[-2] == "alice@example.com"
        assert exec_cmd[-1] == "echo hi"
        assert exec_kwargs["timeout"] == 12

    def test_connect_maps_host_key_errors(self, monkeypatch, tmp_path):
        import runicorn.config as cfg_mod

        monkeypatch.setattr(cfg_mod, "get_known_hosts_file_path", lambda: tmp_path / "known_hosts")
        monkeypatch.setattr(OpenSSHBackend, "_resolve_ssh_path", staticmethod(lambda *_: "ssh"))
        monkeypatch.setattr(
            "runicorn.remote.ssh_backend.shutil.which",
            lambda name: "ssh-keyscan" if name == "ssh-keyscan" else None,
        )
        monkeypatch.setattr(
            "runicorn.remote.ssh_backend.subprocess.run",
            lambda *a, **kw: SimpleNamespace(
                returncode=255,
                stdout="",
                stderr="Host key verification failed",
            ),
        )
        monkeypatch.setattr(
            "runicorn.remote.ssh_backend.OpenSSHTunnel._ssh_keyscan",
            staticmethod(lambda **kwargs: "ssh-ed25519 AAAA"),
        )

        conn = OpenSSHCommandConnection(SSHConfig(host="example.com", username="alice"))

        with pytest.raises(HostKeyConfirmationRequiredError) as exc:
            conn.connect()
        assert exc.value.problem.reason == "unknown"

    def test_password_auth_uses_askpass(self, monkeypatch, tmp_path):
        import runicorn.config as cfg_mod

        calls = []
        monkeypatch.setattr(cfg_mod, "get_known_hosts_file_path", lambda: tmp_path / "known_hosts")
        monkeypatch.setattr(OpenSSHBackend, "_resolve_ssh_path", staticmethod(lambda *_: "ssh"))
        monkeypatch.setattr(
            "runicorn.remote.ssh_backend.shutil.which",
            lambda name: "ssh-keyscan" if name == "ssh-keyscan" else None,
        )
        monkeypatch.setattr(_OpenSSHAskpassHelper, "cleanup", lambda self: None)

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr("runicorn.remote.ssh_backend.subprocess.run", fake_run)

        conn = OpenSSHCommandConnection(
            SSHConfig(host="example.com", username="alice", password="pw", use_agent=False)
        )

        assert conn.connect() is True
        cmd, kwargs = calls[0]
        assert "BatchMode=no" in cmd
        assert "PreferredAuthentications=keyboard-interactive,password" in cmd
        assert "PubkeyAuthentication=no" in cmd
        assert kwargs["env"]["SSH_ASKPASS_REQUIRE"] == "force"
        assert kwargs["env"]["RUNICORN_SSH_ASKPASS_SECRET"] == "pw"
        askpass_path = Path(kwargs["env"]["SSH_ASKPASS"])
        content = askpass_path.read_text(encoding="utf-8")
        if os.name == "nt":
            assert askpass_path.name == "askpass.cmd"
            assert "powershell" in content.lower()
        else:
            assert askpass_path.name == "askpass.sh"
            assert "#!/bin/sh" in content
        assert "RUNICORN_SSH_ASKPASS_SECRET" in content


class TestSSHConnectionPool:
    def test_uses_backend_for_connection_creation(self):
        cfg = SSHConfig(host="example.com", username="u")
        backend = _ConnectBackend(connection=_PoolConnection(cfg))
        pool = SSHConnectionPool(backend=backend)

        conn1 = pool.get_or_create(cfg)
        conn2 = pool.get_or_create(cfg)

        assert conn1 is conn2
        assert backend.called == 1
