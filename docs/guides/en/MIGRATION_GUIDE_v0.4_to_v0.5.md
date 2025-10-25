[English](MIGRATION_GUIDE_v0.4_to_v0.5.md) | [简体中文](../zh/MIGRATION_GUIDE_v0.4_to_v0.5.md)

---

# Runicorn 0.4.x → 0.5.0 Migration Guide

> **Author**: Runicorn Development Team  
> **Version**: v0.5.0  
> **Last Updated**: 2025-10-25  
> **Estimated Time**: 30 minutes

---

## 📋 Overview

Runicorn 0.5.0 introduces the new **Remote Viewer** architecture, replacing the old SSH file sync approach. This is a major upgrade, but remains backward compatible with existing data.

### Major Changes

| Aspect | 0.4.x | 0.5.0 |
|--------|-------|-------|
| **Remote Access** | SSH file sync | Remote Viewer (VSCode Remote-style) |
| **API Endpoints** | `/api/ssh/*` | `/api/remote/*` |
| **Config Format** | `ssh_config.json` | `config.yaml` (new remote section) |
| **Data Format** | Compatible | Fully compatible, no migration needed |

### Migration Features

- ✅ **Backward Compatible**: Existing data needs no modification
- ✅ **Gradual Migration**: Can upgrade first, switch later
- ✅ **Old API Available**: Old API still works in 0.5.0 (removed in 0.6.0)
- ⚠️ **Full Install Required**: Remote server needs full Runicorn, not just SDK

---

## ⚡ Quick Migration (5 minutes)

### Minimal Steps

```bash
# 1. Backup data (recommended)
runicorn export --format zip --output backup_before_v0.5.zip

# 2. Upgrade local Runicorn
pip install -U runicorn

# 3. Verify version
runicorn --version  # Should show: Runicorn 0.5.0

# 4. If using remote, upgrade remote server
ssh user@remote-server "pip install -U runicorn"

# 5. Start viewer
runicorn viewer

# Done! Existing data automatically compatible
```

---

## 📝 Detailed Migration Steps

### Step 1: Preparation

#### 1.1 Backup Data

```bash
# Linux/macOS
tar -czf runicorn_backup_$(date +%Y%m%d).tar.gz ~/RunicornData

# Windows PowerShell
Compress-Archive -Path "$env:USERPROFILE\RunicornData" `
  -DestinationPath "runicorn_backup_$(Get-Date -Format 'yyyyMMdd').zip"

# Or use export
runicorn export --format zip --include-artifacts --output backup.zip
```

#### 1.2 Record Current Config

```bash
runicorn config --show > config_before_upgrade.txt
runicorn --version >> config_before_upgrade.txt
```

#### 1.3 Stop Old Sync Tasks (if any)

If you have auto-sync tasks in 0.4.x:
1. Open Viewer
2. Go to "Remote Storage" or "SSH" page
3. Stop all active sync tasks
4. Wait for current syncs to complete

---

### Step 2: Upgrade Local Environment

```bash
# Upgrade Runicorn
pip install --upgrade runicorn

# Verify upgrade
runicorn --version  # Should show: Runicorn 0.5.0

# Test basic functionality
runicorn config --validate
```

---

### Step 3: Upgrade Remote Servers (if using remote)

```bash
# SSH to remote server
ssh user@gpu-server.com

# On remote server
pip install --upgrade runicorn

# Verify
runicorn --version  # Should show 0.5.0+

# Important: Full Runicorn installation required, not just SDK!
```

---

### Step 4: Migrate Configuration

#### Understanding Config Changes

**Old Config (0.4.x)**: `~/.config/runicorn/ssh_config.json`
```json
{
  "connections": [
    {
      "host": "gpu-server.com",
      "username": "user",
      "private_key_path": "~/.ssh/id_rsa"
    }
  ]
}
```

**New Config (0.5.0)**: `~/.config/runicorn/config.yaml`
```yaml
remote:
  ssh_timeout: 30
  viewer_startup_timeout: 60
  health_check_interval: 30
  max_connections: 5
```

#### Configuration Migration

Remote connections are now configured through UI, not config file (for security). You need to re-add connections in UI:
1. Start Viewer: `runicorn viewer`
2. Open Remote page
3. Manually add SSH connections

---

### Step 5: Use Remote Viewer

#### 5.1 Start Local Viewer

```bash
runicorn viewer
```

#### 5.2 Connect to Remote Server

Via Web UI:
1. Open browser: `http://localhost:23300`
2. Click "Remote" button
3. Click "Add Connection"
4. Fill form:
   - Host: `gpu-server.com`
   - Port: `22`
   - Username: `your-username`
   - Auth: SSH key / Password
5. Click "Connect"

#### 5.3 Select Environment and Start

1. System auto-detects remote Python environments (2-5s)
2. Select environment with Runicorn
3. Click "Start Remote Viewer"
4. Wait 5-10 seconds
5. Auto-opens new browser tab

**Done!** Now you can access remote data in real-time.

---

### Step 6: Verify Migration

```bash
# 1. Local viewer works
runicorn viewer
# Open http://localhost:23300, view local experiments

# 2. Config correct
runicorn config --validate

# 3. Data intact
runicorn export --format json --output test_export.json
```

---

## 🔄 API Migration

### API Endpoint Mapping

| Feature | 0.4.x API | 0.5.0 API | Status |
|---------|-----------|-----------|--------|
| Connect | `POST /api/ssh/connect` | `POST /api/remote/connect` | Old API deprecated |
| Get status | `GET /api/ssh/status` | `GET /api/remote/viewer/status` | Old API deprecated |
| Start sync | `POST /api/ssh/sync` | Removed | No sync needed |
| Query tasks | `GET /api/ssh/tasks` | Removed | No sync tasks |
| List envs | N/A | `GET /api/remote/environments` | New |
| Start viewer | N/A | `POST /api/remote/viewer/start` | New |

### Code Migration Example

#### Old Code (0.4.x)

```python
import requests
import time

# Connect and sync
response = requests.post(
    "http://localhost:23300/api/ssh/connect",
    json={"host": "gpu-server.com", "username": "user", "password": "secret"}
)
connection_id = response.json()["connection_id"]

# Start sync
sync_response = requests.post(
    "http://localhost:23300/api/ssh/sync",
    json={
        "connection_id": connection_id,
        "remote_dir": "/home/user/RunicornData",
        "local_dir": "~/RunicornData"
    }
)
task_id = sync_response.json()["task_id"]

# Poll sync status
while True:
    status = requests.get(
        f"http://localhost:23300/api/ssh/tasks/{task_id}"
    ).json()
    if status["status"] in ["completed", "failed"]:
        break
    time.sleep(5)

print("Sync complete")
```

#### New Code (0.5.0)

```python
import requests

# Connect
response = requests.post(
    "http://localhost:23300/api/remote/connect",
    json={
        "host": "gpu-server.com",
        "port": 22,
        "username": "user",
        "auth_method": "password",
        "password": "secret"
    }
)
connection_id = response.json()["connection_id"]

# List environments
envs = requests.get(
    "http://localhost:23300/api/remote/environments",
    params={"connection_id": connection_id}
).json()

# Select first compatible environment
compatible_env = next(e for e in envs if e["is_compatible"])

# Start Remote Viewer
viewer = requests.post(
    "http://localhost:23300/api/remote/viewer/start",
    json={
        "connection_id": connection_id,
        "env_name": compatible_env["name"]
    }
).json()

print(f"Remote Viewer started: {viewer['viewer_url']}")
print("Access directly, no sync wait needed!")
```

**Key Differences**:
- ✅ No sync step needed
- ✅ Instant access (5-10s vs minutes)
- ✅ Real-time data (no delay)
- ✅ Saves local storage

---

## 🐛 Common Issues and Solutions

### Issue 1: Viewer Won't Start After Upgrade

```bash
# Check if port is occupied
lsof -i :23300  # Linux/macOS
netstat -ano | findstr :23300  # Windows

# Try different port
runicorn viewer --port 23301

# Validate config
runicorn config --validate

# Reset config
runicorn config --reset
```

---

### Issue 2: Remote Connection Fails

```bash
# Test SSH connection
ssh user@remote-server

# Check remote Runicorn version
ssh user@remote-server "runicorn --version"  # Must be 0.5.0+

# If wrong version, upgrade
ssh user@remote-server "pip install -U runicorn"

# View detailed errors
runicorn viewer --log-level DEBUG
```

---

### Issue 3: No Compatible Remote Environments Found

```bash
# On remote server
# List all Python environments
conda env list  # If using conda
ls ~/venv/  # If using virtualenv

# Install Runicorn in each environment
conda activate your-env
pip install runicorn

# Verify
runicorn --version
```

---

### Issue 4: Data Loss Concerns

**Answer**: Data won't be lost!

- ✅ All existing data 100% compatible
- ✅ Upgrade doesn't modify or delete any data
- ✅ Can rollback to 0.4.x anytime

**Verify data integrity**:
```bash
runicorn export --format json --output check.json

# Check experiment count
python -c "
import json
with open('check.json') as f:
    data = json.load(f)
    print(f'Total experiments: {len(data.get(\"experiments\", []))}')
"
```

---

### Issue 5: Will Old API Scripts Still Work?

**Answer**: Still works in 0.5.0, but deprecated.

**Timeline**:
- **0.5.0**: Old API works but marked deprecated
- **0.5.x**: Deprecation warnings shown
- **0.6.0**: Old API will be removed

**Recommendation**: Migrate to new API ASAP.

---

## 📊 Performance Improvements

### Remote Access Performance Comparison

| Operation | 0.4.x (SSH Sync) | 0.5.0 (Remote Viewer) | Improvement |
|-----------|-----------------|---------------------|-------------|
| **Initial connect** | 5-60 minutes | 5-10 seconds | **360x faster** |
| **View new experiment** | Need re-sync | Instant | **Real-time** |
| **Local storage** | Copy (GB) | Zero | **100% saved** |
| **Real-time** | 5-10 min delay | Fully real-time | **Zero delay** |
| **Multi-user** | Conflicts | No conflicts | **More reliable** |

---

## 🔙 Rollback Plan

If you need to rollback to 0.4.x:

```bash
# 1. Uninstall 0.5.0
pip uninstall runicorn

# 2. Install 0.4.x
pip install runicorn==0.4.1

# 3. Verify
runicorn --version
```

**Note**: 
- Data created in 0.5.0 still accessible in 0.4.x
- Remote Viewer connections won't migrate back
- Keep backup recommended

---

## ✅ Migration Checklist

Before completing migration, ensure:

- [ ] All data backed up
- [ ] Local Runicorn upgraded to 0.5.0
- [ ] Remote server (if used) upgraded to 0.5.0
- [ ] Config validated (`runicorn config --validate`)
- [ ] Local Viewer starts normally
- [ ] Remote connection tested (if used)
- [ ] Can view existing experiments
- [ ] Can create new experiments
- [ ] API scripts updated (if any)
- [ ] Team members notified

---

## 🆘 Getting Help

Need help?

**Documentation**:
- 📖 [Full Documentation](../../README.md)
- ❓ [FAQ](../../reference/en/FAQ.md)
- 🔧 [Troubleshooting](../../reference/en/TROUBLESHOOTING.md)

**Community**:
- 💬 [GitHub Issues](https://github.com/yourusername/runicorn/issues)
- 📧 Email: support@runicorn.dev

**When reporting issues, include**:
```bash
runicorn --version > diagnostics.txt
runicorn config --show >> diagnostics.txt
python --version >> diagnostics.txt
```

---

## 🎉 Migration Complete

Congratulations! You've successfully migrated to Runicorn 0.5.0.

**Enjoy new features**:
- 🌐 Remote Viewer (VSCode Remote-style)
- ⚡ Instant remote access
- 💾 Zero local storage usage
- 🔄 Fully real-time data
- 🎯 Better user experience

**Feedback**: Welcome to share your migration experience and suggestions!

---

**Author**: Runicorn Development Team  
**Version**: v0.5.0  
**Last Updated**: 2025-10-25

---

**Back to**: [User Guides](README.md) | [Main Docs](../../README.md)


