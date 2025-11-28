# Changelog

All notable changes to Runicorn.

---

## v0.5.3 - 2025-11-28

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

## v0.5.2 - 2025-11-25

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

## v0.5.1 - 2025-11-20

### 🐛 Bug Fixes & Minor Improvements

- **FIXED**: Chart rendering issues on experiment detail page
- **FIXED**: UI alignment problems in metric cards
- **IMPROVED**: Minor performance optimizations for frontend

---

## v0.5.0 - 2025-10-25

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

## v0.4.0 - 2025-10-03

### 🎉 Major New Feature: Artifacts (Model Versioning)

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

## v0.3.1 - 2025-09-15

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

See [Migration Guide](../../guides/MIGRATION_GUIDE_v0.4_to_v0.5.md) for details.

---

<div align="center">
  <p><strong>Latest version: v0.5.3</strong></p>
  <p><code>pip install -U runicorn</code></p>
</div>
