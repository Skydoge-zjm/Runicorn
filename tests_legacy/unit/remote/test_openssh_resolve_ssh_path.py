from __future__ import annotations

from types import SimpleNamespace

import pytest

from runicorn.remote.ssh_backend import OpenSSHBackend


pytestmark = pytest.mark.unit


def test_resolve_ssh_path_uses_explicit_path(tmp_path, monkeypatch) -> None:
    fake_ssh = tmp_path / "ssh"
    fake_ssh.write_text("x", encoding="utf-8")

    def _run(*args, **kwargs):
        return SimpleNamespace(returncode=0, stderr="OpenSSH_9.0")

    monkeypatch.setattr("runicorn.remote.ssh_backend.subprocess.run", _run)

    resolved = OpenSSHBackend._resolve_ssh_path(str(fake_ssh))
    assert resolved == str(fake_ssh)


def test_resolve_ssh_path_uses_env_var_when_no_explicit(tmp_path, monkeypatch) -> None:
    fake_ssh = tmp_path / "ssh"
    fake_ssh.write_text("x", encoding="utf-8")

    monkeypatch.setenv("RUNICORN_SSH_PATH", str(fake_ssh))

    def _run(*args, **kwargs):
        return SimpleNamespace(returncode=0, stderr="OpenSSH_9.0")

    monkeypatch.setattr("runicorn.remote.ssh_backend.subprocess.run", _run)
    monkeypatch.setattr("runicorn.remote.ssh_backend.shutil.which", lambda name: None)

    resolved = OpenSSHBackend._resolve_ssh_path(None)
    assert resolved == str(fake_ssh)


def test_resolve_ssh_path_falls_back_to_which(monkeypatch) -> None:
    monkeypatch.delenv("RUNICORN_SSH_PATH", raising=False)
    monkeypatch.setattr("runicorn.remote.ssh_backend.shutil.which", lambda name: "ssh")

    def _run(*args, **kwargs):
        return SimpleNamespace(returncode=255, stderr="OpenSSH")

    monkeypatch.setattr("runicorn.remote.ssh_backend.subprocess.run", _run)

    resolved = OpenSSHBackend._resolve_ssh_path(None)
    assert resolved == "ssh"


def test_resolve_ssh_path_returns_none_when_all_fail(monkeypatch) -> None:
    monkeypatch.delenv("RUNICORN_SSH_PATH", raising=False)
    monkeypatch.setattr("runicorn.remote.ssh_backend.shutil.which", lambda name: None)

    def _run(*args, **kwargs):
        return SimpleNamespace(returncode=1, stderr="")

    monkeypatch.setattr("runicorn.remote.ssh_backend.subprocess.run", _run)

    assert OpenSSHBackend._resolve_ssh_path(None) is None
