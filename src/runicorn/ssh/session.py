"""
SSH Session Management

Provides simplified SSH session for basic operations.
Legacy compatibility layer for existing code.
"""
from __future__ import annotations

import logging
import time
from io import StringIO
from pathlib import Path
from typing import Optional

import paramiko

from .host_keys import load_host_keys, get_host_key_policy

logger = logging.getLogger(__name__)

# Global session pool for API usage
_global_session_pool: dict[str, 'SSHSession'] = {}


class SSHSession:
    """
    Simple SSH session wrapper.
    
    This is a lightweight wrapper around Paramiko for basic SSH operations.
    For advanced features, use UnifiedSSHConnection instead.
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        pkey_str: Optional[str] = None,
        pkey_path: Optional[str] = None,
        passphrase: Optional[str] = None,
        use_agent: bool = True,
        timeout: float = 15.0,
        keepalive_seconds: int = 15,
        enable_compression: bool = True
    ):
        """
        Initialize SSH session.
        
        Args:
            host: SSH server hostname
            port: SSH server port
            username: Username for authentication
            password: Password (optional)
            pkey_str: Private key as string (optional)
            pkey_path: Path to private key file (optional)
            passphrase: Passphrase for encrypted key (optional)
            use_agent: Use SSH agent
            timeout: Connection timeout
            keepalive_seconds: Keepalive interval (L3 hardening)
            enable_compression: Enable compression (L3 hardening)
        """
        self.host = host
        self.port = int(port or 22)
        self.username = username
        self.password = password
        self.pkey_str = pkey_str
        self.pkey_path = pkey_path
        self.passphrase = passphrase
        self.use_agent = use_agent
        self.timeout = timeout
        self.keepalive_seconds = keepalive_seconds
        self.enable_compression = enable_compression
        
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None
        self.id = f"{self.username}@{self.host}:{self.port}:{int(time.time()*1000)}"
        
        # Auto-connect on initialization
        self.connect()
    
    def connect(self) -> None:
        """Establish SSH connection with hardening improvements."""
        if self.client:
            return
        
        client = paramiko.SSHClient()
        
        # Load known hosts
        load_host_keys(client)
        client.set_missing_host_key_policy(get_host_key_policy(auto_trust=True))
        
        kwargs = {
            "hostname": self.host,
            "port": self.port,
            "username": self.username,
            "timeout": self.timeout,
            "allow_agent": bool(self.use_agent),
            "look_for_keys": bool(self.use_agent),
            "compress": self.enable_compression,  # L3: Enable compression
        }
        
        if self.password:
            kwargs["password"] = self.password
        
        pkey = None
        if self.pkey_str:
            # Try RSA key first (most common)
            try:
                pkey = paramiko.RSAKey.from_private_key(
                    file_obj=StringIO(self.pkey_str),
                    password=self.passphrase
                )
                logger.debug(f"Successfully parsed RSA key for {self.username}@{self.host}")
            except (paramiko.SSHException, ValueError) as e:
                logger.debug(f"RSA key parse failed: {e}, trying Ed25519...")
                try:
                    pkey = paramiko.Ed25519Key.from_private_key(
                        file_obj=StringIO(self.pkey_str),
                        password=self.passphrase
                    )
                    logger.debug(f"Successfully parsed Ed25519 key for {self.username}@{self.host}")
                except (paramiko.SSHException, ValueError) as e2:
                    logger.debug(f"Failed to parse private key: RSA error: {e}, Ed25519 error: {e2}")
                    raise paramiko.AuthenticationException("Invalid private key format or passphrase")
        elif self.pkey_path:
            p = Path(self.pkey_path).expanduser()
            if p.exists():
                try:
                    pkey = paramiko.RSAKey.from_private_key_file(str(p), password=self.passphrase)
                    logger.debug(f"Successfully loaded RSA key from {p}")
                except (paramiko.SSHException, ValueError, IOError) as e:
                    logger.debug(f"RSA key load failed: {e}, trying Ed25519...")
                    try:
                        pkey = paramiko.Ed25519Key.from_private_key_file(str(p), password=self.passphrase)
                        logger.debug(f"Successfully loaded Ed25519 key from {p}")
                    except (paramiko.SSHException, ValueError, IOError) as e2:
                        logger.error(f"Failed to load private key from {p}: RSA error: {e}, Ed25519 error: {e2}")
                        raise paramiko.AuthenticationException(f"Cannot read private key file: {p}")
        
        if pkey is not None:
            kwargs["pkey"] = pkey
        
        try:
            client.connect(**kwargs)
            
            # L3: Enable keepalive for connection stability
            if self.keepalive_seconds > 0:
                transport = client.get_transport()
                if transport:
                    transport.set_keepalive(self.keepalive_seconds)
                    logger.debug(f"Enabled keepalive: {self.keepalive_seconds}s")
            
            self.client = client
            self.sftp = client.open_sftp()
            logger.info(f"Successfully connected to {self.username}@{self.host}:{self.port}")
        except paramiko.AuthenticationException as e:
            logger.error(f"Authentication failed for {self.username}@{self.host}: {e}")
            raise
        except paramiko.SSHException as e:
            logger.error(f"SSH connection failed to {self.host}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to {self.host}: {e}")
            raise paramiko.SSHException(f"Connection failed: {e}")
    
    def close(self) -> None:
        """Close SSH connection and SFTP channel gracefully."""
        try:
            if self.sftp:
                self.sftp.close()
                logger.debug(f"SFTP connection closed for {self.id}")
        except Exception as e:
            logger.warning(f"Error closing SFTP: {e}")
        finally:
            self.sftp = None
        
        try:
            if self.client:
                self.client.close()
                logger.debug(f"SSH connection closed for {self.id}")
        except Exception as e:
            logger.warning(f"Error closing SSH client: {e}")
        finally:
            self.client = None
