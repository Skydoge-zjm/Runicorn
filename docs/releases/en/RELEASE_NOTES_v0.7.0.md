# Release Notes v0.7.0

**Release date**: 2026-03

---

## Summary

Runicorn v0.7.0 is the release line that follows v0.6.0. Compared with the 0.6.0 release, the current development branch focuses on three themes:

1. hardening Remote Viewer for long-running real use
2. turning the Web UI into a more polished day-to-day product
3. expanding compatibility with common training and logging patterns

---

## Highlights

### Remote Viewer

- New modal-based remote wizard with clearer staged flow
- Faster environment discovery and batched Runicorn checks
- Host key confirmation in the UI
- Health monitoring and reconnect-aware session states
- Better Stop behavior and SSH cleanup
- OpenSSH password authentication support

### Web UI

- Cleaner professional default theme
- Better path tree workflow and folder operations
- URL-backed compare mode and stronger comparison UX
- ZIP export and import preview with conflict detection
- Unified recycle-bin behavior
- Better dark-mode consistency and dialog theming

### Logs, themes, and monitoring

- Virtualized log rendering for large jobs
- Better logs layout and auto-scroll behavior
- Theme presets and surface-color controls
- Backend-collected GPU telemetry history

### SDK and logging compatibility

- ImageNet-style meter compatibility
- TensorBoard SummaryWriter compatibility
- tensorboardX compatibility
- Safer finish and output-watcher behavior

### Desktop

- Native windows for remote sessions in the current desktop build
- External links can open in the system browser

---

## Upgrade notes

### If you are coming from v0.6.0

The biggest user-facing differences are:

- Remote Viewer is more feature-complete and resilient
- the experiments page, compare flow, import/export flow, and recycle-bin model have changed
- settings and theming are more extensive
