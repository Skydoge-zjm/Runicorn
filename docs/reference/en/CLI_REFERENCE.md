[English](CLI_REFERENCE.md) | [简体中文](../zh/CLI_REFERENCE.md)

---

# Runicorn CLI Reference

**Document Type**: Reference  
**Version**: v0.6.0  
**Last Updated**: 2026-01-15

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
| `export` | Export runs to .tar.gz archive | `runicorn export --out backup.tar.gz` |
| `import` | Import runs from archive | `runicorn import --archive backup.tar.gz` |
| `export-data` | Export run metrics to CSV/Excel | `runicorn export-data --run-id ID --format csv` |
| `manage` | Manage experiments (tag, search, delete, cleanup) | `runicorn manage --action search` |
| `rate-limit` | Manage API rate limits | `runicorn rate-limit --action show` |
| `delete` | Permanently delete runs and orphaned assets | `runicorn delete --run-id ID` |

---

## `runicorn viewer` - Start Web Viewer

Start the Runicorn web viewer server.

### Usage

```bash
runicorn viewer [OPTIONS]
```

### Options

#### `--storage PATH`
- **Description**: Storage root directory
- **Default**: Uses `RUNICORN_DIR` env var, global config, or legacy `./.runicorn`
- **Example**: `runicorn viewer --storage /data/experiments`

#### `--host TEXT`
- **Description**: Bind host address
- **Default**: `127.0.0.1`
- **Example**: `runicorn viewer --host 0.0.0.0`

#### `--port INTEGER`
- **Description**: Listen port
- **Default**: `23300`
- **Example**: `runicorn viewer --port 8080`

#### `--reload`
- **Description**: Enable auto-reload (development only)
- **Example**: `runicorn viewer --reload`

#### `--remote-mode` ⭐ v0.5.0
- **Description**: Start in remote mode (bind to 127.0.0.1, enable auto-shutdown)
- **Example**: `runicorn viewer --remote-mode --port 45342`

#### `--log-level TEXT`
- **Description**: Log level
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- **Default**: `INFO`
- **Example**: `runicorn viewer --log-level DEBUG`

### Examples

```bash
# Basic start
runicorn viewer

# Custom port and storage
runicorn viewer --port 8080 --storage /data/ml

# Debug mode
runicorn viewer --log-level DEBUG

# LAN sharing (⚠️ security warning)
runicorn viewer --host 0.0.0.0
```

---

## `runicorn config` - Configuration Management

### Usage

```bash
runicorn config [OPTIONS]
```

### Options

#### `--show`
Display current configuration (default if no other option is given).

```bash
runicorn config --show
```

#### `--set-user-root PATH`
Set the per-user root directory for all projects.

```bash
runicorn config --set-user-root /data/experiments
```

### Examples

```bash
# Show current config
runicorn config --show

# Set storage root
runicorn config --set-user-root ~/my_experiments
```

---

## `runicorn export` - Export Runs

Export runs into a `.tar.gz` archive for offline transfer.

### Usage

```bash
runicorn export [OPTIONS]
```

### Options

- `--storage PATH`: Storage root directory (default: from config or `RUNICORN_DIR`)
- `--project TEXT`: Filter by project name
- `--name TEXT`: Filter by experiment name
- `--run-id TEXT`: Export specific run ID (can be specified multiple times)
- `--out PATH`: Output archive path (default: `runicorn_export_<timestamp>.tar.gz`)

### Examples

```bash
# Export all runs
runicorn export --out backup.tar.gz

# Export specific project
runicorn export --project training --out training_backup.tar.gz

# Export specific runs
runicorn export --run-id 20260115_120000_abc123 --run-id 20260115_130000_def456

# Export from custom storage
runicorn export --storage /data/ml --out archive.tar.gz
```

---

## `runicorn import` - Import Runs

Import runs from a `.zip` or `.tar.gz` archive into storage.

### Usage

```bash
runicorn import --archive FILE [OPTIONS]
```

### Options

- `--storage PATH`: Target storage root (default: from config or `RUNICORN_DIR`)
- `--archive PATH`: **(Required)** Path to the `.zip` or `.tar.gz` archive to import

### Examples

```bash
# Import archive
runicorn import --archive backup.tar.gz

# Import to specific storage
runicorn import --archive backup.zip --storage /data/experiments
```

---

## `runicorn export-data` - Export Metrics

Export run metrics to CSV, Excel, Markdown, or HTML format.

### Usage

```bash
runicorn export-data --run-id ID [OPTIONS]
```

### Options

- `--storage PATH`: Storage root directory
- `--run-id TEXT`: **(Required)** Run ID to export
- `--format TEXT`: Export format: `csv` (default), `excel`, `markdown`, `html`
- `--output PATH`: Output file path (default: auto-generated)

### Examples

```bash
# Export as CSV (stdout)
runicorn export-data --run-id 20260115_120000_abc123

# Export as Excel
runicorn export-data --run-id 20260115_120000_abc123 --format excel --output results.xlsx

# Export as HTML report
runicorn export-data --run-id 20260115_120000_abc123 --format html --output report.html
```

---

## `runicorn manage` - Manage Experiments

Tag, search, delete, or clean up experiments.

### Usage

```bash
runicorn manage --action ACTION [OPTIONS]
```

### Actions

#### `--action tag`
Add tags to an experiment.

```bash
runicorn manage --action tag --run-id ID --tags "baseline,v2"
```

#### `--action search`
Search experiments by project, tags, or text.

```bash
runicorn manage --action search --project vision --tags "baseline"
runicorn manage --action search --text "resnet"
```

#### `--action delete`
Delete a specific experiment.

```bash
runicorn manage --action delete --run-id ID
```

#### `--action cleanup`
Clean up old experiments.

```bash
# Preview cleanup (dry run)
runicorn manage --action cleanup --days 30 --dry-run

# Actually clean up
runicorn manage --action cleanup --days 90
```

### Options

- `--storage PATH`: Storage root directory
- `--run-id TEXT`: Run ID (for tag/delete actions)
- `--tags TEXT`: Comma-separated tags (for tag/search actions)
- `--project TEXT`: Filter by project (for search action)
- `--text TEXT`: Search text (for search action)
- `--days INTEGER`: Days threshold for cleanup (default: 30)
- `--dry-run`: Preview cleanup without deleting

---

## `runicorn rate-limit` - Manage API Rate Limits

Manage Viewer API rate limiting configuration.

### Usage

```bash
runicorn rate-limit --action ACTION [OPTIONS]
```

### Actions

| Action | Description |
|--------|-------------|
| `show` | Show full rate limit config (JSON) |
| `list` | List all configured limits |
| `get` | Get limit for specific endpoint |
| `set` | Set limit for an endpoint |
| `remove` | Remove limit for an endpoint |
| `settings` | Update global settings |
| `reset` | Reset to default configuration |
| `validate` | Validate configuration |

### Examples

```bash
# Show config
runicorn rate-limit --action show

# Set limit for an endpoint
runicorn rate-limit --action set --endpoint /api/remote/connect --max-requests 5 --window 60

# Enable rate limiting
runicorn rate-limit --action settings --enable

# Validate config
runicorn rate-limit --action validate
```

---

## `runicorn delete` - Delete Runs with Assets

Permanently delete runs and clean up orphaned assets (blobs).

### Usage

```bash
runicorn delete --run-id ID [OPTIONS]
```

### Options

- `--storage PATH`: Storage root directory
- `--run-id TEXT`: **(Required)** Run ID to delete (can be specified multiple times)
- `--dry-run`: Preview deletion without actually deleting
- `--force`: Skip confirmation prompt

### Examples

```bash
# Preview deletion
runicorn delete --run-id 20260115_120000_abc123 --dry-run

# Delete with confirmation
runicorn delete --run-id 20260115_120000_abc123

# Force delete multiple runs
runicorn delete --run-id run1 --run-id run2 --force
```

---

## Environment Variables

| Variable | Affects | Example |
|----------|---------|---------|
| `RUNICORN_DIR` | `--storage` for all commands | `/data/experiments` |
| `RUNICORN_USER_ROOT_DIR` | Global storage root | `/data/experiments` |
| `RUNICORN_SSH_PATH` | SSH binary path (v0.6.0) | `/usr/local/bin/ssh` |
| `EDITOR` | Config editing | `vim` |

**Usage**:
```bash
# Linux/macOS
export RUNICORN_DIR=/data/ml
runicorn viewer

# Windows PowerShell
$env:RUNICORN_DIR="E:\ML"
runicorn viewer
```

---

## Common Scenarios

### First-time Setup

```bash
runicorn config --set-user-root ~/my_experiments
runicorn viewer
```

### Remote Server Usage

```bash
# On remote server
runicorn viewer --remote-mode

# On local machine (SSH tunnel)
ssh -L 23300:localhost:23300 user@remote-server

# Access via browser
# http://localhost:23300
```

### Data Migration

```bash
# Old server
runicorn export --out backup.tar.gz

# Transfer to new server
scp backup.tar.gz user@new-server:/tmp/

# New server
runicorn import --archive /tmp/backup.tar.gz
```

### Periodic Cleanup

```bash
# Preview what would be deleted
runicorn manage --action cleanup --days 90 --dry-run

# Clean up old experiments
runicorn manage --action cleanup --days 90
```

---

## Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `0` | Success | Command executed successfully |
| `1` | General error | Command failed |

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
