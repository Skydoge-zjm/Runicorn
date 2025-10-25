# Runicorn v0.5.0 Release Notes

> **Release Date**: 2025-10-25  
> **Version**: v0.5.0  
> **Author**: Runicorn Development Team

[English](RELEASE_NOTES_v0.5.0.md) | [简体中文](../zh/RELEASE_NOTES_v0.5.0.md)

---

## 🚀 Major Updates

### Remote Viewer - VSCode Remote Architecture

Runicorn 0.5.0 introduces an all-new **Remote Viewer** feature, adopting a VSCode Remote Development-style architecture that completely transforms how you access remote servers.

**Core Changes**:
- 🌐 Run Viewer process directly on remote server
- 🔌 Access via SSH tunnel in local browser
- ⚡ Real-time access to remote data, no sync needed
- 💾 Zero local storage usage
- 📊 Full feature parity

**vs Old Remote Sync (0.4.x)**:

| Feature | 0.4.x File Sync | 0.5.0 Remote Viewer |
|---------|-----------------|---------------------|
| Data Transfer | Sync GB-level data | No sync, real-time access |
| Initial Wait | Hours (large datasets) | Seconds (connection startup) |
| Local Storage | Required (mirror copy) | Not required (zero usage) |
| Real-time | 5-10 min delay | Fully real-time (< 100ms) |

---

## ✨ New Features

### Remote Viewer Core Features

- **SSH Connection Management**: Key/password auth, automatic port forwarding
- **Auto Environment Detection**: Smart detection of Conda, Virtualenv environments
- **Viewer Lifecycle Management**: Auto-start, health checks, graceful shutdown
- **Multi-Server Support**: Connect to multiple servers simultaneously, isolated ports
- **Real-time Health Monitoring**: Connection status, performance metrics live display

### UI Improvements

- **Remote Page**: Brand new connection wizard interface
- **Environment Selector**: Display Python version, Runicorn version, storage path
- **Configuration Preview**: Confirm all settings before starting
- **Active Connection Management**: View and manage all remote connections
- **Error Message Optimization**: Clearer error messages and troubleshooting hints

### Performance Optimizations

- **Connection Speed**: Startup time reduced from hours to seconds
- **Network Optimization**: Bandwidth usage reduced from GB to MB
- **Memory Optimization**: No local mirror data storage needed
- **Latency Optimization**: Real-time access latency < 100ms

---

## 💥 Breaking Changes

### ⚠️  API Changes

**Deprecated APIs**:
- `POST /api/ssh/connect` → Use `POST /api/remote/connect`
- `GET /api/ssh/status` → Use `GET /api/remote/viewer/status`
- `POST /api/ssh/sync` → **Removed** (sync no longer needed)
- `GET /api/ssh/mirror/list` → **Removed**
- `DELETE /api/ssh/disconnect` → Use `DELETE /api/remote/connections/{id}`

**New APIs** (12 endpoints):
- Remote connection management (3)
- Environment detection (3)
- Viewer management (4)
- Health checks (2)

See: [Remote API Documentation](../../api/en/remote_api.md)

### ⚠️  Configuration Format Changes

**Old Config** (`ssh_config.json`):
```json
{
  "connections": [
    {
      "host": "server.com",
      "mode": "mirror"
    }
  ]
}
```

**New Config**: No config file needed, all configuration via UI or API

### ⚠️  Module Changes

- **Deprecated**: `src/runicorn/ssh_sync.py`
- **New**: `src/runicorn/remote/` module
- **New**: `src/runicorn/viewer/api/remote.py`

---

## 🔌 New API Endpoints

### Connection Management
```
POST   /api/remote/connect          Establish SSH connection
GET    /api/remote/connections      List all connections
DELETE /api/remote/connections/{id} Disconnect connection
```

### Environment Detection
```
GET    /api/remote/environments           List Python environments
POST   /api/remote/environments/detect   Re-detect environments
GET    /api/remote/config                Get remote configuration
```

### Remote Viewer Management
```
POST   /api/remote/viewer/start    Start Remote Viewer
POST   /api/remote/viewer/stop     Stop Remote Viewer
GET    /api/remote/viewer/status   Get status
GET    /api/remote/viewer/logs     Get logs
```

### Health Checks
```
GET    /api/remote/health          Connection health status
GET    /api/remote/ping            Test connection
```

---

## 🐛 Bug Fixes

- **Fixed**: WebSocket connection memory leak
- **Fixed**: Improper SSH connection timeout handling
- **Fixed**: Error handling during port conflicts
- **Fixed**: Remote Viewer process not properly cleaned up
- **Fixed**: Environment detection failure for non-standard Python installations
- **Fixed**: Race conditions when starting multiple connections simultaneously

---

## 📚 Documentation Updates

### New Documentation

- **[Remote Viewer User Guide](../../guides/en/REMOTE_VIEWER_GUIDE.md)** - Complete usage tutorial
- **[Remote Viewer Architecture](../../architecture/en/REMOTE_VIEWER_ARCHITECTURE.md)** - Technical architecture docs
- **[0.4.x → 0.5.0 Migration Guide](../../guides/en/MIGRATION_GUIDE_v0.4_to_v0.5.md)** - Upgrade guide
- **[Remote API Documentation](../../api/en/remote_api.md)** - Complete API reference

### Updated Documentation

- **README** - Added Remote Viewer quick start
- **Quick Start Guide** - Updated for Remote Viewer
- **CHANGELOG** - Complete v0.5.0 changelog
- **Remote Storage Guide** - Marked as deprecated

---

## ⚠️  Known Limitations

### Platform Support

- ✅ **Local**: Windows, Linux, macOS
- ✅ **Remote Server**: Linux (including WSL)
- ❌ **Remote Server**: Windows (planned)

### Network Requirements

- Stable SSH connection required
- Recommended bandwidth: 1 Mbps+
- Latency: < 500ms (cross-continent may be slower)

### Security Limitations

- Cascaded connections limited to 2 levels (A→B→C)
- Remote server must have Runicorn 0.5.0 installed

---

## 🔄 Upgrade Guide

### For Existing Users

#### 1. Upgrade Local Runicorn

```bash
pip install -U runicorn
```

#### 2. Upgrade Remote Server

```bash
# SSH login to remote server
ssh user@remote-server

# Upgrade Runicorn
pip install -U runicorn
```

#### 3. Migrate to Remote Viewer

**Old Way** (0.4.x file sync):
1. Configure SSH connection
2. Select remote directory
3. Click "Sync this directory"
4. Wait hours for sync to complete

**New Way** (0.5.0 Remote Viewer):
1. Click "Remote" menu
2. Fill in SSH info
3. Select Python environment
4. Click "Start Remote Viewer"
5. **Done in seconds, use immediately**!

See: [Migration Guide](../../guides/en/MIGRATION_GUIDE_v0.4_to_v0.5.md)

### For New Users

Directly use Remote Viewer to access remote servers:

```bash
# 1. Install Runicorn (local and remote)
pip install runicorn

# 2. Start local Viewer
runicorn viewer

# 3. Use Remote feature in browser
```

---

## 🎯 Use Cases

### Suitable for Remote Viewer

✅ **GPU Server Training**: Train on lab/company GPU servers, view locally in real-time  
✅ **Large Datasets**: Datasets too large to sync locally  
✅ **Real-time Monitoring**: Need to view training progress in real-time  
✅ **Multi-Server Management**: Manage experiments across multiple servers simultaneously  

### Not Suitable for Remote Viewer

❌ **Completely Offline**: Environments without network connection  
❌ **Unstable Network**: Scenarios with frequent disconnections  
❌ **Windows Remote Servers**: Not yet supported (planned)  

---

## 📊 Performance Comparison

| Metric | 0.4.x File Sync | 0.5.0 Remote Viewer | Improvement |
|--------|-----------------|---------------------|-------------|
| Initialization Time | 2-8 hours | 5-15 seconds | **99.9%** ↓ |
| Local Storage Usage | 100 GB+ | 0 GB | **100%** ↓ |
| Real-time Latency | 5-10 minutes | < 100ms | **99.9%** ↓ |
| Network Bandwidth | Initial 10+ GB | Continuous 100 KB/s | **99%** ↓ |
| CPU Usage (Remote) | 5-10% | < 5% | **50%** ↓ |
| CPU Usage (Local) | 2-5% | < 2% | **60%** ↓ |

---

## 🔐 Security

### Enhanced Security Measures

- ✅ All communication via SSH encryption
- ✅ Viewer only listens on localhost, not exposed to public internet
- ✅ SSH key authentication supported
- ✅ Automatic port selection to avoid conflicts
- ✅ Complete connection audit logs

### Security Recommendations

1. **Use SSH Keys**: Recommended over passwords
2. **Configure SSH Config**: Simplify connection configuration
3. **Regular Updates**: Keep Runicorn up to date
4. **Network Isolation**: Use only in trusted network environments

---

## 📝 Technical Details

### Architecture Changes

**0.4.x Architecture**:
```
Local Viewer → SSH File Transfer → Local Storage → Local Display
```

**0.5.0 Architecture**:
```
Local Viewer → SSH Tunnel → Remote Viewer → Remote Data → Local Display
```

### Key Technologies

- **SSH Tunnel**: Local port mapped to remote Viewer port
- **FastAPI**: Remote Viewer uses FastAPI for services
- **Process Management**: Remote Viewer runs as background process
- **Health Checks**: Real-time monitoring of connection and Viewer status

---

## 🎉 Community Feedback

We greatly appreciate the valuable feedback from the community during development!

**Major improvements from user feedback**:
- Need for real-time access to remote data
- Reduce local storage usage
- Simplify remote connection process
- Improve connection speed

---

## 📞 Support & Feedback

### Get Help

- **User Guide**: [Remote Viewer User Guide](../../guides/en/REMOTE_VIEWER_GUIDE.md)
- **FAQ**: [Frequently Asked Questions](../../reference/en/FAQ.md)
- **API Docs**: [Remote API Reference](../../api/en/remote_api.md)

### Report Issues

- **GitHub Issues**: [Submit Bug Report](https://github.com/yourusername/runicorn/issues)
- **Feature Requests**: [Submit Feature Suggestion](https://github.com/yourusername/runicorn/discussions)

---

## 🗺️  Future Plans

### v0.5.x Plans

- Windows remote server support
- macOS remote server support
- Connection persistence and auto-reconnect
- More environment detection optimizations

### v0.6.0 Plans

- Multi-user collaboration features
- Experiment sharing and permission management
- Webhook integration
- Advanced visualization features

---

## 📥 Downloads

### PyPI

```bash
pip install -U runicorn
```

### GitHub Releases

- [v0.5.0 Source Code](https://github.com/yourusername/runicorn/archive/v0.5.0.tar.gz)
- [Windows Desktop App](https://github.com/yourusername/runicorn/releases/v0.5.0)

---

## 🙏 Acknowledgments

Thanks to all developers and users who contributed to Runicorn 0.5.0!

**Special Thanks**:
- VSCode Remote Development team for design inspiration
- All users who provided feedback and suggestions
- Open source community support

---

**Author**: Runicorn Development Team  
**Version**: v0.5.0  
**Release Date**: 2025-10-25

**[View Full CHANGELOG](../../CHANGELOG.md)** | **[Back to Documentation](../../README.md)**
