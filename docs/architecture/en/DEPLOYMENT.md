[English](DEPLOYMENT.md) | [简体中文](../zh/DEPLOYMENT.md)

---

# Deployment Architecture

**Document Type**: Architecture  
**Purpose**: Document deployment options and production considerations

---

## Deployment Options

Runicorn supports multiple deployment scenarios:

1. **Local Development** - Single user, local machine
2. **Shared Server** - Team access via network
3. **Desktop Application** - Native Windows app
4. **Remote Training + Local Viewing** - SSH sync

---

## Local Development Deployment

### Architecture

```
┌─────────────────────────────────┐
│   Developer Machine             │
│                                 │
│   ┌─────────────────────────┐  │
│   │ Python Process          │  │
│   │ - SDK (training code)   │  │
│   │ - Writes to local files │  │
│   └─────────────────────────┘  │
│                                 │
│   ┌─────────────────────────┐  │
│   │ Runicorn Viewer         │  │
│   │ - FastAPI server        │  │
│   │ - Serves on 127.0.0.1   │  │
│   └─────────────────────────┘  │
│                                 │
│   ┌─────────────────────────┐  │
│   │ Browser                 │  │
│   │ - React UI              │  │
│   │ - localhost:23300       │  │
│   └─────────────────────────┘  │
│                                 │
│   Storage: ./RunicornData      │
└─────────────────────────────────┘
```

### Setup

```bash
# Install
pip install runicorn

# Configure storage
runicorn config --set-user-root "E:\RunicornData"

# Start viewer
runicorn viewer

# Open browser
http://127.0.0.1:23300
```

### Characteristics

- ✅ **Simple**: One command to start
- ✅ **Private**: No network exposure
- ✅ **Fast**: No network latency
- ⚠️ **Single user**: No concurrent access

---

## Shared Server Deployment

### Architecture

```
┌────────────────────────────────────────────────┐
│         Lab Server (Linux/Windows)             │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │ Runicorn Viewer (Background Service)     │ │
│  │ - Binds to 0.0.0.0:23300                 │ │
│  │ - Serves team members                    │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  Storage: /data/runicorn (Shared)             │
└────────────────┬───────────────────────────────┘
                 │
         Network (LAN)
                 │
     ┌───────────┼───────────┐
     │           │           │
┌────▼────┐ ┌────▼────┐ ┌───▼─────┐
│ User 1  │ │ User 2  │ │ User 3  │
│ Browser │ │ Browser │ │ Browser │
└─────────┘ └─────────┘ └─────────┘
```

### Setup

**On server**:
```bash
# Install
pip install runicorn

# Configure shared storage
export RUNICORN_DIR="/data/runicorn"

# Start as service (systemd)
sudo systemctl start runicorn-viewer

# Or run in screen/tmux
screen -S runicorn
runicorn viewer --host 0.0.0.0 --port 23300
```

**Systemd service** (`/etc/systemd/system/runicorn-viewer.service`):
```ini
[Unit]
Description=Runicorn Viewer Service
After=network.target

[Service]
Type=simple
User=mllab
Environment="RUNICORN_DIR=/data/runicorn"
ExecStart=/usr/local/bin/runicorn viewer --host 0.0.0.0 --port 23300
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**Users access**:
```
http://server-ip:23300
```

### Characteristics

- ✅ **Team access**: Multiple users
- ✅ **Shared storage**: Everyone sees same experiments
- ✅ **Centralized**: One source of truth
- ⚠️ **No auth**: Trust network (use firewall/VPN)
- ⚠️ **Concurrent writes**: SQLite handles, but monitor

---

## Desktop Application Deployment

### Architecture

```
┌─────────────────────────────────────┐
│   Windows Desktop App (Tauri)       │
│                                     │
│  ┌────────────────────────────────┐│
│  │ Tauri Wrapper (Rust)           ││
│  │ - Native window                ││
│  │ - Auto-starts Python backend   ││
│  │ - Embedded web view            ││
│  └────────────────────────────────┘│
│                                     │
│  ┌────────────────────────────────┐│
│  │ Python Sidecar                 ││
│  │ - Runicorn viewer subprocess   ││
│  │ - Runs on random port          ││
│  └────────────────────────────────┘│
│                                     │
│  ┌────────────────────────────────┐│
│  │ React UI (Bundled)             ││
│  │ - Pre-compiled frontend        ││
│  │ - Loaded in webview            ││
│  └────────────────────────────────┘│
│                                     │
│  Storage: User-configured          │
└─────────────────────────────────────┘
```

### Installation

**From GitHub Releases**:
1. Download `Runicorn_Desktop_vX.Y.Z_x64-setup.exe`
2. Run installer
3. Launch "Runicorn Desktop" from Start Menu

### Building from Source

**Prerequisites**:
- Node.js 18+
- Rust (stable)
- Python 3.8+
- NSIS (for installer)

**Build**:
```powershell
cd desktop/tauri
.\build_release.ps1 -Bundles nsis
```

**Output**: 
```
desktop/tauri/src-tauri/target/release/bundle/nsis/
└── Runicorn_Desktop_0.4.0_x64-setup.exe
```

### Characteristics

- ✅ **Native feel**: Windows app, not browser
- ✅ **Auto-start**: Backend starts automatically
- ✅ **Offline**: No network required
- ✅ **Lightweight**: ~10MB installer (vs 100MB+ Electron)
- ⚠️ **Windows only**: Desktop app currently

---

## Remote Viewer Deployment (v0.5.0)

### Architecture

```
┌──────────────────────┐   SSH Tunnel   ┌─────────────────────┐
│   Remote Server      │◄──────────────►│   Local Machine     │
│   (Linux, GPU)       │                │   (Windows/Mac)     │
│                      │                │                     │
│  Training Processes  │                │  Local Viewer       │
│  - Write to storage  │                │  - Initiates conn   │
│  - ~/RunicornData    │                │  - Port forwarding  │
│                      │                │                     │
│  Remote Viewer       │                │  Browser            │
│  - Temporary process │                │  - localhost:8081   │
│  - 127.0.0.1:23300   │◄───tunnel──────│  - Real-time access │
│  - Reads local data  │                │                     │
│                      │                │                     │
│  Full Runicorn       │                │  Full installation  │
└──────────────────────┘                └─────────────────────┘

Workflow:
1. User configures SSH connection in local Viewer
2. Auto-detect remote Python environments
3. Start temporary Viewer on remote server
4. Forward port through SSH tunnel
5. User browser accesses remote data (transparently)
```

### Setup

**On remote server** (training):
```bash
# Install full Runicorn (required)
pip install runicorn

# In training script
import runicorn as rn

run = rn.init(
    project="training",
    storage="~/RunicornData"  # Or any path
)

# Training code...
rn.log({"loss": 0.1})
rn.finish()
```

**On local machine** (viewing):
```bash
# 1. Install Runicorn
pip install runicorn

# 2. Start local viewer
runicorn viewer

# 3. Connect to remote server in Web UI:
#    - Click "Remote" button
#    - Enter SSH credentials:
#      * Host: gpu-server.university.edu
#      * Port: 22
#      * Username: researcher
#      * Auth: SSH key or password
#    
# 4. System automatically:
#    ✓ Detects remote Python environments
#    ✓ Selects environment with Runicorn
#    ✓ Starts remote Viewer
#    ✓ Establishes SSH tunnel
#    ✓ Opens new browser tab
#
# 5. Access remote data in real-time!
#    - No file sync needed
#    - View experiments live
#    - Low latency (~50-100ms)
```

### Comparison with Old Approach (SSH File Sync)

| Feature | Old (SSH Sync) | Remote Viewer (v0.5.0) |
|---------|----------------|------------------------|
| **Data Transfer** | Sync large files | No sync, direct access |
| **Wait Time** | Minutes for first sync | Instant connect (5-10s) |
| **Local Storage** | High usage | Zero usage |
| **Real-time** | Need re-sync | Fully real-time |
| **Network Bandwidth** | High (models, etc.) | Low (metadata only) |
| **Multi-user** | Conflict-prone | No conflicts |
| **Experience** | Local-like | Local-like |

### Characteristics

- ✅ **Zero sync**: No file transfer, direct access
- ✅ **Instant connect**: Ready in 5-10 seconds
- ✅ **Low latency**: Adds 50-100ms (acceptable)
- ✅ **Space saving**: No local storage needed
- ✅ **Real-time**: Training data instantly visible
- ✅ **Auto cleanup**: Automatic cleanup on disconnect
- ✅ **Secure**: SSH encryption, no extra port exposure
- ⚠️ **Requires SSH**: Server must allow SSH access
- ⚠️ **Full install needed**: Remote must have full Runicorn (not just SDK)

---

## Production Considerations

### Security

**Local/Dev**:
- No authentication needed (localhost only)
- Firewall protects from external access

**Shared Server**:
- ⚠️ **No built-in auth** - Rely on network security
- **Recommendations**:
  - Use firewall (allow only internal IPs)
  - Use VPN for remote access
  - Use SSH tunneling: `ssh -L 23300:localhost:23300 server`

**Future**: API key authentication planned for v0.5+

---

### Performance Tuning

**For large deployments (10,000+ experiments)**:

1. **Use V2 API exclusively**
   - Frontend: Always query `/api/v2/experiments`
   - Avoid V1 file-scanning endpoints

2. **Adjust SQLite settings**:
```python
# In src/runicorn/storage/backends.py
PRAGMA cache_size=20000;  # Increase cache (default: 10000)
```

3. **Increase connection pool**:
```python
# In ConnectionPool.__init__
pool_size=20  # Default: 10
```

4. **Regular maintenance**:
```sql
-- Vacuum database (reclaim space)
VACUUM;

-- Analyze for query optimization
ANALYZE;
```

---

### Scaling Strategies

**Vertical Scaling** (single machine):
- ✅ Up to 500,000 experiments tested
- Add RAM for larger cache
- SSD for faster I/O
- More CPU cores for concurrent requests

**Horizontal Scaling** (future):
- Not currently supported (single SQLite file)
- Future: Read replicas, sharding
- Alternative: Multiple independent instances per team

---

### Backup Strategy

**Automated backups**:
```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
runicorn export --out /backups/runicorn_$DATE.tar.gz

# Keep last 30 days
find /backups -name "runicorn_*.tar.gz" -mtime +30 -delete
```

**Database backup** (SQLite):
```bash
# Online backup (while viewer running)
sqlite3 $RUNICORN_DIR/runicorn.db ".backup /backups/runicorn_$DATE.db"
```

---

### Monitoring

**Health check**:
```bash
# Monitor API availability
curl http://localhost:23300/api/health

# Expected: {"status": "ok", "version": "0.4.0"}
```

**Disk usage**:
```bash
# Monitor storage growth
du -sh $RUNICORN_DIR

# Monitor dedup effectiveness
runicorn artifacts --action stats
```

**Performance**:
```bash
# Check query times (should be <100ms)
curl http://localhost:23300/api/v2/experiments?per_page=50

# Monitor in browser DevTools → Network tab
```

---

### Troubleshooting

**Viewer won't start**:
```bash
# Check port availability
lsof -i :23300  # Linux/Mac
netstat -ano | findstr :23300  # Windows

# Check Python version
python --version  # Must be 3.8+

# Check installation
pip list | grep runicorn
```

**Database locked**:
```bash
# Stop viewer gracefully
pkill -INT runicorn  # Or Ctrl+C

# Wait 5 seconds
sleep 5

# Restart
runicorn viewer
```

**Slow queries**:
```bash
# Check if using V1 API (slow)
# Solution: Ensure frontend uses V2 API

# Or: Rebuild indexes
sqlite3 runicorn.db "REINDEX;"
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Python 3.8+ installed
- [ ] Sufficient disk space (estimate: experiments × 10MB + models)
- [ ] Network accessible (if shared deployment)
- [ ] Firewall configured (if applicable)
- [ ] Backup strategy in place

### Post-Deployment

- [ ] Health check passes
- [ ] Storage directory writable
- [ ] Users can access UI
- [ ] Experiments appear correctly
- [ ] Backup tested
- [ ] Monitoring configured

---

**Related**: [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) | [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md)

**Back to**: [Architecture Index](README.md)

