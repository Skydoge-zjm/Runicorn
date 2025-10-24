[English](manifest_api.md) | [简体中文](../zh/manifest_api.md)

---

# Manifest API Documentation

**Version**: v0.4.0  
**Module**: Manifest-Based Sync  
**Status**: ✅ Production Ready

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [CLI Commands](#cli-commands)
3. [Python SDK](#python-sdk)
4. [Manifest Format Specification](#manifest-format-specification)
5. [Server Configuration](#server-configuration)
6. [Client Configuration](#client-configuration)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Overview

Manifest-Based Sync is Runicorn's high-performance synchronization system that achieves:

- **99% Network Reduction** (11,000+ → <200 SFTP operations)
- **95% Faster Sync** (10 minutes → <30 seconds)
- **Sub-linear Scalability** supporting 1000+ experiments
- **Automatic Fallback** to legacy sync if manifest unavailable

### System Architecture

```
Server Side                       Client Side
-----------                       -----------
ManifestGenerator                 ManifestSyncClient
    ↓                                 ↓
Generate manifest.json        →   Download manifest
(every 5 min)                     Parse & validate
                                      ↓
Save to .runicorn/            ←   Compute diff
                                      ↓
                                  Sync changed files
                                  (concurrent + incremental)
```

---

## CLI Commands

### `runicorn generate-manifest`

Generate sync manifest on the server side.

#### Basic Usage

```bash
# Generate full manifest (all experiments)
runicorn generate-manifest

# Generate active manifest (last hour)
runicorn generate-manifest --active

# Specify experiments root directory
runicorn generate-manifest --root /data/experiments

# Custom output path
runicorn generate-manifest --output /tmp/manifest.json

# Verbose logging
runicorn generate-manifest --verbose
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--root` | Path | `.` | Experiments root directory |
| `--output` | Path | `<root>/.runicorn/<type>_manifest.json` | Custom output path |
| `--active` | Flag | - | Generate active manifest (recent only) |
| `--full` | Flag | ✅ | Generate full manifest (default) |
| `--active-window` | Int | `3600` | Active window time (seconds) |
| `--no-incremental` | Flag | - | Disable incremental optimization |
| `--verbose` | Flag | - | Enable debug logging |

#### Example Output

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

---

## Python SDK

### Server-Side: ManifestGenerator

#### Basic Usage

```python
from pathlib import Path
from runicorn.manifest import ManifestGenerator, ManifestType

# Create generator
generator = ManifestGenerator(
    remote_root=Path("/data/experiments"),
    output_dir=None,  # Default: {remote_root}/.runicorn
    active_window_seconds=3600,  # 1 hour
    incremental=True
)

# Generate full manifest
manifest, output_path = generator.generate(
    manifest_type=ManifestType.FULL
)

print(f"Generated manifest with {manifest.total_experiments} experiments")
print(f"Output: {output_path}")
```

### Client-Side: ManifestSyncClient

#### Basic Usage

```python
from pathlib import Path
import paramiko
from runicorn.remote_storage.manifest_sync import ManifestSyncClient

# Create SFTP client
ssh = paramiko.SSHClient()
ssh.connect("server.example.com", username="user", key_filename="~/.ssh/id_rsa")
sftp = ssh.open_sftp()

# Create sync client
client = ManifestSyncClient(
    sftp_client=sftp,
    remote_root="/data/experiments",
    cache_dir=Path("/local/cache"),
    jitter_max=5.0  # Random 0-5s delay
)

# Perform sync with progress callback
def progress_callback(completed, total, current_file):
    percent = (completed / total) * 100
    print(f"[{completed}/{total}] ({percent:.1f}%) {current_file}")

stats = client.sync(progress_callback=progress_callback)

# Check results
if stats.get("skipped"):
    print(f"Sync skipped: {stats['reason']}")
else:
    print(f"Synced {stats['files_synced']} files")
    print(f"Downloaded {stats['bytes_downloaded'] / (1024*1024):.2f} MB")
```

### Integration with MetadataSyncService

Manifest sync is automatically integrated:

```python
from runicorn.remote_storage import MetadataSyncService

# Create service (manifest sync enabled by default)
service = MetadataSyncService(
    ssh_session=ssh_client,
    sftp_client=sftp,
    remote_root="/data/experiments",
    cache_manager=cache,
    use_manifest_sync=True,      # Default: True
    manifest_sync_jitter=5.0      # Default: 5.0 seconds
)

# Sync - automatically tries manifest, falls back to legacy
success = service.sync_all()
```

---

## Manifest Format Specification

### Manifest Structure

```json
{
  "format_version": "1.0",
  "manifest_type": "full",  // or "active"
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
          "priority": 1
        }
      ]
    }
  ],
  "statistics": {
    "total_experiments": 156,
    "total_files": 2340,
    "total_bytes": 1234567890
  }
}
```

---

## Server Configuration

### Automated Generation

#### Systemd (Linux, Recommended)

**Timer** (`/etc/systemd/system/runicorn-manifest.timer`):

```ini
[Unit]
Description=Runicorn Manifest Generation Timer

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
```

**Service** (`/etc/systemd/system/runicorn-manifest.service`):

```ini
[Unit]
Description=Runicorn Manifest Generation

[Service]
Type=oneshot
User=mluser
ExecStart=/usr/local/bin/runicorn generate-manifest --full --root /data/experiments
```

**Enable**:

```bash
sudo systemctl enable runicorn-manifest.timer
sudo systemctl start runicorn-manifest.timer
```

---

## Best Practices

### Server-Side

1. **Generation Frequency**
   - Small labs (<100 experiments): Every 5 minutes
   - Medium labs (100-500): Every 10 minutes
   - Large labs (>500): Every 15 minutes

2. **Monitoring**
   ```bash
   # Check manifest freshness
   ls -lh /data/experiments/.runicorn/*.json
   
   # View statistics
   jq '.statistics' /data/experiments/.runicorn/full_manifest.json
   ```

---

## Troubleshooting

### Issue: Manifest Not Generated

**Solution**:
```bash
# Test manually
runicorn generate-manifest --verbose

# Check permissions
ls -ld /data/experiments/.runicorn

# Check service status
systemctl status runicorn-manifest.service
```

### Issue: Client Falls Back to Legacy

**Possible Causes**:
1. Manifest doesn't exist
2. Network issues
3. Permission problems

**Debug**:
```bash
# Check manifest exists
sftp user@server
> ls /data/experiments/.runicorn/
```

---

## Performance Metrics

### Expected Performance

| Metric | Legacy Sync | Manifest Sync | Improvement |
|--------|-------------|---------------|-------------|
| SFTP ops (100 exps) | 11,000+ | <200 | **99%** ↓ |
| Sync time (100 exps) | ~5 min | ~10 sec | **96%** ↓ |
| Bandwidth (append) | 100% | 5-20% | **80-95%** ↓ |

---

## Related Documentation

- **Server Setup**: [SERVER_SETUP_GUIDE.md](../../future/SERVER_SETUP_GUIDE.md)
- **Implementation Plan**: [MANIFEST_SYNC_IMPLEMENTATION_PLAN.md](../../future/MANIFEST_SYNC_IMPLEMENTATION_PLAN.md)
- **SSH API**: [ssh_api.md](./ssh_api.md)

---

**Last Updated**: 2025-10-23  
**Status**: Production Ready  
**Maintainers**: Runicorn Development Team
