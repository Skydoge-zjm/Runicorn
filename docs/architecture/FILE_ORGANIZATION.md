# Runicorn 文件组织结构

完整的 `src/runicorn/` 目录文件分类说明。

## 📊 架构模块分类

### 🎯 模块 1：SDK / 记录部分

用户训练脚本调用的核心 API。

| 文件 | 功能 | 核心类/函数 |
|------|------|------------|
| `__init__.py` | 导出公开 API | `init()`, `log()`, `finish()`, `Run` |
| `sdk.py` | 核心 Run 类和记录逻辑 | `Run`, `init()`, `log()`, `summary()`, `finish()` |

**使用示例**：
```python
import runicorn as rn
run = rn.init(project="test")
rn.log({"loss": 0.5})
rn.finish()
```

---

### 💾 模块 2：存储管理

管理实验数据的存储位置、格式和访问。

#### 核心存储

| 文件 | 功能 | 说明 |
|------|------|------|
| `config.py` | 存储路径配置 | `get_user_root_dir()` 管理全局存储位置 |
| `storage/__init__.py` | 存储模块入口 | - |
| `storage/backends.py` | 存储后端实现 | `SQLiteStorageBackend`, `HybridStorageBackend` |
| `storage/models.py` | 数据模型定义 | `ExperimentRecord`, `MetricRecord` |
| `storage/migration.py` | 存储迁移工具 | 传统文件 → 现代存储 |
| `storage/sync_utils.py` | 同步工具 | 异步存储的同步包装器 |
| `storage/sql_utils.py` | SQL 工具函数 | SQLite 操作辅助函数 |

**存储结构**：
```
user_root_dir/
  <project>/
    <name>/
      runs/
        <run_id>/
          events.jsonl      # 时序指标
          summary.json      # 汇总数据
          meta.json         # 元数据
          status.json       # 运行状态
          logs.txt          # 日志
          media/            # 图片等
```

---

### 🌐 模块 3：Viewer 后端 / 前端对接

FastAPI Web 服务器，为前端提供 REST API。

#### Viewer 主入口

| 文件 | 功能 |
|------|------|
| `viewer/__init__.py` | Viewer 模块入口 |
| `viewer.py` | CLI 启动入口（薄封装） |
| `viewer/app.py` | FastAPI 应用主体 |

#### API 路由

| 文件 | 端点 | 功能 |
|------|------|------|
| `viewer/api/health.py` | `GET /api/health` | 健康检查 |
| `viewer/api/experiments.py` | `GET /api/experiments` | 实验列表 |
| `viewer/api/runs.py` | `GET /api/runs/{id}` | 单个运行详情 |
| `viewer/api/metrics.py` | `GET /api/metrics/{id}` | 指标数据 + WebSocket 实时推送 |
| `viewer/api/projects.py` | `GET /api/projects` | 项目列表 |
| `viewer/api/artifacts.py` | `/api/artifacts/*` | Artifacts 管理 |
| `viewer/api/experiment_artifacts.py` | `/api/experiments/{id}/artifacts` | 实验的 artifacts |
| `viewer/api/export.py` | `POST /api/export` | 导出实验数据 |
| `viewer/api/import_.py` | `POST /api/import` | 导入实验数据 |
| `viewer/api/config.py` | `GET/PUT /api/config` | 用户配置管理 |
| `viewer/api/gpu.py` | `GET /api/gpu` | GPU 信息 |
| `viewer/api/ui_preferences.py` | `/api/ui-preferences` | UI 偏好设置 |
| `viewer/api/model_lifecycle.py` | `/api/model-lifecycle/*` | 模型生命周期 |
| `viewer/api/remote.py` | `/api/remote/*` | **远程查看 API** |

#### V2 API（新架构）

| 文件 | 功能 |
|------|------|
| `viewer/api/v2/__init__.py` | V2 API 入口 |
| `viewer/api/v2/experiments.py` | V2 实验 API |
| `viewer/api/v2/metrics.py` | V2 指标 API |
| `viewer/api/v2/runs.py` | V2 运行 API |

#### 工具和服务

| 文件 | 功能 |
|------|------|
| `viewer/api/storage_utils.py` | 存储路径工具 |
| `viewer/services/storage.py` | 存储服务层 |
| `viewer/utils/cache.py` | 指标缓存 |
| `viewer/utils/path.py` | 路径处理 |

---

### 🔌 模块 4：远程查看（Remote Viewer）

通过 SSH 访问远程服务器的实验数据。

#### 4.1 客户端（本地 Windows）

| 文件 | 功能 | 核心类 |
|------|------|--------|
| `remote/__init__.py` | 模块入口 | 导出公开 API |
| `remote/connection.py` | SSH 连接管理 | `SSHConfig`, `SSHConnection`, `SSHConnectionPool` |
| `remote/viewer/manager.py` | 远程 Viewer 管理器 | `RemoteViewerManager` |
| `remote/viewer/session.py` | 会话管理 | `ViewerSession` |
| `remote/viewer/tunnel.py` | SSH 隧道管理 | `SSHTunnel` |

**功能**：
- 建立 SSH 连接
- 在远程启动 viewer 进程
- 创建 SSH 隧道（端口转发）
- 管理远程会话生命周期

#### 4.2 服务端（WSL / 远程服务器）

**复用标准 Viewer**：远程服务器运行的就是普通的 `viewer` 模块，只是通过隧道被转发。

#### Remote API（集成在 Viewer 中）

| 文件 | 端点 | 功能 |
|------|------|------|
| `viewer/api/remote.py` | `POST /api/remote/connect` | 建立 SSH 连接 |
|  | `POST /api/remote/disconnect` | 断开连接 |
|  | `GET /api/remote/sessions` | 列出 SSH 连接 |
|  | `POST /api/remote/viewer/start` | 启动远程 viewer |
|  | `POST /api/remote/viewer/stop` | 停止远程 viewer |
|  | `GET /api/remote/viewer/sessions` | 列出远程 viewer 会话 |
|  | `GET /api/remote/fs/list` | 列出远程目录 |
|  | `GET /api/remote/fs/exists` | 检查远程路径 |
|  | `GET /api/remote/status` | 远程系统状态 |

---

### 🧩 模块 5：扩展功能

#### Artifacts（模型版本管理）

| 文件 | 功能 |
|------|------|
| `artifacts/__init__.py` | Artifacts 模块入口 |
| `artifacts/artifact.py` | Artifact 类定义 |
| `artifacts/storage.py` | Artifacts 存储管理 |
| `artifacts/lineage.py` | 血缘追踪 |
| `artifacts/models.py` | Artifacts 数据模型 |

#### Manifest（实验清单）

| 文件 | 功能 |
|------|------|
| `manifest/__init__.py` | Manifest 模块入口 |
| `manifest/models.py` | 清单数据模型 |
| `manifest/generator.py` | 清单生成器 |
| `manifest/cli.py` | 清单 CLI 工具 |

#### 监控和导出

| 文件 | 功能 |
|------|------|
| `monitors.py` | 指标监控、异常检测 |
| `exporters.py` | 数据导出工具（CSV, JSON, TensorBoard） |
| `experiment.py` | 实验管理器 |

#### 环境和安全

| 文件 | 功能 |
|------|------|
| `environment.py` | 环境信息捕获（Python, Git, 依赖等） |
| `security/credentials.py` | 凭据加密存储 |
| `security/path_validation.py` | 路径遍历防护 |
| `security/rate_limiter.py` | API 速率限制 |

#### CLI 工具

| 文件 | 功能 |
|------|------|
| `cli.py` | 命令行接口（`runicorn viewer`, `runicorn config` 等） |

---

## 📂 目录树视图

```
src/runicorn/
│
├─ 📦 模块 1: SDK/记录
│   ├── __init__.py              # 导出公开 API
│   └── sdk.py                   # 核心 Run 类
│
├─ 💾 模块 2: 存储管理
│   ├── config.py                # 存储路径配置
│   └── storage/                 # 存储后端
│       ├── __init__.py
│       ├── backends.py          # SQLite/Hybrid 后端
│       ├── models.py            # 数据模型
│       ├── migration.py         # 迁移工具
│       ├── sync_utils.py
│       └── sql_utils.py
│
├─ 🌐 模块 3: Viewer 后端
│   ├── viewer.py                # CLI 启动入口
│   └── viewer/
│       ├── __init__.py
│       ├── app.py               # FastAPI 应用
│       ├── api/                 # REST API 路由
│       │   ├── health.py        # 健康检查
│       │   ├── experiments.py   # 实验列表
│       │   ├── runs.py          # 运行详情
│       │   ├── metrics.py       # 指标数据
│       │   ├── projects.py      # 项目管理
│       │   ├── artifacts.py     # Artifacts
│       │   ├── export.py        # 导出
│       │   ├── import_.py       # 导入
│       │   ├── config.py        # 配置
│       │   ├── remote.py        # 🔌 远程 API
│       │   └── v2/              # V2 API
│       ├── services/            # 服务层
│       └── utils/               # 工具函数
│
├─ 🔌 模块 4: 远程查看
│   └── remote/                  # 4.1 客户端
│       ├── __init__.py
│       ├── connection.py        # SSH 连接
│       └── viewer/              # Remote Viewer 管理
│           ├── __init__.py
│           ├── manager.py       # ViewerManager
│           ├── session.py       # 会话管理
│           └── tunnel.py        # SSH 隧道
│   # 4.2 服务端 = 复用 viewer/ 模块
│
└─ 🧩 模块 5: 扩展功能
    ├── artifacts/               # Artifacts 系统
    ├── manifest/                # 实验清单
    ├── security/                # 安全工具
    ├── monitors.py              # 监控
    ├── exporters.py             # 导出
    ├── experiment.py            # 实验管理
    ├── environment.py           # 环境捕获
    └── cli.py                   # CLI 工具
```

---

## 🔄 数据流示意

### 本地训练 → 本地查看

```
训练脚本
  ↓ (sdk.py)
本地文件系统
  ↓ (storage/)
Viewer 读取
  ↓ (viewer/api/)
前端展示
```

### 远程训练 → 远程查看

```
远程训练脚本 (WSL)
  ↓ (sdk.py)
远程文件系统
  ↓
[Windows] Remote API 调用
  ↓ (remote/connection.py)
SSH 连接 → 启动远程 viewer
  ↓ (remote/viewer/tunnel.py)
SSH 隧道: localhost:18080 → remote:8080
  ↓
本地浏览器访问 localhost:18080
  ↓ (隧道转发)
远程 viewer/api/ 读取远程数据
  ↓
前端展示
```

---

## 🎯 核心文件快速索引

| 功能 | 文件路径 |
|------|---------|
| 用户 API 入口 | `__init__.py`, `sdk.py` |
| 存储配置 | `config.py` |
| 现代存储后端 | `storage/backends.py` |
| Viewer 启动 | `viewer/app.py` |
| 实验列表 API | `viewer/api/experiments.py` |
| 指标查询 API | `viewer/api/metrics.py` |
| 远程查看 API | `viewer/api/remote.py` |
| SSH 连接管理 | `remote/connection.py` |
| 远程 Viewer 管理 | `remote/viewer/manager.py` |
| CLI 工具 | `cli.py` |

---

**总结**：
- 核心流程：SDK 记录 → Storage 存储 → Viewer 读取 → 前端展示
- 远程扩展：Remote 连接 → SSH 隧道 → 复用 Viewer
- 模块化设计：每个模块职责清晰，可独立测试和维护
