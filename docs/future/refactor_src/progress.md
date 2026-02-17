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
| RF-04: 统一两套加密系统 | 🔲 待开始 | - |
| RF-05: 统一 SSH 连接保存的双代码路径 | 🔲 待开始 | - |

**RF-03 详情**: 将 config.py (307 行) 拆分为 config/ 包 (paths.py, user_config.py, connections.py, rate_limits.py) + 迁入 registry.py → config/registry.py, rnconfig/loader.py → config/rnconfig.py, 提取共享 TOML 基础设施 _toml.py。rate_limits.json 移至 config/_defaults/。registry.py 和 rnconfig/ 保留为兼容 shim。config/__init__.py re-export 所有公开符号，13 个下游消费者无需修改 import。

---

## Phase 3: 架构改善

| 项目 | 状态 | 完成时间 |
|------|------|----------|
| RF-06: storage backends async→sync | 🔲 待开始 | - |
| RF-07: 消除 sdk.py asyncio 裸调用 | 🔲 待开始 | - |
| RF-15: 统一目录布局假设 | 🔲 待开始 | - |
| RF-11: 删除 FileStorageBackend 半成品 | 🔲 待开始 | - |
| RF-12: 处理 modern_storage.py | 🔲 待开始 | - |

---

## Phase 4: 小包合并 + 客户端修复

| 项目 | 状态 | 完成时间 |
|------|------|----------|
| RF-09: index/ → storage/index_db.py | 🔲 待开始 | - |
| RF-10: workspace/ → workspace.py | 🔲 待开始 | - |
| RF-08: 修复 + 重命名 api/ → client/ | 🔲 待开始 | - |

---

## Phase 5: 远期架构演进

| 项目 | 状态 | 完成时间 |
|------|------|----------|
| RF-13: 合并两个 SQLite 数据库 | 🔲 待开始 | - |
| RF-14: Viewer 切换到 SQLite 读取 | 🔲 待开始 | - |
