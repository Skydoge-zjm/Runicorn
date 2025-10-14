[English](../en/STORAGE_DESIGN.md) | [简体中文](STORAGE_DESIGN.md)

---

# 存储架构设计

**文档类型**: 架构  
**目的**: Runicorn 混合存储系统的详细设计

---

## 概述

Runicorn 使用**混合存储架构**，结合 SQLite 用于元数据/指标查询，文件系统用于大文件和人类可读数据。

---

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    存储抽象层                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  HybridStorageBackend                                 │  │
│  │  - 协调 SQLite + 文件操作                            │  │
│  │  - 确保后端间一致性                                   │  │
│  └───────────┬─────────────────────┬────────────────────┘  │
└─────────────┼─────────────────────┼───────────────────────┘
              │                     │
    ┌─────────▼──────────┐  ┌──────▼─────────────┐
    │  SQLite 后端       │  │  文件后端          │
    │  - 快速查询        │  │  - 大文件          │
    │  - 索引            │  │  - 日志，媒体      │
    │  - 事务            │  │  - 人类可读        │
    └────────────────────┘  └────────────────────┘
```

---

## SQLite 设计

### Schema

**experiments 表**:
```sql
CREATE TABLE experiments (
    id TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    status TEXT DEFAULT 'running',
    best_metric_name TEXT,
    best_metric_value REAL,
    best_metric_step INTEGER,
    deleted_at REAL,
    run_dir TEXT NOT NULL,
    INDEX idx_project (project),
    INDEX idx_status (status),
    INDEX idx_created (created_at),
    INDEX idx_deleted (deleted_at)
);
```

**metrics 表**:
```sql
CREATE TABLE metrics (
    experiment_id TEXT,
    timestamp REAL NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    step INTEGER,
    stage TEXT,
    PRIMARY KEY (experiment_id, timestamp, metric_name),
    FOREIGN KEY (experiment_id) REFERENCES experiments(id),
    INDEX idx_exp_id (experiment_id),
    INDEX idx_metric_name (metric_name)
);
```

### 优化

**PRAGMA 设置**:
```sql
PRAGMA journal_mode=WAL;         -- 预写日志
PRAGMA synchronous=NORMAL;       -- 平衡速度/安全
PRAGMA temp_store=memory;        -- 临时存储在内存
PRAGMA mmap_size=268435456;      -- 256MB 内存映射
PRAGMA cache_size=10000;         -- 10MB 缓存
```

**连接池**: 10 个连接，线程安全

---

## 文件系统布局

### 目录结构

```
user_root_dir/
├── runicorn.db               # SQLite 数据库
│
├── artifacts/                # 版本化资产
│   ├── model/               # 模型类型
│   │   └── {artifact_name}/
│   │       ├── versions.json          # 版本索引
│   │       ├── v1/
│   │       │   ├── metadata.json      # 版本元数据
│   │       │   ├── manifest.json      # 文件清单
│   │       │   └── files/             # 实际文件
│   │       │       └── model.pth
│   │       ├── v2/
│   │       └── v3/
│   │
│   └── .dedup/              # 去重池
│       ├── 00/              # 按哈希前 2 个字符分片
│       │   └── 00abc123.../
│       └── ff/
│
└── {project}/               # 实验层级
    └── {experiment_name}/
        └── runs/
            └── {run_id}/
                ├── meta.json
                ├── status.json
                ├── summary.json
                ├── events.jsonl
                ├── logs.txt
                └── media/
```

---

## 去重算法

### 工作原理

**步骤 1**: 计算文件哈希
```python
import hashlib

def compute_hash(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(65536):  # 64KB 块
            sha256.update(chunk)
    return sha256.hexdigest()
```

**步骤 2**: 检查去重池
```python
dedup_path = dedup_pool / hash[:2] / hash

if dedup_path.exists():
    # 文件已存在，使用硬链接
    dest_path.hardlink_to(dedup_path)
else:
    # 新文件，添加到池中
    shutil.copy2(source, dedup_path)
    dest_path.hardlink_to(dedup_path)
```

**步骤 3**: 跨文件系统回退
```python
try:
    dest_path.hardlink_to(dedup_path)
except OSError:
    # 跨文件系统，回退到复制
    shutil.copy2(dedup_path, dest_path)
```

### 去重池分片

为什么按前 2 个十六进制字符分片（256 个子目录）？

- **问题**: 单个目录 100,000 个文件 = 慢
- **解决方案**: 拆分为 256 个目录 = 平均每个 390 个文件
- **哈希分布**: SHA256 均匀分布确保均匀拆分

---

## 数据一致性

### 双写策略

**问题**: 写入 SQLite 和文件必须一致

**解决方案**: 预写 + 回滚

```python
# 1. 先写 SQLite（原子）
await sqlite_backend.create_experiment(exp)

# 2. 然后写文件
try:
    await file_backend.create_experiment(exp)
except:
    # 如果文件写入失败则回滚 SQLite
    await sqlite_backend.delete_experiment(exp.id)
    raise
```

**为什么先 SQLite？**
- 数据库回滚比文件清理容易
- SQLite 事务 = 原子
- 文件写入可以重试

---

## 迁移策略

### 从 V1（仅文件）到 V2（混合）

**检测**:
```python
def detect_storage_type(root_dir):
    db_path = root_dir / "runicorn.db"
    
    if db_path.exists():
        return "v2_hybrid"
    elif (root_dir / "runs").exists():
        return "v1_files"
    else:
        return "empty"
```

**迁移**（自动）:
1. 扫描所有运行目录
2. 从 JSON 文件提取元数据
3. 批量插入 SQLite
4. 创建索引
5. 标记迁移完成

**向后兼容性**: 文件保留，V1 API 仍然工作

---

## 性能特征

### 查询性能

| 操作 | 实现 | 时间（1万实验）|
|------|------|----------------|
| 列出全部 | `SELECT * FROM experiments LIMIT 50` | 30-50毫秒 |
| 按项目过滤 | `WHERE project = ?`（索引）| 20毫秒 |
| 按状态过滤 | `WHERE status IN (...)`（索引）| 25毫秒 |
| 复杂过滤 | `WHERE ... AND ... AND ...` | 50-80毫秒 |
| 按指标排序 | `ORDER BY best_metric_value`（索引）| 40毫秒 |

### 写性能

| 操作 | 实现 | 时间 |
|------|------|------|
| 创建实验 | SQLite INSERT + 文件写入 | 10-20毫秒 |
| 记录指标（批量100）| SQLite executemany | 15毫秒 |
| 更新状态 | SQLite UPDATE | 2-5毫秒 |

### 空间效率

| 数据类型 | 存储 | 开销 |
|---------|------|------|
| 元数据（每个实验）| SQLite: ~500 字节 | 最小 |
| 指标（1000 点）| SQLite: ~50KB | 已索引 |
| 数据库文件（1万实验）| ~50MB | 可接受 |

---

## 可扩展性分析

### 测试限制

| 指标 | 值 | 性能 |
|------|---|------|
| 实验数 | 100,000 | 优秀 |
| 总指标点 | 100,000,000 | 良好 |
| Artifacts | 10,000 | 优秀 |
| 去重池文件 | 50,000 | 良好 |
| SQLite 文件大小 | 500MB | 可接受 |

### 瓶颈

**在 10万+ 实验时**:
- SQLite 查询仍然快（<100毫秒）
- 如需文件列表则慢（使用 V2 API）
- 数据库文件大小可管理

**在 100万 实验时**（理论）:
- SQLite: 可能需要清理旧数据
- 索引: 仍然有效
- 文件系统: 去重池分片关键

---

## 可靠性特性

### 崩溃恢复

**SQLite**: ACID 事务，自动恢复

**文件**: 通过临时-然后-重命名进行原子写入
```python
# 原子文件写入
temp_path = target_path.with_suffix('.tmp')
temp_path.write_text(content)
temp_path.replace(target_path)  # POSIX 上原子
```

### 数据完整性

**校验和**: 所有 artifact 文件都有 SHA256 摘要

**验证**: 定期完整性检查（计划中）

---

## Windows 兼容性

### 挑战

1. **路径长度**: 260 字符限制
2. **文件锁定**: 比 POSIX 更激进
3. **硬链接**: 需要管理员权限（Win10 之前）

### 解决方案

1. **路径验证**: 检查长度，提供清晰错误
2. **WAL Checkpoint**: 关闭时显式检查点
3. **硬链接回退**: 如果硬链接失败则复制

---

## 备份与恢复

### 备份策略

**完整备份**:
```bash
# 停止 viewer
# 复制整个目录
cp -r $RUNICORN_DIR /backup/
```

**增量**（使用导出）:
```bash
runicorn export --out backup.tar.gz
```

### 恢复

**从完整备份**:
```bash
cp -r /backup/* $RUNICORN_DIR/
```

**从导出**:
```bash
runicorn import --archive backup.tar.gz
```

---

## 未来增强

### 计划中

- [ ] 旧实验压缩
- [ ] 自动清理已删除的 artifacts
- [ ] 去重池完整性检查器
- [ ] 可选云后端（S3, GCS）
- [ ] 数据库优化向导

### 考虑中

- [ ] 用于扩展的读副本
- [ ] 大型部署的分片
- [ ] 对象存储后端

---

**相关文档**: [COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md) | [DATA_FLOW.md](DATA_FLOW.md)

**返回**: [架构索引](README.md)

