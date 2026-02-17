"""
Security Module

Provides security features for Runicorn.
"""
from .encryption import (
    encrypt_password,
    decrypt_password,
    is_encrypted,
    SENSITIVE_FIELDS,
)

# Legacy / migration support — credentials.py is deprecated and will be
# removed in a future version.  Do not import from it in new code.
from .credentials import (
    CredentialManager,
    get_credential_manager,
)

__all__ = [
    'encrypt_password',
    'decrypt_password',
    'is_encrypted',
    'SENSITIVE_FIELDS',
    # deprecated, kept for backward compatibility
    'CredentialManager',
    'get_credential_manager',
]
