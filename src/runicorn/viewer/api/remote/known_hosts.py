from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from .shared import (
    KnownHostsAcceptRequest,
    KnownHostsEntry,
    KnownHostsRemoveRequest,
    logger,
)

router = APIRouter()


@router.post("/remote/known-hosts/accept")
async def accept_known_host(payload: KnownHostsAcceptRequest) -> Dict[str, Any]:
    try:
        from ....remote.known_hosts import (
            KnownHostsStore,
            compute_fingerprint_sha256,
            parse_openssh_public_key,
        )
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Remote module not available: {e}")

    if not payload.host:
        raise HTTPException(status_code=400, detail="Invalid host")
    if not payload.key_type:
        raise HTTPException(status_code=400, detail="Invalid key_type")
    if not payload.fingerprint_sha256:
        raise HTTPException(status_code=400, detail="Invalid fingerprint_sha256")
    if "\n" in payload.public_key or "\r" in payload.public_key:
        raise HTTPException(status_code=400, detail="Invalid public_key")
    if "\n" in payload.host or "\r" in payload.host or any(ch.isspace() for ch in payload.host):
        raise HTTPException(status_code=400, detail="Invalid host")
    if "," in payload.host:
        raise HTTPException(status_code=400, detail="Invalid host")
    if "\n" in payload.key_type or "\r" in payload.key_type or any(ch.isspace() for ch in payload.key_type):
        raise HTTPException(status_code=400, detail="Invalid key_type")
    if (
        "\n" in payload.fingerprint_sha256
        or "\r" in payload.fingerprint_sha256
        or any(ch.isspace() for ch in payload.fingerprint_sha256)
    ):
        raise HTTPException(status_code=400, detail="Invalid fingerprint_sha256")

    try:
        parsed_key = parse_openssh_public_key(payload.public_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid public_key: {str(e)}")

    if parsed_key.key_type != payload.key_type:
        raise HTTPException(status_code=400, detail="key_type does not match public_key")

    computed_fingerprint = compute_fingerprint_sha256(parsed_key.key_bytes)
    if computed_fingerprint != payload.fingerprint_sha256:
        raise HTTPException(status_code=400, detail="fingerprint_sha256 does not match public_key")

    store = KnownHostsStore.from_runicorn_config()
    try:
        store.upsert_host_key(
            host=payload.host,
            port=payload.port,
            key_type=payload.key_type,
            key_base64=parsed_key.key_base64,
        )
    except Exception as e:
        logger.error("Failed to write known_hosts: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to write known_hosts: {str(e)}")

    return {"ok": True}


@router.get("/remote/known-hosts/list")
async def list_known_hosts() -> Dict[str, List[KnownHostsEntry]]:
    try:
        from ....remote.known_hosts import KnownHostsStore
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Remote module not available: {e}")

    store = KnownHostsStore.from_runicorn_config()
    try:
        entries = store.list_host_keys()
    except Exception as e:
        logger.error("Failed to list known_hosts: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list known_hosts: {str(e)}")

    return {"entries": [KnownHostsEntry(**entry) for entry in entries]}


@router.post("/remote/known-hosts/remove")
async def remove_known_host(payload: KnownHostsRemoveRequest) -> Dict[str, Any]:
    try:
        from ....remote.known_hosts import KnownHostsStore
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Remote module not available: {e}")

    if not payload.host:
        raise HTTPException(status_code=400, detail="Invalid host")
    if not payload.key_type:
        raise HTTPException(status_code=400, detail="Invalid key_type")

    store = KnownHostsStore.from_runicorn_config()
    try:
        changed = store.remove_host_key(host=payload.host, port=payload.port, key_type=payload.key_type)
    except Exception as e:
        logger.error("Failed to remove known_hosts entry: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to remove known_hosts entry: {str(e)}")

    return {"ok": True, "changed": changed}
