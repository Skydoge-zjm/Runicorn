[English](../en/RATE_LIMIT_CONFIGURATION.md) | [简体中文](RATE_LIMIT_CONFIGURATION.md)

---

# 速率限制配置指南

## 概述

Runicorn 中的速率限制系统现在可以通过 JSON 配置文件进行配置，无需修改代码即可轻松调整限制。

## 配置文件位置

速率限制配置存储在：
- 主要位置: `src/runicorn/config/rate_limits.json`
- 备用位置: `src/runicorn/rate_limits.json`

## 配置结构

```json
{
  "_comment": "速率限制很高，因为这是本地API，无互联网暴露",
  "default": {
    "max_requests": 6000,
    "window_seconds": 60,
    "burst_size": null,
    "description": "默认速率限制 - 本地使用非常宽松"
  },
  "endpoints": {
    "/api/endpoint/path": {
      "max_requests": 100,
      "window_seconds": 60,
      "burst_size": 20,
      "description": "端点特定配置"
    }
  },
  "settings": {
    "enable_rate_limiting": true,
    "log_violations": true,
    "whitelist_localhost": false,
    "custom_headers": {
      "rate_limit_header": "X-RateLimit-Limit",
      "rate_limit_remaining_header": "X-RateLimit-Remaining",
      "rate_limit_reset_header": "X-RateLimit-Reset"
    }
  }
}
```

## 配置参数

### Default 部分
- `max_requests`: 时间窗口内允许的最大请求数
- `window_seconds`: 时间窗口（秒）
- `burst_size`: 可选的突发大小限制（如为 null 则默认为 max_requests）
- `description`: 限制的人类可读描述

### Endpoints 部分
每个端点可以有自己的特定配置，参数与 default 部分相同。

### Settings 部分
- `enable_rate_limiting`: 启用/禁用速率限制的主开关
- `log_violations`: 是否记录速率限制违规
- `whitelist_localhost`: 是否对 localhost 请求绕过速率限制
- `custom_headers`: 速率限制信息的自定义头部名称

## 常见配置

### 1. 连接端点（限制性）
```json
"/api/remote/connect": {
  "max_requests": 10,
  "window_seconds": 60,
  "description": "SSH 连接操作 - 防止暴力破解"
}
```

### 2. 状态轮询端点（非常宽松）
```json
"/api/unified/status": {
  "max_requests": 20000,
  "window_seconds": 60,
  "description": "状态轮询 - UI 更新非常宽松"
}
```

### 3. 下载端点（适中）
```json
"/api/remote/download": {
  "max_requests": 3000,
  "window_seconds": 60,
  "description": "文件下载 - 适度限制"
}
```

## 修改速率限制

### 1. 编辑配置文件
```bash
# 编辑配置
nano src/runicorn/config/rate_limits.json
```

### 2. 重启应用程序
配置在速率限制器首次初始化时加载。重启 Runicorn viewer 以应用更改：
```bash
runicorn viewer
```

## CLI 管理

### 查看当前配置
```bash
runicorn rate-limit --action show
```

### 列出所有限制
```bash
runicorn rate-limit --action list
```

### 设置端点限制
```bash
runicorn rate-limit --action set \
  --endpoint "/api/ssh/connect" \
  --max-requests 5 \
  --window 60 \
  --description "SSH 连接尝试限制"
```

### 移除端点限制
```bash
runicorn rate-limit --action remove --endpoint "/api/ssh/connect"
```

### 修改全局设置
```bash
# 启用速率限制
runicorn rate-limit --action settings --enable

# 禁用速率限制
runicorn rate-limit --action settings --disable

# 启用违规日志
runicorn rate-limit --action settings --log-violations

# 白名单 localhost
runicorn rate-limit --action settings --whitelist-localhost
```

## 最佳实践

### 1. 为敏感端点设置严格限制

**SSH 连接**（防止暴力破解）:
```json
"/api/ssh/connect": {
  "max_requests": 5,
  "window_seconds": 60
}
```

**批量删除**（防止误操作）:
```json
"/api/runs/soft-delete": {
  "max_requests": 10,
  "window_seconds": 60
}
```

### 2. 为查询端点设置宽松限制

**V2 实验查询**（高性能API）:
```json
"/api/v2/experiments": {
  "max_requests": 200,
  "window_seconds": 60
}
```

### 3. 开发环境禁用限制

```json
{
  "settings": {
    "enable_rate_limiting": false,
    "whitelist_localhost": true
  }
}
```

## 速率限制响应

当超过限制时，API 返回：

**状态码**: `429 Too Many Requests`

**响应体**:
```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 45
}
```

**响应头**:
```
Retry-After: 45
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 45
```

## 客户端处理

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

**最后更新**: 2025-10-14

