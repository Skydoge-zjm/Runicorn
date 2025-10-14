[English](REMOTE_STORAGE_USER_GUIDE.md) | [简体中文](../zh/REMOTE_STORAGE_USER_GUIDE.md)

---

# Runicorn Remote Storage User Guide

## 📖 Quick Start (5 minutes)

### What is Remote Storage Mode?

Remote storage mode allows you to **view and manage Artifacts on remote servers locally without syncing all files**.

**Comparison**:
- ❌ Old way: Sync 340GB to local (8 hours)
- ✅ New way: Sync 200MB metadata (5 minutes)

---

## 🚀 Usage Steps

### Step 1: Open Remote Storage Configuration

1. Start Runicorn Viewer
   ```bash
   runicorn viewer
   ```

2. Open in browser: `http://localhost:23300`

3. Click **"Remote Storage"** (🌩️ icon) in top menu

### Step 2: Configure SSH Connection

Fill in the following information:

**Required**:
- **Server Address**: e.g., `gpu-server.lab.edu` or `192.168.1.100`
- **Username**: SSH login username
- **Remote Directory**: Runicorn data storage path, e.g., `/home/user/runicorn_data`

**Authentication Method** (choose one):
- **SSH Key** (recommended):
  - Click "Choose Private Key File" to upload `~/.ssh/id_rsa`
  - Or paste private key content directly
  - If encrypted, fill in "Key Passphrase"
  
- **Password Authentication**:
  - Select "Password" radio button
  - Enter SSH password
  
- **SSH Agent**:
  - If SSH Agent already configured, select this option

**Optional Settings**:
- **Auto Sync**: Periodically sync metadata (recommended)
- **Sync Interval**: Default 10 minutes

### Step 3: Connect and Sync

1. Click **"Connect and Sync Metadata"** button

2. Wait for connection (usually 2-3 seconds)

3. Observe sync progress:
   ```
   Metadata Sync Progress
   [████████████░░░░] 75%
   (150/200 files)
   Current: artifacts/model/resnet50/metadata.json
   ```

4. Wait ~5 minutes to complete
   ```
   ✅ Metadata sync complete!
   ```

5. Header shows **"Remote 🌩️"** badge

### Step 4: Browse Remote Artifacts

1. Click **"Artifacts"** in top menu

2. See all remote artifacts list (instant loading)
   - Loaded from local cache
   - Same speed as local mode

3. Click any artifact to view details
   - Metadata, file list, version history
   - Everything from cache, super fast!

### Step 5: Download Files (On Demand)

1. On Artifact details page, click **"Download to Local (8.00 GB)"** button

2. Download progress window appears:
   ```
   📥 Downloading Artifact: resnet50:v3
   [████████████░░░░] 75%
   Files: 1 / 1
   Size: 6.00 GB / 8.00 GB
   ```

3. Wait for download (depending on network speed, e.g., 10 minutes)

4. Upon completion:
   ```
   ✅ Download Complete!
   Files saved to: /home/user/.runicorn_remote_cache/.../resnet50/v3
   ```

5. Click **"View Download Location"** to open folder

### Step 6: Manage Remote Artifacts

**Delete old version**:
1. On Artifact details page click **"Delete Version"**
2. Confirmation dialog (prompts: will execute on remote server)
3. Completes in 2 seconds
4. ✅ "Soft deleted resnet50:v1 on remote server"

**Set alias** (via API):
```bash
curl -X POST http://localhost:23300/api/remote/artifacts/resnet50/v3/alias \
  -H "Content-Type: application/json" \
  -d '{"alias": "production"}'
```

---

## 🌩️ Header Status Indicator

### View Detailed Status

Click **"Remote 🌩️"** badge in Header to see details:

```
Remote Storage Status
├─ Connection: ✅ Connected
├─ Last Sync: 2 minutes ago
├─ Cached Artifacts: 50
└─ Cache Size: 180 MB

[Sync Now] [Disconnect]
```

### Quick Actions

- **Sync Now**: Manually trigger metadata sync
- **Disconnect**: Disconnect remote, switch to local mode

---

## 🔧 Advanced Features

### Switch Storage Mode

**Via API**:
```bash
# Switch to remote mode
curl -X POST http://localhost:23300/api/remote/mode/switch \
  -H "Content-Type: application/json" \
  -d '{"mode": "remote"}'

# Switch to local mode
curl -X POST http://localhost:23300/api/remote/mode/switch \
  -H "Content-Type: application/json" \
  -d '{"mode": "local"}'
```

### Cache Management

**Clear cache**:
```bash
curl -X POST http://localhost:23300/api/remote/cache/clear
```

**LRU cleanup** (remove old files):
```bash
curl -X POST http://localhost:23300/api/remote/cache/cleanup
```

### View Download Tasks

```bash
# List all download tasks
curl http://localhost:23300/api/remote/downloads

# Query specific task progress
curl http://localhost:23300/api/remote/download/{task_id}/status

# Cancel download
curl -X DELETE http://localhost:23300/api/remote/download/{task_id}
```

---

## 💡 Tips

### Tip 1: Disconnect After First Sync

After initial sync completes, you can disconnect:
- Cached metadata remains
- Can browse artifacts (from cache)
- Reconnect when need to download or manage

**Benefit**: Saves SSH connection resources

### Tip 2: On-Demand Download Strategy

Don't download all artifacts, only what you need:
- Browsing: View from cache (no download)
- Need files: Click download (explicit action)
- Savings: Bandwidth, time, local space

### Tip 3: Use Auto-Sync

Enable auto-sync (default 10 minutes):
- Automatically fetch latest metadata
- No manual syncing needed
- Always see latest state

### Tip 4: Multi-Server Management

Can connect to different servers:
- Each server has independent cache directory
- Switch servers by reconnecting
- Cache directory format: `.runicorn_remote_cache/{host}_{user}`

---

## ❓ FAQ

### Q1: How much data needs to be synced?

**A**: Only metadata files (JSON), **not** large files:
- Synced: `metadata.json`, `manifest.json`, `versions.json`, etc.
- Skipped: Model files (.pth, .h5), datasets, images

**Typical size**: 200MB metadata vs 340GB all data

### Q2: How long does sync take?

**A**: Depends on number of artifacts and network speed:
- Small project (10 artifacts): ~30 seconds
- Medium project (50 artifacts): ~2 minutes
- Large project (200 artifacts): ~5 minutes

### Q3: Where are downloaded files saved?

**A**: Default location:
```
~/.runicorn_remote_cache/{host}_{user}/downloads/{artifact_name}/v{version}/
```

Path shown after download completes.

### Q4: Can I download multiple artifacts simultaneously?

**A**: Yes! Download tasks run in background:
- Start download artifact A
- Minimize progress window
- Start download artifact B
- View all tasks via API: `GET /api/remote/downloads`

### Q5: Where are delete operations executed?

**A**: 
- **Remote mode**: Deletion executes on **server**
- **Local mode**: Deletion executes **locally**

Prompt messages clearly indicate operation location.

### Q6: Does cache persist after disconnect?

**A**: Yes!
- After disconnect, metadata cache remains
- Can browse artifacts (from cache)
- But cannot download or manage (need connection)

### Q7: How to switch back to local mode?

**A**: Two ways:
1. Click Header "Remote" badge → Click "Disconnect"
2. Close and restart Viewer (auto uses local mode)

---

## 🔒 Security Recommendations

### Recommended Authentication

1. **SSH Key** (most recommended)
   ```bash
   # Generate key pair locally
   ssh-keygen -t rsa -b 4096
   
   # Copy public key to server
   ssh-copy-id user@server.edu
   
   # Use private key in Runicorn
   ```

2. **SSH Agent** (convenient)
   ```bash
   # Start SSH Agent
   eval "$(ssh-agent -s)"
   
   # Add key
   ssh-add ~/.ssh/id_rsa
   
   # Runicorn uses automatically
   ```

3. **Password** (not recommended, testing only)

### Private Key Security

- ✅ Private key only in memory, not saved to disk
- ✅ Auto-cleared when Viewer closes
- ✅ Uses standard SSH encryption protocol
- ❌ Don't paste private keys on public computers

---

## 🐛 Troubleshooting

### Issue: Connection Failed

**Symptom**: "Connection failed: timeout"

**Troubleshoot**:
1. Check server address and port are correct
2. Test network connectivity: `ping gpu-server.edu`
3. Test SSH connection: `ssh user@server.edu`
4. Check firewall settings

### Issue: Sync Failed

**Symptom**: "Sync failed: permission denied"

**Troubleshoot**:
1. Check remote directory path is correct
2. Verify directory permissions: `ls -ld /home/user/runicorn_data`
3. Ensure SSH key has read permissions
4. Check server has Python 3.8+

### Issue: Download Failed

**Symptom**: "Download failed: checksum mismatch"

**Troubleshoot**:
1. Re-sync metadata: Click "Sync Now"
2. Clear cache: `POST /api/remote/cache/clear`
3. Check network stability
4. View error details: Shown in download progress window

### Issue: Cannot View Artifacts

**Symptom**: Artifacts list empty in remote mode

**Troubleshoot**:
1. Confirm connected: Header shows "Remote 🌩️"
2. Check sync completed: View sync progress
3. Verify remote directory structure: 
   ```bash
   # Check on server
   ls -la /home/user/runicorn_data/artifacts/
   ```
4. View error logs: Browser console (F12)

---

## 📊 Performance Reference

### Initialization Time (Metadata Sync)

| Artifacts Count | Metadata Size | Est. Time | 100Mbps Network |
|----------------|---------------|-----------|-----------------|
| 10 | ~10MB | 30 seconds | ✅ Very fast |
| 50 | ~50MB | 2 minutes | ✅ Fast |
| 200 | ~200MB | 5 minutes | ✅ Acceptable |
| 1000 | ~1GB | 20 minutes | ⚠️ Be patient |

### Download Time (Actual Files)

| File Size | 10Mbps | 100Mbps | 1Gbps |
|-----------|--------|---------|-------|
| 100MB | 80 sec | 8 sec | <1 sec |
| 1GB | 13 min | 80 sec | 8 sec |
| 8GB | 1.7 hours | 10 min | 1 min |
| 50GB | 11 hours | 1.1 hours | 6 min |

---

## 💡 Best Practices

### Practice 1: Reasonable Sync Interval

- **Frequent training** (hourly experiments): 5-10 minutes
- **Occasional training** (few experiments per day): 30-60 minutes
- **View only** (not training): Disable auto-sync

### Practice 2: Selective Downloads

Don't download all artifacts, only what you need:
- ✅ Models you need to use
- ✅ Data you need to analyze
- ❌ Deprecated old versions
- ❌ Reference-only backups

### Practice 3: Regular Cache Cleanup

Cache auto-cleans via LRU, but can also manually:
- Clean old downloads: `POST /api/remote/cache/cleanup`
- Complete clear: `POST /api/remote/cache/clear`

### Practice 4: Use Alias Management

Set aliases for important versions:
```bash
# Set production version
curl -X POST .../artifacts/resnet50/v10/alias \
  -d '{"alias": "production"}'

# Next time use
run.use_artifact("resnet50:production")
```

---

## 📱 UI Feature Description

### Remote Configuration Page

**Location**: Menu → Remote Storage

**Features**:
- ⚙️ Configure SSH connection
- 🔌 Connect/disconnect server
- 🔄 Manually sync metadata
- 📊 View sync progress
- ℹ️ Feature description and help

### Status Indicator

**Location**: Header right side

**Display**:
- Local mode: `[Local]` (gray badge)
- Remote mode: `[Remote 🌩️]` (green badge)
- Syncing: `[Remote 🌩️ 🔄]` (blue animation)

**Click to**:
- View detailed status
- Quick sync actions
- Quick disconnect

### Artifacts Page

**Remote mode features**:
- List shows remote artifacts
- Click to view details (from cache, instant)
- File list marked `is_remote: true`
- Download button replaces "Open Folder"

### Download Progress Modal

**Shows**:
- 📊 Real-time progress bar
- 📁 File count statistics
- 💾 Byte count statistics
- ⏱️ Estimated remaining size
- 📍 Download save location
- ⚠️ Error messages (if any)

**Actions**:
- ⏹️ Cancel download
- 📁 View download location
- ➖ Minimize window

---

## 🔄 Workflow Examples

### Scenario 1: View Training Results

```
Goal: View today's trained model performance

Steps:
1. Open Runicorn Viewer
2. Header shows "Remote 🌩️" (auto-synced)
3. Click "Artifacts" → See all models
4. Click "resnet50" → View details
5. View metadata: {"accuracy": 0.95, "loss": 0.05}
6. View version history: v1, v2, v3 (latest)
7. View lineage graph: Understand dependencies

Time: <1 minute (all from cache)
Download: 0 bytes
```

### Scenario 2: Download Model for Inference

```
Goal: Download latest model locally for inference

Steps:
1. On artifact details page
2. Click "Download to Local (8.00 GB)"
3. Wait 10 minutes for download
4. Download complete, get path
5. Load in inference script:
   model = torch.load('/path/to/downloaded/model.pth')

Time: 10 minutes
Download: 8 GB (one-time)
```

### Scenario 3: Cleanup Old Versions

```
Goal: Delete old models on server to free space

Steps:
1. Browse artifacts
2. View version history: v1(old), v2(old), v3(latest)
3. Select v1, click "Delete Version"
4. Confirm (prompts: executes on remote server)
5. Completes in 2 seconds
6. v1 deleted on server, space freed

Time: <5 seconds
Effect: Freed 8GB server space
```

---

## 🎓 Deep Understanding

### Metadata vs Large Files

**Metadata** (synced):
- `versions.json` - artifact version index
- `metadata.json` - artifact meta info
- `manifest.json` - file manifest
- `meta.json`, `status.json`, `summary.json` - experiment metadata

**Large Files** (not synced, download on-demand):
- `model.pth` - model weight files
- `dataset/*` - dataset files
- `media/*` - images, videos

### Cache Structure

```
~/.runicorn_remote_cache/{host}_{user}/
├── index.db                    # SQLite index
├── metadata/                   # Cached metadata
│   ├── artifacts/
│   │   ├── model/
│   │   │   └── resnet50/
│   │   │       ├── versions.json
│   │   │       ├── v1/metadata.json
│   │   │       └── v2/metadata.json
│   │   └── dataset/...
│   └── experiments/...
└── downloads/                  # Downloaded files
    └── resnet50/
        └── v3/
            └── model.pth       # Actual model file
```

### Data Flow

**When browsing**:
```
UI → API → RemoteAdapter → LocalCache → SQLite/JSON
                                          ↓
                                    <100ms response
```

**When downloading**:
```
UI → API → RemoteAdapter → FileFetcher → SFTP
                                          ↓
                                    Real-time progress
                                          ↓
                                    Local file system
```

**When managing**:
```
UI → API → RemoteAdapter → RemoteExecutor → SSH
                                          ↓
                                    Execute on server
                                          ↓
                                    Auto-sync metadata
```

---

## 📚 Related Resources

### Documentation

- **Architecture Design**: See project documentation
- **Integration Guide**: See developer documentation  
- **API Reference**: See API documentation

### API Documentation

- **Swagger UI**: `http://localhost:23300/docs`
- **OpenAPI JSON**: `http://localhost:23300/openapi.json`

### Example Code

- **Python Example**: `examples/remote_storage_demo.py`
- **API Testing**: Online testing in Swagger UI

---

## 🎉 Get Started!

**Experience remote storage convenience now**:

1. ⚙️ Configure SSH connection (2 minutes)
2. 🔄 Sync metadata (5 minutes)
3. 📊 Browse artifacts (instant)
4. 📥 Download files on-demand (as needed)
5. 🗑️ Manage remote artifacts (2 seconds)

**Total time**: 10-15 minutes to get fully started

**Benefits**: 
- Save time **96x faster**
- Save space **99.94%**
- Improve experience **∞**

---

**Documentation Version**: v1.0  
**Updated**: 2025-10-03  
**Runicorn Version**: v0.5.0+ (Remote Storage)

