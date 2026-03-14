# Command Line Interface

Runicorn ships with a CLI for starting the viewer, managing storage, exporting data, and handling run cleanup.

!!! info "Need the exact current flags?"

    See [CLI Reference](../reference/cli-reference.md). This overview focuses on common workflows.

---

## Install

```bash
pip install -U runicorn
runicorn --help
runicorn --version
```

---

## Main Commands

| Command | What it is for |
|---------|----------------|
| `viewer` | Start the local web viewer and API |
| `config` | Inspect or change the default storage root |
| `export` | Export one or more runs into an archive |
| `import` | Import a `.zip` or `.tar.gz` archive |
| `export-data` | Export run metrics as CSV, Excel, Markdown, or HTML |
| `manage` | Tag, search, delete, or clean up experiments |
| `rate-limit` | Inspect and change API rate-limit settings |
| `delete` | Permanently delete runs and orphaned assets |

---

## Common Workflows

### Start the Viewer

```bash
runicorn viewer
```

Open [http://127.0.0.1:23300](http://127.0.0.1:23300).

Use a custom bind address only when you really need it:

```bash
runicorn viewer --host 0.0.0.0 --port 8000
```

### Set a Default Storage Root

```bash
runicorn config --show
runicorn config --set-user-root "E:\RunicornData"
```

Storage resolution order:

1. `rn.init(storage=...)`
2. `RUNICORN_DIR`
3. `runicorn config --set-user-root ...`
4. `./.runicorn`

### Export and Import Runs

```bash
runicorn export --project cv --out exports/cv_runs.tar.gz
runicorn import --archive exports/cv_runs.tar.gz
```

### Export Metrics for Reports

```bash
runicorn export-data --run-id 20260115_100000_abc123 --format csv
runicorn export-data --run-id 20260115_100000_abc123 --format html --output report.html
```

### Clean Up Old or Unwanted Runs

Preview first:

```bash
runicorn manage --action cleanup --days 30 --dry-run
runicorn delete --run-id 20260115_100000_abc123 --dry-run
```

Then execute:

```bash
runicorn delete --run-id 20260115_100000_abc123 --force
```

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `RUNICORN_DIR` | Override the default storage root |
| `RUNICORN_DISABLE_MODERN_STORAGE` | Disable the SQLite-backed storage path |
| `RUNICORN_IDLE_TIMEOUT` | Remote-mode viewer idle shutdown timeout |

Example:

```powershell
$env:RUNICORN_DIR = "E:\RunicornData"
runicorn viewer
```

---

## Troubleshooting

### Command Not Found

```bash
python -m pip install -U runicorn
python -m runicorn.cli viewer
```

### Port Already in Use

```bash
runicorn viewer --port 8080
```

### Need the Exact Option List?

Use either:

- [CLI Reference](../reference/cli-reference.md)
- `runicorn <command> --help`

---

## Next Steps

- [CLI Common Workflows](common-workflows.md)
- [Python SDK Overview](../sdk/overview.md)
- [Web UI Overview](../ui/overview.md)
- [FAQ](../reference/faq.md)
