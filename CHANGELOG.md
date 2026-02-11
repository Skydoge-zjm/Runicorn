# Changelog

All notable changes to this project will be documented in this file.

## [0.6.0] - 2025-01

### 🚀 Major New Features

#### New Assets System
- **NEW**: SHA256 content-addressed storage with automatic deduplication (50-90% storage savings)
- **NEW**: `snapshot_workspace()` - Create workspace snapshots with `.rnignore` support
- **NEW**: Blob store for efficient content-addressed storage
- **NEW**: `restore_from_manifest()` - Restore any snapshot to its original state
- **NEW**: `archive_file()` / `archive_dir()` - Archive files with SHA256 deduplication
- **NEW**: `cleanup_orphaned_blobs()` - Clean up orphaned blobs
- **NEW**: New modules: `assets/`, `index/`, `workspace/`, `rnconfig/`
- **REMOVED**: Old `artifacts/` module (replaced by `assets/`)

#### Enhanced Logging System
- **NEW**: Console capture - Automatically capture all `print()` and logging output
- **NEW**: `capture_console=True` parameter for `rn.init()`
- **NEW**: tqdm handling modes: `"smart"` (recommended), `"all"`, `"none"`
- **NEW**: `run.get_logging_handler()` - Python logging integration
- **NEW**: `MetricLogger` compatibility layer - Drop-in replacement for torchvision's MetricLogger
- **NEW**: New modules: `console/`, `log_compat/`

#### Path-based Hierarchy
- **NEW**: Flexible path-based organization replacing rigid `project/name` structure
- **NEW**: `PathTreePanel` - VSCode-style tree navigation for experiments
- **NEW**: `GET /api/paths` - List all paths with optional statistics
- **NEW**: `GET /api/paths/tree` - Get hierarchical tree structure
- **NEW**: `GET /api/paths/runs` - Filter runs by path prefix
- **NEW**: `POST /api/paths/soft-delete` - Batch soft-delete runs by path
- **NEW**: `GET /api/paths/export` - Batch export runs by path
- **NEW**: Run count badges, search & filter, right-click menu, keyboard navigation

#### Inline Compare View
- **NEW**: Compare multiple experiments directly in the experiment list page
- **NEW**: `CompareChartsView` / `CompareRunsPanel` components
- **NEW**: Common metrics auto-detection (metrics shared by 2+ runs)
- **NEW**: Color-coded runs with ECharts linking (synchronized tooltip and zoom)
- **NEW**: Visibility toggle for individual runs or metrics
- **NEW**: Auto-refresh for running experiments

#### New SSH Backend Architecture
- **NEW**: Multi-backend fallback architecture for improved reliability
- **NEW**: `AutoBackend` class with fallback chain: OpenSSH → AsyncSSH → Paramiko
- **NEW**: Connection layer always uses Paramiko (`SSHConnection`)
- **NEW**: `OpenSSHTunnel` - Uses system OpenSSH client (preferred)
- **NEW**: `AsyncSSHTunnel` - Pure Python async implementation
- **NEW**: `SSHTunnel` (Paramiko) - Final fallback, always available
- **NEW**: Strict host key verification with Runicorn-managed known_hosts
- **NEW**: 409 confirmation protocol for unknown/changed host keys
- **NEW**: `RUNICORN_SSH_PATH` environment variable for custom SSH path
- **NEW**: New modules: `known_hosts.py`, `ssh_backend.py`, `host_key.py`

#### Frontend Improvements
- **NEW**: ANSI color support in LogsViewer
- **NEW**: Line numbers in log viewer
- **NEW**: Search functionality in logs with highlighting
- **NEW**: Auto-scroll follow mode for live logs
- **NEW**: Virtual scrolling for 100k+ lines

### 💥 Breaking Changes

#### API Changes
| Old API | New API | Notes |
|---------|---------|-------|
| `project` parameter | `path` parameter | Use path-based hierarchy |
| `name` parameter | `path` parameter | Combine into single path |
| `/api/projects` | `/api/paths` | New endpoint structure |
| `/api/projects/{p}/names` | `/api/paths/tree` | Tree structure |

#### Module Changes
| Removed | Replacement |
|---------|-------------|
| `artifacts/` module | `assets/` module |
| Old `project/name` fields | `path` field |

#### SDK Parameter Changes
```python
# Old (v0.5.x)
run = rn.init(project="cv", name="yolo")

# New (v0.6.0)
run = rn.init(path="cv/yolo")
```

### 🐛 Bug Fixes

- **FIXED**: WebSocket connection stability in Remote Viewer
- **FIXED**: Memory leak in long-running metric logging
- **FIXED**: tqdm output causing log file bloat
- **FIXED**: SSH tunnel reconnection issues
- **FIXED**: Path traversal vulnerability in file operations
- **FIXED**: Race condition in concurrent metric writes

### 📚 Documentation

- **NEW**: Enhanced Logging Guide
- **NEW**: Assets Guide
- **NEW**: SSH Backend Architecture documentation
- **NEW**: Paths API Reference
- **NEW**: Logging API Reference
- **UPDATED**: Quick Start Guide
- **UPDATED**: API Index
- **UPDATED**: System Overview

### ⚠️ Known Limitations

- Console capture starts after `rn.init()` - early prints may be missed
- Maximum path length: 200 characters
- OpenSSH backend requires `ssh` and `ssh-keyscan` in PATH
- Password authentication not supported with OpenSSH tunnel

### 🔄 Migration Guide

See [Release Notes v0.6.0](docs/releases/en/RELEASE_NOTES_v0.6.0.md) for detailed migration instructions.

---

## [0.5.3] - 2025-11-28

### ⚡ Frontend Performance & UI Improvements

#### Unified MetricChart Component
- **NEW**: Single `MetricChart` component handles both single-run and multi-run scenarios
- **REMOVED**: Separate `MultiRunMetricChart.tsx` (merged into unified component)
- **IMPROVED**: Consistent behavior across experiment detail and comparison views
- **IMPROVED**: Reduced bundle size through component consolidation

#### Performance Optimizations
- **NEW**: `LazyChartWrapper` with IntersectionObserver for lazy chart loading
- **NEW**: Pre-loading (200px) for smooth scrolling experience
- **NEW**: Advanced memo optimization using data fingerprints
- **IMPROVED**: O(1) comparison instead of deep equality for re-render prevention
- **IMPROVED**: Faster initial page load for pages with many charts

#### UI Beautification
- **NEW**: Fancy metric cards with enhanced styling
- **NEW**: Animated status badges for run status
- **NEW**: Circular progress components
- **IMPROVED**: Design tokens system for consistent styling

---

## [0.5.2] - 2025-11-25

### ⚡ Backend Performance Improvements

#### LTTB Downsampling
- **NEW**: LTTB (Largest-Triangle-Three-Buckets) algorithm for metrics downsampling
- **NEW**: `?downsample=N` parameter for `/metrics` and `/metrics_step` endpoints
- **IMPROVED**: Reduces large datasets (100k+ points → configurable target)
- **IMPROVED**: Preserves visual characteristics of data

#### Incremental Metrics Cache
- **NEW**: `IncrementalMetricsCache` for efficient metrics file parsing
- **NEW**: File-size based cache invalidation (vs mtime)
- **NEW**: Incremental reading from last known position
- **NEW**: LRU eviction strategy with configurable capacity
- **NEW**: `/metrics/cache/stats` endpoint for cache monitoring

#### Response Improvements
- **NEW**: Response headers (`X-Row-Count`, `X-Total-Count`, `X-Last-Step`)
- **NEW**: `total` and `sampled` fields in metrics response
- **IMPROVED**: Thread-safe operations for concurrent access

---

## [0.5.1] - 2025-11-20

### 🐛 Bug Fixes & Minor Improvements

- **FIXED**: Chart rendering issues on experiment detail page
- **FIXED**: UI alignment problems in metric cards
- **IMPROVED**: Minor performance optimizations for frontend

---

## [0.5.0] - 2025-10-25

### 🚀 Major New Feature: Remote Viewer

**Revolutionary Architecture Change** - Runicorn 0.5.0 introduces an all-new Remote Viewer feature with VSCode Remote Development-style architecture.

#### Core Features
- **NEW**: Remote Viewer - Run Viewer on remote servers, access via SSH tunnel
- **NEW**: Real-time remote data access without file synchronization
- **NEW**: Zero local storage requirement - no need to mirror remote data
- **NEW**: Automatic Python environment detection (Conda/Virtualenv)
- **NEW**: SSH tunnel management with automatic port forwarding
- **NEW**: Full feature parity - all features work identically in remote and local modes

#### Architecture
- **NEW**: `src/runicorn/remote/` module for remote connection management
- **NEW**: `viewer/api/remote.py` with 12 new API endpoints
- **NEW**: Environment detection and Viewer lifecycle management
- **NEW**: Secure SSH-based communication with key/password authentication

#### User Experience
- **NEW**: Remote connection UI with step-by-step wizard
- **NEW**: Environment selection interface showing detected Python environments
- **NEW**: Active connection management panel
- **NEW**: Real-time connection status and health monitoring
- **IMPROVED**: Connection latency < 100ms (vs 5-10 min sync delay in 0.4.x)
- **IMPROVED**: Initial setup time reduced from hours to seconds

#### Performance
- **IMPROVED**: No initial sync wait time (instant connection)
- **IMPROVED**: Zero local disk usage for remote data
- **IMPROVED**: Continuous small bandwidth usage vs large initial sync
- **IMPROVED**: Network efficiency optimized for remote operations

### 💥 Breaking Changes

- **DEPRECATED**: Old SSH file sync (`/api/ssh/*` endpoints) - replaced by Remote Viewer
- **DEPRECATED**: `ssh_sync.py` module - use new `remote/` module instead
- **CHANGED**: Remote configuration format - old `ssh_config.json` no longer used
- **MIGRATION REQUIRED**: Users of 0.4.x remote sync should migrate to Remote Viewer

**Migration Guide**: See [docs/guides/MIGRATION_GUIDE_v0.4_to_v0.5.md](docs/guides/MIGRATION_GUIDE_v0.4_to_v0.5.md)

### 🔌 New API Endpoints

#### Remote Viewer Management
- `POST /api/remote/connect` - Establish SSH connection
- `GET /api/remote/connections` - List active connections
- `DELETE /api/remote/connections/{id}` - Disconnect connection
- `GET /api/remote/environments` - Detect Python environments
- `POST /api/remote/environments/detect` - Re-detect environments
- `GET /api/remote/config` - Get remote configuration
- `POST /api/remote/viewer/start` - Start remote Viewer process
- `POST /api/remote/viewer/stop` - Stop remote Viewer
- `GET /api/remote/viewer/status` - Get Viewer status
- `GET /api/remote/viewer/logs` - Get Viewer logs
- `GET /api/remote/health` - Connection health check
- `GET /api/remote/ping` - Test connection

### 🎨 UI Improvements

- **NEW**: Remote page with connection wizard
- **NEW**: Environment selector with Python version and Runicorn version display
- **NEW**: Configuration review panel before starting Viewer
- **IMPROVED**: Better error messages and troubleshooting hints
- **IMPROVED**: Loading states and progress indicators

### 🐛 Bug Fixes

- **FIXED**: Memory leak in WebSocket connections
- **FIXED**: SSH connection timeout handling
- **FIXED**: Port conflict resolution for multiple connections
- **FIXED**: Remote Viewer process cleanup on disconnect
- **FIXED**: Environment detection for non-standard Python installations

### 📚 Documentation

- **NEW**: [Remote Viewer User Guide](docs/guides/REMOTE_VIEWER_GUIDE.md)
- **NEW**: [Remote Viewer Architecture](docs/architecture/REMOTE_VIEWER_ARCHITECTURE.md)
- **NEW**: [Migration Guide v0.4 to v0.5](docs/guides/MIGRATION_GUIDE_v0.4_to_v0.5.md)
- **NEW**: Complete Remote API documentation
- **UPDATED**: README with Remote Viewer quick start
- **UPDATED**: Installation instructions for remote setup

### ⚠️ Known Limitations

- Remote Viewer currently supports Linux remote servers only (Windows support planned)
- Requires stable SSH connection (recommended for LAN or good internet)
- Remote server must have Runicorn 0.5.0 installed
- Cascaded connections (A→B→C) limited to 2 levels for security

### 🔄 Upgrade Notes

**For existing users**:
1. Upgrade local Runicorn: `pip install -U runicorn`
2. Upgrade on remote server: `ssh user@server; pip install -U runicorn`
3. Old file sync tasks will continue to work but are deprecated
4. New installations should use Remote Viewer for remote access

**For new users**:
- Remote Viewer is the recommended way to access remote servers
- No setup required beyond installing Runicorn on both local and remote

---

## [0.4.0] - 2025-10-03

### 🎉 Major New Feature: Model & Data Versioning (Artifacts)

#### Core Features
- **Added**: Complete Artifacts system for model and dataset version control
- **Added**: `rn.Artifact()` class for creating versioned assets
- **Added**: `run.log_artifact()` for saving artifacts with automatic versioning
- **Added**: `run.use_artifact()` for loading specific artifact versions
- **Added**: Automatic version numbering (v1, v2, v3...)
- **Added**: Alias system (latest, production, etc.)

#### Smart Storage
- **Added**: Content deduplication based on SHA256 hashing
- **Added**: Hardlink optimization - identical files stored only once (save 50-90% space)
- **Added**: Dedup pool mechanism for intelligent content sharing
- **Added**: Atomic writes to prevent data corruption

#### Lineage Tracking
- **Added**: Automatic lineage tracking for artifact dependencies
- **Added**: LineageTracker for building complete dependency graphs
- **Added**: Cycle detection to prevent infinite recursion
- **Added**: Interactive lineage visualization with ECharts

#### Web UI
- **Added**: Artifacts management page with list, search, and statistics
- **Added**: Artifact detail page with version history, files, and metadata
- **Added**: Lineage graph visualization
- **Added**: Storage statistics panel showing dedup effectiveness

#### CLI Tools
- **Added**: `runicorn artifacts` command with actions: list, versions, info, delete, stats

#### API Endpoints
- **Added**: Full RESTful API for artifact management (7 endpoints)

#### Internationalization
- **Added**: 60+ translations for Artifacts features (Chinese & English)

### 🔧 Code Quality Improvements

#### Performance
- **Added**: Metrics caching - 10-20x faster API responses
- **Improved**: Process status checking - 4-10x faster list loading
- **Added**: Recursion depth limits

#### Refactoring
- **Refactored**: Dedup function split into single-responsibility functions
- **Added**: Atomic JSON writes
- **Added**: Cycle detection with visited sets

#### Security
- **Added**: Triple-layer path traversal protection
- **Added**: Input validation for run_id, batch_size, version numbers
- **Added**: Path length checking for Windows compatibility

#### User Experience
- **Improved**: Unified design system with designTokens
- **Improved**: Chart controls layout with auto-wrapping
- **Added**: Skeleton screen loading states
- **Improved**: More informative error messages

#### Code Cleanup
- **Removed**: All console.log statements
- **Added**: React.memo optimization
- **Fixed**: WebSocket memory leak

### 🐛 Bug Fixes
- **Fixed**: SDK async call confusion causing potential data loss
- **Fixed**: Stage line overlapping with legend
- **Fixed**: Text overlap in multi-column mode
- **Fixed**: Windows file lock issues with SQLite
- **Fixed**: 31+ other architecture, security, and performance issues

### 📚 Documentation
- **Added**: `docs/ARTIFACTS_GUIDE.md` - Complete Artifacts user guide
- **Added**: `examples/user_workflow_demo.py` - Full workflow demonstration
- **Added**: `examples/realistic_ml_project/` - Real project example
- **Added**: `tests/TESTING_GUIDE.md` - Testing guide
- **Added**: 35+ test cases

### ⚠️ Known Limitations
- Windows test cleanup may fail (doesn't affect functionality)
- Cross-drive hardlinks fallback to copy (recommend same drive)
- Windows path length limit (~240 characters)

---

## [0.3.1] - 2025-09-26

### 🏗️ Architecture Modernization

#### Code Refactoring
- **NEW**: Modular architecture - viewer.py split into focused modules for better maintainability
- **NEW**: Service layer abstraction for business logic separation
- **NEW**: Enhanced error handling and logging throughout the system

#### High-Performance Storage System  
- **NEW**: SQLite + file hybrid storage architecture for 10x+ query performance improvement
- **NEW**: Automatic migration from file-only to hybrid storage
- **NEW**: Advanced query capabilities with filtering, pagination, and search
- **NEW**: V2 API endpoints (`/api/v2/experiments`, `/api/v2/analytics`) for enhanced performance
- **NEW**: Real-time analytics and system health monitoring

#### Developer Experience
- **NEW**: `rn.log_text()` module-level API for consistent text logging
- **NEW**: Backward compatibility maintained - existing code works unchanged
- **NEW**: Enhanced WebSocket log streaming with full content support

## [0.3.0] - 2025-09-25

### 🎯 Major Features Added

#### Universal Best Metric System
- **NEW**: `rn.set_primary_metric(metric_name, mode="max|min")` - Set any metric as primary indicator
- **NEW**: Automatic tracking of best values during training
- **NEW**: Best metric display in experiment list with metric name and value

#### Soft Delete & Recycle Bin
- **NEW**: Safe experiment deletion - files preserved, can be restored
- **NEW**: Recycle bin interface for managing deleted experiments
- **NEW**: Batch restore and permanent deletion capabilities
- **NEW**: `.deleted` marker files for soft delete implementation

#### Smart Status Detection
- **NEW**: Automatic detection of crashed/interrupted experiments
- **NEW**: Process liveness checking using `psutil`
- **NEW**: Background status checking task (30-second intervals)
- **NEW**: Manual status check button in web interface
- **NEW**: Support for `interrupted` status (Ctrl+C handling)

### 🎨 Interface & UX Improvements

#### Settings Interface
- **NEW**: Tabbed settings interface (Appearance/Layout/Data/Performance)
- **NEW**: Live preview for colors, backgrounds, and effects
- **NEW**: Comprehensive customization options
- **NEW**: Performance settings (auto-refresh intervals, chart heights)

#### Responsive Design Enhancement
- **NEW**: Adaptive chart layouts for different screen sizes
- **NEW**: Smart column switching based on window width
- **IMPROVED**: Chart title positioning to prevent overlap



## [0.2.7] - 2025-09-17

### Added
- Language options:
  - Support switching between Chinese and English.


## [0.2.6] - 2025-09-14

### Added
- Remote (SSH live sync) in the UI and backend.
  - New "Remote" menu in the UI to connect over SSH, browse remote directories, and start/stop a live mirror from a Linux server into your local storage.
  - APIs: `POST /api/ssh/connect`, `GET /api/ssh/listdir`, `POST /api/ssh/mirror/start`, `POST /api/ssh/mirror/stop`, `GET /api/ssh/mirror/list`.
- Docs: Clarified that the web uploader for offline import (uploading `.zip`/`.tar.gz` in the UI) requires the optional dependency `python-multipart`, with install instructions.

### Changed
- Viewer: Even if `python-multipart` is not installed, the server now starts; only the upload endpoint returns `503` with an actionable hint.
- Desktop (Windows): Improved startup robustness and user experience (no user action required).


## [0.2.1] - 2025-09-09

### Fixed
- Desktop/Backend: `POST /api/config/user_root_dir` now correctly parses JSON body (no longer treated as query params).
- Better error handling and messages when setting the data directory (path validation, immediate storage re-init).
- Windows: expand environment variables in paths (e.g., `%USERPROFILE%`).
- Avoided CWD fallback by re-initializing storage with the newly set path explicitly.
- Added lightweight server debug log at [%APPDATA%/Runicorn/server_debug.log](cci:1://file:///e:/pycharm_project/Runicorn/src/runicorn/sdk.py:287:0-292:62).

### Changed
- Build: [desktop/tauri/build_release.ps1](cci:7://file:///e:/pycharm_project/Runicorn/desktop/tauri/build_release.ps1:0:0-0:0) now syncs [web/frontend/dist](cci:7://file:///e:/pycharm_project/Runicorn/web/frontend/dist:0:0-0:0) into [src/runicorn/webui](cci:7://file:///e:/pycharm_project/Runicorn/src/runicorn/webui:0:0-0:0) before sidecar build to ship latest UI.
- Docs: Added Desktop app instructions and Settings → Data Directory flow in both READMEs.

### Desktop
- NSIS installer (Tauri) bundles the sidecar backend and launches it automatically. First run lets users choose a writable data directory.

## [0.2.0] - 2025-09-08

### Added
- Per-user storage root with project/name hierarchy: `user_root_dir/<project>/<name>/runs/<run_id>/...`.
- New CLI command: `runicorn config` to set and inspect the global `user_root_dir`.
- Viewer APIs for hierarchy discovery:
  - `GET /api/projects`
  - `GET /api/projects/{project}/names`
  - `GET /api/projects/{project}/names/{name}/runs`
- Frontend features:
  - Project/Name filters on runs list page.
  - Compare runs overlay on the run detail page (select multiple runs and metrics to plot together).

### Changed
- `runicorn viewer` now defaults to global user config if `--storage` is not provided, then falls back to `./.runicorn`.
- Existing `/api/runs` and `/api/runs/{id}` responses now include `project` and `name` fields.

### Compatibility
- Legacy layout `./.runicorn/runs/<run_id>/` remains fully supported by the viewer.

## [0.1.x]
- Initial public versions with local, read-only viewer, step/time metrics, live logs via WebSocket, and optional GPU telemetry.

