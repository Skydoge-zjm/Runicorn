[English](../en/ssh_api.md) | [简体中文](ssh_api.md)

---

# SSH/Remote API（历史弃用说明）

> ⚠️ **状态：历史接口，不再实现**
>
> `unified/*` 与 `ssh/*` 旧接口已经退出当前实现。该页面仅保留迁移背景，避免旧版本用户失去追溯信息。

- **当前有效远程 API**: [Remote Viewer API](./remote_api.md)
- **迁移指南**: [v0.4.x → v0.5.0 迁移指南](../../guides/zh/MIGRATION_GUIDE_v0.4_to_v0.5.md)
- **适用范围**: 仅用于理解旧版本命名，不应用作当前集成参考

---

## 历史背景

在 `v0.4.x` 时代，Runicorn 曾公开两组远程接口：

- `/api/unified/*`
- `/api/ssh/*`

自 `v0.5.0` 起，远程连接、会话管理与 Viewer 启动流程已经统一到：

- `/api/remote/*`

当前仓库中的前端主路径、后端路由与测试覆盖也都围绕 `remote/*` 组织。

---

## 旧接口映射

下表仅用于帮助旧调用方定位迁移目标，不代表旧端点仍可用。

| 旧接口前缀 | 当前去向 |
|------|------|
| `/api/unified/connect` | `POST /api/remote/connect` |
| `/api/unified/disconnect` | `POST /api/remote/disconnect` |
| `/api/unified/status` | `GET /api/remote/sessions`、`GET /api/remote/viewer/status/{session_id}` |
| `/api/unified/listdir` | `GET /api/remote/storage-candidates`、`GET /api/remote/config`（按当前工作流拆分） |
| `/api/unified/configure_mode` | `POST /api/remote/viewer/start` |
| `/api/unified/deactivate_mode` | `POST /api/remote/viewer/stop` |
| `/api/ssh/*` | 统一迁移到 `remote/*` 会话与 viewer 工作流 |

---

## 迁移建议

1. 不再调用 `/api/unified/*` 或 `/api/ssh/*`。
2. 前端集成改用 [remote_api.md](./remote_api.md) 对应的 `remote/*` 路由。
3. 如仍依赖旧概念模型，先参考迁移指南再调整请求与状态处理逻辑。

---

## 相关文档

- [Remote Viewer API](./remote_api.md)
- [Config API](./config_api.md)
- [v0.4.x → v0.5.0 迁移指南](../../guides/zh/MIGRATION_GUIDE_v0.4_to_v0.5.md)

---

**最后更新**: 2026-05-02
