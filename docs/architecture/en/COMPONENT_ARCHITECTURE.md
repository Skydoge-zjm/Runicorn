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

## Remote Viewer Components (v0.5.0)

### Connection Manager

**Responsibility**: Manage SSH connection lifecycle

**Components**:
- **SSH Client**: Paramiko-based connection management
- **Connection Pool**: Support multiple concurrent connections
- **Authentication Manager**: Password/Key/Agent authentication
- **Keep-alive**: Periodic heartbeat to maintain connection

**Key Classes**:
```python
class ConnectionManager:
    def connect(host, port, username, auth_method) -> Connection
    def disconnect(connection_id, cleanup=True)
    def get_connection(connection_id) -> Connection
    def list_connections() -> List[Connection]
    def is_alive(connection_id) -> bool
```

---

### Environment Detector

**Responsibility**: Auto-detect remote Python environments

**Components**:
- **Environment Scanner**: Detect conda/virtualenv/system Python
- **Version Validator**: Check Runicorn installation and version
- **Compatibility Checker**: Verify version compatibility

**Detection Flow**:
```python
1. Scan conda environments: `conda env list`
2. Scan virtualenv: ~/.virtualenvs/, ~/venv/
3. Check system Python: `which python`
4. Validate Runicorn for each environment:
   python -c "import runicorn; print(runicorn.__version__)"
5. Return compatible environment list
```

---

### Viewer Launcher

**Responsibility**: Start and manage remote Viewer process

**Components**:
- **Process Launcher**: Execute Viewer command on remote
- **Process Monitor**: Track PID and status
- **Log Collector**: Collect remote Viewer logs
- **Cleanup Handler**: Graceful shutdown and force terminate

**Startup Command**:
```bash
source /path/to/env/bin/activate && \
runicorn viewer --host 127.0.0.1 --port 23300 --no-open-browser \
> /tmp/runicorn_viewer_{id}.log 2>&1 &
```

---

### Tunnel Manager

**Responsibility**: SSH port forwarding tunnel management

**Components**:
- **Tunnel Creator**: Establish port forwarding using Paramiko
- **Port Selector**: Auto-select available local port
- **Forwarding Thread**: Background thread handles data forwarding
- **Health Monitor**: Tunnel connectivity check

**Tunnel Structure**:
```python
@dataclass
class Tunnel:
    tunnel_id: str
    connection_id: str
    local_port: int          # e.g. 8081
    remote_port: int         # e.g. 23300
    is_active: bool
    bytes_sent: int
    bytes_received: int
```

---

### Health Checker

**Responsibility**: Monitor connection and Viewer health status

**Components**:
- **Connection Checker**: SSH connection aliveness test
- **Viewer Checker**: HTTP health check
- **Tunnel Checker**: Port connectivity test
- **Latency Tester**: Round-trip time measurement

**Check Interval**: Every 30 seconds

**Health Status**:
```python
@dataclass
class HealthStatus:
    is_healthy: bool
    connection_alive: bool
    viewer_running: bool
    tunnel_active: bool
    latency_ms: float
    last_check_time: float
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
│   │       │   ├── PathTreePanel (v0.6.0)
│   │       │   ├── ExperimentTable
│   │       │   ├── CompareRunsPanel (v0.6.0)
│   │       │   ├── CompareChartsView (v0.6.0)
│   │       │   └── RecycleBin
│   │       ├── RunDetailPage
│   │       │   ├── MetricChart (multiple)
│   │       │   ├── LogsViewer (WebSocket, ANSI)
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

## New Frontend Components (v0.6.0)

### PathTreePanel

**File**: `web/frontend/src/components/PathTreePanel.tsx`

**Responsibility**: VSCode-style hierarchical path navigation for experiments

**Features**:
- Hierarchical path display with folder icons
- Run count badges per path (with running indicator animation)
- Search/filter functionality
- Right-click context menu for batch operations (delete, export)
- Keyboard navigation support
- Smooth animations with framer-motion
- Expanded state persistence in localStorage

**Props**:
```typescript
interface PathTreePanelProps {
  selectedPath: string | null
  onSelectPath: (path: string | null) => void
  onBatchDelete?: (path: string) => void
  onBatchExport?: (path: string) => void
  style?: React.CSSProperties
}
```

**API Integration**:
- `GET /api/paths?include_stats=true` - Fetch path tree with statistics

**Design Pattern**: Controlled component with external state management

---

### CompareChartsView

**File**: `web/frontend/src/components/CompareChartsView.tsx`

**Responsibility**: Display metric comparison charts for selected runs

**Features**:
- Auto-detect common metrics (present in ≥2 runs)
- Metric visibility toggles (show/hide individual metrics)
- ECharts group synchronization for linked zoom/pan
- Performance optimization via `legend.selected` for run visibility
- Responsive grid layout (2 columns on large screens)
- Animated chart appearance with framer-motion

**Props**:
```typescript
interface CompareChartsViewProps {
  runIds: string[]
  visibleRunIds: Set<string>
  metricsMap: Map<string, MetricsData>
  runLabels: Map<string, string>
  colors: string[]
  loading: boolean
}
```

**Performance Optimization**:
- Uses `legend.selected` to toggle series visibility instead of re-rendering
- Excludes X-axis keys from comparison (step, iter, batch, global_step, time, epoch)
- Memoized common metrics calculation

**Design Pattern**: Presentational component with derived state

---

### CompareRunsPanel

**File**: `web/frontend/src/components/CompareRunsPanel.tsx`

**Responsibility**: Left panel showing selected runs info in compare mode

**Features**:
- Color dot matching chart line colors
- Run status indicators (finished/failed/running)
- Eye icon to toggle run visibility in charts
- Click to navigate to run detail page
- Auto-refresh indicator when running experiments exist
- Add more runs button

**Props**:
```typescript
interface CompareRunsPanelProps {
  runs: CompareRunInfo[]
  colors: string[]
  visibleRunIds: Set<string>
  onToggleRunVisibility: (runId: string) => void
  onAddRuns: () => void
  onBack: () => void
  style?: React.CSSProperties
}

interface CompareRunInfo {
  runId: string
  path: string
  alias: string | null
  status: string
}
```

**Design Pattern**: Controlled component with callback props

---

### LogsViewer (Enhanced)

**File**: `web/frontend/src/components/LogsViewer.tsx`

**Responsibility**: Real-time log viewing with ANSI color support

**v0.6.0 Enhancements**:
- **ANSI Color Support**: Full terminal color rendering via `ansi-to-html`
- **Line Numbers**: Numbered lines for easy reference
- **Search Functionality**: Keyword search with highlighting
- **Smart tqdm Filtering**: Heuristic detection of tqdm progress bars
- **Auto-scroll Toggle**: Enable/disable auto-scroll to bottom
- **Copy/Clear**: Copy all logs or clear display

**Key Implementation**:
```typescript
// ANSI converter with terminal-like colors
const ansiConverter = new AnsiToHtml({
  fg: '#e6e9ef',
  bg: '#0b1020',
  colors: {
    0: '#1d1f21',   // black
    1: '#cc6666',   // red
    2: '#b5bd68',   // green
    // ... more colors
  },
})

// tqdm detection heuristic
function isTqdmLine(s: string): boolean {
  // Matches: " 45%|███████████▍            | 45/100 [00:12<00:15,  3.45it/s]"
  if (/\d{1,3}%\|[█▏▎▍▌▋▊▉#\-\s]+\|/.test(s)) return true
  // ... more patterns
  return false
}
```

**WebSocket Connection**:
- Exponential backoff reconnection (500ms base, 10s max)
- Connection status indicator (connected/connecting/disconnected)
- Max 5000 lines buffer

**Design Pattern**: Stateful component with WebSocket lifecycle management

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

