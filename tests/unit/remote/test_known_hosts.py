from __future__ import annotations

import base64
import hashlib

import pytest

from runicorn.remote.known_hosts import (
    KnownHostsStore,
    compute_fingerprint_sha256,
    format_known_hosts_host,
    parse_known_hosts_host,
    parse_openssh_public_key,
)


pytestmark = pytest.mark.unit


def test_format_and_parse_known_hosts_host() -> None:
    assert format_known_hosts_host("example.com", 22) == "example.com"
    assert format_known_hosts_host("example.com", 2222) == "[example.com]:2222"

    assert parse_known_hosts_host("example.com") == ("example.com", 22)
    assert parse_known_hosts_host("[example.com]:2222") == ("example.com", 2222)


def test_parse_openssh_public_key_valid_and_invalid() -> None:
    key_bytes = b"abc"
    key_base64 = base64.b64encode(key_bytes).decode("ascii")

    parsed = parse_openssh_public_key(f"ssh-ed25519 {key_base64} comment")
    assert parsed.key_type == "ssh-ed25519"
    assert parsed.key_base64 == key_base64
    assert parsed.key_bytes == key_bytes

    with pytest.raises(ValueError):
        parse_openssh_public_key("ssh-ed25519")

    with pytest.raises(ValueError):
        parse_openssh_public_key("ssh-ed25519 !!!not-base64!!!")


def test_compute_fingerprint_sha256_matches_reference() -> None:
    key_bytes = b"abc"
    expected_digest = hashlib.sha256(key_bytes).digest()
    expected_fp = base64.b64encode(expected_digest).decode("ascii").rstrip("=")

    assert compute_fingerprint_sha256(key_bytes) == f"SHA256:{expected_fp}"


def test_known_hosts_store_upsert_list_remove(tmp_path) -> None:
    known_hosts_path = tmp_path / "known_hosts"
    store = KnownHostsStore(known_hosts_path)

    key_bytes = b"abc"
    key_base64 = base64.b64encode(key_bytes).decode("ascii")

    assert store.upsert_host_key(host="example.com", port=22, key_type="ssh-ed25519", key_base64=key_base64)
    assert not store.upsert_host_key(host="example.com", port=22, key_type="ssh-ed25519", key_base64=key_base64)

    entries = store.list_host_keys()
    assert len(entries) == 1
    assert entries[0]["host"] == "example.com"
    assert entries[0]["port"] == 22
    assert entries[0]["known_hosts_host"] == "example.com"
    assert entries[0]["key_type"] == "ssh-ed25519"
    assert entries[0]["key_base64"] == key_base64
    assert entries[0]["fingerprint_sha256"] == compute_fingerprint_sha256(key_bytes)

    key_bytes_2 = b"def"
    key_base64_2 = base64.b64encode(key_bytes_2).decode("ascii")
    assert store.upsert_host_key(host="example.com", port=22, key_type="ssh-ed25519", key_base64=key_base64_2)

    entries = store.list_host_keys()
    assert len(entries) == 1
    assert entries[0]["key_base64"] == key_base64_2

    assert store.remove_host_key(host="example.com", port=22, key_type="ssh-ed25519")
    assert not store.remove_host_key(host="example.com", port=22, key_type="ssh-ed25519")

    assert store.list_host_keys() == []
