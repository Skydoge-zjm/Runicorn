# Runicorn 重构提案 v2

> 版本: 2.3
> 日期: 2026-02-17（v2.3 修订：根据 review_v2_new 评阅意见修正事实错误、补充遗漏）
> 分支: refactor/code-cleanup
> 配套文档: src_structure.md（代码地图）、architecture_and_proposal.md（v1 提案，本文件替代之）

---

## 目录

1. [执行摘要](#一执行摘要)
2. [重构项目清单](#二重构项目清单)
   - RF-01: 删除残留代码和空目录
   - RF-02: 消除 viewer/services/storage.py 纯转发层
   - RF-03: 将配置体系统一为 config/ 包
   - RF-04: 统一两套加密系统
   - RF-05: 统一 SSH 连接保存的双代码路径
   - RF-06: 将 storage backends 从 async 改为 sync
   - RF-07: 消除 sdk.py 中的 asyncio 裸调用
   - RF-08: 将 api/ 客户端库重命名为 client/
   - RF-09: 合并 index/ 到 storage/
   - RF-10: 将 workspace/ 包降级为单文件
   - RF-11: 删除或完成 FileStorageBackend 半成品
   - RF-12: 决定 viewer/services/modern_storage.py 命运
   - RF-13: 合并两个 SQLite 数据库（远期）
   - RF-14: 让 Viewer 读取端切换到 SQLite（远期）
   - RF-15: 统一目录布局假设（path vs project/name）
3. [执行计划](#三执行计划)
4. [风险评估](#四风险评估)
5. [验证策略](#五验证策略)

---

## 一、执行摘要

### 当前状态

Runicorn 是一个本地优先的 ML 实验追踪工具，包含 Python SDK（写入端）、FastAPI Viewer（读取端）和 React 前端。当前代码库存在以下几类技术债务：

- **残留代码**: 空目录、半成品类、死代码模块
- **功能重复**: 两套加密系统、两个 SQLite 数据库、两条 SSH 连接保存路径
- **架构错配**: storage backends 用 async 接口但所有调用方都是同步的，导致大量笨拙的 asyncio 桥接代码
- **命名冲突**: `config.py` 与 `config/` 目录同名，`api/` 与 `viewer/api/` 含义相反
- **读写不对称**: SDK 已完成文件 + SQLite 双写，但 Viewer 仍通过文件系统递归扫描读取数据

### 重构原则

1. **收益驱动**: 优先解决对代码质量和运行时性能有实质影响的问题，而非纯粹的目录整理
2. **最小变更**: 能用 1 行改动解决的问题，不做 20 个文件的重构
3. **向后兼容**: 所有重命名/移动必须保留旧 import 路径的过渡期兼容
4. **可验证**: 每个重构项独立可测试，不依赖其他项的完成

### 与 v1 提案的主要区别

| 方面 | v1 提案 | v2 提案（本文件） |
|------|---------|-------------------|
| 核心关注 | 目录结构重排 | 架构问题 + 代码清理 |
| config.py 处理 | 拆分为 config/ 包（高风险） | 采纳 v1 思路合并为 config/ 包，通过 re-export 保持向后兼容 |
| async/sync 问题 | 未提及 | 核心重构项（RF-06, RF-07） |
| 加密统一 | 提到但无迁移方案 | 含完整数据迁移策略（RF-04） |
| SQLite 读取切换 | 未提及 | 明确纳入远期计划（RF-14） |
| sdk.py 巨型文件 | 未提及 | 作为观察项记录，当前不拆分 |

---

## 二、重构项目清单

---

### RF-01: 删除残留代码和空目录

**优先级**: P0（立即执行）
**风险**: 无
**预计工时**: 10 分钟

#### 现状

1. `src/runicorn/viewer/api/modern/` 是一个空目录，仅包含 `__pycache__`。这是早期尝试将 Viewer API 迁移到 modern storage 时留下的残留，后来改为在 `viewer/services/modern_storage.py` 中实现，但 `modern/` 目录未清理。

2. `src/runicorn/security/__init__.py` 当前仅导出 `credentials.py` 的符号（`CredentialManager`, `get_credential_manager`, `encrypt_password`, `decrypt_password`），未导出 `encryption.py` 的同名函数。这导致 `from runicorn.security import encrypt_password` 得到的是 XOR 版本而非 Fernet 版本，属于易混淆的 API 设计（详见 RF-04）。

#### 涉及文件

- `src/runicorn/viewer/api/modern/` — 整个目录删除
- `src/runicorn/viewer/api/modern/__pycache__/` — 随目录一起删除

#### 改进建议

直接删除 `viewer/api/modern/` 目录及其所有内容。

#### 动机

空目录占据代码树空间，误导开发者以为此处有功能实现。删除后消除混淆。

---

### RF-02: 消除 viewer/services/storage.py 纯转发层

**优先级**: P0（立即执行）
**风险**: 低（仅 import 路径变更）
**预计工时**: 30 分钟

#### 现状

`src/runicorn/viewer/services/storage.py` 是一个纯 re-export 文件，没有任何自有逻辑：

```python
# viewer/services/storage.py 的全部实质内容
from ...storage.file_utils import (
    RunEntry, get_storage_root, read_json, write_json,
    is_process_alive, update_status_if_process_dead,
    is_run_deleted, soft_delete_run, restore_run,
    list_run_dirs_legacy, iter_all_runs, find_run_dir_by_id,
    periodic_status_check
)
```

这个文件存在的唯一原因是历史上 storage 逻辑曾直接写在 viewer/services/ 下，后来代码被提取到 `storage/file_utils.py`，但原位置保留为兼容层。

#### 涉及文件

**被删除的文件**:
- `src/runicorn/viewer/services/storage.py`

**需要更新 import 的文件**（10 处）:

Viewer 内部（8 处）:
- `src/runicorn/viewer/__init__.py` — 第 20 行: `from .services.storage import get_storage_root, periodic_status_check`
- `src/runicorn/viewer/api/runs.py` — 第 21 行: `from ..services.storage import (iter_all_runs, find_run_dir_by_id, ...)`
- `src/runicorn/viewer/api/health.py` — 第 11 行: `from ..services.storage import iter_all_runs, read_json, ...`
- `src/runicorn/viewer/api/metrics.py` — 第 24 行: `from ..services.storage import find_run_dir_by_id`
- `src/runicorn/viewer/api/config.py` — 第 22 行: `from ..services.storage import get_storage_root`
- `src/runicorn/viewer/api/projects.py` — 第 21 行: `from ..services.storage import (iter_all_runs, read_json, ...)`
- `src/runicorn/viewer/api/export.py` — 第 16 行: `from ..services.storage import ...`
- `src/runicorn/viewer/api/import_.py` — 第 17 行: `from ..services.storage import ...`

反向依赖（2 处）:
- `src/runicorn/storage/migration.py` — 第 214 行: `from ..viewer.services.storage import iter_all_runs, read_json`（storage 层依赖 viewer 层）
- `src/runicorn/assets/cleanup.py` — 第 59 行: `from ..viewer.services.storage import find_run_dir_by_id`（assets 层依赖 viewer 层）

#### 改进建议

1. 将上述 8 个 viewer 内部文件的 import 从 `from ..services.storage import X` 改为 `from ...storage.file_utils import X`
2. 修复 `migration.py` 的反向依赖，改为 `from .file_utils import iter_all_runs, read_json`
3. 修复 `assets/cleanup.py` 的反向依赖，改为 `from ..storage.file_utils import find_run_dir_by_id`
4. 删除 `viewer/services/storage.py`

#### 动机

消除无逻辑的间接层。每次阅读 viewer 代码时，开发者需要先跳到 `services/storage.py`，发现它只是转发，再跳到 `storage/file_utils.py` 才能看到实际逻辑。删除后减少一次无意义跳转。同时修复 migration.py 对 viewer 层的反向依赖。

---

### RF-03: 将配置体系统一为 config/ 包

**优先级**: P1（Phase 2 首项）
**风险**: 中（13 个文件导入 config.py，但通过 re-export 保持向后兼容）
**预计工时**: 3-4 小时

#### 现状

`src/runicorn/` 下存在四个相关但分散的配置组件：

**组件 1: `config.py`（307 行）— 基础设施层**

用户配置中心，承担 5 个不同职责：
- **跨平台路径解析**: `_config_root_dir()`, `get_config_file_path()`, `get_rnconfig_file_path()`, `get_registry_dir()`, `get_connections_file_path()`, `get_known_hosts_file_path()`
- **JSON 用户配置读写**: `load_user_config()`, `save_user_config()`, `get_user_root_dir()`, `set_user_root_dir()`
- **Fernet 加密 SSH 连接**: `load_saved_connections()`, `save_connections()` → 存入独立 `connections.json`
- **XOR 加密 SSH 连接**: `save_ssh_connections()`, `get_ssh_connections()`, `add_ssh_connection()`, `remove_ssh_connection()` → 存入 `config.json`
- **限流配置**: `get_rate_limit_config()`, `save_rate_limit_config()` → 优先级：用户目录 → 包内 `config/rate_limits.json` → 硬编码默认值

被 **13 个文件**导入：`sdk.py`, `cli.py`, `registry.py`, `rnconfig/loader.py`, `security/encryption.py`, `security/credentials.py`, `security/rate_limiter.py`, `remote/connection.py`, `remote/ssh_backend.py`, `remote/known_hosts.py`, `viewer/api/config.py`, `viewer/api/remote.py`, `viewer/api/ui_preferences.py`。

> **注意**: `viewer/api/__init__.py` 的 `from .config import router as config_router` 导入的是本地路由模块 `viewer/api/config.py`，而非 `runicorn.config`，不在此列表中。`runicorn/__init__.py` 也不直接导入 `config.py`（它导入的是 `.registry` 和 `.rnconfig`）。

**组件 2: `rnconfig/`（Python 包，~70 行）— 项目级 TOML 配置**

两层 TOML 配置合并：用户级 `rnconfig.toml`（路径来自 `config.py` 的 `get_rnconfig_file_path()`）+ 项目级 `rnconfig.toml`（工作区根目录）。包含线程安全的 mtime 缓存。仅 2 个公开函数（`get_effective_rnconfig()`, `load_effective_rnconfig()`），仅 1 个外部调用方（`sdk.py`）。作为独立 Python 包却依赖 `config.py`，逻辑上是配置体系的一部分。

**组件 3: `registry.py`（~100 行）— TOML 键值注册表**

纯函数式 API（`get_config(key)`, `clear_registry_cache()` 等），TOML 文件的键值存取。路径来自 `config.py` 的 `get_registry_dir()`。与 `rnconfig/` 几乎是同一模式的两份实现：

```python
# rnconfig/loader.py
_cache_lock = threading.Lock()
_effective_cache: Dict[Tuple[Path, Path], Tuple[Tuple[int, int], Dict[str, Any]]] = {}

# registry.py
_cache_lock = threading.Lock()
_toml_cache: Dict[Path, Tuple[int, Dict[str, Any]]] = {}
```

两者都实现了 TOML 加载 + 线程安全锁 + mtime 缓存失效，各写了一遍。

**组件 4: `config/`（数据目录，无 `__init__.py`）**

仅包含 `rate_limits.json`。与 `config.py` 同名，对开发者造成困惑。

#### 涉及文件

**被合并的源文件**:
- `src/runicorn/config.py` → 拆分为 `config/paths.py`, `config/user_config.py`, `config/connections.py`, `config/rate_limits.py`
- `src/runicorn/rnconfig/loader.py` → `config/rnconfig.py`
- `src/runicorn/rnconfig/__init__.py` → 改为兼容层 shim
- `src/runicorn/registry.py` → `config/registry.py`，旧文件改为兼容层 shim
- `src/runicorn/config/rate_limits.json` → `config/_defaults/rate_limits.json`

**需要更新 import 的文件（13 个）**: 通过 `config/__init__.py` 的 re-export，绝大多数 `from runicorn.config import X` 的现有 import 无需修改。仅直接引用 `rnconfig` 或 `registry` 的路径需要适配，且旧路径通过兼容层 shim 继续工作。

#### 改进建议

**目标结构**:

```
config/
├── __init__.py        — re-export 所有公开 API（向后兼容）
├── paths.py           — _config_root_dir() + 所有 get_*_path() 函数
├── user_config.py     — load/save_user_config(), get/set_user_root_dir()
├── connections.py     — 统一的 SSH 连接管理（为 RF-04/05 做准备）
├── rate_limits.py     — get/save_rate_limit_config()
├── rnconfig.py        — get_effective_rnconfig() / load_effective_rnconfig()（来自 rnconfig/loader.py）
├── registry.py        — get_config() 等函数式 API（来自 registry.py）
├── _toml.py           — 共享 TOML 加载 + mtime 缓存基础设施
└── _defaults/
    └── rate_limits.json
```

**关键实现要点**:

1. **`config/__init__.py` 完整 re-export**: 保持 `from runicorn.config import load_user_config` 等现有 import 全部可用，零 breaking change

```python
# config/__init__.py
from .paths import (
    _config_root_dir,  # 私有但被 security/ 模块直接引用，必须 re-export
    get_config_file_path, get_rnconfig_file_path,
    get_registry_dir, get_connections_file_path, get_known_hosts_file_path,
)
from .user_config import (
    load_user_config, save_user_config,
    get_user_root_dir, set_user_root_dir,
)
from .connections import (
    load_saved_connections, save_connections,
    save_ssh_connections, get_ssh_connections,
    add_ssh_connection, remove_ssh_connection,
)
from .rate_limits import get_rate_limit_config, save_rate_limit_config
```

> **注意**: `_config_root_dir` 虽是私有函数，但 `security/encryption.py:21` 和 `security/credentials.py:40` 均通过 `from ..config import _config_root_dir` 直接引用。如果不在 `config/__init__.py` 中 re-export，这两个 import 会 break。

2. **旧路径兼容 shim**: 保留 `rnconfig/__init__.py` 和根级 `registry.py` 作为转发层，现有 import 不受影响

```python
# src/runicorn/rnconfig/__init__.py (兼容层)
from ..config.rnconfig import get_effective_rnconfig, load_effective_rnconfig
```

```python
# src/runicorn/registry.py (兼容层)
from .config.registry import get_config, clear_registry_cache
```

3. **`config/_toml.py` 共享基础设施**: 提取 `rnconfig/loader.py` 和 `registry.py` 中重复的 TOML 加载 + mtime 缓存逻辑为一个内部模块，消除代码重复

4. **`config/_defaults/`**: 下划线前缀标记为内部数据目录，吸收原 `config/rate_limits.json`

#### 与 RF-04/RF-05 的关系

RF-03 完成后，`config.py` 中的 SSH 连接代码被拆分到独立的 `config/connections.py`（约 140 行）。RF-04（统一加密）和 RF-05（统一 SSH 路径）在此基础上修改 `connections.py` 会更清晰，改动范围更明确。因此 RF-03 是 RF-04/05 的前置依赖。

#### 动机

1. **config.py 职责过多**: 307 行 / 5 个关注点 / 13 个文件依赖，任何修改（如 RF-04/05 的加密统一）都要在大文件中小心操作
2. **消除代码重复**: `rnconfig/` 和 `registry.py` 的 TOML + mtime 缓存模式各实现了一遍
3. **rnconfig/ 作为独立包不合理**: 70 行、2 个函数、1 个调用方，却是完整 Python 包，且反向依赖 `config.py`
4. **解决命名冲突**: `config.py` 与 `config/` 同级同名
5. **为后续重构奠基**: RF-04/05 的 SSH 连接修改在拆分后的 `connections.py` 上操作比在 307 行的 `config.py` 中操作更安全

---

### RF-04: 统一两套加密系统

**优先级**: P1（本阶段执行）
**风险**: 中（涉及已有加密数据的迁移）
**预计工时**: 2 小时

#### 现状

`src/runicorn/security/` 下存在两个功能重叠的加密模块：

**模块 A: `credentials.py`（XOR 混淆）**
- 类: `CredentialManager`
- 密钥文件: `%APPDATA%/Runicorn/.credential_key`（32 字节随机数据）
- 加密方式: XOR 循环密钥 + base64 编码
- 标记前缀: `ENC:`
- 被调用处: `config.py` 第 175-197 行的 `save_ssh_connections()` / `get_ssh_connections()`
- 数据存储位置: `config.json` 的 `ssh_connections` 字段
- 自述: "This is NOT cryptographically secure but prevents casual viewing"

**模块 B: `encryption.py`（Fernet 对称加密）**
- 函数: `encrypt_password()` / `decrypt_password()` / `is_encrypted()`
- 密钥文件: `%APPDATA%/Runicorn/.secret.key`（Fernet 生成的 base64 密钥）
- 加密方式: `cryptography.Fernet`（AES-128-CBC + HMAC-SHA256）
- 标记特征: Fernet token 以 `gAAAAA` 开头
- 被调用处: `config.py` 第 79-139 行的 `load_saved_connections()` / `save_connections()`
- 数据存储位置: `connections.json` 独立文件
- 外部依赖: `cryptography` 库

**两套系统的调用方对比**:

| 功能 | XOR 路径 (credentials.py) | Fernet 路径 (encryption.py) |
|------|--------------------------|---------------------------|
| 保存 | `save_ssh_connections()` | `save_connections()` |
| 读取 | `get_ssh_connections()` | `load_saved_connections()` |
| 存储 | config.json 内嵌 | connections.json 独立文件 |
| 被谁调用 | `viewer/api/config.py` 第 110 行 | `viewer/api/remote.py`（如有直接调用） |

#### 涉及文件

- `src/runicorn/security/credentials.py` — 待删除
- `src/runicorn/security/encryption.py` — 保留，增加迁移辅助函数
- `src/runicorn/security/__init__.py` — 更新导出
- `src/runicorn/config.py` — 第 175-224 行 SSH 相关函数统一到 Fernet
- `src/runicorn/viewer/api/config.py` — 如有直接引用需更新

#### 改进建议

**步骤 1: 在 `encryption.py` 中添加兼容读取能力**

```python
def _try_decrypt_xor_legacy(value: str) -> Optional[str]:
    """尝试用旧 XOR 方式解密 ENC: 前缀的值（一次性迁移用）"""
    if not value or not value.startswith("ENC:"):
        return None
    try:
        from .credentials import CredentialManager
        manager = CredentialManager()
        return manager.decrypt_credential(value)
    except Exception:
        return None

def decrypt_password(encrypted_password: str) -> str:
    # 先尝试 Fernet 解密
    if is_encrypted(encrypted_password):
        cipher = _get_cipher()
        return cipher.decrypt(encrypted_password.encode('utf-8')).decode('utf-8')
    
    # 兼容旧 XOR 格式
    if encrypted_password.startswith("ENC:"):
        plain = _try_decrypt_xor_legacy(encrypted_password)
        if plain:
            return plain
    
    # 既不是 Fernet 也不是 XOR，当作明文返回
    return encrypted_password
```

**步骤 2: 扩大 `save_connections()` 的加密字段覆盖面**

当前 Fernet 路径（`save_connections()`）仅加密 `password` 字段（`config.py:118-126`），但 XOR 路径（`CredentialManager.encrypt_config()`）加密 `password, passphrase, private_key, secret, token, api_key` 共 6 个敏感字段（`credentials.py:155-164`）。`viewer/api/config.py:149-158` 的 Settings API 确实会保存 `private_key` 和 `passphrase`。

统一后 `save_connections()` 必须加密所有敏感字段，否则会出现"私钥/口令明文落盘"的安全倒退：

```python
# save_connections() 需修改为：
SENSITIVE_FIELDS = ['password', 'passphrase', 'private_key', 'secret', 'token', 'api_key']
for field in SENSITIVE_FIELDS:
    if conn_copy.get(field) and not is_encrypted(conn_copy[field]):
        conn_copy[field] = encrypt_password(conn_copy[field])
```

**步骤 3: 修复调用链中的 `is_encrypted()` guard**

当前 `load_saved_connections()` 第 89 行的逻辑是：
```python
if conn.get('password') and is_encrypted(conn['password']):
    conn['password'] = decrypt_password(conn['password'])
```

`is_encrypted()` 只检查 Fernet 的 `gAAAAA` 前缀。即使步骤 1 让 `decrypt_password()` 兼容 `ENC:` 格式，这段 guard 代码也会让 XOR 格式直接跳过解密。必须同步修改 `load_saved_connections()` 的读取逻辑：

```python
# 修改为：对所有敏感字段尝试解密（Fernet 或 XOR）
for field in SENSITIVE_FIELDS:
    value = conn.get(field)
    if value and (is_encrypted(value) or value.startswith('ENC:')):
        conn[field] = decrypt_password(value)  # decrypt_password 内部已兼容两种格式
```

**步骤 4: 统一 config.py 中的 SSH 函数**

将 `save_ssh_connections()` / `get_ssh_connections()` 的实现改为使用 Fernet 加密（调用 `encryption.py`），而不是 XOR（调用 `credentials.py`）。保留函数签名不变，对外接口无变化。

**步骤 5: 自动迁移**

在 `get_ssh_connections()` 中，读取到 `ENC:` 前缀的旧数据时，用 XOR 解密后立即用 Fernet 重新加密回写。这样用户下次读取时就已经是 Fernet 格式了。

**步骤 6: 确认 `cryptography` 依赖现状**

`encryption.py:68-70` 在缺少 `cryptography` 库时直接 `raise RuntimeError`。经核实，`cryptography>=41.0.0` **已经是** `pyproject.toml` 主依赖列表中的必选依赖（非可选依赖），因此统一后无需调整依赖配置。但应确保 `encryption.py` 中的 `RuntimeError` 错误消息清晰（提示用户重新安装包），以防依赖被意外卸载。

**步骤 7: 删除 credentials.py**

在确认迁移逻辑稳定后（可在下一个版本），删除 `credentials.py` 和 `.credential_key` 密钥文件。

#### 动机

- XOR 混淆不提供真正的安全性，代码注释自己也承认这一点
- 两套系统并存增加维护负担，开发者必须理解两种加密格式
- 两个密钥文件 (`.credential_key` + `.secret.key`) 容易混淆
- 统一后代码更安全，且只有一个密钥文件需要管理

---

### RF-05: 统一 SSH 连接保存的双代码路径

**优先级**: P1（与 RF-04 同时执行）
**风险**: 中
**预计工时**: 1.5 小时（与 RF-04 合并执行）

#### 现状

`config.py` 中存在**两条完全独立的 SSH 连接保存路径**，做着几乎相同的事：

**路径 A（旧版，XOR 加密）**:
- `save_ssh_connections(connections)` — 第 175 行
  - 调用 `credentials.py` 的 `CredentialManager.encrypt_config()`
  - 存储到 `config.json` 的 `ssh_connections` 字段
- `get_ssh_connections()` — 第 186 行
  - 调用 `credentials.py` 的 `CredentialManager.decrypt_config()`
- `add_ssh_connection(connection)` — 第 200 行
  - 基于 `host:port@username` 做去重，保留最近 10 条
- `remove_ssh_connection(key)` — 第 220 行
- 被 `viewer/api/config.py` 第 110 行 (`get_ssh_connections()`) 和第 164 行 (`add_ssh_connection()`) 调用

**路径 B（新版，Fernet 加密）**:
- `save_connections(connections)` — 第 102 行
  - 调用 `encryption.py` 的 `encrypt_password()`
  - 存储到独立的 `connections.json` 文件
- `load_saved_connections()` — 第 79 行
  - 调用 `encryption.py` 的 `decrypt_password()` + `is_encrypted()`
- 被 `viewer/api/remote.py` 和 `viewer/__init__.py` 使用（Remote Viewer 功能）

**关键区别**:
- 路径 A 存入 `config.json`（与其他配置混存），路径 B 存入独立 `connections.json`
- 路径 A 加密 6 个敏感字段（password/passphrase/private_key/secret/token/api_key），路径 B 只加密 password 字段
- 路径 A 有 CRUD 操作（add/remove）且限制最近 10 条（`config.py:214-215`），路径 B 只有 load/save 且不限条数
- 两条路径的数据**不互通** — 通过路径 A 保存的连接，路径 B 读不到，反之亦然

#### 涉及文件

- `src/runicorn/config.py` — 第 79-224 行
- `src/runicorn/viewer/api/config.py` — SSH 连接相关端点
- `src/runicorn/viewer/api/remote.py` — Remote Viewer 连接（如使用路径 B）

#### 改进建议

统一到**路径 B 的存储方式**（独立 `connections.json` + Fernet 加密），但保留路径 A 的 CRUD 接口（`add_ssh_connection` / `remove_ssh_connection` 函数签名不变）：

1. `save_ssh_connections()` 内部改为调用 `save_connections()`
2. `get_ssh_connections()` 内部改为调用 `load_saved_connections()`
3. 首次执行时，检测 `config.json` 中是否有 `ssh_connections` 字段，若有则迁移到 `connections.json` 并从 `config.json` 中删除
4. `add_ssh_connection()` / `remove_ssh_connection()` 底层改为操作 `connections.json`
5. 统一后 `save_connections()` 必须加密所有敏感字段（password/passphrase/private_key 等），不能只加密 password（详见 RF-04 步骤 2）
6. **Schema 统一决策**: 路径 A 限制最近 10 条，路径 B 不限。建议统一后**不限制条数**（10 条限制过于保守），但可在 UI 层做分页/排序

#### 动机

两条路径做同一件事但数据不互通，是用户可见的 bug：用户在 Settings 页面保存的 SSH 连接，在 Remote Viewer 页面可能看不到。统一后消除此问题。

---

### RF-06: 将 storage backends 从 async 改为 sync

**优先级**: P1（本阶段执行）
**风险**: 中高（接口变更影响所有后端实现）
**预计工时**: 3 小时

#### 现状

`src/runicorn/storage/backends.py` 中的 `StorageBackend` 抽象基类定义了 10 个抽象方法，全部声明为 `async`：

```python
class StorageBackend(ABC):
    @abstractmethod
    async def create_experiment(self, experiment: ExperimentRecord) -> str: ...
    @abstractmethod
    async def update_experiment(self, exp_id: str, updates: Dict[str, Any]) -> bool: ...
    @abstractmethod
    async def get_experiment(self, exp_id: str) -> Optional[ExperimentRecord]: ...
    @abstractmethod
    async def list_experiments(self, query: QueryParams) -> List[ExperimentRecord]: ...
    @abstractmethod
    async def count_experiments(self, query: QueryParams) -> int: ...
    @abstractmethod
    async def log_metrics(self, exp_id: str, metrics: List[MetricRecord]) -> bool: ...
    @abstractmethod
    async def get_metrics(self, exp_id: str, ...) -> List[MetricRecord]: ...
    @abstractmethod
    async def soft_delete_experiments(self, exp_ids: List[str], ...) -> Dict[str, bool]: ...
    @abstractmethod
    async def restore_experiments(self, exp_ids: List[str]) -> Dict[str, bool]: ...
    @abstractmethod
    async def get_storage_stats(self) -> StorageStats: ...
```

**但所有三个实现类的方法体都是纯同步代码**（无 await）：
- `SQLiteStorageBackend` — 所有方法直接调用 `self.pool.get_connection()` → `conn.execute()` → `self.pool.return_connection()`，没有任何 `await` 语句
- `FileStorageBackend` — 所有方法直接读写文件，没有任何 `await` 语句
- `HybridStorageBackend` — 调用前两者，同样没有独立的异步操作

**所有调用方也都是同步上下文**：
- `sdk.py` 是纯同步代码，需要通过 `sync_utils.py` 的 `run_async_safe()` 或直接 `asyncio.run()` 来调用
- `viewer/` 虽然是 FastAPI（async），但 metrics API 已经通过 `ThreadPoolExecutor` 在线程池中执行同步 I/O

这意味着 async 声明**没有提供任何并发优势**，反而增加了复杂度。

#### 涉及文件

- `src/runicorn/storage/backends.py` — StorageBackend ABC + 三个实现类（约 900 行）
- `src/runicorn/storage/sync_utils.py` — 改造后大部分内容可删除
- `src/runicorn/storage/migration.py` — `StorageMigrator`, `FilesToSQLiteMigrator`, `ensure_modern_storage()` 等
- `src/runicorn/viewer/services/modern_storage.py` — `ModernStorageService`（如保留）
- `src/runicorn/sdk.py` — 第 475-505 行 `_init_modern_storage()`，第 573-597 行 `log()` 中的双写

#### 改进建议

1. 将 `StorageBackend` ABC 的所有方法从 `async def` 改为 `def`
2. 相应更新 `SQLiteStorageBackend`、`FileStorageBackend`、`HybridStorageBackend` 的所有方法签名
3. 删除方法中不存在的 `await`（当前这些方法虽然声明为 async 但内部没有 await）
4. `sync_utils.py` 中的 `run_async_safe()`、`create_experiment_sync()`、`log_metrics_sync()` 等包装函数可以简化为直接调用
5. `migration.py` 中的 `migrate_all()`、`ensure_modern_storage()` 等改为同步函数
6. 如果 Viewer 未来需要异步调用（如 RF-14），可以在 FastAPI 路由层使用 `run_in_executor` 将同步调用放入线程池

#### 动机

- **消除复杂度**: 当前为了在同步环境中调用 async 方法，`sdk.py` 中出现了 3 处丑陋的三段式 fallback 代码（尝试获取 event loop → 判断是否 running → 选择 create_task / run_until_complete / asyncio.run），这是 bug 和竞态条件的温床
- **消除 sync_utils.py**: 这个文件存在的唯一原因是桥接 async 后端和 sync 调用方，后端改为 sync 后它就不再需要了
- **SQLite 操作天然是同步的**: `sqlite3` 标准库是同步 API，将其包在 async 壳里再用 sync 调用是多此一举
- **不损失性能**: async 的优势在于 I/O 等待期间可以处理其他请求，但 SQLite 的本地文件 I/O 几乎无等待时间，async 没有实际收益

---

### RF-07: 消除 sdk.py 中的 asyncio 裸调用

**优先级**: P1（依赖 RF-06 完成）
**风险**: 低（RF-06 完成后此项为自然结果）
**预计工时**: 1 小时

#### 现状

`sdk.py` 中有至少 3 处直接使用 asyncio 调用 storage backend 方法的代码，均采用相同的三段式 fallback 模式：

**位置 1: `summary()` 方法，第 899-919 行**
```python
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(self.storage_backend.update_experiment(self.id, storage_updates))
    else:
        loop.run_until_complete(self.storage_backend.update_experiment(self.id, storage_updates))
except RuntimeError:
    asyncio.run(self.storage_backend.update_experiment(self.id, storage_updates))
```

**位置 2: `_update_best_metric()` 方法，第 958-965 行** — 完全相同的模式

**位置 3: `finish()` 方法，第 1026-1033 行** — 完全相同的模式

另外，`_init_modern_storage()` 和 `log()` 方法通过 `sync_utils.py` 的包装函数调用，稍微好些但仍有间接层。

#### 涉及文件

- `src/runicorn/sdk.py` — 第 897-922, 948-968, 1017-1037 行

#### 改进建议

RF-06 完成后（backend 方法变为同步），这些代码全部简化为直接调用：

```python
# 改造前（三段式 fallback）
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(self.storage_backend.update_experiment(self.id, updates))
    else:
        loop.run_until_complete(self.storage_backend.update_experiment(self.id, updates))
except RuntimeError:
    asyncio.run(self.storage_backend.update_experiment(self.id, updates))

# 改造后（直接调用）
self.storage_backend.update_experiment(self.id, updates)
```

同时可以删除 `sdk.py` 中所有 `import asyncio` 语句（目前 sdk.py 不需要 asyncio）。

#### 动机

三段式 fallback 有以下问题：
- `create_task()` 路径在 running loop 中创建了一个未被 await 的 task，结果实际上是 fire-and-forget，更新可能丢失
- 三种路径的行为不一致（有的是同步等待完成，有的是异步 fire-and-forget）
- 代码重复 3 次，违反 DRY 原则

---

### RF-08: 修复并重命名 api/ 客户端库为 client/

**优先级**: P3（降级，应先修复再改名）
**风险**: 低（改名本身），中（修复客户端需对齐服务端 API）
**预计工时**: 1 小时（仅改名），3-4 小时（含修复）

#### 现状

`src/runicorn/api/` 是 SDK 端的 HTTP 客户端库（发送请求到 Viewer），但 `src/runicorn/viewer/api/` 是 Viewer 端的 HTTP 服务端路由（处理请求）。两者都叫 `api`，职责完全相反。

`src/runicorn/api/` 包含：
- `client.py` — `RunicornClient` HTTP 客户端（封装 requests）
- `remote.py` — `RemoteAPI` 远程 Viewer 操作
- `models.py` — 客户端数据模型
- `exceptions.py` — API 异常类
- `utils.py` — 工具函数（需要 pandas）

**⚠️ 客户端当前已不可用**（与 Viewer API 严重不一致，共 6 处）：

1. **健康检查失败**: `client.py:81` 检查 `status == "healthy"`，但服务端 `viewer/api/health.py:33` 返回 `{"status": "ok"}` → `_verify_connection()` 始终抛出 `APIConnectionError`
2. **核心端点不存在**: `client.py:195` 调用 `GET /api/experiments`，但 `viewer/api/experiments.py` 没有此路由（只有 `POST /experiments/tag`、`GET /experiments/search`、`DELETE /experiments/delete`）→ `list_experiments()` 始终 404
3. **指标端点路径错误**: `client.py:251` 请求 `GET /api/metrics/{run_id}`，但服务端路由是 `GET /api/runs/{run_id}/metrics`（`metrics.py:152`）和 `GET /api/runs/{run_id}/metrics_step`（`metrics.py:221`）→ `get_metrics()` 始终 404
4. **配置更新方法不存在**: `client.py:292` 用 `PUT /api/config`，但服务端只有 `GET /api/config`（`config.py:28`）和 `POST /api/config/user_root_dir`（`config.py:46`），没有 PUT → `update_config()` 始终 405
5. **导出端点路径错误**: `client.py:279` 用 `POST /api/export`，但服务端路由是 `GET /api/export/{run_id}/csv`（`export.py:31`）和 `GET /api/export/{run_id}/report`（`export.py:71`）→ `export_experiment()` 始终 404
6. **GPU 端点路径错误**: `client.py:298` 请求 `GET /api/gpu`，但服务端路由是 `GET /api/gpu/telemetry`（`gpu.py:17`）→ `get_gpu_info()` 始终 404

这意味着只改名是把"坏的东西搬家"，收益极低。

#### 涉及文件

- `src/runicorn/api/` — 重命名为 `src/runicorn/client/`
- `src/runicorn/api/client.py` — 重命名为 `src/runicorn/client/http.py`（避免 `client/client.py`）
- `src/runicorn/__init__.py` — 如果有从 api 导出的符号
- 外部用户代码 — `from runicorn.api import RunicornClient` 需要兼容

#### 改进建议

**推荐方案：先修复再改名**

1. **修复 health check**: `_verify_connection()` 中将 `"healthy"` 改为 `"ok"`（对齐服务端）
2. **修复 `list_experiments()`**: 改为调用 `GET /api/runs`（服务端实际存在的路由），或改为 `GET /api/experiments/search`
3. 将 `api/` 目录重命名为 `client/`
4. 将 `client.py` 重命名为 `http.py`
5. 保留 `api/__init__.py` 作为兼容层（re-export 所有符号），并添加 deprecation warning

**备选方案：标记为弃用**

如果短期内不打算维护客户端库，直接在 `api/__init__.py` 和 README 中标注 experimental/deprecated，避免用户依赖不可用的代码。

#### 动机

`api/` 和 `viewer/api/` 同名是开发者导航时的最大混淆源之一。但**仅改名不修复**收益很低，因为客户端当前与 Viewer API 严重不一致（health check 必定失败，list_experiments 必定 404），改名后仍然不可用。建议将修复与改名绑定，或降级为低优先级。

---

### RF-09: 合并 index/ 到 storage/

**优先级**: P2（可安排）
**风险**: 低
**预计工时**: 30 分钟

#### 现状

`src/runicorn/index/` 包只有两个文件：
- `__init__.py` — 仅导出 `IndexDb`
- `db.py` — `IndexDb` 类实现（约 300 行）

`IndexDb` 管理 `storage_root/index/runicorn.db` 数据库，包含 3 张表（`runs`、`assets`、`run_assets`），主要用于 SDK 写入端的资产去重。

它与 `storage/` 在概念上高度相关：
- 都是 SQLite 数据库
- 都以 `storage_root` 为根目录
- `runs` 表与 `storage/runicorn.db` 的 `experiments` 表有字段重叠
- 都由 `sdk.py` 在 `Run.__init__()` 中初始化

#### 涉及文件

- `src/runicorn/index/__init__.py` — 删除
- `src/runicorn/index/db.py` — 移动为 `src/runicorn/storage/index_db.py`
- `src/runicorn/sdk.py` — 第 25 行 `from .index import IndexDb` → `from .storage.index_db import IndexDb`
- `src/runicorn/assets/cleanup.py` — 第 58 行 `from ..index import IndexDb`（也需更新）

#### 主要风险

`storage/file_utils.py:19` 有 `from ..sdk import DEFAULT_DIRNAME, _default_storage_dir`（storage 层反向依赖 sdk 层）。如果合并 index 后更多模块从 `runicorn.storage import ...`，import 链会变得更复杂。合并时应保持"按文件精确 import"（如 `from .storage.index_db import IndexDb`），**避免**将 IndexDb 塞进 `storage/__init__.py` 的批量 re-export 中引发隐性循环。

#### 改进建议

1. 将 `index/db.py` 移动为 `storage/index_db.py`
2. 更新 `sdk.py` 和 `assets/cleanup.py` 的 import 为精确路径 `from .storage.index_db import IndexDb`
3. **不要**在 `storage/__init__.py` 中 re-export IndexDb（避免加重循环依赖风险）
4. 保留 `index/__init__.py` 作为兼容层 shim

#### 动机

消除只有一个类的孤立小包。`index/` 在语义上属于存储基础设施，放入 `storage/` 更符合直觉。

---

### RF-10: 将 workspace/ 包降级为单文件

**优先级**: P3（低优先级）
**风险**: 极低
**预计工时**: 15 分钟

#### 现状

`src/runicorn/workspace/` 包含：
- `__init__.py` — 仅 `from .root import get_workspace_root`
- `root.py` — 仅 25 行，一个私有函数 `_find_git_root()` + 一个公共函数 `get_workspace_root()`

整个包的全部功能就是：向上查找 `.git` 目录，找不到就 fallback 到 `cwd`。

#### 涉及文件

- `src/runicorn/workspace/__init__.py` — 删除
- `src/runicorn/workspace/root.py` — 移动为 `src/runicorn/workspace.py`
- `src/runicorn/sdk.py` — 第 19 行 `from .workspace import get_workspace_root`（无需改动，Python 对包和模块的 import 语法相同）
- `src/runicorn/rnconfig/loader.py` — 如有引用需检查

#### 改进建议

将 `workspace/root.py` 的内容直接放入 `workspace.py` 单文件，删除 `workspace/` 目录。

#### 动机

为单个 25 行函数维护一个 Python 包是过度抽象。如果未来功能增长（不太可能，工作区检测是稳定功能），再升级为包。

---

### RF-11: 删除或完成 FileStorageBackend 半成品

**优先级**: P2（可安排）
**风险**: 低
**预计工时**: 30 分钟

#### 现状

`src/runicorn/storage/backends.py` 中的 `FileStorageBackend`（第 165-325 行）是一个半成品实现：

- `create_experiment()` — 有实现，但使用 `experiment.project` / `experiment.name`（`backends.py:190-199`），而 `ExperimentRecord` dataclass **根本没有这两个属性**（只有 `path`，见 `models.py:23-25`）→ 运行时必定 `AttributeError`
- `get_experiment()` — 返回 `None`（第 253 行注释 "Placeholder"）
- `list_experiments()` — 返回空列表 `[]`（第 259 行注释 "Placeholder"）
- `get_metrics()` — 返回空列表 `[]`（第 300 行注释 "Placeholder"）
- `soft_delete_experiments()` — 返回 Placeholder
- `restore_experiments()` — 返回 Placeholder
- `get_storage_stats()` — 返回空 `StorageStats()`

同时 `HybridStorageBackend` 依赖 `FileStorageBackend` 作为其 file_backend 成员，但由于后者是半成品，Hybrid 模式实际上也无法正常工作。

**`migration.py` 中 `get_metrics()` 也不可用**:

`FilesToSQLiteFileReader.get_metrics()`（`migration.py:304-309`）调用 `await self.get_experiment(exp_id)`，但 `FilesToSQLiteFileReader` 未 override `get_experiment()`，继承自 `FileStorageBackend` 的实现返回 `None`（`backends.py:253`）。因此 `if not experiment: return []` 始终成立 → **指标迁移始终返回空列表**，即使 `events.jsonl` 文件存在且有数据也读不出来。

**`migration.py` 中 `_load_experiment_from_files()` 的问题更严重**:

`FilesToSQLiteFileReader._load_experiment_from_files()`（`migration.py:275-298`）直接用关键字参数构造 `ExperimentRecord(project=project, name=name, ...)`，但 `ExperimentRecord` dataclass 没有 `project`/`name` 字段 → **直接 `TypeError: __init__() got an unexpected keyword argument 'project'`**。虽然 `ExperimentRecord.from_dict()` 有 legacy 转换逻辑（`models.py:67-73`），但迁移代码用的是直接构造函数。**这意味着整个迁移链路当前不可用。**

同样，`_verify_migration()`（`migration.py:181`）访问 `sqlite_exp.project`，也会 `AttributeError`。

#### 涉及文件

- `src/runicorn/storage/backends.py` — 第 165-325 行 `FileStorageBackend`，第 865-925+ 行 `HybridStorageBackend`
- `src/runicorn/storage/__init__.py` — 导出列表
- `src/runicorn/storage/migration.py` — `FilesToSQLiteMigrator` 使用 `FileStorageBackend`

#### 改进建议

**推荐方案：删除 FileStorageBackend 和 HybridStorageBackend**

理由：
- SDK 写入端已经有完善的文件写入逻辑（在 `sdk.py` 中直接写 JSON 文件），不需要通过 `FileStorageBackend` 再封装一层
- Viewer 读取端通过 `file_utils.py` 直接读取文件，也不需要 `FileStorageBackend`
- `SQLiteStorageBackend` 是唯一完整实现且实际被使用的后端
- `HybridStorageBackend` 的 `_migrate_from_files()` 方法体是空的（"placeholder"），也无法使用

如果删除，需要同时：
1. `StorageBackend` ABC 保留（作为接口定义）
2. `SQLiteStorageBackend` 保留（唯一完整实现）
3. `migration.py` 中 `FilesToSQLiteFileReader` 必须改为**不继承 FileStorageBackend 的独立迁移工具类**，并修复 `ExperimentRecord` 的构造方式（用 `ExperimentRecord.from_dict()` 或直接使用 `path` 字段替代 `project`/`name`）
4. `_verify_migration()` 中 `sqlite_exp.project` 改为 `sqlite_exp.path`
5. `storage/__init__.py` 的导出列表更新

#### 动机

半成品代码比没有代码更糟糕 — 它让开发者以为功能存在，但运行时得到的是空结果。保留它增加认知负担（"这个类是完成的吗？能用吗？"），不如删掉让代码库更诚实。

---

### RF-12: 决定 viewer/services/modern_storage.py 的命运

**优先级**: P2（可安排）
**风险**: 低
**预计工时**: 30 分钟

#### 现状

`src/runicorn/viewer/services/modern_storage.py` 包含 `ModernStorageService` 类（约 300 行），设计为 Viewer API 路由与 storage backends 之间的适配层。它实现了：
- `list_experiments()` — 将 API 查询参数转换为 `QueryParams`，调用后端，格式化输出
- `get_experiment_detail()` — 获取单个实验详情
- `get_experiment_metrics()` — 按 step 分组指标数据为前端兼容格式
- `update_experiment_status()` — 更新状态
- `close()` — 关闭数据库连接

**但这个类没有被任何 API 路由调用**。唯一的引用在 `viewer/__init__.py` 第 120 行的 shutdown 事件中：

```python
from .services.modern_storage import close_storage_service
close_storage_service()
```

而 `close_storage_service()` 内部检查全局单例是否存在，由于没有路由创建过实例，它实际上是空操作。

#### 涉及文件

- `src/runicorn/viewer/services/modern_storage.py`
- `src/runicorn/viewer/__init__.py` — shutdown 事件中的引用

#### 改进建议

**方案 A（推荐）：暂时删除，在 RF-14 实施时重新设计**

这个文件不仅未接入，而且代码层面有**硬错误**：
- `list_experiments()` 构造 `QueryParams(project=..., name=...)`（`modern_storage.py:93-105`），但 `QueryParams` dataclass 没有 `project`/`name` 字段 → **TypeError**
- `_experiment_to_api_format()` 访问 `experiment.project`/`experiment.name`（`modern_storage.py:298-299`），但 `ExperimentRecord` 没有这些属性 → **AttributeError**
- `count_experiments()` 同样构造带 `project`/`name` 的 `QueryParams`（`modern_storage.py:125-127`）→ **TypeError**

如果 RF-14 纳入实施计划，这个文件的设计理念是对的，但实现需要从头重写以对齐当前数据模型（`path` 而非 `project`/`name`）。不如在 RF-14 实施时重新设计，而不是维护一个既未接入又有硬错误的模块。

**方案 B：保留但标记为 WIP**

如果选择保留，应在文件顶部和 `__init__.py` 中添加明确注释：
```python
# WARNING: This module is not yet integrated into any API routes.
# It is a work-in-progress for the planned SQLite-based viewer read path.
# Do not import or use until RF-14 is complete.
```

#### 动机

死代码增加认知负担。保留一个未接入的服务层会让新开发者困惑："这个文件存在但没人用，是 bug 还是 design？"

---

### RF-13: 合并两个 SQLite 数据库（远期）

**优先级**: P3（远期）
**风险**: 高
**预计工时**: 评估阶段 4 小时，实施阶段 8-16 小时

#### 现状

系统中存在两个独立的 SQLite 数据库：

**数据库 1: `storage_root/index/runicorn.db`（IndexDb）**
- 3 张表: `runs`、`assets`、`run_assets`
- `runs` 表字段: `run_id`, `path`, `alias`, `created_at`, `ended_at`, `status`, `run_dir`, `workspace_root`
- 主要用途: 资产去重（通过 `assets` 表的 fingerprint 唯一索引）
- 写入方: `sdk.py` 的 `Run.__init__()` (upsert_run)、`scan_outputs_once()` (record_asset_for_run)、`log_config()`、`log_dataset()`、`log_pretrained()`
- 读取方: `assets/cleanup.py` 的 `delete_run_completely()` 通过 `IndexDb.delete_run_with_orphan_assets()` 读写（永久删除 run 时查询孤儿 asset 再删除）

**数据库 2: `storage_root/runicorn.db`（SQLiteStorageBackend）**
- 7 张表: `experiments`, `metrics`, `experiment_tags`, `environments`, `experiment_files`, `query_cache`, `storage_stats`
- 3 个视图: `v_path_stats`, `v_best_experiments`, `v_recent_activity`
- `experiments` 表字段: 与 IndexDb 的 `runs` 表高度重叠（id, path, alias, created_at, status, run_dir 等），但多了 best_metric、soft_delete、platform 等字段
- 写入方: `sdk.py` 通过 `SQLiteStorageBackend` 双写
- 读取方: 无（Viewer 当前不读 SQLite）

**重叠分析**:
- `IndexDb.runs` 和 `SQLiteStorageBackend.experiments` 存储了**几乎相同的 run 元数据**
- `sdk.py` 的 `Run.__init__()` 同时写入两个数据库（第 234-296 行写 IndexDb，第 256-260 行写 SQLiteStorageBackend）

#### 改进建议

将 IndexDb 的 `assets` 和 `run_assets` 表合并到 `storage/runicorn.db` 中，并废弃 `index/runicorn.db`：

1. 在 `schema.sql` 中添加 `assets` 和 `run_assets` 表定义
2. 在 `SQLiteStorageBackend` 中添加资产相关方法（`upsert_asset`, `record_asset_for_run` 等）
3. 修改 `sdk.py` 使只写入一个数据库
4. 提供迁移脚本将 `index/runicorn.db` 的数据合并到 `storage/runicorn.db`

#### 动机

两个数据库存储重叠数据是资源浪费（双倍磁盘 I/O、双倍连接管理），也增加了数据不一致的风险。合并后 SDK 只需要初始化一个数据库连接。

#### 为什么标记为远期

这个改动影响面大（`sdk.py` 中大量与 IndexDb 交互的代码需要重写），需要仔细的数据迁移方案，且当前两个数据库都正常工作，不影响用户功能。建议在 RF-06（async→sync）和 RF-11（清理 backends）完成后再实施。

---

### RF-14: 让 Viewer 读取端切换到 SQLite（远期）

**优先级**: P3（远期，RF-06 + RF-13 完成后）
**风险**: 高
**预计工时**: 评估阶段 4 小时，实施阶段 16-24 小时

#### 现状

SDK 写入端已实现文件 + SQLite 双写（`sdk.py` 第 573-597 行），但 Viewer 读取端的核心 API 路由（约 8 个路由模块：`runs.py`, `projects.py`, `metrics.py`, `health.py`, `config.py`, `export.py`, `import_.py`, `storage.py`）仍然通过 `file_utils.py` 读取文件系统。其余路由模块（`gpu.py`, `system.py`, `remote.py`, `ui_preferences.py`, `experiments.py`）不依赖 `file_utils`。

以 `list_runs` 为例（`viewer/api/runs.py` 第 76-152 行）：

```python
@router.get("/runs")
async def list_runs(request: Request):
    storage_root = get_storage_root(request)
    for entry in iter_all_runs(storage_root):  # ← 递归遍历文件系统
        meta = read_json(run_dir / "meta.json")    # ← 逐个读 JSON
        status = read_json(run_dir / "status.json") # ← 逐个读 JSON
        summary = read_json(run_dir / "summary.json")
        ...
```

`iter_all_runs()` 通过 `_scan_runs_recursive()` 递归扫描 `runs/` 目录树，对每个找到的目录检查是否包含 `meta.json` 或 `status.json`。当 run 数量超过几百个时，这个操作涉及大量文件系统 I/O。

类似地，`projects.py` 的 `_get_path_stats()` 对每个 run 分别读取 `meta.json` + `status.json` 来统计路径下的 run 数量，而 SQLite 的 `v_path_stats` 视图可以用一条 SQL 完成。

#### 期望目标

对于已经有 SQLite 数据的 run，Viewer 直接从 `runicorn.db` 查询，而不是遍历文件系统。对于只存在于文件系统的旧 run（迁移前），fallback 到文件读取。

#### 涉及文件（评估）

- `src/runicorn/viewer/api/runs.py` — `list_runs()`, `get_run_detail()`
- `src/runicorn/viewer/api/projects.py` — `list_paths()`, `_get_path_stats()`
- `src/runicorn/viewer/api/metrics.py` — `get_metrics()`（可从 SQLite metrics 表直接查询）
- `src/runicorn/viewer/api/health.py` — `check_all_status()`
- `src/runicorn/viewer/services/` — 需要新的服务层连接 SQLite

#### 改进建议

1. 在 Viewer startup 时初始化 `SQLiteStorageBackend` 实例，存入 `app.state`
2. 修改核心路由（`list_runs`, `get_run_detail`, `get_metrics`, `list_paths`）优先从 SQLite 查询
3. 保留文件系统读取作为 fallback（处理未迁移的旧数据）
4. `periodic_status_check` 同时更新文件和 SQLite

#### 动机

这是**唯一能带来用户可感知性能提升**的重构项。100 个 run 的 `list_runs` 从遍历 100×3=300 个 JSON 文件变为一条 SQL 查询，响应时间预计从秒级降到毫秒级。

#### 前置条件

1. 依赖 RF-06（backends 改为 sync）和最好也完成 RF-13（数据库合并）
2. 需要仔细处理数据一致性（文件系统是 source of truth，SQLite 是加速缓存的关系，还是反过来？需要明确设计决策）
3. **必须先完成 RF-15**（统一目录布局假设），否则 CLI export、storage stats 等代码仍按旧布局遍历，与 SQLite 数据不一致

---

### RF-15: 统一目录布局假设（path vs project/name）

**优先级**: P1（影响 RF-11/RF-14 的可行性）
**风险**: 中（多处遍历逻辑需修改）
**预计工时**: 2-3 小时

#### 现状

代码库中存在两种目录布局假设，且**部分代码使用了已过时的布局**：

**当前实际布局（新）**: `storage_root/runs/<path>/<id>/`
- `iter_all_runs()`（`storage/file_utils.py:281+`）通过 `_scan_runs_recursive()` 递归扫描 `runs/` 目录树
- SDK 写入端（`sdk.py`）按此布局创建 run 目录

**旧布局假设**: `storage_root/<project>/<name>/runs/<id>/`
- `cli.py:134-170` 的 `export` 命令按 `root/<project>/<name>/runs/<id>` 遍历，不使用 `iter_all_runs()`
- `viewer/api/storage.py:105-123` 的 `get_storage_stats()` 按 `project_dir → exp_dir → "runs" → run_dir` 遍历
- `FileStorageBackend._get_run_dir()`（`backends.py:190`）使用 `project/name/runs/id` 构建路径
- `FilesToSQLiteFileReader._load_experiment_from_files()`（`migration.py:246-247`）从 `entry.project`/`entry.name` 提取信息
- `ModernStorageService._experiment_to_api_format()`（`modern_storage.py:298-299`）输出 `experiment.project`/`experiment.name`

**后果**:
- CLI `export` 命令找不到新布局下的 run → 导出为空
- `storage/stats` API 统计不到新布局下的 run → 统计值偏低
- 迁移链路硬 TypeError（详见 RF-11）

#### 涉及文件

- `src/runicorn/cli.py` — 第 134-170 行 export 遍历逻辑
- `src/runicorn/viewer/api/storage.py` — 第 105-123 行 stats 遍历逻辑
- `src/runicorn/storage/backends.py` — `FileStorageBackend._get_run_dir()`
- `src/runicorn/storage/migration.py` — `_load_experiment_from_files()` 和 `_verify_migration()`
- `src/runicorn/viewer/services/modern_storage.py` — `_experiment_to_api_format()` 和 `QueryParams` 构造
- `src/runicorn/extensions/experiment.py` — `ExperimentMetadata` dataclass 有 `project`/`name` 字段（line 22-24），`_find_run_path()` 按 `storage_root/project/name/runs/run_id` 构建路径（line 264-267），`delete_experiments()` 依赖 `meta.project`/`meta.name`（line 248）

#### 改进建议

1. **CLI export**: 将自行遍历逻辑改为基于 `iter_all_runs()` 或 `IndexDb` 查询
2. **storage stats**: 同样改为基于 `iter_all_runs()` 遍历，而非硬编码 `project/name/runs` 结构
3. **migration.py**: 使用 `ExperimentRecord.from_dict()` 替代直接构造函数，或改为使用 `path` 字段（`entry.path`）
4. **modern_storage.py**: 使用 `path` 字段替代 `project`/`name`，`QueryParams` 用 `path=` 参数
5. **extensions/experiment.py**: `ExperimentMetadata` 需从 `project`/`name` 迁移到 `path` 字段，`_find_run_path()` 改为基于 `iter_all_runs()` 或 `IndexDb` 查找，而非硬编码旧布局

#### 动机

这不仅是"代码风格"问题，而是**会造成功能错误**的现实 bug。CLI export 找不到新布局的 run，storage stats 统计值不准确。更重要的是，这个问题直接影响 RF-11（迁移 TypeError）和 RF-14（SQLite 读取路径）的可行性。在推进这些重构项之前，必须先统一布局假设。

---

## 三、执行计划

### Phase 1: 无争议清理（预计 40 分钟）

| 序号 | 项目 | 风险 | 工时 |
|------|------|------|------|
| 1.1 | RF-01: 删除空目录和残留 | 无 | 10 min |
| 1.2 | RF-02: 删除 viewer/services/storage.py 转发层 | 低 | 30 min |

**验证点**: `python -m runicorn viewer` 启动正常，所有 API 路由可访问。

### Phase 2: 配置体系重构（预计 7-8 小时）

| 序号 | 项目 | 风险 | 工时 | 依赖 |
|------|------|------|------|------|
| 2.1 | RF-03: 将配置体系统一为 config/ 包 | 中 | 3-4h | - |
| 2.2 | RF-04: 统一加密系统 | 中 | 2h | RF-03 |
| 2.3 | RF-05: 统一 SSH 连接路径 | 中 | 1.5h | RF-03, RF-04 |

**验证点**: 所有现有 `from runicorn.config import X` 仍可用。SSH 连接保存/读取/自动迁移旧格式测试通过。

### Phase 3: 架构改善（预计 8-9 小时）

| 序号 | 项目 | 风险 | 工时 | 依赖 |
|------|------|------|------|------|
| 3.1 | RF-06: storage backends async→sync | 中高 | 3h | - |
| 3.2 | RF-07: 消除 sdk.py asyncio 裸调用 | 低 | 1h | RF-06 |
| 3.3 | RF-15: 统一目录布局假设 | 中 | 2-3h | - |
| 3.4 | RF-11: 删除 FileStorageBackend 半成品 | 低 | 30 min | RF-06, RF-15 |
| 3.5 | RF-12: 处理 modern_storage.py | 低 | 30 min | RF-15 |

**验证点**: `Run.log()` + `Run.finish()` 全流程测试。SQLite 双写正常。无 asyncio 相关 warning。CLI export 和 storage stats 能正确发现新布局下的 run。

### Phase 4: 小包合并 + 客户端修复（预计 2-5 小时）

| 序号 | 项目 | 风险 | 工时 | 依赖 |
|------|------|------|------|------|
| 4.1 | RF-09: index/ → storage/index_db.py | 低 | 30 min | - |
| 4.2 | RF-10: workspace/ → workspace.py | 极低 | 15 min | - |
| 4.3 | RF-08: 修复 + 重命名 api/ → client/（可选） | 低~中 | 1-3h | - |

**验证点**: SDK Run 创建和资产记录测试通过。如修复了 RF-08，`RunicornClient` 的 health check 和 list 操作可用。

### Phase 5: 远期架构演进（时间待定）

| 序号 | 项目 | 风险 | 工时 | 依赖 |
|------|------|------|------|------|
| 5.1 | RF-13: 合并两个 SQLite 数据库 | 高 | 8-16h | Phase 3, Phase 4 |
| 5.2 | RF-14: Viewer 切换到 SQLite 读取 | 高 | 16-24h | RF-13 |

---

## 四、风险评估

### 高风险项

**RF-06 (async→sync)**: 修改 `StorageBackend` 接口影响所有三个实现类 + 迁移工具 + SDK 调用方。虽然改动机械（删除 async/await 关键字），但数量多，容易遗漏。
- **缓解**: 改完后运行 `python -c "from runicorn.storage import *"` 验证 import，再做全功能测试

**RF-04 (统一加密)**: 涉及已有加密数据的格式变更。如果迁移逻辑有 bug，用户会丢失已保存的 SSH 密码。
- **缓解**: 迁移前先读取并打印（不含敏感值，只打印"成功解密 N 条"），确认旧数据可读；迁移时保留原文件备份

### 中风险项

**RF-03 (config 包合并)**: 涉及 13 个文件的 import 依赖。虽然通过 `__init__.py` re-export 保持向后兼容，但需要确保所有 import 路径在合并后仍然正常工作。特别注意 `_config_root_dir` 这个私有符号被 `security/encryption.py` 和 `security/credentials.py` 直接引用，必须在 `config/__init__.py` 中 re-export。
- **缓解**: 合并后运行 `python -c "from runicorn.config import load_user_config, get_ssh_connections, get_rate_limit_config, _config_root_dir"` 验证核心 import；检查 `rnconfig` 和 `registry` 兼容层 shim 可用

**RF-15 (统一目录布局)**: 多处遍历逻辑需修改，且修改后必须兼容新旧两种布局（旧数据可能仍按 `project/name/runs` 存在）。
- **缓解**: 修改后在包含新旧两种布局的 storage_root 下测试 CLI export 和 storage stats

**RF-05 (统一 SSH 路径)**: 需要确保 `config.json` 中的旧数据和 `connections.json` 中的新数据都能被正确迁移到统一位置。
- **缓解**: 编写迁移测试用例，覆盖 3 种场景（仅有旧数据、仅有新数据、两者都有）

### 低风险项

RF-01, RF-02, RF-09, RF-10, RF-11, RF-12 均为低风险或无风险操作。RF-08 仅改名部分为低风险，若含修复客户端则为中风险。

---

## 五、验证策略

### 每个 Phase 结束时的验证清单

1. **Import 验证**: `python -c "import runicorn; print(runicorn.__version__)"` 成功
2. **CLI 验证**: 以下命令均可执行（不报 ImportError）:
   - `python -m runicorn viewer --help`
   - `python -m runicorn config --show`
   - `python -m runicorn export --help`
   - `python -m runicorn export-data --help`
   - `python -m runicorn manage --help`
   - `python -m runicorn rate-limit --help`
   - `python -m runicorn delete --help`
3. **SDK 验证**: 创建 Run、log 指标、finish 全流程无报错:
   ```python
   import runicorn
   run = runicorn.init(path="test/refactor", capture_console=False)
   run.log({"loss": 0.5, "acc": 95.0}, step=1)
   run.set_primary_metric("acc", mode="max")
   run.log({"loss": 0.3, "acc": 97.0}, step=2)
   run.finish()
   ```
4. **Viewer 验证**: `python -m runicorn viewer` 启动后:
   - `GET /api/health` 返回 200
   - `GET /api/runs` 返回 run 列表
   - `GET /api/paths` 返回路径树
5. **加密验证**（Phase 2 后）: 已保存的 SSH 连接仍可读取，新保存的使用 Fernet 格式

### 回归测试建议

如果项目有现有测试套件，每个 Phase 后运行全量测试。如果没有，建议至少为以下核心路径添加冒烟测试：
- `Run` 生命周期: init → log → log_image → log_config → finish
- `NoOpRun` 在 disabled 状态下的行为
- `config.py` 配置读写
- SSH 连接加密/解密往返
- `iter_all_runs()` 在新旧两种目录布局下的发现能力

---

## 附录: 不在本次重构范围内的项目

以下问题已识别但**有意不纳入**本次重构：

1. **sdk.py 拆分**: 1161 行的单文件确实偏大，但当前结构内聚性强（`Run` 类的所有方法在同一文件中），拆分的收益不明显。如果未来新增大量方法，可考虑按功能拆分（如 `sdk/run.py`, `sdk/media.py`, `sdk/assets_logging.py`）。

2. **前端结构优化**: `api.ts` vs `api/` 分裂、`fancy/` 组件边界等问题与后端重构正交，建议在前端专项迭代中处理。
3. **storage/schema.sql 中的 PRAGMA**: 当前 schema.sql 底部包含 `PRAGMA journal_mode = WAL` 等语句，但这些 PRAGMA 在 `SQLiteStorageBackend._initialize_schema()` 中通过 `executescript()` 执行时可能不生效（PRAGMA 不保证在 script 模式下持久化）。这是一个潜在 bug，但不属于结构重构范围。
