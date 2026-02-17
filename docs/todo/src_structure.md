# Runicorn src 目录结构与职责文档

> 生成时间: 2026-02-16
> 基于分支: refactor/code-cleanup
> 用途: 为后续重构工作提供完整的代码地图

---

## 总览

```
src/runicorn/                        # Python 后端 + SDK
├── __init__.py          # 包入口，导出公共 API
├── __main__.py          # python -m runicorn 入口
├── sdk.py               # 核心 SDK（Run 类）
├── cli.py               # CLI 命令行入口
├── config.py            # 用户配置中心
├── enabled.py           # 全局开关 + NoOpRun
├── registry.py          # TOML 配置注册表
├── VERSION.txt          # 版本号文件
│
├── assets/              # 资产管理
├── console/             # 控制台捕获
├── extensions/          # 可选扩展功能
├── storage/             # 存储层（文件 + SQLite）
├── index/               # 轻量索引数据库
├── config/              # 数据目录（非 Python 包）
├── rnconfig/            # 项目级配置加载器
├── log_compat/          # ML 日志兼容层
├── workspace/           # 工作区检测
├── api/                 # SDK 端 API 客户端
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
- **依赖**: `sdk`, `registry`, `enabled`, `rnconfig`, `assets`, `extensions`

### `__main__.py`
- **职责**: 允许 `python -m runicorn` 运行
- **实现**: 调用 `cli.main()`

### `sdk.py`
- **职责**: **核心模块**，`Run` 类的完整实现
- **功能**:
  - 创建 run 目录结构（`storage_root/runs/<path>/<run_id>/`）
  - 写入 `meta.json`, `status.json`, `events.jsonl`, `summary.json`
  - **双写**: 文件系统 + SQLite（当 `HAS_MODERN_STORAGE=True`）
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
- **环境变量**:
  - `RUNICORN_DIR`: 覆盖默认存储根目录
  - `RUNICORN_DISABLE_MODERN_STORAGE`: 设为 `1`/`true`/`yes` 可禁用 SQLite 双写（用于测试）
- **可选依赖**: PIL（图片保存）、NumPy（数组→图片转换），通过 try/except 在第 59-73 行导入
- **关键路径**:
  - 第 31-39 行: modern storage import（SQLite 双写）
  - 第 42-56 行: extensions import（monitors, environment）
  - 第 176-378 行: `Run.__init__()`（含 console capture 初始化）
  - 第 475-505 行: `_init_modern_storage()`
  - 第 525-610 行: `log()`（含 modern storage 双写 + monitoring 异常检测）
  - 第 970-1071 行: `finish()`（停止 console capture → 关闭 index → 写 best metric → 更新状态 → 关闭 storage backend → flush 磁盘）
- **依赖**: `config`, `enabled`, `workspace`, `assets`, `index`, `storage`, `extensions`（可选）, `console`（可选）, `PIL`（可选）, `numpy`（可选）

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
- **关键路径**:
  - 第 14 行: `from .viewer import create_app`
  - 第 287 行: `from .extensions.exporters import MetricsExporter`
  - 第 317 行: `from .extensions.experiment import ExperimentManager`
- **依赖**: `viewer`, `config`, `sdk`, `extensions`（延迟导入）, `security`

### `config.py`
- **职责**: **用户配置中心**，管理所有持久化配置的路径和读写
- **配置目录**: `%APPDATA%/Runicorn/`（Windows）、`~/Library/Application Support/Runicorn`（macOS）、`~/.config/runicorn`（Linux/XDG）
- **管理的文件**:
  - `config.json`: 用户根目录 (`user_root_dir`) 等
  - `connections.json`: SSH 连接配置（密码加密存储）
  - `known_hosts`: SSH 已知主机
  - `rnconfig.toml`: 用户级 rnconfig
  - `rate_limits.json`: API 限流配置
  - `registry/`: TOML 注册表目录
  - `.credential_key` / `.secret.key`: 加密密钥
- **功能**:
  - `get_config_file_path()` / `load_user_config()` / `save_user_config()`: JSON 配置读写
  - `get_user_root_dir()` / `set_user_root_dir()`: 存储根目录管理
  - `load_saved_connections()` / `save_connections()`: SSH 连接加解密存储
  - `get_rate_limit_config()` / `save_rate_limit_config()`: 限流配置（三级优先级: 用户目录 > 包内 config/ > 硬编码默认）
  - `save_ssh_connections()` / `get_ssh_connections()` / `add_ssh_connection()` / `remove_ssh_connection()`: SSH 连接 CRUD
- **依赖**: `security.encryption`, `security.credentials`

### `enabled.py`
- **职责**: 全局启用/禁用开关
- **机制**: `RUNICORN_ON` 环境变量 或 `set_enabled()` 编程控制
- **`NoOpRun`**: 禁用时的空实现替身，所有方法返回 None/空值，保证用户代码不需要 if/else
- **导出**: `is_enabled()`, `set_enabled()`, `reset_enabled()`, `enabled()` (context manager), `NoOpRun`

### `registry.py`
- **职责**: TOML 配置注册表
- **机制**: 从 `%APPDATA%/Runicorn/registry/` 目录下按 key 路径（如 `"model/lr"`）查找对应 `.toml` 文件，读取 `value` 字段
- **特性**: 带 mtime 缓存，文件变更自动刷新
- **依赖**: `config`（获取 registry 目录路径）

---

## 二、子包详情

### `assets/` — 资产管理

**职责**: 管理 run 关联的所有文件资产（代码快照、输出文件、数据集、预训练模型等）

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出 `snapshot_workspace` |
| `archive.py` | 文件/目录归档到 `storage_root/archive/` 目录，基于指纹去重（相同内容不重复存储） |
| `assets_json.py` | 原子读写 `assets.json`（FileLock 保护），记录 run 关联的所有资产元数据 |
| `blob_store.py` | 二进制大对象存储（图片等媒体文件） |
| `cleanup.py` | 孤立资产清理（删除不再被任何 run 引用的归档文件） |
| `fingerprint.py` | 文件/目录指纹计算（用于去重和变更检测） |
| `ignore.py` | 类 `.gitignore` 的排除规则（`.runicornignore`），控制快照和扫描范围 |
| `outputs_scan.py` | 输出文件扫描与自动归档：监控指定目录，检测新文件/变更文件，自动归档到 archive |
| `restore.py` | 从归档恢复资产到指定目录 |
| `snapshot.py` | 工作区代码快照（zip 格式），尊重 ignore 规则 |

**被谁调用**: `sdk.py`（快照、输出扫描、资产记录）

---

### `console/` — 控制台捕获

**职责**: 拦截训练过程的 stdout/stderr 输出，写入 `logs.txt` 供 Viewer 实时显示

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出 `LogManager`, `TeeWriter`, `ConsoleCapture`, `RunicornLoggingHandler` |
| `capture.py` | `TeeWriter`: 双写流（原始终端流 + 日志文件），支持 smart/all/none 三种 tqdm 处理模式（smart 模式缓冲 `\r` 行仅写最终版本）；`ConsoleCapture`: 上下文管理器，替换 `sys.stdout`/`sys.stderr` 为 `TeeWriter`，注册 atexit 紧急恢复防止异常退出时丢失原始流 |
| `log_manager.py` | `LogManager`: 线程安全的日志文件写入器，singleton-per-path 模式（按文件路径复用实例 + 引用计数），每次写入立即 flush 支持 Viewer 实时流式查看 |
| `logging_handler.py` | `RunicornLoggingHandler`: Python `logging.Handler` 子类，通过 `LogManager` 写入 run 的 `logs.txt`；支持懒初始化（无 Run 时静默丢弃）、自定义格式、自动回退到 `get_active_run()` |

**被谁调用**: `sdk.py`（`Run.__init__` 中 `capture_console=True` 时启用）

---

### `extensions/` — 可选扩展功能

**职责**: 非核心的增强功能，通过 try/except 可选加载，缺失时不影响核心功能

| 文件 | 职责 |
|------|------|
| `__init__.py` | 统一导出所有扩展类 |
| `monitors.py` | `MetricMonitor`: 检测 loss NaN/Inf、指标突变等异常；`AnomalyDetector`: 基于统计的异常检测；`AlertRule`: 告警规则定义 |
| `experiment.py` | `ExperimentManager`: 实验搜索/过滤/批量打标签/批量删除/清理过期 run。CLI `manage` 子命令的后端实现 |
| `exporters.py` | `MetricsExporter`: 将 run 指标导出为 CSV/Excel/Markdown/HTML 格式。CLI `export-data` 子命令的后端实现 |
| `environment.py` | `EnvironmentCapture`: 捕获完整运行环境信息（git commit/branch/dirty、pip/conda 包列表、GPU 信息、系统信息），写入 `environment.json` |

**被谁调用**:
- `sdk.py`: `monitors`（指标检测）、`environment`（环境捕获）
- `cli.py`: `exporters`（export-data 命令）、`experiment`（manage 命令）
- `__init__.py`: 可选导出到包级 API

---

### `storage/` — 存储层

**职责**: 实验数据的持久化存储，支持文件和 SQLite 两种后端

| 文件 | 职责 |
|------|------|
| `__init__.py` | 统一导出所有存储组件 |
| `file_utils.py` | **文件系统工具**（当前 Viewer 读取端的实际数据源）：`iter_all_runs()` 扫描目录发现所有 run（支持新旧两种目录布局）；`read_json()` / `write_json()`；`is_process_alive()` 进程存活检查（使用 psutil）；`update_status_if_process_dead()` 自动标记崩溃 run；`soft_delete_run()` / `restore_run()` 软删除/恢复；`periodic_status_check()` 后台定期巡检 |
| `backends.py` | **三种存储后端实现**: `StorageBackend`（抽象接口）→ `FileStorageBackend`（文件实现，半成品，多个方法返回空）、`SQLiteStorageBackend`（完整实现，含连接池 `ConnectionPool`、WAL 模式、批量写入）、`HybridStorageBackend`（组合双写，读取优先 SQLite） |
| `models.py` | 6 个数据模型：`ExperimentRecord`（实验元数据，含 path 层级、别名、best metric 追踪、软删除支持）、`MetricRecord`（指标数据点，含 step/stage）、`QueryParams`（查询参数，支持 path 前缀/精确匹配、多状态过滤、时间范围、指标范围）、`EnvironmentRecord`（环境信息：git/pip/conda/GPU/环境变量）、`StorageStats`（存储统计：实验数、指标点数、DB 大小/碎片率）、`MigrationStatus`（迁移状态追踪：进度百分比、错误列表） |
| `migration.py` | 存储迁移：`FilesToSQLiteMigrator`（文件→SQLite 批量迁移）；`detect_storage_type()` 检测当前存储类型（file_only/sqlite_only/hybrid/empty）；`ensure_modern_storage()` 自动选择后端并按需迁移；`migrate_storage_system()` 高层迁移入口（含备份） |
| `sql_utils.py` | SQL 安全工具：列名白名单验证（防 SQL 注入） |
| `sync_utils.py` | 同步包装器：在同步代码（如 `sdk.py`）中安全调用 async 存储后端方法 |
| `schema.sql` | SQLite 完整 DDL：7 张表（`experiments` 实验核心元数据、`metrics` 指标时序数据、`experiment_tags` 标签、`environments` 环境信息、`experiment_files` 文件引用、`query_cache` 查询缓存含过期机制、`storage_stats` 存储统计）+ 3 个预计算视图（`v_path_stats` 按 path 统计、`v_best_experiments` 最优实验排名、`v_recent_activity` 近期活动分级）+ 性能 PRAGMA（WAL 模式、256MB mmap、10MB cache） |

**架构说明**:
- **写入端** (`sdk.py`): 始终写文件 + 可选双写 SQLite
- **读取端** (`viewer/api/`): 当前只通过 `file_utils.py` 读文件，尚未切换到 SQLite
- **两个数据库**: `storage_root/runicorn.db`（storage 层）和 `storage_root/index/runicorn.db`（index 层）是独立的

---

### `index/` — 轻量索引数据库

**职责**: 独立的 SQLite 索引，记录 run 和 asset 的映射关系

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出 `IndexDb` |
| `db.py` | `IndexDb`: 管理 `storage_root/index/runicorn.db`，包含 `runs`、`assets`、`run_assets` 三张表。提供 `upsert_run()`、`finish_run()`、`upsert_asset()`、`record_asset_for_run()` 等方法。线程安全（per-thread connection + FileLock） |

**与 storage/ 的关系**: 这是一个**独立的**索引数据库（路径为 `index/runicorn.db`），与 `storage/` 的 `runicorn.db` 不同。`IndexDb` 主要由 SDK 写入端使用，记录资产去重信息。

**被谁调用**: `sdk.py`（创建 run 时 upsert_run、归档资产时 record_asset_for_run）

---

### `config/` — 数据目录

**注意**: 这**不是** Python 包（没有 `__init__.py`），是纯数据目录。

| 文件 | 职责 |
|------|------|
| `rate_limits.json` | API 限流的打包默认配置，被 `config.py` 的 `get_rate_limit_config()` 读取（优先级低于用户目录的同名文件） |

**问题**: 与同级的 `config.py` 同名，容易混淆。

---

### `rnconfig/` — 项目级配置加载器

**职责**: 加载和合并两层 `rnconfig.toml` 配置

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出 `get_effective_rnconfig`, `load_effective_rnconfig` |
| `loader.py` | 读取用户级（`%APPDATA%/Runicorn/rnconfig.toml`）和项目级（工作区根目录 `rnconfig.toml`）两份配置，深度合并（项目级覆盖用户级），带 mtime 缓存自动刷新 |

**被谁调用**: `__init__.py`（导出到包级 API）

---

### `log_compat/` — ML 日志兼容层

**职责**: 为常见 ML 框架提供 drop-in 替换的日志组件

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出 `MetricLogger`, `SmoothedValue`, `TorchvisionMetricLogger` |
| `torchvision.py` | 替代 torchvision/DeiT 的 `MetricLogger`/`SmoothedValue`：完全兼容原始 API（`update()`, `log_every()`, `synchronize_between_processes()`），额外自动将指标转发到 `runicorn.Run.log()`。纯 Python 实现，PyTorch 可选加速 |

**使用方式**: 用户将 `from torchvision.references.detection.utils import MetricLogger` 替换为 `from runicorn.log_compat.torchvision import MetricLogger`

---

### `workspace/` — 工作区检测

**职责**: 确定用户项目的工作区根目录

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出 `get_workspace_root` |
| `root.py` | `get_workspace_root()`: 优先使用显式参数 → 向上查找 `.git` 目录 → fallback 到 `cwd`。用于代码快照和 rnconfig 查找 |

**被谁调用**: `sdk.py`, `rnconfig/loader.py`

---

### `api/` — SDK 端 API 客户端

**职责**: 提供 Python 编程接口访问 Viewer REST API（类似 requests 封装）

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出 `RunicornClient`, `connect()`, 异常类, 数据模型 |
| `client.py` | `RunicornClient`: HTTP 客户端，封装 GET/POST/PUT/DELETE，内置重试策略和错误处理。提供 `list_experiments()`, `get_run()`, `get_metrics()`, `export_experiment()` 等高层方法。**注意**：当前有部分方法/路径与 Viewer 实现不一致（例如 `list_experiments()` 使用 `/api/experiments`、`get_metrics()` 使用 `/api/metrics/{run_id}`、`update_config()` 使用 `PUT /api/config`），需要与 `viewer/api/` 对齐 |
| `remote.py` | `RemoteAPI`: 远程 Viewer 操作（SSH 连接/断开、启动/停止远程 Viewer、列出会话、浏览远程目录） |
| `models.py` | 客户端数据模型：`Experiment`, `MetricPoint`, `MetricSeries`, `RemoteSession`, `Project` |
| `exceptions.py` | API 异常：`RunicornAPIError`, `ConnectionError`, `NotFoundError`, `BadRequestError`, `ServerError`, `AuthenticationError` |
| `utils.py` | 客户端工具函数（均需 pandas）：`metrics_to_dataframe()` 指标转 DataFrame、`experiments_to_dataframe()` 实验列表转 DataFrame（自动转换时间戳）、`export_metrics_to_csv()` 导出指标到 CSV 文件、`compare_runs()` 多 run 指标对比（按 step 对齐） |

**与 viewer/api/ 的区别**: `api/` 是**客户端**（发 HTTP 请求），`viewer/api/` 是**服务端**（处理 HTTP 请求）

---

### `remote/` — SSH 远程访问

**职责**: SSH 连接管理和远程 Viewer 功能的底层实现

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出 `SSHConnection`, `SSHConnectionPool`, `SSHConfig` |
| `connection.py` | `SSHConfig`: SSH 配置数据类；`SSHConnection`: SSH 连接封装（自动重连、keepalive、SFTP、命令执行），支持密码/密钥文件/密钥内容/agent 多种认证方式；`SSHConnectionPool`: 连接池，按 `user@host:port` 复用连接 |
|| `ssh_backend.py` | SSH 后端抽象层：`SshBackend` ABC + `SshConnection`/`SshTunnel` Protocol；隧道实现含 `OpenSSHTunnel`（系统 OpenSSH，严格 known_hosts/Windows 无窗口）与 `AsyncSSHTunnel`（asyncssh）；并提供 `ParamikoBackend`/`OpenSSHBackend`/`AsyncSSHBackend` 与 `AutoBackend`（自动选择/回退） |
| `environment.py` | `RemoteEnvironmentDetector`: 远程 Python 环境自动检测（类似 VSCode Remote 策略），三阶段查找 conda（PATH → 常见路径 → shell 初始化文件解析），列出所有 conda 环境和系统 Python |
| `host_key.py` | SSH 主机密钥验证数据模型：`HostKeyProblem` frozen dataclass（含 host/port/指纹/公钥/验证原因）；异常层级 `HostKeyConfirmationRequiredError` → `UnknownHostKeyError`（首次连接） / `HostKeyChangedError`（密钥变更） |
| `known_hosts.py` | `KnownHostsStore`: OpenSSH known_hosts 文件管理（并发安全，FileLock 保护），支持 `upsert_host_key()` / `remove_host_key()` / `list_host_keys()`；工具函数：`format_known_hosts_host()` 格式化非标端口、`compute_fingerprint_sha256()` 计算 SHA256 指纹、`parse_openssh_public_key()` 解析公钥 |
| `viewer/` | 远程 Viewer 子模块 |
| `viewer/__init__.py` | 导出 `RemoteViewerManager` |
| `viewer/manager.py` | `RemoteViewerManager`: 管理远程 Viewer 会话的生命周期（启动/停止/列出） |
| `viewer/session.py` | 远程 Viewer 会话数据模型 |
| `viewer/tunnel.py` | SSH 隧道管理（端口转发） |

**被谁调用**: `viewer/__init__.py`（初始化连接池和 RemoteViewerManager）、`viewer/api/remote.py`（API 路由）

---

### `security/` — 安全模块

**职责**: 提供加密、路径验证、限流等安全功能

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出 `CredentialManager`, `get_credential_manager`, `encrypt_password`, `decrypt_password` |
| `credentials.py` | `CredentialManager`: 基于 XOR 混淆的凭证加解密（基础版），使用 `%APPDATA%/Runicorn/.credential_key` 随机密钥（32 字节）。提供 `encrypt_credential()` / `decrypt_credential()` 单值加解密（标记前缀 `ENC:`），`encrypt_config()` / `decrypt_config()` 批量处理字典中的敏感字段（password, passphrase, private_key, secret, token, api_key）。被 `config.py` 的 `save_ssh_connections()` / `get_ssh_connections()` 使用。模块级 `get_credential_manager()` 提供单例访问 |
| `encryption.py` | 基于 `cryptography.Fernet` 的对称加密（正式版），使用 `%APPDATA%/Runicorn/.secret.key`（自动生成）。提供 `encrypt_password()` / `decrypt_password()` / `is_encrypted()`（Fernet token 以 `gAAAAA` 开头）。被 `config.py` 的 `save_connections()` / `load_saved_connections()` 使用。与 `credentials.py` 的区别：这里用真正的密码学库，credentials 只是 XOR 混淆 |
| `path_validation.py` | 路径安全验证：`validate_path()` 防目录遍历攻击（检查 `..`、符号链接、路径长度）；`sanitize_filename()` 文件名消毒（移除特殊字符、处理 Windows 保留名）；`create_safe_directory()` 安全创建目录 |
| `rate_limiter.py` | `RateLimiter`: 滑动窗口限流核心实现（内存存储，per-client 时间戳队列）；`EndpointRateLimiter`: 按 endpoint 配置不同限流策略，支持 localhost 白名单 |

**问题**: `credentials.py`（XOR 混淆）和 `encryption.py`（Fernet 加密）功能重叠，`config.py` 中两套都在用

---

### `viewer/` — Viewer Web 应用（FastAPI）

**职责**: 提供实验数据的 Web 界面和 REST API

#### `viewer/__init__.py`
- `create_app()`: 创建并配置 FastAPI 应用
  - 初始化存储根目录
  - 配置 CORS（`allow_origins=["*"]` 含 localhost:5173，实际允许所有来源）
  - 添加限流中间件
  - 注册 13 个 API 路由
  - startup: 启动后台状态巡检任务
  - shutdown: 清理资源（取消后台任务、关闭 Remote Viewer 会话、关闭 SSH 连接池、关闭 storage service 数据库连接）
  - 初始化 Remote Viewer 组件（SSH 连接池 + RemoteViewerManager）
  - 挂载静态前端（优先 `RUNICORN_FRONTEND_DIST` 或 `RUNICORN_DESKTOP_FRONTEND` 环境变量 → fallback `webui/` 目录）

#### `viewer/api/` — API 路由（服务端）

| 文件 | 职责 |
|------|------|
| `__init__.py` | 统一导出 13 个 router |
| `health.py` | `/api/health` 健康检查 |
|| `runs.py` | `/api/runs/*` run 列表/详情、alias&tags 更新、assets 获取/下载、软删除/回收站/永久删除 |
|| `experiments.py` | `/api/experiments/*` 实验管理（tag/search/delete）。**注意**: 当前依赖 `ExperimentManager` 的导入失败时会返回 501（通常不可用） |
|| `metrics.py` | 指标/日志：`/api/runs/{id}/metrics(_step)` 指标查询（增量缓存 + 可选 downsample）；`/api/metrics/cache/stats` 缓存统计；WS `/api/runs/{id}/logs/ws` 日志流 |
|| `config.py` | `/api/config/*` 配置查询和修改（user_root_dir、ssh_connections 等） |
| `export.py` | `/api/export/*` 导出功能 |
| `import_.py` | `/api/import/*` 导入归档 |
| `projects.py` | `/api/projects/*` 项目列表 |
| `gpu.py` | `/api/gpu/*` GPU 信息（调用 `services/gpu.py`） |
| `system.py` | `/api/system/*` 系统信息（CPU/内存/磁盘） |
| `storage.py` | `/api/storage/*` 存储状态查询 |
| `remote.py` | `/api/remote/*` 远程 Viewer 操作（SSH 连接、启动远程 viewer、隧道管理） |
| `ui_preferences.py` | UI 偏好设置：列宽 `/api/config/column-widths*`；dismissed alerts `/api/config/dismissed-alerts*` |
| `listdir_cache.py` | 目录列表缓存（减少重复文件扫描） |
| `storage_utils.py` | 存储相关的 API 工具函数 |
| `modern/` | **空目录**（只有 `__pycache__`，残留待删除） |

**数据读取方式**: 当前所有路由通过 `storage/file_utils.py` 读取文件系统，未使用 SQLite 后端。

#### `viewer/services/` — 服务层

| 文件 | 职责 |
|------|------|
| `__init__.py` | 空 |
| `storage.py` | **纯转发层**：re-export `storage/file_utils.py` 的所有函数（含 `list_run_dirs_legacy`），兼容 `from viewer.services.storage import ...` 旧 import 路径 |
| `modern_storage.py` | `ModernStorageService`: 封装 `storage/backends.py` 的后端选择和数据格式转换。**未被任何 API 路由调用**。唯一活跃代码是 `close_storage_service()`，在 shutdown 事件中被调用（当前等于空操作，因为没有路由创建实例） |
|| `gpu.py` | GPU 信息采集：调用 `nvidia-smi` 获取 GPU 利用率/显存/温度/功耗，解析 CSV（`--format=csv,noheader,nounits`）输出 |
| `system_monitor.py` | 系统监控：CPU 使用率（总体+逐核）、内存/Swap 使用、磁盘空间、Load Average |

#### `viewer/middleware/` — 中间件

| 文件 | 职责 |
|------|------|
| `__init__.py` | 空 |
| `rate_limit.py` | `RateLimitMiddleware`: FastAPI 中间件，从 `config.py` 加载限流配置，调用 `security/rate_limiter.py` 的 `EndpointRateLimiter` 执行限流检查 |

#### `viewer/utils/` — 工具函数

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出缓存相关类 |
| `cache.py` | `MetricsCache`: 指标数据缓存（按 run_id 缓存已解析的 events.jsonl） |
| `incremental_cache.py` | `IncrementalMetricsCache`: 增量指标缓存（只读取 events.jsonl 的新增部分，通过文件偏移量实现） |
| `helpers.py` | 通用工具函数 |
| `logging.py` | Viewer 日志配置（`setup_logging()`） |
| `validation.py` | 请求参数验证 |

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

| 文件 | 职责 |
|------|------|
| `main.tsx` | ReactDOM 渲染入口，包裹 BrowserRouter |
| `App.tsx` | 根组件：6 条路由定义、Ant Design ConfigProvider（主题/暗色/紧凑模式）、SettingsProvider（全局 UI 设置 Context）、背景效果（渐变/图片/磨砂玻璃）、API 健康检查轮询、语言切换、首次运行自动打开 Settings |
| `api.ts` | 主 API 客户端：封装 fetch 调用后端 `/api/*`，包含 `listRuns`、`getRunDetail`、`getMetrics`、`health`、`getGpuTelemetry`、`getSystemMonitor`、`listProjects`、`getConfig`、`setUserRootDir`、`getSavedSSHConnections`、`importArchive` 等约 20 个函数 |
| `i18n.ts` | i18next 初始化：支持中/英两种语言，浏览器语言自动检测，localStorage 缓存 |

### `pages/` — 页面

| 文件 | 路由 | 职责 |
|------|------|------|
| `ExperimentPage.tsx` | `/` | 主页：实验列表表格、路径树侧栏、搜索/过滤、批量操作（删除/恢复/打标签/改别名）、导出、对比模式（CompareRunsPanel + CompareChartsView）、回收站、导入归档 |
| `RunDetailPage.tsx` | `/runs/:id` | Run 详情：指标图表、日志查看器、资产列表、配置信息、环境信息 |
| `PerformanceMonitorPage.tsx` | `/performance` | 硬件监控：CPU（逐核利用率）、内存磁盘、GPU 指标、GPU 遥测，Tab 页形式，可通过 Settings 控制显示/隐藏 |
| `RemoteViewerPage.tsx` | `/remote` | 远程 Viewer 管理：SSH 连接向导、已保存服务器列表、启动/停止远程 Viewer、会话状态 |
| `AssetsPage.tsx` | `/assets` | 资产浏览器：按类型分类、搜索、预览 |
| `AssetDetailPage.tsx` | `/assets/:id` | 资产详情：代码预览（CodeMirror）、文本文件预览、图片预览、下载 |

### `components/` — 组件

**指标与图表**

| 文件 | 职责 |
|------|------|
| `MetricChart.tsx` | 单指标折线图（ECharts），支持多 run 叠加 |
| `CompareChartsView.tsx` | 多 run 指标对比图表区域 |
| `CompareRunsPanel.tsx` | 多 run 对比左侧面板（选择 run、选择指标） |
| `AutoResizeEChart.tsx` | 自适应容器大小的 ECharts 包装 |
| `LazyChartWrapper.tsx` | 懒加载图表包装（Intersection Observer） |

**硬件监控**

| 文件 | 职责 |
|------|------|
| `CpuDetailCard.tsx` | CPU 详情卡片（总体+逐核利用率、频率、Load Average） |
| `MemoryDiskCard.tsx` | 内存/Swap/磁盘使用卡片 |
| `GpuMetricsCard.tsx` | GPU 指标卡片（利用率、显存、温度、功耗） |
| `GpuTelemetry.tsx` | GPU 遥测时序图 |

**实验管理**

| 文件 | 职责 |
|------|------|
| `PathTreePanel.tsx` | 路径层级树侧栏（按 path 组织 run） |
| `AddTagModal.tsx` | 标签添加/编辑弹窗 |
| `RecycleBin.tsx` | 回收站（软删除 run 的恢复/永久删除） |
| `ResizableTitle.tsx` | 可拖拽调整列宽的表头 |

**Run 详情**

| 文件 | 职责 |
|------|------|
| `LogsViewer.tsx` | 日志查看器（ANSI 颜色支持、自动滚动） |
| `RunAssets.tsx` | Run 资产列表 |
| `SystemInfoPanel.tsx` | 系统/环境信息面板 |

**远程 Viewer**

| 文件 | 职责 |
|------|------|
| `remote/RemoteConfigCard.tsx` | SSH 连接配置卡片 |
| `remote/RemoteSessionCard.tsx` | 远程 Viewer 会话卡片 |
| `remote/HostKeyModal.tsx` | SSH 主机密钥确认弹窗 |
| `remote/CondaEnvSelector.tsx` | 远程 Conda 环境选择器 |

**UI 基础**

| 文件 | 职责 |
|------|------|
| `SettingsDrawer.tsx` | 全局设置抽屉（主题/背景/刷新/图表/Tab 控制）+ `UiSettings` 类型定义 |
| `LoadingSkeleton.tsx` | 骨架屏加载占位 |
| `DismissibleAlert.tsx` | 可永久关闭的提示条 |
| `DismissedAlertsManager.tsx` | 已关闭提示的管理面板 |
| `animations/PageTransition.tsx` | 页面切换动画（framer-motion） |
| `fancy/FancyMetricCard.tsx` | 带渐变/动效的指标卡片 |
| `fancy/FancyStatCard.tsx` | 带动效的统计卡片 |
| `fancy/CircularProgress.tsx` | 环形进度条 |
| `fancy/AnimatedStatusBadge.tsx` | 动画状态徽章 |
| `fancy/FancyEmpty.tsx` | 美化的空状态 |
| `fancy/ServerStatusLight.tsx` | 服务器状态指示灯 |
| `fancy/ShimmerSkeleton.tsx` | 闪光骨架屏 |

**资产预览**

| 文件 | 职责 |
|------|------|
| `assets/AssetPreview.tsx` | 资产预览路由（按类型分发） |
| `assets/TextFilePreview.tsx` | 文本文件预览 |
| `assets/code/CodeArchivePreview.tsx` | 代码归档预览（zip 解压浏览） |
| `assets/code/CodeTextViewer.tsx` | 代码文本查看器（CodeMirror 语法高亮） |

### `hooks/` — 自定义 Hooks

| 文件 | 职责 |
|------|------|
| `useSavedConnections.ts` | 管理已保存的 SSH 连接（CRUD + 状态） |
| `useRemoteSessions.ts` | 管理远程 Viewer 会话（轮询状态） |
| `useAssetsIndex.ts` | 资产索引查询 |
| `useColumnWidths.ts` | 表格列宽持久化 |
| `useSuccessConfetti.tsx` | 操作成功时的彩纸动画 |

### `api/` — 分模块 API 客户端

| 文件 | 职责 |
|------|------|
| `remote.ts` | Remote Viewer API 客户端：SSH 连接/断开、启动/停止远程 Viewer、浏览远程目录、主机密钥管理 |
| `preferences.ts` | 用户偏好 API：已关闭提示的管理（dismiss/undismiss/clear） |

**注意**: 与主 `api.ts` 的关系是补充——`api.ts` 包含大部分 API 调用，`api/remote.ts` 和 `api/preferences.ts` 是后加入的独立模块。

### 其他目录

| 目录 | 职责 |
|------|------|
| `contexts/SettingsContext.tsx` | 全局 UI 设置的 React Context |
| `types/remote.ts` | Remote Viewer 相关 TypeScript 类型定义 |
| `config/animation_config/` | 各页面/组件的动画参数配置（颜色、时长、缓动等） |
| `utils/format.ts` | 数据格式化（时间、字节、数字） |
| `utils/logger.ts` | 前端日志工具 |
| `utils/assetDownload.ts` | 资产下载工具 |
| `utils/assetIdentity.ts` | 资产标识/去重工具 |
| `utils/assetParse.ts` | 资产文件解析 |
| `styles/designTokens.ts` | 设计令牌（颜色、间距等） |
| `styles/gradients.ts` | 渐变色预设 |
| `styles/*.css` | 表格增强样式、可调整列宽样式 |
| `locales/en/` | 英文翻译（common、experiments、remote、assets、settings） |
| `locales/zh/` | 中文翻译（同上） |

---

## 三、已知问题

### 结构问题
1. **`config.py` 和 `config/` 同名**: `config/` 是数据目录（只含 `rate_limits.json`），与 `config.py` 容易混淆
2. **`api/`（客户端）和 `viewer/api/`（服务端）都叫 api**: 职责完全不同但命名相似
3. **`viewer/api/modern/` 空目录**: 只有 `__pycache__`，残留待删除
4. **`viewer/services/storage.py` 纯转发层**: 只是 re-export `storage/file_utils.py`，多了一层不必要的间接

### 功能重叠
5. **两套加密**: `security/credentials.py`（XOR 混淆）和 `security/encryption.py`（Fernet），`config.py` 中两套都在用
6. **两个 SQLite 数据库**: `storage_root/runicorn.db`（storage 层）和 `storage_root/index/runicorn.db`（index 层），职责有重叠
7. **`viewer/services/modern_storage.py` 未接入**: 设计为 API 路由的存储适配层，但无路由调用

### 未完成功能
8. **storage 双写已完成但读取未切换**: SDK 写入端已双写文件+SQLite，但 Viewer 读取端仍只读文件
9. **`FileStorageBackend` 半成品**: `get_experiment()` 返回 `None`，`list_experiments()` 返回空列表，`get_metrics()` 返回空列表
