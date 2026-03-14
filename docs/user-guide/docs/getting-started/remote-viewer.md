# Remote Viewer Guide

Access experiments on remote servers without copying the whole run directory to your local machine.

---

## Overview

Remote Viewer runs a lightweight Runicorn viewer process on the remote machine and forwards it through SSH. In Runicorn 0.7.0, this workflow is much more robust than the older 0.6.0-era docs suggest.

Key points:

- zero file sync for normal browsing
- saved server profiles and connection presets
- host key confirmation inside the UI
- faster environment probing
- health monitoring and reconnect states
- OpenSSH-first connection flow with password support

## Prerequisites

### Remote machine

1. Python 3.10+ installed
2. Runicorn installed in the Python environment you plan to use:
   ```bash
   conda activate ml_env
   pip install runicorn
   ```
3. SSH access enabled

### Local machine

1. Runicorn installed: `pip install runicorn`
2. SSH credentials available
3. Local viewer running: `runicorn viewer`

---

## Connection flow

### 1. Open the Remote page

Start the local viewer, then open [http://127.0.0.1:23300](http://127.0.0.1:23300) and click **Remote**.

### 2. Add or choose a saved server

The current UI separates saved servers from saved connection profiles. That lets you reuse the same host with different Python environments or storage roots.

Typical fields:

| Field | Example | Description |
|-------|---------|-------------|
| Host | `gpu-server.lab.com` | Remote server hostname or IP |
| Port | `22` | SSH port |
| Username | `your_username` | SSH login |
| Auth Method | SSH key / Password | Runicorn 0.7.0 supports both |
| Private Key | `~/.ssh/id_ed25519` | Recommended for regular use |
| Password | `••••••••` | Supported in the OpenSSH path |

### 3. Confirm the host key if prompted

If the host is new or its key changed, Runicorn asks you to confirm the SSH host key in the UI before continuing.

### 4. Pick a Python environment

The environment step is now much faster than older versions because the SSH side caches environment discovery and batches Runicorn checks.

You can choose from:

- conda environments
- virtualenvs
- system Python
- saved environment presets

### 5. Review config and start the session

When you press **Start**, Runicorn will:

1. start the remote viewer process
2. open the SSH tunnel
3. register the session locally
4. show the session card and status

After that, what you enter is almost the same viewer experience as the local one. The key difference is that the viewer backend is running on the remote server, while you are interacting with it through the local UI.

---

## Authentication options

### SSH key

Recommended for regular use.

### Password

Runicorn 0.7.0 adds OpenSSH password support for command and tunnel paths. If authentication fails, Runicorn no longer jumps to Paramiko just because the password was wrong.

---

## Session states and recovery

Remote session cards can show states such as:

- `running`
- `reconnecting`
- `degraded`
- `disconnected`
- `stopped`

Runicorn 0.7.0 adds:

- health monitoring for long-running sessions
- tunnel auto-reconnect
- better handling for crashed remote viewer processes
- clearer status messages in the UI

### Stop behavior

The UI now centers around a single **Stop** action. When the last session using a connection is stopped, Runicorn also cleans up the underlying SSH connection automatically.

---

## Idle shutdown

Remote-mode viewers can auto-stop after an idle timeout. This matters most when you start remote sessions that should not stay open forever on shared servers.

---

## Best practices

!!! tip "Prefer SSH keys when possible"

    Key-based auth is still the smoothest option for repeated use.

!!! tip "Install Runicorn in the environment you actually train with"

    The environment picker can only launch a remote viewer where Runicorn is available.

!!! tip "Reuse saved server profiles"

    Save the host once, then vary profiles for different remote roots or environments.

!!! tip "Treat host key warnings seriously"

    If a familiar host suddenly shows a changed key, verify it before accepting.

---

## Troubleshooting

### Authentication failed

Check the username, auth method, key path, or password first. If password auth fails, fix the credentials rather than expecting an automatic backend switch.

### No environments found

Make sure the target Python environment has Runicorn installed and is accessible over SSH.

### Session becomes degraded or reconnecting

This usually means the remote process or tunnel hit a transient issue. Wait for automatic recovery first. If the state stays degraded, stop the session and start it again.

### Host key confirmation keeps reappearing

Open the security drawer, inspect known-host entries, and remove stale records if the host really changed.

---

## Remote Viewer vs the old sync mindset

| Topic | Current Remote Viewer | Old sync-style workflow |
|-------|-----------------------|-------------------------|
| Primary model | SSH tunnel to remote viewer | Copy run files around |
| Startup | Connect and start | Sync first, browse later |
| Storage | Remote data stays remote | Local mirror required |
| Recovery | Health monitor and reconnect states | Usually manual retry |
| Security | Host key confirmation and saved connections | External to the workflow |

---

## Next steps

- [Desktop App](../reference/desktop-app.md)
- [Remote Workflow Tutorial](../tutorials/remote-workflow.md)
- [Web UI Overview](../ui/overview.md)
- [Troubleshooting](../reference/troubleshooting.md)

---

<div class="rn-page-nav">
  <a href="../ui/overview.md">Web UI Overview -></a> |
  <a href="../tutorials/remote-workflow.md">Remote Workflow Tutorial -></a>
</div>
