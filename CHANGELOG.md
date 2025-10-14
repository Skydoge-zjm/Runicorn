# Changelog

All notable changes to this project will be documented in this file.

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

