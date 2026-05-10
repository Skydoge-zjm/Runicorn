[English](ssh_api.md) | [简体中文](../zh/ssh_api.md)

---

# SSH/Remote API (Historical Deprecation Note)

> ⚠️ **Status: historical interface, no longer implemented**
>
> The legacy `unified/*` and `ssh/*` endpoints are no longer part of the current implementation. This page is retained only for migration context and historical traceability.

- **Current remote API**: [Remote Viewer API](./remote_api.md)
- **Migration guide**: [v0.4.x → v0.5.0 Migration Guide](../../guides/en/MIGRATION_GUIDE_v0.4_to_v0.5.md)
- **Intended use**: historical reference only, not a source of current integration details

---

## Background

In the `v0.4.x` line, Runicorn exposed two remote API families:

- `/api/unified/*`
- `/api/ssh/*`

Since `v0.5.0`, remote connection, session management, and viewer startup have been consolidated under:

- `/api/remote/*`

The current frontend flow, backend routes, and test coverage are all organized around `remote/*`.

---

## Legacy-to-current mapping

This table exists only to help older integrations migrate. It does not imply the legacy routes are still callable.

| Legacy route | Current destination |
|------|------|
| `/api/unified/connect` | `POST /api/remote/connect` |
| `/api/unified/disconnect` | `POST /api/remote/disconnect` |
| `/api/unified/status` | `GET /api/remote/sessions`, `GET /api/remote/viewer/status/{session_id}` |
| `/api/unified/listdir` | `GET /api/remote/storage-candidates`, `GET /api/remote/config` (split across the current workflow) |
| `/api/unified/configure_mode` | `POST /api/remote/viewer/start` |
| `/api/unified/deactivate_mode` | `POST /api/remote/viewer/stop` |
| `/api/ssh/*` | Migrate to the `remote/*` session and viewer workflow |

---

## Migration guidance

1. Stop calling `/api/unified/*` and `/api/ssh/*`.
2. Move active integrations to [remote_api.md](./remote_api.md) and the `remote/*` routes it documents.
3. If older code still depends on the legacy mental model, use the migration guide before updating request/response handling.

---

## Related documents

- [Remote Viewer API](./remote_api.md)
- [Config API](./config_api.md)
- [v0.4.x → v0.5.0 Migration Guide](../../guides/en/MIGRATION_GUIDE_v0.4_to_v0.5.md)

---

**Last Updated**: 2026-05-02
