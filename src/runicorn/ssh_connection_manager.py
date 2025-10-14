"""
Unified SSH Connection Manager

Provides a single SSH connection that can be shared between different features.
This ensures efficient resource usage and seamless mode switching.
"""
from __future__ import annotations

import logging
import threading
import time
from io import StringIO
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

import paramiko
from .ssh_host_keys import load_host_keys, get_host_key_policy

logger = logging.getLogger(__name__)


class UnifiedSSHConnection:
    """
    Unified SSH connection that can be shared across different features.
    
    This class maintains a single SSH/SFTP connection that can be used by:
    - Smart mode (RemoteStorageAdapter)
    - Mirror mode (MirrorTask)
    - Other features that need SSH access
    """
    
    # Singleton instance storage
    _instances: Dict[str, 'UnifiedSSHConnection'] = {}
    _lock = threading.Lock()
    
    @classmethod
    def get_or_create(
        cls,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        private_key_path: Optional[str] = None,
        passphrase: Optional[str] = None,
        use_agent: bool = True,
        timeout: float = 15.0
    ) -> 'UnifiedSSHConnection':
        """
        Get existing connection or create a new one.
        
        Uses singleton pattern to ensure only one connection per host/user combo.
        """
        key = f"{username}@{host}:{port}"
        
        with cls._lock:
            if key in cls._instances and cls._instances[key].is_connected():
                logger.info(f"Reusing existing SSH connection for {key}")
                return cls._instances[key]
            
            logger.info(f"Creating new SSH connection for {key}")
            instance = cls(
                host, port, username, password, private_key,
                private_key_path, passphrase, use_agent, timeout
            )
            cls._instances[key] = instance
            return instance
    
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        private_key_path: Optional[str] = None,
        passphrase: Optional[str] = None,
        use_agent: bool = True,
        timeout: float = 15.0
    ):
        """Initialize SSH connection parameters."""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.private_key = private_key
        self.private_key_path = private_key_path
        self.passphrase = passphrase
        self.use_agent = use_agent
        self.timeout = timeout
        
        # Connection objects
        self._ssh_client: Optional[paramiko.SSHClient] = None
        self._sftp_client: Optional[paramiko.SFTPClient] = None
        
        # Connection state
        self._connected = False
        self._connection_lock = threading.RLock()
        
        # Reference counting for shared usage
        self._ref_count = 0
        self._ref_lock = threading.Lock()
        
        # Connection info
        self.connection_id = f"{username}@{host}:{port}"
        self.connected_at: Optional[float] = None
    
    def connect(self) -> Tuple[bool, Optional[str]]:
        """
        Establish SSH connection.
        
        Returns:
            (success, error_message)
        """
        with self._connection_lock:
            if self._connected:
                logger.debug(f"Already connected to {self.connection_id}")
                return True, None
            
            try:
                # Create SSH client
                client = paramiko.SSHClient()
                # Load known hosts and set secure policy
                load_host_keys(client)
                # Use TOFU (Trust On First Use) policy by default
                client.set_missing_host_key_policy(get_host_key_policy(auto_trust=True))
                
                # Prepare connection parameters
                kwargs = {
                    "hostname": self.host,
                    "port": self.port,
                    "username": self.username,
                    "timeout": self.timeout,
                    "allow_agent": self.use_agent,
                    "look_for_keys": self.use_agent,
                }
                
                # Handle authentication
                if self.password:
                    kwargs["password"] = self.password
                
                # Handle private key
                pkey = self._load_private_key()
                if pkey:
                    kwargs["pkey"] = pkey
                
                # Connect
                client.connect(**kwargs)
                
                # Open SFTP channel
                sftp = client.open_sftp()
                
                # Store connections
                self._ssh_client = client
                self._sftp_client = sftp
                self._connected = True
                self.connected_at = time.time()
                
                logger.info(f"Successfully connected to {self.connection_id}")
                return True, None
                
            except paramiko.AuthenticationException as e:
                error_msg = f"Authentication failed: {e}"
                logger.error(error_msg)
                return False, error_msg
            except paramiko.SSHException as e:
                error_msg = f"SSH connection failed: {e}"
                logger.error(error_msg)
                return False, error_msg
            except Exception as e:
                error_msg = f"Unexpected error: {e}"
                logger.error(error_msg)
                return False, error_msg
    
    def disconnect(self, force: bool = False) -> None:
        """
        Disconnect SSH connection.
        
        Args:
            force: Force disconnect even if there are active references
        """
        with self._connection_lock:
            if not force:
                with self._ref_lock:
                    if self._ref_count > 0:
                        logger.warning(
                            f"Cannot disconnect {self.connection_id}: "
                            f"{self._ref_count} active references"
                        )
                        return
            
            if not self._connected:
                return
            
            # Close SFTP
            if self._sftp_client:
                try:
                    self._sftp_client.close()
                except Exception as e:
                    logger.warning(f"Error closing SFTP: {e}")
                finally:
                    self._sftp_client = None
            
            # Close SSH
            if self._ssh_client:
                try:
                    self._ssh_client.close()
                except Exception as e:
                    logger.warning(f"Error closing SSH: {e}")
                finally:
                    self._ssh_client = None
            
            self._connected = False
            self.connected_at = None
            
            # Remove from instances
            key = self.connection_id
            if key in self._instances:
                del self._instances[key]
            
            logger.info(f"Disconnected from {self.connection_id}")
    
    def acquire(self) -> None:
        """
        Acquire a reference to this connection.
        
        Call this when starting to use the connection.
        """
        with self._ref_lock:
            self._ref_count += 1
            logger.debug(f"Acquired connection {self.connection_id} (refs: {self._ref_count})")
    
    def release(self) -> None:
        """
        Release a reference to this connection.
        
        Call this when done using the connection.
        """
        with self._ref_lock:
            if self._ref_count > 0:
                self._ref_count -= 1
                logger.debug(f"Released connection {self.connection_id} (refs: {self._ref_count})")
    
    def is_connected(self) -> bool:
        """Check if connection is active."""
        with self._connection_lock:
            if not self._connected:
                return False
            
            # Verify connection is still alive
            if self._ssh_client:
                try:
                    transport = self._ssh_client.get_transport()
                    if transport and transport.is_active():
                        return True
                except Exception:
                    pass
            
            self._connected = False
            return False
    
    def get_ssh_client(self) -> Optional[paramiko.SSHClient]:
        """Get SSH client for command execution."""
        if self.is_connected():
            return self._ssh_client
        return None
    
    def get_sftp_client(self) -> Optional[paramiko.SFTPClient]:
        """Get SFTP client for file operations."""
        if self.is_connected():
            return self._sftp_client
        return None
    
    def execute_command(self, command: str, timeout: float = 30.0) -> Tuple[str, str, int]:
        """
        Execute command on remote server.
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds
            
        Returns:
            (stdout, stderr, exit_code)
        """
        ssh = self.get_ssh_client()
        if not ssh:
            raise RuntimeError("Not connected")
        
        try:
            stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
            
            # Read output
            out = stdout.read().decode('utf-8', errors='replace')
            err = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()
            
            return out, err, exit_code
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise
    
    def _load_private_key(self) -> Optional[paramiko.PKey]:
        """Load private key for authentication."""
        if self.private_key:
            # Try different key types
            for key_class in [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey]:
                try:
                    return key_class.from_private_key(
                        file_obj=StringIO(self.private_key),
                        password=self.passphrase
                    )
                except Exception:
                    continue
        
        if self.private_key_path:
            key_path = Path(self.private_key_path).expanduser()
            if key_path.exists():
                # Try different key types
                for key_class in [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey]:
                    try:
                        return key_class.from_private_key_file(
                            str(key_path),
                            password=self.passphrase
                        )
                    except Exception:
                        continue
        
        return None
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "connected": self.is_connected(),
            "connection_id": self.connection_id,
            "connected_at": self.connected_at,
            "reference_count": self._ref_count,
        }
    
    @classmethod
    def disconnect_all(cls) -> None:
        """Disconnect all active connections."""
        with cls._lock:
            for connection in list(cls._instances.values()):
                try:
                    connection.disconnect(force=True)
                except Exception as e:
                    logger.error(f"Error disconnecting {connection.connection_id}: {e}")
            cls._instances.clear()
