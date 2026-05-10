from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException


def _get_first(entry: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in entry:
            return entry[key]
    return None


def normalize_saved_connection_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(entry)

    if "private_key_path" in normalized and "privateKeyPath" not in normalized:
        normalized["privateKeyPath"] = normalized.pop("private_key_path")
    if "created_at" in normalized and "createdAt" not in normalized:
        normalized["createdAt"] = normalized.pop("created_at")
    if "auth_method" in normalized and "authMethod" not in normalized:
        normalized["authMethod"] = normalized.pop("auth_method")

    return normalized


def mask_saved_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    masked = normalize_saved_connection_entry(entry)
    password = masked.pop("password", None)
    private_key = masked.pop("private_key", None)
    passphrase = masked.pop("passphrase", None)
    if masked.get("kind") == "server":
        masked["hasSavedPassword"] = bool(password)
        masked["hasSavedPrivateKey"] = bool(masked.get("privateKeyPath") or private_key)
        masked["hasSavedPassphrase"] = bool(passphrase)
    return masked


def get_saved_server(server_id: str) -> Dict[str, Any]:
    from ....config import load_saved_connections

    connections = load_saved_connections()
    for entry in connections:
        normalized = normalize_saved_connection_entry(entry)
        if normalized.get("kind") == "server" and normalized.get("id") == server_id:
            return normalized

    raise HTTPException(status_code=404, detail=f"Saved server not found: {server_id}")


def resolve_saved_server_payload(
    *,
    saved_server_id: Optional[str],
    host: Optional[str],
    port: int,
    username: Optional[str],
    password: Optional[str],
    private_key: Optional[str],
    private_key_path: Optional[str],
    passphrase: Optional[str],
    use_agent: bool,
) -> Dict[str, Any]:
    resolved = {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "private_key": private_key,
        "private_key_path": private_key_path,
        "passphrase": passphrase,
        "use_agent": use_agent,
    }

    if not saved_server_id:
        return resolved

    saved = get_saved_server(saved_server_id)

    for field in ("host", "username"):
        incoming = resolved.get(field)
        saved_value = saved.get(field)
        if incoming and saved_value and incoming != saved_value:
            raise HTTPException(
                status_code=400,
                detail=f"Saved server mismatch for field: {field}",
            )
        resolved[field] = saved_value

    incoming_port = resolved.get("port")
    saved_port = int(saved.get("port", incoming_port or 22))
    if incoming_port and incoming_port != saved_port:
        raise HTTPException(
            status_code=400,
            detail="Saved server mismatch for field: port",
        )
    resolved["port"] = saved_port

    credential_fields = {
        "password": ("password",),
        "private_key": ("private_key",),
        "private_key_path": ("private_key_path", "privateKeyPath"),
        "passphrase": ("passphrase",),
    }
    for resolved_field, saved_keys in credential_fields.items():
        if resolved.get(resolved_field) is None:
            saved_value = _get_first(saved, *saved_keys)
            if saved_value is not None:
                resolved[resolved_field] = saved_value

    return resolved


def merge_saved_connection_secrets(connections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from ....config import load_saved_connections

    existing_servers = {}
    for entry in load_saved_connections():
        normalized = normalize_saved_connection_entry(entry)
        if normalized.get("kind") == "server" and normalized.get("id"):
            existing_servers[normalized["id"]] = normalized

    merged: List[Dict[str, Any]] = []
    for raw_entry in connections:
        entry = normalize_saved_connection_entry(raw_entry)
        if entry.get("kind") != "server":
            merged.append(entry)
            continue

        existing = existing_servers.get(entry.get("id"))
        if existing is None:
            merged.append(entry)
            continue

        merged_entry = dict(entry)
        for field in ("password", "private_key", "passphrase"):
            if field not in merged_entry and existing.get(field) is not None:
                merged_entry[field] = existing.get(field)
        if "privateKeyPath" not in merged_entry:
            existing_key_path = _get_first(existing, "privateKeyPath", "private_key_path")
            if existing_key_path is not None:
                merged_entry["privateKeyPath"] = existing_key_path
        merged.append(merged_entry)
    return merged
