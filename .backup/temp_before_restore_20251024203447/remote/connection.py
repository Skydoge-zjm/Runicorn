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
from paramiko import SSHClient, SFTPClient, AutoAddPolicy

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
                self._client.set_missing_host_key_policy(AutoAddPolicy())
                
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
                self._client.connect(**connect_kwargs)
                
                # Enable keepalive
                transport = self._client.get_transport()
                if transport:
                    transport.set_keepalive(self.config.keepalive_interval)
                
                self._connected = True
                logger.info(f"SSH connected to {self.config.get_key()}")
                return True
                
            except Exception as e:
                logger.error(f"SSH connection failed: {e}")
                self._connected = False
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
