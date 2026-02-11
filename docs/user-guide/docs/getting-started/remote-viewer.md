# Remote Viewer Guide

Access experiments on remote GPU servers without file sync — VSCode Remote-style architecture!

---

## Overview

**Remote Viewer** (v0.5.0+) is a revolutionary feature that lets you view experiments running on remote servers directly from your local browser. Unlike traditional file sync approaches, Remote Viewer:

- ✅ **Zero file transfer** — Data stays on the remote server
- ✅ **Instant access** — No waiting for sync (< 100ms latency)
- ✅ **Secure** — All traffic goes through SSH tunnel
- ✅ **Easy setup** — Just SSH credentials + Python environment

<figure markdown>
  ![Remote Viewer](../assets/remote.png)
  <figcaption>Connect to remote servers via SSH tunnel</figcaption>
</figure>

!!! info "Architecture"
    Remote Viewer works like VSCode Remote Development. A Viewer process runs on your remote server, and you access it through an SSH tunnel. Your data never leaves the server!

---

## Prerequisites

### On Remote Server

1. **Python 3.10+** installed
2. **Runicorn** installed in a Python environment:
   ```bash
   # Conda environment
   conda activate ml_env
   pip install runicorn
   
   # Or virtualenv
   source /path/to/venv/bin/activate
   pip install runicorn
   ```
3. **SSH access** enabled

### On Local Machine

1. **Runicorn** installed: `pip install runicorn`
2. **SSH credentials** — password or private key

---

## Quick Start

### Step 1: Start Local Viewer

```bash
runicorn viewer
```

Open [http://127.0.0.1:23300](http://127.0.0.1:23300)

### Step 2: Go to Remote Page

Click **"Remote"** in the navigation menu.

### Step 3: Connect to Server

Fill in the connection form:

| Field | Example | Description |
|-------|---------|-------------|
| **Host** | `gpu-server.lab.com` | Remote server hostname or IP |
| **Port** | `22` | SSH port (default: 22) |
| **Username** | `your_username` | SSH login username |
| **Auth Method** | Key / Password | Choose authentication method |
| **Private Key** | `~/.ssh/id_rsa` | Path to SSH private key |
| **Password** | `••••••••` | SSH password (if using password auth) |

Click **Connect**.

### Step 4: Select Python Environment

After connecting, Runicorn automatically detects Python environments with Runicorn installed:

- Conda environments
- Virtualenvs
- System Python

Select the environment you use for training.

### Step 5: Start Remote Viewer

Click **Start Viewer**. This will:

1. Launch a Viewer process on the remote server
2. Create an SSH tunnel to your local machine
3. Open the remote experiments in your browser

!!! success "Done!"
    You can now browse remote experiments as if they were local!

---

## Features

### Real-time Experiment Monitoring

- 📊 **Live metrics** — Charts update as training progresses
- 📝 **Live logs** — Stream training logs in real-time
- 🖼️ **Images** — View logged images immediately

### Connection Management

- 🔗 **Multiple connections** — Connect to multiple servers
- 💾 **Save credentials** — Store connection settings (encrypted)
- 🔄 **Auto-reconnect** — Automatic reconnection on network issues

### Health Monitoring

- ✅ **Connection status** — See if connection is alive
- ⏱️ **Latency** — Monitor network latency
- 📈 **Viewer status** — Check if remote Viewer is running

---

## Troubleshooting

### Connection Failed

```
Error: SSH authentication failed
```

**Solutions**:

1. Verify SSH credentials are correct
2. Check if SSH key has correct permissions: `chmod 600 ~/.ssh/id_rsa`
3. Try connecting via terminal first: `ssh user@host`

### No Environments Detected

```
Warning: No compatible Python environments found
```

**Solutions**:

1. Install Runicorn on remote server:
   ```bash
   pip install runicorn
   ```
2. Check if environment is activated before running detection
3. Verify Python version is 3.10+

### Viewer Won't Start

```
Error: Failed to start remote Viewer
```

**Solutions**:

1. Check if port is available on remote server
2. Verify Runicorn is installed in selected environment
3. Check remote server logs for errors

### High Latency

If you experience slow response times:

1. Check network connection quality
2. Consider using a closer server
3. Reduce chart refresh rate in settings

---

## Best Practices

!!! tip "Use SSH Keys"
    SSH keys are more secure and convenient than passwords. Generate one if you haven't:
    ```bash
    ssh-keygen -t ed25519 -C "your_email@example.com"
    ssh-copy-id user@remote-server
    ```

!!! tip "Persistent Storage Path"
    Always use a consistent storage path on remote server:
    ```python
    run = rn.init(
        path="training",
        storage="/data/runicorn"  # Consistent path
    )
    ```

!!! tip "Save Connections"
    Save frequently used connections for quick access. Credentials are stored securely.

---

## Comparison: Remote Viewer vs File Sync

| Feature | Remote Viewer (v0.5.0+) | File Sync (v0.4.x) |
|---------|------------------------|-------------------|
| **Data Location** | Stays on server | Copied to local |
| **Initial Wait** | None (instant) | Minutes to hours |
| **Bandwidth** | Low (UI only) | High (all files) |
| **Privacy** | Data never leaves server | Data copied locally |
| **Storage** | No local storage needed | Requires local space |
| **Real-time** | ✅ Yes | ⚠️ Delayed |

---

## Next Steps

- [Python SDK Overview](../sdk/overview.md) — Learn the SDK
- [CLI Overview](../cli/overview.md) — Command-line tools
- [FAQ](../reference/faq.md) — Common questions

---

<div align="center">
  <p><strong>Ready to train on remote servers?</strong></p>
  <p>Start the viewer and connect to your GPU server! 🚀</p>
</div>
