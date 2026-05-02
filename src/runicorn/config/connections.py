"""SSH connection configuration management.

All actively written connections live in ``connections.json`` and use Fernet
for sensitive fields. The old ``config.json:ssh_connections`` + ``ENC:``
format is retained only as a migration source and should be removable after a
full release window with no observed legacy migrations.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from .paths import get_connections_file_path
from .user_config import load_user_config, save_user_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core load / save  (connections.json, Fernet)
# ---------------------------------------------------------------------------

def load_saved_connections() -> List[Dict[str, Any]]:
    """Load saved SSH connections from connections.json and decrypt all sensitive fields."""
    # Legacy migration is only relevant when the old config.json payload still
    # exists. Keep the normal read path centered on connections.json.
    if _legacy_config_has_ssh_connections():
        _migrate_legacy_xor_connections()

    path = get_connections_file_path()
    try:
        if path.exists():
            connections = json.loads(path.read_text(encoding="utf-8"))

            from ..security.encryption import decrypt_password, is_encrypted, SENSITIVE_FIELDS
            for conn in connections:
                for field in SENSITIVE_FIELDS:
                    value = conn.get(field)
                    if value and (is_encrypted(value) or value.startswith('ENC:')):
                        try:
                            conn[field] = decrypt_password(value)
                        except Exception as e:
                            logger.warning(f"Failed to decrypt {field} for {conn.get('name', 'unknown')}: {e}")
                            conn[field] = None

            return connections
    except Exception as e:
        logger.warning(f"Failed to load connections: {e}")
    return []


def save_connections(connections: List[Dict[str, Any]]) -> None:
    """Save SSH connections to connections.json, encrypting all sensitive fields."""
    path = get_connections_file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        from ..security.encryption import encrypt_password, is_encrypted, SENSITIVE_FIELDS
        connections_to_save = []
        for conn in connections:
            conn_copy = conn.copy()
            for field in SENSITIVE_FIELDS:
                value = conn_copy.get(field)
                if value and not is_encrypted(value):
                    try:
                        conn_copy[field] = encrypt_password(value)
                    except Exception as e:
                        logger.error(f"Failed to encrypt {field} for {conn.get('name', 'unknown')}: {e}")
                        conn_copy[field] = None  # Don't save unencrypted
            connections_to_save.append(conn_copy)

        path.write_text(json.dumps(connections_to_save, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Saved {len(connections_to_save)} connections to {path}")
    except Exception as e:
        logger.error(f"Failed to save connections: {e}")
        raise


# ---------------------------------------------------------------------------
# CRUD helpers  (used by viewer/api/config.py)
# ---------------------------------------------------------------------------

def get_ssh_connections() -> List[Dict[str, Any]]:
    """Get saved SSH connection configurations (unified, Fernet)."""
    return load_saved_connections()


def save_ssh_connections(connections: List[Dict[str, Any]]) -> None:
    """Save SSH connection configurations (unified, Fernet)."""
    save_connections(connections)


def add_ssh_connection(connection: Dict[str, Any]) -> None:
    """Add or update an SSH connection configuration."""
    connections = load_saved_connections()

    # Find and update if exists (by host+port+username)
    key = f"{connection.get('host')}:{connection.get('port', 22)}@{connection.get('username')}"
    connection['key'] = key

    # Remove existing connection with same key
    connections = [c for c in connections if c.get('key') != key]

    # Add new/updated connection
    connections.append(connection)

    save_connections(connections)


def remove_ssh_connection(key: str) -> None:
    """Remove an SSH connection configuration."""
    connections = load_saved_connections()
    connections = [c for c in connections if c.get('key') != key]
    save_connections(connections)


# ---------------------------------------------------------------------------
# Legacy XOR migration  (config.json → connections.json)
# ---------------------------------------------------------------------------

def _legacy_config_has_ssh_connections() -> bool:
    """Return True only when the legacy ``config.json`` payload still exists."""
    from .paths import get_config_file_path

    path = get_config_file_path()
    if not path.exists():
        return False

    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        logger.debug("Skipping legacy SSH migration check; failed to read %s: %s", path, e)
        return False

    return '"ssh_connections"' in text


def _load_legacy_xor_connections(path: Path) -> List[Dict[str, Any]]:
    """Load legacy SSH connections from config.json if the old key is present."""
    try:
        cfg = load_user_config()
    except Exception as e:
        logger.warning("Failed to load legacy SSH config from %s: %s", path, e)
        return []

    legacy = cfg.get("ssh_connections")
    if not legacy:
        return []
    if not isinstance(legacy, list):
        logger.warning("Ignoring malformed legacy ssh_connections in %s", path)
        return []
    return legacy


def _migrate_legacy_xor_connections() -> None:
    """Migrate legacy ``config.json:ssh_connections`` into Fernet storage.

    Trigger condition:
    - ``config.json`` still contains the historical ``ssh_connections`` key

    Input source:
    - legacy XOR or plaintext values stored in ``config.json``

    Removal condition:
    - after one release window with no observed legacy migrations, this helper
      and the XOR compatibility path should be removed together
    """
    from .paths import get_config_file_path

    config_path = get_config_file_path()
    legacy = _load_legacy_xor_connections(config_path)
    if not legacy:
        return

    logger.info(
        "Legacy SSH migration triggered from %s with %d entries",
        config_path,
        len(legacy),
    )

    from ..security.encryption import SENSITIVE_FIELDS

    # The only allowed use of the XOR helper is reading legacy config payloads
    # so they can be re-saved via the Fernet-backed connections.json path.
    from ..security.encryption import _try_decrypt_xor_legacy
    migrated: List[Dict[str, Any]] = []
    for conn in legacy:
        decrypted = conn.copy()
        for field in SENSITIVE_FIELDS:
            value = decrypted.get(field)
            if value and isinstance(value, str) and value.startswith("ENC:"):
                plain = _try_decrypt_xor_legacy(value)
                decrypted[field] = plain if plain is not None else None
        migrated.append(decrypted)

    # Merge with any existing connections.json data (avoid duplicates by key)
    path = get_connections_file_path()
    existing: List[Dict[str, Any]] = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass

    existing_keys = {c.get('key') for c in existing if c.get('key')}
    migrated_new_entries = 0
    for entry in migrated:
        if entry.get('key') not in existing_keys:
            existing.append(entry)
            migrated_new_entries += 1

    # Save merged list (will encrypt with Fernet)
    save_connections(existing)
    logger.info(
        "Legacy SSH migration wrote %d new entries into %s",
        migrated_new_entries,
        path,
    )

    # Remove legacy key from config.json
    # Pass {"ssh_connections": None} so save_user_config pops the key
    # from the on-disk config (passing the whole cfg without the key
    # would silently leave it behind).
    save_user_config({"ssh_connections": None})
    logger.info("Legacy SSH migration removed config.json:ssh_connections")
