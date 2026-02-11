[English](../en/python_client_api.md) | [简体中文](python_client_api.md)

---

# Python API Client - 程序化访问

**模块**: Python API Client  
**包**: `runicorn.api`  
**版本**: v1.0  
**描述**: 通过 Python 代码程序化访问 Runicorn Viewer REST API。

---

## 目录

1. [概述](#概述)
2. [安装](#安装)
3. [快速开始](#快速开始)
4. [核心类](#核心类)
5. [API 方法](#api-方法)
6. [扩展 API](#扩展-api)
7. [错误处理](#错误处理)
8. [最佳实践](#最佳实践)
9. [完整示例](#完整示例)

---

## 概述

Python API Client 提供了对 Runicorn Viewer REST API 的简洁封装，使您可以通过 Python 代码进行以下操作：

- 📊 查询和分析实验数据
- 🔌 控制远程 Viewer 会话
- 📤 导出数据为各种格式
- 🐼 集成 pandas DataFrame

### 主要特性

- ✅ **类型安全**: 完整的类型提示支持
- ✅ **自动重试**: 内置请求重试机制
- ✅ **上下文管理**: 支持 `with` 语句自动清理
- ✅ **DataFrame 集成**: 内置 pandas 转换工具
- ✅ **模块化设计**: Remote API 独立扩展

---

## 安装

Python API Client 包含在 Runicorn 主包中：

```bash
# 安装 Runicorn（包含 API Client）
pip install runicorn

# 或从源码安装
pip install -e .
```

### 依赖项

**必需依赖**：
- `requests` >= 2.25.0
- `urllib3` >= 1.26.0

**可选依赖**：
- `pandas` >= 1.2.0（用于 DataFrame 工具）

```bash
# 安装可选依赖
pip install "runicorn[pandas]"
```

---

## 快速开始

### 基本使用

```python
import runicorn.api as api

# 连接到 Viewer
client = api.connect("http://127.0.0.1:23300")

# 列出实验
experiments = client.list_experiments(project="vision")
print(f"Found {len(experiments)} experiments")

# 获取指标
for exp in experiments[:3]:
    metrics = client.get_metrics(exp["id"])
    print(f"{exp['name']}: {list(metrics['metrics'].keys())}")

# 关闭连接
client.close()
```

### 使用上下文管理器

```python
import runicorn.api as api

# 自动管理连接生命周期
with api.connect() as client:
    experiments = client.list_experiments()
    # ... 使用 client
# 自动调用 client.close()
```

---

## 核心类

### RunicornClient

主客户端类，提供对 Viewer API 的访问。

#### 构造函数

```python
RunicornClient(
    base_url: str = "http://127.0.0.1:23300",
    timeout: int = 30,
    max_retries: int = 3
)
```

**参数**：
- `base_url` (str): Viewer 基础 URL
- `timeout` (int): 请求超时（秒）
- `max_retries` (int): 最大重试次数

**示例**：
```python
from runicorn.api import RunicornClient

# 使用自定义配置
client = RunicornClient(
    base_url="http://localhost:8080",
    timeout=60,
    max_retries=5
)
```

#### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `base_url` | `str` | Viewer 基础 URL |
| `timeout` | `int` | 请求超时时间 |
| `session` | `requests.Session` | HTTP 会话对象 |
| `remote` | `RemoteAPI` | Remote API 扩展 |

---

## API 方法

### 实验管理

#### list_experiments()

列出所有实验。

```python
client.list_experiments(
    project: Optional[str] = None,
    name: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> List[Dict[str, Any]]
```

**参数**：
- `project`: 过滤项目名
- `name`: 过滤实验名
- `status`: 过滤状态（`running`, `finished`, `failed`）
- `limit`: 最大结果数
- `offset`: 分页偏移量

**返回值**: 实验记录列表

**示例**：
```python
# 列出所有实验
all_experiments = client.list_experiments()

# 过滤条件
vision_exps = client.list_experiments(project="vision")
running_exps = client.list_experiments(status="running")

# 分页
page1 = client.list_experiments(limit=10, offset=0)
page2 = client.list_experiments(limit=10, offset=10)
```

---

#### get_experiment()

获取实验详情。

```python
client.get_experiment(run_id: str) -> Dict[str, Any]
```

**参数**：
- `run_id`: 运行 ID

**返回值**: 实验详细信息

**示例**：
```python
run = client.get_experiment("20250124_120000_abc123")

print(f"项目: {run['project']}")
print(f"名称: {run['name']}")
print(f"状态: {run['status']}")
print(f"创建时间: {run['created_at']}")
```

**别名**: `get_run()`

---

#### list_projects()

列出所有项目。

```python
client.list_projects() -> List[Dict[str, Any]]
```

**返回值**: 项目列表，包含实验计数

**示例**：
```python
projects = client.list_projects()

for proj in projects:
    print(f"{proj['name']}: {proj['experiment_count']} experiments")
```

---

### 指标数据

#### get_metrics()

获取运行的指标数据。

```python
client.get_metrics(
    run_id: str,
    metric_names: Optional[List[str]] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]
```

**参数**：
- `run_id`: 运行 ID
- `metric_names`: 指定指标名称列表
- `limit`: 数据点数量限制

**返回值**: 指标数据字典

**示例**：
```python
# 获取所有指标
metrics = client.get_metrics("20250124_120000_abc123")

# 获取特定指标
metrics = client.get_metrics(
    "20250124_120000_abc123",
    metric_names=["loss", "accuracy"]
)

# 处理指标数据
for metric_name, points in metrics["metrics"].items():
    values = [p["value"] for p in points]
    print(f"{metric_name}: min={min(values)}, max={max(values)}")
```

---

### 配置管理

#### get_config()

获取 Viewer 配置。

```python
client.get_config() -> Dict[str, Any]
```

**返回值**: 配置信息

**示例**：
```python
config = client.get_config()

print(f"存储根目录: {config['user_root']}")
print(f"端口: {config.get('port', 23300)}")
```

---

#### update_config()

更新 Viewer 配置。

```python
client.update_config(config: Dict[str, Any]) -> Dict[str, Any]
```

**参数**：
- `config`: 配置字典

**示例**：
```python
result = client.update_config({
    "user_root": "/new/storage/path"
})
```

---

### 数据导出

#### export_experiment()

导出实验数据。

```python
client.export_experiment(
    run_id: str,
    format: str = "json",
    include_media: bool = False
) -> bytes
```

**参数**：
- `run_id`: 运行 ID
- `format`: 导出格式（`json`, `csv`）
- `include_media`: 是否包含媒体文件

**返回值**: 导出的二进制数据

**示例**：
```python
# 导出为 JSON
data = client.export_experiment("run_id", format="json")
with open("experiment.json", "wb") as f:
    f.write(data)

# 导出为 CSV
data = client.export_experiment("run_id", format="csv")
with open("metrics.csv", "wb") as f:
    f.write(data)
```

---

### 系统管理

#### health_check()

检查 Viewer 健康状态。

```python
client.health_check() -> Dict[str, Any]
```

**返回值**: 健康状态信息

**示例**：
```python
health = client.health_check()

print(f"状态: {health['status']}")
print(f"版本: {health.get('version', 'unknown')}")
```

---

#### get_gpu_info()

获取 GPU 信息。

```python
client.get_gpu_info() -> Dict[str, Any]
```

**返回值**: GPU 信息

**示例**：
```python
gpu_info = client.get_gpu_info()

if gpu_info.get("available"):
    print(f"GPU: {gpu_info['devices'][0]['name']}")
    print(f"显存: {gpu_info['devices'][0]['memory_total']} MB")
```

---

## 扩展 API

### Remote API

通过 `client.remote` 访问。

#### connect()

建立 SSH 连接。

```python
client.remote.connect(
    host: str,
    port: int = 22,
    username: str = None,
    password: str = None,
    private_key_path: str = None,
    passphrase: str = None
) -> Dict[str, Any]
```

**示例**：
```python
result = client.remote.connect(
    host="remote-server.com",
    port=22,
    username="user",
    private_key_path="/path/to/key"
)

print(f"连接 ID: {result['connection_id']}")
```

---

#### start_viewer()

启动远程 Viewer。

```python
client.remote.start_viewer(
    connection_id: str,
    remote_root: str,
    local_port: Optional[int] = None,
    remote_port: Optional[int] = None
) -> Dict[str, Any]
```

**示例**：
```python
session = client.remote.start_viewer(
    connection_id="remote-server.com",
    remote_root="/data/runicorn"
)

print(f"访问地址: http://localhost:{session['local_port']}")
```

---

#### list_sessions()

列出 SSH 会话。

```python
client.remote.list_sessions() -> List[Dict[str, Any]]
```

---

#### list_viewer_sessions()

列出 Remote Viewer 会话。

```python
client.remote.list_viewer_sessions() -> List[Dict[str, Any]]
```

---

#### stop_viewer()

停止 Remote Viewer。

```python
client.remote.stop_viewer(session_id: str) -> Dict[str, Any]
```

---

#### disconnect()

断开 SSH 连接。

```python
client.remote.disconnect(host: str) -> Dict[str, Any]
```

---

## 错误处理

### 异常层次结构

```
RunicornAPIError
├── ConnectionError       # 连接失败
├── NotFoundError         # 资源未找到（404）
├── BadRequestError       # 请求参数无效（400）
├── ServerError           # 服务器错误（500+）
└── AuthenticationError   # 认证失败
```

### 异常捕获示例

```python
from runicorn.api import (
    RunicornClient,
    ConnectionError,
    NotFoundError,
    BadRequestError
)

try:
    client = RunicornClient("http://localhost:23300")
    run = client.get_run("nonexistent_id")
    
except ConnectionError as e:
    print(f"无法连接到 Viewer: {e}")
    print("请确保 Viewer 正在运行: runicorn viewer")
    
except NotFoundError as e:
    print(f"资源未找到: {e}")
    
except BadRequestError as e:
    print(f"请求参数无效: {e}")
    
except Exception as e:
    print(f"未知错误: {e}")
```

### 重试机制

客户端内置自动重试机制：

```python
# 自定义重试配置
client = RunicornClient(
    base_url="http://localhost:23300",
    max_retries=5  # 最多重试 5 次
)
```

**重试条件**：
- HTTP 状态码：500, 502, 503, 504
- 请求方法：GET, POST, PUT, DELETE
- 重试策略：指数退避（0.5s, 1s, 2s, 4s, 8s）

---

## 最佳实践

### 1. 使用上下文管理器

```python
# 推荐：自动管理资源
with api.connect() as client:
    experiments = client.list_experiments()
    # ... 使用 client

# 不推荐：手动管理
client = api.connect()
try:
    experiments = client.list_experiments()
finally:
    client.close()
```

### 2. 批量操作

```python
# 推荐：批量获取
experiments = client.list_experiments()
for exp in experiments:
    metrics = client.get_metrics(exp["id"])
    # ... 处理

# 不推荐：频繁连接
for i in range(100):
    with api.connect() as client:
        # 每次都创建新连接
```

### 3. 错误处理

```python
# 推荐：明确的错误处理
try:
    run = client.get_run(run_id)
except NotFoundError:
    print(f"Run {run_id} 不存在")
except Exception as e:
    print(f"错误: {e}")

# 不推荐：忽略错误
run = client.get_run(run_id)  # 可能抛出异常
```

### 4. 分页处理

```python
# 推荐：分页获取大量数据
def get_all_experiments(client):
    offset = 0
    limit = 100
    all_exps = []
    
    while True:
        batch = client.list_experiments(limit=limit, offset=offset)
        if not batch:
            break
        all_exps.extend(batch)
        offset += limit
    
    return all_exps
```

### 5. DataFrame 集成

```python
# 使用内置工具转换为 DataFrame
from runicorn.api import utils
import pandas as pd

with api.connect() as client:
    # 实验列表转 DataFrame
    experiments = client.list_experiments()
    df_exps = utils.experiments_to_dataframe(experiments)
    
    # 指标转 DataFrame
    metrics = client.get_metrics("run_id")
    df_metrics = utils.metrics_to_dataframe(metrics)
    
    # 分析
    print(df_metrics.describe())
    print(df_exps.groupby("project").size())
```

---

## 完整示例

### 示例 1：分析实验性能

```python
import runicorn.api as api
import pandas as pd

with api.connect() as client:
    # 获取所有视觉项目实验
    experiments = client.list_experiments(project="vision")
    
    # 找到最佳实验
    best_run = None
    best_acc = 0
    
    for exp in experiments:
        # 获取指标
        metrics = client.get_metrics(exp["id"])
        
        if "accuracy" in metrics["metrics"]:
            acc_points = metrics["metrics"]["accuracy"]
            max_acc = max(p["value"] for p in acc_points)
            
            if max_acc > best_acc:
                best_acc = max_acc
                best_run = exp
    
    if best_run:
        print(f"最佳实验: {best_run['name']}")
        print(f"准确率: {best_acc:.2f}%")
        print(f"运行 ID: {best_run['id']}")
```

### 示例 2：导出多个实验

```python
import runicorn.api as api
from pathlib import Path

output_dir = Path("exports")
output_dir.mkdir(exist_ok=True)

with api.connect() as client:
    experiments = client.list_experiments(project="nlp", limit=10)
    
    for exp in experiments:
        # 导出为 JSON
        data = client.export_experiment(exp["id"], format="json")
        
        # 保存文件
        filename = f"{exp['name']}_{exp['id']}.json"
        filepath = output_dir / filename
        filepath.write_bytes(data)
        
        print(f"✓ 导出: {filename}")
```

### 示例 3：对比多个实验

```python
import runicorn.api as api
from runicorn.api import utils
import matplotlib.pyplot as plt

with api.connect() as client:
    run_ids = ["run1", "run2", "run3"]
    
    # 对比 loss 指标
    df = utils.compare_runs(client, run_ids, "loss")
    
    # 绘图
    plt.figure(figsize=(10, 6))
    for run_id in run_ids:
        plt.plot(df["step"], df[run_id], label=run_id)
    
    plt.xlabel("Step")
    plt.ylabel("Loss")
    plt.legend()
    plt.title("Loss Comparison")
    plt.show()
```

### 示例 4：管理 Artifacts

```python
import runicorn.api as api

with api.connect() as client:
    # 列出所有模型
    models = client.artifacts.list_artifacts(type="model")
    
    for model in models:
        print(f"\n模型: {model['name']}")
        
        # 获取所有版本
        versions = client.artifacts.list_versions(model['name'])
        print(f"  版本: {len(versions)}")
        
        # 显示最新版本信息
        latest = versions[0]
        print(f"  最新: v{latest['version']}")
        print(f"  大小: {latest['size_bytes'] / 1024 / 1024:.2f} MB")
        print(f"  创建: {latest['created_at']}")
```

### 示例 5：远程 Viewer 管理

```python
import runicorn.api as api

with api.connect() as client:
    # 连接到远程服务器
    result = client.remote.connect(
        host="gpu-server.lab.com",
        username="researcher",
        private_key_path="~/.ssh/id_rsa"
    )
    
    print(f"✓ SSH 已连接: {result['connection_id']}")
    
    # 启动远程 Viewer
    session = client.remote.start_viewer(
        connection_id="gpu-server.lab.com",
        remote_root="/data/experiments"
    )
    
    print(f"✓ Remote Viewer 已启动")
    print(f"  访问地址: http://localhost:{session['local_port']}")
    print(f"  远程 PID: {session['remote_pid']}")
    
    # 列出会话
    sessions = client.remote.list_viewer_sessions()
    print(f"\n活动会话: {len(sessions)}")
    
    # 清理
    input("按 Enter 停止 Remote Viewer...")
    client.remote.stop_viewer(session['session_id'])
    client.remote.disconnect("gpu-server.lab.com")
    print("✓ 已清理")
```

---

## 工具函数

### utils 模块

`runicorn.api.utils` 提供实用工具函数。

#### metrics_to_dataframe()

```python
utils.metrics_to_dataframe(metrics_data: Dict) -> pd.DataFrame
```

将指标数据转换为 pandas DataFrame。

#### experiments_to_dataframe()

```python
utils.experiments_to_dataframe(experiments: List[Dict]) -> pd.DataFrame
```

将实验列表转换为 pandas DataFrame。

#### export_metrics_to_csv()

```python
utils.export_metrics_to_csv(
    client: RunicornClient,
    run_id: str,
    output_path: str,
    metric_names: Optional[List[str]] = None
) -> str
```

导出指标到 CSV 文件。

#### compare_runs()

```python
utils.compare_runs(
    client: RunicornClient,
    run_ids: List[str],
    metric_name: str
) -> pd.DataFrame
```

对比多个实验的特定指标。

---

## 数据模型

### Experiment

```python
@dataclass
class Experiment:
    id: str
    project: str
    name: str
    status: str
    created_at: float
    updated_at: float
    summary: Dict[str, Any]
    tags: List[str]
    
    @property
    def created_datetime(self) -> datetime
    
    @property
    def updated_datetime(self) -> datetime
```

### MetricSeries

```python
@dataclass
class MetricSeries:
    name: str
    points: List[MetricPoint]
    
    @property
    def values(self) -> List[float]
    
    @property
    def steps(self) -> List[int]
    
    def last_value(self) -> Optional[float]
    def min_value(self) -> Optional[float]
    def max_value(self) -> Optional[float]
```

### Artifact

```python
@dataclass
class Artifact:
    name: str
    version: int
    type: str
    created_at: float
    size_bytes: int
    metadata: Dict[str, Any]
    
    @property
    def id(self) -> str  # "name:vN"
    
    @property
    def size_mb(self) -> float
```

---

## 性能建议

### 连接池

客户端使用 `requests.Session` 实现连接池，自动复用 TCP 连接。

### 批量请求

```python
# 推荐：批量获取
experiments = client.list_experiments(limit=100)
for exp in experiments:
    # 处理单个实验
    pass

# 不推荐：逐个请求
for i in range(100):
    exp = client.get_experiment(f"run_{i}")
```

### 缓存策略

对于不常变化的数据，建议本地缓存：

```python
import pickle
from pathlib import Path

cache_file = Path(".cache/experiments.pkl")

# 尝试从缓存加载
if cache_file.exists():
    with open(cache_file, "rb") as f:
        experiments = pickle.load(f)
else:
    # 从 API 获取
    with api.connect() as client:
        experiments = client.list_experiments()
    
    # 保存到缓存
    cache_file.parent.mkdir(exist_ok=True)
    with open(cache_file, "wb") as f:
        pickle.dump(experiments, f)
```

---

## 故障排查

### 连接失败

```python
# 问题：ConnectionError
# 解决：确保 Viewer 正在运行
runicorn viewer

# 检查端口
client = api.connect("http://localhost:23300")
```

### 超时错误

```python
# 增加超时时间
client = RunicornClient(timeout=120)
```

### 速率限制

```python
import time

try:
    result = client.list_experiments()
except Exception as e:
    if "429" in str(e):  # Too Many Requests
        time.sleep(60)  # 等待 1 分钟
        result = client.list_experiments()
```

---

## 参考资料

- **REST API 文档**: [README.md](./README.md)
- **SDK 文档**: [../user-guide/docs/sdk/overview.md](../user-guide/docs/sdk/overview.md)
- **示例代码**: `tests/common/test_api_client.py`
- **源代码**: `src/runicorn/api/`

---

**最后更新**: 2025-10-24  
**维护者**: Runicorn 开发团队  
**API 版本**: v1.0

