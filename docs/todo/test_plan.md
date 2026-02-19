# Runicorn 全面测试规划

> 版本: 1.0
> 日期: 2026-02-19
> 基准分支: refactor/src-restructure（RF-01 ~ RF-15 全部完成后）
> 配套文档: refactor_proposal_v2.md, src_structure.md, progress.md

---

## 一、概述

### 1.1 目标
为 `src/runicorn/` 的所有核心模块编写全面测试，覆盖三个层级：
- **Unit**: 隔离测试单个函数/类，mock 所有外部依赖
- **Integration**: 测试模块间协作（如 SDK 写入 → SQLite 存储 → Viewer 读取）
- **E2E**: 模拟真实用户场景（启动 Viewer、HTTP 请求、SDK 生命周期）

### 1.2 框架与约定
- **框架**: pytest（已在 pyproject.toml 配置）
- **Python 版本**: ≥ 3.10
- **标记**: `@pytest.mark.unit` / `@pytest.mark.integration` / `@pytest.mark.e2e`
- **运行命令**:
  - 全量 unit + integration: `pytest`
  - 仅 unit: `pytest -m unit`
  - 含 e2e: `pytest --run-e2e`
- **临时目录**: 所有涉及文件 I/O 的测试使用 `tmp_path` fixture，禁止写入工作目录
- **数据库测试**: 每个测试用例使用独立的 SQLite 文件（`tmp_path / "runicorn.db"`），测试结束自动清理

### 1.3 现有测试现状
现有 `tests/` 目录结构混乱，覆盖面集中在 assets 和 remote 模块。**本计划不延续现有结构**，而是从零设计。可保留仍有效的测试文件，但需迁移到新目录并适配新 fixture。

---

## 二、目录结构

```
tests/
├── conftest.py                       # 全局 fixture + 标记注册 + src 路径注入
├── fixtures/                         # 可复用 fixture 模块
│   ├── __init__.py
│   ├── storage.py                    # storage_root, sqlite_backend, populated_db
│   ├── viewer.py                     # fastapi TestClient, app fixture
│   └── sdk.py                        # Run fixture, NoOpRun fixture
│
├── unit/
│   ├── conftest.py
│   ├── test_sdk_run.py               # SDK Run 类核心方法
│   ├── test_sdk_media.py             # log_image, log_text
│   ├── test_sdk_assets.py            # log_config, log_dataset, log_pretrained, scan_outputs
│   ├── test_enabled.py               # enabled/disabled 开关 + NoOpRun
│   ├── test_cli.py                   # CLI 子命令解析与执行
│   │
│   ├── config/
│   │   ├── test_paths.py             # 跨平台路径解析
│   │   ├── test_user_config.py       # load/save user config
│   │   ├── test_connections.py       # SSH 连接 CRUD + 加密迁移
│   │   ├── test_rate_limits.py       # 限流配置读写
│   │   ├── test_rnconfig.py          # rnconfig 两层合并
│   │   ├── test_registry.py          # TOML 注册表
│   │   ├── test_toml_cache.py        # _toml.py 共享缓存基础设施
│   │   └── test_compat_shims.py      # registry.py / rnconfig/ 兼容 shim 导入
│   │
│   ├── storage/
│   │   ├── test_sqlite_backend.py    # SQLiteStorageBackend 全接口
│   │   ├── test_connection_pool.py   # ConnectionPool 并发行为
│   │   ├── test_file_utils.py        # iter_all_runs, read/write_json, soft_delete, periodic_status_check
│   │   ├── test_models.py            # ExperimentRecord, MetricRecord, QueryParams 序列化
│   │   ├── test_migration.py         # FilesToSQLiteMigrator, migrate_index_to_unified
│   │   ├── test_index_db.py          # IndexDb (deprecated) 兼容层
│   │   ├── test_sql_utils.py         # 列名白名单验证
│   │   └── test_schema.py            # schema.sql DDL 完整性（表/视图/索引）
│   │
│   ├── security/
│   │   ├── test_encryption.py        # Fernet 加解密 + XOR 兼容读取
│   │   ├── test_path_validation.py   # 路径遍历防护
│   │   └── test_rate_limiter.py      # 滑动窗口限流算法
│   │
│   ├── viewer/
│   │   ├── test_db_reader.py         # db_reader.py 辅助层
│   │   └── test_listdir_cache.py     # 目录缓存
│   │
│   ├── client/
│   │   ├── test_http_client.py       # RunicornClient 请求构造（mock httpx）
│   │   ├── test_models.py            # RunInfo, PathInfo, MetricPoint
│   │   └── test_utils.py             # metrics_to_dataframe 等
│   │
│   ├── console/
│   │   ├── test_capture.py           # TeeWriter, ConsoleCapture
│   │   ├── test_log_manager.py       # LogManager singleton + 引用计数
│   │   └── test_logging_handler.py   # RunicornLoggingHandler
│   │
│   ├── extensions/
│   │   ├── test_monitors.py          # MetricMonitor, AnomalyDetector
│   │   ├── test_experiment.py        # ExperimentManager
│   │   ├── test_exporters.py         # MetricsExporter
│   │   └── test_environment.py       # EnvironmentCapture
│   │
│   └── remote/
│       ├── test_known_hosts.py       # KnownHostsStore (可复用现有)
│       └── test_ssh_backend.py       # AutoBackend 选择逻辑
│
├── integration/
│   ├── conftest.py
│   ├── test_sdk_storage.py           # SDK Run → SQLite 双写验证
│   ├── test_sdk_lifecycle.py         # init → log → set_primary_metric → finish 全流程
│   ├── test_viewer_runs_api.py       # /api/runs/* 路由（TestClient）
│   ├── test_viewer_projects_api.py   # /api/projects/* 路由
│   ├── test_viewer_metrics_api.py    # /api/runs/{id}/metrics 路由
│   ├── test_viewer_health_api.py     # /api/health 路由
│   ├── test_viewer_export_api.py     # /api/export/* 路由
│   ├── test_viewer_import_api.py     # /api/import/* 路由
│   ├── test_viewer_config_api.py     # /api/config/* 路由
│   ├── test_viewer_storage_api.py    # /api/storage/* 路由
│   ├── test_viewer_sqlite_sync.py    # 文件系统 → SQLite 同步
│   ├── test_client_server.py         # RunicornClient → Viewer 联调
│   ├── test_config_migration.py      # XOR→Fernet 数据迁移
│   └── test_encryption_roundtrip.py  # 敏感字段加解密往返
│
├── e2e/
│   ├── conftest.py
│   ├── test_full_workflow.py         # SDK 写入 → Viewer 查询 → 客户端读取
│   ├── test_cli_commands.py          # CLI 全子命令 smoke test
│   └── test_viewer_startup.py        # Viewer 进程启动 + 健康检查
│
└── data/                             # 测试用静态数据
    ├── sample_meta.json
    ├── sample_events.jsonl
    ├── sample_rnconfig.toml
    └── sample_rate_limits.json
```

---

## 三、公共 Fixture 设计

### 3.1 `conftest.py`（根级）
```python
# 保留现有的 sys.path 注入和 --run-e2e 选项
# 新增 marker 注册:
#   @pytest.mark.unit
#   @pytest.mark.integration
#   @pytest.mark.e2e
#   @pytest.mark.slow
```

### 3.2 `fixtures/storage.py`
- `storage_root(tmp_path)` — 创建标准 storage_root 目录结构（`runs/` 子目录）
- `sqlite_backend(storage_root)` — 初始化 SQLiteStorageBackend（执行 schema.sql），yield 后调用 `close()`
- `populated_storage(storage_root)` — 预填充 3~5 个 run 的文件系统数据（meta.json, status.json, events.jsonl）
- `populated_db(sqlite_backend, populated_storage)` — 将文件系统数据同步到 SQLite

### 3.3 `fixtures/viewer.py`
- `app(storage_root, sqlite_backend)` — 调用 `create_app()` 并注入 `app.state.storage_root` + `app.state.storage_backend`，跳过真实 startup 事件
- `client(app)` — httpx `AsyncClient` 或 Starlette `TestClient`

### 3.4 `fixtures/sdk.py`
- `run_instance(storage_root)` — 创建一个 `Run` 实例（`capture_console=False`, `enable_modern_storage=True`），yield 后调用 `finish()`
- `noop_run()` — 返回 `NoOpRun` 实例

---

## 四、各模块测试用例详细规划

### 4.1 SDK 核心 — `sdk.py`

#### `test_sdk_run.py` (unit)
- `test_run_creates_directory_structure` — 验证 `Run.__init__` 创建 `storage_root/runs/<path>/<id>/` 及 meta.json, status.json
- `test_run_log_writes_events_jsonl` — `run.log({"loss": 0.5}, step=1)` 后 events.jsonl 含对应行
- `test_run_log_auto_step_increment` — 不传 step 时自动递增
- `test_run_log_multiple_metrics` — 单次 log 多个指标
- `test_run_set_primary_metric` — 设置后 summary.json 含 best_metric_name/value
- `test_run_best_metric_tracking_max` — mode="max" 时只记录更大值
- `test_run_best_metric_tracking_min` — mode="min" 时只记录更小值
- `test_run_finish_writes_status` — finish() 后 status.json 中 status="finished"
- `test_run_finish_failed_status` — finish(status="failed") 写入 "failed"
- `test_run_context_manager_success` — `with Run(...) as run:` 正常退出 → finished
- `test_run_context_manager_exception` — with 块抛异常 → failed
- `test_run_double_finish_idempotent` — 多次 finish 不报错
- `test_run_sqlite_dual_write` — log() 后 SQLite experiments 和 metrics 表有对应记录
- `test_run_sqlite_disabled_via_env` — `RUNICORN_DISABLE_MODERN_STORAGE=1` 时不写 SQLite
- `test_run_summary_writes_file` — summary() 方法正确写入 summary.json
- `test_run_init_with_alias` — alias 参数写入 meta.json
- `test_run_init_with_tags` — tags 参数写入 meta.json 和 experiment_tags 表
- `test_run_storage_backend_asset_methods` — log_config/log_dataset/log_pretrained 调用 backend 的资产方法

#### `test_sdk_media.py` (unit)
- `test_log_image_from_path` — 传入文件路径
- `test_log_image_from_pil` — 传入 PIL Image（mock PIL）
- `test_log_image_from_numpy` — 传入 numpy 数组（mock numpy）
- `test_log_image_no_pil_graceful` — PIL 不可用时不崩溃
- `test_log_text_writes_file` — log_text 写入 txt 文件

#### `test_enabled.py` (unit)
- `test_default_enabled` — 默认启用
- `test_disable_via_env` — `RUNICORN_ON=0` → disabled
- `test_set_enabled_programmatic` — `set_enabled(False)` → disabled
- `test_reset_enabled` — reset 后恢复默认
- `test_noop_run_all_methods_silent` — NoOpRun 所有方法可调用且不报错
- `test_noop_run_returns_none` — NoOpRun.log() 返回 None
- `test_enabled_context_manager` — `with enabled(False):` 块内 disabled，块外恢复

### 4.2 config/ 包

#### `test_paths.py` (unit)
- `test_config_root_dir_windows` — Windows 下返回 `%APPDATA%/Runicorn`（mock platform/env）
- `test_config_root_dir_linux` — Linux 下返回 `~/.config/runicorn`
- `test_config_root_dir_macos` — macOS 下返回 `~/Library/Application Support/Runicorn`
- `test_get_config_file_path` — 返回 `config_root / "config.json"`
- `test_get_connections_file_path` — 返回 `config_root / "connections.json"`
- `test_get_known_hosts_file_path` — 返回 `config_root / "known_hosts"`
- `test_get_registry_dir` — 返回 `config_root / "registry"`

#### `test_user_config.py` (unit)
- `test_load_empty_config` — 文件不存在返回默认空 dict
- `test_save_and_load_roundtrip` — 写入后读回一致
- `test_get_user_root_dir_default` — 未设置时返回默认路径
- `test_set_user_root_dir` — 设置后持久化到 config.json
- `test_corrupt_config_file_graceful` — JSON 损坏不崩溃，返回默认值

#### `test_connections.py` (unit) — RF-04/RF-05 核心验证
- `test_save_connections_encrypts_all_sensitive_fields` — password, passphrase, private_key, secret, token, api_key 全部加密
- `test_load_connections_decrypts_all_fields` — 读回时解密还原
- `test_add_ssh_connection` — 新增连接后持久化
- `test_remove_ssh_connection` — 删除连接后持久化
- `test_add_duplicate_connection_updates` — host:port@user 相同时覆盖
- `test_legacy_xor_migration` — config.json 中的 `ENC:` 前缀数据自动迁移到 Fernet + connections.json
- `test_legacy_xor_and_fernet_coexist` — 同时存在两种格式时都能正确读取
- `test_no_connection_limit` — 不再有 10 条限制（RF-05 改动）
- `test_plaintext_password_gets_encrypted` — 未加密的明文存入时自动加密

#### `test_rnconfig.py` (unit)
- `test_load_user_level_only` — 仅有用户级 rnconfig.toml
- `test_load_project_level_only` — 仅有项目级 rnconfig.toml
- `test_merge_project_overrides_user` — 项目级覆盖用户级
- `test_mtime_cache_hit` — 文件未变时返回缓存
- `test_mtime_cache_invalidation` — 修改文件后缓存刷新

#### `test_registry.py` (unit)
- `test_get_config_existing_key` — 读取已有的 TOML key
- `test_get_config_missing_key` — 不存在的 key 返回 None
- `test_clear_registry_cache` — 清缓存后下次读取从文件加载
- `test_mtime_cache` — 同 rnconfig 的缓存逻辑

#### `test_compat_shims.py` (unit)
- `test_import_from_runicorn_config` — `from runicorn.config import load_user_config` 可用
- `test_import_from_runicorn_registry` — `from runicorn.registry import get_config` 可用（兼容 shim）
- `test_import_from_runicorn_rnconfig` — `from runicorn.rnconfig import get_effective_rnconfig` 可用（兼容 shim）
- `test_import_private_config_root_dir` — `from runicorn.config import _config_root_dir` 可用（security/ 依赖）

### 4.3 storage/ 存储层

#### `test_sqlite_backend.py` (unit) — RF-06/RF-13/RF-14 核心验证
CRUD 基础:
- `test_create_experiment` — 插入后 get 返回相同数据
- `test_create_duplicate_id_upserts` — 相同 ID 重复插入为 upsert
- `test_update_experiment` — 更新 status/alias 等字段
- `test_get_experiment_not_found` — 不存在的 ID 返回 None
- `test_list_experiments_no_filter` — 无条件列出全部
- `test_list_experiments_with_query` — QueryParams 过滤（path, status, time_range）
- `test_count_experiments` — 计数与 list 结果一致
- `test_log_metrics` — 批量写入指标记录
- `test_get_metrics_all` — 获取全部指标
- `test_get_metrics_by_name` — 按名称过滤
- `test_soft_delete` — 软删除后 list 不返回、get 仍返回（deleted_at 非 None）
- `test_restore_experiments` — 恢复后 deleted_at 为 None
- `test_get_storage_stats` — 返回正确的实验数/指标数/DB 大小

Viewer 专用方法 (RF-14):
- `test_list_experiments_for_viewer` — 返回含 tags_csv 和 assets_count 的 dict
- `test_list_deleted_for_viewer` — 仅返回已软删除的记录
- `test_get_unique_paths` — 返回去重的 path 列表
- `test_get_path_stats` — 按 path 统计 run 数量/最新时间
- `test_get_running_experiments` — 仅返回 status="running"
- `test_experiment_exists` — 存在返回 True，不存在返回 False
- `test_set_tags_and_get_tags` — 标签的 CRUD
- `test_set_tags_replaces_existing` — 重新设置标签替换旧值

资产方法 (RF-13):
- `test_upsert_asset` — 插入资产记录
- `test_link_run_asset` — 关联 run 和 asset
- `test_record_asset_for_run` — 一步完成 upsert + link
- `test_delete_run_with_orphan_assets` — 删除 run 时清理无引用资产
- `test_get_assets_for_run` — 获取 run 的所有资产
- `test_get_asset_by_fingerprint` — 按指纹查找
- `test_get_asset_ref_count` — 资产引用计数

#### `test_connection_pool.py` (unit)
- `test_pool_init_creates_connections` — 初始化后 pool 有 N 个连接
- `test_get_and_return_connection` — 获取连接后归还
- `test_concurrent_access` — 多线程同时获取连接无死锁（threading）
- `test_close_all` — close_all 后所有连接关闭

#### `test_file_utils.py` (unit)
- `test_iter_all_runs_new_layout` — `runs/<path>/<id>/` 目录结构
- `test_iter_all_runs_legacy_layout` — `<project>/<name>/runs/<id>/` 旧目录结构
- `test_iter_all_runs_mixed_layouts` — 新旧混合目录
- `test_iter_all_runs_include_deleted` — include_deleted=True 包含 .deleted 标记的 run
- `test_find_run_dir_by_id` — 按 ID 查找 run 目录
- `test_find_run_dir_by_id_not_found` — 不存在的 ID 返回 None
- `test_read_json_valid` — 读取正常 JSON 文件
- `test_read_json_missing_file` — 文件不存在返回空 dict
- `test_read_json_corrupt` — 损坏 JSON 不崩溃
- `test_write_json` — 写入并读回一致
- `test_soft_delete_run` — 创建 .deleted 标记文件
- `test_restore_run` — 删除 .deleted 标记文件
- `test_is_process_alive` — mock psutil 测试进程存活判断
- `test_update_status_if_process_dead` — 进程死亡时更新 status.json
- `test_periodic_status_check_with_backend` — 传入 backend 时同步更新 SQLite（RF-14）

#### `test_models.py` (unit)
- `test_experiment_record_from_dict` — 含 legacy project/name → path 转换
- `test_experiment_record_to_dict` — 序列化
- `test_query_params_defaults` — 默认值
- `test_query_params_with_filters` — path/status/time_range 组合
- `test_metric_record_creation` — 基本属性
- `test_storage_stats_fields` — 字段完整性

#### `test_migration.py` (unit)
- `test_files_to_sqlite_migrator` — 基本迁移流程
- `test_migration_with_new_layout` — 新目录布局下的迁移
- `test_migration_with_legacy_layout` — 旧目录布局下的迁移
- `test_migrate_index_to_unified` — IndexDb → 统一 DB 迁移（RF-13）
- `test_migrate_index_idempotent` — 重复迁移不报错
- `test_ensure_modern_storage` — 自动检测并初始化 SQLiteStorageBackend
- `test_detect_storage_type` — 检测 file_only/sqlite_only/hybrid/empty

#### `test_schema.py` (unit)
- `test_schema_creates_all_tables` — 7 张表 + assets/run_assets = 9 张表
- `test_schema_creates_views` — 3 个预计算视图
- `test_schema_wal_mode` — WAL 模式生效
- `test_schema_idempotent` — 重复执行 schema.sql 不报错

### 4.4 security/ 安全模块

#### `test_encryption.py` (unit) — RF-04 核心验证
- `test_encrypt_decrypt_roundtrip` — Fernet 加解密往返
- `test_is_encrypted_fernet` — `gAAAAA` 前缀识别
- `test_is_encrypted_plaintext` — 普通文本返回 False
- `test_decrypt_xor_legacy` — `ENC:` 前缀旧格式可解密
- `test_decrypt_auto_detect` — decrypt_password 自动识别 Fernet vs XOR
- `test_decrypt_plaintext_passthrough` — 明文原样返回
- `test_encrypt_all_sensitive_fields` — SENSITIVE_FIELDS 列表完整
- `test_missing_key_file_auto_creates` — 密钥文件不存在时自动生成

#### `test_path_validation.py` (unit)
- `test_validate_path_normal` — 正常路径通过
- `test_validate_path_traversal_attack` — 含 `..` 的路径被拒
- `test_validate_path_symlink` — 符号链接被拒（可配置）
- `test_sanitize_filename` — 移除特殊字符
- `test_sanitize_windows_reserved` — Windows 保留名（CON, PRN 等）
- `test_create_safe_directory` — 安全创建目录

#### `test_rate_limiter.py` (unit)
- `test_sliding_window_basic` — 窗口内请求计数
- `test_sliding_window_expired` — 过期请求不计数
- `test_endpoint_rate_limiter_different_endpoints` — 不同端点独立限流
- `test_localhost_whitelist` — localhost 请求不限流
- `test_rate_limiter_thread_safety` — 多线程并发访问

### 4.5 viewer/ Viewer 层

#### `test_db_reader.py` (unit) — RF-14 核心验证
- `test_get_backend_present` — app.state 有 backend 时返回
- `test_get_backend_absent` — app.state 无 backend 时返回 None
- `test_find_run_entry_fast_sqlite_hit` — SQLite 有记录时直接返回
- `test_find_run_entry_fast_sqlite_miss_fallback` — SQLite 无记录时回退文件扫描
- `test_find_run_entry_fast_deleted_excluded` — 已删除的 run 不返回（默认）
- `test_find_run_entry_fast_deleted_included` — include_deleted=True 时返回已删除
- `test_list_runs_from_db` — 正常返回 run 列表（含 tags 解析）
- `test_list_runs_from_db_empty` — 空数据库返回 None（触发 fallback）
- `test_list_runs_from_db_error_returns_none` — 异常时返回 None
- `test_sync_filesystem_to_db` — 文件系统 run 同步到 SQLite
- `test_sync_filesystem_to_db_idempotent` — 已存在的 run 不重复插入
- `test_sync_preserves_deleted_state` — 同步已软删除的 run 时保留 deleted_at
- `test_sync_tags_from_meta` — meta.json 中的 tags 同步到 experiment_tags 表

#### `test_listdir_cache.py` (unit)
- `test_cache_hit` — 第二次调用返回缓存
- `test_cache_expiry` — 过期后重新扫描

### 4.6 client/ 客户端库

#### `test_http_client.py` (unit) — RF-08 核心验证
- `test_health_check` — 验证请求 `/api/health`，期望 `{"status": "ok"}`
- `test_list_runs` — 验证请求 `GET /api/runs`
- `test_get_run_detail` — 验证请求 `GET /api/runs/{id}`
- `test_get_metrics` — 验证请求 `GET /api/runs/{id}/metrics`
- `test_export_csv` — 验证请求 `GET /api/export/{id}/csv`
- `test_export_report` — 验证请求 `GET /api/export/{id}/report`
- `test_set_user_root_dir` — 验证请求 `POST /api/config/user_root_dir`
- `test_get_gpu_info` — 验证请求 `GET /api/gpu/telemetry`
- `test_list_paths` — 验证请求 `GET /api/paths`
- `test_get_storage_stats` — 验证请求 `GET /api/storage/stats`
- `test_retry_on_failure` — 网络错误时重试
- `test_api_error_handling` — 4xx/5xx 响应抛出对应异常
- `test_connection_verify_fails_graceful` — 连接失败时抛出 APIConnectionError

#### `test_client_models.py` (unit)
- `test_run_info_from_dict` — RunInfo 数据模型
- `test_path_info_from_dict` — PathInfo 数据模型
- `test_legacy_experiment_alias` — Experiment 别名可用（向后兼容）
- `test_legacy_project_alias` — Project 别名可用

### 4.7 console/ 控制台捕获

#### `test_capture.py` (unit)
- `test_tee_writer_writes_both` — 同时写入终端和文件
- `test_tee_writer_tqdm_smart_mode` — smart 模式下 `\r` 行被缓冲
- `test_console_capture_replaces_stdout` — 进入 capture 后 sys.stdout 变更
- `test_console_capture_restores_stdout` — 退出 capture 后 sys.stdout 恢复
- `test_console_capture_atexit` — 异常退出时恢复原始流

#### `test_log_manager.py` (unit)
- `test_singleton_per_path` — 相同路径返回相同实例
- `test_reference_counting` — 关闭最后一个引用时才释放
- `test_write_immediate_flush` — 写入后立即 flush

### 4.8 extensions/ 扩展功能

#### `test_monitors.py` (unit)
- `test_metric_monitor_nan_detection` — loss=NaN 触发告警
- `test_metric_monitor_inf_detection` — loss=Inf 触发告警
- `test_anomaly_detector_sudden_change` — 突变检测
- `test_alert_rule_creation` — AlertRule 构造

#### `test_experiment.py` (unit) — RF-15 验证
- `test_search_experiments` — 按条件搜索
- `test_tag_experiments` — 批量打标签
- `test_delete_experiments` — 批量删除
- `test_find_run_path_new_layout` — 新目录布局下查找（RF-15 修正后）
- `test_find_run_path_fallback` — find_run_dir_by_id fallback

#### `test_exporters.py` (unit)
- `test_export_csv` — CSV 格式导出
- `test_export_markdown` — Markdown 格式导出

#### `test_environment.py` (unit)
- `test_capture_git_info` — 捕获 git commit/branch
- `test_capture_pip_packages` — 捕获 pip 包列表
- `test_capture_system_info` — 捕获系统信息

### 4.9 CLI

#### `test_cli.py` (unit)
- `test_viewer_help` — `viewer --help` 不报错
- `test_config_show` — `config --show` 输出配置
- `test_export_help` — `export --help` 不报错
- `test_export_data_help` — `export-data --help` 不报错
- `test_manage_help` — `manage --help` 不报错
- `test_delete_help` — `delete --help` 不报错
- `test_rate_limit_help` — `rate-limit --help` 不报错
- `test_export_uses_iter_all_runs` — export 命令使用 iter_all_runs（RF-15 验证）

---

## 五、Integration 测试详细规划

### 5.1 SDK → Storage 集成

#### `test_sdk_storage.py`
- `test_run_creates_sqlite_record` — Run init 后 SQLite experiments 表有记录
- `test_run_log_writes_to_sqlite` — log() 后 SQLite metrics 表有记录
- `test_run_finish_updates_sqlite_status` — finish() 更新 SQLite status
- `test_run_best_metric_in_sqlite` — set_primary_metric → log → summary 后 SQLite 有 best_metric
- `test_run_assets_recorded_in_unified_db` — log_config/log_dataset → assets 表有记录（RF-13）
- `test_run_tags_in_sqlite` — init with tags → experiment_tags 表有记录

#### `test_sdk_lifecycle.py`
- `test_full_lifecycle` — init → log(×N) → set_primary_metric → log_config → finish：文件系统和 SQLite 均正确
- `test_lifecycle_with_console_capture` — capture_console=True 的完整流程
- `test_lifecycle_disabled` — RUNICORN_ON=0 时全流程静默

### 5.2 Viewer API 集成（使用 TestClient）

#### `test_viewer_runs_api.py`
- `test_list_runs_from_sqlite` — 预填充 SQLite 后 GET /api/runs 返回完整列表
- `test_list_runs_fallback_to_files` — SQLite 无数据时从文件系统读取
- `test_get_run_detail` — GET /api/runs/{id} 返回详情
- `test_update_run_alias` — PUT /api/runs/{id} 更新别名（双写文件+SQLite）
- `test_update_run_tags` — PUT /api/runs/{id} 更新标签（双写）
- `test_soft_delete_run` — DELETE /api/runs/{id} 软删除（双写）
- `test_restore_run` — POST /api/runs/{id}/restore 恢复（双写）
- `test_list_deleted_runs` — GET /api/runs/deleted 返回回收站
- `test_get_run_assets` — GET /api/runs/{id}/assets 返回资产列表

#### `test_viewer_projects_api.py`
- `test_list_paths_from_sqlite` — GET /api/paths 从 SQLite 获取路径
- `test_list_path_stats` — 每个 path 的 run 数量、最新时间
- `test_list_runs_by_path` — GET /api/paths/{path}/runs 按路径筛选
- `test_soft_delete_by_path` — 按路径批量软删除

#### `test_viewer_metrics_api.py`
- `test_get_metrics_from_file` — 从 events.jsonl 读取指标
- `test_get_metrics_step` — GET /api/runs/{id}/metrics_step
- `test_metrics_cache_stats` — GET /api/metrics/cache/stats

#### `test_viewer_health_api.py`
- `test_health_returns_ok` — GET /api/health 返回 `{"status": "ok"}`
- `test_health_check_updates_dead_runs` — 后台巡检发现死进程后更新（双写 SQLite）

#### `test_viewer_export_api.py`
- `test_export_csv` — GET /api/export/{id}/csv 返回 CSV
- `test_export_report` — GET /api/export/{id}/report 返回 HTML/JSON

#### `test_viewer_import_api.py`
- `test_import_archive` — POST /api/import/upload 后文件系统和 SQLite 均有记录
- `test_import_triggers_sync` — 导入后触发文件系统→SQLite 同步

#### `test_viewer_sqlite_sync.py`
- `test_sync_on_startup` — app startup 时文件系统 → SQLite 同步
- `test_sync_handles_partial_data` — meta.json 缺失字段时不崩溃
- `test_sync_preserves_deleted` — 同步已软删除 run 保留 deleted_at

### 5.3 Client → Server 联调

#### `test_client_server.py`
- `test_client_health_check` — RunicornClient.check_status() 通过 TestClient 成功
- `test_client_list_runs` — RunicornClient.list_runs() 返回正确数据
- `test_client_get_metrics` — RunicornClient.get_metrics() 返回正确数据
- `test_client_get_storage_stats` — RunicornClient.get_storage_stats()

### 5.4 加密迁移集成

#### `test_config_migration.py`
- `test_xor_to_fernet_migration` — 准备含 XOR 加密的 config.json，调用 get_ssh_connections() 触发自动迁移，验证 connections.json 使用 Fernet
- `test_migration_preserves_all_connections` — 迁移前后连接数量一致
- `test_migration_removes_from_config_json` — 迁移后 config.json 中无 ssh_connections 字段

#### `test_encryption_roundtrip.py`
- `test_save_load_roundtrip_all_fields` — 保存含所有敏感字段的连接，重新读取后明文一致
- `test_mixed_format_connections` — 部分 Fernet + 部分 XOR + 部分明文，load 后均正确解密

---

## 六、E2E 测试规划

### `test_full_workflow.py`
完整端到端流程（标记 `@pytest.mark.e2e`）：
1. 启动 Viewer（uvicorn 子进程或 TestClient）
2. SDK 创建 Run 并 log 指标
3. HTTP GET /api/runs 验证 run 出现
4. HTTP GET /api/runs/{id}/metrics 验证指标数据
5. RunicornClient 连接并读取相同数据
6. SDK finish()，验证状态更新

### `test_cli_commands.py`
对每个 CLI 子命令执行 smoke test（`subprocess.run`）：
- `python -m runicorn viewer --help` → exit 0
- `python -m runicorn config --show` → exit 0
- `python -m runicorn export --help` → exit 0
- `python -m runicorn export-data --help` → exit 0
- `python -m runicorn manage --help` → exit 0
- `python -m runicorn rate-limit --help` → exit 0
- `python -m runicorn delete --help` → exit 0

### `test_viewer_startup.py`
- `test_viewer_creates_app_successfully` — `create_app()` 返回 FastAPI 实例，包含 74 个路由
- `test_viewer_startup_initializes_backend` — startup 事件后 `app.state.storage_backend` 不为 None
- `test_viewer_shutdown_closes_backend` — shutdown 事件后 backend 已关闭

---

## 七、重构项目（RF-01~RF-15）专项验证矩阵

以下列出每个 RF 项需要被测试覆盖的关键点，以及对应的测试文件：

- **RF-01** (删除空目录): 无需专项测试，import 验证即可
- **RF-02** (消除转发层): `test_compat_shims.py` — 验证 `from runicorn.storage.file_utils import ...` 直接可用
- **RF-03** (config 包): `test_paths.py`, `test_user_config.py`, `test_compat_shims.py`
- **RF-04** (统一加密): `test_encryption.py`, `test_connections.py`, `test_encryption_roundtrip.py`
- **RF-05** (统一 SSH 路径): `test_connections.py`, `test_config_migration.py`
- **RF-06** (async→sync): `test_sqlite_backend.py` — 所有方法为同步调用（无 await）
- **RF-07** (消除 asyncio): `test_sdk_run.py` — SDK 直接调用 backend（无 asyncio）
- **RF-08** (client 重命名+修复): `test_http_client.py`, `test_client_server.py`, `test_client_models.py`
- **RF-09** (index 合并): `test_sqlite_backend.py` 资产方法, `test_index_db.py` 兼容 shim
- **RF-10** (workspace 降级): `test_compat_shims.py` — `from runicorn.workspace import get_workspace_root`
- **RF-11** (删除 FileStorageBackend): `test_sqlite_backend.py` — 验证 SQLiteStorageBackend 是唯一完整实现
- **RF-12** (删除 modern_storage): 无需专项测试（已删除）
- **RF-13** (合并 DB): `test_sqlite_backend.py` 资产方法, `test_migration.py` migrate_index_to_unified
- **RF-14** (Viewer SQLite 读取): `test_db_reader.py`, `test_viewer_runs_api.py`, `test_viewer_projects_api.py`, `test_viewer_sqlite_sync.py`
- **RF-15** (统一目录布局): `test_file_utils.py` iter_all_runs 新旧布局, `test_experiment.py` find_run_path

---

## 八、优先级与执行建议

### Phase T1: 基础设施 + 存储层（最高优先级）
建立 conftest.py 和 fixtures/ → 编写 storage/ 全部 unit 测试 → config/ 测试。
这是其他一切的基础。

### Phase T2: SDK + Viewer 集成
SDK unit 测试 → Viewer API integration 测试 → db_reader unit 测试。
覆盖最核心的用户路径。

### Phase T3: 安全 + 客户端
security/ unit 测试 → client/ unit 测试 → client-server integration。
验证 RF-04/05/08 的正确性。

### Phase T4: 扩展 + E2E
extensions/ + console/ unit 测试 → E2E 全流程。
完善覆盖率。

### 预估测试用例数量
- Unit: ~170 个
- Integration: ~45 个
- E2E: ~10 个
- **合计: ~225 个**
