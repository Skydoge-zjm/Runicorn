"""
Remote Viewer API Extension for RunicornClient
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .http import RunicornClient


class RemoteAPI:
    """Remote Viewer API methods."""
    
    def __init__(self, client: RunicornClient):
        self.client = client
    
    def connect(
        self,
        host: str,
        port: int = 22,
        username: str = None,
        password: str = None,
        private_key_path: str = None,
        passphrase: str = None,
    ) -> Dict[str, Any]:
        """
        Establish SSH connection to remote server.
        
        Args:
            host: Remote host
            port: SSH port (default: 22)
            username: SSH username
            password: SSH password (optional)
            private_key_path: Path to private key (optional)
            passphrase: Private key passphrase (optional)
            
        Returns:
            Connection info
        """
        payload = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "private_key_path": private_key_path,
            "passphrase": passphrase,
        }
        
        return self.client.post("/api/remote/connect", json=payload)
    
    def disconnect(
        self,
        host: str,
        port: int = 22,
        username: str = None,
    ) -> Dict[str, Any]:
        """
        Disconnect from remote server.
        
        Args:
            host: Remote host to disconnect
            port: SSH port (default: 22)
            username: SSH username (required to uniquely identify connection)
            
        Returns:
            Status message
        """
        if username is None:
            raise ValueError("username is required to disconnect")
        payload = {"host": host, "port": port, "username": username}
        return self.client.post("/api/remote/disconnect", json=payload)
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List active SSH connections.
        
        Returns:
            List of SSH sessions
        """
        data = self.client.get("/api/remote/sessions")
        return data.get("sessions", [])
    
    def start_viewer(
        self,
        host: Optional[str] = None,
        remote_root: str = None,
        port: int = 22,
        username: Optional[str] = None,
        password: Optional[str] = None,
        private_key_path: Optional[str] = None,
        passphrase: Optional[str] = None,
        local_port: Optional[int] = None,
        remote_port: Optional[int] = None,
        conda_env: Optional[str] = None,
        connection_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Start remote viewer and create SSH tunnel.
        
        Server expects full SSH params (host, port, username). For backward
        compatibility, connection_id (format: user@host:port) can be passed
        instead of host/port/username; it will be parsed to derive them.
        
        Args:
            host: Remote server hostname or IP (required unless connection_id)
            remote_root: Remote storage root path
            port: SSH port (default: 22)
            username: SSH username (required unless connection_id)
            password: SSH password (optional)
            private_key_path: Path to private key (optional)
            passphrase: Private key passphrase (optional)
            local_port: Local port for tunnel (auto if None)
            remote_port: Remote viewer port (auto if None)
            conda_env: Conda environment name (optional)
            connection_id: [Deprecated] Use host, port, username instead.
                If provided, parses user@host:port to derive host, port, username.
            
        Returns:
            Viewer session info
        """
        if connection_id is not None:
            host, port, username = self._parse_connection_id(connection_id)
        if host is None or username is None:
            raise ValueError("host and username are required (or pass connection_id for backward compatibility)")
        if remote_root is None:
            raise ValueError("remote_root is required")
        
        payload = {
            "host": host,
            "port": port,
            "username": username,
            "remote_root": remote_root,
        }
        if password is not None:
            payload["password"] = password
        if private_key_path is not None:
            payload["private_key_path"] = private_key_path
        if passphrase is not None:
            payload["passphrase"] = passphrase
        if local_port is not None:
            payload["local_port"] = local_port
        if remote_port is not None:
            payload["remote_port"] = remote_port
        if conda_env is not None:
            payload["conda_env"] = conda_env
        
        return self.client.post("/api/remote/viewer/start", json=payload)
    
    @staticmethod
    def _parse_connection_id(connection_id: str) -> tuple:
        """Parse connection_id (user@host:port) to (host, port, username)."""
        try:
            username_host, port_str = connection_id.rsplit(":", 1)
            username, host = username_host.split("@", 1)
            return host, int(port_str), username
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid connection_id format '{connection_id}': expected user@host:port") from e
    
    def stop_viewer(self, session_id: str) -> Dict[str, Any]:
        """
        Stop remote viewer session.
        
        Args:
            session_id: Viewer session ID
            
        Returns:
            Status message
        """
        payload = {"session_id": session_id}
        return self.client.post("/api/remote/viewer/stop", json=payload)
    
    def list_viewer_sessions(self) -> List[Dict[str, Any]]:
        """
        List active remote viewer sessions.
        
        Returns:
            List of viewer sessions
        """
        data = self.client.get("/api/remote/viewer/sessions")
        return data.get("sessions", [])
    
    def list_remote_storage_candidates(
        self,
        connection_id: str,
        conda_env: str = "system",
        scan_root: Optional[str] = None,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Detect candidate Runicorn storage roots under the remote user's home directory.
        
        Args:
            connection_id: SSH connection ID
            conda_env: Conda environment name used to resolve a Python interpreter
            
        Returns:
            List of candidate storage roots
        """
        params = {
            "connection_id": connection_id,
            "conda_env": conda_env,
            "max_depth": max_depth,
        }
        if scan_root is not None:
            params["scan_root"] = scan_root

        data = self.client.get("/api/remote/storage-candidates", params=params)
        return data.get("candidates", [])
    
    def get_remote_status(self) -> Dict[str, Any]:
        """
        Get overall remote access status.
        
        Returns:
            Status info
        """
        return self.client.get("/api/remote/status")
    
    def confirm_host_key(
        self,
        host: str,
        port: int,
        key_type: str,
        public_key: str,
        fingerprint_sha256: str,
    ) -> Dict[str, Any]:
        """
        Accept and add host key to known_hosts after HostKeyConfirmationRequiredError.
        
        Call this when connect() or start_viewer() raises HostKeyConfirmationRequiredError.
        Then retry the original operation.
        
        Args:
            host: Remote host
            port: SSH port
            key_type: Key type (e.g. ssh-ed25519, ssh-rsa)
            public_key: Full public key content
            fingerprint_sha256: SHA256 fingerprint of the key
            
        Returns:
            Success status
        """
        payload = {
            "host": host,
            "port": port,
            "key_type": key_type,
            "public_key": public_key,
            "fingerprint_sha256": fingerprint_sha256,
        }
        return self.client.post("/api/remote/known-hosts/accept", json=payload)
