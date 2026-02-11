[English](SYSTEM_OVERVIEW.md) | [简体中文](../zh/SYSTEM_OVERVIEW.md)

---

# Runicorn System Overview

**Document Type**: Architecture  
**Version**: v0.6.0  
**Last Updated**: 2025-01-XX

---

## Purpose

This document provides a high-level overview of the Runicorn system architecture, explaining the overall design, technology choices, and core principles.

---

## System Architecture Diagram

### Overall Architecture (v0.5.0)

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Layer                                │
│  ┌──────────┬──────────┬────────────┬──────────────────────┐  │
│  │ Python   │ Web UI   │ Desktop    │ CLI                  │  │
│  │ SDK      │ (Browser)│ App (Tauri)│ Commands             │  │
│  └────┬─────┴─────┬────┴──────┬─────┴────────────┬─────────┘  │
└───────┼───────────┼───────────┼──────────────────┼────────────┘
        │           │           │                  │
┌───────▼───────────▼───────────▼──────────────────▼────────────┐
│                     API Layer (FastAPI)                         │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────────┐│
│  │ Runs API │ Artifacts│ Metrics  │ Config   │ Remote       ││
│  │ (V1/V2)  │ API      │ API      │ API      │ Viewer API   ││
│  └────┬─────┴─────┬────┴────┬─────┴────┬─────┴──────┬───────┘│
└───────┼───────────┼─────────┼──────────┼────────────┼────────┘
        │           │         │          │            │
┌───────▼───────────▼─────────▼──────────▼────────────▼────────┐
│                   Business Logic Layer                          │
│  ┌──────────────┬──────────────┬──────────────────────────┐  │
│  │ Experiment   │ Artifact     │ Environment             │  │
│  │ Manager      │ Storage      │ Capture                 │  │
│  └──────┬───────┴──────┬───────┴──────────────┬──────────┘  │
└─────────┼──────────────┼────────────────────────┼───────────┘
          │              │                        │
┌─────────▼──────────────▼────────────────────────▼───────────┐
│                  Storage Layer (Hybrid)                       │
│  ┌────────────────────┬─────────────────────────────────┐   │
│  │ SQLite Backend     │ File System                     │   │
│  │ - experiments tbl  │ - runs/ (metadata, logs)        │   │
│  │ - metrics table    │ - artifacts/ (models, datasets) │   │
│  │ - indexes          │ - .dedup/ (deduplication pool)  │   │
│  └────────────────────┴─────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Remote Viewer Architecture (v0.5.0 New)

```
Local Machine                           Remote Server
┌────────────────────────┐            ┌────────────────────────┐
│  Local Viewer          │            │  Remote Server         │
│  (localhost:23300)     │            │  (gpu-server.com)      │
│                        │            │                        │
│  ┌──────────────────┐ │            │  ┌──────────────────┐ │
│  │ Remote API       │ │            │  │ Remote Viewer    │ │
│  │ /api/remote/*    │ │            │  │ (temp process)   │ │
│  └────────┬─────────┘ │            │  └────────┬─────────┘ │
│           │           │            │           │           │
│           │ SSH Conn  │────────────│           │           │
│           │ (port 22) │            │           │           │
│           │           │            │           │           │
│  ┌────────▼─────────┐ │            │  ┌────────▼─────────┐ │
│  │ SSH Tunnel       │◄├────────────┤►│  Viewer Instance │ │
│  │ (localhost:8081) │ │Port Forward│  │  (port 23300)    │ │
│  └──────────────────┘ │            │  └──────────────────┘ │
│           │           │            │           │           │
│  ┌────────▼─────────┐ │            │  ┌────────▼─────────┐ │
│  │ Browser          │ │            │  │ Data Storage     │
│  │ http://          │ │            │  │ ~/RunicornData   │ │
│  │  localhost:8081  │ │            │  └──────────────────┘ │
│  └──────────────────┘ │            │                        │
└────────────────────────┘            └────────────────────────┘

Workflow:
1. User connects to remote server via local Viewer (SSH)
2. Auto-detect remote Python environments and Runicorn installation
3. Start temporary Viewer instance on remote server
4. Port forward via SSH tunnel to local machine
5. User accesses remote data via local browser
6. No file sync needed, real-time remote data access
```

---

## Technology Stack

### Backend

| Technology | Version | Purpose | Why Chosen |
|------------|---------|---------|------------|
| **Python** | 3.8+ | Core language | Ecosystem, ML community standard |
| **FastAPI** | 0.110+ | API framework | Modern, async, auto-docs, performance |
| **SQLite** | 3.x | Metadata storage | Zero-config, portable, ACID |
| **Paramiko** | 3.3+ | SSH client | Pure Python, well-maintained |
| **Uvicorn** | 0.23+ | ASGI server | High performance, production-ready |

### Frontend

| Technology | Version | Purpose | Why Chosen |
|------------|---------|---------|------------|
| **React** | 18.2 | UI framework | Component reusability, ecosystem |
| **TypeScript** | 5.4+ | Type safety | Catch errors early, better IDE support |
| **Ant Design** | 5.19+ | UI components | Professional, comprehensive, i18n |
| **ECharts** | 5.5+ | Charting | Powerful, performant, ML-focused |
| **Vite** | 5.3+ | Build tool | Fast HMR, optimized builds |

### Desktop

| Technology | Version | Purpose | Why Chosen |
|------------|---------|---------|------------|
| **Tauri** | Latest | Desktop wrapper | Lightweight, secure, cross-platform |
| **Rust** | Stable | Native backend | Performance, safety |

---

## Core Design Principles

### 1. Privacy-First

**Principle**: All data stays local, zero telemetry

**Implementation**:
- No external network calls except SSH (user-initiated)
- No analytics, tracking, or usage reporting
- No cloud dependencies

**Rationale**: ML research often involves sensitive or proprietary data

---

### 2. Zero-Configuration

**Principle**: Works out of the box with sensible defaults

**Implementation**:
- SQLite database auto-created
- Storage directories auto-initialized
- No database server setup required
- Default config works for most users

**Rationale**: Reduce barrier to entry, focus on research not setup

---

### 3. Performance-Scalable

**Principle**: Fast for both small and large scale

**Implementation**:
- Hybrid storage: Files for large data, SQLite for queries
- V2 API: 100x faster for 10,000+ experiments
- Connection pooling and caching
- Efficient indexing

**Rationale**: Support from individual researchers (10s of experiments) to labs (10,000s of experiments)

---

### 4. Backward Compatible

**Principle**: Never break existing user code

**Implementation**:
- V1 API maintained alongside V2
- Automatic storage migration
- Optional new features
- Semantic versioning

**Rationale**: Trust and stability for research workflows

---

### 5. Self-Contained

**Principle**: Minimal dependencies, offline-capable

**Implementation**:
- Bundled frontend in Python package
- No Node.js runtime required
- Standard library preferred over external deps
- Optional dependencies for extras

**Rationale**: Work in air-gapped environments, reduce installation issues

---

## System Boundaries

### In Scope

✅ **Local experiment tracking**
- Record metrics, logs, images
- Organize experiments hierarchically
- Compare multiple runs

✅ **Model version control**
- Automatic versioning
- Content deduplication
- Lineage tracking

✅ **Local-first collaboration**
- SSH-based remote sync
- Shared storage on network drives
- Export/import for transfer

✅ **Visualization**
- Real-time metric charts
- Log streaming
- Artifact lineage graphs

### Out of Scope

❌ **Cloud hosting** - Runicorn is self-hosted only
❌ **Multi-tenancy** - Designed for single user/team
❌ **Distributed storage** - No built-in replication
❌ **Authentication** - Local API, no auth needed
❌ **Team permissions** - No RBAC system

---

## High-Level Components

### 1. SDK Layer

**Responsibility**: User-facing Python API

**Key Classes**:
- `Run`: Experiment context and lifecycle
- `Artifact`: Version-controlled assets
- Module-level functions: `init()`, `log()`, `finish()`

**Design Pattern**: Singleton active run, thread-safe

---

### 2. Storage Layer

**Responsibility**: Persistent data management

**Components**:
- **SQLite Backend**: Fast metadata queries
- **File System**: Large files, logs, media
- **Hybrid Coordinator**: Synchronizes both backends

**Design Pattern**: Strategy pattern for backends

---

### 3. API Layer

**Responsibility**: HTTP interface to storage

**Components**:
- **Route Modules**: Organized by feature (runs, artifacts, etc.)
- **Service Layer**: Business logic abstraction
- **Middleware**: CORS, rate limiting, logging

**Design Pattern**: Layered architecture, dependency injection

---

### 4. Web UI

**Responsibility**: Visualization and interaction

**Components**:
- **React App**: SPA with client-side routing
- **Components**: Reusable UI elements
- **State Management**: Context API + localStorage
- **API Client**: Centralized HTTP layer

**Design Pattern**: Component-based, unidirectional data flow

---

### 5. Artifacts System

**Responsibility**: Version control for ML assets

**Components**:
- **Artifact Storage**: Physical file management
- **Version Index**: Metadata and versioning
- **Dedup Pool**: Content-addressed storage
- **Lineage Tracker**: Dependency graph builder

**Design Pattern**: Content-addressable storage, immutable versions

---

### 6. Assets System (v0.6.0 New)

**Responsibility**: Workspace snapshots and content-addressed blob storage

**Components**:
- **Snapshot Manager** (`snapshot.py`): Create workspace snapshots with SHA256 fingerprinting
- **Blob Store** (`blob_store.py`): Content-addressed storage with automatic deduplication
- **Fingerprint Calculator** (`fingerprint.py`): Fast file hashing for change detection
- **Ignore Parser** (`ignore.py`): `.rnignore` file parsing (gitignore-compatible)
- **Outputs Scanner** (`outputs_scan.py`): Automatic output file detection
- **Assets JSON** (`assets_json.py`): Manifest file handling

**Key Features**:
- SHA256-based content deduplication (50-90% storage savings)
- Incremental snapshots (only changed files)
- Manifest-based restore
- Orphaned blob cleanup

**Design Pattern**: Content-addressable storage, copy-on-write

---

### 7. Console Capture System (v0.6.0 New)

**Responsibility**: Capture stdout/stderr and Python logging output

**Components**:
- **Log Manager** (`log_manager.py`): Central logging coordination
- **Capture** (`capture.py`): TeeWriter for stdout/stderr interception
- **Logging Handler** (`logging_handler.py`): Python `logging` module integration

**Key Features**:
- Transparent stdout/stderr capture
- Python logging handler integration via `run.get_logging_handler()`
- Smart tqdm filtering (modes: smart/all/none)
- Real-time WebSocket streaming

**Design Pattern**: Decorator pattern for stream interception

---

### 8. Log Compatibility Layer (v0.6.0 New)

**Responsibility**: Drop-in replacement for common ML logging libraries

**Components**:
- **MetricLogger** (`log_compat/torchvision.py`): torchvision.MetricLogger compatible API

**Key Features**:
- API-compatible with torchvision's MetricLogger
- Automatic metric aggregation (avg, median, max, value)
- Seamless integration with existing training scripts

**Design Pattern**: Adapter pattern

---

### 9. Index System (v0.6.0 New)

**Responsibility**: Fast experiment and run indexing

**Components**:
- **Index Database** (`index/db.py`): SQLite-based index for quick lookups

**Key Features**:
- Accelerated experiment listing
- Path-based filtering
- Status aggregation

---

### 10. Workspace Management (v0.6.0 New)

**Responsibility**: Workspace root detection and configuration

**Components**:
- **Root Detector** (`workspace/root.py`): Find workspace root directory

**Key Features**:
- Automatic workspace detection (looks for `.runicorn/` or `runicorn.yaml`)
- Support for nested workspaces

---

### 11. Runtime Configuration (v0.6.0 New)

**Responsibility**: Load and manage runtime configuration

**Components**:
- **Config Loader** (`rnconfig/loader.py`): YAML/JSON configuration loading

**Key Features**:
- `runicorn.yaml` support
- Environment variable overrides
- Default value fallbacks

---

### 12. Remote Viewer System (v0.5.0+, Enhanced in v0.6.0)

**Responsibility**: VSCode Remote-style remote access

**Components**:
- **Connection Manager**: SSH connection lifecycle management
- **Environment Detector**: Auto-discover remote Python environments
- **Viewer Launcher**: Start temporary Viewer on remote server
- **SSH Tunnel Manager**: Port forwarding and tunnel maintenance
- **Health Checker**: Connection and Viewer status monitoring

**v0.6.0 Enhancements**:
- **Multi-backend SSH Architecture**: OpenSSH → AsyncSSH → Paramiko fallback chain
- **Strict Host Key Verification**: Runicorn-managed known_hosts with 409 confirmation protocol
- **AutoBackend Selector**: Automatic best-backend selection

**Design Pattern**: Proxy pattern, Remote Procedure Call (RPC)

**Benefits**:
- ✅ No file sync needed, real-time remote data access
- ✅ Low latency, runs directly in remote environment
- ✅ Automatic environment detection and management
- ✅ Secure SSH tunnel communication
- ✅ Zero configuration, automatic cleanup

See **[SSH_BACKEND_ARCHITECTURE.md](SSH_BACKEND_ARCHITECTURE.md)** for detailed backend design.

---

## Data Storage Layout

```
user_root_dir/
├── runicorn.db                 # SQLite database
│   ├── experiments table       # Experiment metadata
│   ├── metrics table           # Metric data points
│   └── indexes                 # Performance indexes
│
├── artifacts/                  # Versioned assets
│   ├── model/
│   │   └── {name}/
│   │       ├── versions.json   # Version index
│   │       └── v{N}/           # Version directories
│   │           ├── metadata.json
│   │           ├── manifest.json
│   │           └── files/
│   └── .dedup/                 # Content dedup pool
│       └── {hash[:2]}/
│           └── {hash}/
│
└── {project}/                  # Experiment hierarchy
    └── {name}/
        └── runs/
            └── {run_id}/
                ├── meta.json
                ├── status.json
                ├── summary.json
                ├── events.jsonl
                ├── logs.txt
                └── media/
```

---

## Key Design Decisions

### Hybrid Storage (SQLite + Files)

**Decision**: Use both SQLite and file system

**Rationale**:
- SQLite excels at queries, aggregations, filtering
- Files excel at large blobs, human-readable logs
- Hybrid gets best of both worlds

**Trade-off**: Complexity of dual-write, but performance gain worth it

---

### Content Deduplication

**Decision**: SHA256-based deduplication with hard links

**Rationale**:
- ML models often share layers (pretrained weights)
- Hard links: zero-copy deduplication
- SHA256: secure, fast, collision-resistant

**Trade-off**: Cross-filesystem limitations, but 50-90% space savings

---

### Version Control (Not Git)

**Decision**: Custom versioning system for artifacts

**Rationale**:
- Git not designed for large binary files
- Git-LFS adds complexity and external dependencies
- Custom system: simpler, faster, better UX

**Trade-off**: No Git features, but optimized for ML workflow

---

## Performance Characteristics

### Query Performance

| Operation | V1 (Files) | V2 (SQLite) | Improvement |
|-----------|------------|-------------|-------------|
| List 100 exps | 500ms | 5ms | 100x |
| List 1000 exps | 5s | 50ms | 100x |
| Filter by project | 5s | 30ms | 167x |
| Complex query | N/A | 80ms | ∞ |

### Storage Efficiency

| Scenario | Without Dedup | With Dedup | Savings |
|----------|---------------|------------|---------|
| 10 model checkpoints | 10 GB | 1.5 GB | 85% |
| 100 similar models | 100 GB | 20 GB | 80% |

### Scalability Limits

| Metric | Tested | Practical Limit | Notes |
|--------|--------|-----------------|-------|
| Experiments | 100,000 | ~500,000 | V2 API required |
| Artifacts | 10,000 | ~50,000 | Dedup pool size |
| Metrics points | 10M | ~100M | Per experiment |
| Concurrent users | 100 | ~500 | SQLite WAL mode |

---

## System Constraints

### By Design

1. **Single-machine**: Not distributed (by choice for simplicity)
2. **Local-first**: Network is optional (for offline work)
3. **Python ecosystem**: Tightly integrated with ML tools

### Technical Limitations

1. **SQLite limitations**:
   - Single-writer at a time (WAL mode helps)
   - Not suitable for >1000 concurrent writes/sec
   - Database file can grow large (100MB+ for 100k experiments)

2. **File system limitations**:
   - Hard links require same filesystem/drive
   - Windows path length (260 chars, mitigated)
   - Case sensitivity varies by OS

3. **WebSocket limitations**:
   - Number of concurrent connections (OS dependent)
   - Browser limits (~6 connections per domain)

---

## Extension Points

### For Developers

**Plugin System** (planned):
- Custom storage backends
- Custom exporters
- Custom visualizations

**Hooks** (current):
- Environment capture: Pluggable
- Monitors: Optional monitoring hooks

---

## Comparison with Alternatives

### vs. Weights & Biases

| Aspect | W&B | Runicorn |
|--------|-----|----------|
| **Deployment** | Cloud (SaaS) | Self-hosted |
| **Privacy** | Data on W&B servers | 100% local |
| **Cost** | $50+/user/month | Free, open-source |
| **Setup** | Account required | `pip install` |
| **Performance** | Excellent | Excellent (V2 API) |
| **Collaboration** | Built-in | SSH sync |

### vs. MLflow

| Aspect | MLflow | Runicorn |
|--------|--------|----------|
| **Setup** | Moderate (server) | Easy (no server) |
| **Storage** | Various backends | SQLite + Files |
| **Version Control** | Model registry | Artifacts system |
| **Performance** | Good | Excellent (100x faster) |
| **Deduplication** | No | Yes (50-90% savings) |

### vs. TensorBoard

| Aspect | TensorBoard | Runicorn |
|--------|-------------|----------|
| **UI** | Basic | Modern (Ant Design) |
| **Comparison** | Limited | Full multi-run |
| **Versioning** | No | Built-in |
| **Status Tracking** | No | Auto-detect crashes |
| **Storage** | Event files | Hybrid optimized |

---

## Design Goals Achieved

✅ **Privacy**: Zero external calls, all data local  
✅ **Performance**: 100x faster queries (V2 API)  
✅ **Simplicity**: `pip install`, zero config  
✅ **Scalability**: Tested to 100,000 experiments  
✅ **Efficiency**: 50-90% storage savings  
✅ **Compatibility**: Python 3.8-3.13, Windows/Linux/macOS  
✅ **Extensibility**: Modular architecture  
✅ **Offline**: Fully functional without network  

---

## Architecture Evolution Achieved

### v0.6.0 (Current) ✅

- **Assets System**: SHA256 content-addressed storage with deduplication
  - Workspace snapshots with fingerprinting
  - Blob store for efficient storage
  - Manifest-based restore
- **Enhanced Logging**: Console capture and Python logging integration
  - TeeWriter for stdout/stderr capture
  - `get_logging_handler()` for Python logging
  - MetricLogger compatibility layer
  - Smart tqdm filtering
- **Path-based Hierarchy**: VSCode-style path tree navigation
  - PathTreePanel component
  - `/api/paths` endpoints
  - Batch operations (delete, export)
- **Inline Compare View**: Multi-run metric comparison
  - CompareChartsView with ECharts
  - Common metrics auto-detection
  - Visibility toggles
- **SSH Backend Architecture**: Multi-backend fallback chain
  - OpenSSH → AsyncSSH → Paramiko
  - Strict host key verification
  - 409 confirmation protocol
- **New Modules**: `assets/`, `console/`, `log_compat/`, `index/`, `workspace/`, `rnconfig/`

### v0.5.0 ✅

- **Remote Viewer**: VSCode Remote-style remote access
  - SSH tunnel + temporary Viewer instance
  - Automatic environment detection
  - Real-time data access without sync
- **Unified Remote API**: `/api/remote/*` endpoints
- **Connection Lifecycle Management**: Automatic cleanup and health monitoring

---

## Related Architecture Documents

- **[COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md)** - Detailed component design
- **[STORAGE_DESIGN.md](STORAGE_DESIGN.md)** - Storage layer deep dive
- **[DATA_FLOW.md](DATA_FLOW.md)** - How data flows through system
- **[DESIGN_DECISIONS.md](DESIGN_DECISIONS.md)** - Why we made these choices
- **[SSH_BACKEND_ARCHITECTURE.md](SSH_BACKEND_ARCHITECTURE.md)** - SSH backend design (v0.6.0)

---

## For More Information

- **API Specs**: See [../../api/](../../api/)
- **User Guides**: See [../../guides/](../../guides/)
- **Code**: See `src/runicorn/`

---

**Navigation**: [Architecture Docs Index](README.md) | [Main Docs](../../README.md)


