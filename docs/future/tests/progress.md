# Runicorn 测试开发进度

> 分支: test/comprehensive
> 开始时间: 2026-02-19
> 配套计划: docs/todo/test_plan.md v1.1

## Phase T1: 基础设施 + 存储层 ✅ 完成

| 模块 | 状态 | 用例数 | 备注 |
|------|------|--------|------|
| T1.1 测试基础设施 | ✅ | — | conftest + fixtures + 目录骨架 |
| T1.2 config/_toml.py | ✅ | 6 | TOML 缓存加载/失效/默认值 |
| T1.3 config/paths.py | ✅ | 7+3skip | 跨平台路径; Py3.13 monkeypatch os.name 不可用 |
| T1.4 config/user_config.py | ✅ | 7 | 发现 bug: save_user_config 无法删键 |
| T1.5 config/connections.py | ✅ | 9 | Fernet 加密, CRUD, legacy XOR 迁移 |
| T1.6 config/rnconfig + registry | ✅ | 9 | 单例加载 + 注册表查找 |
| T1.7 config/rate_limits.py | ✅ | 4 | 限速配置读取 |
| T1.8 兼容 shim | ✅ | 4 | 兼容垫片转发 |
| T1.9 storage/models.py | ✅ | 18 | 含 legacy project/name 转换 |
| T1.10 storage/sql_utils + schema | ✅ | 11 | 列名白名单 + DDL 完整性/幂等 |
| T1.11 storage/backends.py | ✅ | 45 | ConnectionPool 4 + SQLiteBackend 41 |
| T1.12 storage/file_utils.py | ✅ | 27 | 新旧布局, soft-delete, process alive |
| T1.13 storage/migration + index_db | ✅ | 23 | migration 12 + index_db 11 |

**T1 合计: 170 passed, 3 skipped**

## Phase T2: SDK + Viewer ✅ 完成

| 模块 | 状态 | 用例数 | 备注 |
|------|------|--------|------|
| T2.1 enabled.py | ✅ | 12 | is_enabled, set/reset, NoOpRun, context manager, 接口一致性 |
| T2.1 workspace.py | ✅ | 3 | .git 查找, explicit_root, fallback cwd |
| T2.2 sdk.py normalize_path + helpers | ✅ | 13 | 含 _default_storage_dir, _gen_run_id |
| T2.3 sdk.py Run class core | ✅ | 18 | init, log, primary metric, finish, context manager, SQLite |
| T2.4 sdk.py media + assets | ✅ | 11 | log_image(bytes/path/PIL/numpy), log_text, log_config, log_dataset, log_pretrained |
| T2.5 cli.py | ✅ | 10 | 8 subcommand --help + no-subcommand + config --show |
| T2.6 viewer listdir_cache | ✅ | 8 | rate limit, cache hit/miss/expiry, eviction, invalidate, stats |
| T2.6 viewer incremental_cache | ✅ | 7 | full read, cache hit, incremental, truncation, stats, eviction |
| T2.7 viewer db_reader | ✅ | 11 | get_backend, list_runs, find_run_entry_fast, sync_filesystem |
| T2.8 integration sdk_storage | ✅ | 6 | SDK→SQLite 双写: metrics, experiment, finish, best_metric, assets |
| T2.8 integration sdk_lifecycle | ✅ | 3 | 完整训练流程, 失败流程, 资产流程 |

**T2 合计: 102 passed, 0 skipped**
**T1+T2 总计: 272 passed, 3 skipped**

发现 Bug: Run.finish() 二次调用死锁（详见下方 Bug 列表 #2）

## Phase T3: 安全 + 客户端
⏳ 待 T2 完成后开始

## Phase T4: 扩展 + 资产 + E2E
⏳ 待 T3 完成后开始

## 发现的 Bug
（测试过程中发现的 bug 记录在此，遵循 .warprules 规则 7：测试代码和修复分开提交）

1. **save_user_config 无法删键** — `config/user_config.py` 的 `save_user_config()` 使用 dict merge 更新，无法删除已有键。导致 `_migrate_legacy_xor_connections()` 迁移后 `ssh_connections` 残留在 config.json 中。记录于 `test_connections.py:152-158`。状态：待修复。

2. **Run.finish() 二次调用死锁** — `sdk.py` 的 `finish()` 方法调用 `storage_backend.close()` 关闭 ConnectionPool（清空队列并关闭所有连接），但未将 `self.storage_backend` 置为 `None`。第二次 `finish()` 时 `if self.storage_backend:` 仍为 True，调用 `update_experiment()` → `pool.get()` 在空队列上永久阻塞。修复方案：`close()` 后加 `self.storage_backend = None`。记录于 `test_sdk_run.py::TestRunFinish::test_run_double_finish_idempotent`（测试中以 `RUNICORN_DISABLE_MODERN_STORAGE=1` 绕过）。状态：待修复。

---
*此文档为唯一进度文档，遵循 .warprules 规则 11*
