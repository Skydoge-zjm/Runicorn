[English](../en/CONFIGURATION.md) | [简体中文](CONFIGURATION.md)

---

# Runicorn 配置参考

**文档类型**: 参考  
**版本**: v0.6.0  
**最后更新**: 2026-01-15

---

## 概述

Runicorn 支持通过配置文件和环境变量进行配置。配置文件位置：

- **Linux/macOS**: `~/.config/runicorn/config.yaml`
- **Windows**: `%APPDATA%\Runicorn\config.yaml`

---

## 配置文件格式

```yaml
# Runicorn 配置文件 v0.6.0

# 存储配置
storage:
  # 用户数据根目录
  user_root_dir: ~/RunicornData
  
  # 使用 SQLite 数据库（V2 API）
  use_database: true
  
  # SQLite 数据库路径
  database_path: ${user_root_dir}/runicorn.db
  
  # 自动备份数据库
  auto_backup: true
  backup_interval_hours: 24
  
  # 最大保留备份数
  max_backups: 7

# Viewer 服务器配置
viewer:
  # 监听主机
  host: 127.0.0.1
  
  # 监听端口
  port: 23300
  
  # 自动打开浏览器
  auto_open_browser: true
  
  # 日志级别 (DEBUG|INFO|WARNING|ERROR)
  log_level: INFO
  
  # CORS 允许的源
  cors_origins:
    - http://localhost:3000
    - http://127.0.0.1:3000

# Remote Viewer 配置 (v0.5.0)
remote:
  # SSH 连接超时（秒）
  ssh_timeout: 30
  
  # SSH Keep-alive 间隔（秒）
  ssh_keepalive_interval: 60
  
  # Viewer 启动超时（秒）
  viewer_startup_timeout: 60
  
  # 健康检查间隔（秒）
  health_check_interval: 30
  
  # 自动端口范围
  auto_port_range:
    start: 8081
    end: 8199
  
  # 最大并发连接数
  max_connections: 5
  
  # 日志级别
  log_level: INFO
  
  # 临时文件清理
  cleanup_temp_files: true
  
  # Viewer 日志保留天数
  viewer_log_retention_days: 7

# Assets 系统配置 (v0.6.0)
assets:
  # 初始化时自动快照工作区代码
  snapshot_code: false
  
  # 快照忽略文件
  rnignore_file: .rnignore
  
  # 归档目录
  archive_dir: ${user_root_dir}/archive
  
  # 最大快照大小（MB）
  max_snapshot_size_mb: 500
  
  # 启用 SHA256 去重
  enable_deduplication: true

# 增强日志配置 (v0.6.0)
enhanced_logging:
  # 捕获 stdout/stderr
  capture_console: false
  
  # tqdm 进度条处理模式 (smart/all/none)
  tqdm_mode: smart
  
  # 日志文件最大大小（MB）
  max_log_file_size_mb: 50
  
  # 日志格式
  log_format: "%(asctime)s %(message)s"

# 路径层级配置 (v0.6.0)
paths:
  # 最大路径长度
  max_path_length: 200
  
  # 允许的字符
  allowed_chars: "a-zA-Z0-9_-/"

# Artifacts 配置
artifacts:
  # 启用内容去重
  enable_deduplication: true
  
  # 去重池路径
  dedup_pool_path: ${user_root_dir}/artifacts/.dedup
  
  # 最大文件大小（MB），超过则不去重
  max_dedup_file_size_mb: 1024
  
  # 硬链接回退到复制
  hardlink_fallback_to_copy: true

# 性能配置
performance:
  # SQLite 连接池大小
  db_pool_size: 10
  
  # 查询缓存 TTL（秒）
  query_cache_ttl: 60
  
  # 最大并发请求数
  max_concurrent_requests: 100
  
  # WebSocket 连接超时（秒）
  websocket_timeout: 300

# 安全配置
security:
  # 启用速率限制
  enable_rate_limit: true
  
  # 每分钟最大请求数
  rate_limit_per_minute: 60
  
  # 允许的主机列表（空表示仅 localhost）
  allowed_hosts: []
  
  # SSH 密钥权限检查
  check_ssh_key_permissions: true

# UI 配置
ui:
  # 默认语言 (en|zh)
  default_language: zh
  
  # 默认主题 (light|dark)
  default_theme: light
  
  # 每页显示实验数
  experiments_per_page: 50
  
  # 图表刷新间隔（秒）
  chart_refresh_interval: 5
  
  # 实时日志最大行数
  max_log_lines: 1000

# 日志配置
logging:
  # 日志目录
  log_dir: ~/.config/runicorn/logs
  
  # 日志级别
  level: INFO
  
  # 日志格式
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
  # 日志文件大小限制（MB）
  max_file_size_mb: 10
  
  # 日志文件保留数量
  backup_count: 5
  
  # 输出到控制台
  console_output: true

# 实验配置
experiments:
  # 自动捕获环境信息
  auto_capture_env: true
  
  # 捕获 Git 信息
  capture_git_info: true
  
  # 捕获系统信息
  capture_system_info: true
  
  # 默认状态过期时间（小时）
  status_timeout_hours: 48
  
  # 自动标记僵尸实验
  auto_mark_zombie: true

# 扩展配置
extensions:
  # 启用的扩展
  enabled:
    - gpu_monitor
    - email_notifier
  
  # GPU 监控配置
  gpu_monitor:
    enabled: true
    interval_seconds: 10
  
  # 邮件通知配置
  email_notifier:
    enabled: false
    smtp_host: smtp.gmail.com
    smtp_port: 587
    from_address: runicorn@example.com
```

---

## 配置项详解

### Storage 存储配置

#### `user_root_dir`
- **类型**: 字符串
- **默认值**: `~/RunicornData`
- **说明**: 用户数据根目录，所有实验数据存储在此
- **示例**: `/data/runicorn` 或 `E:\RunicornData`

#### `use_database`
- **类型**: 布尔值
- **默认值**: `true`
- **说明**: 是否使用 SQLite 数据库（V2 API），建议启用以获得更好性能

#### `database_path`
- **类型**: 字符串
- **默认值**: `${user_root_dir}/runicorn.db`
- **说明**: SQLite 数据库文件路径

---

### Viewer 服务器配置

#### `host`
- **类型**: 字符串
- **默认值**: `127.0.0.1`
- **说明**: Viewer 监听的主机地址
- **安全提示**: 生产环境不建议设置为 `0.0.0.0`

#### `port`
- **类型**: 整数
- **默认值**: `23300`
- **说明**: Viewer 监听的端口
- **范围**: `1024-65535`

#### `auto_open_browser`
- **类型**: 布尔值
- **默认值**: `true`
- **说明**: 启动时是否自动打开浏览器

---

### Assets 系统配置（v0.6.0）

#### `snapshot_code`
- **类型**: 布尔值
- **默认值**: `false`
- **说明**: 在 `rn.init()` 时自动快照工作区代码

#### `tqdm_mode`（`enhanced_logging` 下）
- **类型**: 字符串
- **默认值**: `smart`
- **选项**: `smart`, `all`, `none`
- **说明**: tqdm 进度条在日志中的捕获方式

#### `capture_console`（`enhanced_logging` 下）
- **类型**: 布尔值
- **默认值**: `false`
- **说明**: 捕获 stdout/stderr 到实验日志

---

### Remote Viewer 配置（v0.5.0+）

#### `ssh_timeout`
- **类型**: 整数（秒）
- **默认值**: `30`
- **说明**: SSH 连接超时时间
- **推荐**: 网络不稳定时增加到 `60`

#### `ssh_keepalive_interval`
- **类型**: 整数（秒）
- **默认值**: `60`
- **说明**: SSH Keep-alive 发送间隔，保持连接活跃

#### `viewer_startup_timeout`
- **类型**: 整数（秒）
- **默认值**: `60`
- **说明**: 等待远程 Viewer 启动的最大时间

#### `health_check_interval`
- **类型**: 整数（秒）
- **默认值**: `30`
- **说明**: 健康检查执行间隔

#### `auto_port_range`
- **类型**: 对象
- **默认值**: `{start: 8081, end: 8199}`
- **说明**: 自动选择本地端口的范围
- **注意**: 确保该范围内端口未被占用

#### `max_connections`
- **类型**: 整数
- **默认值**: `5`
- **说明**: 最大并发 Remote 连接数
- **范围**: `1-10`

---

### Artifacts 配置

#### `enable_deduplication`
- **类型**: 布尔值
- **默认值**: `true`
- **说明**: 是否启用文件内容去重，可节省 50-90% 存储空间

#### `max_dedup_file_size_mb`
- **类型**: 整数（MB）
- **默认值**: `1024`
- **说明**: 超过此大小的文件不进行去重
- **推荐**: 根据磁盘空间和性能调整

---

## 环境变量

Runicorn 支持通过环境变量覆盖配置：

| 环境变量 | 配置项 | 示例 |
|---------|--------|------|
| `RUNICORN_USER_ROOT_DIR` | `storage.user_root_dir` | `/data/runicorn` |
| `RUNICORN_VIEWER_PORT` | `viewer.port` | `8080` |
| `RUNICORN_LOG_LEVEL` | `viewer.log_level` | `DEBUG` |
| `RUNICORN_REMOTE_TIMEOUT` | `remote.ssh_timeout` | `60` |
| `RUNICORN_SSH_PATH` | SSH 可执行文件路径 (v0.6.0) | `/usr/local/bin/ssh` |
| `RUNICORN_DIR` | `storage.user_root_dir`（别名） | `/data/runicorn` |

**使用示例**:
```bash
# Linux/macOS
export RUNICORN_USER_ROOT_DIR=/data/experiments
export RUNICORN_VIEWER_PORT=8080
runicorn viewer

# Windows (PowerShell)
$env:RUNICORN_USER_ROOT_DIR="E:\Experiments"
$env:RUNICORN_VIEWER_PORT=8080
runicorn viewer
```

---

## 配置优先级

配置项的优先级（从高到低）：

1. **命令行参数**: `runicorn viewer --port 8080`
2. **环境变量**: `RUNICORN_VIEWER_PORT=8080`
3. **配置文件**: `config.yaml`
4. **默认值**: 内置默认值

---

## 配置示例

### 开发环境配置

```yaml
storage:
  user_root_dir: ./dev_data

viewer:
  host: 127.0.0.1
  port: 23300
  log_level: DEBUG

remote:
  log_level: DEBUG
  health_check_interval: 10

logging:
  level: DEBUG
  console_output: true
```

### 生产环境配置

```yaml
storage:
  user_root_dir: /data/runicorn
  auto_backup: true

viewer:
  host: 0.0.0.0  # 谨慎使用
  port: 23300
  log_level: WARNING

remote:
  max_connections: 10
  viewer_startup_timeout: 120

security:
  enable_rate_limit: true
  rate_limit_per_minute: 120

performance:
  db_pool_size: 20
  max_concurrent_requests: 200
```

### 研究团队配置

```yaml
storage:
  user_root_dir: /shared/experiments

artifacts:
  enable_deduplication: true
  max_dedup_file_size_mb: 2048

experiments:
  auto_capture_env: true
  capture_git_info: true

remote:
  max_connections: 20
  health_check_interval: 60

ui:
  experiments_per_page: 100
```

---

## 配置管理命令

### 查看当前配置

```bash
runicorn config --show
```

### 编辑配置文件

```bash
runicorn config --edit
```

### 重置为默认配置

```bash
runicorn config --reset
```

### 验证配置文件

```bash
runicorn config --validate
```

---

## 故障排查

### 配置文件未生效

**检查项**:
1. 确认配置文件路径正确
2. 检查 YAML 语法是否有误
3. 使用 `--validate` 验证配置
4. 检查环境变量是否覆盖了配置

### 端口冲突

**解决方法**:
```yaml
viewer:
  port: 23301  # 更改为其他端口
```

或：
```bash
runicorn viewer --port 23301
```

### Remote 连接超时

**调整配置**:
```yaml
remote:
  ssh_timeout: 120
  viewer_startup_timeout: 180
  health_check_interval: 60
```

---

## 相关文档

- **[CLI 参考](CLI_REFERENCE.md)** - 命令行使用
- **[FAQ](FAQ.md)** - 常见问题
- **[部署架构](../../architecture/zh/DEPLOYMENT.md)** - 部署配置

---

**返回**: [参考文档索引](README.md) | [主文档](../../README.md)


