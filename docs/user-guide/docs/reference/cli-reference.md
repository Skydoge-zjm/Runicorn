# CLI Reference

This page mirrors the current `runicorn --help` output so the command list,
defaults, and option names stay aligned with the shipped CLI.

## Commands

| Command | Purpose |
|---------|---------|
| `viewer` | Start the local read-only viewer API |
| `config` | Manage Runicorn user configuration |
| `export` | Export runs into a .tar.gz for offline transfer |
| `import` | Import an archive (.zip/.tar.gz) of runs into storage |
| `export-data` | Export run metrics to CSV or Excel |
| `manage` | Manage experiments (tag, search, delete) |
| `rate-limit` | Manage API rate limits |
| `delete` | Permanently delete runs and their orphaned assets |

## Top-Level Help

```text
usage: runicorn [-h] [--version]
                {viewer,config,export,import,export-data,manage,rate-limit,delete} ...

Runicorn CLI

positional arguments:
  {viewer,config,export,import,export-data,manage,rate-limit,delete}
    viewer              Start the local read-only viewer API
    config              Manage Runicorn user configuration
    export              Export runs into a .tar.gz for offline transfer
    import              Import an archive (.zip/.tar.gz) of runs into storage
    export-data         Export run metrics to CSV or Excel
    manage              Manage experiments (tag, search, delete)
    rate-limit          Manage API rate limits
    delete              Permanently delete runs and their orphaned assets

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
```

## `viewer`

Start the local read-only viewer API

```text
usage: runicorn viewer [-h] [--storage STORAGE] [--host HOST] [--port PORT]
                       [--reload] [--remote-mode]
                       [--idle-timeout IDLE_TIMEOUT]
                       [--log-level {DEBUG,INFO,WARNING,ERROR}]

options:
  -h, --help            show this help message and exit
  --storage STORAGE     Storage root directory; if omitted, uses global config
                        or legacy ./.runicorn
  --host HOST           Host to bind (default: 127.0.0.1)
  --port PORT           Port to bind (default: 23300)
  --reload              Enable auto-reload (dev only)
  --remote-mode         Remote mode: bind only to 127.0.0.1 and enable auto-
                        shutdown
  --idle-timeout IDLE_TIMEOUT
                        Idle timeout in seconds for remote-mode auto-shutdown
                        (default: 1800)
  --log-level {DEBUG,INFO,WARNING,ERROR}
                        Logging level (default: INFO)
```

## `config`

Manage Runicorn user configuration

```text
usage: runicorn config [-h] [--show] [--set-user-root USER_ROOT]

options:
  -h, --help            show this help message and exit
  --show                Show current configuration
  --set-user-root USER_ROOT
                        Set the per-user root directory for all projects
```

## `export`

Export runs into a .tar.gz for offline transfer

```text
usage: runicorn export [-h] [--storage STORAGE] [--project PROJECT]
                       [--name NAME] [--run-id RUN_IDS] [--out OUT_PATH]

options:
  -h, --help         show this help message and exit
  --storage STORAGE  Storage root directory; if omitted, uses global config or
                     legacy ./.runicorn
  --project PROJECT  Filter by project (new layout)
  --name NAME        Filter by experiment name (new layout)
  --run-id RUN_IDS   Export only specific run id(s); can be set multiple times
  --out OUT_PATH     Output archive path (.tar.gz). Default:
                     runicorn_export_<ts>.tar.gz
```

## `import`

Import an archive (.zip/.tar.gz) of runs into storage

```text
usage: runicorn import [-h] [--storage STORAGE] --archive ARCHIVE

options:
  -h, --help         show this help message and exit
  --storage STORAGE  Target storage root; if omitted, uses global config or
                     legacy ./.runicorn
  --archive ARCHIVE  Path to the .zip or .tar.gz archive to import
```

## `export-data`

Export run metrics to CSV or Excel

```text
usage: runicorn export-data [-h] [--storage STORAGE] --run-id RUN_ID
                            [--format {csv,excel,markdown,html}]
                            [--output OUTPUT]

options:
  -h, --help            show this help message and exit
  --storage STORAGE     Storage root directory
  --run-id RUN_ID       Run ID to export
  --format {csv,excel,markdown,html}
                        Export format
  --output OUTPUT       Output file path (default: auto-generated)
```

## `manage`

Manage experiments (tag, search, delete)

```text
usage: runicorn manage [-h] [--storage STORAGE]
                       --action {tag,search,delete,cleanup} [--run-id RUN_ID]
                       [--tags TAGS] [--project PROJECT] [--text TEXT]
                       [--days DAYS] [--dry-run]

options:
  -h, --help            show this help message and exit
  --storage STORAGE     Storage root directory
  --action {tag,search,delete,cleanup}
                        Management action
  --run-id RUN_ID       Run ID for tagging
  --tags TAGS           Comma-separated tags
  --project PROJECT     Filter by project
  --text TEXT           Search text
  --days DAYS           Days for cleanup (default: 30)
  --dry-run             Preview cleanup without deleting
```

## `rate-limit`

Manage API rate limits

```text
usage: runicorn rate-limit [-h]
                           [--action {show,list,get,set,remove,settings,reset,validate}]
                           [--endpoint ENDPOINT] [--max-requests MAX_REQUESTS]
                           [--window WINDOW] [--burst BURST]
                           [--description DESCRIPTION] [--enable] [--disable]
                           [--log-violations] [--no-log-violations]
                           [--whitelist-localhost] [--no-whitelist-localhost]

options:
  -h, --help            show this help message and exit
  --action {show,list,get,set,remove,settings,reset,validate}
                        Rate limit action (default: show)
  --endpoint ENDPOINT   API endpoint path (e.g., /api/remote/connect)
  --max-requests MAX_REQUESTS
                        Maximum requests allowed
  --window WINDOW       Time window in seconds (default: 60)
  --burst BURST         Burst size limit
  --description DESCRIPTION
                        Description of the limit
  --enable              Enable rate limiting
  --disable             Disable rate limiting
  --log-violations      Log rate limit violations
  --no-log-violations   Don't log rate limit violations
  --whitelist-localhost
                        Whitelist localhost
  --no-whitelist-localhost
                        Don't whitelist localhost
```

## `delete`

Permanently delete runs and their orphaned assets

```text
usage: runicorn delete [-h] [--storage STORAGE] [--run-id RUN_IDS] [--dry-run]
                       [--force]

options:
  -h, --help         show this help message and exit
  --storage STORAGE  Storage root directory
  --run-id RUN_IDS   Run ID to delete (can specify multiple)
  --dry-run          Preview deletion without actually deleting
  --force            Skip confirmation prompt
```
