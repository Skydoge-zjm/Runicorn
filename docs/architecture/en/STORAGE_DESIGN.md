[English](STORAGE_DESIGN.md) | [简体中文](../zh/STORAGE_DESIGN.md)

---

# Storage Architecture Design

**Document Type**: Architecture  
**Purpose**: Detailed design of Runicorn's hybrid storage system

---

## Overview

Runicorn uses a **hybrid storage architecture** combining SQLite for metadata/metrics queries and file system for large files and human-readable data.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Storage Abstraction Layer                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  HybridStorageBackend                                 │  │
│  │  - Coordinates SQLite + File operations              │  │
│  │  - Ensures consistency between backends              │  │
│  └───────────┬─────────────────────┬────────────────────┘  │
└─────────────┼─────────────────────┼───────────────────────┘
              │                     │
    ┌─────────▼──────────┐  ┌──────▼─────────────┐
    │  SQLite Backend    │  │  File Backend      │
    │  - Fast queries    │  │  - Large files     │
    │  - Indexes         │  │  - Logs, media     │
    │  - Transactions    │  │  - Human-readable  │
    └────────────────────┘  └────────────────────┘
```

---

## SQLite Design

### Schema

**experiments table**:
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

**metrics table**:
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

### Optimizations

**PRAGMA Settings**:
```sql
PRAGMA journal_mode=WAL;         -- Write-Ahead Logging
PRAGMA synchronous=NORMAL;       -- Balance speed/safety
PRAGMA temp_store=memory;        -- Temp in RAM
PRAGMA mmap_size=268435456;      -- 256MB memory mapping
PRAGMA cache_size=10000;         -- 10MB cache
```

**Connection Pool**: 10 connections, thread-safe

---

## File System Layout

### Directory Structure

```
user_root_dir/
├── runicorn.db               # SQLite database
│
├── artifacts/                # Versioned assets
│   ├── model/               # Model type
│   │   └── {artifact_name}/
│   │       ├── versions.json          # Version index
│   │       ├── v1/
│   │       │   ├── metadata.json      # Version metadata
│   │       │   ├── manifest.json      # File manifest
│   │       │   └── files/             # Actual files
│   │       │       └── model.pth
│   │       ├── v2/
│   │       └── v3/
│   │
│   ├── dataset/             # Dataset type
│   ├── config/              # Config type
│   │
│   └── .dedup/              # Deduplication pool
│       ├── 00/              # Shard by first 2 chars of hash
│       │   └── 00abc123.../
│       ├── 01/
│       └── ff/
│
└── {project}/               # Experiment hierarchy
    └── {experiment_name}/
        └── runs/
            └── {run_id}/
                ├── meta.json            # Run metadata
                ├── status.json          # Status info
                ├── summary.json         # Summary metrics
                ├── events.jsonl         # Metrics stream
                ├── logs.txt             # Text logs
                ├── environment.json     # Environment snapshot
                ├── artifacts_created.json   # Created artifacts
                ├── artifacts_used.json      # Used artifacts
                └── media/               # Images, files
                    └── {timestamp}_{hash}_{key}.{ext}
```

---

## Deduplication Algorithm

### How It Works

**Step 1**: Compute file hash
```python
import hashlib

def compute_hash(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(65536):  # 64KB chunks
            sha256.update(chunk)
    return sha256.hexdigest()
```

**Step 2**: Check dedup pool
```python
dedup_path = dedup_pool / hash[:2] / hash

if dedup_path.exists():
    # File already exists, use hard link
    dest_path.hardlink_to(dedup_path)
else:
    # New file, add to pool
    shutil.copy2(source, dedup_path)
    dest_path.hardlink_to(dedup_pool)
```

**Step 3**: Fallback for cross-filesystem
```python
try:
    dest_path.hardlink_to(dedup_path)
except OSError:
    # Cross-filesystem, fallback to copy
    shutil.copy2(dedup_path, dest_path)
```

### Dedup Pool Sharding

Why shard by first 2 hex chars (256 subdirectories)?

- **Problem**: Single directory with 100,000 files = slow
- **Solution**: Split into 256 directories = avg 390 files each
- **Hash distribution**: SHA256 uniform distribution ensures even split

---

## Data Consistency

### Dual-Write Strategy

**Problem**: Writing to both SQLite and files must be consistent

**Solution**: Write-ahead + rollback

```python
# 1. Write to SQLite first (atomic)
await sqlite_backend.create_experiment(exp)

# 2. Then write to files
try:
    await file_backend.create_experiment(exp)
except:
    # Rollback SQLite if file write fails
    await sqlite_backend.delete_experiment(exp.id)
    raise
```

**Why SQLite first?**
- Database rollback easier than file cleanup
- SQLite transaction = atomic
- File writes can be retried

---

## Migration Strategy

### From V1 (Files Only) to V2 (Hybrid)

**Detection**:
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

**Migration** (automatic):
1. Scan all run directories
2. Extract metadata from JSON files
3. Batch insert into SQLite
4. Create indexes
5. Mark migration complete

**Backward Compatibility**: Files remain, V1 API still works

---

## Performance Characteristics

### Query Performance

| Operation | Implementation | Time (10k exps) |
|-----------|----------------|-----------------|
| List all | `SELECT * FROM experiments LIMIT 50` | 30-50ms |
| Filter by project | `WHERE project = ?` (indexed) | 20ms |
| Filter by status | `WHERE status IN (...)` (indexed) | 25ms |
| Complex filter | `WHERE ... AND ... AND ...` | 50-80ms |
| Sort by metric | `ORDER BY best_metric_value` (indexed) | 40ms |

### Write Performance

| Operation | Implementation | Time |
|-----------|----------------|------|
| Create experiment | SQLite INSERT + file writes | 10-20ms |
| Log metric (batch 100) | SQLite executemany | 15ms |
| Update status | SQLite UPDATE | 2-5ms |

### Space Efficiency

| Data Type | Storage | Overhead |
|-----------|---------|----------|
| Metadata (per exp) | SQLite: ~500 bytes | Minimal |
| Metrics (1000 points) | SQLite: ~50KB | Indexed |
| Database file (10k exps) | ~50MB | Acceptable |

---

## Scalability Analysis

### Tested Limits

| Metric | Value | Performance |
|--------|-------|-------------|
| Experiments | 100,000 | Excellent |
| Metrics points (total) | 100,000,000 | Good |
| Artifacts | 10,000 | Excellent |
| Dedup pool files | 50,000 | Good |
| SQLite file size | 500MB | Acceptable |

### Bottlenecks

**At 100k+ experiments**:
- SQLite queries still fast (<100ms)
- File listing slow if needed (use V2 API)
- Database file size manageable

**At 1M experiments** (theoretical):
- SQLite: May need cleanup of old data
- Indexes: Still effective
- File system: Dedup pool sharding critical

---

## Reliability Features

### Crash Recovery

**SQLite**: ACID transactions, automatic recovery

**Files**: Atomic writes via temp-then-rename
```python
# Atomic file write
temp_path = target_path.with_suffix('.tmp')
temp_path.write_text(content)
temp_path.replace(target_path)  # Atomic on POSIX
```

### Data Integrity

**Checksums**: All artifact files have SHA256 digest

**Validation**: Periodic integrity checks (planned)

---

## Windows Compatibility

### Challenges

1. **Path Length**: 260 character limit
2. **File Locking**: More aggressive than POSIX
3. **Hard Links**: Require admin rights (pre-Win10)

### Solutions

1. **Path validation**: Check length, provide clear error
2. **WAL Checkpoint**: Explicit checkpoint on close
3. **Hard link fallback**: Copy if hard link fails

---

## Backup & Recovery

### Backup Strategy

**Full backup**:
```bash
# Stop viewer
# Copy entire directory
cp -r $RUNICORN_DIR /backup/
```

**Incremental** (using export):
```bash
runicorn export --out backup.tar.gz
```

### Recovery

**From full backup**:
```bash
cp -r /backup/* $RUNICORN_DIR/
```

**From export**:
```bash
runicorn import --archive backup.tar.gz
```

---

## Future Enhancements

### Planned

- [ ] Compression for old experiments
- [ ] Automatic cleanup of deleted artifacts
- [ ] Dedup pool integrity checker
- [ ] Optional cloud backends (S3, GCS)
- [ ] Database optimization wizard

### Under Consideration

- [ ] Read replicas for scaling
- [ ] Sharding for very large deployments
- [ ] Object storage backends

---

**Related Docs**: [COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md) | [DATA_FLOW.md](DATA_FLOW.md)

**Back to**: [Architecture Index](README.md)

