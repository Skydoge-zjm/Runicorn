"""
SSH Tunnel for Remote Viewer

Provides local port forwarding to remote viewer instance.
"""
from __future__ import annotations

import logging
import select
import socket
import threading
from typing import Optional

import paramiko

logger = logging.getLogger(__name__)


class SSHTunnel:
    """
    SSH port forwarding tunnel.
    
    Forwards local_port to remote_host:remote_port via SSH.
    """
    
    def __init__(
        self,
        ssh_transport: paramiko.Transport,
        local_port: int,
        remote_host: str,
        remote_port: int,
        stop_event: threading.Event,
    ):
        self.ssh_transport = ssh_transport
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.stop_event = stop_event
        self._server_socket: Optional[socket.socket] = None
        
    def start(self) -> None:
        """
        Start tunnel in current thread.
        
        This method blocks until stop_event is set.
        Should be called in a separate thread.
        """
        try:
            # Create local server socket
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind(("127.0.0.1", self.local_port))
            self._server_socket.listen(5)
            self._server_socket.settimeout(1.0)  # Allow periodic check of stop_event
            
            logger.info(
                f"SSH tunnel listening on 127.0.0.1:{self.local_port} "
                f"-> {self.remote_host}:{self.remote_port}"
            )
            
            while not self.stop_event.is_set():
                try:
                    # Accept client connection
                    client_socket, client_addr = self._server_socket.accept()
                    logger.debug(f"Tunnel connection from {client_addr}")
                    
                    # Handle in separate thread
                    thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket,),
                        daemon=True
                    )
                    thread.start()
                    
                except socket.timeout:
                    # Timeout is expected, continue loop
                    continue
                except Exception as e:
                    if not self.stop_event.is_set():
                        logger.error(f"Error accepting connection: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Tunnel start failed: {e}")
            raise
        finally:
            self._cleanup()
            logger.info("SSH tunnel stopped")
    
    def _handle_client(self, client_socket: socket.socket) -> None:
        """Handle a single client connection."""
        channel = None
        try:
            # Open channel to remote
            channel = self.ssh_transport.open_channel(
                "direct-tcpip",
                (self.remote_host, self.remote_port),
                client_socket.getpeername()
            )
            
            if channel is None:
                logger.error("Failed to open SSH channel")
                client_socket.close()
                return
            
            # Bidirectional data forwarding
            while not self.stop_event.is_set():
                r, w, x = select.select([client_socket, channel], [], [], 1.0)
                
                if client_socket in r:
                    data = client_socket.recv(4096)
                    if len(data) == 0:
                        break
                    channel.send(data)
                
                if channel in r:
                    data = channel.recv(4096)
                    if len(data) == 0:
                        break
                    client_socket.send(data)
                    
        except Exception as e:
            logger.debug(f"Client connection error: {e}")
        finally:
            if channel:
                channel.close()
            client_socket.close()
    
    def _cleanup(self) -> None:
        """Cleanup resources."""
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception as e:
                logger.warning(f"Error closing server socket: {e}")
            self._server_socket = None
    
    def stop(self) -> None:
        """Stop the tunnel."""
        self.stop_event.set()
        self._cleanup()


def find_available_port(start_port: int = 8080, end_port: int = 9000) -> int:
    """
    Find an available local port.
    
    Args:
        start_port: Start of port range
        end_port: End of port range
        
    Returns:
        Available port number
        
    Raises:
        RuntimeError: If no available port found
    """
    for port in range(start_port, end_port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("127.0.0.1", port))
            sock.close()
            return port
        except OSError:
            continue
    
    raise RuntimeError(f"No available port in range {start_port}-{end_port}")
