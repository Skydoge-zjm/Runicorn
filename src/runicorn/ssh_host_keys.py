"""
SSH Host Key Management

Provides secure host key verification for SSH connections.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any
import paramiko
from paramiko.ssh_exception import SSHException

logger = logging.getLogger(__name__)


class KnownHostsPolicy(paramiko.MissingHostKeyPolicy):
    """
    Policy for handling SSH host keys with user confirmation.
    """
    
    def __init__(self, known_hosts_file: Path, auto_add: bool = False):
        """
        Initialize the policy.
        
        Args:
            known_hosts_file: Path to known hosts file
            auto_add: If True, automatically add new hosts (not recommended for production)
        """
        self.known_hosts_file = known_hosts_file
        self.auto_add = auto_add
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Ensure the known hosts file exists."""
        self.known_hosts_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.known_hosts_file.exists():
            self.known_hosts_file.touch(mode=0o600)  # Secure permissions
    
    def missing_host_key(self, client, hostname, key):
        """
        Called when host key is not found in known hosts.
        
        Args:
            client: SSHClient instance
            hostname: Hostname being connected to
            key: The host key
        """
        key_type = key.get_name()
        key_fingerprint = self._get_fingerprint(key)
        
        logger.warning(
            f"Unknown host: {hostname}\n"
            f"Key type: {key_type}\n"
            f"Fingerprint: {key_fingerprint}"
        )
        
        if self.auto_add:
            # Auto-add mode (use with caution)
            logger.info(f"Auto-adding host key for {hostname}")
            self._add_host_key(hostname, key)
            client.get_host_keys().add(hostname, key.get_name(), key)
        else:
            # Reject unknown hosts
            raise SSHException(
                f"Server '{hostname}' not found in known hosts.\n"
                f"Key fingerprint: {key_fingerprint}\n"
                f"To trust this host, add it to known hosts file or enable auto-add mode."
            )
    
    def _get_fingerprint(self, key) -> str:
        """Get human-readable fingerprint of a key."""
        import binascii
        return ":".join(
            f"{b:02x}" for b in binascii.unhexlify(key.get_fingerprint().hex())
        )
    
    def _add_host_key(self, hostname: str, key):
        """Add a host key to the known hosts file."""
        try:
            host_keys = paramiko.HostKeys(str(self.known_hosts_file))
            host_keys.add(hostname, key.get_name(), key)
            host_keys.save(str(self.known_hosts_file))
            logger.info(f"Added host key for {hostname}")
        except Exception as e:
            logger.error(f"Failed to save host key: {e}")
            raise


class TrustOnFirstUsePolicy(KnownHostsPolicy):
    """
    Trust On First Use (TOFU) policy.
    
    Automatically trusts hosts on first connection, but verifies on subsequent connections.
    """
    
    def missing_host_key(self, client, hostname, key):
        """
        Trust the host on first connection.
        """
        key_fingerprint = self._get_fingerprint(key)
        
        logger.info(
            f"First connection to {hostname}\n"
            f"Trusting key fingerprint: {key_fingerprint}"
        )
        
        # Add the key
        self._add_host_key(hostname, key)
        client.get_host_keys().add(hostname, key.get_name(), key)


def get_known_hosts_file() -> Path:
    """
    Get the path to the known hosts file.
    
    Returns:
        Path to known hosts file in user config directory
    """
    from .config import _config_root_dir
    return _config_root_dir() / "known_hosts"


def load_host_keys(client: paramiko.SSHClient) -> None:
    """
    Load known host keys into SSH client.
    
    Args:
        client: SSHClient instance to configure
    """
    known_hosts_file = get_known_hosts_file()
    
    if known_hosts_file.exists():
        try:
            client.load_host_keys(str(known_hosts_file))
            logger.debug(f"Loaded host keys from {known_hosts_file}")
        except Exception as e:
            logger.warning(f"Failed to load host keys: {e}")
    
    # Also try to load system host keys
    try:
        client.load_system_host_keys()
    except Exception:
        pass  # System host keys might not be available


def get_host_key_policy(auto_trust: bool = False) -> paramiko.MissingHostKeyPolicy:
    """
    Get the appropriate host key policy.
    
    Args:
        auto_trust: If True, use TOFU policy; otherwise use strict checking
        
    Returns:
        Host key policy instance
    """
    known_hosts_file = get_known_hosts_file()
    
    if auto_trust:
        return TrustOnFirstUsePolicy(known_hosts_file)
    else:
        return KnownHostsPolicy(known_hosts_file, auto_add=False)


def add_trusted_host(hostname: str, port: int = 22) -> bool:
    """
    Manually add a host to trusted hosts by connecting and saving its key.
    
    Args:
        hostname: Host to trust
        port: SSH port
        
    Returns:
        True if successfully added
    """
    try:
        # Create temporary client to fetch the key
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Try to connect just to get the host key
        # This will fail authentication but we'll get the host key
        try:
            client.connect(
                hostname, 
                port=port, 
                username="dummy",
                password="dummy",
                timeout=5,
                auth_timeout=1
            )
        except paramiko.AuthenticationException:
            # Expected - we just want the host key
            pass
        
        # Get the host key
        host_keys = client.get_host_keys()
        if hostname in host_keys:
            # Save to our known hosts file
            known_hosts_file = get_known_hosts_file()
            our_hosts = paramiko.HostKeys(str(known_hosts_file))
            
            for key_type, key in host_keys[hostname].items():
                our_hosts.add(hostname, key_type, key)
            
            our_hosts.save(str(known_hosts_file))
            logger.info(f"Added trusted host: {hostname}:{port}")
            return True
        
    except Exception as e:
        logger.error(f"Failed to add trusted host {hostname}: {e}")
    
    return False
