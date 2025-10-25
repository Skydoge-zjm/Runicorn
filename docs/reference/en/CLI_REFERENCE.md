[English](CLI_REFERENCE.md) | [简体中文](../zh/CLI_REFERENCE.md)

---

# Runicorn CLI Reference

**Document Type**: Reference  
**Version**: v0.5.0  
**Last Updated**: 2025-10-25

---

## Overview

Runicorn provides a unified command-line interface (CLI) for managing experiments, launching viewer, and configuring the system.

```bash
runicorn --help
```

---

## Command Summary

| Command | Description | Example |
|---------|-------------|---------|
| `viewer` | Start web viewer | `runicorn viewer` |
| `config` | Manage configuration | `runicorn config --show` |
| `export` | Export experiment data | `runicorn export --format json` |
| `import` | Import experiment data | `runicorn import data.zip` |
| `clean` | Clean up data | `runicorn clean --zombie` |
| `version` | Show version info | `runicorn --version` |

---

## `runicorn viewer` - Start Web Viewer

Start the Runicorn web viewer server.

### Usage

```bash
runicorn viewer [OPTIONS]
```

### Options

#### `--host TEXT`
- **Description**: Bind host address
- **Default**: `127.0.0.1`
- **Example**: `runicorn viewer --host 0.0.0.0`

#### `--port INTEGER`
- **Description**: Listen port
- **Default**: `23300`
- **Range**: `1024-65535`
- **Example**: `runicorn viewer --port 8080`

#### `--storage-root PATH`
- **Description**: Data storage root directory
- **Default**: `~/RunicornData`
- **Example**: `runicorn viewer --storage-root /data/experiments`

#### `--no-open-browser`
- **Description**: Don't auto-open browser
- **Example**: `runicorn viewer --no-open-browser`

#### `--log-level TEXT`
- **Description**: Log level
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- **Default**: `INFO`
- **Example**: `runicorn viewer --log-level DEBUG`

#### `--remote-mode` ⭐ v0.5.0
- **Description**: Start in remote mode (usually auto-invoked)
- **Example**: `runicorn viewer --remote-mode --port 45342`

### Examples

```bash
# Basic start
runicorn viewer

# Custom port and storage
runicorn viewer --port 8080 --storage-root /data/ml

# Debug mode
runicorn viewer --log-level DEBUG --no-open-browser

# LAN sharing (⚠️ security warning)
runicorn viewer --host 0.0.0.0
```

---

## `runicorn config` - Configuration Management

### Usage

```bash
runicorn config [COMMAND] [OPTIONS]
```

### Commands

#### `--show`
Display current configuration
```bash
runicorn config --show
```

#### `--edit`
Open config file in editor
```bash
runicorn config --edit
```

#### `--set-user-root PATH`
Set user data root directory
```bash
runicorn config --set-user-root /data/experiments
```

#### `--reset`
Reset configuration to defaults
```bash
runicorn config --reset
```

#### `--validate`
Validate configuration file
```bash
runicorn config --validate
```

#### `--path`
Show config file path
```bash
runicorn config --path
```

---

## `runicorn export` - Export Data

Export experiment data to various formats.

### Usage

```bash
runicorn export [OPTIONS]
```

### Options

- `--format TEXT`: Export format (`json`, `csv`, `tensorboard`, `zip`)
- `--output PATH`: Output file path
- `--project TEXT`: Export specific project only
- `--run-id TEXT`: Export specific run only
- `--include-artifacts`: Include artifact files
- `--compress`: Compress output

### Examples

```bash
# Export all data (JSON)
runicorn export --format json --output all_experiments.json

# Export to CSV
runicorn export --format csv --project training --output results.csv

# Export to TensorBoard
runicorn export --format tensorboard --output ./tb_logs/

# Export with artifacts
runicorn export \
  --run-id 20251025_143022_a1b2c3 \
  --include-artifacts \
  --compress \
  --output backup.zip
```

---

## `runicorn import` - Import Data

Import experiment data from export files.

### Usage

```bash
runicorn import [FILE] [OPTIONS]
```

### Options

- `--merge`: Merge with existing data (skip conflicts)
- `--overwrite`: Overwrite existing data
- `--dry-run`: Preview import without executing

### Examples

```bash
# Import ZIP file
runicorn import experiment_backup.zip

# Import with overwrite
runicorn import data.json --overwrite

# Preview import
runicorn import data.zip --dry-run
```

---

## `runicorn clean` - Clean Up Data

Clean expired or unused data.

### Usage

```bash
runicorn clean [OPTIONS]
```

### Options

- `--zombie`: Clean zombie experiments (>48h running)
- `--temp`: Clean temporary files
- `--cache`: Clean cache files
- `--dedup`: Clean orphaned dedup files
- `--older-than DAYS`: Clean data older than specified days
- `--dry-run`: Preview cleanup
- `--force`: Force cleanup without confirmation

### Examples

```bash
# Clean zombie experiments
runicorn clean --zombie

# Clean all temp files
runicorn clean --temp --cache

# Clean old data (preview)
runicorn clean --older-than 30 --dry-run

# Force clean dedup pool
runicorn clean --dedup --force
```

---

## `runicorn version` - Version Info

Display version information and system status.

### Usage

```bash
runicorn --version
# or
runicorn version
```

### Example Output

```
Runicorn 0.5.0

Platform: Linux-5.15.0-x86_64
Python: 3.10.12
Storage: /home/user/RunicornData (42.3 GB used)
Database: V2 API enabled
Remote Viewer: Available
```

---

## Global Options

All commands support:

- `--help`: Show help
- `--version`: Show version
- `--quiet`: Quiet mode
- `--verbose`: Verbose mode

---

## Environment Variables

| Variable | Affects | Example |
|----------|---------|---------|
| `RUNICORN_USER_ROOT_DIR` | `--storage-root` | `/data/experiments` |
| `RUNICORN_VIEWER_PORT` | `--port` | `8080` |
| `RUNICORN_LOG_LEVEL` | `--log-level` | `DEBUG` |
| `EDITOR` | `config --edit` | `vim` |

**Usage**:
```bash
# Linux/macOS
export RUNICORN_USER_ROOT_DIR=/data/ml
runicorn viewer

# Windows PowerShell
$env:RUNICORN_USER_ROOT_DIR="E:\ML"
runicorn viewer
```

---

## Common Scenarios

### First-time Setup

```bash
runicorn --version
runicorn config --set-user-root ~/my_experiments
runicorn viewer
```

### Remote Server Usage

```bash
# On remote server
runicorn viewer --no-open-browser

# On local machine (SSH tunnel)
ssh -L 23300:localhost:23300 user@remote-server

# Access via browser
# http://localhost:23300
```

### Data Migration

```bash
# Old server
runicorn export --format zip --include-artifacts --output backup.zip

# Transfer to new server
scp backup.zip user@new-server:/tmp/

# New server
runicorn import /tmp/backup.zip
```

### Periodic Cleanup

```bash
#!/bin/bash
# cleanup.sh
runicorn clean --zombie --force
runicorn clean --temp --cache --force
runicorn clean --older-than 90 --dry-run

# Add to cron:
# 0 2 * * 0  /path/to/cleanup.sh
```

---

## Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `0` | Success | Command executed successfully |
| `1` | General error | Command failed |
| `2` | Config error | Invalid or missing config |
| `3` | Permission error | Insufficient permissions |
| `4` | Resource unavailable | Port occupied or path missing |

---

## Shell Aliases

### Bash/Zsh (~/.bashrc or ~/.zshrc)

```bash
alias rv='runicorn viewer'
alias rc='runicorn config'
alias rexp='runicorn export'
alias rimp='runicorn import'
```

### PowerShell (profile)

```powershell
Set-Alias rv 'runicorn viewer'
function rc { runicorn config $args }
```

---

## Shell Completion

### Bash

```bash
eval "$(_RUNICORN_COMPLETE=bash_source runicorn)"
```

### Zsh

```bash
eval "$(_RUNICORN_COMPLETE=zsh_source runicorn)"
```

---

## Troubleshooting

### Command Not Found

```bash
pip show runicorn
which runicorn  # Linux/macOS
where runicorn  # Windows
```

### Port Already in Use

```bash
# Linux/macOS
lsof -i :23300

# Windows
netstat -ano | findstr :23300

# Use different port
runicorn viewer --port 23301
```

### Permission Issues

```bash
# Check permissions
ls -la ~/.config/runicorn/

# Fix permissions
chmod 700 ~/.config/runicorn/
chmod 600 ~/.config/runicorn/config.yaml
```

---

## Related Documentation

- **[Configuration](CONFIGURATION.md)** - Config file reference
- **[API Reference](../../api/en/README.md)** - HTTP API docs
- **[User Guide](../../guides/en/QUICKSTART.md)** - Getting started

---

**Back to**: [Reference Docs](README.md) | [Main Docs](../../README.md)


