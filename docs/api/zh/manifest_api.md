[English](../en/manifest_api.md) | [简体中文](manifest_api.md)

---

# Manifest API 文档

**版本**: v0.4.0  
**模块**: Manifest-Based Sync  
**状态**: ✅ 生产就绪

---

## 📋 目录

1. [概述](#概述)
2. [CLI 命令](#cli-命令)
3. [Python SDK](#python-sdk)
4. [Manifest 格式规范](#manifest-格式规范)
5. [服务端配置](#服务端配置)
6. [客户端配置](#客户端配置)
7. [最佳实践](#最佳实践)
8. [故障排除](#故障排除)

---

## 概述

Manifest-Based Sync 是 Runicorn 的高性能同步系统，通过预生成的元数据清单实现：

- **99% 网络请求减少** (11,000+ → <200 SFTP 操作)
- **95% 同步时间减少** (10分钟 → <30秒)
- **子线性扩展性** 支持 1000+ 实验
- **自动回退** 到 legacy sync 如果 manifest 不可用

### 系统架构

```
服务器端                          客户端
--------                          ------
ManifestGenerator                 ManifestSyncClient
    ↓                                 ↓
生成 manifest.json          →    下载 manifest
(每 5 分钟)                       解析和验证
                                     ↓
保存到 .runicorn/           ←    计算 diff
                                     ↓
                                  同步变更文件
                                  (并发 + 增量)
```

---

## CLI 命令

### `runicorn generate-manifest`

在服务器端生成同步 manifest。

#### 基本用法

```bash
# 生成完整 manifest（所有实验）
runicorn generate-manifest

# 生成活跃 manifest（最近 1 小时）
runicorn generate-manifest --active

# 指定实验根目录
runicorn generate-manifest --root /data/experiments

# 自定义输出路径
runicorn generate-manifest --output /tmp/manifest.json

# 详细日志
runicorn generate-manifest --verbose
```

#### 参数说明

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `--root` | Path | `.` | 实验根目录 |
| `--output` | Path | `<root>/.runicorn/<type>_manifest.json` | 自定义输出路径 |
| `--active` | Flag | - | 生成活跃 manifest（仅最近实验）|
| `--full` | Flag | ✅ | 生成完整 manifest（默认）|
| `--active-window` | Int | `3600` | 活跃窗口时间（秒）|
| `--no-incremental` | Flag | - | 禁用增量生成优化 |
| `--verbose` | Flag | - | 启用调试日志 |

#### 输出示例

```bash
$ runicorn generate-manifest --verbose

============================================================
Manifest Generation Complete
============================================================
Type:          full
Output:        /data/experiments/.runicorn/full_manifest.json
Compressed:    /data/experiments/.runicorn/full_manifest.json.gz
Revision:      42
Snapshot ID:   550e8400-e29b-41d4-a716-446655440000
Experiments:   156
Files:         2340
Total Size:    1.23 GB
============================================================
```

#### 退出代码

| 代码 | 含义 |
|------|------|
| `0` | 成功 |
| `1` | 失败（权限、路径等错误）|
| `130` | 用户中断（Ctrl+C）|

---

## Python SDK

### 服务端：ManifestGenerator

#### 基本用法

```python
from pathlib import Path
from runicorn.manifest import ManifestGenerator, ManifestType

# 创建生成器
generator = ManifestGenerator(
    remote_root=Path("/data/experiments"),
    output_dir=None,  # 默认: {remote_root}/.runicorn
    active_window_seconds=3600,  # 1 小时
    incremental=True
)

# 生成完整 manifest
manifest, output_path = generator.generate(
    manifest_type=ManifestType.FULL
)

print(f"Generated manifest with {manifest.total_experiments} experiments")
print(f"Output: {output_path}")
```

#### 生成活跃 Manifest

```python
# 仅包含最近 30 分钟的实验
manifest, path = generator.generate(
    manifest_type=ManifestType.ACTIVE,
)

# 使用自定义输出路径
manifest, path = generator.generate(
    manifest_type=ManifestType.FULL,
    output_path=Path("/tmp/my_manifest.json")
)
```

#### ManifestGenerator API

```python
class ManifestGenerator:
    def __init__(
        self,
        remote_root: Path,
        output_dir: Optional[Path] = None,
        active_window_seconds: int = 3600,
        incremental: bool = True
    ):
        """
        初始化 manifest 生成器。
        
        Args:
            remote_root: 实验根目录
            output_dir: 输出目录（默认: {remote_root}/.runicorn）
            active_window_seconds: 活跃窗口时间（秒）
            incremental: 启用增量生成
        """
    
    def generate(
        self,
        manifest_type: ManifestType = ManifestType.FULL,
        output_path: Optional[Path] = None
    ) -> Tuple[SyncManifest, Path]:
        """
        生成 sync manifest。
        
        Args:
            manifest_type: FULL 或 ACTIVE
            output_path: 自定义输出路径（可选）
            
        Returns:
            (manifest, output_file_path) 元组
        """
```

### 客户端：ManifestSyncClient

#### 基本用法

```python
from pathlib import Path
import paramiko
from runicorn.remote_storage.manifest_sync import ManifestSyncClient

# 创建 SFTP 客户端
ssh = paramiko.SSHClient()
ssh.connect("server.example.com", username="user", key_filename="~/.ssh/id_rsa")
sftp = ssh.open_sftp()

# 创建同步客户端
client = ManifestSyncClient(
    sftp_client=sftp,
    remote_root="/data/experiments",
    cache_dir=Path("/local/cache"),
    jitter_max=5.0  # 随机 0-5 秒延迟
)

# 执行同步（带进度回调）
def progress_callback(completed, total, current_file):
    percent = (completed / total) * 100
    print(f"[{completed}/{total}] ({percent:.1f}%) {current_file}")

stats = client.sync(progress_callback=progress_callback)

# 检查结果
if stats.get("skipped"):
    print(f"Sync skipped: {stats['reason']}")
else:
    print(f"Synced {stats['files_synced']} files")
    print(f"Downloaded {stats['bytes_downloaded'] / (1024*1024):.2f} MB")
    print(f"Incremental: {stats['incremental_count']}")
    print(f"Full: {stats['full_count']}")
```

#### ManifestSyncClient API

```python
class ManifestSyncClient:
    def __init__(
        self,
        sftp_client: paramiko.SFTPClient,
        remote_root: str,
        cache_dir: Path,
        jitter_max: float = 5.0
    ):
        """
        初始化 manifest sync 客户端。
        
        Args:
            sftp_client: 活跃的 SFTP 客户端
            remote_root: 远程根目录
            cache_dir: 本地缓存目录
            jitter_max: 最大随机延迟（秒，防止惊群）
        """
    
    def sync(
        self,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        执行 manifest-based 同步。
        
        Args:
            progress_callback: 进度回调 (completed, total, current_file)
            
        Returns:
            统计信息字典:
            {
                "files_synced": int,
                "bytes_downloaded": int,
                "incremental_count": int,
                "full_count": int,
                "failed_count": int,
                "duration": float,
                "manifest_revision": int,
                "skipped": bool,  # 如果没有变化
                "reason": str  # 跳过原因
            }
            
        Raises:
            IOError: Manifest 下载失败
            ValueError: Manifest 验证失败
        """
```

### 集成到 MetadataSyncService

Manifest sync 已自动集成到 `MetadataSyncService`：

```python
from runicorn.remote_storage import MetadataSyncService

# 创建服务（manifest sync 默认启用）
service = MetadataSyncService(
    ssh_session=ssh_client,
    sftp_client=sftp,
    remote_root="/data/experiments",
    cache_manager=cache,
    use_manifest_sync=True,      # 默认: True
    manifest_sync_jitter=5.0      # 默认: 5.0 秒
)

# 同步 - 自动尝试 manifest，失败时回退到 legacy
success = service.sync_all()
```

#### 禁用 Manifest Sync

```python
# 仅使用 legacy sync
service = MetadataSyncService(
    ...,
    use_manifest_sync=False
)
```

---

## Manifest 格式规范

### Manifest 结构

```json
{
  "format_version": "1.0",
  "manifest_type": "full",  // 或 "active"
  "revision": 42,
  "snapshot_id": "550e8400-e29b-41d4-a716-446655440000",
  "generated_at": 1704067200.0,
  "server_hostname": "ml-server-01",
  "remote_root": "/data/experiments",
  "experiments": [
    {
      "run_id": "20250101_120000_abc123",
      "project": "my_project",
      "name": "experiment_1",
      "status": "completed",
      "created_at": 1704060000.0,
      "updated_at": 1704067000.0,
      "files": [
        {
          "path": "my_project/experiment_1/runs/20250101_120000_abc123/meta.json",
          "size": 1024,
          "mtime": 1704060000.0,
          "priority": 1,
          "is_append_only": false
        },
        {
          "path": "my_project/experiment_1/runs/20250101_120000_abc123/events.jsonl",
          "size": 524288,
          "mtime": 1704067000.0,
          "tail_hash": "5d41402abc4b2a76b9719d911017c592",
          "priority": 3,
          "is_append_only": true
        }
      ],
      "tags": ["production", "v2"]
    }
  ],
  "statistics": {
    "total_experiments": 156,
    "total_files": 2340,
    "total_bytes": 1234567890
  },
  "generator_version": "1.0"
}
```

### 字段说明

#### Manifest 元数据

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `format_version` | String | ✅ | Manifest 格式版本 |
| `manifest_type` | String | ✅ | "full" 或 "active" |
| `revision` | Integer | ✅ | 单调递增的修订号 |
| `snapshot_id` | String | ✅ | 唯一快照标识符（UUID）|
| `generated_at` | Float | ✅ | 生成时间戳 |
| `server_hostname` | String | ✅ | 服务器标识 |
| `remote_root` | String | ✅ | 远程根路径 |

#### Experiment Entry

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `run_id` | String | ✅ | 运行唯一标识符 |
| `project` | String | ✅ | 项目名称 |
| `name` | String | ✅ | 实验名称 |
| `status` | String | ✅ | 运行状态 |
| `created_at` | Float | ✅ | 创建时间戳 |
| `updated_at` | Float | ✅ | 更新时间戳 |
| `files` | Array | ✅ | 文件列表 |
| `tags` | Array | - | 可选标签 |

#### File Entry

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `path` | String | ✅ | 相对路径（POSIX 格式）|
| `size` | Integer | ✅ | 文件大小（字节）|
| `mtime` | Float | ✅ | 修改时间戳 |
| `priority` | Integer | - | 同步优先级（1=最高）|
| `is_append_only` | Boolean | - | 是否为追加文件 |
| `tail_hash` | String | - | 尾部哈希（追加文件验证）|

### 文件优先级

| 优先级 | 值 | 文件类型 | 描述 |
|--------|----|----|------|
| Critical | 1 | meta.json, status.json | 关键元数据 |
| High | 2 | summary.json | 汇总信息 |
| Medium | 3 | events.jsonl, logs.txt | 实验数据 |
| Low | 4 | media/* | 媒体文件 |

---

## 服务端配置

### 自动生成配置

#### Systemd（Linux，推荐）

**完整 Manifest Timer** (`/etc/systemd/system/runicorn-manifest.timer`):

```ini
[Unit]
Description=Runicorn Full Manifest Generation Timer
Requires=runicorn-manifest.service

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
AccuracySec=30s

[Install]
WantedBy=timers.target
```

**完整 Manifest Service** (`/etc/systemd/system/runicorn-manifest.service`):

```ini
[Unit]
Description=Runicorn Full Manifest Generation
After=network.target

[Service]
Type=oneshot
User=mluser
Group=mluser
WorkingDirectory=/data/experiments
ExecStart=/usr/local/bin/runicorn generate-manifest --full --root /data/experiments
StandardOutput=append:/var/log/runicorn/manifest.log
StandardError=append:/var/log/runicorn/manifest.error.log

[Install]
WantedBy=multi-user.target
```

**启用和启动**:

```bash
# 创建日志目录
sudo mkdir -p /var/log/runicorn
sudo chown mluser:mluser /var/log/runicorn

# 重载 systemd
sudo systemctl daemon-reload

# 启用和启动 timer
sudo systemctl enable runicorn-manifest.timer
sudo systemctl start runicorn-manifest.timer

# 检查状态
systemctl status runicorn-manifest.timer
systemctl list-timers runicorn*
```

#### Cron（Linux/macOS）

```bash
# 编辑 crontab
crontab -e

# 每 5 分钟生成完整 manifest
*/5 * * * * cd /data/experiments && runicorn generate-manifest --full >> /var/log/runicorn/manifest.log 2>&1

# 每分钟生成活跃 manifest（可选）
* * * * * cd /data/experiments && runicorn generate-manifest --active >> /var/log/runicorn/manifest-active.log 2>&1
```

#### Windows Task Scheduler

**PowerShell 脚本** (`C:\Scripts\generate-manifest.ps1`):

```powershell
$ErrorActionPreference = "Stop"
$ExperimentsDir = "D:\experiments"
$LogFile = "C:\Logs\runicorn\manifest.log"

# 创建日志目录
$LogDir = Split-Path -Parent $LogFile
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force
}

# 记录开始时间
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LogFile -Value "$timestamp - Starting manifest generation"

try {
    Set-Location $ExperimentsDir
    & runicorn generate-manifest --full --root $ExperimentsDir 2>&1 | Add-Content -Path $LogFile
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "$timestamp - Completed successfully"
    
} catch {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "$timestamp - ERROR: $($_.Exception.Message)"
    exit 1
}
```

**任务配置**:
1. 打开任务计划程序
2. 创建任务
3. 触发器：每 5 分钟重复
4. 操作：`powershell.exe -ExecutionPolicy Bypass -File "C:\Scripts\generate-manifest.ps1"`

---

## 客户端配置

### 启用 Manifest Sync

```python
from runicorn.remote_storage import MetadataSyncService

service = MetadataSyncService(
    ssh_session=ssh,
    sftp_client=sftp,
    remote_root="/data/experiments",
    cache_manager=cache,
    
    # Manifest sync 配置
    use_manifest_sync=True,      # 启用 manifest-first sync
    manifest_sync_jitter=5.0,     # 0-5 秒随机延迟
)
```

### 监控和日志

```python
import logging

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)

# 查看 manifest sync 日志
logger = logging.getLogger('runicorn.remote_storage.manifest_sync')
logger.setLevel(logging.DEBUG)
```

---

## 最佳实践

### 服务端

1. **生成频率**
   - 小型实验室（<100 实验）：每 5 分钟
   - 中型实验室（100-500）：每 10 分钟
   - 大型实验室（>500）：每 15 分钟

2. **Manifest 类型**
   - **Full manifest**: 定期生成（5-15 分钟）
   - **Active manifest**: 可选，用于快速更新（1-2 分钟）

3. **监控**
   ```bash
   # 检查 manifest 新鲜度
   ls -lh /data/experiments/.runicorn/*.json
   
   # 查看生成日志
   tail -f /var/log/runicorn/manifest.log
   
   # 验证 manifest 内容
   jq '.statistics' /data/experiments/.runicorn/full_manifest.json
   ```

### 客户端

1. **回退策略**
   - Manifest sync 失败时自动回退到 legacy sync
   - 无需手动干预

2. **性能优化**
   - 使用 jitter 避免同时请求（thundering herd）
   - 监控 manifest 下载时间
   - 检查网络延迟

3. **错误处理**
   ```python
   try:
       stats = client.sync()
       if stats.get("failed_count") > 0:
           logger.warning(f"{stats['failed_count']} files failed to sync")
   except IOError as e:
       logger.error(f"Manifest download failed: {e}")
       # 将自动回退到 legacy sync
   ```

---

## 故障排除

### 问题：Manifest 未生成

**症状**: `.runicorn/` 目录为空或 manifest 文件不存在

**解决方案**:
```bash
# 手动生成测试
runicorn generate-manifest --verbose

# 检查权限
ls -ld /data/experiments/.runicorn

# 检查服务状态（systemd）
systemctl status runicorn-manifest.service
journalctl -u runicorn-manifest.service -n 50
```

### 问题：Manifest 过大

**症状**: Manifest 文件 > 10MB

**原因**: 实验数量过多或文件过多

**解决方案**:
1. 使用 active manifest（减少实验数量）
2. 检查是否有异常大量文件的实验
3. 考虑分区存储

### 问题：客户端回退到 Legacy Sync

**症状**: 日志显示 "falling back to legacy sync"

**可能原因**:
1. Manifest 不存在（服务端未配置）
2. Manifest 格式错误
3. 网络问题
4. 权限问题

**调试**:
```bash
# 检查 manifest 是否存在
sftp user@server
> ls /data/experiments/.runicorn/

# 手动下载测试
scp user@server:/data/experiments/.runicorn/full_manifest.json /tmp/

# 验证 manifest
jq empty /tmp/full_manifest.json && echo "Valid JSON"
```

### 问题：同步速度慢

**可能原因**:
1. 网络延迟高
2. 大量小文件
3. 并发度不足

**优化**:
```python
# 调整并发参数
client.MAX_WORKERS = 5  # 默认 3
client.BATCH_SIZE = 10  # 默认 5

# 减少 jitter（如果网络稳定）
client = ManifestSyncClient(
    ...,
    jitter_max=1.0  # 默认 5.0
)
```

### 问题：Manifest 修订号未增加

**症状**: 多次生成后 revision 保持不变

**原因**: 实验没有变化，这是正常行为

**验证**:
```bash
# 检查修订历史
jq '.revision' /data/experiments/.runicorn/full_manifest.json

# 检查生成时间
jq '.generated_at | todate' /data/experiments/.runicorn/full_manifest.json
```

---

## 性能指标

### 预期性能

| 指标 | Legacy Sync | Manifest Sync | 改进 |
|------|-------------|---------------|------|
| SFTP 操作数（100 实验）| 11,000+ | <200 | **99%** ↓ |
| 同步时间（100 实验）| ~5 分钟 | ~10 秒 | **96%** ↓ |
| 同步时间（500 实验）| ~15 分钟 | ~30 秒 | **97%** ↓ |
| 带宽（追加文件）| 100% | 5-20% | **80-95%** ↓ |

### Manifest 大小

| 实验数 | 文件数 | Manifest (.json) | 压缩后 (.gz) |
|--------|--------|-----------------|-------------|
| 100 | ~1,000 | ~500 KB | ~100 KB |
| 500 | ~5,000 | ~2.5 MB | ~500 KB |
| 1,000 | ~10,000 | ~5 MB | ~1 MB |

---

## 示例代码

### 完整服务端设置

```python
from pathlib import Path
from runicorn.manifest import ManifestGenerator, ManifestType
import schedule
import time

def generate_manifests():
    """定期生成 manifests"""
    generator = ManifestGenerator(
        remote_root=Path("/data/experiments"),
        active_window_seconds=3600,
        incremental=True
    )
    
    try:
        # 生成完整 manifest
        manifest, path = generator.generate(ManifestType.FULL)
        print(f"Generated full manifest: {manifest.total_experiments} experiments")
        
        # 可选：生成活跃 manifest
        manifest, path = generator.generate(ManifestType.ACTIVE)
        print(f"Generated active manifest: {manifest.total_experiments} experiments")
        
    except Exception as e:
        print(f"Error generating manifest: {e}")

# 每 5 分钟生成一次
schedule.every(5).minutes.do(generate_manifests)

# 运行调度器
while True:
    schedule.run_pending()
    time.sleep(60)
```

### 完整客户端设置

```python
import paramiko
from pathlib import Path
from runicorn.remote_storage import MetadataSyncService
from runicorn.remote_storage.cache_manager import LocalCacheManager

# SSH 连接
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("ml-server.example.com", username="mluser", key_filename="~/.ssh/id_rsa")
sftp = ssh.open_sftp()

# 缓存管理器
cache = LocalCacheManager(root_dir=Path("/local/cache"))

# 创建同步服务（manifest sync 自动启用）
service = MetadataSyncService(
    ssh_session=ssh,
    sftp_client=sftp,
    remote_root="/data/experiments",
    cache_manager=cache,
    use_manifest_sync=True,
    manifest_sync_jitter=5.0
)

# 执行同步
print("Starting sync...")
success = service.sync_all()

if success:
    print("Sync completed successfully!")
    print(f"Files synced: {service.progress.synced_files}")
    print(f"Bytes downloaded: {service.progress.synced_bytes / (1024*1024):.2f} MB")
else:
    print("Sync failed!")

# 清理
sftp.close()
ssh.close()
```

---

## 相关文档

- **服务端设置**: [SERVER_SETUP_GUIDE.md](../../future/SERVER_SETUP_GUIDE.md)
- **实现计划**: [MANIFEST_SYNC_IMPLEMENTATION_PLAN.md](../../future/MANIFEST_SYNC_IMPLEMENTATION_PLAN.md)
- **SSH API**: [ssh_api.md](./ssh_api.md)

---

**最后更新**: 2025-10-23  
**状态**: 生产就绪  
**维护者**: Runicorn 开发团队
