# Remote Viewer API Code Examples

> **Version**: v0.5.0  
> **Last Updated**: 2025-10-25

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
    
    def __init__(self, base_url: str = "http://localhost:23300"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def connect(
        self,
        host: str,
        username: str,
        auth_method: str = "key",
        port: int = 22,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Connect to remote server
        
        Args:
            host: Remote server address
            username: SSH username
            auth_method: Authentication method ("key", "password", "agent")
            port: SSH port
            **kwargs: Additional parameters
                private_key_path: Private key path (auth_method="key")
                password: Password (auth_method="password")
                key_passphrase: Private key passphrase
                timeout: Connection timeout
        
        Returns:
            Response dictionary containing connection_id
        """
        payload = {
            "host": host,
            "port": port,
            "username": username,
            "auth_method": auth_method,
        }
        
        # Add authentication info
        if auth_method == "key":
            if "private_key_path" in kwargs:
                payload["private_key_path"] = kwargs["private_key_path"]
            if "key_passphrase" in kwargs:
                payload["key_passphrase"] = kwargs["key_passphrase"]
        elif auth_method == "password":
            if "password" not in kwargs:
                raise ValueError("Password required for password authentication")
            payload["password"] = kwargs["password"]
        
        # Optional parameters
        if "timeout" in kwargs:
            payload["timeout"] = kwargs["timeout"]
        
        response = self.session.post(
            f"{self.base_url}/api/remote/connect",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def list_connections(self) -> List[Dict[str, Any]]:
        """List all active connections"""
        response = self.session.get(f"{self.base_url}/api/remote/connections")
        response.raise_for_status()
        return response.json()["connections"]
    
    def disconnect(self, connection_id: str, cleanup_viewer: bool = True) -> Dict[str, Any]:
        """Disconnect connection"""
        response = self.session.delete(
            f"{self.base_url}/api/remote/connections/{connection_id}",
            params={"cleanup_viewer": cleanup_viewer}
        )
        response.raise_for_status()
        return response.json()
    
    def list_environments(
        self,
        connection_id: str,
        filter_type: str = "all"
    ) -> List[Dict[str, Any]]:
        """List Python environments"""
        response = self.session.get(
            f"{self.base_url}/api/remote/environments",
            params={
                "connection_id": connection_id,
                "filter": filter_type
            }
        )
        response.raise_for_status()
        return response.json()["environments"]
    
    def detect_environments(
        self,
        connection_id: str,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Re-detect environments"""
        response = self.session.post(
            f"{self.base_url}/api/remote/environments/detect",
            json={
                "connection_id": connection_id,
                "force_refresh": force_refresh
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_remote_config(self, connection_id: str, env_name: str) -> Dict[str, Any]:
        """Get remote configuration"""
        response = self.session.get(
            f"{self.base_url}/api/remote/config",
            params={
                "connection_id": connection_id,
                "env_name": env_name
            }
        )
        response.raise_for_status()
        return response.json()
    
    def start_viewer(
        self,
        connection_id: str,
        env_name: str,
        remote_root: Optional[str] = None,
        auto_open: bool = True
    ) -> Dict[str, Any]:
        """Start Remote Viewer"""
        payload = {
            "connection_id": connection_id,
            "env_name": env_name,
            "auto_open": auto_open
        }
        
        if remote_root:
            payload["remote_root"] = remote_root
        
        response = self.session.post(
            f"{self.base_url}/api/remote/viewer/start",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def stop_viewer(self, connection_id: str, cleanup: bool = True) -> Dict[str, Any]:
        """Stop Remote Viewer"""
        response = self.session.post(
            f"{self.base_url}/api/remote/viewer/stop",
            json={
                "connection_id": connection_id,
                "cleanup": cleanup
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_viewer_status(self, connection_id: str) -> Dict[str, Any]:
        """Get Viewer status"""
        response = self.session.get(
            f"{self.base_url}/api/remote/viewer/status",
            params={"connection_id": connection_id}
        )
        response.raise_for_status()
        return response.json()
    
    def get_viewer_logs(
        self,
        connection_id: str,
        lines: int = 100
    ) -> List[str]:
        """Get Viewer logs"""
        response = self.session.get(
            f"{self.base_url}/api/remote/viewer/logs",
            params={
                "connection_id": connection_id,
                "lines": lines
            }
        )
        response.raise_for_status()
        return response.json()["logs"]
    
    def health_check(self, connection_id: str) -> Dict[str, Any]:
        """Health check"""
        response = self.session.get(
            f"{self.base_url}/api/remote/health",
            params={"connection_id": connection_id}
        )
        response.raise_for_status()
        return response.json()
    
    def ping(self, connection_id: str) -> Dict[str, Any]:
        """Test connection latency"""
        response = self.session.get(
            f"{self.base_url}/api/remote/ping",
            params={"connection_id": connection_id}
        )
        response.raise_for_status()
        return response.json()
    
    def close(self):
        """Close session"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

### Basic Usage Example

```python
from runicorn_remote_client import RunicornRemoteClient

# Create client
with RunicornRemoteClient() as client:
    # 1. Connect to remote server
    result = client.connect(
        host="gpu-server.com",
        username="mluser",
        auth_method="key",
        private_key_path="~/.ssh/id_rsa"
    )
    
    connection_id = result["connection_id"]
    print(f"✓ Connected: {connection_id}")
    
    # 2. List Python environments
    environments = client.list_environments(
        connection_id=connection_id,
        filter_type="runicorn_only"
    )
    
    print(f"✓ Found {len(environments)} environments")
    for env in environments:
        print(f"  - {env['name']}: Python {env['python_version']}, Runicorn {env['runicorn_version']}")
    
    # 3. Start Remote Viewer
    viewer = client.start_viewer(
        connection_id=connection_id,
        env_name=environments[0]["name"],
        auto_open=True
    )
    
    print(f"✓ Viewer started: {viewer['viewer']['url']}")
    
    # 4. Monitor status
    status = client.get_viewer_status(connection_id)
    print(f"✓ Viewer status: {status['viewer']['status']}")
    
    # 5. Health check
    health = client.health_check(connection_id)
    print(f"✓ Connection health: {health['health']}")
    
    # 6. Cleanup when done
    input("Press Enter to disconnect...")
    client.disconnect(connection_id)
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
      authMethod = 'key',
      port = 22,
      privateKeyPath,
      password,
      keyPassphrase,
      timeout
    } = options;

    const payload = {
      host,
      port,
      username,
      auth_method: authMethod,
    };

    // Add authentication info
    if (authMethod === 'key') {
      if (privateKeyPath) payload.private_key_path = privateKeyPath;
      if (keyPassphrase) payload.key_passphrase = keyPassphrase;
    } else if (authMethod === 'password') {
      if (!password) throw new Error('Password required');
      payload.password = password;
    }

    if (timeout) payload.timeout = timeout;

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
   * List all active connections
   */
  async listConnections() {
    const response = await fetch(`${this.baseUrl}/api/remote/connections`);
    
    if (!response.ok) {
      throw new Error(`Failed to list connections: ${response.statusText}`);
    }

    const data = await response.json();
    return data.connections;
  }

  /**
   * Disconnect connection
   */
  async disconnect(connectionId, cleanupViewer = true) {
    const response = await fetch(
      `${this.baseUrl}/api/remote/connections/${connectionId}?cleanup_viewer=${cleanupViewer}`,
      { method: 'DELETE' }
    );

    if (!response.ok) {
      throw new Error(`Disconnect failed: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * List Python environments
   */
  async listEnvironments(connectionId, filterType = 'all') {
    const response = await fetch(
      `${this.baseUrl}/api/remote/environments?connection_id=${connectionId}&filter=${filterType}`
    );

    if (!response.ok) {
      throw new Error(`Failed to list environments: ${response.statusText}`);
    }

    const data = await response.json();
    return data.environments;
  }

  /**
   * Re-detect environments
   */
  async detectEnvironments(connectionId, forceRefresh = false) {
    const response = await fetch(`${this.baseUrl}/api/remote/environments/detect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        connection_id: connectionId,
        force_refresh: forceRefresh,
      }),
    });

    if (!response.ok) {
      throw new Error(`Detection failed: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Start Remote Viewer
   */
  async startViewer(connectionId, envName, options = {}) {
    const { remoteRoot, autoOpen = true } = options;

    const payload = {
      connection_id: connectionId,
      env_name: envName,
      auto_open: autoOpen,
    };

    if (remoteRoot) payload.remote_root = remoteRoot;

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
  async stopViewer(connectionId, cleanup = true) {
    const response = await fetch(`${this.baseUrl}/api/remote/viewer/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        connection_id: connectionId,
        cleanup,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to stop viewer: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get Viewer status
   */
  async getViewerStatus(connectionId) {
    const response = await fetch(
      `${this.baseUrl}/api/remote/viewer/status?connection_id=${connectionId}`
    );

    if (!response.ok) {
      throw new Error(`Failed to get status: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get Viewer logs
   */
  async getViewerLogs(connectionId, lines = 100) {
    const response = await fetch(
      `${this.baseUrl}/api/remote/viewer/logs?connection_id=${connectionId}&lines=${lines}`
    );

    if (!response.ok) {
      throw new Error(`Failed to get logs: ${response.statusText}`);
    }

    const data = await response.json();
    return data.logs;
  }

  /**
   * Health check
   */
  async healthCheck(connectionId) {
    const response = await fetch(
      `${this.baseUrl}/api/remote/health?connection_id=${connectionId}`
    );

    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Test connection latency
   */
  async ping(connectionId) {
    const response = await fetch(
      `${this.baseUrl}/api/remote/ping?connection_id=${connectionId}`
    );

    if (!response.ok) {
      throw new Error(`Ping failed: ${response.statusText}`);
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
      authMethod: 'key',
      privateKeyPath: '~/.ssh/id_rsa',
    });

    console.log(`✓ Connected: ${connection_id}`);

    // 2. List environments
    const environments = await client.listEnvironments(connection_id, 'runicorn_only');
    
    console.log(`✓ Found ${environments.length} environments`);
    environments.forEach(env => {
      console.log(`  - ${env.name}: Python ${env.python_version}, Runicorn ${env.runicorn_version}`);
    });

    // 3. Start Viewer
    const viewer = await client.startViewer(
      connection_id,
      environments[0].name,
      { autoOpen: true }
    );

    console.log(`✓ Viewer started: ${viewer.viewer.url}`);

    // 4. Monitor status
    const status = await client.getViewerStatus(connection_id);
    console.log(`✓ Viewer status: ${status.viewer.status}`);

    // 5. Health check
    const health = await client.healthCheck(connection_id);
    console.log(`✓ Connection health: ${health.health}`);

    // 6. Cleanup when done
    // await client.disconnect(connection_id);
    // console.log('✓ Disconnected');

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
        result = client.connect(
            host=host,
            username=username,
            auth_method="key",
            private_key_path=key_path
        )
        conn_id = result["connection_id"]
        
        # Start Viewer
        viewer = client.start_viewer(
            connection_id=conn_id,
            env_name=env_name,
            auto_open=False  # Don't auto-open browser
        )
        
        print(f"Viewer URL: {viewer['viewer']['url']}")
        
        # Monitoring loop
        while True:
            status = client.get_viewer_status(conn_id)
            health = client.health_check(conn_id)
            
            if health["health"] != "healthy":
                print(f"Warning: Connection unhealthy - {health}")
                break
            
            print(f"Status: {status['viewer']['status']}, Uptime: {status['viewer']['uptime_seconds']}s")
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
        
        # List all connections
        all_connections = client.list_connections()
        print(f"\nTotal {len(all_connections)} active connections:")
        
        for conn in all_connections:
            print(f"  - {conn['host']}: {conn['status']}")
            if conn.get('viewer'):
                print(f"    Viewer: {conn['viewer']['url']}")
        
        # Interactive management
        while True:
            print("\nOptions: (l)ist, (h)ealth, (q)uit")
            choice = input("> ").lower()
            
            if choice == 'l':
                for conn in client.list_connections():
                    print(f"{conn['connection_id']}: {conn['host']} - {conn['status']}")
            
            elif choice == 'h':
                for conn_id in connections:
                    health = client.health_check(conn_id)
                    print(f"{conn_id}: {health['health']}")
            
            elif choice == 'q':
                break
    
    finally:
        # Cleanup all connections
        for conn_id in connections:
            try:
                client.disconnect(conn_id)
                print(f"✓ Disconnected: {conn_id}")
            except Exception as e:
                print(f"✗ Failed to disconnect: {conn_id} - {e}")
        
        client.close()

# Usage
servers = [
    {
        "host": "gpu-server-01.com",
        "username": "mluser",
        "auth_method": "key",
        "private_key_path": "~/.ssh/id_rsa"
    },
    {
        "host": "gpu-server-02.com",
        "username": "mluser",
        "auth_method": "key",
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
        result = client.connect(
            host=host,
            username=username,
            auth_method="key",
            private_key_path=key_path
        )
        conn_id = result["connection_id"]
        
        # Get all environments
        envs = client.list_environments(conn_id, filter_type="runicorn_only")
        
        if not envs:
            print("Error: No environments with Runicorn found")
            return None
        
        # Select latest Runicorn version
        best_env = max(envs, key=lambda e: e["runicorn_version"])
        
        print(f"Selected environment: {best_env['name']}")
        print(f"  Python: {best_env['python_version']}")
        print(f"  Runicorn: {best_env['runicorn_version']}")
        print(f"  Storage: {best_env['storage_root']}")
        
        # Start Viewer
        viewer = client.start_viewer(
            connection_id=conn_id,
            env_name=best_env["name"]
        )
        
        return viewer["viewer"]["url"]

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
        result = client.connect(
            host="gpu-server.com",
            username="mluser",
            auth_method="key",
            private_key_path="~/.ssh/id_rsa",
            timeout=30
        )
        conn_id = result["connection_id"]
        
    except requests.exceptions.Timeout:
        print("Error: Connection timeout, check if server is reachable")
        return
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("Error: SSH authentication failed, check key")
        elif e.response.status_code == 503:
            print("Error: SSH service unavailable")
        else:
            print(f"Error: HTTP {e.response.status_code} - {e}")
        return
    
    except Exception as e:
        print(f"Error: Connection failed - {e}")
        return
    
    try:
        # Get environments
        envs = client.list_environments(conn_id, "runicorn_only")
        
        if not envs:
            print("Error: No environments with Runicorn found")
            print("Hint: Run 'pip install runicorn' on remote server")
            return
        
        # Start Viewer
        viewer = client.start_viewer(
            connection_id=conn_id,
            env_name=envs[0]["name"]
        )
        
        print(f"✓ Success: {viewer['viewer']['url']}")
        
    except requests.exceptions.HTTPError as e:
        error_data = e.response.json()
        
        if error_data.get("error") == "environment_not_found":
            print(f"Error: Environment not found - {error_data['message']}")
        elif error_data.get("error") == "viewer_already_running":
            print("Warning: Viewer already running")
        else:
            print(f"Error: {error_data.get('message', str(e))}")
    
    except Exception as e:
        print(f"Error: Start failed - {e}")
    
    finally:
        # Ensure cleanup
        if conn_id:
            try:
                client.disconnect(conn_id)
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
    auth_method="key",
    private_key_path="~/.ssh/id_rsa",
    timeout=60  # Increase timeout
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
    auth_method="key",
    private_key_path=key_path
)
```

### 4. Regular Health Checks

```python
import time

def keep_alive(client, conn_id, interval=30):
    """Periodically ping to keep connection alive"""
    while True:
        try:
            result = client.ping(conn_id)
            print(f"Ping: {result['latency_ms']}ms")
            time.sleep(interval)
        except Exception as e:
            print(f"Connection lost: {e}")
            break
```

### 5. Logging

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
**Version**: v0.5.0  
**Last Updated**: 2025-10-25

**[Back to API Docs](README.md)** | **[View API Reference](remote_api.md)**
