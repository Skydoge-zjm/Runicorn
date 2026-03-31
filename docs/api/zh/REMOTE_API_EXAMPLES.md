# Remote Viewer API 代码示例

> **版本**: v0.7.0
> **最后更新**: 2026-03-28

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
        建立 SSH 连接

        Args:
            host: 远程服务器地址
            username: SSH 用户名
            port: SSH 端口
            password: SSH 密码（可选）
            private_key: 私钥内容（可选）
            private_key_path: 私钥路径（可选）
            passphrase: 私钥密码（可选）
            use_agent: 使用 SSH Agent（默认: True）

        Returns:
            包含 connection_id 的响应字典
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
    result = client.connect(host="gpu-server.com", username="mluser", private_key_path="~/.ssh/id_rsa")

    connection_id = result["connection_id"]
    print(f"✓ 已连接: {connection_id}")

    # 2. （可选）列出 Python 环境
    envs = client.list_conda_envs(connection_id=connection_id)
    print(f"✓ 找到 {len(envs)} 个环境")

    # 3. 启动 Remote Viewer
    viewer = client.start_viewer(host="gpu-server.com", username="mluser", remote_root="/data/experiments")
    session_id = viewer["session"]["sessionId"]
    print(f"✓ Viewer 已启动: {viewer['session']['url']}")

    # 4. 监控状态
    status = client.get_viewer_session(session_id=session_id)
    print(f"✓ Viewer 状态: {status['status']}")

    # 5. 完成后清理
    input("按 Enter 键断开连接...")
    client.stop_viewer(session_id=session_id)
    client.disconnect(host="gpu-server.com", port=22, username="mluser")
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
   * 列出所有活动 SSH 会话
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
   * 断开 SSH 会话
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
   * 列出 Python 环境
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
   * 启动 Remote Viewer
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
   * 停止 Remote Viewer
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
   * 获取 Viewer 会话状态
   */
  async getViewerSession(sessionId) {
    const response = await fetch(`${this.baseUrl}/api/remote/viewer/status/${sessionId}`);

    if (!response.ok) {
      throw new Error(`Failed to get status: ${response.statusText}`);
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
      privateKeyPath: '~/.ssh/id_rsa',
      useAgent: true,
    });

    console.log(`✓ 已连接: ${connection_id}`);

    // 2. 列出环境
    const envs = await client.listCondaEnvs(connection_id);

    console.log(`✓ 找到 ${envs.length} 个环境`);
    envs.forEach(env => {
      console.log(`  - ${env.name}: Python ${env.python_version} (${env.type})`);
    });

    // 3. 启动 Viewer
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
    console.log(`✓ Viewer 已启动: ${viewer.session.url}`);

    // 4. 监控状态
    const status = await client.getViewerSession(sessionId);
    console.log(`✓ Viewer 状态: ${status.status}`);

    // 5. 完成后清理
    await client.stopViewer(sessionId);
    await client.disconnect({ host: 'gpu-server.com', port: 22, username: 'mluser' });
    console.log('✓ 已断开连接');

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

        # 监控循环
        while True:
            status = client.get_viewer_session(session_id=session_id)
            print(f"状态: {status['status']}, 运行时间: {status['uptimeSeconds']}s")
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

        # 列出所有会话
        all_sessions = client.list_sessions()
        print(f"\n总计 {len(all_sessions)} 个活动会话:")

        for sess in all_sessions:
            print(f"  - {sess['key']}: connected={sess['connected']}")

        # 交互式管理
        while True:
            print("\n选项: (l)ist, (q)uit")
            choice = input("> ").lower()

            if choice == 'l':
                for sess in client.list_sessions():
                    print(f"{sess['key']}: connected={sess['connected']}")

            elif choice == 'q':
                break

    finally:
        # 清理所有连接
        for server in servers:
            try:
                client.disconnect(host=server["host"], port=server.get("port", 22), username=server["username"])
                print(f"✓ 已断开: {server['host']}")
            except Exception as e:
                print(f"✗ 断开失败: {server['host']} - {e}")

        client.close()

# 使用
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

### 场景 3: 环境检测和选择

```python
from runicorn_remote_client import RunicornRemoteClient

def select_best_environment(host, username, key_path):
    """自动选择最佳环境"""

    with RunicornRemoteClient() as client:
        # 连接
        result = client.connect(host=host, username=username, private_key_path=key_path)
        conn_id = result["connection_id"]

        envs = client.list_conda_envs(connection_id=conn_id)

        if not envs:
            print("错误: 未找到安装 Runicorn 的环境")
            return None

        best_env = next((e for e in envs if e.get("is_default")), envs[0])

        print(f"选择环境: {best_env['name']}")
        print(f"  Python: {best_env['python_version']}")
        print(f"  Type: {best_env['type']}")

        # 启动 Viewer
        viewer = client.start_viewer(
            host=host,
            username=username,
            remote_root="~/runicorn_data",
            private_key_path=key_path,
            conda_env=best_env["name"],
        )

        return viewer["session"]["url"]

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
        result = client.connect(host="gpu-server.com", username="mluser", private_key_path="~/.ssh/id_rsa")
        conn_id = result["connection_id"]

    except requests.exceptions.Timeout:
        print("错误: 连接超时，请检查服务器是否可达")
        return

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 409:
            print("错误: 需要确认 host key")
        elif e.response.status_code == 503:
            print("错误: SSH 服务不可用")
        else:
            print(f"错误: HTTP {e.response.status_code} - {e}")
        return

    except Exception as e:
        print(f"错误: 连接失败 - {e}")
        return

    try:
        viewer = client.start_viewer(
            host="gpu-server.com",
            username="mluser",
            remote_root="~/runicorn_data",
            private_key_path="~/.ssh/id_rsa",
            conda_env=None,
        )
        print(f"✓ 成功: {viewer['session']['url']}")

    except requests.exceptions.HTTPError as e:
        error_data = e.response.json()

        print(f"错误: {error_data.get('detail', str(e))}")

    except Exception as e:
        print(f"错误: 启动失败 - {e}")

    finally:
        # 确保清理
        if conn_id:
            try:
                client.disconnect(host="gpu-server.com", port=22, username="mluser")
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
    private_key_path="~/.ssh/id_rsa",
    port=22,
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
    private_key_path=key_path
)
```

### 4. 日志记录

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
**版本**: v0.7.0
**最后更新**: 2026-03-28

**[返回 API 文档](README.md)** | **[查看 API 参考](remote_api.md)**
