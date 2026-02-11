from __future__ import annotations

import pytest

from runicorn.remote.known_hosts import (
    KnownHostsLockTimeout,
    KnownHostsStore,
    KnownHostsWriteError,
)


pytestmark = pytest.mark.unit


def test_known_hosts_store_lock_timeout(tmp_path, monkeypatch) -> None:
    import runicorn.remote.known_hosts as mod

    class _Lock:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            raise mod.Timeout("timeout")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(mod, "FileLock", _Lock)

    store = KnownHostsStore(tmp_path / "known_hosts", lock_timeout_seconds=0.01)
    with pytest.raises(KnownHostsLockTimeout):
        store.list_host_keys()


def test_known_hosts_store_write_error(tmp_path, monkeypatch) -> None:
    import runicorn.remote.known_hosts as mod

    def _fail_replace(*args, **kwargs):
        raise OSError("replace failed")

    monkeypatch.setattr(mod.os, "replace", _fail_replace)

    store = KnownHostsStore(tmp_path / "known_hosts")
    with pytest.raises(KnownHostsWriteError):
        store.upsert_host_key(host="example.com", port=22, key_type="ssh-ed25519", key_base64="AAAA")
