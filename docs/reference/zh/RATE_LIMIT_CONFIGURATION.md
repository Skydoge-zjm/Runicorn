[English](../en/RATE_LIMIT_CONFIGURATION.md) | [简体中文](RATE_LIMIT_CONFIGURATION.md)

---

# 速率限制配置指南

**最后更新**: 2026-05-10

## 概述

当前速率限制实现分成两层：

1. 配置读取与保存  
   `src/runicorn/config/rate_limits.py`
2. 运行时应用  
   `src/runicorn/security/rate_limiter.py`

文档中的路径、示例端点和行为均以这两处实现为准。

## 配置加载优先级

`get_rate_limit_config()` 当前按以下顺序加载：

1. 用户配置目录中的 `rate_limits.json`
2. 包内默认文件 `src/runicorn/config/_defaults/rate_limits.json`
3. 读取失败时使用 `rate_limiter.py` 中的 fallback 默认值

包内默认文件会在首次加载时复制到用户配置目录，供后续修改。

## 当前默认文件

仓库中的默认配置文件：

```text
src/runicorn/config/_defaults/rate_limits.json
```

当前默认文件中可核实的特殊配置 bucket 包括：

- `/api/remote/connect`
- `/api/remote/status`
- `/api/metrics/gpu`
- `/api/remote/download`
- `/api/remote/sync`
- `/api/runs`

示例片段：

```json
{
  "default": {
    "max_requests": 6000,
    "window_seconds": 60,
    "burst_size": null
  },
  "endpoints": {
    "/api/remote/connect": {
      "max_requests": 10,
      "window_seconds": 60
    },
    "/api/remote/status": {
      "max_requests": 20000,
      "window_seconds": 60
    }
  },
  "settings": {
    "enable_rate_limiting": false,
    "log_violations": true,
    "whitelist_localhost": false
  }
}
```

## 运行时 fallback

如果配置读取失败，`src/runicorn/security/rate_limiter.py` 会回退到硬编码默认值。当前代码中可确认的 fallback bucket 为：

- `/api/remote/connect`
- `/api/remote/status`
- `/api/remote/download`
- `/api/remote/sync`
- `/api/runs`

需要特别区分两件事：

1. 这些路径当前真实存在于限流配置与 fallback 里
2. 它们不等于当前一定公开注册了对应 API 路由

其中 `/api/remote/download`、`/api/remote/sync` 在本次文档更新时只在 rate-limit 配置与 fallback 中核实到，未在当前 `/api/remote/*` 路由注册表中核实到对应公开接口。因此它们在本页只能作为“限流配置项示例”出现，不能当作当前 API 参考。

## 配置结构

### `default`

- `max_requests`
- `window_seconds`
- `burst_size`
- `description`

### `endpoints`

按端点路径覆盖默认限制，字段与 `default` 一致。

### `settings`

- `enable_rate_limiting`
- `log_violations`
- `whitelist_localhost`
- `custom_headers`

## 当前已确认的读写 API

当前仓库中已确认的配置函数：

- `runicorn.config.get_rate_limit_config`
- `runicorn.config.save_rate_limit_config`

示例：

```python
from runicorn.config import get_rate_limit_config, save_rate_limit_config

config = get_rate_limit_config()
config["endpoints"]["/api/remote/connect"] = {
    "max_requests": 5,
    "window_seconds": 60,
    "burst_size": None,
    "description": "Tighter SSH connection limit"
}
save_rate_limit_config(config)
```

## 适合保留在文档中的示例

### 严格限制连接类端点

```json
"/api/remote/connect": {
  "max_requests": 5,
  "window_seconds": 60
}
```

### 放宽高频轮询端点

```json
"/api/remote/status": {
  "max_requests": 20000,
  "window_seconds": 60
}
```

### 调整全局开关

```json
{
  "settings": {
    "enable_rate_limiting": false,
    "whitelist_localhost": true
  }
}
```

## 响应头

当前响应头名称由 `custom_headers` 控制，默认值为：

```text
X-RateLimit-Limit
X-RateLimit-Remaining
X-RateLimit-Reset
```

超限时仍返回：

```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 45
}
```

## 文档维护要求

当以下内容变化时，应同步更新本文档：

1. `src/runicorn/config/_defaults/rate_limits.json` 中的默认端点集合
2. `get_rate_limit_config()` 的加载优先级
3. `rate_limiter.py` 的 fallback 端点
4. 对外暴露的配置函数名

如果某个路径只存在于 rate-limit 配置中、但没有对应公开路由，文档必须显式标注它是“配置 bucket”，不能写成当前 API 能力。

---

- **[参考文档索引](README.md)**
- **[API 文档概览](../../api/zh/README.md)**
