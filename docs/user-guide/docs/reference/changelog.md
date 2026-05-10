# Changelog

All notable changes to Runicorn.

## <span class="rn-badge">v0.7.1</span> — 2026-05-10

### Reliability and API alignment

- Metrics identity handling tightened to avoid overwrite risk in rapid-write cases
- Remote API surface and legacy path cleanup aligned to the current unified Remote Viewer model
- Remote API, architecture, and desktop build docs brought back into sync with the shipped implementation

### Security, CI, and desktop build hardening

- Legacy XOR credential migration boundary tightened
- Frontend smoke/baseline coverage expanded
- Desktop build configuration and sidecar packaging workflow made more reproducible

---

## <span class="rn-badge">v0.7.0</span> — 2026-03

### Remote Viewer hardening

- New remote wizard flow with clearer steps and progress feedback
- Faster environment probing and batched environment checks
- Saved server/profile workflow refined
- Health monitoring, reconnecting and degraded states, and cleaner Stop behavior
- OpenSSH password support and more predictable backend selection

### Web UI productization

- Professional default appearance and cleaner navigation
- Better path tree workflow for organizing and deleting runs
- Compare mode improvements, including URL-backed state and hover linking across charts
- ZIP export plus import preview with conflict detection
- Unified recycle-bin model for runs and folder-level delete flows

### Logs, themes, and monitoring

- Virtualized log rendering for large log streams
- Better dark-mode consistency and theme-aware dialogs
- Theme presets and surface color controls
- Backend-collected GPU telemetry history and improved performance page layout

### SDK and compatibility

- Logging compatibility expanded to ImageNet-style meters, TensorBoard, and tensorboardX
- Safer finish behavior and output watcher cleanup
- Stronger SQLite-backed indexing and migration behavior under the hood

### Desktop

- Current desktop build can open remote sessions in native windows
- External links can be opened in the system browser

---

## <span class="rn-badge">v0.6.0</span> — 2026-01-15

### 📦 New Assets System

- **NEW**: SHA256 content-addressed storage with automatic deduplication (50-90% space savings)
- **NEW**: `snapshot_workspace()` for capturing workspace state
- **NEW**: Blob storage with `store_blob()` and `get_blob_path()`
- **NEW**: `restore_from_manifest()` for workspace restoration
- **NEW**: `.rnignore` support for excluding files from snapshots
- **NEW**: `delete_run_completely()` and `cleanup_orphaned_blobs()` for cleanup

### 📝 Enhanced Logging

- **NEW**: Console capture with `capture_console=True` parameter
- **NEW**: `run.get_logging_handler()` for Python logging integration
- **NEW**: `MetricLogger` compatibility layer (from `runicorn.log_compat.torchvision`)
- **NEW**: Smart tqdm filtering with `tqdm_mode` parameter (smart/all/none)
- **IMPROVED**: Automatic log file format with timestamps

### 🌳 Path-based Hierarchy

- **NEW**: `PathTreePanel` component for VSCode-style navigation
- **NEW**: `/api/paths` endpoint for listing paths with statistics
- **NEW**: `/api/paths/tree` endpoint for tree structure
- **NEW**: `/api/paths/runs` endpoint for filtering runs by path
- **NEW**: `/api/paths/soft-delete` for batch soft deletion
- **NEW**: `/api/paths/export` for batch export

### 📊 Inline Compare View

- **NEW**: `CompareChartsView` component for multi-run metric comparison
- **NEW**: `CompareRunsPanel` with common metrics detection
- **NEW**: ECharts linked axis for synchronized zooming
- **IMPROVED**: Unified chart component for single and multi-run views

### 🔐 SSH Backend Architecture

- **NEW**: `AutoBackend` with fallback chain: OpenSSH → AsyncSSH → Paramiko
- **NEW**: Separation of connection (Paramiko) and tunneling (multi-backend)
- **NEW**: `RUNICORN_SSH_PATH` environment variable for custom SSH path
- **NEW**: Strict host key verification with 409 confirmation protocol
- **IMPROVED**: Better error handling and backend detection

### 🎨 Frontend Improvements

- **NEW**: LogsViewer with ANSI color support
- **NEW**: Line numbers in log viewer
- **NEW**: Search functionality in logs
- **IMPROVED**: Performance optimizations for large log files

---

## <span class="rn-badge">v0.5.3</span> — 2025-11-28

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

## <span class="rn-badge">v0.5.2</span> — 2025-11-25

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

## <span class="rn-badge">v0.5.1</span> — 2025-11-20

### 🐛 Bug Fixes & Minor Improvements

- **FIXED**: Chart rendering issues on experiment detail page
- **FIXED**: UI alignment problems in metric cards
- **IMPROVED**: Minor performance optimizations for frontend

---

## <span class="rn-badge">v0.5.0</span> — 2025-10-25

### 🚀 Major New Feature: Remote Viewer

**Revolutionary Architecture Change** - VSCode Remote Development-style remote server access.

#### Core Features

- **NEW**: Remote Viewer - Run Viewer on remote servers, access via SSH tunnel
- **NEW**: Real-time remote data access without file synchronization
- **NEW**: Zero local storage requirement - no need to mirror remote data
- **NEW**: Automatic Python environment detection (Conda/Virtualenv)
- **NEW**: SSH tunnel management with automatic port forwarding
- **NEW**: Full feature parity - all features work identically in remote and local modes

#### New API Endpoints

- `POST /api/remote/connect` - Establish SSH connection
- `GET /api/remote/connections` - List active connections
- `DELETE /api/remote/connections/{id}` - Disconnect
- `GET /api/remote/environments` - Detect Python environments
- `POST /api/remote/viewer/start` - Start remote Viewer
- `POST /api/remote/viewer/stop` - Stop remote Viewer
- `GET /api/remote/viewer/status` - Get Viewer status
- `GET /api/remote/health` - Connection health check

#### User Experience

- **NEW**: Remote connection wizard UI
- **NEW**: Environment selector with version display
- **NEW**: Active connection management panel
- **NEW**: Real-time connection status and health monitoring
- **IMPROVED**: Connection latency < 100ms (vs 5-10 min sync delay in 0.4.x)

#### Breaking Changes

- **DEPRECATED**: Old SSH file sync (`/api/ssh/*` endpoints)
- **DEPRECATED**: `ssh_sync.py` module - use new `remote/` module

---

## <span class="rn-badge">v0.4.0</span> — 2025-10-03

### 🎉 Artifacts (Model Versioning)

!!! warning "Deprecated in v0.6.0"
    The Artifacts API (`rn.Artifact`, `run.log_artifact`, `run.use_artifact`) has been replaced by the current assets workflow. See [Assets & Outputs](../sdk/assets-and-outputs.md) for the supported approach.

#### Core Features

- **NEW**: Complete Artifacts system for models and datasets
- **NEW**: `rn.Artifact()` class for creating versioned assets
- **NEW**: `run.log_artifact()` - Save with automatic versioning (v1, v2, v3...)
- **NEW**: `run.use_artifact()` - Load specific versions
- **NEW**: Alias system (latest, production, etc.)

#### Smart Storage

- **NEW**: Content deduplication via SHA256 hashing
- **NEW**: Hard-link optimization (50-90% space savings)
- **NEW**: Atomic writes to prevent corruption

#### Lineage Tracking

- **NEW**: Automatic dependency tracking
- **NEW**: Interactive lineage graph visualization
- **NEW**: Cycle detection

#### Web UI

- **NEW**: Artifacts management page
- **NEW**: Version history browser
- **NEW**: Storage statistics dashboard

---

## <span class="rn-badge">v0.3.1</span> — 2025-09-15

### Initial Release

- Basic experiment tracking
- Metrics logging and visualization
- Web viewer
- SSH file sync (deprecated in v0.5.0)

---

## Upgrade Guide

### From v0.4.x to v0.5.x

1. **Install latest version**:
   ```bash
   pip install -U runicorn
   ```

2. **Migrate from SSH sync to Remote Viewer**:
   - Old method: Configure SSH sync, wait for file transfer
   - New method: Connect via Remote page, view instantly

3. **Update any API integrations**:
   - `/api/ssh/*` endpoints are deprecated
   - Use `/api/remote/*` endpoints instead

---

<div align="center">
  <p><strong>Latest version: <span class="rn-badge">v0.7.1</span></strong></p>
  <p><code>pip install -U runicorn</code></p>
</div>
