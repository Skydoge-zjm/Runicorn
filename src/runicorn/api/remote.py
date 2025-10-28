"""
Remote Viewer API Extension for RunicornClient
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import RunicornClient


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
    
    def disconnect(self, host: str) -> Dict[str, Any]:
        """
        Disconnect from remote server.
        
        Args:
            host: Remote host to disconnect
            
        Returns:
            Status message
        """
        payload = {"host": host}
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
        connection_id: str,
        remote_root: str,
        local_port: Optional[int] = None,
        remote_port: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Start remote viewer and create SSH tunnel.
        
        Args:
            connection_id: SSH connection ID
            remote_root: Remote storage root path
            local_port: Local port for tunnel (auto if None)
            remote_port: Remote viewer port (auto if None)
            
        Returns:
            Viewer session info
        """
        payload = {
            "connection_id": connection_id,
            "remote_root": remote_root,
            "local_port": local_port,
            "remote_port": remote_port,
        }
        
        return self.client.post("/api/remote/viewer/start", json=payload)
    
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
    
    def list_remote_directory(
        self,
        connection_id: str,
        path: str,
    ) -> List[Dict[str, Any]]:
        """
        List remote directory contents.
        
        Args:
            connection_id: SSH connection ID
            path: Remote directory path
            
        Returns:
            List of files and directories
        """
        params = {
            "connection_id": connection_id,
            "path": path,
        }
        
        data = self.client.get("/api/remote/fs/list", params=params)
        return data.get("entries", [])
    
    def check_remote_path(
        self,
        connection_id: str,
        path: str,
    ) -> bool:
        """
        Check if remote path exists.
        
        Args:
            connection_id: SSH connection ID
            path: Remote path
            
        Returns:
            True if path exists
        """
        params = {
            "connection_id": connection_id,
            "path": path,
        }
        
        data = self.client.get("/api/remote/fs/exists", params=params)
        return data.get("exists", False)
    
    def get_remote_status(self) -> Dict[str, Any]:
        """
        Get overall remote access status.
        
        Returns:
            Status info
        """
        return self.client.get("/api/remote/status")
