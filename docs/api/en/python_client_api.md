[English](python_client_api.md) | [简体中文](../zh/python_client_api.md)

---

# Python API Client - Programmatic Access

**Module**: Python API Client
**Package**: `runicorn.client`
**Utility Module**: `runicorn.client.utils`
**Version**: v0.7.2
**Last Updated**: 2026-03-28
**Description**: Programmatic access to the Runicorn Viewer REST API from Python.

---

## Overview

The current Python client is exposed from `runicorn.client`, not `runicorn.api`.

It is designed for:

- querying runs and path hierarchies
- fetching metrics for analysis
- exporting CSV/report artifacts
- controlling Remote Viewer sessions
- converting API responses into pandas DataFrames

`connect()` verifies `GET /api/health` when the client is created, so connection failures surface early.

---

## Installation

The client ships with the main Runicorn package:

```bash
pip install runicorn
```

If you want DataFrame helpers, install pandas separately:

```bash
pip install pandas
```

---

## Quick Start

```python
import runicorn.client as client_mod

with client_mod.connect("http://127.0.0.1:23300") as client:
    runs = client.list_runs_by_path(path="vision", exact=False)
    print(f"Matched runs: {len(runs)}")

    if runs:
        metrics = client.get_metrics(runs[0]["id"], downsample=500)
        print(metrics["columns"])
        print(metrics["rows"][:2])
```

---

## Core Client

### `connect()`

```python
import runicorn.client as client_mod

client = client_mod.connect(
    base_url="http://127.0.0.1:23300",
    timeout=30,
    max_retries=3,
)
```

Returns a `RunicornClient` instance.

### `RunicornClient`

You can also construct the client directly:

```python
from runicorn.client import RunicornClient

client = RunicornClient(
    base_url="http://127.0.0.1:23300",
    timeout=30,
    max_retries=3,
)
```

The client supports context-manager usage:

```python
import runicorn.client as client_mod

with client_mod.connect() as client:
    health = client.health_check()
    print(health["status"])
```

---

## Experiment Management

The Viewer UI and Python client now use **run** terminology. Older docs may still say "experiment", but the current public client methods are:

### `list_runs()`

```python
runs = client.list_runs()
```

Returns a list of run records such as `id`, `path`, `alias`, and `status`.

### `get_run(run_id)`

```python
run = client.get_run("20260328_120000_abcd12")
print(run["path"], run["status"])
```

### `list_paths(include_stats=False)`

```python
path_info = client.list_paths(include_stats=True)
print(path_info.keys())
```

This returns the path listing/tree payload exposed by `/api/paths`.

### `list_runs_by_path(path=None, exact=False)`

Use this instead of the removed `list_experiments(project=..., name=...)` pattern.

```python
vision_runs = client.list_runs_by_path(path="vision", exact=False)
baseline_runs = client.list_runs_by_path(path="vision/baseline", exact=True)
```

---

## Metrics Data

### `get_metrics(run_id, downsample=None)`

```python
metrics = client.get_metrics("20260328_120000_abcd12", downsample=1000)
```

The response shape is:

```python
{
    "columns": ["global_step", "loss", "acc"],
    "rows": [
        {"global_step": 1, "loss": 0.8, "acc": 0.52},
        {"global_step": 2, "loss": 0.6, "acc": 0.61},
    ],
    ...
}
```

Use `metrics["columns"]` and `metrics["rows"]`. Do not expect the old `metrics["metrics"]` structure.

### `export_csv(run_id)`

```python
csv_bytes = client.export_csv("20260328_120000_abcd12")
```

### `export_report(run_id, format="markdown")`

```python
report_bytes = client.export_report("20260328_120000_abcd12", format="html")
```

`format` currently supports `"markdown"` and `"html"`.

---

## Configuration And Health

### `get_config()`

```python
config = client.get_config()
```

### `set_user_root_dir(path)`

```python
updated = client.set_user_root_dir(r"E:\runs")
```

### `get_gpu_info()`

```python
gpu = client.get_gpu_info()
```

### `health_check()`

```python
health = client.health_check()
```

### `get_storage_stats()`

```python
stats = client.get_storage_stats()
```

### `check_status()`

```python
result = client.check_status()
```

---

## Remote API

Remote Viewer helpers are exposed under `client.remote`.

```python
import runicorn.client as client_mod

with client_mod.connect() as client:
    client.remote.connect(
        host="gpu-server",
        port=22,
        username="alice",
        private_key_path="C:/Users/alice/.ssh/id_ed25519",
    )

    session = client.remote.start_viewer(
        host="gpu-server",
        port=22,
        username="alice",
        remote_root="/data/runicorn",
        conda_env="runicorn_dev",
    )

    print(session)
```

Current remote helpers:

- `client.remote.connect(...)`
- `client.remote.disconnect(host, port=22, username=...)`
- `client.remote.list_sessions()`
- `client.remote.start_viewer(...)`
- `client.remote.stop_viewer(session_id)`
- `client.remote.list_viewer_sessions()`
- `client.remote.list_remote_storage_candidates(connection_id, conda_env="system", scan_root=None, max_depth=3)`
- `client.remote.get_remote_status()`
- `client.remote.confirm_host_key(...)`

Notes:

- `start_viewer()` currently expects `host`, `port`, `username`, and `remote_root`.
- `connection_id="user@host:port"` is still accepted for backward compatibility, but the preferred flow is explicit SSH parameters.
- If the server requests host-key confirmation, catch `HostKeyConfirmationRequiredError`, call `confirm_host_key(...)`, then retry the original operation.

---

## Utility Functions

Import helpers from `runicorn.client.utils`:

```python
import runicorn.client as client_mod
import runicorn.client.utils as client_utils

with client_mod.connect() as client:
    runs = client.list_runs()
    runs_df = client_utils.runs_to_dataframe(runs)

    if runs:
        metrics = client.get_metrics(runs[0]["id"])
        metrics_df = client_utils.metrics_to_dataframe(metrics)
```

Available helpers:

- `metrics_to_dataframe(metrics_data)`
- `runs_to_dataframe(runs)`
- `export_metrics_to_csv(client, run_id, output_path)`
- `compare_runs(client, run_ids, metric_name)`

Backward-compatibility note:

- `experiments_to_dataframe` is still available as an alias of `runs_to_dataframe`.

---

## Error Handling

The package exports these commonly used exceptions:

```python
from runicorn.client import (
    ConnectionError,
    NotFoundError,
    BadRequestError,
    ServerError,
    HostKeyConfirmationRequiredError,
)
```

Example:

```python
import runicorn.client as client_mod
from runicorn.client import ConnectionError, NotFoundError

try:
    with client_mod.connect() as client:
        run = client.get_run("missing-run")
except NotFoundError:
    print("Run not found")
except ConnectionError as exc:
    print(f"Viewer unavailable: {exc}")
```

---

## Notes

- Use `runicorn.client`, not the removed `runicorn.api` path.
- Use path-based filtering with `list_runs_by_path(...)` instead of the removed `project` / `name` filters.
- Treat metric payloads as `{columns, rows}` responses and convert them with `runicorn.client.utils` when needed.
