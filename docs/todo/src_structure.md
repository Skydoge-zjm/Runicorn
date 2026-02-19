# Runicorn src 目录结构与职责文档

> 更新时间: 2026-02-19
> 基于分支: refactor/src-restructure
> 用途: 为后续开发提供完整的代码地图

---

## 总览

```
src/runicorn/                        # Python 后端 + SDK
├── __init__.py          # 包入口，导出公共 API
├── __main__.py          # python -m runicorn 入口
├── sdk.py               # 核心 SDK（Run 类）
├── cli.py               # CLI 命令行入口
├── enabled.py           # 全局开关 + NoOpRun
├── workspace.py         # 工作区检测（单文件）
├── VERSION.txt          # 版本号文件
│
├── config/              # 统一配置包（路径、用户配置、连接、限流、注册表、rnconfig）
├── client/              # SDK 端 API 客户端（原 api/）
├── assets/              # 资产管理
├── console/             # 控制台捕获
├── extensions/          # 可选扩展功能
├── storage/             # 存储层（文件 + SQLite 统一后端）
├── log_compat/          # ML 日志兼容层
├── remote/              # SSH 远程访问
├── security/            # 安全模块
├── viewer/              # Viewer Web 应用（FastAPI）
└── webui/               # 打包后的前端静态文件

web/frontend/src/                    # React 前端（TypeScript）
├── main.tsx             # ReactDOM 入口
├── App.tsx              # 根组件：路由、主题、布局
├── api.ts               # 主 API 客户端（fetch → /api/*）
├── i18n.ts              # i18next 国际化（中/英）
│
├── pages/               # 页面级组件（6 个路由页面）
├── components/          # 可复用 UI 组件
├── hooks/               # 自定义 React hooks
├── api/                 # 分模块 API 客户端
├── contexts/            # React Context
├── config/              # 前端配置（动画参数等）
├── types/               # TypeScript 类型定义
├── utils/               # 工具函数
├── styles/              # 样式/设计令牌
└── locales/             # 国际化翻译文件
```

---

## 一、顶层单文件

### `__init__.py`
- **职责**: 包入口，导出公共 API
- **导出**: `Run`, `init`, `get_active_run`, `get_config`, `enabled`, `is_enabled`, `set_enabled`, `reset_enabled`, `get_effective_rnconfig`, `snapshot_workspace`
- **版本号**: 从 `VERSION.txt` 读取，fallback 硬编码 `"0.6.0"`
- **可选导出**: 通过 try/except 从 `extensions/` 导入 `MetricMonitor`, `AnomalyDetector`, `AlertRule`, `ExperimentManager`, `ExperimentMetadata`, `MetricsExporter`, `EnvironmentCapture`, `EnvironmentInfo`
- **依赖**: `sdk`, `config.registry`, `config.rnconfig`, `enabled`, `assets`, `extensions`

### `__main__.py`
- **职责**: 允许 `python -m runicorn` 运行
- **实现**: 调用 `cli.main()`

### `sdk.py`
- **职责**: **核心模块**，`Run` 类的完整实现
- **功能**:
  - 创建 run 目录结构（`storage_root/runs/<path>/<run_id>/`）
  - 写入 `meta.json`, `status.json`, `events.jsonl`, `summary.json`
  - **双写**: 文件系统 + SQLite（当 `HAS_MODERN_STORAGE=True`），直接同步调用 `SQLiteStorageBackend`
  - `log()` 记录标量指标（自动步数管理）
  - `log_image()` 记录图片（支持 PIL Image, numpy array, 文件路径）
  - `log_text()` 记录文本日志
  - `log_config()` 记录训练配置（argparse args, config files, extra dict）
  - `log_dataset()` / `log_pretrained()` 记录数据集和预训练模型
  - `set_primary_metric()` 设置主指标跟踪（自动追踪 best value）
  - `scan_outputs_once()` / `watch_outputs()` 输出文件自动扫描归档
  - `summary()` 写入汇总信息
  - `finish()` 结束 run
  - 可选: `MetricMonitor`（loss 异常检测）、`AnomalyDetector`（基于统计的异常检测）、`EnvironmentCapture`（环境捕获）
  - 可选: `ConsoleCapture`（stdout/stderr 捕获，含 tqdm 智能处理）
  - `get_logging_handler()`: 返回 `RunicornLoggingHandler` 实例，将 Python logger 输出写入 run 的 `logs.txt`
  - 支持 context manager（`with Run(...) as run:`），异常时自动 `finish(status="failed")`
- **资产管理**: 通过 `SQLiteStorageBackend.record_asset_for_run()` 写入统一 DB（不再使用 IndexDb）
- **环境变量**:
  - `RUNICORN_DIR`: 覆盖默认存储根目录
  - `RUNICORN_DISABLE_MODERN_STORAGE`: 设为 `1`/`true`/`yes` 可禁用 SQLite 双写（用于测试）
- **可选依赖**: PIL（图片保存）、NumPy（数组→图片转换），通过 try/except 导入
- **依赖**: `config`（`get_user_root_dir`）, `enabled`, `workspace`, `assets`, `storage`（`SQLiteStorageBackend`, `ExperimentRecord`, `MetricRecord`）, `extensions`（可选）, `console`（可选）, `PIL`（可选）, `numpy`（可选）

### `cli.py`
- **职责**: CLI 命令行入口
- **子命令**:
  - `viewer`: 启动 FastAPI Viewer 服务（uvicorn）
  - `config`: 管理用户配置（show, set-user-root）
  - `export`: 导出 run 为 `.tar.gz`
  - `import`: 导入 `.zip/.tar.gz` 归档
  - `export-data`: 导出指标为 CSV/Excel/Markdown/HTML（调用 `extensions.exporters`）
  - `manage`: 实验管理（tag/search/delete/cleanup）（调用 `extensions.experiment`）
  - `rate-limit`: API 限流管理（show/list/get/set/remove/settings/reset/validate）
  - `delete`: 永久删除 run 及孤立资产
- **依赖**: `viewer`, `config`, `sdk`, `extensions`（延迟导入）, `security`

### `enabled.py`
- **职责**: 全局启用/禁用开关
- **机制**: `RUNICORN_ON` 环境变量 或 `set_enabled()` 编程控制
- **`NoOpRun`**: 禁用时的空实现替身，所有方法返回 None/空值，保证用户代码不需要 if/else
- **导出**: `is_enabled()`, `set_enabled()`, `reset_enabled()`, `enabled()` (context manager), `NoOpRun`

### `workspace.py`
- **职责**: 确定用户项目的工作区根目录（原 `workspace/` 包，已简化为单文件）
- **实现**: `get_workspace_root()`: 优先使用显式参数 → 向上查找 `.git` 目录 → fallback 到 `cwd`
- **被谁调用**: `sdk.py`, `config/rnconfig.py`

---

## 二、子包详情

### `config/` — 统一配置包

**职责**: 管理所有持久化配置的路径和读写。原 `config.py` + `rnconfig/` + `registry.py` + 数据目录 `config/` 统一合并为单一 Python 包。

**配置目录**: `%APPDATA%/Runicorn/`（Windows）、`~/Library/Application Support/Runicorn`（macOS）、`~/.config/runicorn`（Linux/XDG）

- `__init__.py` — 统一 re-export 所有公共符号，保持 `from runicorn.config import ...` 向后兼容
- `paths.py` — 跨平台配置路径解析：`_config_root_dir()`, `get_config_file_path()`, `get_rnconfig_file_path()`, `get_registry_dir()`, `get_connections_file_path()`, `get_known_hosts_file_path()`
- `user_config.py` — `config.json` 读写：`load_user_config()`, `save_user_config()`, `get_user_root_dir()`, `set_user_root_dir()`
- `connections.py` — SSH 连接配置管理（Fernet 加密存储于 `connections.json`）：`load_saved_connections()`, `save_connections()`, `get_ssh_connections()`, `save_ssh_connections()`, `add_ssh_connection()`, `remove_ssh_connection()`。内含自动迁移逻辑：首次读取时将 `config.json` 中 XOR 加密的遗留连接迁移到 Fernet
- `rate_limits.py` — 限流配置读写：`get_rate_limit_config()`, `save_rate_limit_config()`（三级优先级：用户目录 > 包内 `_defaults/` > 硬编码默认）
- `rnconfig.py` — 项目级 TOML 配置加载（原 `rnconfig/loader.py`）：读取用户级 + 项目级 `rnconfig.toml`，深度合并，mtime 缓存
- `registry.py` — TOML 配置注册表（原顶层 `registry.py`）：从 `%APPDATA%/Runicorn/registry/` 目录按 key 路径查找 `.toml` 文件
- `_toml.py` — 共享 TOML 加载工具：`load_toml()`, `load_toml_cached()`（mtime 缓存，线程安全），被 `registry.py` 和 `rnconfig.py` 共用
- `_defaults/rate_limits.json` — API 限流的打包默认配置

**依赖**: `security.encryption`（connections.py 加密解密）, `workspace`（rnconfig.py 查找项目根目录）

---

### `client/` — SDK 端 API 客户端（原 `api/`）

**职责**: 提供 Python 编程接口访问 Viewer REST API

- `__init__.py` — 导出 `RunicornClient`, `connect()`, 异常类, 数据模型（`RunInfo`, `MetricPoint`, `MetricSeries`, `RemoteSession`, `PathInfo`）。`Experiment` 和 `Project` 作为向后兼容别名保留
- `http.py` — `RunicornClient`（原 `client.py`）：HTTP 客户端，封装 GET/POST/PUT/DELETE，内置重试策略和错误处理。提供 `list_runs()`, `get_run()`, `get_metrics()`, `export_experiment()` 等高层方法
- `remote.py` — `RemoteAPI`: 远程 Viewer 操作（SSH 连接/断开、启动/停止远程 Viewer、列出会话、浏览远程目录）
- `models.py` — 客户端数据模型：`RunInfo`（原 `Experiment`）, `MetricPoint`, `MetricSeries`, `RemoteSession`, `PathInfo`（原 `Project`）
- `exceptions.py` — API 异常：`RunicornAPIError`, `ConnectionError`, `NotFoundError`, `BadRequestError`, `ServerError`, `AuthenticationError`
- `utils.py` — 客户端工具函数（均需 pandas）：`metrics_to_dataframe()`, `experiments_to_dataframe()`, `export_metrics_to_csv()`, `compare_runs()`

**与 viewer/api/ 的区别**: `client/` 是**客户端**（发 HTTP 请求），`viewer/api/` 是**服务端**（处理 HTTP 请求）

---

### `assets/` — 资产管理

**职责**: 管理 run 关联的所有文件资产（代码快照、输出文件、数据集、预训练模型等）

- `__init__.py` — 导出 `snapshot_workspace`
- `archive.py` — 文件/目录归档到 `storage_root/archive/` 目录，基于指纹去重（相同内容不重复存储）
- `assets_json.py` — 原子读写 `assets.json`（FileLock 保护），记录 run 关联的所有资产元数据
- `blob_store.py` — 二进制大对象存储（图片等媒体文件）
- `cleanup.py` — 孤立资产清理（删除不再被任何 run 引用的归档文件）
- `fingerprint.py` — 文件/目录指纹计算（用于去重和变更检测）
- `ignore.py` — 类 `.gitignore` 的排除规则（`.runicornignore`），控制快照和扫描范围
- `outputs_scan.py` — 输出文件扫描与自动归档：监控指定目录，检测新文件/变更文件，自动归档到 archive
- `restore.py` — 从归档恢复资产到指定目录
- `snapshot.py` — 工作区代码快照（zip 格式），尊重 ignore 规则

**被谁调用**: `sdk.py`（快照、输出扫描、资产记录）

---

### `console/` — 控制台捕获

**职责**: 拦截训练过程的 stdout/stderr 输出，写入 `logs.txt` 供 Viewer 实时显示

- `__init__.py` — 导出 `LogManager`, `TeeWriter`, `ConsoleCapture`, `RunicornLoggingHandler`
- `capture.py` — `TeeWriter`: 双写流（原始终端流 + 日志文件），支持 smart/all/none 三种 tqdm 处理模式；`ConsoleCapture`: 上下文管理器，替换 `sys.stdout`/`sys.stderr` 为 `TeeWriter`，注册 atexit 紧急恢复
- `log_manager.py` — `LogManager`: 线程安全的日志文件写入器，singleton-per-path 模式，每次写入立即 flush
- `logging_handler.py` — `RunicornLoggingHandler`: Python `logging.Handler` 子类，通过 `LogManager` 写入 run 的 `logs.txt`

**被谁调用**: `sdk.py`（`Run.__init__` 中 `capture_console=True` 时启用）

---

### `extensions/` — 可选扩展功能

**职责**: 非核心的增强功能，通过 try/except 可选加载，缺失时不影响核心功能

- `__init__.py` — 统一导出所有扩展类
- `monitors.py` — `MetricMonitor`: 检测 loss NaN/Inf、指标突变等异常；`AnomalyDetector`: 基于统计的异常检测；`AlertRule`: 告警规则定义
- `experiment.py` — `ExperimentManager`: 实验搜索/过滤/批量打标签/批量删除/清理过期 run。CLI `manage` 子命令的后端实现
- `exporters.py` — `MetricsExporter`: 将 run 指标导出为 CSV/Excel/Markdown/HTML 格式。CLI `export-data` 子命令的后端实现
- `environment.py` — `EnvironmentCapture`: 捕获完整运行环境信息（git commit/branch/dirty、pip/conda 包列表、GPU 信息、系统信息），写入 `environment.json`

**被谁调用**:
- `sdk.py`: `monitors`（指标检测）、`environment`（环境捕获）
- `cli.py`: `exporters`（export-data 命令）、`experiment`（manage 命令）
- `__init__.py`: 可选导出到包级 API

---

### `storage/` — 存储层

**职责**: 实验数据的持久化存储，统一 SQLite 后端 + 文件系统工具

- `__init__.py` — 统一导出：`StorageBackend`, `SQLiteStorageBackend`, `ExperimentRecord`, `MetricRecord`, `QueryParams`, `RunEntry`, `StorageMigrator`, 以及 file_utils 工具函数
- `file_utils.py` — **文件系统工具**（Viewer 读取端的 fallback 数据源）：`iter_all_runs()` 扫描目录发现所有 run；`read_json()` / `write_json()`；`is_process_alive()` 进程存活检查；`update_status_if_process_dead()` 自动标记崩溃 run；`soft_delete_run()` / `restore_run()` 软删除/恢复；`periodic_status_check()` 后台定期巡检（支持通过 `backend` 参数从 SQLite 获取 running 列表加速巡检）
- `backends.py` — **两个类**：`StorageBackend`（抽象接口 ABC）和 `SQLiteStorageBackend`（完整实现）。`SQLiteStorageBackend` 包含：连接池 `ConnectionPool`、WAL 模式、批量写入、Viewer 优化查询（`list_experiments_for_viewer`, `list_deleted_for_viewer`, `get_unique_paths`, `get_path_stats`, `get_running_experiments`, `experiment_exists`）、资产管理（`upsert_asset`, `link_run_asset`, `record_asset_for_run`, `get_assets_for_run`, `get_asset_ref_count`, `get_asset_by_fingerprint`）、标签管理（`set_tags`, `get_tags`）、`delete_run_with_orphan_assets()`
- `models.py` — 6 个数据模型：`ExperimentRecord`, `MetricRecord`, `QueryParams`, `EnvironmentRecord`, `StorageStats`, `MigrationStatus`
- `migration.py` — 存储迁移：`StorageMigrator`（通用后端间迁移）、`FilesToSQLiteMigrator`（文件→SQLite 批量迁移，含验证）、`FilesToSQLiteFileReader`（继承 `StorageBackend`，读取文件目录）；`detect_storage_type()`；`ensure_modern_storage()`；`migrate_index_to_unified()` 将 `index/runicorn.db` 数据迁入统一 `runicorn.db`
- `sql_utils.py` — SQL 安全工具：列名白名单验证（防 SQL 注入）
- `index_db.py` — **DEPRECATED**: 遗留索引数据库（`storage_root/index/runicorn.db`，含 `runs`/`assets`/`run_assets` 三表）。保留仅供迁移使用，新代码应使用 `SQLiteStorageBackend`
- `schema.sql` — SQLite 完整 DDL：7 张表（`experiments`, `metrics`, `experiment_tags`, `environments`, `experiment_files`, `query_cache`, `storage_stats`）+ 资产表（`assets`, `run_assets`）+ 3 个预计算视图 + 性能 PRAGMA

**架构说明**:
- **写入端** (`sdk.py`): 始终写文件 + 同步双写 SQLite（直接调用 `SQLiteStorageBackend`，无需 async 包装）
- **读取端** (`viewer/`): 优先通过 `SQLiteStorageBackend` 读取，fallback 到 `file_utils.py` 读文件
- **统一数据库**: `storage_root/runicorn.db`（含实验、指标、资产表）。遗留 `index/runicorn.db` 已弃用

---

### `log_compat/` — ML 日志兼容层

**职责**: 为常见 ML 框架提供 drop-in 替换的日志组件

- `__init__.py` — 导出 `MetricLogger`, `SmoothedValue`, `TorchvisionMetricLogger`
- `torchvision.py` — 替代 torchvision/DeiT 的 `MetricLogger`/`SmoothedValue`：完全兼容原始 API，额外自动将指标转发到 `runicorn.Run.log()`

**使用方式**: 用户将 `from torchvision.references.detection.utils import MetricLogger` 替换为 `from runicorn.log_compat.torchvision import MetricLogger`

---

### `remote/` — SSH 远程访问

**职责**: SSH 连接管理和远程 Viewer 功能的底层实现

- `__init__.py` — 导出 `SSHConnection`, `SSHConnectionPool`, `SSHConfig`
- `connection.py` — `SSHConfig` 数据类；`SSHConnection` SSH 连接封装（自动重连、keepalive、SFTP、命令执行）；`SSHConnectionPool` 连接池
- `ssh_backend.py` — SSH 后端抽象层：`SshBackend` ABC + 隧道实现（`OpenSSHTunnel`, `AsyncSSHTunnel`）+ `ParamikoBackend`/`OpenSSHBackend`/`AsyncSSHBackend`/`AutoBackend`
- `environment.py` — `RemoteEnvironmentDetector`: 远程 Python 环境自动检测
- `host_key.py` — SSH 主机密钥验证数据模型
- `known_hosts.py` — `KnownHostsStore`: OpenSSH known_hosts 文件管理（FileLock 保护）
- `viewer/__init__.py` — 导出 `RemoteViewerManager`
- `viewer/manager.py` — `RemoteViewerManager`: 管理远程 Viewer 会话生命周期
- `viewer/session.py` — 远程 Viewer 会话数据模型
- `viewer/tunnel.py` — SSH 隧道管理（端口转发）

**被谁调用**: `viewer/__init__.py`（初始化连接池和 RemoteViewerManager）、`viewer/api/remote.py`（API 路由）

---

### `security/` — 安全模块

**职责**: 提供加密、路径验证、限流等安全功能

- `__init__.py` — 主导出 `encrypt_password`, `decrypt_password`, `is_encrypted`, `SENSITIVE_FIELDS`；向后兼容导出 `CredentialManager`, `get_credential_manager`（已弃用）
- `encryption.py` — **主加密模块**: 基于 `cryptography.Fernet` 的对称加密，使用 `%APPDATA%/Runicorn/.secret.key`。`encrypt_password()` / `decrypt_password()` / `is_encrypted()`。`decrypt_password()` 支持三级解密优先级：Fernet → 遗留 XOR（`ENC:` 前缀）→ 明文直通。`SENSITIVE_FIELDS` 列表供 `config/connections.py` 使用
- `credentials.py` — **DEPRECATED**: 基于 XOR 混淆的遗留凭证加解密（`ENC:` 前缀）。仅供 `encryption.py` 的 `_try_decrypt_xor_legacy()` 迁移旧数据时调用，新代码不应直接使用
- `path_validation.py` — 路径安全验证：`validate_path()` 防目录遍历攻击；`sanitize_filename()` 文件名消毒；`create_safe_directory()` 安全创建目录
- `rate_limiter.py` — `RateLimiter`: 滑动窗口限流核心实现；`EndpointRateLimiter`: 按 endpoint 配置不同限流策略，支持 localhost 白名单

---

### `viewer/` — Viewer Web 应用（FastAPI）

**职责**: 提供实验数据的 Web 界面和 REST API

#### `viewer/__init__.py`
- `create_app()`: 创建并配置 FastAPI 应用
  - 初始化存储根目录
  - 配置 CORS
  - 添加限流中间件
  - 注册 13 个 API 路由
  - 初始化 `SQLiteStorageBackend` 实例，存入 `app.state.storage_backend`
  - startup: 启动后台状态巡检 + 在后台线程执行 `sync_filesystem_to_db()` 将文件系统 run 同步到 SQLite
  - shutdown: 取消后台任务、关闭 Remote Viewer 会话、关闭 SSH 连接池、关闭 `SQLiteStorageBackend`
  - 初始化 Remote Viewer 组件（SSH 连接池 + RemoteViewerManager）
  - 挂载静态前端（优先 `RUNICORN_FRONTEND_DIST` 或 `RUNICORN_DESKTOP_FRONTEND` 环境变量 → fallback `webui/` 目录）

#### `viewer/api/` — API 路由（服务端）

- `__init__.py` — 统一导出 13 个 router
- `health.py` — `/api/health` 健康检查
- `runs.py` — `/api/runs/*` run 列表/详情、alias&tags 更新、assets 获取/下载、软删除/回收站/永久删除
- `experiments.py` — `/api/experiments/*` 实验管理（tag/search/delete）
- `metrics.py` — 指标/日志：`/api/runs/{id}/metrics(_step)` 指标查询（增量缓存 + 可选 downsample）；`/api/metrics/cache/stats` 缓存统计；WS `/api/runs/{id}/logs/ws` 日志流
- `config.py` — `/api/config/*` 配置查询和修改
- `export.py` — `/api/export/*` 导出功能
- `import_.py` — `/api/import/*` 导入归档
- `projects.py` — `/api/projects/*` 项目列表
- `gpu.py` — `/api/gpu/*` GPU 信息
- `system.py` — `/api/system/*` 系统信息（CPU/内存/磁盘）
- `storage.py` — `/api/storage/*` 存储状态查询
- `remote.py` — `/api/remote/*` 远程 Viewer 操作
- `ui_preferences.py` — UI 偏好设置：列宽、dismissed alerts
- `listdir_cache.py` — 目录列表缓存
- `storage_utils.py` — 存储相关的 API 工具函数

**数据读取方式**: 路由通过 `viewer/services/db_reader.py` 优先从 SQLite 查询，fallback 到 `storage/file_utils.py` 读文件。

#### `viewer/services/` — 服务层

- `__init__.py` — 空
- `db_reader.py` — **Viewer 专用 SQLite 读取层**：`get_backend(request)` 从 app.state 获取后端；`find_run_entry_fast()` O(1) SQLite 查找 + O(n) 文件扫描 fallback；`list_runs_from_db()` 返回 Viewer 格式的 run 列表；`sync_filesystem_to_db()` 扫描文件系统将缺失 run 写入 SQLite 并同步 tags
- `gpu.py` — GPU 信息采集：调用 `nvidia-smi` 解析 CSV 输出
- `system_monitor.py` — 系统监控：CPU、内存/Swap、磁盘、Load Average

#### `viewer/middleware/` — 中间件

- `__init__.py` — 空
- `rate_limit.py` — `RateLimitMiddleware`: 调用 `security/rate_limiter.py` 执行限流检查

#### `viewer/utils/` — 工具函数

- `__init__.py` — 导出 `IncrementalMetricsCache`, `get_incremental_metrics_cache`
- `incremental_cache.py` — `IncrementalMetricsCache`: 增量指标缓存（只读取 events.jsonl 的新增部分，通过文件偏移量实现）
- `helpers.py` — 通用工具函数
- `logging.py` — Viewer 日志配置（`setup_logging()`）
- `validation.py` — 请求参数验证

---

### `webui/` — 前端静态文件

**职责**: 构建后的前端产物（HTML/CSS/JS），被 `viewer/__init__.py` 的 `_mount_static_frontend()` 挂载为 FastAPI 静态文件服务

---

## 二（续）、前端代码 `web/frontend/`

**技术栈**: React 18 + TypeScript + Vite + Ant Design 5 + ECharts + i18next

### 目录结构

```
web/frontend/src/
├── main.tsx              # ReactDOM 入口
├── App.tsx               # 根组件：路由、主题、布局、Settings
├── api.ts                # 主 API 客户端（fetch 封装，调用后端 /api/*）
├── i18n.ts               # i18next 国际化初始化（中/英）
├── vite-env.d.ts         # Vite 类型声明
│
├── pages/                # 页面级组件（路由对应）
├── components/           # 可复用 UI 组件
├── hooks/                # 自定义 React hooks
├── api/                  # 分模块 API 客户端
├── contexts/             # React Context
├── config/               # 前端配置（动画参数等）
├── types/                # TypeScript 类型定义
├── utils/                # 工具函数
├── styles/               # 样式/设计令牌
├── locales/              # 国际化翻译文件
└── runicorn/webui        # 构建输出符号链接
```

### 入口文件

- `main.tsx` — ReactDOM 渲染入口，包裹 BrowserRouter
- `App.tsx` — 根组件：6 条路由定义、Ant Design ConfigProvider（主题/暗色/紧凑模式）、SettingsProvider、背景效果、API 健康检查轮询、语言切换
- `api.ts` — 主 API 客户端：封装 fetch 调用后端 `/api/*`，约 20 个函数
- `i18n.ts` — i18next 初始化：支持中/英两种语言，浏览器语言自动检测，localStorage 缓存

### `pages/` — 页面

- `ExperimentPage.tsx` — `/` 主页：实验列表表格、路径树侧栏、搜索/过滤、批量操作、导出、对比模式、回收站、导入归档
- `RunDetailPage.tsx` — `/runs/:id` Run 详情：指标图表、日志查看器、资产列表、配置信息、环境信息
- `PerformanceMonitorPage.tsx` — `/performance` 硬件监控：CPU/内存/磁盘/GPU
- `RemoteViewerPage.tsx` — `/remote` 远程 Viewer 管理：SSH 连接向导、服务器列表、启动/停止远程 Viewer
- `AssetsPage.tsx` — `/assets` 资产浏览器：按类型分类、搜索、预览
- `AssetDetailPage.tsx` — `/assets/:id` 资产详情：代码/文本/图片预览、下载

### `components/` — 组件

**指标与图表**: `MetricChart.tsx`, `CompareChartsView.tsx`, `CompareRunsPanel.tsx`, `AutoResizeEChart.tsx`, `LazyChartWrapper.tsx`

**硬件监控**: `CpuDetailCard.tsx`, `MemoryDiskCard.tsx`, `GpuMetricsCard.tsx`, `GpuTelemetry.tsx`

**实验管理**: `PathTreePanel.tsx`, `AddTagModal.tsx`, `RecycleBin.tsx`, `ResizableTitle.tsx`

**Run 详情**: `LogsViewer.tsx`, `RunAssets.tsx`, `SystemInfoPanel.tsx`

**远程 Viewer**: `remote/RemoteConfigCard.tsx`, `remote/RemoteSessionCard.tsx`, `remote/HostKeyModal.tsx`, `remote/CondaEnvSelector.tsx`

**UI 基础**: `SettingsDrawer.tsx`, `LoadingSkeleton.tsx`, `DismissibleAlert.tsx`, `DismissedAlertsManager.tsx`, `animations/PageTransition.tsx`, `fancy/FancyMetricCard.tsx`, `fancy/FancyStatCard.tsx`, `fancy/CircularProgress.tsx`, `fancy/AnimatedStatusBadge.tsx`, `fancy/FancyEmpty.tsx`, `fancy/ServerStatusLight.tsx`, `fancy/ShimmerSkeleton.tsx`

**资产预览**: `assets/AssetPreview.tsx`, `assets/TextFilePreview.tsx`, `assets/code/CodeArchivePreview.tsx`, `assets/code/CodeTextViewer.tsx`

### `hooks/` — 自定义 Hooks

- `useSavedConnections.ts` — 管理已保存的 SSH 连接（CRUD + 状态）
- `useRemoteSessions.ts` — 管理远程 Viewer 会话（轮询状态）
- `useAssetsIndex.ts` — 资产索引查询
- `useColumnWidths.ts` — 表格列宽持久化
- `useSuccessConfetti.tsx` — 操作成功时的彩纸动画

### `api/` — 分模块 API 客户端

- `remote.ts` — Remote Viewer API 客户端
- `preferences.ts` — 用户偏好 API

### 其他目录

- `contexts/SettingsContext.tsx` — 全局 UI 设置的 React Context
- `types/remote.ts` — Remote Viewer 相关 TypeScript 类型定义
- `config/animation_config/` — 各页面/组件的动画参数配置
- `utils/format.ts`, `utils/logger.ts`, `utils/assetDownload.ts`, `utils/assetIdentity.ts`, `utils/assetParse.ts` — 工具函数
- `styles/designTokens.ts`, `styles/gradients.ts`, `styles/*.css` — 样式
- `locales/en/`, `locales/zh/` — 国际化翻译文件

---

## 三、已知问题

### 已解决（RF-01~RF-15）
1. ~~`config.py` 和 `config/` 同名~~ → `config.py` 已拆分并入 `config/` 包
2. ~~`api/`（客户端）和 `viewer/api/`（服务端）都叫 api~~ → 客户端已改名为 `client/`
3. ~~`viewer/api/modern/` 空目录~~ → 已删除
4. ~~`viewer/services/storage.py` 纯转发层~~ → 已删除
5. ~~`viewer/services/modern_storage.py` 未接入~~ → 已删除，替换为 `db_reader.py`
6. ~~`FileStorageBackend` / `HybridStorageBackend` 半成品~~ → 已删除，仅保留 `StorageBackend` ABC + `SQLiteStorageBackend`
7. ~~两套加密混用~~ → `encryption.py`（Fernet）为唯一主加密模块，`credentials.py` 仅保留供 XOR 遗留数据迁移

### 仍存在
8. **`storage/index_db.py` 遗留**: 已标记 DEPRECATED 但尚未物理删除，SDK 已不再使用（改用 `SQLiteStorageBackend` 的资产方法）。待确认无外部调用后可移除
9. **Viewer 读取仍有文件 fallback**: `db_reader.py` 优先 SQLite 但在 DB 为空或查询失败时退回文件扫描，长期目标是完全切到 SQLite
10. **`security/credentials.py` 待移除**: 仅用于 XOR→Fernet 迁移，一旦用户数据全部迁移完成可删除
