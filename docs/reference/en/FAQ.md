[English](FAQ.md) | [简体中文](../zh/FAQ.md)

---

# Runicorn Frequently Asked Questions (FAQ)

**Document Type**: Reference  
**Version**: v0.5.3  
**Last Updated**: 2025-11-28

---

## Table of Contents

- [Basics](#basics)
- [Installation & Configuration](#installation--configuration)
- [Remote Viewer (v0.5.0)](#remote-viewer-v050)
- [Data Management](#data-management)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

---

## Basics

### Q1: What is Runicorn?

**A**: Runicorn is a lightweight ML experiment tracking tool providing:
- 🚀 Zero-config experiment tracking
- 📊 Real-time visualization dashboard
- 🗄️ High-performance storage (SQLite + files)
- 🔄 Artifact version control
- 🌐 Remote Viewer (VSCode Remote-style)
- 🔒 100% local, privacy-first

---

### Q2: How is Runicorn different from W&B/MLflow?

| Feature | W&B | MLflow | Runicorn |
|---------|-----|--------|----------|
| **Deployment** | Cloud SaaS | Needs server | Local zero-config |
| **Privacy** | Data in cloud | Self-hostable | 100% local |
| **Cost** | $50+/user/month | Free open-source | Free open-source |
| **Setup** | Register account | Configure server | `pip install` |
| **Remote** | Cloud access | Needs config | VSCode Remote-style |

**Best for**:
- ✅ Individual researchers or small teams
- ✅ Privacy-sensitive projects
- ✅ No external dependencies
- ✅ Remote server access needed

---

### Q3: Which ML frameworks does Runicorn support?

**A**: Framework-agnostic, supports:
- ✅ PyTorch
- ✅ TensorFlow / Keras
- ✅ JAX
- ✅ scikit-learn
- ✅ Hugging Face Transformers
- ✅ Any Python code

---

## Installation & Configuration

### Q4: How to install Runicorn?

```bash
# Basic installation
pip install runicorn

# From source
git clone https://github.com/yourusername/runicorn.git
cd runicorn
pip install -e .

# Verify
runicorn --version
```

**Requirements**: Python 3.8+, Windows/Linux/macOS

---

### Q5: How to configure storage path?

Three methods:

```bash
# Method 1: Command-line
runicorn viewer --storage-root /data/experiments

# Method 2: Environment variable
export RUNICORN_USER_ROOT_DIR=/data/experiments

# Method 3: Config file
# ~/.config/runicorn/config.yaml
storage:
  user_root_dir: /data/experiments
```

---

## Remote Viewer (v0.5.0)

### Q6: What's different from old SSH sync (0.4.x)?

| Feature | Old (0.4.x) | Remote Viewer (0.5.0) |
|---------|-------------|---------------------|
| **Architecture** | SSH file sync | VSCode Remote-style |
| **Data location** | Local copy | Remote server |
| **Sync time** | Minutes to hours | 5-10 seconds |
| **Storage** | Large (local copy) | Zero (no local storage) |
| **Real-time** | 5-10 min delay | Fully real-time |

**How it works**:
1. Start temporary Viewer on remote (127.0.0.1 only)
2. Forward port via SSH tunnel to local
3. Access via local browser, feels like local
4. No file transfer, direct remote data access

---

### Q7: What are the requirements for Remote Viewer?

**Local machine**:
- ✅ Python 3.8+
- ✅ Runicorn 0.5.0+
- ✅ SSH client (system default)

**Remote server**:
- ✅ Linux or WSL
- ✅ Python 3.8+
- ✅ **Runicorn 0.5.0+ (full install)**
- ✅ SSH server running

**Network**:
- ✅ Stable SSH connection
- ✅ SSH port access (usually 22)

**Note**: Remote server needs full Runicorn installation, not just SDK!

---

### Q8: How to use Remote Viewer?

**Step 1: Ensure Runicorn on remote**
```bash
ssh user@gpu-server.com
pip install runicorn
runicorn --version  # Should show 0.5.0+
```

**Step 2: Start local Viewer**
```bash
runicorn viewer
```

**Step 3: Connect to remote**
1. Open browser: `http://localhost:23300`
2. Click "Remote" button
3. Enter SSH info:
   - Host: `gpu-server.com`
   - Username: `your-username`
   - Auth: SSH key or password
4. Click "Connect"

**Step 4: Select environment and start**
- System auto-detects remote Python environments
- Select environment with Runicorn
- Click "Start Remote Viewer"
- System auto-opens new tab

**Done!** Now you can view remote data in real-time.

---

### Q9: Does Remote Viewer support Windows remote servers?

**A**: Not currently, only Linux and WSL.

**Supported**:
- ✅ Linux (Ubuntu, CentOS, Debian, etc.)
- ✅ WSL (Windows Subsystem for Linux)

**Not supported**:
- ❌ Native Windows servers
- ❌ macOS servers (planned)

**Workaround for Windows users**:
1. Use WSL2 as remote server
2. Wait for future version support

---

### Q10: Can I connect to multiple servers simultaneously?

**A**: Yes! Each connection uses a different local port.

**Example**:
```
Local Viewer (localhost:23300)
├── GPU Server 1 → localhost:8081
├── GPU Server 2 → localhost:8082
└── GPU Server 3 → localhost:8083
```

**Limit**: Default max 5 concurrent connections (configurable)

---

### Q11: Is Remote Viewer secure?

**A**: Yes, very secure!

**Security measures**:
- ✅ **SSH encryption**: All traffic encrypted via SSH
- ✅ **Localhost only**: Remote Viewer binds to 127.0.0.1
- ✅ **No public exposure**: No extra ports exposed
- ✅ **SSH key support**: Recommended authentication
- ✅ **No password storage**: Passwords only in memory
- ✅ **Auto cleanup**: Automatic resource cleanup on disconnect

**Best practices**:
1. Use SSH keys instead of passwords
2. Configure SSH Keep-alive
3. Use only on trusted networks

---

### Q12: What's the performance of Remote Viewer?

**Latency** (measured):

| Network | Added Latency | Experience |
|---------|--------------|------------|
| LAN | +20-50ms | Nearly imperceptible |
| Same city | +50-100ms | Smooth |
| Cross-region | +100-300ms | Good |
| Cross-country | +300-500ms | Acceptable |

**Bandwidth**:
- Idle: < 1 KB/s
- Browsing experiments: ~50-100 KB/s
- Real-time charts: ~100-500 KB/s

**CPU usage**:
- Remote server: < 5%
- Local machine: < 2%

---

## Data Management

### Q13: Where is experiment data stored?

**Default locations**:
- Linux/macOS: `~/RunicornData`
- Windows: `%USERPROFILE%\RunicornData`

**Structure**:
```
RunicornData/
├── runicorn.db              # SQLite database
├── project1/
│   └── experiment1/
│       └── runs/
│           └── 20251025_143022_abc123/
│               ├── meta.json
│               ├── events.jsonl
│               └── logs.txt
└── artifacts/               # Artifact storage
```

---

### Q14: How to backup data?

**Method 1: Export command**
```bash
runicorn export \
  --format zip \
  --include-artifacts \
  --output backup_$(date +%Y%m%d).zip
```

**Method 2: Direct copy**
```bash
tar -czf runicorn_backup.tar.gz ~/RunicornData
```

**Method 3: Auto backup**
```yaml
# config.yaml
storage:
  auto_backup: true
  backup_interval_hours: 24
```

---

### Q15: How does Artifact deduplication work?

**A**: Content-Addressable Storage with SHA256 hashing.

**Process**:
1. Calculate file SHA256 hash
2. Check if exists in dedup pool
3. If exists, create hard link (zero-copy)
4. If not, copy to dedup pool

**Effect**: Save 50-90% storage space

---

## Performance

### Q16: Why is experiment list loading slow?

**A**: Might be using V1 API (file scanning).

**Solution: Enable V2 API (SQLite)**

```yaml
# config.yaml
storage:
  use_database: true
```

**Performance comparison**:
- V1 (1000 experiments): ~5-10 seconds
- V2 (1000 experiments): ~50 milliseconds
- **100x faster!**

---

## Troubleshooting

### Q17: Connection to remote server fails?

**Troubleshoot in order**:

1. **Test SSH connection**
```bash
ssh user@remote-server
```

2. **Check remote Runicorn**
```bash
ssh user@remote-server "runicorn --version"
```

3. **Check Python environment**
```bash
ssh user@remote-server "which python"
```

4. **View detailed errors**
```bash
runicorn viewer --log-level DEBUG
```

5. **View remote logs**
```bash
ssh user@remote-server "cat /tmp/runicorn_viewer_*.log"
```

---

### Q18: Viewer startup fails?

**Error: "Port already in use"**
```bash
# Check port usage
lsof -i :23300  # Linux/macOS
netstat -ano | findstr :23300  # Windows

# Use different port
runicorn viewer --port 23301
```

**Error: "Permission denied"**
```bash
# Fix permissions
chmod -R 755 ~/RunicornData
```

---

## Advanced Usage

### Q19: How to use in Jupyter Notebook?

```python
import runicorn as rn

# Initialize
run = rn.init(project="research", name="experiment-1")

# Log metrics
run.log({"loss": 0.5, "accuracy": 0.9})

# Log image
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [4, 5, 6])
run.log_image("plot", fig)

# Finish
run.finish()
```

---

### Q20: How to use Artifact versioning?

**Create Artifact**:
```python
artifact = rn.Artifact(name="my-model", type="model")
artifact.add_file("model.pth")
run.log_artifact(artifact)  # Auto-versioned
```

**Use Artifact**:
```python
# Load latest
artifact = run.use_artifact("my-model:latest")

# Load specific version
artifact = run.use_artifact("my-model:v3")

# Download and use
model_path = artifact.download()
```

---

## Getting Help

### Q21: Where to get help?

**Documentation**:
- 📚 [User Guides](../../guides/en/)
- 🔧 [API Reference](../../api/en/)
- 🏗️ [Architecture Docs](../../architecture/en/)

**Community**:
- 💬 GitHub Issues: https://github.com/yourusername/runicorn/issues
- 📧 Email: support@runicorn.dev

**Diagnostic info**:
```bash
runicorn config --show > diagnosis.txt
runicorn --version >> diagnosis.txt
```

---

**Didn't find your answer?**

Check [full documentation](../../README.md) or [submit an issue](https://github.com/yourusername/runicorn/issues/new)

---

**Back to**: [Reference Docs](README.md) | [Main Docs](../../README.md)


