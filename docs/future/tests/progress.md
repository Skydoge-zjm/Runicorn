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

## Phase T2: SDK + Viewer
⏳ 待开始

## Phase T3: 安全 + 客户端
⏳ 待 T2 完成后开始

## Phase T4: 扩展 + 资产 + E2E
⏳ 待 T3 完成后开始

## 发现的 Bug
（测试过程中发现的 bug 记录在此，遵循 .warprules 规则 7：测试代码和修复分开提交）

1. **save_user_config 无法删键** — `config/user_config.py` 的 `save_user_config()` 使用 dict merge 更新，无法删除已有键。导致 `_migrate_legacy_xor_connections()` 迁移后 `ssh_connections` 残留在 config.json 中。记录于 `test_connections.py:152-158`。状态：待修复。

---
*此文档为唯一进度文档，遵循 .warprules 规则 11*
