[English](API_INDEX.md) | [简体中文](../zh/API_INDEX.md)

---

# Complete API Index

**Version**: v0.7.1
**Total Endpoints**: REST API + Python Client
**Last Updated**: 2026-05-10

---

## 🐍 Python API Client

**New**: Programmatic Python access interface

| Component | Description | Docs |
|-----------|-------------|------|
| **RunicornClient** | Main client class | [📖](./python_client_api.md) |
| **Experiments API** | Experiment query and management | [📖](./python_client_api.md#experiment-management) |
| **Metrics API** | Metrics data access | [📖](./python_client_api.md#metrics-data) |
| **Remote API** | Remote Viewer control | [📖](./python_client_api.md#remote-api) |
| **Utils** | pandas DataFrame tools | [📖](./python_client_api.md#utility-functions) |

**Quick Example**:
```python
import runicorn.client as client_mod

with client_mod.connect() as client:
    runs = client.list_runs_by_path(path="vision")
    metrics = client.get_metrics(runs[0]["id"])
```

---

## 📑 REST API Endpoint List

### Runs API (Experiment Management)

| Method | Endpoint | Description | Docs |
|--------|----------|-------------|------|
| GET | `/api/runs` | List all runs | [📖](./runs_api.md#list-runs) |
| GET | `/api/runs/{run_id}` | Get run detail | [📖](./runs_api.md#get-run-detail) |
| POST | `/api/runs/soft-delete` | Soft delete runs | [📖](./runs_api.md#soft-delete-runs) |
| GET | `/api/recycle-bin` | List deleted runs | [📖](./runs_api.md#list-deleted-runs) |
| POST | `/api/recycle-bin/restore` | Restore deleted runs | [📖](./runs_api.md#restore-runs) |
| POST | `/api/recycle-bin/empty` | Permanently delete all | [📖](./runs_api.md#empty-recycle-bin) |

### Metrics API (Training Data)

| Method | Endpoint | Description | Docs |
|--------|----------|-------------|------|
| GET | `/api/runs/{run_id}/metrics` | Get time-based metrics (supports LTTB downsampling) | [📖](./metrics_api.md#get-metrics-time-based) |
| GET | `/api/runs/{run_id}/metrics_step` | Get step-based metrics (supports LTTB downsampling) | [📖](./metrics_api.md#get-step-metrics) |
| GET | `/api/metrics/cache/stats` | Get incremental cache statistics | [📖](./metrics_api.md#cache-statistics) |
| WS | `/api/runs/{run_id}/logs/ws` | Real-time log stream | [📖](./metrics_api.md#real-time-log-streaming) |

### Config API (Settings)

| Method | Endpoint | Description | Docs |
|--------|----------|-------------|------|
| GET | `/api/config` | Get configuration | [📖](./config_api.md#get-configuration) |
| POST | `/api/config/user_root_dir` | Set storage root | [📖](./config_api.md#set-user-root-directory) |
| GET | `/api/config/ssh_connections` | Get saved connections | [📖](./config_api.md#get-saved-ssh-connections) |
| POST | `/api/config/ssh_connections` | Save connection | [📖](./config_api.md#save-ssh-connection) |
| DELETE | `/api/config/ssh_connections/{key}` | Delete connection | [📖](./config_api.md#delete-ssh-connection) |
| GET | `/api/config/ssh_connections/{key}/details` | Get connection details | [📖](./config_api.md) |

### Remote Viewer API (Remote Access) 🆕

**Current entry point**: [remote_api.md](./remote_api.md)  
**Historical note**: [ssh_api.md](./ssh_api.md)

#### Connection Management

| Method | Endpoint | Description | Docs |
|--------|----------|-------------|------|
| POST | `/api/remote/connect` | Establish SSH connection | [📖](./remote_api.md#post-apiremoteconnect) |
| GET | `/api/remote/sessions` | List SSH sessions | [📖](./remote_api.md#get-apiremotesessions) |
| POST | `/api/remote/disconnect` | Disconnect session | [📖](./remote_api.md#post-apiremotedisconnect) |
| GET | `/api/remote/status` | Remote status | [📖](./remote_api.md#get-apiremotestatus) |

#### Host key and saved connections

| Method | Endpoint | Description | Docs |
|--------|----------|-------------|------|
| POST | `/api/remote/known-hosts/accept` | Accept host key | [📖](./remote_api.md) |
| GET | `/api/remote/known-hosts/list` | List known_hosts entries | [📖](./remote_api.md) |
| POST | `/api/remote/known-hosts/remove` | Remove known_hosts entry | [📖](./remote_api.md) |
| GET | `/api/remote/connections/saved` | Load masked saved connections | [📖](./remote_api.md) |
| POST | `/api/remote/connections/saved` | Save the connection list | [📖](./remote_api.md) |

#### Environment Detection

| Method | Endpoint | Description | Docs |
|--------|----------|-------------|------|
| GET | `/api/remote/conda-envs` | List Python environments | [📖](./remote_api.md#get-apiremoteconda-envs) |
| GET | `/api/remote/env-configs` | Batch-read environment version summaries | [📖](./remote_api.md) |
| GET | `/api/remote/config` | Get remote config | [📖](./remote_api.md#get-apiremoteconfig) |
| GET | `/api/remote/storage-candidates` | Detect candidate remote storage roots | [📖](./remote_api.md) |

#### Remote Viewer Management

| Method | Endpoint | Description | Docs |
|--------|----------|-------------|------|
| POST | `/api/remote/viewer/start` | Start Remote Viewer | [📖](./remote_api.md#post-apiremoteviewerstart) |
| POST | `/api/remote/viewer/stop` | Stop Remote Viewer | [📖](./remote_api.md#post-apiremoteviewerstop) |
| GET | `/api/remote/viewer/sessions` | List Viewer sessions | [📖](./remote_api.md#get-apiremoteviewersessions) |
| GET | `/api/remote/viewer/status/{session_id}` | Get Viewer status by session_id | [📖](./remote_api.md#get-apiremoteviewerstatussession_id) |

### Enhanced Logging API (introduced in v0.6.0)

**Current scope**: Console capture and Python logging integration

| Component | Description | Docs |
|-----------|-------------|------|
| `capture_console` | SDK parameter for stdout/stderr capture | [📖](./logging_api.md#sdk-parameters) |
| `tqdm_mode` | Smart tqdm filtering (smart/all/none) | [📖](./logging_api.md#sdk-parameters) |
| `get_logging_handler()` | Python logging.Handler integration | [📖](./logging_api.md#logging-handler) |
| `MetricLogger` | torchvision-compatible metric logger | [📖](./logging_api.md#metriclogger-compatibility) |

### Path Hierarchy API (introduced in v0.6.0)

**Current scope**: Flexible path-based experiment organization

| Method | Endpoint | Description | Docs |
|--------|----------|-------------|------|
| GET | `/api/paths` | List all paths with optional stats | [📖](./paths_api.md#get-apipaths) |
| GET | `/api/paths/tree` | Get path tree structure | [📖](./paths_api.md#get-apipathstree) |
| GET | `/api/paths/runs` | List runs filtered by path | [📖](./paths_api.md#get-apipathsruns) |
| POST | `/api/paths/soft-delete` | Batch soft delete by path | [📖](./paths_api.md#post-apipathssoft-delete) |
| GET | `/api/paths/export` | Export runs by path (JSON/ZIP) | [📖](./paths_api.md#get-apipathsexport) |

### Projects API (Hierarchy - Legacy)

| Method | Endpoint | Description | Docs |
|--------|----------|-------------|------|
| GET | `/api/projects` | List top-level path segments | [📖](./paths_api.md#get-apiprojects) |
| GET | `/api/projects/{project}/names` | List second-level segments | [📖](./paths_api.md#get-apiprojectsprojectnames) |
| GET | `/api/projects/{project}/names/{name}/runs` | List runs under project/name | [📖](./paths_api.md#get-apiprojectsprojectnamesname-runs) |

### Health & System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | API health check |
| GET | `/api/gpu/telemetry` | GPU monitoring data |

---

## 🔍 Search by Use Case

### Use Case: Monitor Training

```bash
# 1. Get run details
GET /api/runs/{run_id}

# 2. Stream logs in real-time
WS  ws://127.0.0.1:23300/api/runs/{run_id}/logs/ws

# 3. Poll metrics
GET /api/runs/{run_id}/metrics_step

# 4. Check GPU usage
GET /api/gpu/telemetry
```

### Use Case: Remote Viewer (New)

```bash
# 1. Connect to remote server
POST /api/remote/connect
Body: {"host": "gpu-server.com", "port": 22, "username": "mluser", "password": null, "private_key": null, "private_key_path": "~/.ssh/id_rsa", "passphrase": null, "use_agent": true}

# 2. Detect Python environments
GET /api/remote/conda-envs?connection_id=user@host:port

# 3. Start Remote Viewer
POST /api/remote/viewer/start
Body: {"host": "gpu-server.com", "port": 22, "username": "mluser", "private_key_path": "~/.ssh/id_rsa", "use_agent": true, "remote_root": "~/runicorn_data", "local_port": null, "remote_port": null, "conda_env": "system"}

# 4. Monitor status
GET /api/remote/viewer/status/{session_id}

# 5. Access remote data
# Browser opens: http://localhost:8081

# 6. Disconnect
POST /api/remote/disconnect
Body: {"host": "gpu-server.com", "port": 22, "username": "mluser"}
```

### Use Case: Analytics

```bash
# 1. Get all experiments
GET /api/runs

# 2. Filter by project
GET /api/projects/{project}/names/{name}/runs

# 3. Export data
POST /api/runs/export
GET /api/paths/export?path={path}&format=json
```

---

## 📊 Response Time Benchmarks

Based on 10,000 experiments:

| Endpoint | Avg Response | P95 | Backend |
|----------|-------------|-----|---------|
| `GET /api/runs` | 50-80 ms | 120ms | SQLite |
| `GET /api/runs/{id}/metrics_step` | 100-300 ms | 500ms | File read + parse |
| `GET /api/health` | < 5 ms | 10ms | In-memory |

---

## 🔐 Security Considerations

### Input Validation

All user inputs are validated:

```python
# Run ID validation
Pattern: ^[0-9]{8}_[0-9]{6}_[a-f0-9]{6}$
Example: 20250114_153045_a1b2c3

# Project/Name validation
Rules:
- No '..' (path traversal)
- No '/' or '\' (path separators)
- Max length: 100 characters

# File path validation
Rules:
- No '..' anywhere
- Must be within storage root
- Triple-layer verification
```

### Rate Limiting

See [Rate Limiting](#rate-limiting) section in main README.

**Headers to monitor**:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 15
```

### SSH Security

- Never log credentials
- Prefer SSH keys or SSH agent
- Host-key validation failures return `409` and require explicit confirmation
- The active remote route family is `/api/remote/*`
- `/api/unified/*` and `/api/ssh/*` remain only as historical context

---

## 🛠️ Testing APIs

### Using cURL

```bash
# Basic GET
curl http://127.0.0.1:23300/api/health

# POST with JSON body
curl -X POST http://127.0.0.1:23300/api/runs/soft-delete \
  -H "Content-Type: application/json" \
  -d '{"run_ids": ["20250114_153045_a1b2c3"]}'

```

### Using Postman

Import this collection: [runicorn_api.postman_collection.json](./runicorn_api.postman_collection.json)

**Or create manually**:
1. Create new collection "Runicorn API"
2. Set collection variable: `baseUrl = http://127.0.0.1:23300/api`
3. Add requests using `{{baseUrl}}/runs` syntax

### Using HTTPie

```bash
# Install httpie
pip install httpie

# GET request
http GET http://127.0.0.1:23300/api/runs

# POST with JSON
http POST http://127.0.0.1:23300/api/runs/soft-delete \
  run_ids:='["20250114_153045_a1b2c3"]'

# Pretty output
http --pretty=all GET http://127.0.0.1:23300/api/config
```

---

## 📱 Client Libraries

### Official SDK

**Python SDK** (recommended):
```python
import runicorn as rn

# Create experiment
run = rn.init(path="demo/exp1")

# Log metrics
run.log({"loss": 0.1, "accuracy": 0.95}, step=100)

# Finish
run.finish()
```

See main [README.md](../../README.md) for full SDK documentation.

### Community Libraries
> Note: Community libraries for other languages (JavaScript, R, Julia) are welcome. See [CONTRIBUTING.md](../../CONTRIBUTING.md).

> 🔔 **Note**: Community libraries for other languages (JavaScript, R, Julia) are welcome. See [CONTRIBUTING.md](../../CONTRIBUTING.md).

---

## 🔗 Related Resources

### Documentation

- **API Overview**: [README.md](./README.md)
- **Quick Reference**: [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
- **Detailed Modules**: Individual API docs
- **Examples**: [examples/](../../examples/) directory

### Interactive Tools

- **FastAPI Docs**: `http://127.0.0.1:23300/docs` (Swagger UI)
- **ReDoc**: `http://127.0.0.1:23300/redoc` (Alternative UI)
- **OpenAPI Schema**: `http://127.0.0.1:23300/openapi.json`

### Support

- **Issues**: GitHub Issues
- **Security**: [SECURITY.md](../../SECURITY.md)
- **Community**: [CONTRIBUTING.md](../../CONTRIBUTING.md)

---

## 📝 API Changelog

### v0.7.1 (Current) 🚀
**Current Release Highlights**
- ✅ **Remote Viewer hardening**: saved connections, health monitoring, reconnect states, and OpenSSH password support
- ✅ **Web UI productization**: cleaner navigation, ZIP import/export preview, unified recycle bin, and improved compare flow
- ✅ **Logs & monitoring**: virtualized logs, stronger dark-mode consistency, and backend-collected GPU telemetry history
- ✅ **Logging compatibility**: better support for ImageNet meters, TensorBoard, and tensorboardX
- ✅ **Desktop workflow improvements**: native remote-session handling in the current desktop flow

### v0.6.0
**Major Foundations**
- ✅ **Enhanced Logging API**: Console capture, Python logging handler, MetricLogger compatibility
- ✅ **Assets System**: SHA256 content-addressed workspace snapshots with deduplication
- ✅ **Path Hierarchy API**: Flexible path-based experiment organization with tree navigation
- ✅ **SSH Backend Architecture**: Multi-backend fallback (OpenSSH → AsyncSSH → Paramiko)
- ✅ **SQLite Storage Backend**: High-performance storage with connection pooling and WAL mode

### v0.5.4 ⚡
**Performance & UI Improvements**
- ✅ **Unified MetricChart**: Single component for single-run and multi-run views
- ✅ **Lazy chart loading**: IntersectionObserver-based chart rendering
- ✅ **Advanced memo optimization**: Data fingerprint comparison for re-render prevention
- ✅ Frontend beautification: Fancy metric cards, animated status badges

### v0.5.2
**Backend Performance**
- ✅ **Added LTTB downsampling** for metrics endpoints (`?downsample=N`)
- ✅ **Added incremental caching** for metrics (file-size based invalidation)
- ✅ Added `/metrics/cache/stats` endpoint for cache monitoring
- ✅ Added response headers (`X-Row-Count`, `X-Total-Count`, `X-Last-Step`)
- ✅ Added `total` and `sampled` fields to metrics response

### v0.5.1
**Frontend Detail Page Optimizations**
- ✅ Minor UI improvements for experiment detail page
- ✅ Bug fixes for chart rendering

### v0.5.0
- ✅ **Added Remote Viewer API** (now evolved into the `/api/remote/*` route family)
- ✅ Deprecated old SSH file sync API
- ✅ SSH key and password authentication support
- ✅ Automatic Python environment detection
- ✅ Remote Viewer lifecycle management
- ✅ Connection health monitoring

### v0.4.0
- ✅ Added Unified SSH API
- ✅ Enhanced error responses
- ✅ Added rate limiting

### v0.3.1
- Basic Runs API
- Metrics query
- SSH mirror support

### Possible Future Directions (Not Committed)

- Windows remote server support
- GraphQL API support
- Webhook notifications
- API key authentication
- Batch upload endpoints

---

**Interactive Docs**: http://127.0.0.1:23300/docs

