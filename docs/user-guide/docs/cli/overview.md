# Command Line Interface

Runicorn provides a powerful CLI for managing experiments, artifacts, and configuration.

---

## Installation

The CLI is automatically installed with Runicorn:

```bash
pip install runicorn
```

Verify installation:

```bash
runicorn --help
```

---

## Available Commands

| Command | Description | Documentation |
|---------|-------------|---------------|
| `viewer` | Start the web viewer | [📖](viewer.md) |
| `config` | Manage configuration | [📖](config.md) |
| `export` | Export experiments | [📖](export-import.md#export) |
| `import` | Import experiments | [📖](export-import.md#import) |
| `artifacts` | Manage artifacts | [📖](artifacts.md) |
| `export-data` | Export metrics to CSV/Excel | [📖](export-import.md#export-data) |
| `manage` | Advanced experiment management | [📖](overview.md#manage-command) |
| `rate-limit` | Configure rate limits | [📖](overview.md#rate-limit-command) |

---

## Quick Reference

### Start Viewer

```bash
# Default (port 23300)
runicorn viewer

# Custom host and port
runicorn viewer --host 0.0.0.0 --port 8000

# With auto-reload (development)
runicorn viewer --reload
```

### Configuration

```bash
# Show current config
runicorn config --show

# Set storage root
runicorn config --set-user-root "E:\RunicornData"
```

### Export/Import

```bash
# Export all experiments
runicorn export --out experiments.tar.gz

# Export specific project
runicorn export --project image_classification --out exports/images.tar.gz

# Import archive
runicorn import --archive experiments.tar.gz
```

### Artifacts

```bash
# List all artifacts
runicorn artifacts --action list

# List versions
runicorn artifacts --action versions --name resnet50-model

# Get artifact info
runicorn artifacts --action info --name resnet50-model --version 3

# Storage statistics
runicorn artifacts --action stats
```

---

## Common Workflows

### Workflow 1: Setup New Machine

```bash
# Install Runicorn
pip install runicorn

# Configure storage
runicorn config --set-user-root "E:\MLData\Runicorn"

# Verify
runicorn config --show

# Start viewer
runicorn viewer
```

### Workflow 2: Backup Experiments

```bash
# Export all experiments from a project
runicorn export \
  --project image_classification \
  --out backups/image_classification_2025-10-14.tar.gz

# Verify export
ls -lh backups/

# Copy to backup drive
cp backups/*.tar.gz /mnt/backup/
```

### Workflow 3: Transfer Between Machines

**On Machine A** (export):
```bash
runicorn export \
  --project production_models \
  --out transfer.tar.gz
```

**Transfer file** (USB, network, etc.):
```bash
scp transfer.tar.gz user@machine-b:/home/user/
```

**On Machine B** (import):
```bash
runicorn import --archive transfer.tar.gz

# Verify
runicorn viewer
# Check experiments appeared
```

---

## Command Options

### Global Options

Available for all commands:

| Option | Description |
|--------|-------------|
| `--help` | Show help message |
| `--storage PATH` | Override storage root |

**Example**:
```bash
# Use custom storage for this command only
runicorn viewer --storage "D:\TempStorage"

# Show help for specific command
runicorn artifacts --help
```

### Storage Override

The `--storage` option temporarily overrides the configured storage root:

```bash
# Normal: Uses configured storage
runicorn viewer

# Override: Uses specified storage
runicorn viewer --storage "E:\OtherData"

# Export from different storage
runicorn export --storage "D:\OldData" --out old_experiments.tar.gz
```

---

## Tips & Tricks

### Tip 1: Create Aliases

**Bash/Linux**:
```bash
# Add to ~/.bashrc or ~/.zshrc
alias rv='runicorn viewer'
alias rconfig='runicorn config --show'
alias rexport='runicorn export --out'

# Usage
rv  # Start viewer
rconfig  # Show config
```

**PowerShell/Windows**:
```powershell
# Add to $PROFILE
function rv { runicorn viewer }
function rconfig { runicorn config --show }

# Usage
rv  # Start viewer
```

### Tip 2: Quick Stats

```bash
# One-liner to see artifact stats
runicorn artifacts --action stats | grep -E "Total|Dedup"
```

### Tip 3: Scheduled Exports

**Linux/Mac** (cron):
```bash
# Add to crontab: Export every day at 2 AM
0 2 * * * runicorn export --out /backups/daily_$(date +\%Y\%m\%d).tar.gz
```

**Windows** (Task Scheduler):
```powershell
# Create scheduled task
$action = New-ScheduledTaskAction -Execute "runicorn" -Argument "export --out E:\Backups\daily.tar.gz"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "RunicornBackup"
```

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `RUNICORN_DIR` | Default storage root | `E:\RunicornData` |
| `RUNICORN_DISABLE_MODERN_STORAGE` | Disable SQLite backend | `1` |

**Usage**:

```bash
# Linux/Mac
export RUNICORN_DIR="/data/runicorn"
runicorn viewer

# Windows (PowerShell)
$env:RUNICORN_DIR = "E:\RunicornData"
runicorn viewer

# Windows (CMD)
set RUNICORN_DIR=E:\RunicornData
runicorn viewer
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Invalid arguments |

**Example** (script usage):
```bash
#!/bin/bash

runicorn export --project demo --out demo.tar.gz

if [ $? -eq 0 ]; then
    echo "✓ Export successful"
    # Continue with backup
    cp demo.tar.gz /backups/
else
    echo "✗ Export failed"
    exit 1
fi
```

---

## Troubleshooting

### Command Not Found

```bash
runicorn: command not found
```

**Solution**:
```bash
# Ensure Runicorn is installed
pip list | grep runicorn

# If not installed
pip install runicorn

# If installed but not in PATH (use python -m)
python -m runicorn.cli viewer
```

### Permission Denied

```bash
Error: Permission denied: 'E:\RunicornData'
```

**Solution**:
1. Check directory exists and is writable
2. Create directory: `mkdir E:\RunicornData`
3. Check permissions: `icacls E:\RunicornData` (Windows) or `ls -la` (Linux)

### Port Already in Use

```bash
Error: Address already in use
```

**Solution**:
```bash
# Use different port
runicorn viewer --port 8080

# Or kill process using port 23300
# Windows
netstat -ano | findstr :23300
taskkill /PID <PID> /F

# Linux
lsof -i :23300
kill -9 <PID>
```

---

## Next Steps

- [📺 Viewer Commands](viewer.md) - Detailed viewer options
- [⚙️ Config Commands](config.md) - Configuration management
- [📦 Artifacts Management](artifacts.md) - CLI artifact operations
- [📤 Export & Import](export-import.md) - Data portability

---

<div align="center">
  <p><a href="viewer.md">Learn More About Viewer Commands →</a></p>
</div>

