# Runicorn Refactoring Suggestions

## viewer.py 模块重构建议

### 当前问题
1. 文件过大（777行），难以维护
2. 混合了多种功能（API路由、SSH管理、文件操作等）
3. 缺少适当的错误处理和日志记录

### 建议的模块拆分结构

```
src/runicorn/
├── viewer/
│   ├── __init__.py        # FastAPI app创建
│   ├── api/
│   │   ├── __init__.py
│   │   ├── runs.py        # 运行管理相关API
│   │   ├── metrics.py     # 指标和图表API
│   │   ├── config.py      # 配置管理API
│   │   ├── ssh.py         # SSH远程连接API
│   │   └── import.py      # 导入/导出API
│   ├── models/
│   │   ├── __init__.py
│   │   ├── run.py         # Run数据模型
│   │   ├── metrics.py     # 指标数据模型
│   │   └── ssh.py         # SSH相关模型
│   ├── services/
│   │   ├── __init__.py
│   │   ├── storage.py     # 存储操作服务
│   │   ├── gpu.py         # GPU监控服务
│   │   └── websocket.py   # WebSocket处理
│   └── utils/
│       ├── __init__.py
│       ├── logging.py     # 日志配置
│       └── security.py    # 安全检查工具
```

### 安全性改进

1. **移除_debug_log函数**
   - 使用Python标准logging模块
   - 配置适当的日志级别和格式化器
   - 避免将敏感信息写入日志

2. **改进路径遍历保护**
```python
import os
from pathlib import Path

def secure_path_join(base: Path, *paths) -> Path:
    """Safely join paths preventing directory traversal"""
    base = base.resolve()
    joined = base.joinpath(*paths).resolve()
    
    # Check if the resolved path is within the base directory
    if not str(joined).startswith(str(base)):
        raise ValueError(f"Path traversal detected: {joined}")
    
    return joined
```

3. **SSH凭据安全**
   - 不在内存中长期存储密码
   - 使用加密存储临时凭据
   - 实现会话超时机制

### 性能优化

1. **事件文件处理**
```python
import asyncio
from typing import AsyncIterator

async def read_events_async(events_path: Path, 
                           chunk_size: int = 1000) -> AsyncIterator[dict]:
    """异步读取事件，支持大文件"""
    async with aiofiles.open(events_path, mode='r') as f:
        buffer = []
        async for line in f:
            if line.strip():
                try:
                    event = json.loads(line)
                    buffer.append(event)
                    if len(buffer) >= chunk_size:
                        for evt in buffer:
                            yield evt
                        buffer.clear()
                except json.JSONDecodeError:
                    continue
        
        # Yield remaining events
        for evt in buffer:
            yield evt
```

2. **缓存机制**
```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedStorage:
    def __init__(self, cache_ttl: int = 60):
        self.cache_ttl = cache_ttl
        self._cache = {}
        self._cache_time = {}
    
    def get_run_list(self, force_refresh: bool = False):
        cache_key = "run_list"
        
        if not force_refresh and cache_key in self._cache:
            if datetime.now() - self._cache_time[cache_key] < timedelta(seconds=self.cache_ttl):
                return self._cache[cache_key]
        
        # Load fresh data
        data = self._load_run_list()
        self._cache[cache_key] = data
        self._cache_time[cache_key] = datetime.now()
        return data
```

### 错误处理改进

```python
import logging
from typing import Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class RunicornError(Exception):
    """Base exception for Runicorn errors"""
    pass

class StorageError(RunicornError):
    """Storage related errors"""
    pass

class ConfigError(RunicornError):
    """Configuration errors"""
    pass

def handle_storage_operation(func):
    """Decorator for handling storage operations"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            raise HTTPException(status_code=404, detail=str(e))
        except PermissionError as e:
            logger.error(f"Permission denied: {e}")
            raise HTTPException(status_code=403, detail="Permission denied")
        except StorageError as e:
            logger.error(f"Storage error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.exception("Unexpected error in storage operation")
            raise HTTPException(status_code=500, detail="Internal server error")
    return wrapper
```

### 测试策略

1. **单元测试**
   - 为每个服务模块编写单元测试
   - 使用pytest和pytest-asyncio
   - Mock外部依赖（文件系统、SSH连接等）

2. **集成测试**
   - 使用TestClient测试API端点
   - 创建临时目录进行文件操作测试
   - 使用Docker容器测试SSH功能

3. **性能测试**
   - 使用locust进行负载测试
   - 监控内存使用和响应时间
   - 测试大文件处理能力

### 文档改进

1. **API文档**
   - 使用FastAPI自动生成OpenAPI规范
   - 添加详细的端点描述和示例
   - 提供Postman集合

2. **开发者文档**
   - 架构设计文档
   - 贡献指南
   - 代码风格指南

3. **用户文档**
   - 安装和配置指南
   - 使用教程
   - 故障排除指南
