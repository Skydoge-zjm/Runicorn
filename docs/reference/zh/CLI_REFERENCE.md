[English](../en/CLI_REFERENCE.md) | [简体中文](CLI_REFERENCE.md)

---

# Runicorn CLI 参考

**文档类型**: 参考  
**版本**: v0.6.0  
**最后更新**: 2026-01-15

---

## 概述

Runicorn 提供统一的命令行接口（CLI）用于管理实验、启动查看器和配置系统。

```bash
runicorn --help
```

---

## 命令总览

| 命令 | 说明 | 示例 |
|------|------|------|
| `viewer` | 启动 Web 查看器 | `runicorn viewer` |
| `config` | 管理配置 | `runicorn config --show` |
| `export` | 导出实验到 .tar.gz 归档 | `runicorn export --out backup.tar.gz` |
| `import` | 从归档导入实验 | `runicorn import --archive backup.tar.gz` |
| `export-data` | 导出运行指标到 CSV/Excel | `runicorn export-data --run-id ID --format csv` |
| `manage` | 管理实验（标签、搜索、删除、清理） | `runicorn manage --action search` |
| `rate-limit` | 管理 API 限流 | `runicorn rate-limit --action show` |
| `delete` | 永久删除实验及孤立资产 | `runicorn delete --run-id ID` |

---

## `runicorn viewer` - 启动 Web 查看器

启动 Runicorn Web 查看器服务器。

### 基本用法

```bash
runicorn viewer [OPTIONS]
```

### 选项

#### `--storage PATH`
- **说明**: 数据存储根目录
- **默认值**: 使用 `RUNICORN_DIR` 环境变量、全局配置或传统 `./.runicorn`
- **示例**: `runicorn viewer --storage /data/experiments`

#### `--host TEXT`
- **说明**: 绑定的主机地址
- **默认值**: `127.0.0.1`
- **示例**: `runicorn viewer --host 0.0.0.0`

#### `--port INTEGER`
- **说明**: 监听端口
- **默认值**: `23300`
- **示例**: `runicorn viewer --port 8080`

#### `--reload`
- **说明**: 启用自动重载（仅开发用）
- **示例**: `runicorn viewer --reload`

#### `--remote-mode` ⭐ v0.5.0 新增
- **说明**: 以远程模式启动（绑定 127.0.0.1，启用自动关闭）
- **示例**: `runicorn viewer --remote-mode --port 45342`

#### `--log-level TEXT`
- **说明**: 日志级别
- **选项**: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- **默认值**: `INFO`
- **示例**: `runicorn viewer --log-level DEBUG`

### 使用示例

```bash
# 基本启动
runicorn viewer

# 自定义端口和存储路径
runicorn viewer --port 8080 --storage /data/ml

# 调试模式
runicorn viewer --log-level DEBUG

# 局域网共享（⚠️ 注意安全）
runicorn viewer --host 0.0.0.0
```

---

## `runicorn config` - 配置管理

### 基本用法

```bash
runicorn config [OPTIONS]
```

### 选项

#### `--show`
显示当前配置（未指定其他选项时为默认行为）。

```bash
runicorn config --show
```

#### `--set-user-root PATH`
设置用户数据根目录。

```bash
runicorn config --set-user-root /data/experiments
```

### 使用示例

```bash
# 查看当前配置
runicorn config --show

# 设置存储根目录
runicorn config --set-user-root ~/my_experiments
```

---

## `runicorn export` - 导出实验

将实验导出为 `.tar.gz` 归档用于离线迁移。

### 基本用法

```bash
runicorn export [OPTIONS]
```

### 选项

- `--storage PATH`: 存储根目录（默认：从配置或 `RUNICORN_DIR` 获取）
- `--project TEXT`: 按项目名过滤
- `--name TEXT`: 按实验名过滤
- `--run-id TEXT`: 导出指定的 Run ID（可多次指定）
- `--out PATH`: 输出归档路径（默认：`runicorn_export_<时间戳>.tar.gz`）

### 使用示例

```bash
# 导出全部实验
runicorn export --out backup.tar.gz

# 导出指定项目
runicorn export --project training --out training_backup.tar.gz

# 导出指定实验
runicorn export --run-id 20260115_120000_abc123 --run-id 20260115_130000_def456

# 从自定义存储目录导出
runicorn export --storage /data/ml --out archive.tar.gz
```

---

## `runicorn import` - 导入实验

从 `.zip` 或 `.tar.gz` 归档导入实验到存储目录。

### 基本用法

```bash
runicorn import --archive FILE [OPTIONS]
```

### 选项

- `--storage PATH`: 目标存储根目录（默认：从配置或 `RUNICORN_DIR` 获取）
- `--archive PATH`: **（必填）** 要导入的 `.zip` 或 `.tar.gz` 归档路径

### 使用示例

```bash
# 导入归档
runicorn import --archive backup.tar.gz

# 导入到指定存储目录
runicorn import --archive backup.zip --storage /data/experiments
```

---

## `runicorn export-data` - 导出指标数据

将运行指标导出为 CSV、Excel、Markdown 或 HTML 格式。

### 基本用法

```bash
runicorn export-data --run-id ID [OPTIONS]
```

### 选项

- `--storage PATH`: 存储根目录
- `--run-id TEXT`: **（必填）** 要导出的 Run ID
- `--format TEXT`: 导出格式：`csv`（默认）、`excel`、`markdown`、`html`
- `--output PATH`: 输出文件路径（默认：自动生成）

### 使用示例

```bash
# 导出为 CSV（输出到终端）
runicorn export-data --run-id 20260115_120000_abc123

# 导出为 Excel
runicorn export-data --run-id 20260115_120000_abc123 --format excel --output results.xlsx

# 导出为 HTML 报告
runicorn export-data --run-id 20260115_120000_abc123 --format html --output report.html
```

---

## `runicorn manage` - 管理实验

对实验进行标签、搜索、删除或清理操作。

### 基本用法

```bash
runicorn manage --action ACTION [OPTIONS]
```

### 操作类型

#### `--action tag`
为实验添加标签。

```bash
runicorn manage --action tag --run-id ID --tags "baseline,v2"
```

#### `--action search`
按项目、标签或文本搜索实验。

```bash
runicorn manage --action search --project vision --tags "baseline"
runicorn manage --action search --text "resnet"
```

#### `--action delete`
删除指定实验。

```bash
runicorn manage --action delete --run-id ID
```

#### `--action cleanup`
清理过期实验。

```bash
# 预览清理（不实际删除）
runicorn manage --action cleanup --days 30 --dry-run

# 实际清理
runicorn manage --action cleanup --days 90
```

### 选项

- `--storage PATH`: 存储根目录
- `--run-id TEXT`: Run ID（用于 tag/delete 操作）
- `--tags TEXT`: 逗号分隔的标签（用于 tag/search 操作）
- `--project TEXT`: 按项目过滤（用于 search 操作）
- `--text TEXT`: 搜索文本（用于 search 操作）
- `--days INTEGER`: 清理天数阈值（默认：30）
- `--dry-run`: 预览清理，不实际删除

---

## `runicorn rate-limit` - 管理 API 限流

管理 Viewer API 的限流配置。

### 基本用法

```bash
runicorn rate-limit --action ACTION [OPTIONS]
```

### 操作类型

| 操作 | 说明 |
|------|------|
| `show` | 显示完整限流配置（JSON） |
| `list` | 列出所有已配置的限制 |
| `get` | 获取特定端点的限制 |
| `set` | 设置端点的限制 |
| `remove` | 移除端点的限制 |
| `settings` | 更新全局设置 |
| `reset` | 重置为默认配置 |
| `validate` | 验证配置 |

### 使用示例

```bash
# 查看配置
runicorn rate-limit --action show

# 设置端点限流
runicorn rate-limit --action set --endpoint /api/remote/connect --max-requests 5 --window 60

# 启用限流
runicorn rate-limit --action settings --enable

# 验证配置
runicorn rate-limit --action validate
```

---

## `runicorn delete` - 删除实验及资产

永久删除实验并清理孤立资产（blob 文件）。

### 基本用法

```bash
runicorn delete --run-id ID [OPTIONS]
```

### 选项

- `--storage PATH`: 存储根目录
- `--run-id TEXT`: **（必填）** 要删除的 Run ID（可多次指定）
- `--dry-run`: 预览删除，不实际执行
- `--force`: 跳过确认提示

### 使用示例

```bash
# 预览删除
runicorn delete --run-id 20260115_120000_abc123 --dry-run

# 删除（需确认）
runicorn delete --run-id 20260115_120000_abc123

# 强制删除多个实验
runicorn delete --run-id run1 --run-id run2 --force
```

---

## 环境变量

| 变量 | 影响 | 示例 |
|------|------|------|
| `RUNICORN_DIR` | 所有命令的 `--storage` | `/data/experiments` |
| `RUNICORN_USER_ROOT_DIR` | 全局存储根目录 | `/data/experiments` |
| `RUNICORN_SSH_PATH` | SSH 程序路径（v0.6.0） | `/usr/local/bin/ssh` |
| `EDITOR` | 配置编辑器 | `vim` |

**使用方式**：
```bash
# Linux/macOS
export RUNICORN_DIR=/data/ml
runicorn viewer

# Windows PowerShell
$env:RUNICORN_DIR="E:\ML"
runicorn viewer
```

---

## 常见场景

### 首次配置

```bash
runicorn config --set-user-root ~/my_experiments
runicorn viewer
```

### 远程服务器使用

```bash
# 在远程服务器上
runicorn viewer --remote-mode

# 在本地机器上（SSH 隧道）
ssh -L 23300:localhost:23300 user@remote-server

# 通过浏览器访问
# http://localhost:23300
```

### 数据迁移

```bash
# 旧服务器
runicorn export --out backup.tar.gz

# 传输到新服务器
scp backup.tar.gz user@new-server:/tmp/

# 新服务器
runicorn import --archive /tmp/backup.tar.gz
```

### 定期清理

```bash
# 预览将被删除的实验
runicorn manage --action cleanup --days 90 --dry-run

# 清理旧实验
runicorn manage --action cleanup --days 90
```

---

## 退出代码

| 代码 | 含义 | 说明 |
|------|------|------|
| `0` | 成功 | 命令执行成功 |
| `1` | 错误 | 命令执行失败 |

---

## 故障排除

### 命令未找到

```bash
pip show runicorn
which runicorn  # Linux/macOS
where runicorn  # Windows
```

### 端口被占用

```bash
# Linux/macOS
lsof -i :23300

# Windows
netstat -ano | findstr :23300

# 使用其他端口
runicorn viewer --port 23301
```

### 权限问题

```bash
# 检查权限
ls -la ~/.config/runicorn/

# 修复权限
chmod 700 ~/.config/runicorn/
chmod 600 ~/.config/runicorn/config.yaml
```

---

## 相关文档

- **[配置参考](CONFIGURATION.md)** - 配置文件说明
- **[API 参考](../../api/zh/README.md)** - HTTP API 文档
- **[快速开始](../../guides/zh/QUICKSTART.md)** - 入门指南

---

**返回**: [参考文档](README.md) | [主文档](../../README.md)
