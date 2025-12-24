# Remote Viewer API Code Examples

> **Version**: v0.5.4  
> **Last Updated**: 2025-12-22

[English](REMOTE_API_EXAMPLES.md) | [简体中文](../zh/REMOTE_API_EXAMPLES.md)

---

## 📖 Table of Contents

- [Python Client](#python-client)
- [JavaScript Client](#javascript-client)
- [Real-World Use Cases](#real-world-use-cases)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

---

## Python Client

### Complete Python Client Class

```python
import requests
from typing import Optional, Dict, List, Any

class RunicornRemoteClient:
    """Runicorn Remote Viewer API Client"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:23300"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def connect(
        self,
        host: str,
        username: str,
        port: int = 22,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        private_key_path: Optional[str] = None,
        passphrase: Optional[str] = None,
        use_agent: bool = True,
    ) -> Dict[str, Any]:
        """
        Establish SSH connection.

        Args:
            host: Remote server address
            username: SSH username
            port: SSH port
            password: SSH password (optional)
            private_key: Private key content (optional)
            private_key_path: Private key path (optional)
            passphrase: Private key passphrase (optional)
            use_agent: Use SSH agent (default: True)

        Returns:
            Response dictionary containing connection_id
        """
        payload = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "private_key": private_key,
            "private_key_path": private_key_path,
            "passphrase": passphrase,
            "use_agent": use_agent,
        }

        response = self.session.post(
            f"{self.base_url}/api/remote/connect",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def list_sessions(self) -> List[Dict[str, Any]]:
        response = self.session.get(f"{self.base_url}/api/remote/sessions")
        response.raise_for_status()
        return response.json()["sessions"]

    def disconnect(self, *, host: str, port: int, username: str) -> Dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/api/remote/disconnect",
            json={"host": host, "port": port, "username": username},
        )
        response.raise_for_status()
        return response.json()

    def list_conda_envs(self, *, connection_id: str) -> List[Dict[str, Any]]:
        response = self.session.get(
            f"{self.base_url}/api/remote/conda-envs",
            params={"connection_id": connection_id},
        )
        response.raise_for_status()
        return response.json()["envs"]

    def get_remote_config(self, *, connection_id: str, conda_env: str = "system") -> Dict[str, Any]:
        response = self.session.get(
            f"{self.base_url}/api/remote/config",
            params={"connection_id": connection_id, "conda_env": conda_env},
        )
        response.raise_for_status()
        return response.json()

    def start_viewer(
        self,
        *,
        host: str,
        username: str,
        remote_root: str,
        port: int = 22,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        private_key_path: Optional[str] = None,
        passphrase: Optional[str] = None,
        use_agent: bool = True,
        local_port: Optional[int] = None,
        remote_port: Optional[int] = None,
        conda_env: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "private_key": private_key,
            "private_key_path": private_key_path,
            "passphrase": passphrase,
            "use_agent": use_agent,
            "remote_root": remote_root,
            "local_port": local_port,
            "remote_port": remote_port,
            "conda_env": conda_env,
        }
        response = self.session.post(f"{self.base_url}/api/remote/viewer/start", json=payload)
        response.raise_for_status()
        return response.json()

    def stop_viewer(self, *, session_id: str) -> Dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/api/remote/viewer/stop",
            json={"session_id": session_id},
        )
        response.raise_for_status()
        return response.json()

    def get_viewer_session(self, *, session_id: str) -> Dict[str, Any]:
        response = self.session.get(f"{self.base_url}/api/remote/viewer/status/{session_id}")
        response.raise_for_status()
        return response.json()
    
    def close(self):
        """Close session"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

### Basic Usage Example

```python
from runicorn_remote_client import RunicornRemoteClient

# Create client
with RunicornRemoteClient() as client:
    # 1. Connect to remote server
    result = client.connect(host="gpu-server.com", username="mluser", private_key_path="~/.ssh/id_rsa")
    
    connection_id = result["connection_id"]
    print(f"✓ Connected: {connection_id}")
    
    # 2. (optional) List Python environments
    envs = client.list_conda_envs(connection_id=connection_id)
    print(f"✓ Found {len(envs)} env(s)")

    # 3. Start Remote Viewer
    viewer = client.start_viewer(host="gpu-server.com", username="mluser", remote_root="/data/experiments")
    session_id = viewer["session"]["sessionId"]
    print(f"✓ Viewer started: {viewer['session']['url']}")

    # 4. Monitor status
    status = client.get_viewer_session(session_id=session_id)
    print(f"✓ Viewer status: {status['status']}")

    # 5. Cleanup when done
    input("Press Enter to disconnect...")
    client.stop_viewer(session_id=session_id)
    client.disconnect(host="gpu-server.com", port=22, username="mluser")
    print("✓ Disconnected")
```

---

## JavaScript Client

### Complete JavaScript/TypeScript Client Class

```javascript
class RunicornRemoteClient {
  /**
   * Runicorn Remote Viewer API Client
   * @param {string} baseUrl - API base URL
   */
  constructor(baseUrl = 'http://localhost:23300') {
    this.baseUrl = baseUrl;
  }

  /**
   * Connect to remote server
   */
  async connect(options) {
    const {
      host,
      username,
      port = 22,
      password = null,
      privateKey = null,
      privateKeyPath = null,
      passphrase = null,
      useAgent = true
    } = options;

    const payload = {
      host,
      port,
      username,
      password,
      private_key: privateKey,
      private_key_path: privateKeyPath,
      passphrase,
      use_agent: useAgent,
    };

    const response = await fetch(`${this.baseUrl}/api/remote/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Connection failed: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * List all active SSH sessions
   */
  async listSessions() {
    const response = await fetch(`${this.baseUrl}/api/remote/sessions`);
    
    if (!response.ok) {
      throw new Error(`Failed to list sessions: ${response.statusText}`);
    }

    const data = await response.json();
    return data.sessions;
  }

  /**
   * Disconnect an SSH session
   */
  async disconnect({ host, username, port = 22 }) {
    const response = await fetch(`${this.baseUrl}/api/remote/disconnect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ host, port, username }),
    });

    if (!response.ok) {
      throw new Error(`Disconnect failed: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * List Python environments
   */
  async listCondaEnvs(connectionId) {
    const response = await fetch(`${this.baseUrl}/api/remote/conda-envs?connection_id=${connectionId}`);

    if (!response.ok) {
      throw new Error(`Failed to list environments: ${response.statusText}`);
    }

    const data = await response.json();
    return data.envs;
  }

  /**
   * Start Remote Viewer
   */
  async startViewer(options) {
    const {
      host,
      username,
      remoteRoot,
      port = 22,
      password = null,
      privateKey = null,
      privateKeyPath = null,
      passphrase = null,
      useAgent = true,
      localPort = null,
      remotePort = null,
      condaEnv = null,
    } = options;

    const payload = {
      host,
      port,
      username,
      password,
      private_key: privateKey,
      private_key_path: privateKeyPath,
      passphrase,
      use_agent: useAgent,
      remote_root: remoteRoot,
      local_port: localPort,
      remote_port: remotePort,
      conda_env: condaEnv,
    };

    const response = await fetch(`${this.baseUrl}/api/remote/viewer/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Failed to start viewer: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Stop Remote Viewer
   */
  async stopViewer(sessionId) {
    const response = await fetch(`${this.baseUrl}/api/remote/viewer/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to stop viewer: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get Viewer session status
   */
  async getViewerSession(sessionId) {
    const response = await fetch(`${this.baseUrl}/api/remote/viewer/status/${sessionId}`);

    if (!response.ok) {
      throw new Error(`Failed to get status: ${response.statusText}`);
    }

    return response.json();
  }
}

// Export
export default RunicornRemoteClient;
```

### JavaScript Usage Example

```javascript
// Create client
const client = new RunicornRemoteClient();

(async () => {
  try {
    // 1. Connect to remote server
    const { connection_id } = await client.connect({
      host: 'gpu-server.com',
      username: 'mluser',
      privateKeyPath: '~/.ssh/id_rsa',
      useAgent: true,
    });

    console.log(`✓ Connected: ${connection_id}`);

    // 2. List environments
    const envs = await client.listCondaEnvs(connection_id);
    
    console.log(`✓ Found ${envs.length} env(s)`);
    envs.forEach(env => {
      console.log(`  - ${env.name}: Python ${env.python_version} (${env.type})`);
    });

    // 3. Start Viewer
    const viewer = await client.startViewer({
      host: 'gpu-server.com',
      port: 22,
      username: 'mluser',
      privateKeyPath: '~/.ssh/id_rsa',
      useAgent: true,
      remoteRoot: '~/runicorn_data',
      condaEnv: null,
    });

    const sessionId = viewer.session.sessionId;
    console.log(`✓ Viewer started: ${viewer.session.url}`);

    // 4. Monitor status
    const status = await client.getViewerSession(sessionId);
    console.log(`✓ Viewer status: ${status.status}`);

    // 5. Cleanup when done
    await client.stopViewer(sessionId);
    await client.disconnect({ host: 'gpu-server.com', port: 22, username: 'mluser' });
    console.log('✓ Disconnected');

  } catch (error) {
    console.error('Error:', error.message);
  }
})();
```

---

## Real-World Use Cases

### Use Case 1: Automated Training Monitoring

```python
import time
from runicorn_remote_client import RunicornRemoteClient

def monitor_training(host, username, key_path, env_name):
    """Automatically connect and monitor remote training"""
    
    with RunicornRemoteClient() as client:
        # Connect
        result = client.connect(host=host, username=username, private_key_path=key_path)
        
        viewer = client.start_viewer(
            host=host,
            username=username,
            remote_root="~/runicorn_data",
            private_key_path=key_path,
            conda_env=env_name,
        )
        session_id = viewer["session"]["sessionId"]
        print(f"Viewer URL: {viewer['session']['url']}")
        
        # Monitoring loop
        while True:
            status = client.get_viewer_session(session_id=session_id)
            print(f"Status: {status['status']}, Uptime: {status['uptimeSeconds']}s")
            time.sleep(30)  # Check every 30 seconds

# Usage
monitor_training(
    host="gpu-server.com",
    username="mluser",
    key_path="~/.ssh/id_rsa",
    env_name="pytorch-env"
)
```

### Use Case 2: Multi-Server Management

```python
from runicorn_remote_client import RunicornRemoteClient

def manage_multiple_servers(servers):
    """Connect and manage multiple servers"""
    
    client = RunicornRemoteClient()
    connections = []
    
    try:
        # Connect to all servers
        for server in servers:
            result = client.connect(**server)
            conn_id = result["connection_id"]
            connections.append(conn_id)
            
            print(f"✓ Connected to {server['host']}: {conn_id}")
        
        # List all sessions
        all_sessions = client.list_sessions()
        print(f"\nTotal {len(all_sessions)} active session(s):")
        
        for sess in all_sessions:
            print(f"  - {sess['key']}: connected={sess['connected']}")
        
        # Interactive management
        while True:
            print("\nOptions: (l)ist, (q)uit")
            choice = input("> ").lower()
            
            if choice == 'l':
                for sess in client.list_sessions():
                    print(f"{sess['key']}: connected={sess['connected']}")
            
            elif choice == 'q':
                break
    
    finally:
        # Cleanup all connections
        for server in servers:
            try:
                client.disconnect(host=server["host"], port=server.get("port", 22), username=server["username"])
                print(f"✓ Disconnected: {server['host']}")
            except Exception as e:
                print(f"✗ Failed to disconnect: {server['host']} - {e}")
        
        client.close()

# Usage
servers = [
    {
        "host": "gpu-server-01.com",
        "username": "mluser",
        "private_key_path": "~/.ssh/id_rsa"
    },
    {
        "host": "gpu-server-02.com",
        "username": "mluser",
        "private_key_path": "~/.ssh/id_rsa"
    },
]

manage_multiple_servers(servers)
```

### Use Case 3: Environment Detection and Selection

```python
from runicorn_remote_client import RunicornRemoteClient

def select_best_environment(host, username, key_path):
    """Automatically select best environment"""
    
    with RunicornRemoteClient() as client:
        # Connect
        result = client.connect(host=host, username=username, private_key_path=key_path)
        conn_id = result["connection_id"]
        
        envs = client.list_conda_envs(connection_id=conn_id)
        
        if not envs:
            print("Error: No environments with Runicorn found")
            return None

        best_env = next((e for e in envs if e.get("is_default")), envs[0])
        print(f"Selected environment: {best_env['name']}")
        print(f"  Python: {best_env['python_version']}")
        print(f"  Type: {best_env['type']}")
        
        # Start Viewer
        viewer = client.start_viewer(
            host=host,
            username=username,
            remote_root="~/runicorn_data",
            private_key_path=key_path,
            conda_env=best_env["name"],
        )
        
        return viewer["session"]["url"]

# Usage
url = select_best_environment(
    host="gpu-server.com",
    username="mluser",
    key_path="~/.ssh/id_rsa"
)

if url:
    print(f"\n✓ Viewer available: {url}")
```

---

## Error Handling

### Python Error Handling Example

```python
from runicorn_remote_client import RunicornRemoteClient
import requests

def safe_connect_and_start():
    """Connect with complete error handling"""
    
    client = RunicornRemoteClient()
    conn_id = None
    
    try:
        # Connect
        result = client.connect(host="gpu-server.com", username="mluser", private_key_path="~/.ssh/id_rsa")
        conn_id = result["connection_id"]
        
    except requests.exceptions.Timeout:
        print("Error: Connection timeout, check if server is reachable")
        return
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 409:
            print("Error: Host key confirmation required")
        elif e.response.status_code == 503:
            print("Error: SSH service unavailable")
        else:
            print(f"Error: HTTP {e.response.status_code} - {e}")
        return
    
    except Exception as e:
        print(f"Error: Connection failed - {e}")
        return
    
    try:
        viewer = client.start_viewer(
            host="gpu-server.com",
            username="mluser",
            remote_root="~/runicorn_data",
            private_key_path="~/.ssh/id_rsa",
            conda_env=None,
        )
        print(f"✓ Success: {viewer['session']['url']}")
        
    except requests.exceptions.HTTPError as e:
        error_data = e.response.json()
        
        print(f"Error: {error_data.get('detail', str(e))}")
    
    except Exception as e:
        print(f"Error: Start failed - {e}")
    
    finally:
        # Ensure cleanup
        if conn_id:
            try:
                client.disconnect(host="gpu-server.com", port=22, username="mluser")
            except:
                pass
        
        client.close()

safe_connect_and_start()
```

---

## Best Practices

### 1. Use Context Managers

```python
# ✅ Recommended
with RunicornRemoteClient() as client:
    # ... use client
    pass  # Automatic cleanup

# ❌ Not recommended
client = RunicornRemoteClient()
# ... use
client.close()  # Easy to forget
```

### 2. Set Appropriate Timeouts

```python
# For unstable networks
result = client.connect(
    host="remote-server.com",
    username="user",
    private_key_path="~/.ssh/id_rsa",
    port=22,
)
```

### 3. Use Environment Variables for Credentials

```python
import os

host = os.getenv("REMOTE_HOST")
username = os.getenv("REMOTE_USERNAME")
key_path = os.getenv("SSH_KEY_PATH")

client.connect(
    host=host,
    username=username,
    private_key_path=key_path
)
```

### 4. Logging

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    result = client.connect(...)
    logger.info(f"Connected: {result['connection_id']}")
except Exception as e:
    logger.error(f"Connection failed: {e}", exc_info=True)
```

---

**Author**: Runicorn Development Team  
**Version**: v0.5.4  
**Last Updated**: 2025-12-22

**[Back to API Docs](README.md)** | **[View API Reference](remote_api.md)**
