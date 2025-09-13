# 更新日志

记录本项目的所有重要变更。

## [0.2.6] - 2025-09-14

### 新增
- 远程同步（SSH 实时镜像）：
  - UI 新增「Remote」菜单，可通过 SSH 连接远程 Linux 服务器、浏览目录，并启动/停止将远程 runs 实时镜像到本地存储。
  - 新增后端接口：`POST /api/ssh/connect`、`GET /api/ssh/listdir`、`POST /api/ssh/mirror/start`、`POST /api/ssh/mirror/stop`、`GET /api/ssh/mirror/list`。
- 文档：明确“离线导入（UI 上传 .zip/.tar.gz）需要可选依赖 `python-multipart`”，并提供安装指引。

### 变更
- Viewer：即使未安装 `python-multipart`，服务也能正常启动；仅当调用“离线导入”接口时返回 `503` 并提示安装依赖。
- 桌面端（Windows）：提升启动鲁棒性与使用体验（无需用户手动干预）。

## [0.2.1] - 2025-09-09

### 修复
- 后端：`POST /api/config/user_root_dir` 正确解析 JSON body；设置数据目录时的错误提示更友好，并在设置后立即生效。
- Windows：支持在路径中展开环境变量（例如 `%USERPROFILE%`）。
- 增加轻量服务调试日志（写入 `%APPDATA%/Runicorn/server_debug.log`）。

### 变更
- 构建：`desktop/tauri/build_release.ps1` 在构建 sidecar 前会同步 `web/frontend/dist` 到 `src/runicorn/webui`，以携带最新 UI。
- 文档：新增桌面应用使用说明及“设置 → 数据目录”流程。

### 桌面端
- NSIS 安装器（Tauri）集成并自动启动本地后端。首次运行可在设置中选择可写的数据目录。

## [0.2.0] - 2025-09-08

### 新增
- 用户级存储根与项目/实验层级：`user_root_dir/<project>/<name>/runs/<run_id>/...`。
- 新增 CLI：`runicorn config` 用于设置与查看全局 `user_root_dir`。
- Viewer 层级发现 API：
  - `GET /api/projects`
  - `GET /api/projects/{project}/names`
  - `GET /api/projects/{project}/names/{name}/runs`
- 前端：
  - 运行列表增加 Project/Name 筛选。
  - 运行详情支持同一实验的多次运行叠加展示（多曲线对比）。

### 变更
- `runicorn viewer` 在未显式传入 `--storage` 时，优先使用全局用户配置，其次回退到 `./.runicorn`。
- `/api/runs` 与 `/api/runs/{id}` 响应增加 `project` 与 `name` 字段。

### 兼容性
- 保持对旧版目录结构 `./.runicorn/runs/<run_id>/` 的兼容。

## [0.1.x]
- 初始公开版本：本地只读 Viewer、步/时间指标、实时日志（WebSocket）、可选 GPU 面板。
