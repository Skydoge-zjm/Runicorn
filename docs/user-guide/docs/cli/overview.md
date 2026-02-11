# Command Line Interface

Runicorn provides a powerful CLI for managing experiments, assets, and configuration.

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

| Command | Description |
|---------|-------------|
| `viewer` | Start the web viewer |
| `config` | Manage configuration |
| `export` | Export experiments |
| `import` | Import experiments |
| `delete` | Permanently delete runs and orphaned assets |
| `export-data` | Export metrics to CSV/Excel |
| `manage` | Advanced experiment management |
| `rate-limit` | Configure rate limits |

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

### Delete Runs

```bash
# Preview deletion (dry run)
runicorn delete --run-id 20260115_100000_abc123 --dry-run

# Delete a single run permanently
runicorn delete --run-id 20260115_100000_abc123 --force

# Delete multiple runs
runicorn delete --run-id run1 --run-id run2 --force
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
runicorn delete --help
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

=== "Bash / Zsh"

    ```bash
    # Add to ~/.bashrc or ~/.zshrc
    alias rv='runicorn viewer'
    alias rconfig='runicorn config --show'
    alias rexport='runicorn export --out'

    # Usage
    rv  # Start viewer
    rconfig  # Show config
    ```

=== "PowerShell"

    ```powershell
    # Add to $PROFILE
    function rv { runicorn viewer }
    function rconfig { runicorn config --show }

    # Usage
    rv  # Start viewer
    ```

### Tip 2: Quick Cleanup

```bash
# Preview cleanup of experiments older than 30 days
runicorn manage --action cleanup --days 30 --dry-run
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

=== "Linux / macOS"

    ```bash
    export RUNICORN_DIR="/data/runicorn"
    runicorn viewer
    ```

=== "PowerShell"

    ```powershell
    $env:RUNICORN_DIR = "E:\RunicornData"
    runicorn viewer
    ```

=== "CMD"

    ```cmd
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

- More CLI documentation coming soon
- For now, use `runicorn --help` to see all available commands
- See [Python SDK](../sdk/overview.md) for programmatic usage

---

<div class="rn-page-nav">
  <a href="../sdk/overview.md">Explore Python SDK →</a>
</div>

