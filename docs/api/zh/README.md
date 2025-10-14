[English](../en/README.md) | [简体中文](README.md)

---

# Runicorn API 文档

**版本**: v0.4.0  
**基础 URL**: `http://127.0.0.1:23300/api`  
**协议**: HTTP/1.1  
**格式**: JSON  
**字符编码**: UTF-8

---

## 目录

1. [快速开始](#快速开始)
2. [认证](#认证)
3. [API 模块](#api-模块)
4. [错误处理](#错误处理)
5. [速率限制](#速率限制)
6. [版本控制](#版本控制)

---

## 快速开始

### 快速入门

```bash
# 启动 Runicorn viewer
runicorn viewer --host 127.0.0.1 --port 23300

# API 现在可通过以下地址访问
http://127.0.0.1:23300/api
```

### API 健康检查

```bash
GET /api/health

响应:
{
  "status": "ok",
  "version": "0.4.0",
  "timestamp": 1704067200.0
}
```

---

## 认证

**当前版本**: 无需认证（仅本地 API）

> ⚠️ **安全提示**: API 设计为仅本地使用。请勿在没有适当认证和加密的情况下将其暴露到互联网。

**未来版本**: 可能支持 API 密钥用于多用户场景。

---

## API 模块

Runicorn API 按逻辑模块组织：

| 模块 | 描述 | 文档 | 端点数 |
|------|------|------|--------|
| **Runs API** | 实验运行管理（CRUD、软删除、恢复）| [runs_api.md](./runs_api.md) | 6个端点 |
| **Artifacts API** | 模型和数据集版本控制 | [artifacts_api.md](./artifacts_api.md) | 7个端点 |
| **Metrics API** | 实时指标查询和可视化数据 | [metrics_api.md](./metrics_api.md) | 3 HTTP + 1 WebSocket |
| **V2 API** | 高性能 SQLite 查询 ⚡ | [v2_api.md](./v2_api.md) | 4个端点 |
| **Config API** | 配置和偏好设置管理 | [config_api.md](./config_api.md) | 6个端点 |
| **SSH/Remote API** | 通过 SSH 进行远程服务器同步 | [ssh_api.md](./ssh_api.md) | 12个端点 |

**快速参考**: 查看 [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) 获取常用操作

---

## 错误处理

### 标准错误响应

所有错误遵循以下结构：

```json
{
  "detail": "错误消息描述"
}
```

### HTTP 状态码

| 代码 | 含义 | 描述 |
|------|------|------|
| `200` | OK | 请求成功 |
| `201` | Created | 资源创建成功 |
| `400` | Bad Request | 无效的输入参数 |
| `404` | Not Found | 资源未找到 |
| `409` | Conflict | 资源已存在或冲突 |
| `429` | Too Many Requests | 超过速率限制 |
| `500` | Internal Server Error | 服务器错误 |
| `503` | Service Unavailable | 服务暂时不可用 |

### 常见错误示例

```json
// 400 Bad Request
{
  "detail": "Invalid run_id format: abc123. Expected format: YYYYMMDD_HHMMSS_XXXXXX"
}

// 404 Not Found
{
  "detail": "Run not found: 20250101_120000_abc123"
}

// 429 Too Many Requests
{
  "detail": "Rate limit exceeded",
  "retry_after": 45
}

// 500 Internal Server Error
{
  "detail": "Failed to query database: connection timeout"
}
```

---

## 速率限制

### 默认限制

- **默认**: 每个 IP 每分钟 60 个请求
- **敏感端点**: 自定义限制（见各个 API 文档）

### 速率限制响应头

每个响应包含这些头部：

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 15
```

### 处理速率限制

```python
import requests
import time

def api_call_with_retry(url):
    response = requests.get(url)
    
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        print(f"速率限制。等待 {retry_after} 秒...")
        time.sleep(retry_after)
        return api_call_with_retry(url)
    
    return response.json()
```

---

## 版本控制

### API 版本

- **V1 API** (`/api/*`): 稳定，向后兼容，基于文件
- **V2 API** (`/api/v2/*`): 高性能，基于 SQLite，推荐用于新集成

### 版本策略

- **V1**: 为向后兼容而维护，适用于简单用例
- **V2**: 推荐用于生产环境，提供 50-100 倍性能提升

### 迁移指南

查看 [V1_TO_V2_MIGRATION.md](./V1_TO_V2_MIGRATION.md) 获取详细迁移说明。

---

## 快速参考

### 最常用端点

```bash
# 列出所有实验运行
GET /api/runs

# 获取运行详情
GET /api/runs/{run_id}

# 获取运行指标
GET /api/runs/{run_id}/metrics_step

# 列出 artifacts
GET /api/artifacts?type=model

# 获取 artifact 版本
GET /api/artifacts/{name}/versions

# 健康检查
GET /api/health
```

### WebSocket 端点

```bash
# 实时日志流
ws://127.0.0.1:23300/api/runs/{run_id}/logs/ws
```

---

## 其他资源

- **快速开始指南**: [../guides/zh/QUICKSTART.md](../guides/zh/QUICKSTART.md)
- **Python SDK**: 查看 `src/runicorn/sdk.py`
- **OpenAPI Schema**: `http://127.0.0.1:23300/docs` (FastAPI 自动生成)
- **示例**: `examples/` 目录

---

## 支持

- **Issues**: GitHub Issues
- **安全**: 查看 [SECURITY.md](../../SECURITY.md)
- **贡献**: 查看 [CONTRIBUTING.md](../../CONTRIBUTING.md)

---

**最后更新**: 2025-10-14  
**维护者**: Runicorn 开发团队


