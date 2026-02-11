"""
SSH Connection Management

Provides unified SSH connection with connection pooling and reuse.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Tuple

import paramiko
from paramiko import SSHClient, SFTPClient

from ..config import get_known_hosts_file_path
from .host_key import (
    HostKeyChangedError,
    HostKeyConfirmationRequiredError,
    HostKeyProblem,
    HostKeyVerificationReason,
    UnknownHostKeyError,
)
from .known_hosts import compute_fingerprint_sha256, format_known_hosts_host

logger = logging.getLogger(__name__)


@dataclass
class SSHConfig:
    """SSH connection configuration."""
    host: str
    port: int = 22
    username: str = ""
    password: Optional[str] = None
    private_key: Optional[str] = None  # Private key content
    private_key_path: Optional[str] = None  # Path to key file
    passphrase: Optional[str] = None
    use_agent: bool = True
    timeout: int = 30
    keepalive_interval: int = 30  # Send keepalive every 30s
    compression: bool = True
    
    def get_key(self) -> str:
        """Get unique key for connection pool."""
        return f"{self.username}@{self.host}:{self.port}"


def _build_host_key_problem(
    *,
    host: str,
    port: int,
    key: paramiko.PKey,
    reason: HostKeyVerificationReason,
    expected_key: Optional[paramiko.PKey] = None,
) -> HostKeyProblem:
    known_hosts_host = format_known_hosts_host(host, port)
    key_type = key.get_name()
    key_base64 = key.get_base64()
    public_key = f"{key_type} {key_base64}"
    fingerprint_sha256 = compute_fingerprint_sha256(key.asbytes())

    expected_fingerprint_sha256 = None
    expected_public_key = None
    if expected_key is not None:
        expected_key_type = expected_key.get_name()
        expected_key_base64 = expected_key.get_base64()
        expected_public_key = f"{expected_key_type} {expected_key_base64}"
        expected_fingerprint_sha256 = compute_fingerprint_sha256(expected_key.asbytes())

    return HostKeyProblem(
        host=host,
        port=port,
        known_hosts_host=known_hosts_host,
        key_type=key_type,
        fingerprint_sha256=fingerprint_sha256,
        public_key=public_key,
        reason=reason,
        expected_fingerprint_sha256=expected_fingerprint_sha256,
        expected_public_key=expected_public_key,
    )


class _RejectUnknownHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port

    def missing_host_key(self, client: SSHClient, hostname: str, key: paramiko.PKey) -> None:
        problem = _build_host_key_problem(
            host=self._host,
            port=self._port,
            key=key,
            reason="unknown",
        )
        raise UnknownHostKeyError(problem)


class SSHConnection:
    """
    SSH connection wrapper with automatic reconnection.
    
    Features:
    - Auto keepalive
    - Connection health check
    - SFTP support
    - Command execution
    """
    
    def __init__(self, config: SSHConfig):
        self.config = config
        self._client: Optional[SSHClient] = None
        self._sftp: Optional[SFTPClient] = None
        self._lock = threading.Lock()
        self._connected = False
        
    def connect(self) -> bool:
        """
        Establish SSH connection.
        
        Returns:
            True if connection successful
            
        Raises:
            Exception: If connection fails
        """
        with self._lock:
            if self._connected and self._client:
                # Already connected, check health
                if self._check_health():
                    return True
                # Unhealthy, reconnect
                self.disconnect()
            
            try:
                self._client = SSHClient()

                known_hosts_path = get_known_hosts_file_path()
                try:
                    if known_hosts_path.exists():
                        self._client.load_host_keys(str(known_hosts_path))
                except Exception as e:
                    logger.warning(f"Failed to load known_hosts from {known_hosts_path}: {e}")

                self._client.set_missing_host_key_policy(
                    _RejectUnknownHostKeyPolicy(host=self.config.host, port=self.config.port)
                )
                
                # Prepare connection kwargs
                connect_kwargs = {
                    "hostname": self.config.host,
                    "port": self.config.port,
                    "username": self.config.username,
                    "timeout": self.config.timeout,
                    "compress": self.config.compression,
                    "allow_agent": self.config.use_agent,
                }
                
                # Add authentication
                if self.config.password:
                    connect_kwargs["password"] = self.config.password
                
                if self.config.private_key:
                    # Load key from string
                    from io import StringIO
                    key_file = StringIO(self.config.private_key)
                    try:
                        pkey = paramiko.RSAKey.from_private_key(
                            key_file, 
                            password=self.config.passphrase
                        )
                    except paramiko.SSHException:
                        key_file.seek(0)
                        try:
                            pkey = paramiko.Ed25519Key.from_private_key(
                                key_file,
                                password=self.config.passphrase
                            )
                        except paramiko.SSHException:
                            key_file.seek(0)
                            pkey = paramiko.ECDSAKey.from_private_key(
                                key_file,
                                password=self.config.passphrase
                            )
                    connect_kwargs["pkey"] = pkey
                    
                elif self.config.private_key_path:
                    # Load key from file
                    key_path = Path(self.config.private_key_path).expanduser()
                    try:
                        pkey = paramiko.RSAKey.from_private_key_file(
                            str(key_path),
                            password=self.config.passphrase
                        )
                    except paramiko.SSHException:
                        try:
                            pkey = paramiko.Ed25519Key.from_private_key_file(
                                str(key_path),
                                password=self.config.passphrase
                            )
                        except paramiko.SSHException:
                            pkey = paramiko.ECDSAKey.from_private_key_file(
                                str(key_path),
                                password=self.config.passphrase
                            )
                    connect_kwargs["pkey"] = pkey
                
                # Connect
                try:
                    self._client.connect(**connect_kwargs)
                except paramiko.ssh_exception.BadHostKeyException as e:
                    problem = _build_host_key_problem(
                        host=self.config.host,
                        port=self.config.port,
                        key=e.key,
                        reason="changed",
                        expected_key=e.expected_key,
                    )
                    raise HostKeyChangedError(problem) from e
                
                # Enable keepalive
                transport = self._client.get_transport()
                if transport:
                    transport.set_keepalive(self.config.keepalive_interval)
                
                self._connected = True
                logger.info(f"SSH connected to {self.config.get_key()}")
                return True
                
            except HostKeyConfirmationRequiredError as e:
                problem = e.problem
                logger.warning(
                    "SSH host key verification requires confirmation: host=%s port=%s reason=%s key_type=%s fingerprint=%s",
                    problem.host,
                    problem.port,
                    problem.reason,
                    problem.key_type,
                    problem.fingerprint_sha256,
                )
                self._connected = False
                if self._client:
                    try:
                        self._client.close()
                    except Exception:
                        pass
                self._client = None
                raise

            except Exception as e:
                logger.error(f"SSH connection failed: {e}", exc_info=True)
                self._connected = False
                if self._client:
                    try:
                        self._client.close()
                    except Exception:
                        pass
                self._client = None
                raise
    
    def disconnect(self) -> None:
        """Close SSH connection and cleanup resources."""
        with self._lock:
            if self._sftp:
                try:
                    self._sftp.close()
                except Exception as e:
                    logger.warning(f"Error closing SFTP: {e}")
                self._sftp = None
            
            if self._client:
                try:
                    self._client.close()
                except Exception as e:
                    logger.warning(f"Error closing SSH client: {e}")
                self._client = None
            
            self._connected = False
            logger.info(f"SSH disconnected from {self.config.get_key()}")
    
    def _check_health(self) -> bool:
        """Check if connection is still alive."""
        if not self._client:
            return False
        
        transport = self._client.get_transport()
        if not transport or not transport.is_active():
            return False
        
        try:
            # Try a simple command
            transport.send_ignore()
            return True
        except Exception:
            return False
    
    def exec_command(
        self, 
        command: str, 
        timeout: Optional[int] = None
    ) -> Tuple[str, str, int]:
        """
        Execute command on remote server.
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (stdout, stderr, exit_code)
            
        Raises:
            RuntimeError: If not connected
            Exception: If command execution fails
        """
        if not self._connected or not self._client:
            raise RuntimeError("Not connected to SSH server")
        
        try:
            stdin, stdout, stderr = self._client.exec_command(
                command,
                timeout=timeout or self.config.timeout
            )
            
            stdout_str = stdout.read().decode('utf-8')
            stderr_str = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()
            
            return stdout_str, stderr_str, exit_code
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise
    
    def get_sftp(self) -> SFTPClient:
        """
        Get SFTP client for file operations.
        
        Returns:
            SFTP client instance
            
        Raises:
            RuntimeError: If not connected
        """
        if not self._connected or not self._client:
            raise RuntimeError("Not connected to SSH server")
        
        with self._lock:
            if not self._sftp or not self._sftp.sock:
                self._sftp = self._client.open_sftp()
            
            return self._sftp
    
    @property
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self._connected and self._check_health()


class SSHConnectionPool:
    """
    Connection pool for SSH connections.
    
    Features:
    - Connection reuse
    - Automatic cleanup
    - Thread-safe
    """
    
    def __init__(self):
        self._pool: Dict[str, SSHConnection] = {}
        self._lock = threading.Lock()
    
    def get_or_create(self, config: SSHConfig) -> SSHConnection:
        """
        Get existing connection or create new one.
        
        Args:
            config: SSH configuration
            
        Returns:
            SSH connection instance
        """
        key = config.get_key()
        
        with self._lock:
            # Check if connection exists and is healthy
            if key in self._pool:
                conn = self._pool[key]
                if conn.is_connected:
                    logger.debug(f"Reusing connection: {key}")
                    return conn
                else:
                    # Connection dead, remove it
                    logger.info(f"Removing dead connection: {key}")
                    conn.disconnect()
                    del self._pool[key]
            
            # Create new connection
            logger.info(f"Creating new connection: {key}")
            conn = SSHConnection(config)
            conn.connect()
            self._pool[key] = conn
            return conn
    
    def remove(self, host: str, port: int, username: str) -> bool:
        """
        Remove connection from pool.
        
        Args:
            host: Remote host
            port: SSH port
            username: SSH username
            
        Returns:
            True if connection was removed
        """
        key = f"{username}@{host}:{port}"
        
        with self._lock:
            if key in self._pool:
                conn = self._pool[key]
                conn.disconnect()
                del self._pool[key]
                logger.info(f"Connection removed: {key}")
                return True
            return False
    
    def get_connection(self, host: str, port: int, username: str) -> Optional[SSHConnection]:
        """Get existing connection from pool (without creating)."""
        key = f"{username}@{host}:{port}"
        return self._pool.get(key)
    
    def close_all(self) -> None:
        """Close all connections in pool."""
        with self._lock:
            for conn in self._pool.values():
                try:
                    conn.disconnect()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
            self._pool.clear()
            logger.info("All connections closed")
    
    def list_connections(self) -> list[Dict[str, any]]:
        """List all active connections."""
        with self._lock:
            return [
                {
                    "key": key,
                    "host": conn.config.host,
                    "port": conn.config.port,
                    "username": conn.config.username,
                    "connected": conn.is_connected,
                }
                for key, conn in self._pool.items()
            ]
