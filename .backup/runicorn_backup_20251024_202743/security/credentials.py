"""
Credential Security Module

Provides encryption and decryption for sensitive credentials.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Note: This is a basic implementation. For production, consider using:
# - System keyring (python-keyring)
# - Hardware security modules
# - Cloud key management services


class CredentialManager:
    """
    Manages encryption and decryption of sensitive credentials.
    
    Uses a simple obfuscation method by default. This is NOT cryptographically secure
    but prevents casual viewing of passwords in config files.
    """
    
    def __init__(self, key_file: Optional[Path] = None):
        """
        Initialize credential manager.
        
        Args:
            key_file: Path to key file (will be created if not exists)
        """
        if key_file is None:
            from ..config import _config_root_dir
            key_file = _config_root_dir() / ".credential_key"
        
        self.key_file = Path(key_file)
        self._ensure_key()
    
    def _ensure_key(self):
        """Ensure encryption key exists."""
        if not self.key_file.exists():
            # Generate a random key
            key = os.urandom(32)
            
            # Create directory with secure permissions
            self.key_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write key with restricted permissions
            self.key_file.write_bytes(key)
            
            # Set secure permissions (owner read/write only)
            if os.name != 'nt':  # Unix-like systems
                os.chmod(self.key_file, 0o600)
            
            logger.info("Generated new credential encryption key")
    
    def _get_key(self) -> bytes:
        """Get the encryption key."""
        return self.key_file.read_bytes()
    
    def encrypt_credential(self, credential: str) -> str:
        """
        Encrypt a credential.
        
        Args:
            credential: Plain text credential
            
        Returns:
            Encrypted credential as base64 string
        """
        if not credential:
            return ""
        
        try:
            key = self._get_key()
            
            # Simple XOR encryption (not cryptographically secure)
            # For production, use proper encryption like Fernet
            credential_bytes = credential.encode('utf-8')
            
            # Extend or truncate key to match credential length
            key_extended = key * (len(credential_bytes) // len(key) + 1)
            key_extended = key_extended[:len(credential_bytes)]
            
            # XOR encryption
            encrypted = bytes(a ^ b for a, b in zip(credential_bytes, key_extended))
            
            # Add a marker to identify encrypted values
            result = b"ENC:" + base64.b64encode(encrypted)
            return result.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to encrypt credential: {e}")
            # Return original if encryption fails (fail-open)
            return credential
    
    def decrypt_credential(self, encrypted: str) -> str:
        """
        Decrypt a credential.
        
        Args:
            encrypted: Encrypted credential
            
        Returns:
            Decrypted plain text credential
        """
        if not encrypted:
            return ""
        
        # Check if it's actually encrypted
        if not encrypted.startswith("ENC:"):
            # Not encrypted, return as-is
            return encrypted
        
        try:
            key = self._get_key()
            
            # Remove marker and decode
            encrypted_bytes = base64.b64decode(encrypted[4:])
            
            # Extend or truncate key to match encrypted length
            key_extended = key * (len(encrypted_bytes) // len(key) + 1)
            key_extended = key_extended[:len(encrypted_bytes)]
            
            # XOR decryption
            decrypted = bytes(a ^ b for a, b in zip(encrypted_bytes, key_extended))
            
            return decrypted.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to decrypt credential: {e}")
            # Return empty string if decryption fails (fail-closed)
            return ""
    
    def encrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in a configuration dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configuration with encrypted sensitive fields
        """
        encrypted_config = config.copy()
        
        # Fields to encrypt
        sensitive_fields = [
            'password', 'passphrase', 'private_key',
            'secret', 'token', 'api_key'
        ]
        
        for field in sensitive_fields:
            if field in encrypted_config and encrypted_config[field]:
                encrypted_config[field] = self.encrypt_credential(
                    encrypted_config[field]
                )
        
        return encrypted_config
    
    def decrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt sensitive fields in a configuration dictionary.
        
        Args:
            config: Configuration with encrypted fields
            
        Returns:
            Configuration with decrypted fields
        """
        decrypted_config = config.copy()
        
        # Fields to decrypt
        sensitive_fields = [
            'password', 'passphrase', 'private_key',
            'secret', 'token', 'api_key'
        ]
        
        for field in sensitive_fields:
            if field in decrypted_config and decrypted_config[field]:
                value = decrypted_config[field]
                if isinstance(value, str) and value.startswith("ENC:"):
                    decrypted_config[field] = self.decrypt_credential(value)
        
        return decrypted_config


# Global instance
_credential_manager: Optional[CredentialManager] = None


def get_credential_manager() -> CredentialManager:
    """
    Get the global credential manager instance.
    
    Returns:
        CredentialManager instance
    """
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager


def encrypt_password(password: str) -> str:
    """
    Convenience function to encrypt a password.
    
    Args:
        password: Plain text password
        
    Returns:
        Encrypted password
    """
    return get_credential_manager().encrypt_credential(password)


def decrypt_password(encrypted: str) -> str:
    """
    Convenience function to decrypt a password.
    
    Args:
        encrypted: Encrypted password
        
    Returns:
        Decrypted password
    """
    return get_credential_manager().decrypt_credential(encrypted)
