# Runicorn v0.6.0 发布说明

> **发布日期**: 2025-01  
> **版本**: v0.6.0  
> **作者**: Runicorn 开发团队

[English](../en/RELEASE_NOTES_v0.6.0.md) | [简体中文](RELEASE_NOTES_v0.6.0.md)

---

## 🚀 重大更新

Runicorn v0.6.0 是一个功能丰富的版本，引入了多项重大改进：

| 功能 | 描述 |
|------|------|
| **新资产系统** | 基于 SHA256 内容寻址存储，自动去重 |
| **增强日志系统** | 控制台捕获、tqdm 智能过滤、MetricLogger 兼容 |
| **路径层级结构** | VSCode 风格的实验树形导航 |
| **内联比较视图** | 在实验列表页直接进行多运行指标对比 |
| **新 SSH 后端** | 多后端回退架构 (OpenSSH → AsyncSSH → Paramiko) |
| **前端改进** | 日志 ANSI 颜色支持、行号、搜索功能 |

---

## ✨ 新功能

### 1. 资产系统

新的资产系统采用现代化的 SHA256 内容寻址存储架构，替代了旧的 artifacts 模块。

#### 核心特性

- **SHA256 去重**: 相同文件只存储一次，节省 50-90% 存储空间
- **工作区快照**: 支持 `.rnignore` 的完整代码库捕获
- **Blob 存储**: 高效的内容寻址存储
- **基于清单的恢复**: 将任何快照恢复到原始状态

#### 快速开始

```python
import runicorn as rn

# 初始化时自动快照代码
run = rn.init(
    path="cv/yolo/experiment",
    snapshot_code=True,  # 自动快照工作区
)

# 或手动快照工作区
from runicorn import snapshot_workspace

snapshot = snapshot_workspace(
    root=Path("./my_project"),
    out_zip=Path("./snapshot.zip"),
)
print(f"捕获了 {snapshot['file_count']} 个文件，{snapshot['total_bytes']} 字节")
```

#### 存储结构

```
<storage_root>/
├── archive/
│   ├── code/           # 代码快照 (SHA256 去重)
│   ├── datasets/       # 数据集归档
│   └── outputs/        # 模型输出
└── runs/<path>/<run_id>/
    ├── assets.json     # 资产清单
    └── code_snapshot.zip
```

#### API 参考

| 函数 | 描述 |
|------|------|
| `snapshot_workspace(root, out_zip)` | 创建工作区 ZIP 快照 |
| `archive_file(path, archive_dir)` | 归档文件并 SHA256 去重 |
| `archive_dir(path, archive_dir)` | 归档目录 |
| `restore_from_manifest(manifest, target)` | 从资产清单恢复 |

---

### 2. 增强日志系统

新的日志系统与现有代码无缝集成 - 无需任何修改。

#### 控制台捕获

自动捕获所有 `print()` 和 logging 输出：

```python
import runicorn as rn

# 启用控制台捕获
run = rn.init(
    path="training/bert",
    capture_console=True,  # 捕获 stdout/stderr
    tqdm_mode="smart",     # 智能 tqdm 过滤
)

# 现有代码无需修改
print("开始训练...")
print(f"Epoch 1: loss={0.5:.4f}, acc={0.85:.2f}")

# 所有输出都会捕获到 logs.txt 并可在 Web UI 中查看
```

#### tqdm 处理模式

| 模式 | 行为 |
|------|------|
| `"smart"` | 只保留进度条最终状态（推荐） |
| `"all"` | 捕获所有进度更新 |
| `"none"` | 禁用 tqdm 捕获 |

#### Python Logging 集成

```python
import logging
import runicorn as rn

run = rn.init(path="experiment", capture_console=True)

# 获取写入 Runicorn 的 logging handler
logger = logging.getLogger(__name__)
logger.addHandler(run.get_logging_handler(level=logging.INFO))

logger.info("这会写入 logs.txt")
logger.warning("警告也会被捕获")
```

#### MetricLogger 兼容层

torchvision MetricLogger 的即插即用替代品：

```python
# 之前 (torchvision)
# from torchvision.references.detection.utils import MetricLogger

# 之后 (Runicorn - 只需改一行 import！)
from runicorn.log_compat.torchvision import MetricLogger

metric_logger = MetricLogger(delimiter="  ")
for data in metric_logger.log_every(dataloader, 10, header="Train"):
    loss = model(data)
    metric_logger.update(loss=loss.item(), lr=optimizer.param_groups[0]['lr'])
    # 指标会自动记录到 Runicorn！
```

**特性**：
- 纯 Python 实现（无需 PyTorch 也能工作）
- 有 PyTorch 时自动加速
- 通过 `run.log()` 自动记录指标
- 支持分布式训练的 `synchronize_between_processes()`

---

### 3. 路径层级结构

用灵活的路径式组织替代固定的 `project/name` 结构。

#### VSCode 风格导航

新的 `PathTreePanel` 提供直观的树形导航：

```
┌─────────────────┬──────────────────────────────────────────┐
│  路径树         │  运行列表                                 │
│  ┌───────────┐  │  ┌────────────────────────────────────┐  │
│  │ 📁 cv     │  │  │ 路径    │ 状态 │ 创建时间 │ ...   │  │
│  │  └ 📁 yolo│  │  ├────────────────────────────────────┤  │
│  │    └ 📁 v1│  │  │ cv/yolo │ ✓    │ 2025...  │       │  │
│  │ 📁 nlp    │  │  │ cv/yolo │ ✓    │ 2025...  │       │  │
│  │  └ 📁 bert│  │  └────────────────────────────────────┘  │
│  └───────────┘  │                                          │
└─────────────────┴──────────────────────────────────────────┘
```

#### SDK 用法

```python
import runicorn as rn

# 灵活的路径结构 - 任意深度
run = rn.init(path="cv/detection/yolo/ablation_lr")
run = rn.init(path="nlp/bert/finetune")
run = rn.init(path="thesis/chapter3/experiment1")

# 可选别名，便于识别
run = rn.init(path="cv/yolo", alias="best-v2")
```

#### 新 API 端点

| 端点 | 描述 |
|------|------|
| `GET /api/paths` | 列出所有路径，可选统计信息 |
| `GET /api/paths/tree` | 获取层级树结构 |
| `GET /api/paths/runs?path=cv/yolo` | 按路径前缀过滤运行 |
| `POST /api/paths/soft-delete` | 按路径批量软删除 |
| `GET /api/paths/export` | 按路径批量导出 |

#### 功能特性

- **运行计数徽章**: 显示每个路径下的运行数量
- **搜索过滤**: 快速查找路径
- **右键菜单**: 批量删除、导出操作
- **键盘导航**: 方向键选择，Enter 确认
- **可折叠面板**: 需要时节省屏幕空间

---

### 4. 内联比较视图

在实验列表页面直接比较多个实验。

#### 使用方法

1. 在实验表格中选择 2 个以上运行
2. 点击「比较」按钮
3. 即时查看并排指标图表

```
┌─────────────────┬──────────────────────────────────────────┐
│  已选运行       │  [← 返回]           共有指标: 3          │
│  ┌───────────┐  ├──────────────────────────────────────────┤
│  │ ● run_1   │  │  ┌─────────────┐  ┌─────────────┐       │
│  │   cv/yolo │  │  │    loss     │  │  accuracy   │       │
│  ├───────────┤  │  └─────────────┘  └─────────────┘       │
│  │ ● run_2   │  │  ┌─────────────┐                        │
│  │   cv/yolo │  │  │   f1_score  │                        │
│  └───────────┘  │  └─────────────┘                        │
└─────────────────┴──────────────────────────────────────────┘
```

#### 功能特性

- **共有指标检测**: 自动显示 2 个以上运行共有的指标
- **颜色编码**: 左侧面板颜色与图表曲线对应
- **ECharts 联动**: 跨图表同步 tooltip 和缩放
- **可见性切换**: 显示/隐藏单个运行或指标
- **自动刷新**: 运行中的实验实时更新

---

### 5. 新 SSH 后端架构

SSH 隧道层的完全重写，提升可靠性和兼容性。

#### 多后端回退链

```
┌─────────────────────────────────────────────────────────────┐
│                     AutoBackend                              │
├─────────────────────────────────────────────────────────────┤
│  连接: 始终使用 Paramiko (SSHConnection)                     │
├─────────────────────────────────────────────────────────────┤
│  隧道回退链:                                                 │
│                                                             │
│  1. OpenSSHTunnel (首选)                                    │
│     └─ 使用系统 OpenSSH 客户端                               │
│     └─ 与 SSH agent 兼容性最好                               │
│     └─ 需要: PATH 中有 ssh, ssh-keyscan                      │
│                    ↓ (如不可用)                              │
│  2. AsyncSSHTunnel                                          │
│     └─ 纯 Python 异步实现                                    │
│     └─ 性能良好                                              │
│                    ↓ (如不可用)                              │
│  3. SSHTunnel (Paramiko)                                    │
│     └─ 最终回退                                              │
│     └─ 始终可用                                              │
└─────────────────────────────────────────────────────────────┘
```

#### 安全特性

- **严格主机密钥检查**: 所有后端都强制主机密钥验证
- **Runicorn 管理的 known_hosts**: 与系统 known_hosts 分离
- **409 确认协议**: UI 提示未知/已更改的主机密钥
- **BatchMode**: 无交互式密码提示（请使用密钥！）

#### 配置

```bash
# 可选: 指定自定义 SSH 路径
export RUNICORN_SSH_PATH=/usr/local/bin/ssh

# 后端自动检测 - 无需配置！
```

---

### 6. 前端改进

#### LogsViewer 增强

日志查看器有了显著改进：

| 功能 | 描述 |
|------|------|
| **ANSI 颜色** | 完整支持彩色终端输出 |
| **行号** | 便于引用和导航 |
| **搜索** | 在日志中查找文本并高亮 |
| **自动滚动** | 实时日志的跟随模式 |
| **虚拟滚动** | 流畅处理 10 万行以上 |

#### ANSI 输出示例

```python
# 彩色输出会被保留！
print("\033[32m✓ 训练完成\033[0m")
print("\033[31m✗ 验证失败\033[0m")
print("\033[33m⚠ 警告: 学习率过高\033[0m")
```

---

## 💥 破坏性变更

### API 变更

| 旧 API | 新 API | 说明 |
|--------|--------|------|
| `project` 参数 | `path` 参数 | 使用路径层级 |
| `name` 参数 | `path` 参数 | 合并为单一路径 |
| `/api/projects` | `/api/paths` | 新端点结构 |
| `/api/projects/{p}/names` | `/api/paths/tree` | 树结构 |

### 模块变更

| 已移除 | 替代 |
|--------|------|
| `artifacts/` 模块 | `assets/` 模块 |
| 旧的 `project/name` 字段 | `path` 字段 |

### SDK 参数变更

```python
# 旧版 (v0.5.x)
run = rn.init(project="cv", name="yolo")

# 新版 (v0.6.0)
run = rn.init(path="cv/yolo")
```

---

## 🐛 Bug 修复

- **修复**: Remote Viewer 中 WebSocket 连接稳定性问题
- **修复**: 长时间指标记录的内存泄漏
- **修复**: tqdm 输出导致日志文件膨胀
- **修复**: SSH 隧道重连问题
- **修复**: 文件操作中的路径遍历漏洞
- **修复**: 并发指标写入的竞态条件

---

## 📚 文档更新

### 新文档

- **[增强日志指南](../../guides/zh/ENHANCED_LOGGING_GUIDE.md)** - 控制台捕获和 MetricLogger
- **[资产指南](../../guides/zh/ASSETS_GUIDE.md)** - 新资产系统使用
- **[SSH 后端架构](../../architecture/zh/SSH_BACKEND_ARCHITECTURE.md)** - 技术细节
- **[路径 API 参考](../../api/zh/paths_api.md)** - 新 API 端点
- **[日志 API 参考](../../api/zh/logging_api.md)** - 日志集成

### 更新文档

- **快速入门指南** - 更新新功能
- **API 索引** - 添加新端点
- **系统概览** - 新模块架构

---

## ⚠️ 已知限制

### 控制台捕获

- 捕获在 `rn.init()` 之后开始 - 早期 print 可能被遗漏
- 某些 C 扩展可能绕过 Python stdout
- 交互式提示 (input()) 可能行为异常

### 路径层级

- 最大路径长度: 200 字符
- 允许字符: `a-z A-Z 0-9 _ - /`
- 路径中不允许 `..`（安全考虑）

### SSH 后端

- OpenSSH 后端需要 PATH 中有 `ssh` 和 `ssh-keyscan`
- OpenSSH 隧道不支持密码认证
- Windows: OpenSSH 可能默认不可用

---

## 🔄 迁移指南

### 从 v0.5.x 升级到 v0.6.0

#### 1. 更新 SDK 调用

```python
# 之前 (v0.5.x)
run = rn.init(project="my_project", name="experiment_1")

# 之后 (v0.6.0)
run = rn.init(path="my_project/experiment_1")
```

#### 2. 启用新功能（可选）

```python
# 添加控制台捕获
run = rn.init(
    path="my_project/experiment",
    capture_console=True,
    tqdm_mode="smart",
)

# 添加代码快照
run = rn.init(
    path="my_project/experiment",
    snapshot_code=True,
)
```

#### 3. 更新 MetricLogger（如使用）

```python
# 更改 import
# from utils import MetricLogger
from runicorn.log_compat.torchvision import MetricLogger

# 其余代码无需修改！
```

#### 4. 数据库迁移

数据库 schema 在首次运行时自动迁移。现有数据会保留：
- `project` + `name` → `path`（用 `/` 连接）
- 所有指标和资产保持不变

---

## 📥 下载

### PyPI

```bash
pip install -U runicorn
```

### 带图像支持

```bash
pip install -U "runicorn[images]"
```

### GitHub Releases

- [v0.6.0 源代码](https://github.com/Skydoge-zjm/runicorn/archive/v0.6.0.tar.gz)
- [Windows 桌面应用](https://github.com/Skydoge-zjm/runicorn/releases/v0.6.0)

---

## 🙏 致谢

感谢所有为 v0.6.0 提供反馈的贡献者和用户！

**主要贡献**：
- 增强日志系统设计参考了 W&B 和 Neptune 的研究
- 路径层级灵感来自 VSCode 文件浏览器
- SSH 后端改进基于社区反馈

---

**作者**: Runicorn 开发团队  
**版本**: v0.6.0  
**发布日期**: 2025-01

**[查看完整 CHANGELOG](../../CHANGELOG_zh.md)** | **[返回文档](../../README_zh.md)**
