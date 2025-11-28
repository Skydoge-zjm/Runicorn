[English](API_INDEX.md) | [简体中文](../zh/API_INDEX.md)

---

# Complete API Index

**Version**: v0.5.x  
**Total Endpoints**: 53+ REST + Python Client  
**Last Updated**: 2025-11-28

---

## 🐍 Python API Client

**New**: Programmatic Python access interface

| Component | Description | Docs |
|-----------|-------------|------|
| **RunicornClient** | Main client class | [📖](./python_client_api.md) |
| **Experiments API** | Experiment query and management | [📖](./python_client_api.md#experiment-management) |
| **Metrics API** | Metrics data access | [📖](./python_client_api.md#metrics-data) |
| **Artifacts API** | Programmatic artifacts management | [📖](./python_client_api.md#artifacts-api) |
| **Remote API** | Remote Viewer control | [📖](./python_client_api.md#remote-api) |
| **Utils** | pandas DataFrame tools | [📖](./python_client_api.md#utility-functions) |

**Quick Example**:
```python
import runicorn.api as api

with api.connect() as client:
    experiments = client.list_experiments(project="vision")
    metrics = client.get_metrics(experiments[0]["id"])
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

### Artifacts API (Version Control)

| Method | Endpoint | Description | Docs |
|--------|----------|-------------|------|
| GET | `/api/artifacts` | List artifacts | [📖](./artifacts_api.md#list-artifacts) |
| GET | `/api/artifacts/{name}/versions` | List versions | [📖](./artifacts_api.md#list-artifact-versions) |
| GET | `/api/artifacts/{name}/v{version}` | Get version detail | [📖](./artifacts_api.md#get-artifact-detail) |
| GET | `/api/artifacts/{name}/v{version}/files` | List files | [📖](./artifacts_api.md#list-artifact-files) |
| GET | `/api/artifacts/{name}/v{version}/lineage` | Get lineage graph | [📖](./artifacts_api.md#get-artifact-lineage) |
| GET | `/api/artifacts/stats` | Get storage stats | [📖](./artifacts_api.md#get-storage-statistics) |
| DELETE | `/api/artifacts/{name}/v{version}` | Delete version | [📖](./artifacts_api.md#delete-artifact-version) |

### V2 API (High Performance) ⚡

| Method | Endpoint | Description | Docs |
|--------|----------|-------------|------|
| GET | `/api/v2/experiments` | Advanced query | [📖](./v2_api.md#list-experiments) |
| GET | `/api/v2/experiments/{id}` | Get detail | [📖](./v2_api.md#get-experiment-detail) |
| GET | `/api/v2/experiments/{id}/metrics/fast` | Fast metrics | [📖](./v2_api.md#fast-metrics-retrieval) |
| POST | `/api/v2/experiments/batch-delete` | Batch delete | [📖](./v2_api.md#batch-delete) |

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

**v0.5.0 New**: VSCode Remote-style remote server access

#### Connection Management

| Method | Endpoint | Description | Docs |
|--------|----------|-------------|------|
| POST | `/api/remote/connect` | Establish SSH connection | [📖](./remote_api.md#post-apiremoteconnect) |
| GET | `/api/remote/connections` | List all connections | [📖](./remote_api.md#get-apiremoteconnections) |
| DELETE | `/api/remote/connections/{id}` | Disconnect | [📖](./remote_api.md#delete-apiremoteconnectionsid) |

#### Environment Detection

| Method | Endpoint | Description | Docs |
|--------|----------|-------------|------|
| GET | `/api/remote/environments` | List Python environments | [📖](./remote_api.md#get-apiremoteenvironments) |
| POST | `/api/remote/environments/detect` | Re-detect environments | [📖](./remote_api.md#post-apiremoteenvironmentsdetect) |
| GET | `/api/remote/config` | Get remote config | [📖](./remote_api.md#get-apiremoteconfig) |

#### Remote Viewer Management

| Method | Endpoint | Description | Docs |
|--------|----------|-------------|------|
| POST | `/api/remote/viewer/start` | Start Remote Viewer | [📖](./remote_api.md#post-apiremoteviewerstart) |
| POST | `/api/remote/viewer/stop` | Stop Remote Viewer | [📖](./remote_api.md#post-apiremoteviewerstop) |
| GET | `/api/remote/viewer/status` | Get Viewer status | [📖](./remote_api.md#get-apiremoteviewerstatus) |
| GET | `/api/remote/viewer/logs` | Get Viewer logs | [📖](./remote_api.md#get-apiremoteviewerlogs) |

#### Health Checks

| Method | Endpoint | Description | Docs |
|--------|----------|-------------|------|
| GET | `/api/remote/health` | Connection health status | [📖](./remote_api.md#get-apiremotehealth) |
| GET | `/api/remote/ping` | Test connection latency | [📖](./remote_api.md#get-apiremoteping) |

### Projects API (Hierarchy)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List all projects |
| GET | `/api/projects/{project}/names` | List experiment names in project |
| GET | `/api/projects/{project}/names/{name}/runs` | List runs in experiment |

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

### Use Case: Manage Models

```bash
# 1. List all models
GET /api/artifacts?type=model

# 2. View version history
GET /api/artifacts/resnet50-model/versions

# 3. Get specific version
GET /api/artifacts/resnet50-model/v3

# 4. Check dependencies
GET /api/artifacts/resnet50-model/v3/lineage

# 5. Download files
GET /api/artifacts/resnet50-model/v3/files
```

### Use Case: Remote Viewer (New)

```bash
# 1. Connect to remote server
POST /api/remote/connect
Body: {"host": "gpu-server.com", "username": "user", "auth_method": "key", "private_key_path": "~/.ssh/id_rsa"}

# 2. Detect Python environments
GET /api/remote/environments?connection_id=conn_1a2b3c4d

# 3. Start Remote Viewer
POST /api/remote/viewer/start
Body: {"connection_id": "conn_1a2b3c4d", "env_name": "pytorch-env", "auto_open": true}

# 4. Monitor status
GET /api/remote/viewer/status?connection_id=conn_1a2b3c4d

# 5. Access remote data
# Browser opens: http://localhost:8081

# 6. Disconnect
DELETE /api/remote/connections/conn_1a2b3c4d
```

### Use Case: Analytics

```bash
# 1. Get all experiments (V2 for performance)
GET /api/v2/experiments?per_page=1000

# 2. Filter by project
GET /api/v2/experiments?project=image_classification

# 3. Filter by performance
GET /api/v2/experiments?best_metric_min=0.9&status=finished

# 4. Get storage stats
GET /api/artifacts/stats
```

---

## 📊 Response Time Benchmarks

Based on 10,000 experiments:

| Endpoint | Avg Response | P95 | Backend |
|----------|-------------|-----|---------|
| `GET /api/runs` | 5-8 seconds | 10s | File scan |
| `GET /api/v2/experiments` | 50-80 ms | 120ms | SQLite |
| `GET /api/runs/{id}/metrics_step` | 100-300 ms | 500ms | File read + parse |
| `GET /api/v2/experiments/{id}/metrics/fast` | 30-60 ms | 100ms | SQLite (cached) |
| `GET /api/artifacts` | 200-400 ms | 600ms | File scan |
| `GET /api/artifacts/stats` | 1-3 seconds | 5s | Recursive scan |

**Recommendation**: Use V2 API for queries involving large numbers of experiments.

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
- Use SSH keys > passwords
- Use SSH agent when possible
- Connections are not persisted
- Max 5 connection attempts per minute

---

## 🛠️ Testing APIs

### Using cURL

```bash
# Basic GET
curl http://127.0.0.1:23300/api/health

# GET with query params
curl "http://127.0.0.1:23300/api/artifacts?type=model"

# POST with JSON body
curl -X POST http://127.0.0.1:23300/api/runs/soft-delete \
  -H "Content-Type: application/json" \
  -d '{"run_ids": ["20250114_153045_a1b2c3"]}'

# DELETE
curl -X DELETE "http://127.0.0.1:23300/api/artifacts/old-model/v1?permanent=false"
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
run = rn.init(project="demo", name="exp1")

# Log metrics
rn.log({"loss": 0.1, "accuracy": 0.95}, step=100)

# Save artifact
artifact = rn.Artifact("my-model", type="model")
artifact.add_file("model.pth")
run.log_artifact(artifact)

rn.finish()
```

See main [README.md](../../README.md) for full SDK documentation.

### Community Libraries

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

### v0.5.x (Current)
- ✅ **Added LTTB downsampling** for metrics endpoints (`?downsample=N`)
- ✅ **Added incremental caching** for metrics (file-size based invalidation)
- ✅ Added `/metrics/cache/stats` endpoint for cache monitoring
- ✅ Added response headers (`X-Row-Count`, `X-Total-Count`, `X-Last-Step`)
- ✅ Added `total` and `sampled` fields to metrics response

### v0.5.0
- ✅ **Added Remote Viewer API** (12 endpoints)
- ✅ Deprecated old SSH file sync API
- ✅ SSH key and password authentication support
- ✅ Automatic Python environment detection
- ✅ Remote Viewer lifecycle management
- ✅ Connection health monitoring

### v0.4.0
- ✅ Added V2 high-performance API
- ✅ Added Artifacts API (version control)
- ✅ Added Unified SSH API
- ✅ Enhanced error responses
- ✅ Added rate limiting

### v0.3.1
- Basic Runs API
- Metrics query
- SSH mirror support

### Future Versions

**v0.6.0** (Planned):
- Windows remote server support
- GraphQL API support
- Webhook notifications
- API key authentication
- Batch upload endpoints

---

**Interactive Docs**: http://127.0.0.1:23300/docs

