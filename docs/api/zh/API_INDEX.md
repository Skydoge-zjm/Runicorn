[English](../en/API_INDEX.md) | [简体中文](API_INDEX.md)

---

# 完整 API 索引

**版本**: v0.4.0  
**总端点数**: 40+  
**最后更新**: 2025-10-14

---

## 📑 完整端点列表

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
| GET | `/api/runs/{run_id}/metrics` | 获取基于时间的指标 | [📖](./metrics_api.md#获取指标基于时间) |
| GET | `/api/runs/{run_id}/metrics_step` | 获取基于步骤的指标 | [📖](./metrics_api.md#获取步骤指标) |
| WS | `/api/runs/{run_id}/logs/ws` | 实时日志流 | [📖](./metrics_api.md#实时日志流) |

### Artifacts API (版本控制)

| 方法 | 端点 | 描述 | 文档 |
|------|------|------|------|
| GET | `/api/artifacts` | 列出 artifacts | [📖](./artifacts_api.md#列出-artifacts) |
| GET | `/api/artifacts/{name}/versions` | 列出版本 | [📖](./artifacts_api.md#列出-artifact-版本) |
| GET | `/api/artifacts/{name}/v{version}` | 获取版本详情 | [📖](./artifacts_api.md#获取-artifact-详情) |
| GET | `/api/artifacts/{name}/v{version}/files` | 列出文件 | [📖](./artifacts_api.md#列出-artifact-文件) |
| GET | `/api/artifacts/{name}/v{version}/lineage` | 获取血缘图 | [📖](./artifacts_api.md#获取-artifact-血缘) |
| GET | `/api/artifacts/stats` | 获取存储统计 | [📖](./artifacts_api.md#获取存储统计) |
| DELETE | `/api/artifacts/{name}/v{version}` | 删除版本 | [📖](./artifacts_api.md#删除-artifact-版本) |

### V2 API (高性能) ⚡

| 方法 | 端点 | 描述 | 文档 |
|------|------|------|------|
| GET | `/api/v2/experiments` | 高级查询 | [📖](./v2_api.md#列出实验) |
| GET | `/api/v2/experiments/{id}` | 获取详情 | [📖](./v2_api.md#获取实验详情) |
| GET | `/api/v2/experiments/{id}/metrics/fast` | 快速指标 | [📖](./v2_api.md#快速指标检索) |
| POST | `/api/v2/experiments/batch-delete` | 批量删除 | [📖](./v2_api.md#批量删除) |

### Config API (设置)

| 方法 | 端点 | 描述 | 文档 |
|------|------|------|------|
| GET | `/api/config` | 获取配置 | [📖](./config_api.md#获取配置) |
| POST | `/api/config/user_root_dir` | 设置存储根目录 | [📖](./config_api.md#设置用户根目录) |
| GET | `/api/config/ssh_connections` | 获取已保存的连接 | [📖](./config_api.md#获取已保存的-ssh-连接) |
| POST | `/api/config/ssh_connections` | 保存连接 | [📖](./config_api.md#保存-ssh-连接) |
| DELETE | `/api/config/ssh_connections/{key}` | 删除连接 | [📖](./config_api.md#删除-ssh-连接) |
| GET | `/api/config/ssh_connections/{key}/details` | 获取连接详情 | [📖](./config_api.md) |

### SSH/Remote API (同步)

| 方法 | 端点 | 描述 | 文档 |
|------|------|------|------|
| POST | `/api/unified/connect` | 连接到服务器 | [📖](./ssh_api.md#连接到远程服务器) |
| POST | `/api/unified/disconnect` | 断开连接 | [📖](./ssh_api.md) |
| GET | `/api/unified/status` | 获取状态 | [📖](./ssh_api.md#获取连接状态) |
| GET | `/api/unified/listdir` | 浏览目录 | [📖](./ssh_api.md#浏览远程目录) |
| POST | `/api/unified/configure_mode` | 配置同步 | [📖](./ssh_api.md#配置同步模式) |
| POST | `/api/unified/deactivate_mode` | 停用同步 | [📖](./ssh_api.md) |

### Manifest API (高性能同步) 🚀

| 类型 | 命令/方法 | 描述 | 文档 |
|------|-----------|------|------|
| CLI | `runicorn generate-manifest` | 生成 sync manifest | [📖](./manifest_api.md#cli-命令) |
| CLI | `runicorn generate-manifest --active` | 生成活跃 manifest | [📖](./manifest_api.md#cli-命令) |
| Python | `ManifestGenerator.generate()` | 服务端生成 manifest | [📖](./manifest_api.md#服务端manifestgenerator) |
| Python | `ManifestSyncClient.sync()` | 客户端 manifest sync | [📖](./manifest_api.md#客户端manifestsyncclient) |
| Python | `MetadataSyncService(..., use_manifest_sync=True)` | 自动集成 | [📖](./manifest_api.md#集成到-metadatasyncservice) |

### Projects API (层级)

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/projects` | 列出所有项目 |
| GET | `/api/projects/{project}/names` | 列出项目中的实验名称 |
| GET | `/api/projects/{project}/names/{name}/runs` | 列出实验中的运行 |

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

### 用例: 管理模型

```bash
# 1. 列出所有模型
GET /api/artifacts?type=model

# 2. 查看版本历史
GET /api/artifacts/resnet50-model/versions

# 3. 获取特定版本
GET /api/artifacts/resnet50-model/v3

# 4. 检查依赖关系
GET /api/artifacts/resnet50-model/v3/lineage

# 5. 下载文件
GET /api/artifacts/resnet50-model/v3/files
```

### 用例: 远程同步

```bash
# 1. 连接到服务器
POST /api/unified/connect
Body: {"host": "server", "username": "user", "password": "secret"}

# 2. 浏览远程
GET /api/unified/listdir?path=/data/runicorn

# 3. 配置同步
POST /api/unified/configure_mode
Body: {"mode": "smart", "remote_root": "/data/runicorn"}

# 4. 监控同步
GET /api/unified/status

# 5. 查询已同步的实验
GET /api/runs
```

### 用例: 分析

```bash
# 1. 获取所有实验（使用 V2 以提高性能）
GET /api/v2/experiments?per_page=1000

# 2. 按项目过滤
GET /api/v2/experiments?project=image_classification

# 3. 按性能过滤
GET /api/v2/experiments?best_metric_min=0.9&status=finished

# 4. 获取存储统计
GET /api/artifacts/stats
```

---

## 📊 响应时间基准

基于 10,000 个实验：

| 端点 | 平均响应 | P95 | 后端 |
|------|---------|-----|------|
| `GET /api/runs` | 5-8 秒 | 10秒 | 文件扫描 |
| `GET /api/v2/experiments` | 50-80 毫秒 | 120毫秒 | SQLite |
| `GET /api/runs/{id}/metrics_step` | 100-300 毫秒 | 500毫秒 | 文件读取+解析 |
| `GET /api/v2/experiments/{id}/metrics/fast` | 30-60 毫秒 | 100毫秒 | SQLite（缓存）|
| `GET /api/artifacts` | 200-400 毫秒 | 600毫秒 | 文件扫描 |
| `GET /api/artifacts/stats` | 1-3 秒 | 5秒 | 递归扫描 |

**建议**: 对于涉及大量实验的查询，使用 V2 API。

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

# 带查询参数的 GET
curl "http://127.0.0.1:23300/api/artifacts?type=model"

# 带 JSON 体的 POST
curl -X POST http://127.0.0.1:23300/api/runs/soft-delete \
  -H "Content-Type: application/json" \
  -d '{"run_ids": ["20250114_153045_a1b2c3"]}'

# DELETE
curl -X DELETE "http://127.0.0.1:23300/api/artifacts/old-model/v1?permanent=false"
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
rn.log({"loss": 0.1, "accuracy": 0.95}, step=100)

# 保存 artifact
artifact = rn.Artifact("my-model", type="model")
artifact.add_file("model.pth")
run.log_artifact(artifact)

rn.finish()
```

查看主 [README.md](../../README.md) 获取完整 SDK 文档。

### 社区库

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

## 📝 API 变更日志

### v0.4.0 (当前)
- ✅ 添加 V2 高性能 API
- ✅ 添加 Artifacts API（版本控制）
- ✅ 添加统一 SSH API
- ✅ 增强错误响应
- ✅ 添加速率限制

### v0.3.1
- 基本 Runs API
- 指标查询
- SSH 镜像支持

### 未来版本

**v0.5.0**（计划中）:
- GraphQL API 支持
- 批量上传端点
- Webhook 通知
- API 密钥认证

---

**交互式文档**: http://127.0.0.1:23300/docs


