[English](REMOTE_STORAGE_USER_GUIDE.md) | [简体中文](../zh/REMOTE_STORAGE_USER_GUIDE.md)

---

> ⚠️  **Deprecated in v0.5.0**  
>
> The file-transfer-based remote sync feature described here was deprecated in v0.5.0.  
> Use **Remote Viewer** instead:
>
> - [Remote Viewer User Guide](REMOTE_VIEWER_GUIDE.md)
> - [Remote API Reference](../../api/en/remote_api.md)
> - [Remote Viewer Architecture](../../architecture/en/REMOTE_VIEWER_ARCHITECTURE.md)
> - [0.4.x → 0.5.0 Migration Guide](MIGRATION_GUIDE_v0.4_to_v0.5.md)

---

# Runicorn Remote Storage User Guide (Historical Reference)

## Historical summary

Remote Storage was an earlier remote-access model built around:

1. connecting to a remote machine over SSH
2. syncing metadata into a local cache
3. browsing cached artifacts locally
4. downloading files on demand when needed

That model is different from the current **Remote Viewer** product path. The current version is centered on `/api/remote/*` connection management, environment detection, known-host handling, saved connections, and viewer session lifecycle rather than a sync/cache/download-task model.

## Why it was replaced

The older model had several practical drawbacks:

- the user mental model was more complex because it mixed remote metadata, local cache, and on-demand downloads
- docs, UI, and background tasks tended to expand around sync state
- for the actual goal of real-time access to remote data, Remote Viewer is a more direct fit

For those reasons, the primary remote workflow moved to Remote Viewer in `v0.5.0`.

## Capabilities that existed in the historical design

The items below are preserved only to explain older terminology and design direction. They should not be read as proof that the current primary product surface still exposes them:

- remote metadata sync
- browsing artifacts from a local cache
- on-demand file downloads
- older local/remote mode switching
- cache management and download-task management
- several historical `/api/remote/*` design sketches

If you are trying to determine whether a route, button, or workflow exists in the current version, do not use this page as the source of truth. Use:

- [docs/api/en/remote_api.md](../../api/en/remote_api.md)
- [docs/architecture/en/REMOTE_VIEWER_ARCHITECTURE.md](../../architecture/en/REMOTE_VIEWER_ARCHITECTURE.md)

## Migration notes

If you previously used the older model, map it to the current product like this:

### Old goal: connect remotely and browse data

Use:

- the Remote Viewer page for connection setup
- saved connections for server/profile reuse
- `connect` and `viewer/start` for current-session setup

### Old goal: sync metadata and browse offline

Use:

- Remote Viewer as the default way to access remote data directly
- the current saved server / profile model when you need repeatable setup

### Old goal: depend on older remote-storage APIs

Use:

- the verified `/api/remote/*` routes documented in [../../api/en/remote_api.md](../../api/en/remote_api.md)
- the migration guide instead of treating historical remote-storage routes as active API reference

## What to read now

- User workflow: [REMOTE_VIEWER_GUIDE.md](REMOTE_VIEWER_GUIDE.md)
- API reference: [../../api/en/remote_api.md](../../api/en/remote_api.md)
- Architecture: [../../architecture/en/REMOTE_VIEWER_ARCHITECTURE.md](../../architecture/en/REMOTE_VIEWER_ARCHITECTURE.md)
- Migration context: [MIGRATION_GUIDE_v0.4_to_v0.5.md](MIGRATION_GUIDE_v0.4_to_v0.5.md)

## Scope

This page is retained only to help readers understand:

- why the term "Remote Storage" still appears in historical material
- where older users should migrate
- why the maintained documentation has moved to Remote Viewer

This page no longer serves as:

- current-version usage instructions
- current API reference
- current UI feature documentation

---

**Status**: Historical reference page  
**Current primary path**: Remote Viewer
