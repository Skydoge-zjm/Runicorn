# src 重构进度

> 基于: refactor_proposal_v2.md
> 分支: refactor/src-restructure

---

## Phase 1: 无争议清理

| 项目 | 状态 | 完成时间 |
|------|------|----------|
| RF-01: 删除 viewer/api/modern/ 空目录 | ✅ 完成 | 2026-02-17 |
| RF-02: 消除 viewer/services/storage.py 转发层 | ✅ 完成 | 2026-02-17 |

**RF-01 详情**: 删除 `viewer/api/modern/` 目录（仅含 `__pycache__`，非 git 跟踪）。

**RF-02 详情**: 更新 10 处 import（8 处 viewer 内部 + migration.py 反向依赖 + assets/cleanup.py 反向依赖），删除 `viewer/services/storage.py` 纯转发层。验证通过：import、CLI、viewer 均正常。

---

## Phase 2: 配置体系重构

| 项目 | 状态 | 完成时间 |
|------|------|----------|
| RF-03: 将配置体系统一为 config/ 包 | ✅ 完成 | 2026-02-17 |
| RF-04: 统一两套加密系统 | ✅ 完成 | 2026-02-17 |
| RF-05: 统一 SSH 连接保存的双代码路径 | ✅ 完成 | 2026-02-17 |

**RF-03 详情**: 将 config.py (307 行) 拆分为 config/ 包 (paths.py, user_config.py, connections.py, rate_limits.py) + 迁入 registry.py → config/registry.py, rnconfig/loader.py → config/rnconfig.py, 提取共享 TOML 基础设施 _toml.py。rate_limits.json 移至 config/_defaults/。registry.py 和 rnconfig/ 保留为兼容 shim。config/__init__.py re-export 所有公开符号，13 个下游消费者无需修改 import。

**RF-04+RF-05 详情**: 统一加密为 Fernet，统一 SSH 连接存储为 connections.json。encryption.py 新增 SENSITIVE_FIELDS、_try_decrypt_xor_legacy()、decrypt_password() 兼容两种格式。connections.py 重写：load/save 加解密所有敏感字段，get_ssh_connections/save_ssh_connections 委托给 Fernet 路径，新增 _migrate_legacy_xor_connections() 自动迁移 config.json 中的 XOR 数据，取消 10 条连接限制。security/__init__.py 主导出切换为 encryption.py，credentials.py 保留为 deprecated。

---

## Phase 3: 架构改善

| 项目 | 状态 | 完成时间 |
|------|------|----------|
| RF-06: storage backends async→sync | ✅ 完成 | 2026-02-17 |
| RF-07: 消除 sdk.py asyncio 裸调用 | ✅ 完成 | 2026-02-17 |

**RF-06+RF-07 详情**: backends.py 中 StorageBackend ABC 及三个实现类（SQLiteStorageBackend, FileStorageBackend, HybridStorageBackend）全部方法从 async def 改为 def。migration.py 同步化。sync_utils.py 简化为直接调用的薄包装（保留向后兼容）。sdk.py 中 3 处 asyncio 三段式 fallback（summary/update_best_metric/finish）替换为直接同步调用，删除 import asyncio。

| RF-15: 统一目录布局假设 | ✅ 完成 | 2026-02-17 |

**RF-15 详情**: CLI export 命令和 export-data 命令改用 iter_all_runs()/find_run_dir_by_id() 替代手动遍历，同时支持新布局（runs/<path>/<id>）和旧布局（<project>/<name>/runs/<id>）。viewer/api/storage.py 的 get_storage_stats() 改用 iter_all_runs() 统计，输出字段从 projects_count/experiments_count 简化为 paths_count。extensions/experiment.py 的 _find_run_path() 新增新布局路径 + find_run_dir_by_id() fallback。

| RF-11: 删除 FileStorageBackend 半成品 | ✅ 完成 | 2026-02-17 |

**RF-11 详情**: 删除 FileStorageBackend（半成品，多处 Placeholder，create_experiment 访问不存在的 experiment.project/name）和 HybridStorageBackend（依赖前者，同样不可用）。FilesToSQLiteFileReader 从继承 FileStorageBackend 改为继承 StorageBackend，新增 _experiments 缓存使 get_experiment/get_metrics 可用，_load_experiment_from_files 改用 path 字段替代 project/name，_verify_migration 同样修正。ensure_modern_storage() 去除 FileStorageBackend/HybridStorageBackend 回退路径，统一返回 SQLiteStorageBackend。storage/__init__.py 和 sdk.py 导出同步更新。

| RF-12: 处理 modern_storage.py | ✅ 完成 | 2026-02-17 |

**RF-12 详情**: 删除 viewer/services/modern_storage.py（未接入任何 API 路由，且含硬错误：experiment.project/name 不存在、QueryParams(project=...) TypeError，RF-11 删除 FileStorageBackend/HybridStorageBackend 后导入已无法成功）。移除 viewer/__init__.py shutdown 事件中的 close_storage_service() 调用（原本也是空操作）。待 RF-14（Viewer 切换到 SQLite 读取）实施时重新设计。

---

## Phase 4: 小包合并 + 客户端修复

| 项目 | 状态 | 完成时间 |
|------|------|----------|
| RF-09: index/ → storage/index_db.py | ✅ 完成 | 2026-02-17 |

**RF-09 详情**: git mv index/db.py → storage/index_db.py。sdk.py 和 assets/cleanup.py 的 import 改为 from .storage.index_db import IndexDb。index/__init__.py 保留为兼容 shim。额外修复: file_utils.py 对 sdk.py 的循环依赖——将顶层 from ..sdk import DEFAULT_DIRNAME, _default_storage_dir 改为 get_storage_root() 内的懒加载 import，打破 sdk → storage → file_utils → sdk 循环链。
| RF-10: workspace/ → workspace.py | 🔲 待开始 | - |
| RF-08: 修复 + 重命名 api/ → client/ | 🔲 待开始 | - |

---

## Phase 5: 远期架构演进

| 项目 | 状态 | 完成时间 |
|------|------|----------|
| RF-13: 合并两个 SQLite 数据库 | 🔲 待开始 | - |
| RF-14: Viewer 切换到 SQLite 读取 | 🔲 待开始 | - |
