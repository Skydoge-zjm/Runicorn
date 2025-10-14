[English](COMPONENT_ARCHITECTURE.md) | [简体中文](../zh/COMPONENT_ARCHITECTURE.md)

---

# Component Architecture

**Document Type**: Architecture  
**Purpose**: Detailed breakdown of Runicorn's component structure and interactions

---

## Component Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                        SDK Layer                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Run class - Experiment context and lifecycle        │   │
│  │ Artifact class - Versioned asset management         │   │
│  │ Module functions - Convenience API (init, log, etc) │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Viewer/API Layer                          │
│  ┌──────────────┬──────────────┬─────────────────────────┐ │
│  │ API Routes   │ Services     │ Middleware              │ │
│  │ - runs.py    │ - storage.py │ - CORS                  │ │
│  │ - artifacts  │ - gpu.py     │ - Rate limiting         │ │
│  │ - metrics    │ - modern_st  │ - Logging               │ │
│  └──────────────┴──────────────┴─────────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Business Logic Layer                        │
│  ┌──────────────┬──────────────┬─────────────────────────┐ │
│  │ Experiment   │ Artifact     │ Environment             │ │
│  │ Manager      │ Storage      │ Capture                 │ │
│  │ Lineage      │ Dedup Pool   │ SSH Client              │ │
│  └──────────────┴──────────────┴─────────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     Storage Layer                            │
│  ┌───────────────────────┬──────────────────────────────┐  │
│  │ SQLite Backend        │ File System Backend          │  │
│  │ - Connection pool     │ - Directory scanner          │  │
│  │ - Query builder       │ - JSON reader/writer         │  │
│  │ - Transaction mgmt    │ - File lock manager          │  │
│  └───────────────────────┴──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## SDK Layer Components

### Run Class

**Responsibility**: Manage single experiment lifecycle

**Key Methods**:
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

**Design Patterns**:
- Singleton: One active run per process
- Builder: Fluent API for configuration
- Thread-safe: FileLock for concurrent access

---

### Artifact Class

**Responsibility**: Version-controlled asset management

**Key Methods**:
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

**Design Patterns**:
- Builder: Chainable methods
- Immutable: Version snapshots never change
- Content-addressable: Files identified by hash

---

## API Layer Components

### Route Organization

**Modular Structure**:
```
viewer/api/
├── runs.py           # Experiment CRUD
├── artifacts.py      # Artifact version control
├── metrics.py        # Metrics queries
├── config.py         # Configuration
├── ssh.py            # SSH connections
├── experiments.py    # Advanced experiment operations
├── v2/               # V2 high-performance API
│   ├── experiments.py
│   └── analytics.py
└── __init__.py       # Route registration
```

**Dependency Injection**:
```python
# Routes don't create dependencies
@router.get("/runs")
async def list_runs(request: Request):
    storage_root = request.app.state.storage_root  # Injected
    # Use storage_root...
```

---

### Service Layer

**Purpose**: Abstract business logic from routes

**Structure**:
```
viewer/services/
├── storage.py         # File system operations
├── modern_storage.py  # SQLite operations
└── gpu.py             # GPU telemetry
```

**Pattern**: Services are stateless functions

```python
# Service function
async def list_experiments(
    storage_root: Path,
    project: str = None,
    status: str = None
) -> List[ExperimentRecord]:
    # Business logic here
    pass

# Route uses service
@router.get("/runs")
async def list_runs(request: Request):
    storage_root = request.app.state.storage_root
    experiments = await list_experiments(storage_root)
    return experiments
```

---

## Storage Layer Components

### SQLite Backend

**Components**:
- **ConnectionPool**: Thread-safe connection management
- **SQLiteStorageBackend**: CRUD operations
- **Query Builder**: Dynamic SQL generation with validation

**Thread Safety**:
```python
class ConnectionPool:
    def __init__(db_path, pool_size=10):
        self.pool = queue.Queue(maxsize=pool_size)
        # Pre-create connections
        for _ in range(pool_size):
            conn = create_connection()
            self.pool.put(conn)
    
    def get_connection():
        return self.pool.get()  # Blocks if all in use
    
    def return_connection(conn):
        self.pool.put(conn)
```

---

### File Backend

**Components**:
- **Directory Scanner**: Discovers runs in file system
- **JSON Reader**: Safe JSON parsing with error handling
- **Status Checker**: Process liveness detection

**Lazy Loading**:
```python
# Only load what's needed
def list_runs(root):
    for entry in iter_all_runs(root):
        # Don't load full metadata yet
        yield RunEntry(dir=entry.dir, project=entry.project)

# Load details on demand
def get_run_detail(run_id):
    entry = find_run(run_id)
    # Now load full metadata
    return load_all_metadata(entry.dir)
```

---

## Artifacts System Components

### Artifact Storage

**Components**:
- **Version Manager**: Sequential version assignment
- **File Hasher**: SHA256 computation
- **Dedup Manager**: Hard link creation
- **Manifest Builder**: File inventory

**Component Interaction**:
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

### Lineage Tracker

**Components**:
- **Graph Builder**: Constructs dependency graph
- **Traverser**: BFS/DFS traversal with depth limit
- **Node Creator**: Converts runs/artifacts to nodes

**Algorithm**:
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
        
        # Find dependencies
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

## Remote Sync Components

### Adapter Pattern

**Purpose**: Unified interface for local/remote storage

```python
class StorageAdapter(ABC):
    @abstractmethod
    def list_artifacts(type): pass
    
    @abstractmethod
    def load_artifact(name, type, version): pass

class LocalAdapter(StorageAdapter):
    # Implements using local filesystem

class RemoteAdapter(StorageAdapter):
    # Implements using SSH + cache
```

**Usage**:
```python
# API doesn't care if local or remote
adapter = get_storage_adapter(request)  # Returns LocalAdapter or RemoteAdapter
artifacts = adapter.list_artifacts(type="model")  # Works the same
```

---

### Cache Manager

**Components**:
- **Metadata Cache**: SQLite index of remote metadata
- **File Cache**: LRU cache for downloaded files
- **Sync Scheduler**: Periodic metadata refresh

**Cache Structure**:
```
~/.runicorn_remote_cache/{host}_{user}/
├── index.db           # SQLite: Cached metadata
├── metadata/          # Raw JSON files
└── downloads/         # Downloaded artifacts (LRU)
```

---

## Frontend Components

### Component Tree

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
│   │       │   ├── MetricChart (multiple)
│   │       │   ├── LogsViewer (WebSocket)
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

### State Management

**Context Providers**:
```javascript
App
└── SettingsProvider (global settings)
    └── RouterProvider
        └── Page components
            └── Local state (useState, useEffect)
```

**localStorage**: Persistent user preferences

---

## Module Dependencies

### Dependency Graph

```
SDK (runicorn.sdk)
    ↓ imports
storage.backends
    ↓ imports
storage.models
    ↓
(No circular dependencies)

viewer.api.runs
    ↓ imports
viewer.services.storage
    ↓ imports
config
    ↓
(Clean layered dependencies)
```

### Import Rules

- ✅ **Top-down**: Upper layers import lower layers
- ❌ **No cycles**: Lower layers never import upper
- ✅ **Interfaces**: Use abstract base classes for flexibility

---

**Related**: [DATA_FLOW.md](DATA_FLOW.md) | [STORAGE_DESIGN.md](STORAGE_DESIGN.md)

**Back to**: [Architecture Index](README.md)

