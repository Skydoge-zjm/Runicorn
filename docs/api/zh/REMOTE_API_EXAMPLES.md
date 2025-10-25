# Remote Viewer API 代码示例

> **版本**: v0.5.0  
> **最后更新**: 2025-10-25

[English](../en/REMOTE_API_EXAMPLES.md) | [简体中文](REMOTE_API_EXAMPLES.md)

---

## 📖 目录

- [Python 客户端](#python-客户端)
- [JavaScript 客户端](#javascript-客户端)
- [实际使用场景](#实际使用场景)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)

---

## Python 客户端

### 完整的 Python 客户端类

```python
import requests
from typing import Optional, Dict, List, Any

class RunicornRemoteClient:
    """Runicorn Remote Viewer API 客户端"""
    
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
        连接到远程服务器
        
        Args:
            host: 远程服务器地址
            username: SSH 用户名
            auth_method: 认证方式 ("key", "password", "agent")
            port: SSH 端口
            **kwargs: 额外参数
                private_key_path: 私钥路径 (auth_method="key")
                password: 密码 (auth_method="password")
                key_passphrase: 私钥密码
                timeout: 连接超时
        
        Returns:
            包含 connection_id 的响应字典
        """
        payload = {
            "host": host,
            "port": port,
            "username": username,
            "auth_method": auth_method,
        }
        
        # 添加认证信息
        if auth_method == "key":
            if "private_key_path" in kwargs:
                payload["private_key_path"] = kwargs["private_key_path"]
            if "key_passphrase" in kwargs:
                payload["key_passphrase"] = kwargs["key_passphrase"]
        elif auth_method == "password":
            if "password" not in kwargs:
                raise ValueError("Password required for password authentication")
            payload["password"] = kwargs["password"]
        
        # 可选参数
        if "timeout" in kwargs:
            payload["timeout"] = kwargs["timeout"]
        
        response = self.session.post(
            f"{self.base_url}/api/remote/connect",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def list_connections(self) -> List[Dict[str, Any]]:
        """列出所有活动连接"""
        response = self.session.get(f"{self.base_url}/api/remote/connections")
        response.raise_for_status()
        return response.json()["connections"]
    
    def disconnect(self, connection_id: str, cleanup_viewer: bool = True) -> Dict[str, Any]:
        """断开连接"""
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
        """列出 Python 环境"""
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
        """重新检测环境"""
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
        """获取远程配置"""
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
        """启动 Remote Viewer"""
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
        """停止 Remote Viewer"""
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
        """获取 Viewer 状态"""
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
        """获取 Viewer 日志"""
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
        """健康检查"""
        response = self.session.get(
            f"{self.base_url}/api/remote/health",
            params={"connection_id": connection_id}
        )
        response.raise_for_status()
        return response.json()
    
    def ping(self, connection_id: str) -> Dict[str, Any]:
        """测试连接延迟"""
        response = self.session.get(
            f"{self.base_url}/api/remote/ping",
            params={"connection_id": connection_id}
        )
        response.raise_for_status()
        return response.json()
    
    def close(self):
        """关闭会话"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

### 基础使用示例

```python
from runicorn_remote_client import RunicornRemoteClient

# 创建客户端
with RunicornRemoteClient() as client:
    # 1. 连接到远程服务器
    result = client.connect(
        host="gpu-server.com",
        username="mluser",
        auth_method="key",
        private_key_path="~/.ssh/id_rsa"
    )
    
    connection_id = result["connection_id"]
    print(f"✓ 已连接: {connection_id}")
    
    # 2. 列出 Python 环境
    environments = client.list_environments(
        connection_id=connection_id,
        filter_type="runicorn_only"
    )
    
    print(f"✓ 找到 {len(environments)} 个环境")
    for env in environments:
        print(f"  - {env['name']}: Python {env['python_version']}, Runicorn {env['runicorn_version']}")
    
    # 3. 启动 Remote Viewer
    viewer = client.start_viewer(
        connection_id=connection_id,
        env_name=environments[0]["name"],
        auto_open=True
    )
    
    print(f"✓ Viewer 已启动: {viewer['viewer']['url']}")
    
    # 4. 监控状态
    status = client.get_viewer_status(connection_id)
    print(f"✓ Viewer 状态: {status['viewer']['status']}")
    
    # 5. 健康检查
    health = client.health_check(connection_id)
    print(f"✓ 连接健康: {health['health']}")
    
    # 6. 完成后清理
    input("按 Enter 键断开连接...")
    client.disconnect(connection_id)
    print("✓ 已断开连接")
```

---

## JavaScript 客户端

### 完整的 JavaScript/TypeScript 客户端类

```javascript
class RunicornRemoteClient {
  /**
   * Runicorn Remote Viewer API 客户端
   * @param {string} baseUrl - API 基础 URL
   */
  constructor(baseUrl = 'http://localhost:23300') {
    this.baseUrl = baseUrl;
  }

  /**
   * 连接到远程服务器
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

    // 添加认证信息
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
   * 列出所有活动连接
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
   * 断开连接
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
   * 列出 Python 环境
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
   * 重新检测环境
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
   * 启动 Remote Viewer
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
   * 停止 Remote Viewer
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
   * 获取 Viewer 状态
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
   * 获取 Viewer 日志
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
   * 健康检查
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
   * 测试连接延迟
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

// 导出
export default RunicornRemoteClient;
```

### JavaScript 使用示例

```javascript
// 创建客户端
const client = new RunicornRemoteClient();

(async () => {
  try {
    // 1. 连接到远程服务器
    const { connection_id } = await client.connect({
      host: 'gpu-server.com',
      username: 'mluser',
      authMethod: 'key',
      privateKeyPath: '~/.ssh/id_rsa',
    });

    console.log(`✓ 已连接: ${connection_id}`);

    // 2. 列出环境
    const environments = await client.listEnvironments(connection_id, 'runicorn_only');
    
    console.log(`✓ 找到 ${environments.length} 个环境`);
    environments.forEach(env => {
      console.log(`  - ${env.name}: Python ${env.python_version}, Runicorn ${env.runicorn_version}`);
    });

    // 3. 启动 Viewer
    const viewer = await client.startViewer(
      connection_id,
      environments[0].name,
      { autoOpen: true }
    );

    console.log(`✓ Viewer 已启动: ${viewer.viewer.url}`);

    // 4. 监控状态
    const status = await client.getViewerStatus(connection_id);
    console.log(`✓ Viewer 状态: ${status.viewer.status}`);

    // 5. 健康检查
    const health = await client.healthCheck(connection_id);
    console.log(`✓ 连接健康: ${health.health}`);

    // 6. 完成后清理
    // await client.disconnect(connection_id);
    // console.log('✓ 已断开连接');

  } catch (error) {
    console.error('错误:', error.message);
  }
})();
```

---

## 实际使用场景

### 场景 1: 自动化训练监控

```python
import time
from runicorn_remote_client import RunicornRemoteClient

def monitor_training(host, username, key_path, env_name):
    """自动连接并监控远程训练"""
    
    with RunicornRemoteClient() as client:
        # 连接
        result = client.connect(
            host=host,
            username=username,
            auth_method="key",
            private_key_path=key_path
        )
        conn_id = result["connection_id"]
        
        # 启动 Viewer
        viewer = client.start_viewer(
            connection_id=conn_id,
            env_name=env_name,
            auto_open=False  # 不自动打开浏览器
        )
        
        print(f"Viewer URL: {viewer['viewer']['url']}")
        
        # 监控循环
        while True:
            status = client.get_viewer_status(conn_id)
            health = client.health_check(conn_id)
            
            if health["health"] != "healthy":
                print(f"警告: 连接不健康 - {health}")
                break
            
            print(f"状态: {status['viewer']['status']}, 运行时间: {status['viewer']['uptime_seconds']}s")
            time.sleep(30)  # 每30秒检查一次

# 使用
monitor_training(
    host="gpu-server.com",
    username="mluser",
    key_path="~/.ssh/id_rsa",
    env_name="pytorch-env"
)
```

### 场景 2: 多服务器管理

```python
from runicorn_remote_client import RunicornRemoteClient

def manage_multiple_servers(servers):
    """连接并管理多个服务器"""
    
    client = RunicornRemoteClient()
    connections = []
    
    try:
        # 连接所有服务器
        for server in servers:
            result = client.connect(**server)
            conn_id = result["connection_id"]
            connections.append(conn_id)
            
            print(f"✓ 已连接到 {server['host']}: {conn_id}")
        
        # 列出所有连接
        all_connections = client.list_connections()
        print(f"\n总计 {len(all_connections)} 个活动连接:")
        
        for conn in all_connections:
            print(f"  - {conn['host']}: {conn['status']}")
            if conn.get('viewer'):
                print(f"    Viewer: {conn['viewer']['url']}")
        
        # 交互式管理
        while True:
            print("\n选项: (l)ist, (h)ealth, (q)uit")
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
        # 清理所有连接
        for conn_id in connections:
            try:
                client.disconnect(conn_id)
                print(f"✓ 已断开: {conn_id}")
            except Exception as e:
                print(f"✗ 断开失败: {conn_id} - {e}")
        
        client.close()

# 使用
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

### 场景 3: 环境检测和选择

```python
from runicorn_remote_client import RunicornRemoteClient

def select_best_environment(host, username, key_path):
    """自动选择最佳环境"""
    
    with RunicornRemoteClient() as client:
        # 连接
        result = client.connect(
            host=host,
            username=username,
            auth_method="key",
            private_key_path=key_path
        )
        conn_id = result["connection_id"]
        
        # 获取所有环境
        envs = client.list_environments(conn_id, filter_type="runicorn_only")
        
        if not envs:
            print("错误: 未找到安装 Runicorn 的环境")
            return None
        
        # 选择最新版本的 Runicorn
        best_env = max(envs, key=lambda e: e["runicorn_version"])
        
        print(f"选择环境: {best_env['name']}")
        print(f"  Python: {best_env['python_version']}")
        print(f"  Runicorn: {best_env['runicorn_version']}")
        print(f"  存储: {best_env['storage_root']}")
        
        # 启动 Viewer
        viewer = client.start_viewer(
            connection_id=conn_id,
            env_name=best_env["name"]
        )
        
        return viewer["viewer"]["url"]

# 使用
url = select_best_environment(
    host="gpu-server.com",
    username="mluser",
    key_path="~/.ssh/id_rsa"
)

if url:
    print(f"\n✓ Viewer 可用: {url}")
```

---

## 错误处理

### Python 错误处理示例

```python
from runicorn_remote_client import RunicornRemoteClient
import requests

def safe_connect_and_start():
    """带完整错误处理的连接"""
    
    client = RunicornRemoteClient()
    conn_id = None
    
    try:
        # 连接
        result = client.connect(
            host="gpu-server.com",
            username="mluser",
            auth_method="key",
            private_key_path="~/.ssh/id_rsa",
            timeout=30
        )
        conn_id = result["connection_id"]
        
    except requests.exceptions.Timeout:
        print("错误: 连接超时，请检查服务器是否可达")
        return
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("错误: SSH 认证失败，请检查密钥")
        elif e.response.status_code == 503:
            print("错误: SSH 服务不可用")
        else:
            print(f"错误: HTTP {e.response.status_code} - {e}")
        return
    
    except Exception as e:
        print(f"错误: 连接失败 - {e}")
        return
    
    try:
        # 获取环境
        envs = client.list_environments(conn_id, "runicorn_only")
        
        if not envs:
            print("错误: 未找到安装 Runicorn 的环境")
            print("提示: 在远程服务器上运行 'pip install runicorn'")
            return
        
        # 启动 Viewer
        viewer = client.start_viewer(
            connection_id=conn_id,
            env_name=envs[0]["name"]
        )
        
        print(f"✓ 成功: {viewer['viewer']['url']}")
        
    except requests.exceptions.HTTPError as e:
        error_data = e.response.json()
        
        if error_data.get("error") == "environment_not_found":
            print(f"错误: 环境不存在 - {error_data['message']}")
        elif error_data.get("error") == "viewer_already_running":
            print("警告: Viewer 已在运行")
        else:
            print(f"错误: {error_data.get('message', str(e))}")
    
    except Exception as e:
        print(f"错误: 启动失败 - {e}")
    
    finally:
        # 确保清理
        if conn_id:
            try:
                client.disconnect(conn_id)
            except:
                pass
        
        client.close()

safe_connect_and_start()
```

---

## 最佳实践

### 1. 使用上下文管理器

```python
# ✅ 推荐
with RunicornRemoteClient() as client:
    # ... 使用客户端
    pass  # 自动清理

# ❌ 不推荐
client = RunicornRemoteClient()
# ... 使用
client.close()  # 容易忘记
```

### 2. 设置合适的超时

```python
# 对于不稳定的网络
result = client.connect(
    host="remote-server.com",
    username="user",
    auth_method="key",
    private_key_path="~/.ssh/id_rsa",
    timeout=60  # 增加超时时间
)
```

### 3. 使用环境变量管理凭据

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

### 4. 定期健康检查

```python
import time

def keep_alive(client, conn_id, interval=30):
    """定期 ping 保持连接活跃"""
    while True:
        try:
            result = client.ping(conn_id)
            print(f"Ping: {result['latency_ms']}ms")
            time.sleep(interval)
        except Exception as e:
            print(f"连接丢失: {e}")
            break
```

### 5. 日志记录

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

**作者**: Runicorn Development Team  
**版本**: v0.5.0  
**最后更新**: 2025-10-25

**[返回 API 文档](README.md)** | **[查看 API 参考](remote_api.md)**
