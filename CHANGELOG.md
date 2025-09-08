# Changelog

All notable changes to this project will be documented in this file.


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

