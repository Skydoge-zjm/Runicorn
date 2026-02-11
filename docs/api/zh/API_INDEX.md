[English](../en/API_INDEX.md) | [简体中文](API_INDEX.md)

---

# 完整 API 索引

**版本**: v0.6.0  
**总端点数**: 35+ REST + Python Client  
**最后更新**: 2026-01-15

---

## 🐍 Python API Client

**新增**: Python 程序化访问接口

| 组件 | 描述 | 文档 |
|------|------|------|
| **RunicornClient** | 主客户端类 | [📖](./python_client_api.md) |
| **Experiments API** | 实验查询和管理 | [📖](./python_client_api.md#实验管理) |
| **Metrics API** | 指标数据访问 | [📖](./python_client_api.md#指标数据) |
| **Remote API** | 远程 Viewer 控制 | [📖](./python_client_api.md#remote-api) |
| **Utils** | pandas DataFrame 工具 | [📖](./python_client_api.md#工具函数) |

**快速示例**:
```python
import runicorn.api as api

with api.connect() as client:
    experiments = client.list_experiments(project="vision")
    metrics = client.get_metrics(experiments[0]["id"])
```

---

## 📑 REST API 端点列表

### Runs API (实验管理)

| 方法 | 端点 | 描述 | 文档 |
|------|------|------|------|
| GET | `/api/runs` | 列出所有运行 | [📖](./runs_api.md#列出运行) |
| GET | `/api/runs/{run_id}` | 获取运行详情 | [📖](./runs_api.md#获取运行详情) |
| POST | `/api/runs/soft-delete` | 软删除运行 | [📖](./runs_api.md#软删除运行) |
| GET | `/api/recycle-bin` | 列出已删除的运行 | [📖](./runs_api.md#列出已删除的运行) |
| POST | `/api/recycle-bin/restore` | 恢复已删除的运行 | [📖](./runs_api.md#恢复运行) |
| POST | `/api/recycle-bin/empty` | 永久删除所有 | [📖](./runs_api.md#清空回收站) |

### Metrics API (训练数据)

| 方法 | 端点 | 描述 | 文档 |
|------|------|------|------|
| GET | `/api/runs/{run_id}/metrics` | 获取基于时间的指标（支持 LTTB 降采样） | [📖](./metrics_api.md#获取指标基于时间) |
| GET | `/api/runs/{run_id}/metrics_step` | 获取基于步骤的指标（支持 LTTB 降采样） | [📖](./metrics_api.md#获取步骤指标) |
| GET | `/api/metrics/cache/stats` | 获取增量缓存统计 | [📖](./metrics_api.md#缓存统计) |
| WS | `/api/runs/{run_id}/logs/ws` | 实时日志流 | [📖](./metrics_api.md#实时日志流) |

### Config API (设置)

| 方法 | 端点 | 描述 | 文档 |
|------|------|------|------|
| GET | `/api/config` | 获取配置 | [📖](./config_api.md#获取配置) |
| POST | `/api/config/user_root_dir` | 设置存储根目录 | [📖](./config_api.md#设置用户根目录) |
| GET | `/api/config/ssh_connections` | 获取已保存的连接 | [📖](./config_api.md#获取已保存的-ssh-连接) |
| POST | `/api/config/ssh_connections` | 保存连接 | [📖](./config_api.md#保存-ssh-连接) |
| DELETE | `/api/config/ssh_connections/{key}` | 删除连接 | [📖](./config_api.md#删除-ssh-连接) |
| GET | `/api/config/ssh_connections/{key}/details` | 获取连接详情 | [📖](./config_api.md) |

### Remote Viewer API (远程访问) 🆕

**v0.5.4**: VSCode Remote 风格的远程服务器访问

#### 连接管理

| 方法 | 端点 | 描述 | 文档 |
|------|------|------|------|
| POST | `/api/remote/connect` | 建立 SSH 连接 | [📖](./remote_api.md#post-apiremoteconnect) |
| GET | `/api/remote/sessions` | 列出 SSH 会话 | [📖](./remote_api.md#get-apiremotesessions) |
| POST | `/api/remote/disconnect` | 断开会话 | [📖](./remote_api.md#post-apiremotedisconnect) |
| GET | `/api/remote/status` | 远程状态 | [📖](./remote_api.md#get-apiremotestatus) |

#### 环境检测

| 方法 | 端点 | 描述 | 文档 |
|------|------|------|------|
| GET | `/api/remote/conda-envs` | 列出 Python 环境 | [📖](./remote_api.md#get-apiremoteconda-envs) |
| GET | `/api/remote/config` | 获取远程配置 | [📖](./remote_api.md#get-apiremoteconfig) |

#### Remote Viewer 管理

| 方法 | 端点 | 描述 | 文档 |
|------|------|------|------|
| POST | `/api/remote/viewer/start` | 启动 Remote Viewer | [📖](./remote_api.md#post-apiremoteviewerstart) |
| POST | `/api/remote/viewer/stop` | 停止 Remote Viewer | [📖](./remote_api.md#post-apiremoteviewerstop) |
| GET | `/api/remote/viewer/sessions` | 列出 Viewer 会话 | [📖](./remote_api.md#get-apiremoteviewersessions) |
| GET | `/api/remote/viewer/status/{session_id}` | 按 session_id 获取 Viewer 状态 | [📖](./remote_api.md#get-apiremoteviewerstatussession_id) |

### 增强日志 API 🆕 (v0.6.0)

**新增**: 控制台捕获和 Python logging 集成

| 组件 | 描述 | 文档 |
|------|------|------|
| `capture_console` | SDK 参数，用于 stdout/stderr 捕获 | [📖](./logging_api.md#sdk-参数) |
| `tqdm_mode` | 智能 tqdm 过滤 (smart/all/none) | [📖](./logging_api.md#sdk-参数) |
| `get_logging_handler()` | Python logging.Handler 集成 | [📖](./logging_api.md#日志处理器) |
| `MetricLogger` | torchvision 兼容的指标记录器 | [📖](./logging_api.md#metriclogger-兼容层) |

### 路径层级 API 🆕 (v0.6.0)

**新增**: 灵活的基于路径的实验组织

| 方法 | 端点 | 描述 | 文档 |
|------|------|------|------|
| GET | `/api/paths` | 列出所有路径（可含统计） | [📖](./paths_api.md#get-apipaths) |
| GET | `/api/paths/tree` | 获取路径树结构 | [📖](./paths_api.md#get-apipathstree) |
| GET | `/api/paths/runs` | 按路径过滤列出运行 | [📖](./paths_api.md#get-apipathsruns) |
| POST | `/api/paths/soft-delete` | 按路径批量软删除 | [📖](./paths_api.md#post-apipathssoft-delete) |
| GET | `/api/paths/export` | 按路径导出运行 (JSON/ZIP) | [📖](./paths_api.md#get-apipathsexport) |

### Projects API (层级 - 旧版兼容)

| 方法 | 端点 | 描述 | 文档 |
|------|------|------|------|
| GET | `/api/projects` | 列出顶层路径段 | [📖](./paths_api.md#get-apiprojects) |
| GET | `/api/projects/{project}/names` | 列出第二层路径段 | [📖](./paths_api.md#get-apiprojectsprojectnames) |
| GET | `/api/projects/{project}/names/{name}/runs` | 列出 project/name 下的运行 | [📖](./paths_api.md#get-apiprojectsprojectnamesname-runs) |

### Health & System

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/health` | API 健康检查 |
| GET | `/api/gpu/telemetry` | GPU 监控数据 |

---

## 🔍 按用例搜索

### 用例: 监控训练

```bash
# 1. 获取运行详情
GET /api/runs/{run_id}

# 2. 实时流式日志
WS  ws://127.0.0.1:23300/api/runs/{run_id}/logs/ws

# 3. 轮询指标
GET /api/runs/{run_id}/metrics_step

# 4. 检查 GPU 使用情况
GET /api/gpu/telemetry
```

### 用例: Remote Viewer (新)

```bash
# 1. 连接到远程服务器
POST /api/remote/connect
Body: {"host": "gpu-server.com", "port": 22, "username": "mluser", "password": null, "private_key": null, "private_key_path": "~/.ssh/id_rsa", "passphrase": null, "use_agent": true}

# 2. 检测 Python 环境
GET /api/remote/conda-envs?connection_id=user@host:port

# 3. 启动 Remote Viewer
POST /api/remote/viewer/start
Body: {"host": "gpu-server.com", "port": 22, "username": "mluser", "private_key_path": "~/.ssh/id_rsa", "use_agent": true, "remote_root": "~/runicorn_data", "local_port": null, "remote_port": null, "conda_env": "system"}

# 4. 监控状态
GET /api/remote/viewer/status/{session_id}

# 5. 访问远程数据
# 浏览器打开: http://localhost:8081

# 6. 断开连接
POST /api/remote/disconnect
Body: {"host": "gpu-server.com", "port": 22, "username": "mluser"}
```

### 用例: 分析

```bash
# 1. 获取所有实验
GET /api/runs

# 2. 按项目过滤
GET /api/projects/{project}/names/{name}/runs

# 3. 导出数据
GET /api/export?format=json
```

---

## 📊 响应时间基准

基于 10,000 个实验：

| 端点 | 平均响应 | P95 | 后端 |
|------|---------|-----|------|
| `GET /api/runs` | 50-80 毫秒 | 120毫秒 | SQLite |
| `GET /api/runs/{id}/metrics_step` | 100-300 毫秒 | 500毫秒 | 文件读取+解析 |
| `GET /api/health` | < 5 毫秒 | 10毫秒 | 内存 |

---

## 🔐 安全考虑

### 输入验证

所有用户输入都经过验证：

```python
# Run ID 验证
模式: ^[0-9]{8}_[0-9]{6}_[a-f0-9]{6}$
示例: 20250114_153045_a1b2c3

# 项目/名称验证
规则:
- 不能有 '..'（路径遍历）
- 不能有 '/' 或 '\'（路径分隔符）
- 最大长度: 100 字符

# 文件路径验证
规则:
- 任何地方都不能有 '..'
- 必须在存储根目录内
- 三层验证
```

### 速率限制

查看主 README 中的[速率限制](#速率限制)部分。

**要监控的响应头**:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 15
```

### SSH 安全

- 永远不要记录凭据
- 使用 SSH 密钥 > 密码
- 尽可能使用 SSH agent
- 连接不会持久化
- 每分钟最多 5 次连接尝试

---

## 🛠️ 测试 API

### 使用 cURL

```bash
# 基本 GET
curl http://127.0.0.1:23300/api/health

# 带 JSON 体的 POST
curl -X POST http://127.0.0.1:23300/api/runs/soft-delete \
  -H "Content-Type: application/json" \
  -d '{"run_ids": ["20250114_153045_a1b2c3"]}'

```

### 使用 Postman

导入此集合: [runicorn_api.postman_collection.json](../runicorn_api.postman_collection.json)

**或手动创建**:
1. 创建新集合 "Runicorn API"
2. 设置集合变量: `baseUrl = http://127.0.0.1:23300/api`
3. 使用 `{{baseUrl}}/runs` 语法添加请求

### 使用 HTTPie

```bash
# 安装 httpie
pip install httpie

# GET 请求
http GET http://127.0.0.1:23300/api/runs

# 带 JSON 的 POST
http POST http://127.0.0.1:23300/api/runs/soft-delete \
  run_ids:='["20250114_153045_a1b2c3"]'

# 美化输出
http --pretty=all GET http://127.0.0.1:23300/api/config
```

---

## 📱 客户端库

### 官方 SDK

**Python SDK**（推荐）:
```python
import runicorn as rn

# 创建实验
run = rn.init(project="demo", name="exp1")

# 记录指标
run.log({"loss": 0.1, "accuracy": 0.95}, step=100)

# 完成
run.finish()
```

> 🔔 **注意**: 欢迎为其他语言（JavaScript、R、Julia）贡献社区库。查看 [CONTRIBUTING.md](../../CONTRIBUTING.md)。

---

## 🔗 相关资源

### 文档

- **API 概览**: [README.md](./README.md)
- **快速参考**: [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
- **详细模块**: 各个 API 文档
- **示例**: [examples/](../../examples/) 目录

### 交互式工具

- **FastAPI 文档**: `http://127.0.0.1:23300/docs` (Swagger UI)
- **ReDoc**: `http://127.0.0.1:23300/redoc` (替代 UI)
- **OpenAPI Schema**: `http://127.0.0.1:23300/openapi.json`

### 支持

- **Issues**: GitHub Issues
- **安全**: [SECURITY.md](../../SECURITY.md)
- **社区**: [CONTRIBUTING.md](../../CONTRIBUTING.md)

---

## API 变更日志

### v0.6.0 (当前) 🚀
**重大新功能**
- ✅ **增强日志 API**: 控制台捕获、Python logging 处理器、MetricLogger 兼容
- ✅ **资产系统**: SHA256 内容寻址工作区快照，支持去重
- ✅ **路径层级 API**: 灵活的基于路径的实验组织，支持树形导航
- ✅ **SSH 后端架构**: 多后端回退 (OpenSSH → AsyncSSH → Paramiko)
- ✅ **SQLite 存储后端**: 高性能存储，支持连接池和 WAL 模式

### v0.5.4 ⚡
 - ✅ **统一 MetricChart**：单组件支持单实验和多实验视图
 - ✅ **图表懒加载**：基于 IntersectionObserver 的图表渲染
 - ✅ **高级 memo 优化**：数据指纹比较防止不必要的重渲染
- ✅ 前端美化：精美的指标卡片、动画状态徽章

### v0.5.2
**后端性能**
- ✅ **新增 LTTB 降采样** 用于指标端点（`?downsample=N`）
- ✅ **新增增量缓存** 用于指标（基于文件大小的失效机制）
- ✅ 新增 `/metrics/cache/stats` 端点用于缓存监控
- ✅ 新增响应头（`X-Row-Count`, `X-Total-Count`, `X-Last-Step`）
- ✅ 新增指标响应中的 `total` 和 `sampled` 字段

### v0.5.1
**前端详情页优化**
- ✅ 实验详情页的小型 UI 改进
- ✅ 图表渲染的 Bug 修复

### v0.5.0
- ✅ **新增 Remote Viewer API**（12个端点）
- ✅ 弃用旧的 SSH 文件同步 API
- ✅ 支持 SSH 密钥和密码认证
- ✅ 自动 Python 环境检测
- ✅ Remote Viewer 生命周期管理
- ✅ 连接健康监控

### v0.4.0
- ✅ 添加统一 SSH API
- ✅ 增强错误响应
- ✅ 添加速率限制

### v0.3.1
- 基本 Runs API
- 指标查询
- SSH 镜像支持

### 未来版本

**v0.7.0**（计划中）:
- Windows 远程服务器支持
- GraphQL API 支持
- Webhook 通知
- API 密钥认证
- 批量上传端点

---

**交互式文档**: http://127.0.0.1:23300/docs


