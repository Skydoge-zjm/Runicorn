# Runicorn Remote Viewer User Guide

> **Version**: v0.5.0  
> **Last Updated**: 2025-10-25  
> **Author**: Runicorn Development Team

[English](REMOTE_VIEWER_GUIDE.md) | [简体中文](../zh/REMOTE_VIEWER_GUIDE.md)

---

## 📖 Table of Contents

1. [What is Remote Viewer](#what-is-remote-viewer)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Detailed Usage Steps](#detailed-usage-steps)
5. [Advanced Features](#advanced-features)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)
8. [FAQ](#faq)

---

## What is Remote Viewer

### Overview

Remote Viewer adopts a **VSCode Remote Development-style architecture**, allowing you to:

- Run **Viewer process on remote server**
- Access via **SSH tunnel** in local browser
- **Real-time viewing** of remote experiment data, no sync needed

### vs Traditional Approach

| Feature | Traditional Sync (0.4.x) | Remote Viewer (0.5.0) |
|---------|--------------------------|----------------------|
| **Data Transfer** | Full sync | Real-time access |
| **Local Storage** | Required (mirror) | Not required |
| **Latency** | 5-10 minutes | < 100ms |
| **Initial Wait** | Hours (large datasets) | Seconds (startup) |
| **Network** | Large initial bandwidth | Continuous small traffic |
| **Feature Completeness** | Some limitations | 100% features |

### Use Cases

✅ **Suitable for**:
- Training models on remote GPU servers
- Datasets too large to sync locally
- Real-time monitoring of remote experiments
- Managing experiments across multiple servers

❌ **Not suitable for**:
- Completely offline environments
- Unstable network connections
- Windows remote servers (not yet supported)

---

## Architecture

### Workflow

```
┌─────────────────┐                    ┌──────────────────────┐
│   Local Machine │                    │    Remote Server      │
│                 │                    │                      │
│  1. Start Local │    SSH Connection  │  2. Detect Python    │
│     Viewer      ├───────────────────>│     Environments     │
│                 │                    │                      │
│  3. Select Env  │                    │  4. Start Remote     │
│                 │                    │     Viewer Process   │
│                 │                    │     (Background)      │
│                 │                    │                      │
│  5. Establish   │    Port Forwarding │  6. Viewer Listens   │
│     SSH Tunnel  │<───────────────────│     localhost:45342  │
│                 │                    │                      │
│  7. Browser     │                    │  8. Read Data and    │
│     Access      │                    │     Return to        │
│     localhost:  │                    │     Frontend         │
│     8081        │                    │                      │
└─────────────────┘                    └──────────────────────┘
```

### Technical Details

- **Remote Viewer Process**: Independent FastAPI server running on remote server
- **SSH Tunnel**: Local port (e.g., 8081) mapped to remote Viewer port (e.g., 45342)
- **Process Management**: Remote Viewer runs as background process, auto-cleanup on disconnect
- **Session Isolation**: Each connection uses independent port, no interference

---

## Prerequisites

### Local Machine Requirements

- Python 3.8+
- Runicorn installed (`pip install runicorn`)
- SSH client (built-in on Windows/Linux/macOS)

### Remote Server Requirements

1. **Operating System**: Linux (Ubuntu, CentOS, etc.) or WSL
2. **Python Environment**: 
   - Python 3.8+
   - Conda or Virtualenv recommended
3. **Runicorn Installation**: 
   ```bash
   pip install runicorn
   ```
4. **SSH Access**: 
   - SSH service running
   - Valid login credentials (key or password)

### Network Requirements

- Stable SSH connection
- Recommended bandwidth: 1 Mbps+ (for real-time chart updates)
- Latency: < 500ms (cross-continent connections may be slower)

---

## Detailed Usage Steps

### Step 1: Start Local Viewer

```bash
runicorn viewer
```

Browser automatically opens http://localhost:23300

### Step 2: Navigate to Remote Page

Click the **"Remote"** button in the top menu bar.

### Step 3: Configure SSH Connection

#### 3.1 Fill in Server Information

**Basic Info**:
- **Host**: Server address
  - Domain: `gpu-server.lab.edu`
  - IP: `192.168.1.100`
- **Port**: Default `22`
- **Username**: SSH login username

#### 3.2 Choose Authentication Method

**Method 1: SSH Key (Recommended)**

- Click "SSH Key" tab
- **Private Key Path**: Enter or select private key file
  - Linux/macOS: `~/.ssh/id_rsa`
  - Windows: `C:\Users\YourName\.ssh\id_rsa`
- **Key Passphrase** (optional): If key is password-protected

**Method 2: Password**

- Click "Password" tab
- Enter SSH login password

**Method 3: SSH Agent**

- If SSH Agent is configured, select this option
- System will automatically use keys from Agent

#### 3.3 Click Connect

Click **"Connect to Server"** button.

**Success Message**:
```
✅ SSH Connection Successful
Server: gpu-server.lab.edu
User: your-username
```

### Step 4: Select Python Environment

#### 4.1 View Detected Environments

System automatically detects Python environments on remote server, showing a list:

| Environment | Python Version | Runicorn Version | Storage Root |
|-------------|----------------|------------------|--------------|
| base | Python 3.10.8 | 0.5.0 | /home/user/RunicornData |
| pytorch-env | Python 3.9.15 | 0.5.0 | /data/experiments |
| tf-gpu | Python 3.8.12 | ❌ Not Installed | - |

#### 4.2 Select Appropriate Environment

Click **"Use This Environment"** button on the environment card.

**Notes**:
- ✅ Must select environment with Runicorn installed
- ✅ Recommended to select same environment as training scripts
- ⚠️  Environments without Runicorn will show warnings

### Step 5: Confirm Configuration

#### 5.1 Review Configuration Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Remote Configuration Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Remote Server: gpu-server.lab.edu:22
User: your-username
Python Environment: pytorch-env
Python Version: Python 3.9.15
Runicorn Version: 0.5.0
Storage Root: /data/experiments
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### 5.2 Check Path

Confirm **Storage Root** is correct:
- This is where Runicorn data is stored on remote server
- Usually `~/RunicornData` or custom path

#### 5.3 Start Remote Viewer

Click **"Start Remote Viewer"** button.

**Startup Process**:
1. Start Viewer process on remote server
2. Establish SSH tunnel
3. Health check
4. Automatically open new browser tab

**Estimated Time**: 5-15 seconds

### Step 6: Use Remote Viewer

#### 6.1 Access Remote Data

After new tab opens, address will be similar to:
```
http://localhost:8081
```

Interface is identical to local Viewer, including:
- Experiment list
- Experiment details
- Chart visualization
- Log viewing
- Artifacts management

#### 6.2 Manage Connections

At the bottom of Remote page, you can see active connections:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Active Connections
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 gpu-server.lab.edu
   User: your-username
   Environment: pytorch-env
   Local Port: 8081
   Status: Running
   
   [Open Viewer]  [Stop Connection]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Advanced Features

### Multi-Server Management

You can connect to multiple servers simultaneously:

```
🟢 gpu-server-01 → localhost:8081
🟢 gpu-server-02 → localhost:8082
🟢 data-server   → localhost:8083
```

Each connection runs independently, no interference.

### Custom Storage Path

If Runicorn data on remote server is not in default location:

1. After selecting environment, click **"Custom Path"**
2. Enter actual storage root directory path
3. Confirm and start

### Port Conflict Handling

If local port is occupied, system automatically selects another available port.

---

## Troubleshooting

### Issue 1: Connection Failed

**Symptom**: Shows "SSH Connection Failed"

**Possible Causes**:
- SSH service not running
- Incorrect hostname or IP
- Wrong port
- Firewall blocking

**Solution**:
```bash
# Test SSH connection
ssh username@hostname

# Check SSH service
sudo systemctl status sshd
```

### Issue 2: No Environments Detected

**Symptom**: Environment list is empty

**Possible Causes**:
- Python not installed on remote server
- Conda not properly configured

**Solution**:
```bash
# Check on remote server
which python3
conda env list
```

### Issue 3: Runicorn Version Mismatch

**Symptom**: Shows "Runicorn version incompatible"

**Solution**:
```bash
# Update remote Runicorn
pip install -U runicorn
```

### Issue 4: Remote Viewer Startup Failed

**Symptom**: "Cannot start remote Viewer"

**Troubleshooting Steps**:
1. Check remote logs:
   ```bash
   tail -f /tmp/runicorn_viewer_*.log
   ```
2. Confirm port is not occupied:
   ```bash
   netstat -tuln | grep 45342
   ```
3. Check permissions:
   ```bash
   ls -la ~/RunicornData
   ```

---

## Best Practices

### 1. Use SSH Keys

✅ **Recommended**: SSH key authentication
- More secure
- No need to enter password each time
- Supports agent forwarding

```bash
# Generate SSH key
ssh-keygen -t rsa -b 4096

# Copy public key to server
ssh-copy-id username@hostname
```

### 2. Configure SSH Config

Configure server in `~/.ssh/config`:

```
Host gpu-server
    HostName gpu-server.lab.edu
    User your-username
    Port 22
    IdentityFile ~/.ssh/id_rsa
    ServerAliveInterval 60
```

Then in Runicorn, just enter hostname `gpu-server`.

### 3. Use tmux/screen

Use tmux or screen on remote server so training continues even if SSH disconnects:

```bash
# Start tmux
tmux new -s training

# Run training script
python train.py

# Detach session: Ctrl+B, D
```

### 4. Regular Cleanup

Regularly clean up old experiment data:

```bash
# Check storage usage
du -sh ~/RunicornData

# Delete old experiments (in Viewer)
```

---

## FAQ

### Q1: What's the difference between Remote Viewer and old "remote sync"?

**A**: Completely different architecture:

| Feature | Remote Sync (0.4.x) | Remote Viewer (0.5.0) |
|---------|---------------------|---------------------|
| Principle | File sync | Run Viewer remotely |
| Data Location | Local copy | Remote server |
| Real-time | Delayed | Real-time |
| Storage Need | Large | None |

### Q2: Does it support Windows remote servers?

**A**: Currently no, only supports Linux and WSL. Windows support is on the roadmap.

### Q3: Can I connect to multiple servers simultaneously?

**A**: Yes, each connection uses a different local port.

### Q4: Will data be lost after disconnecting?

**A**: No, data remains on the remote server. Reconnect to continue accessing.

### Q5: Do I need to keep SSH connection?

**A**: Yes, closing SSH connection will make Remote Viewer inaccessible, but remote data is unaffected.

### Q6: How's the performance?

**A**: 
- Latency: < 100ms (LAN), < 500ms (cross-continent)
- Bandwidth: ~100-500 KB/s (real-time chart updates)
- CPU: Remote server < 5%, Local < 2%

### Q7: Is it secure?

**A**: 
- ✅ All communication via SSH encryption
- ✅ Viewer only listens on localhost
- ✅ Not exposed to public internet
- ✅ Supports SSH key authentication

### Q8: How to stop Remote Viewer?

**A**: 
- Click "Stop Connection" on Remote page
- Or close local Viewer
- Remote process auto-cleanup

---

## More Resources

- [API Documentation](../../api/en/remote_api.md)
- [Architecture Documentation](../../architecture/en/REMOTE_VIEWER_ARCHITECTURE.md)
- [Troubleshooting](../../reference/en/TROUBLESHOOTING.md)

---

**Author**: Runicorn Development Team  
**Version**: v0.5.0  
**Last Updated**: 2025-10-25
