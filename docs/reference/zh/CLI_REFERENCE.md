[English](../en/CLI_REFERENCE.md) | [简体中文](CLI_REFERENCE.md)

---

# Runicorn CLI 参考

**文档类型**: 参考  
**版本**: v0.5.0  
**最后更新**: 2025-10-25

---

## 概述

Runicorn 提供统一的命令行接口（CLI）用于管理实验、启动查看器和配置系统。

**安装后可用命令**:
```bash
runicorn --help
```

---

## 命令总览

| 命令 | 说明 | 示例 |
|------|------|------|
| `viewer` | 启动 Web 查看器 | `runicorn viewer` |
| `config` | 管理配置 | `runicorn config --show` |
| `export` | 导出实验数据 | `runicorn export --format json` |
| `import` | 导入实验数据 | `runicorn import data.zip` |
| `clean` | 清理数据 | `runicorn clean --zombie` |
| `version` | 显示版本信息 | `runicorn --version` |

---

## `runicorn viewer` - 启动 Web 查看器

启动 Runicorn Web 查看器服务器。

### 基本用法

```bash
runicorn viewer [OPTIONS]
```

### 选项

#### `--host TEXT`
- **说明**: 绑定的主机地址
- **默认值**: `127.0.0.1`
- **示例**: 
  ```bash
  runicorn viewer --host 0.0.0.0  # 允许外部访问（谨慎使用）
  ```

#### `--port INTEGER`
- **说明**: 监听端口
- **默认值**: `23300`
- **范围**: `1024-65535`
- **示例**: 
  ```bash
  runicorn viewer --port 8080
  ```

#### `--storage-root PATH`
- **说明**: 数据存储根目录
- **默认值**: `~/RunicornData`
- **示例**: 
  ```bash
  runicorn viewer --storage-root /data/experiments
  runicorn viewer --storage-root E:\RunicornData  # Windows
  ```

#### `--no-open-browser`
- **说明**: 不自动打开浏览器
- **默认值**: 自动打开
- **示例**: 
  ```bash
  runicorn viewer --no-open-browser
  ```

#### `--log-level TEXT`
- **说明**: 日志级别
- **选项**: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- **默认值**: `INFO`
- **示例**: 
  ```bash
  runicorn viewer --log-level DEBUG
  ```

#### `--cors-origin TEXT`
- **说明**: 允许的 CORS 源（可多次指定）
- **默认值**: 无
- **示例**: 
  ```bash
  runicorn viewer --cors-origin http://localhost:3000
  ```

#### `--remote-mode` ⭐ v0.5.0 新增
- **说明**: 以远程模式启动（通常由系统自动调用）
- **用途**: 在远程服务器上运行 Viewer
- **示例**: 
  ```bash
  runicorn viewer --remote-mode --port 45342
  ```
- **注意**: 此选项一般不需要手动使用

### 使用示例

#### 基本启动
```bash
# 使用默认配置启动
runicorn viewer

# 启动后自动打开浏览器到 http://127.0.0.1:23300
```

#### 自定义端口和存储路径
```bash
runicorn viewer \
  --port 8080 \
  --storage-root /data/ml_experiments
```

#### 调试模式
```bash
runicorn viewer \
  --log-level DEBUG \
  --no-open-browser
```

#### 共享访问（局域网）
```bash
# ⚠️ 安全警告：仅在可信网络中使用
runicorn viewer \
  --host 0.0.0.0 \
  --port 23300
  
# 其他机器可通过 http://<your-ip>:23300 访问
```

---

## `runicorn config` - 配置管理

管理 Runicorn 配置文件。

### 基本用法

```bash
runicorn config [COMMAND] [OPTIONS]
```

### 子命令

#### `--show`
显示当前配置

```bash
runicorn config --show

# 输出示例：
# Configuration:
#   User Root Dir: /home/user/RunicornData
#   Viewer Port: 23300
#   Log Level: INFO
#   ...
```

#### `--edit`
在默认编辑器中打开配置文件

```bash
runicorn config --edit

# Linux/macOS: 使用 $EDITOR 或 nano
# Windows: 使用 notepad
```

#### `--set-user-root PATH`
设置用户数据根目录

```bash
runicorn config --set-user-root /data/experiments

# 输出：
# User root directory set to: /data/experiments
```

#### `--reset`
重置配置为默认值

```bash
runicorn config --reset

# 需要确认
# Are you sure you want to reset configuration? [y/N]: y
# Configuration reset to defaults.
```

#### `--validate`
验证配置文件

```bash
runicorn config --validate

# 输出：
# ✓ Configuration file is valid
# ✓ All paths are accessible
# ✓ Port 23300 is available
```

#### `--path`
显示配置文件路径

```bash
runicorn config --path

# Linux/macOS 输出：
# ~/.config/runicorn/config.yaml

# Windows 输出：
# C:\Users\Username\AppData\Roaming\Runicorn\config.yaml
```

### 使用示例

```bash
# 查看配置
runicorn config --show

# 修改存储路径
runicorn config --set-user-root /data/experiments

# 验证配置
runicorn config --validate

# 重置配置
runicorn config --reset
```

---

## `runicorn export` - 导出数据

导出实验数据到各种格式。

### 基本用法

```bash
runicorn export [OPTIONS]
```

### 选项

#### `--format TEXT`
- **说明**: 导出格式
- **选项**: `json`, `csv`, `tensorboard`, `zip`
- **默认值**: `json`

#### `--output PATH`
- **说明**: 输出文件路径
- **默认值**: `./runicorn_export_{timestamp}.{format}`

#### `--project TEXT`
- **说明**: 仅导出指定项目

#### `--name TEXT`
- **说明**: 仅导出指定实验名称

#### `--run-id TEXT`
- **说明**: 仅导出指定运行ID

#### `--include-artifacts`
- **说明**: 包含 artifacts 文件

#### `--compress`
- **说明**: 压缩输出

### 使用示例

#### 导出所有数据（JSON）
```bash
runicorn export --format json --output all_experiments.json
```

#### 导出为 CSV
```bash
runicorn export \
  --format csv \
  --project training \
  --output training_results.csv
```

#### 导出到 TensorBoard 格式
```bash
runicorn export \
  --format tensorboard \
  --project mnist \
  --output ./tensorboard_logs/
```

#### 导出单个实验（包含 artifacts）
```bash
runicorn export \
  --run-id 20251025_143022_a1b2c3 \
  --include-artifacts \
  --compress \
  --output experiment_backup.zip
```

#### 导出项目到压缩包
```bash
runicorn export \
  --format zip \
  --project research_2024 \
  --include-artifacts \
  --output research_2024_backup.zip
```

---

## `runicorn import` - 导入数据

从导出文件导入实验数据。

### 基本用法

```bash
runicorn import [FILE] [OPTIONS]
```

### 选项

#### `--merge`
- **说明**: 合并到现有数据（不覆盖）
- **默认**: 如果存在冲突则跳过

#### `--overwrite`
- **说明**: 覆盖现有数据

#### `--dry-run`
- **说明**: 预览导入但不实际执行

### 使用示例

#### 导入 ZIP 文件
```bash
runicorn import experiment_backup.zip
```

#### 导入并覆盖现有数据
```bash
runicorn import all_experiments.json --overwrite
```

#### 预览导入
```bash
runicorn import data.zip --dry-run

# 输出：
# Would import:
#   - Project: training
#     - 10 experiments
#     - 5 artifacts
#   - Total size: 1.2 GB
```

---

## `runicorn clean` - 清理数据

清理过期或无用的数据。

### 基本用法

```bash
runicorn clean [OPTIONS]
```

### 选项

#### `--zombie`
- **说明**: 清理僵尸实验（长时间未完成）
- **定义**: 超过 48 小时状态为 `running` 的实验

#### `--temp`
- **说明**: 清理临时文件

#### `--cache`
- **说明**: 清理缓存文件

#### `--dedup`
- **说明**: 清理孤立的去重文件

#### `--older-than DAYS`
- **说明**: 清理超过指定天数的数据

#### `--dry-run`
- **说明**: 预览清理但不执行

#### `--force`
- **说明**: 强制清理不需要确认

### 使用示例

#### 清理僵尸实验
```bash
runicorn clean --zombie

# 输出：
# Found 3 zombie experiments:
#   - 20251020_100523_xyz123 (5 days old)
#   - 20251019_153045_abc456 (6 days old)
#   - 20251018_092314_def789 (7 days old)
# Clean these experiments? [y/N]: y
# Cleaned 3 experiments.
```

#### 清理所有临时文件
```bash
runicorn clean --temp --cache
```

#### 清理旧数据（30天前）
```bash
runicorn clean --older-than 30 --dry-run

# 预览将被清理的数据
```

#### 强制清理去重池中的孤立文件
```bash
runicorn clean --dedup --force
```

---

## `runicorn version` - 版本信息

显示版本信息和系统状态。

### 基本用法

```bash
runicorn --version
# 或
runicorn version
```

### 输出示例

```
Runicorn 0.5.0

Platform: Linux-5.15.0-x86_64
Python: 3.10.12
Storage: /home/user/RunicornData (42.3 GB used)
Database: V2 API enabled
Remote Viewer: Available

Components:
  - FastAPI: 0.110.0
  - SQLite: 3.37.2
  - Paramiko: 3.3.1
  - React: 18.2.0
```

### 详细信息

```bash
runicorn version --verbose

# 包括更多系统信息和依赖版本
```

---

## 全局选项

所有命令都支持以下全局选项：

### `--help`
显示帮助信息

```bash
runicorn --help
runicorn viewer --help
runicorn config --help
```

### `--version`
显示版本信息

```bash
runicorn --version
```

### `--quiet`
静默模式（减少输出）

```bash
runicorn export --format json --quiet
```

### `--verbose`
详细模式（更多输出）

```bash
runicorn import data.zip --verbose
```

---

## 环境变量

CLI 命令支持以下环境变量：

| 环境变量 | 影响的选项 | 示例 |
|---------|-----------|------|
| `RUNICORN_USER_ROOT_DIR` | `--storage-root` | `/data/experiments` |
| `RUNICORN_VIEWER_PORT` | `--port` | `8080` |
| `RUNICORN_LOG_LEVEL` | `--log-level` | `DEBUG` |
| `EDITOR` | `config --edit` | `vim` |

**使用示例**:
```bash
# Linux/macOS
export RUNICORN_USER_ROOT_DIR=/data/ml
runicorn viewer

# Windows PowerShell
$env:RUNICORN_USER_ROOT_DIR="E:\ML"
runicorn viewer
```

---

## 常见使用场景

### 场景 1: 首次启动

```bash
# 1. 检查版本
runicorn --version

# 2. 配置存储路径
runicorn config --set-user-root ~/my_experiments

# 3. 启动 Viewer
runicorn viewer
```

### 场景 2: 远程服务器使用

```bash
# 在远程服务器上
# 1. 启动 Viewer（不打开浏览器）
runicorn viewer --no-open-browser

# 2. 在本地使用 SSH 隧道
# ssh -L 23300:localhost:23300 user@remote-server

# 3. 在本地浏览器访问
# http://localhost:23300
```

### 场景 3: 数据迁移

```bash
# 旧服务器
runicorn export \
  --format zip \
  --include-artifacts \
  --output backup_2024.zip

# 传输文件到新服务器
scp backup_2024.zip user@new-server:/tmp/

# 新服务器
runicorn import /tmp/backup_2024.zip
```

### 场景 4: 定期清理

```bash
# 创建清理脚本 cleanup.sh
#!/bin/bash
runicorn clean --zombie --force
runicorn clean --temp --cache --force
runicorn clean --older-than 90 --dry-run

# 设置定时任务（cron）
# 0 2 * * 0  /path/to/cleanup.sh
```

### 场景 5: 调试问题

```bash
# 启动调试模式
runicorn viewer \
  --log-level DEBUG \
  --no-open-browser \
  --port 23300 2>&1 | tee runicorn_debug.log

# 检查配置
runicorn config --validate

# 查看版本信息
runicorn version --verbose
```

---

## 退出代码

| 代码 | 含义 | 说明 |
|------|------|------|
| `0` | 成功 | 命令执行成功 |
| `1` | 一般错误 | 命令执行失败 |
| `2` | 配置错误 | 配置文件无效或缺失 |
| `3` | 权限错误 | 权限不足 |
| `4` | 资源不可用 | 端口占用或路径不存在 |

**使用示例**:
```bash
runicorn viewer --port 23300
if [ $? -eq 0 ]; then
    echo "Viewer started successfully"
else
    echo "Failed to start viewer"
fi
```

---

## 快捷命令别名

可以在 shell 配置文件中添加别名：

### Bash/Zsh (~/.bashrc 或 ~/.zshrc)

```bash
# Runicorn 别名
alias rv='runicorn viewer'
alias rc='runicorn config'
alias rexp='runicorn export'
alias rimp='runicorn import'
```

### PowerShell (Microsoft.PowerShell_profile.ps1)

```powershell
# Runicorn 别名
Set-Alias rv 'runicorn viewer'
function rc { runicorn config $args }
function rexp { runicorn export $args }
```

**使用**:
```bash
rv              # runicorn viewer
rc --show       # runicorn config --show
rexp --format json  # runicorn export --format json
```

---

## Shell 自动补全

### Bash

```bash
# 添加到 ~/.bashrc
eval "$(_RUNICORN_COMPLETE=bash_source runicorn)"
```

### Zsh

```bash
# 添加到 ~/.zshrc
eval "$(_RUNICORN_COMPLETE=zsh_source runicorn)"
```

### PowerShell

```powershell
# 添加到 profile
Register-ArgumentCompleter -Native -CommandName runicorn -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    # 自动补全逻辑
}
```

---

## 故障排查

### 命令未找到

```bash
# 检查安装
pip show runicorn

# 检查 PATH
which runicorn  # Linux/macOS
where runicorn  # Windows
```

### 端口已占用

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
# Linux/macOS: 检查文件权限
ls -la ~/.config/runicorn/

# 修复权限
chmod 700 ~/.config/runicorn/
chmod 600 ~/.config/runicorn/config.yaml
```

---

## 相关文档

- **[配置参考](CONFIGURATION.md)** - 配置文件详解
- **[API 参考](../../api/zh/README.md)** - HTTP API 文档
- **[用户指南](../../guides/zh/QUICKSTART.md)** - 快速开始

---

**返回**: [参考文档索引](README.md) | [主文档](../../README.md)


