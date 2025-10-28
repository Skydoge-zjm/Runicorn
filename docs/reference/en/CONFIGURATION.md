[English](CONFIGURATION.md) | [简体中文](../zh/CONFIGURATION.md)

---

# Runicorn Configuration Reference

**Document Type**: Reference  
**Version**: v0.5.0  
**Last Updated**: 2025-10-25

---

## Overview

Runicorn supports configuration via config files and environment variables. Config file locations:

- **Linux/macOS**: `~/.config/runicorn/config.yaml`
- **Windows**: `%APPDATA%\Runicorn\config.yaml`

---

## Configuration File Format

```yaml
# Runicorn Configuration v0.5.0

storage:
  user_root_dir: ~/RunicornData
  use_database: true
  database_path: ${user_root_dir}/runicorn.db
  auto_backup: true
  backup_interval_hours: 24
  max_backups: 7

viewer:
  host: 127.0.0.1
  port: 23300
  auto_open_browser: true
  log_level: INFO
  cors_origins:
    - http://localhost:3000

# Remote Viewer Configuration (v0.5.0)
remote:
  ssh_timeout: 30
  ssh_keepalive_interval: 60
  viewer_startup_timeout: 60
  health_check_interval: 30
  auto_port_range:
    start: 8081
    end: 8199
  max_connections: 5
  log_level: INFO
  cleanup_temp_files: true
  viewer_log_retention_days: 7

artifacts:
  enable_deduplication: true
  dedup_pool_path: ${user_root_dir}/artifacts/.dedup
  max_dedup_file_size_mb: 1024
  hardlink_fallback_to_copy: true

performance:
  db_pool_size: 10
  query_cache_ttl: 60
  max_concurrent_requests: 100
  websocket_timeout: 300

security:
  enable_rate_limit: true
  rate_limit_per_minute: 60
  allowed_hosts: []
  check_ssh_key_permissions: true

ui:
  default_language: en
  default_theme: light
  experiments_per_page: 50
  chart_refresh_interval: 5
  max_log_lines: 1000

logging:
  log_dir: ~/.config/runicorn/logs
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  max_file_size_mb: 10
  backup_count: 5
  console_output: true

experiments:
  auto_capture_env: true
  capture_git_info: true
  capture_system_info: true
  status_timeout_hours: 48
  auto_mark_zombie: true
```

---

## Key Configuration Options

### Remote Viewer (v0.5.0)

#### `ssh_timeout`
- **Type**: Integer (seconds)
- **Default**: `30`
- **Description**: SSH connection timeout
- **Recommended**: Increase to `60` for unstable networks

#### `viewer_startup_timeout`
- **Type**: Integer (seconds)
- **Default**: `60`
- **Description**: Maximum time to wait for remote Viewer startup

#### `health_check_interval`
- **Type**: Integer (seconds)
- **Default**: `30`
- **Description**: Interval for health checks

#### `auto_port_range`
- **Type**: Object
- **Default**: `{start: 8081, end: 8199}`
- **Description**: Port range for automatic local port selection

#### `max_connections`
- **Type**: Integer
- **Default**: `5`
- **Description**: Maximum concurrent remote connections
- **Range**: `1-10`

---

## Environment Variables

| Variable | Config Key | Example |
|----------|-----------|---------|
| `RUNICORN_USER_ROOT_DIR` | `storage.user_root_dir` | `/data/runicorn` |
| `RUNICORN_VIEWER_PORT` | `viewer.port` | `8080` |
| `RUNICORN_LOG_LEVEL` | `viewer.log_level` | `DEBUG` |
| `RUNICORN_REMOTE_TIMEOUT` | `remote.ssh_timeout` | `60` |

**Usage**:
```bash
# Linux/macOS
export RUNICORN_USER_ROOT_DIR=/data/experiments
runicorn viewer

# Windows PowerShell
$env:RUNICORN_USER_ROOT_DIR="E:\Experiments"
runicorn viewer
```

---

## Configuration Priority

Priority (highest to lowest):
1. **Command-line arguments**: `runicorn viewer --port 8080`
2. **Environment variables**: `RUNICORN_VIEWER_PORT=8080`
3. **Config file**: `config.yaml`
4. **Defaults**: Built-in defaults

---

## Example Configurations

### Development
```yaml
storage:
  user_root_dir: ./dev_data

viewer:
  log_level: DEBUG

remote:
  log_level: DEBUG
  health_check_interval: 10
```

### Production
```yaml
storage:
  user_root_dir: /data/runicorn
  auto_backup: true

viewer:
  host: 0.0.0.0  # Use with caution
  log_level: WARNING

remote:
  max_connections: 10
  viewer_startup_timeout: 120

security:
  enable_rate_limit: true
```

---

## Configuration Commands

```bash
# Show current config
runicorn config --show

# Edit config file
runicorn config --edit

# Reset to defaults
runicorn config --reset

# Validate config
runicorn config --validate
```

---

## Troubleshooting

### Config Not Taking Effect
1. Check file path is correct
2. Validate YAML syntax
3. Check environment variables
4. Use `--validate` command

### Port Conflict
```yaml
viewer:
  port: 23301  # Change port
```

### Remote Connection Timeout
```yaml
remote:
  ssh_timeout: 120
  viewer_startup_timeout: 180
```

---

## Related Documentation

- **[CLI Reference](CLI_REFERENCE.md)** - Command-line usage
- **[FAQ](FAQ.md)** - Common questions
- **[Deployment](../../architecture/en/DEPLOYMENT.md)** - Deployment config

---

**Back to**: [Reference Docs](README.md) | [Main Docs](../../README.md)


