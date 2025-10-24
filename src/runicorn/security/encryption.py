"""
Password encryption utilities for secure storage.

Uses Fernet symmetric encryption with a user-specific key.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import to avoid dependency issues if cryptography not installed
_fernet_instance: Optional[object] = None


def _get_key_path() -> Path:
    """Get path to encryption key file."""
    from ..config import _config_root_dir
    return _config_root_dir() / ".secret.key"


def _ensure_key() -> bytes:
    """
    Ensure encryption key exists, creating it if necessary.
    
    Returns:
        Encryption key as bytes
    """
    key_path = _get_key_path()
    
    try:
        # Try to load existing key
        if key_path.exists():
            return key_path.read_bytes()
        
        # Generate new key
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        
        # Save key with restricted permissions
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(key)
        
        # Set restrictive permissions (owner read/write only)
        if os.name != 'nt':  # Unix-like systems
            os.chmod(key_path, 0o600)
        
        logger.info(f"Generated new encryption key at {key_path}")
        return key
        
    except Exception as e:
        logger.error(f"Failed to manage encryption key: {e}")
        raise


def _get_cipher():
    """Get or create Fernet cipher instance."""
    global _fernet_instance
    
    if _fernet_instance is None:
        try:
            from cryptography.fernet import Fernet
            key = _ensure_key()
            _fernet_instance = Fernet(key)
        except ImportError:
            logger.error("cryptography library not installed. Cannot encrypt passwords.")
            raise RuntimeError("cryptography library required for password encryption")
    
    return _fernet_instance


def encrypt_password(password: str) -> str:
    """
    Encrypt a password for secure storage.
    
    Args:
        password: Plain text password
        
    Returns:
        Encrypted password as base64 string
    """
    if not password:
        return ""
    
    try:
        cipher = _get_cipher()
        encrypted = cipher.encrypt(password.encode('utf-8'))
        return encrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to encrypt password: {e}")
        raise


def decrypt_password(encrypted_password: str) -> str:
    """
    Decrypt a stored password.
    
    Args:
        encrypted_password: Encrypted password as base64 string
        
    Returns:
        Plain text password
    """
    if not encrypted_password:
        return ""
    
    try:
        cipher = _get_cipher()
        decrypted = cipher.decrypt(encrypted_password.encode('utf-8'))
        return decrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to decrypt password: {e}")
        raise


def is_encrypted(value: str) -> bool:
    """
    Check if a value appears to be encrypted.
    
    Args:
        value: String to check
        
    Returns:
        True if value looks like encrypted data
    """
    if not value:
        return False
    
    # Fernet tokens start with 'gAAAAA' (base64 of version byte + timestamp)
    # This is a heuristic check
    try:
        return value.startswith('gAAAAA') and len(value) > 50
    except:
        return False
