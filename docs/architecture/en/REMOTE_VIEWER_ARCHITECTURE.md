[English](REMOTE_VIEWER_ARCHITECTURE.md) | [简体中文](../zh/REMOTE_VIEWER_ARCHITECTURE.md)

---

# Remote Viewer Architecture

**Document Type**: Architecture  
**Version**: v0.5.0  
**Last Updated**: 2025-10-25  
**Status**: Implemented ✅

---

## Overview

### Design Goals

Remote Viewer is a core feature introduced in Runicorn v0.5.0, designed to provide a VSCode Remote-like experience for accessing remote server data in real-time without file synchronization.

**Core Objectives**:
1. **Zero Configuration**: Users only need to provide SSH credentials, system handles all configuration
2. **Real-time Data Access**: Run Viewer directly on remote environment, no local sync needed
3. **Low Latency**: Near-local access speed through SSH tunneling
4. **Security**: SSH-encrypted communication, no additional port exposure
5. **Auto Cleanup**: Automatic resource cleanup on disconnect

### Core Concepts

**Why Remote Viewer?**

Traditional SSH file sync approaches have issues:
- ❌ Need to sync large amounts of data from remote to local
- ❌ Sync process is time-consuming, especially for large models
- ❌ Consumes local storage space
- ❌ Data updates require re-sync
- ❌ Multi-user collaboration prone to conflicts

**Remote Viewer Solution**:
- ✅ No file sync, Viewer runs directly on remote
- ✅ SSH tunnel forwards remote port to local
- ✅ Local browser access, experience like local
- ✅ Real-time data, no sync wait
- ✅ Saves local storage
- ✅ Supports multi-user simultaneous access

### Comparison with VSCode Remote

| Aspect | VSCode Remote | Runicorn Remote Viewer |
|--------|---------------|------------------------|
| **Connection** | SSH | SSH |
| **Port Forwarding** | Yes | Yes |
| **Auto Cleanup** | Yes | Yes |
| **Environment Detection** | Partial | Fully Automatic |
| **Temporary Process** | Background Service | Temporary Viewer |
| **Config Complexity** | Low | Very Low |
| **ML-Specific Optimization** | No | Yes |

---

## Architecture Design

### Overall Architecture

Remote Viewer uses **Proxy Pattern** and **RPC (Remote Procedure Call)** design, forwarding user requests through SSH tunnel to temporary Viewer instance running on remote server.

**Core Component Layers**:
```
1. User Interface Layer (Browser)
   ↓ HTTP
2. Local Viewer API Layer (Remote API)
   ↓ SSH + Port Forwarding
3. SSH Tunnel Layer (Encrypted Communication)
   ↓ TCP
4. Remote Viewer Instance (Temporary Process)
   ↓ File I/O
5. Remote Data Storage (RunicornData)
```

### Component Division

System consists of **5 core components**:

#### 1. Connection Manager

**Responsibility**: Manage complete SSH connection lifecycle

**Main Functions**:
- SSH connection establishment and authentication (password/key)
- Connection pool management (multiple concurrent connections)
- Connection state tracking
- Auto-reconnect mechanism
- Connection disconnect and resource cleanup

**Technical Implementation**:
- Uses `paramiko.SSHClient` to establish SSH connection
- Supports password and SSH key authentication
- Uses `paramiko.AgentKeys` for SSH Agent support
- Connection timeout: 30 seconds
- Keep-alive interval: 60 seconds

#### 2. Environment Detector

**Responsibility**: Auto-discover and verify remote server Python environments

**Detection Algorithm**:
```
1. Execute `which python` to get system Python
2. Check conda environments: `conda env list`
3. Scan common virtualenv directories
4. For each Python environment:
   a. Execute `python -c "import runicorn; print(runicorn.__version__)"`
   b. If successful, record environment info
   c. Get config: `python -c "import runicorn.config; print(...)"`
5. Return all valid environment list
```

#### 3. Viewer Launcher

**Responsibility**: Start and manage temporary Viewer process on remote server

**Startup Flow**:
```
1. Check if target port is available
2. Build startup command:
   source /path/to/env/bin/activate && \
   runicorn viewer --host 127.0.0.1 --port 23300 --no-open-browser \
   > /tmp/runicorn_viewer_{connection_id}.log 2>&1 &
3. Execute command via SSH
4. Get process PID
5. Wait 2-3 seconds to confirm startup
6. Check if port is listening: `netstat -tuln | grep :23300`
7. Return process info
```

#### 4. Tunnel Manager

**Responsibility**: Establish and maintain SSH port forwarding tunnel

**Technical Implementation**:
- Uses `paramiko` Transport.open_channel to create tunnel
- Local port auto-selection (range 8081-8099)
- Background thread handles port forwarding
- Tunnel health monitoring and auto-rebuild

#### 5. Health Checker

**Responsibility**: Monitor connection and Viewer health status

**Health Check Logic**:
```
Health check every 30 seconds:

1. Connection check: Execute simple command test
2. Viewer check: HTTP GET /api/health
3. Tunnel check: Test local port connectivity
4. Exception handling: Auto-reconnect/rebuild
```

---

## Security Design

### SSH Authentication

**Supported Authentication Methods**:
1. **Password Authentication**: Username + Password
2. **SSH Key Authentication**: Private key file + optional passphrase
3. **SSH Agent**: Use system SSH Agent

**Security Practices**:
- ✅ Passwords not stored locally, memory-only
- ✅ Private key path configurable, supports `~/.ssh/id_rsa` etc.
- ✅ SSH Agent preferred, avoids key exposure
- ✅ Connection uses encrypted channel (SSH protocol)

### Network Security

- ✅ Viewer only listens on `127.0.0.1`, not exposed externally
- ✅ SSH tunnel encrypts all communication
- ✅ No additional firewall port opening required
- ✅ Auto cleanup prevents zombie processes

---

## Performance Characteristics

### Latency Testing

Performance in typical scenarios:

| Operation | Local Mode | Remote Viewer | Difference |
|-----------|-----------|---------------|------------|
| Load experiment list | 50ms | 120ms | +70ms |
| View experiment details | 30ms | 90ms | +60ms |
| Load metrics charts | 80ms | 180ms | +100ms |
| Real-time log stream | 10ms | 50ms | +40ms |

**Conclusion**: Remote Viewer adds approximately 50-100ms latency but maintains good user experience.

### Bandwidth Optimization

- Only transfer necessary data (metadata, metrics)
- Large files like images loaded on-demand
- Supports data compression (gzip)
- Typical session bandwidth: < 1 MB/min

---

## Fault Handling

### Common Failure Scenarios

| Failure | Detection | Recovery Strategy |
|---------|-----------|-------------------|
| SSH connection dropped | Keep-alive failure | Auto-reconnect (max 3 attempts) |
| Viewer process crashed | Health check failure | Notify user, provide logs |
| Tunnel broken | Port unreachable | Rebuild tunnel |
| Port conflict | Startup failure | Auto-select another port |

---

## Related Documentation

- **[SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)** - Overall system architecture
- **[Remote API Documentation](../../api/en/remote_api.md)** - API reference
- **[Remote Viewer User Guide](../../guides/en/REMOTE_VIEWER_GUIDE.md)** - Usage guide

---

**Navigation**: [Architecture Docs Index](README.md) | [Main Docs](../../README.md)


