# Changelog

All notable changes to this project will be documented in this file.

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

