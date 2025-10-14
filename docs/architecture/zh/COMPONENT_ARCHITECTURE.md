[English](../en/COMPONENT_ARCHITECTURE.md) | [简体中文](COMPONENT_ARCHITECTURE.md)

---

# 组件架构

**文档类型**: 架构  
**目的**: Runicorn 组件结构和交互的详细分解

---

## 组件层次

```
┌─────────────────────────────────────────────────────────────┐
│                        SDK 层                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Run 类 - 实验上下文和生命周期                       │   │
│  │ Artifact 类 - 版本化资产管理                        │   │
│  │ 模块函数 - 便捷 API（init, log 等）                │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Viewer/API 层                             │
│  ┌──────────────┬──────────────┬─────────────────────────┐ │
│  │ API 路由     │ 服务         │ 中间件                  │ │
│  │ - runs.py    │ - storage.py │ - CORS                  │ │
│  │ - artifacts  │ - gpu.py     │ - 速率限制              │ │
│  │ - metrics    │ - modern_st  │ - 日志                  │ │
│  └──────────────┴──────────────┴─────────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  业务逻辑层                                  │
│  ┌──────────────┬──────────────┬─────────────────────────┐ │
│  │ 实验         │ Artifact     │ 环境                    │ │
│  │ 管理器       │ 存储         │ 捕获                    │ │
│  │ 血缘         │ 去重池       │ SSH 客户端              │ │
│  └──────────────┴──────────────┴─────────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     存储层                                   │
│  ┌───────────────────────┬──────────────────────────────┐  │
│  │ SQLite 后端           │ 文件系统后端                 │  │
│  │ - 连接池              │ - 目录扫描器                 │  │
│  │ - 查询构建器          │ - JSON 读写器                │  │
│  │ - 事务管理            │ - 文件锁管理器               │  │
│  └───────────────────────┴──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## SDK 层组件

### Run 类

**职责**: 管理单个实验生命周期

**关键方法**:
```python
class Run:
    def __init__(project, name, storage, run_id, capture_env)
    def log(data, step, stage)
    def log_text(text)
    def log_image(key, image, step)
    def set_primary_metric(name, mode)
    def summary(update)
    def log_artifact(artifact)
    def use_artifact(spec)
    def finish(status)
```

**设计模式**:
- 单例: 每个进程一个活动运行
- 构建器: 流畅的配置 API
- 线程安全: FileLock 用于并发访问

---

### Artifact 类

**职责**: 版本控制的资产管理

**关键方法**:
```python
class Artifact:
    def __init__(name, type, description, metadata)
    def add_file(path, name)
    def add_dir(path, exclude_patterns)
    def add_reference(uri, checksum)
    def add_metadata(metadata)
    def add_tags(*tags)
    def download(target_dir)
    def get_manifest()
```

**设计模式**:
- 构建器: 可链式方法
- 不可变: 版本快照永不改变
- 内容寻址: 文件通过哈希识别

---

## API 层组件

### 路由组织

**模块化结构**:
```
viewer/api/
├── runs.py           # 实验 CRUD
├── artifacts.py      # Artifact 版本控制
├── metrics.py        # 指标查询
├── config.py         # 配置
├── ssh.py            # SSH 连接
├── experiments.py    # 高级实验操作
├── v2/               # V2 高性能 API
│   ├── experiments.py
│   └── analytics.py
└── __init__.py       # 路由注册
```

**依赖注入**:
```python
# 路由不创建依赖
@router.get("/runs")
async def list_runs(request: Request):
    storage_root = request.app.state.storage_root  # 注入
    # 使用 storage_root...
```

---

### 服务层

**目的**: 从路由中抽象业务逻辑

**结构**:
```
viewer/services/
├── storage.py         # 文件系统操作
├── modern_storage.py  # SQLite 操作
└── gpu.py             # GPU 遥测
```

**模式**: 服务是无状态函数

```python
# 服务函数
async def list_experiments(
    storage_root: Path,
    project: str = None,
    status: str = None
) -> List[ExperimentRecord]:
    # 业务逻辑在这里
    pass

# 路由使用服务
@router.get("/runs")
async def list_runs(request: Request):
    storage_root = request.app.state.storage_root
    experiments = await list_experiments(storage_root)
    return experiments
```

---

## 存储层组件

### SQLite 后端

**组件**:
- **ConnectionPool**: 线程安全连接管理
- **SQLiteStorageBackend**: CRUD 操作
- **Query Builder**: 带验证的动态 SQL 生成

**线程安全**:
```python
class ConnectionPool:
    def __init__(db_path, pool_size=10):
        self.pool = queue.Queue(maxsize=pool_size)
        # 预创建连接
        for _ in range(pool_size):
            conn = create_connection()
            self.pool.put(conn)
    
    def get_connection():
        return self.pool.get()  # 如果全部使用则阻塞
    
    def return_connection(conn):
        self.pool.put(conn)
```

---

### 文件后端

**组件**:
- **目录扫描器**: 在文件系统中发现运行
- **JSON 读取器**: 带错误处理的安全 JSON 解析
- **状态检查器**: 进程活跃性检测

**延迟加载**:
```python
# 仅加载所需内容
def list_runs(root):
    for entry in iter_all_runs(root):
        # 还不加载完整元数据
        yield RunEntry(dir=entry.dir, project=entry.project)

# 按需加载详情
def get_run_detail(run_id):
    entry = find_run(run_id)
    # 现在加载完整元数据
    return load_all_metadata(entry.dir)
```

---

## Artifacts 系统组件

### Artifact 存储

**组件**:
- **版本管理器**: 顺序版本分配
- **文件哈希器**: SHA256 计算
- **去重管理器**: 硬链接创建
- **清单构建器**: 文件清单

**组件交互**:
```
ArtifactStorage
    ├── _store_file()
    │   ├── compute_hash()
    │   ├── check_dedup_pool()
    │   └── create_link_or_copy()
    ├── save_artifact()
    │   ├── validate()
    │   ├── assign_version()
    │   ├── store_files()
    │   ├── create_manifest()
    │   └── update_index()
    └── load_artifact()
        ├── find_version()
        ├── load_metadata()
        └── load_manifest()
```

---

### 血缘追踪器

**组件**:
- **图构建器**: 构建依赖图
- **遍历器**: BFS/DFS 遍历带深度限制
- **节点创建器**: 将运行/artifacts 转换为节点

**算法**:
```python
def build_lineage(artifact_id, max_depth=3):
    graph = Graph()
    queue = [(artifact_id, 0)]  # (id, depth)
    visited = set()
    
    while queue:
        id, depth = queue.pop(0)
        if depth > max_depth or id in visited:
            continue
        
        visited.add(id)
        node = create_node(id)
        graph.add_node(node)
        
        # 查找依赖
        if is_artifact(id):
            creator_run = find_creator(id)
            graph.add_edge(creator_run, id, "produces")
            queue.append((creator_run, depth + 1))
        else:  # is run
            used_artifacts = find_used_artifacts(id)
            for art in used_artifacts:
                graph.add_edge(art, id, "uses")
                queue.append((art, depth + 1))
    
    return graph
```

---

## 远程同步组件

### 适配器模式

**目的**: 本地/远程存储的统一接口

```python
class StorageAdapter(ABC):
    @abstractmethod
    def list_artifacts(type): pass
    
    @abstractmethod
    def load_artifact(name, type, version): pass

class LocalAdapter(StorageAdapter):
    # 使用本地文件系统实现

class RemoteAdapter(StorageAdapter):
    # 使用 SSH + 缓存实现
```

**使用**:
```python
# API 不关心是本地还是远程
adapter = get_storage_adapter(request)  # 返回 LocalAdapter 或 RemoteAdapter
artifacts = adapter.list_artifacts(type="model")  # 工作方式相同
```

---

### 缓存管理器

**组件**:
- **元数据缓存**: 远程元数据的 SQLite 索引
- **文件缓存**: 下载文件的 LRU 缓存
- **同步调度器**: 定期元数据刷新

**缓存结构**:
```
~/.runicorn_remote_cache/{host}_{user}/
├── index.db           # SQLite: 缓存的元数据
├── metadata/          # 原始 JSON 文件
└── downloads/         # 下载的 artifacts（LRU）
```

---

## 前端组件

### 组件树

```
App
├── Layout
│   ├── Header
│   │   ├── Menu
│   │   ├── LanguageSelector
│   │   └── SettingsButton
│   ├── Content
│   │   └── Routes
│   │       ├── ExperimentPage
│   │       │   ├── ExperimentTable
│   │       │   └── RecycleBin
│   │       ├── RunDetailPage
│   │       │   ├── MetricChart（多个）
│   │       │   ├── LogsViewer（WebSocket）
│   │       │   └── RunArtifacts
│   │       ├── ArtifactsPage
│   │       │   └── ArtifactTable
│   │       └── ArtifactDetailPage
│   │           ├── ArtifactInfo
│   │           ├── VersionHistory
│   │           └── LineageGraph
│   └── Footer
└── SettingsDrawer
```

### 状态管理

**Context 提供者**:
```javascript
App
└── SettingsProvider（全局设置）
    └── RouterProvider
        └── 页面组件
            └── 本地状态（useState, useEffect）
```

**localStorage**: 持久化用户偏好

---

## 模块依赖

### 依赖图

```
SDK (runicorn.sdk)
    ↓ 导入
storage.backends
    ↓ 导入
storage.models
    ↓
（无循环依赖）

viewer.api.runs
    ↓ 导入
viewer.services.storage
    ↓ 导入
config
    ↓
（清晰的分层依赖）
```

### 导入规则

- ✅ **自上而下**: 上层导入下层
- ❌ **无循环**: 下层永不导入上层
- ✅ **接口**: 使用抽象基类以获得灵活性

---

**相关文档**: [DATA_FLOW.md](DATA_FLOW.md) | [STORAGE_DESIGN.md](STORAGE_DESIGN.md)

**返回**: [架构索引](README.md)

