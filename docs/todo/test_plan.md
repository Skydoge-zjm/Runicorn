# Runicorn 全面测试规划

> 版本: 1.1（审阅修订版）
> 日期: 2026-02-19
> 基准分支: test/comprehensive（基于 develop 的 merge commit dc2dc4d，RF-01~RF-15 已全部完成）
> 配套文档: src_structure.md, test_plan_review_synthesis.md

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
  - 含 e2e: `pytest`（E2E 测试默认运行，无需额外标记）
- **临时目录**: 所有涉及文件 I/O 的测试使用 `tmp_path` fixture，禁止写入工作目录
- **数据库测试**: 每个测试用例使用独立的 SQLite 文件（`tmp_path / "runicorn.db"`），测试结束自动清理
- **异步测试**: 涉及 `async def` 的被测函数（如 `periodic_status_check`）需 `pytest-asyncio` 支持，测试函数标记 `@pytest.mark.asyncio`
- **参数化**: 跨平台路径（win/linux/macos）、加密格式（fernet/xor/plaintext）、Viewer 列表/过滤等场景应使用 `@pytest.mark.parametrize` 收敛用例，避免重复

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
│   ├── test_workspace.py              # get_workspace_root .git 查找与 fallback
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
│   │   ├── test_listdir_cache.py     # 目录缓存
│   │   └── test_incremental_cache.py # IncrementalMetricsCache 增量读取
│   │
│   ├── client/
│   │   ├── test_http_client.py       # RunicornClient 请求构造（mock requests）
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
│   ├── assets/
│   │   ├── test_fingerprint.py       # dir_stat_fingerprint, stat_fingerprint 确定性
│   │   ├── test_archive.py           # 基于指纹的归档去重
│   │   ├── test_ignore.py            # .runicornignore 规则解析与匹配
│   │   └── test_assets_json.py       # ensure_assets_file, update_assets_atomic 原子写入
│   │
│   ├── log_compat/
│   │   └── test_torchvision.py       # MetricLogger/SmoothedValue API 兼容 + 指标转发
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
│   ├── test_viewer_projects_api.py   # /api/paths/* 路由（projects_router 实际提供 paths 层级 API）
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
└── data/                             # 测试用静态数据（仅用于 fixture 无法动态生成的场景）
    ├── sample_meta.json              # 被 populated_storage fixture 引用
    ├── sample_events.jsonl           # 被 populated_storage fixture 引用
    ├── sample_rnconfig.toml          # 被 test_rnconfig.py 引用
    └── sample_rate_limits.json       # 被 test_rate_limits.py 引用
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
- `app(storage_root, sqlite_backend)` — 调用 `create_app()` 并手动设置 `app.state.storage_root` + `app.state.storage_backend`，**不通过 TestClient 触发 startup 事件**（startup 会启动 periodic_status_check 和 sync_filesystem_to_db 后台线程，干扰测试稳定性）；如需 TestClient 包装，应先 monkeypatch 掉后台任务
- `client(app)` — Starlette `TestClient`（同步），或 httpx `AsyncClient`（异步）

### 3.4 `fixtures/sdk.py`
- `run_instance(storage_root, monkeypatch)` — 先 `monkeypatch.delenv("RUNICORN_DISABLE_MODERN_STORAGE", raising=False)` 确保现代存储启用，然后创建 `Run(storage=str(storage_root), capture_console=False)`，yield 后调用 `finish()`。显式传入 `run_id` 以确保可复现性
- `noop_run()` — 返回 `NoOpRun` 实例

### 3.5 `fixtures/config.py`（新增）
- `mock_config_root(tmp_path, monkeypatch)` — 统一将 `config.paths._config_root_dir` 指向 `tmp_path`，避免触碰真实 `%APPDATA%`、`.secret.key`、用户目录。config 包测试（paths, user_config, connections, rate_limits）均应使用

### 3.6 全局测试约定
- **缓存/全局单例重置**: `_toml.py` 缓存、`IncrementalMetricsCache`、`LogManager` 单例等全局状态，每个测试模块需在 fixture 中显式清理（如 `clear_toml_cache()`），避免测试互相污染
- **时间/并发确定性**: rate limiter、outputs scan、cache expiry、后台巡检等时间敏感测试，应用 `monkeypatch` 替换时间源（或依赖注入）而非 `sleep`，确保确定性

---

## 四、各模块测试用例详细规划

### 4.1 SDK 核心 — `sdk.py`

#### `test_sdk_run.py` (unit)
- `test_run_creates_directory_structure` — 验证 `Run.__init__` 创建 `storage_root/runs/<path>/<id>/` 及 meta.json, status.json
- `test_run_log_writes_events_jsonl` — `run.log({"loss": 0.5}, step=1)` 后 events.jsonl 含对应行
- `test_run_log_auto_step_increment` — 不传 step 时自动递增
- `test_run_log_multiple_metrics` — 单次 log 多个指标
- `test_run_set_primary_metric` — `set_primary_metric()` 设置内部状态，多次 `log()` 后 `finish()`，断言 summary.json 含 best_metric_name/best_metric_value/best_metric_step
- `test_run_best_metric_tracking_max` — mode="max" 时只记录更大值
- `test_run_best_metric_tracking_min` — mode="min" 时只记录更小值
- `test_run_finish_writes_status` — finish() 后 status.json 中 status="finished"
- `test_run_finish_failed_status` — finish(status="failed") 写入 "failed"
- `test_run_context_manager_success` — `with Run(...) as run:` 正常退出 → finished
- `test_run_context_manager_exception` — with 块抛异常 → failed
- `test_run_double_finish_idempotent` — 多次 finish 不报错
- `test_run_sqlite_dual_write` — log() 后 SQLite experiments 和 metrics 表有对应记录
- `test_run_sqlite_disabled_via_env` — `RUNICORN_DISABLE_MODERN_STORAGE=1` 时不写 SQLite，断言 `run.storage_backend is None` 且数据库文件不存在
- `test_run_summary_writes_file` — summary() 方法正确写入 summary.json
- `test_run_init_with_alias` — alias 参数写入 meta.json
- `test_run_storage_backend_asset_methods` — log_config/log_dataset/log_pretrained 调用 backend 的资产方法

#### `test_sdk_assets.py` (unit) — 资产方法专项
- `test_log_config_writes_config_json` — 验证写入文件路径和内容结构
- `test_log_dataset_records_asset_in_db` — 验证 assets 表有记录
- `test_log_pretrained_records_asset` — 同上
- `test_scan_outputs_once_archives_new_files` — 验证新文件被归档

#### `test_normalize_path` 用例（在 `test_sdk_run.py` 中）
- `test_normalize_path_default` — `None` → `"default"`
- `test_normalize_path_strips_root` — `"/"` → `""`
- `test_normalize_path_traversal_rejected` — 含 `".."` 的 path 抛 ValueError
- `test_normalize_path_invalid_chars_rejected` — 特殊字符抛 ValueError
- `test_normalize_path_max_length` — 超 200 字符抛 ValueError

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
- `test_noop_run_methods_match_run_interface` — 用 `inspect` 比对 `Run` 和 `NoOpRun` 的公共方法签名一致性（注意 `log_image()` 返回 `""`，`scan_outputs_once()` 返回 `{"scanned":0,...}`，并非全部返回 None）
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
- `test_get_rnconfig_file_path` — 返回 `config_root / "rnconfig.toml"`

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

#### `test_toml_cache.py` (unit) — `_toml.py` 共享缓存基础设施
- `test_load_toml_valid` — 正常 TOML 文件解析正确
- `test_load_toml_missing_returns_empty` — 文件不存在返回空 dict
- `test_load_toml_cached_same_mtime` — 相同 mtime 不重复读取
- `test_load_toml_cached_invalidated_on_change` — mtime 变化后刷新缓存
- `test_clear_toml_cache` — 清缓存后重新从文件加载

#### `test_rate_limits.py` (unit) — 限流配置读写
- `test_load_defaults_when_no_user_file` — 用户配置不存在时使用内置默认
- `test_load_from_package_defaults` — fallback 到 _defaults/ 目录
- `test_load_hardcoded_fallback` — 两者均不存在时返回硬编码默认
- `test_user_config_overrides_defaults` — 用户文件中的字段覆盖默认
- `test_save_and_load_roundtrip` — 保存后重新加载一致

#### `test_compat_shims.py` (unit)
- `test_import_from_runicorn_config` — `from runicorn.config import load_user_config` 可用
- `test_import_from_runicorn_registry` — `from runicorn.registry import get_config` 可用（兼容 shim）
- `test_import_from_runicorn_rnconfig` — `from runicorn.rnconfig import get_effective_rnconfig` 可用（兼容 shim）
- `test_import_private_config_root_dir` — `from runicorn.config import _config_root_dir` 可用（security/ 依赖）

#### `test_workspace.py` (unit) — RF-10 验证（workspace 是真实模块，非兼容 shim）
- `test_get_workspace_root_finds_git` — 无参数时返回当前目录祖先中有 .git 的目录
- `test_get_workspace_root_explicit` — 指定 explicit_root 时直接返回
- `test_get_workspace_root_fallback_cwd` — 无 .git 时 fallback 到 `cwd()`

### 4.3 storage/ 存储层

#### `test_sqlite_backend.py` (unit) — RF-06/RF-13/RF-14 核心验证
CRUD 基础:
- `test_create_experiment` — 插入后 get 返回相同数据
- `test_create_duplicate_id_raises_integrity_error` — 相同 ID 重复插入抛 IntegrityError（当前实现使用 INSERT INTO 而非 INSERT OR REPLACE）
- `test_update_experiment` — 更新 status/alias 等字段
- `test_get_experiment_not_found` — 不存在的 ID 返回 None
- `test_list_experiments_no_filter` — 无条件列出全部
- `test_list_experiments_with_query` — QueryParams 过滤（path, status, time_range）
- `test_count_experiments` — 计数与 list 结果一致
- `test_log_metrics` — 批量写入指标记录
- `test_get_metrics_all` — 获取全部指标
- `test_get_metrics_by_name` — 按名称过滤
- `test_soft_delete_excluded_from_list` — 软删除后 `list_experiments(include_deleted=False)` 不含该记录
- `test_soft_delete_get_still_returns` — 软删除后 `get_experiment()` 仍返回（需先确认实际 `get_experiment` 实现行为）
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
- `test_pool_init_creates_connections` — 指定 `pool_size=5`，初始化后 `len(pool.all_connections) == 5`
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
- `test_experiment_record_is_active` — deleted_at is None → True
- `test_experiment_record_is_running` — status="running", deleted_at=None → True
- `test_experiment_record_compute_duration` — started_at/ended_at 均有时正确计算
- `test_experiment_record_short_id` — short_id 属性返回截断值
- `test_experiment_record_path_parts` — path_parts() 解析正确
- `test_query_params_defaults` — 默认值
- `test_query_params_with_filters` — path/status/time_range 组合
- `test_metric_record_creation` — 基本属性
- `test_storage_stats_fields` — 字段完整性
- `test_environment_record_creation` — EnvironmentRecord 基本属性
- `test_migration_status_progress_percent` — processed/total 计算正确
- `test_migration_status_is_complete` — 全部处理完成时返回 True
- `test_migration_status_has_errors` — 有失败记录时返回 True

#### `test_migration.py` (unit)
- `test_files_to_sqlite_migrator` — 基本迁移流程
- `test_migration_with_new_layout` — 新目录布局下的迁移
- `test_migration_with_legacy_layout` — 旧目录布局下的迁移
- `test_migrate_index_to_unified` — IndexDb → 统一 DB 迁移（RF-13）
- `test_migrate_index_idempotent` — 重复迁移不报错
- `test_ensure_modern_storage` — 自动检测并初始化 SQLiteStorageBackend
- `test_detect_storage_type` — 检测 file_only/sqlite_only/hybrid/empty

#### `test_schema.py` (unit)
- `test_schema_creates_all_tables` — 用 `SELECT name FROM sqlite_master WHERE type='table'` 断言精确表名集合（set 对比），而非仅断言数量
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
- `test_cache_different_dirs` — 不同目录独立缓存

#### `test_incremental_cache.py` (unit) — IncrementalMetricsCache
- `test_incremental_read_new_lines` — 追加新行后再次查询只返回新增部分
- `test_incremental_cache_invalidated_on_truncation` — events.jsonl 被截断时重置偏移量
- `test_cache_stats_endpoint` — 缓存统计信息正确

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

#### `test_models.py` (unit) — client/models.py（命名与目录结构一致）
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

### 4.10 assets/ 资产包（新增）

#### `test_fingerprint.py` (unit)
- `test_stat_fingerprint_same_file` — 相同文件产生相同指纹
- `test_stat_fingerprint_different_file` — 不同文件产生不同指纹
- `test_dir_stat_fingerprint_deterministic` — 相同目录多次计算结果一致
- `test_fingerprint_empty_dir` — 空目录边界情况
- `test_fingerprint_permission_error` — 权限错误处理

#### `test_archive.py` (unit)
- `test_archive_file_by_fingerprint` — 基于指纹的归档去重
- `test_archive_dir` — 目录归档
- `test_archive_dedup_skips_existing` — 相同指纹不重复归档

#### `test_ignore.py` (unit)
- `test_runicornignore_rules_parsing` — 规则解析
- `test_runicornignore_matching` — 文件匹配逻辑
- `test_runicornignore_no_file` — 无 .runicornignore 时默认行为

#### `test_assets_json.py` (unit)
- `test_ensure_assets_file_creates` — 不存在时创建
- `test_update_assets_atomic` — 原子写入验证（写入中断不破坏原文件）

### 4.11 log_compat/ 兼容层（新增）

#### `test_torchvision.py` (unit)
- `test_metric_logger_forwards_to_run` — MetricLogger 写入时 events.jsonl 有对应记录（mock Run）
- `test_smoothed_value_api_compat` — median/global_avg/max/min 等属性与 torchvision 原版行为一致
- `test_metric_logger_context_manager` — 上下文管理器用法

### 4.12 CLI

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
- `test_run_best_metric_in_sqlite` — set_primary_metric → 多次 log → finish 后 SQLite 有 best_metric
- `test_run_assets_recorded_in_unified_db` — log_config/log_dataset → assets 表有记录（RF-13）
- `test_run_tags_via_set_tags` — Run 创建后通过 `storage_backend.set_tags(run_id, [...])` 写入标签，验证 experiment_tags 表有记录

#### `test_sdk_lifecycle.py`
- `test_full_lifecycle` — init → log(×N) → set_primary_metric → log_config → finish：文件系统和 SQLite 均正确
- `test_lifecycle_with_console_capture` — capture_console=True 的完整流程
- `test_lifecycle_disabled` — RUNICORN_ON=0 时全流程静默

### 5.2 Viewer API 集成（使用 TestClient）

#### `test_viewer_runs_api.py`
- `test_list_runs_from_sqlite` — 预填充 SQLite 后 GET /api/runs 返回完整列表
- `test_list_runs_fallback_to_files` — SQLite 无数据时从文件系统读取
- `test_get_run_detail` — GET /api/runs/{id} 返回详情
- `test_update_run_alias` — PATCH /api/runs/{id} 更新别名（双写 meta.json + SQLite experiments.alias）
- `test_update_run_tags` — PATCH /api/runs/{id} 更新标签（双写 meta.json + SQLite experiment_tags，set_tags 语义）
- `test_soft_delete_run` — POST /api/runs/soft-delete 批量软删除（payload 带 run_ids，双写）
- `test_restore_run` — POST /api/recycle-bin/restore 恢复（双写）
- `test_list_deleted_runs` — GET /api/recycle-bin 返回回收站列表
- `test_empty_recycle_bin` — POST /api/recycle-bin/empty 永久删除
- `test_get_run_assets` — GET /api/runs/{id}/assets 返回资产列表

#### `test_viewer_projects_api.py`（projects_router 实际提供 /api/paths 层级 API）
- `test_list_paths_from_sqlite` — GET /api/paths 从 SQLite 获取路径
- `test_list_path_stats` — 每个 path 的 run 数量、最新时间
- `test_list_runs_by_path` — GET /api/paths/runs 按路径筛选
- `test_path_tree` — GET /api/paths/tree 返回树形结构

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

#### `test_viewer_config_api.py`
- `test_get_user_root_dir` — GET /api/config/user_root_dir 返回当前值
- `test_set_user_root_dir` — POST /api/config/user_root_dir 持久化验证

#### `test_viewer_storage_api.py`
- `test_get_storage_stats` — GET /api/storage/stats 返回正确字段

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
5. RunicornClient 连接并读取相同数据（通过 httpx 直接访问 TestClient 暴露的临时端口，或使用 ASGI transport 桥接）
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
- `test_viewer_creates_app_successfully` — `create_app()` 返回 FastAPI 实例，断言关键路由前缀存在（`/api/health`, `/api/runs`, `/api/paths`, `/api/recycle-bin`, `/api/remote` 等）而非硬编码路由数量
- `test_viewer_startup_initializes_backend` — startup 事件后 `app.state.storage_backend` 不为 None
- `test_viewer_shutdown_closes_backend` — shutdown 事件后 backend 已关闭

---

## 七、重构项目（RF-01~RF-15）专项验证矩阵

以下列出每个 RF 项需要被测试覆盖的关键点，以及对应的测试文件：

- **RF-01** (删除空目录): 无需专项测试，import 验证即可
- **RF-02** (消除转发层): 通过 `test_sqlite_backend.py`、`test_file_utils.py` 等 storage 测试隐式覆盖（转发层已删除，直接测试真实模块即可）
- **RF-03** (config 包): `test_paths.py`, `test_user_config.py`, `test_compat_shims.py`
- **RF-04** (统一加密): `test_encryption.py`, `test_connections.py`, `test_encryption_roundtrip.py`
- **RF-05** (统一 SSH 路径): `test_connections.py`, `test_config_migration.py`
- **RF-06** (async→sync): `test_sqlite_backend.py` — 所有方法为同步调用（无 await）
- **RF-07** (消除 asyncio): `test_sdk_run.py` — SDK 直接调用 backend（无 asyncio）
- **RF-08** (client 重命名+修复): `test_http_client.py`（mock requests）, `test_client_server.py`, `test_models.py`（client/）
- **RF-09** (index 合并): `test_sqlite_backend.py` 资产方法, `test_index_db.py` 兼容 shim
- **RF-10** (workspace 降级): `test_workspace.py` — `get_workspace_root()` .git 查找、显式指定、fallback cwd（workspace 是真实模块，非兼容 shim）
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

### Phase T4: 扩展 + 资产 + E2E
extensions/ + console/ + assets/ + log_compat/ unit 测试 → E2E 全流程。
完善覆盖率，较依赖系统环境的测试（WebSocket、remote SSH、system/gpu）用 `@pytest.mark.slow` / `@pytest.mark.requires_*` marker 隔离，默认 CI 不跑。

### 预估测试用例数量
- Unit: ~220 个（含新增 assets/log_compat/workspace/_toml/rate_limits/models 补充）
- Integration: ~50 个（含新增 config_api/storage_api/recycle-bin）
- E2E: ~10 个
- **合计: ~280 个**
