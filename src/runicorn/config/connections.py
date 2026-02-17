"""SSH connection configuration management.

Contains both the Fernet path (connections.json) and the XOR path
(config.json ssh_connections). RF-04/RF-05 will unify these.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from .paths import get_connections_file_path
from .user_config import load_user_config, save_user_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Path B: Fernet-encrypted connections.json (newer)
# ---------------------------------------------------------------------------

def load_saved_connections() -> List[Dict[str, Any]]:
    """Load saved SSH connections from connections.json and decrypt passwords."""
    path = get_connections_file_path()
    try:
        if path.exists():
            connections = json.loads(path.read_text(encoding="utf-8"))

            # Decrypt passwords
            from ..security.encryption import decrypt_password, is_encrypted
            for conn in connections:
                if conn.get('password') and is_encrypted(conn['password']):
                    try:
                        conn['password'] = decrypt_password(conn['password'])
                    except Exception as e:
                        logger.warning(f"Failed to decrypt password for {conn.get('name', 'unknown')}: {e}")
                        conn['password'] = None  # Clear invalid password

            return connections
    except Exception as e:
        logger.warning(f"Failed to load connections: {e}")
    return []


def save_connections(connections: List[Dict[str, Any]]) -> None:
    """Save SSH connections to connections.json with encrypted passwords."""
    path = get_connections_file_path()
    try:
        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Debug: log incoming connections
        for conn in connections:
            logger.info(f"Processing connection '{conn.get('name')}': has_password={bool(conn.get('password'))}, password_length={len(conn.get('password', ''))}")

        # Encrypt passwords before saving
        from ..security.encryption import encrypt_password, is_encrypted
        connections_to_save = []
        for conn in connections:
            conn_copy = conn.copy()
            password = conn_copy.get('password')
            if password:  # Has password
                if not is_encrypted(password):
                    try:
                        conn_copy['password'] = encrypt_password(password)
                        logger.info(f"✓ Encrypted password for '{conn.get('name', 'unknown')}'")
                    except Exception as e:
                        logger.error(f"Failed to encrypt password for {conn.get('name', 'unknown')}: {e}")
                        conn_copy['password'] = None  # Don't save unencrypted password
                else:
                    logger.info(f"Password for '{conn.get('name', 'unknown')}' is already encrypted")
            else:
                logger.warning(f"No password for '{conn.get('name', 'unknown')}'")
            # Keep password field even if None (for consistency)
            connections_to_save.append(conn_copy)

        # Write with pretty formatting
        path.write_text(json.dumps(connections_to_save, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Saved {len(connections_to_save)} connections to {path}")
    except Exception as e:
        logger.error(f"Failed to save connections: {e}")
        raise


# ---------------------------------------------------------------------------
# Path A: XOR-encrypted ssh_connections in config.json (older)
# ---------------------------------------------------------------------------

def save_ssh_connections(connections: list[Dict[str, Any]]) -> None:
    """Save SSH connection configurations with encryption."""
    from ..security.credentials import get_credential_manager

    manager = get_credential_manager()
    encrypted_connections = [
        manager.encrypt_config(conn) for conn in connections
    ]
    save_user_config({"ssh_connections": encrypted_connections})


def get_ssh_connections() -> list[Dict[str, Any]]:
    """Get saved SSH connection configurations with decryption."""
    from ..security.credentials import get_credential_manager

    cfg = load_user_config()
    connections = cfg.get("ssh_connections", [])

    # Decrypt sensitive fields
    manager = get_credential_manager()
    return [
        manager.decrypt_config(conn) for conn in connections
    ]


def add_ssh_connection(connection: Dict[str, Any]) -> None:
    """Add or update an SSH connection configuration."""
    connections = get_ssh_connections()

    # Find and update if exists (by host+port+username)
    key = f"{connection.get('host')}:{connection.get('port', 22)}@{connection.get('username')}"
    connection['key'] = key

    # Remove existing connection with same key
    connections = [c for c in connections if c.get('key') != key]

    # Add new/updated connection
    connections.append(connection)

    # Keep only last 10 connections
    connections = connections[-10:]

    save_ssh_connections(connections)


def remove_ssh_connection(key: str) -> None:
    """Remove an SSH connection configuration."""
    connections = get_ssh_connections()
    connections = [c for c in connections if c.get('key') != key]
    save_ssh_connections(connections)
