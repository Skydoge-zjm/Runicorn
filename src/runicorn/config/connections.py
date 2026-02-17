"""SSH connection configuration management.

All connections are stored in a single ``connections.json`` file using
Fernet symmetric encryption for sensitive fields.  Legacy XOR-encrypted
data in ``config.json`` is migrated automatically on first read.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from .paths import get_connections_file_path
from .user_config import load_user_config, save_user_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core load / save  (connections.json, Fernet)
# ---------------------------------------------------------------------------

def load_saved_connections() -> List[Dict[str, Any]]:
    """Load saved SSH connections from connections.json and decrypt all sensitive fields."""
    # Migrate legacy data from config.json on every read (idempotent/fast).
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

def _migrate_legacy_xor_connections() -> None:
    """One-time migration: read XOR-encrypted SSH connections from config.json,
    merge them into connections.json (Fernet), then remove the old key.
    """
    cfg = load_user_config()
    legacy = cfg.get("ssh_connections")
    if not legacy:
        return  # Nothing to migrate

    logger.info(f"Migrating {len(legacy)} legacy XOR SSH connections to Fernet...")

    from ..security.encryption import SENSITIVE_FIELDS

    # Decrypt legacy entries using the XOR helper in encryption.py
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
    for entry in migrated:
        if entry.get('key') not in existing_keys:
            existing.append(entry)

    # Save merged list (will encrypt with Fernet)
    save_connections(existing)

    # Remove legacy key from config.json
    cfg.pop("ssh_connections", None)
    save_user_config(cfg)
    logger.info("Legacy XOR SSH connections migrated successfully.")
