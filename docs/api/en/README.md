[English](README.md) | [简体中文](../zh/README.md)

---

# Runicorn API Documentation

**Version**: v0.6.0  
**Base URL**: `http://127.0.0.1:23300/api`  
**Protocol**: HTTP/1.1  
**Format**: JSON  
**Character Encoding**: UTF-8

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [API Modules](#api-modules)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [Versioning](#versioning)

---

## Getting Started

### Quick Start

```bash
# Start the Runicorn viewer
runicorn viewer --host 127.0.0.1 --port 23300

# API is now available at
http://127.0.0.1:23300/api
```

### API Health Check

```bash
GET /api/health

Response:
{
  "status": "ok",
  "version": "0.6.0",
  "timestamp": 1704067200.0
}
```

---

## Authentication

**Current Version**: No authentication required (local-only API)

> ⚠️ **Security Note**: The API is designed for local use only. Do not expose it to the internet without proper authentication and encryption.

**Future Versions**: May support API keys for multi-user scenarios.

---

## API Types

Runicorn provides two ways to access the API:

### 🐍 Python API Client (Recommended)

**New**: Programmatic access interface for simplified Python integration

```python
import runicorn.api as api

with api.connect() as client:
    experiments = client.list_experiments(project="vision")
    metrics = client.get_metrics(experiments[0]["id"])
```

**Features**:
- ✅ Type safety and auto-completion
- ✅ Auto-retry and connection management
- ✅ pandas DataFrame integration
- ✅ Remote API extension

**Documentation**: [python_client_api.md](./python_client_api.md)

---

### 🌐 REST API Modules

HTTP REST API endpoints for Web UI and third-party integrations.

| Module | Description | Documentation | Endpoints |
|--------|-------------|---------------|-----------|
| **Python Client** 🆕 | Programmatic Python access | [python_client_api.md](./python_client_api.md) | SDK |
| **Runs API** | Experiment run management (CRUD, soft delete, restore) | [runs_api.md](./runs_api.md) | 6 endpoints |
| **Metrics API** | Real-time metrics queries and visualization data | [metrics_api.md](./metrics_api.md) | 3 HTTP + 1 WebSocket |
| **Config API** | Configuration and preferences management | [config_api.md](./config_api.md) | 6 endpoints |
| **Remote Viewer API** 🆕 | VSCode Remote-style remote access | [remote_api.md](./remote_api.md) | 12 endpoints |
| **Logging API** 🆕 | Enhanced logging with console capture (v0.6.0) | [logging_api.md](./logging_api.md) | SDK |
| **Paths API** 🆕 | Path-based hierarchy navigation (v0.6.0) | [paths_api.md](./paths_api.md) | 5+3 endpoints |
| **SSH API** | SSH connection management (deprecated) | [ssh_api.md](./ssh_api.md) | 12 endpoints |

> ⚠️ **Deprecated**: Old SSH file sync API (`/api/unified/*`) has been replaced by Remote Viewer API. See [Migration Guide](../../guides/en/MIGRATION_GUIDE_v0.4_to_v0.5.md)

**Quick Reference**: See [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) for common operations

---

## Error Handling

### Standard Error Response

All errors follow this structure:

```json
{
  "detail": "Error message description"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `200` | OK | Request successful |
| `201` | Created | Resource created successfully |
| `400` | Bad Request | Invalid input parameters |
| `404` | Not Found | Resource not found |
| `409` | Conflict | Resource already exists or conflict |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server error |
| `503` | Service Unavailable | Service temporarily unavailable |

### Common Error Examples

```json
// 400 Bad Request
{
  "detail": "Invalid run_id format: abc123. Expected format: YYYYMMDD_HHMMSS_XXXXXX"
}

// 404 Not Found
{
  "detail": "Run not found: 20250101_120000_abc123"
}

// 429 Too Many Requests
{
  "detail": "Rate limit exceeded",
  "retry_after": 45
}

// 500 Internal Server Error
{
  "detail": "Failed to query database: connection timeout"
}
```

---

## Rate Limiting

### Default Limits

- **Default**: 60 requests per minute per IP
- **Sensitive endpoints**: Custom limits (see individual API docs)

### Rate Limit Headers

Every response includes these headers:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 15
```

### Handling Rate Limits

```python
import requests
import time

def api_call_with_retry(url):
    response = requests.get(url)
    
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        print(f"Rate limited. Waiting {retry_after} seconds...")
        time.sleep(retry_after)
        return api_call_with_retry(url)
    
    return response.json()
```

---

## Versioning

All API endpoints are under `/api/*`. The storage backend uses SQLite with connection pooling and WAL mode for high-performance queries.

---

## Quick Reference

### Most Used Endpoints

```bash
# List all experiment runs
GET /api/runs

# Get run details
GET /api/runs/{run_id}

# Get run metrics
GET /api/runs/{run_id}/metrics_step

# Connect to remote server (new)
POST /api/remote/connect

# Start Remote Viewer (new)
POST /api/remote/viewer/start

# Health check
GET /api/health
```

### WebSocket Endpoints

```bash
# Real-time logs streaming
ws://127.0.0.1:23300/api/runs/{run_id}/logs/ws
```

---

## Additional Resources

- **Quickstart Guide**: [QUICKSTART.md](../../guides/en/QUICKSTART.md)
- **Python SDK**: See `src/runicorn/sdk.py`
- **OpenAPI Schema**: `http://127.0.0.1:23300/docs` (auto-generated by FastAPI)
- **Examples**: `examples/` directory

---

## Support

- **Issues**: GitHub Issues
- **Security**: See [SECURITY.md](../../SECURITY.md)
- **Contributing**: See [CONTRIBUTING.md](../../CONTRIBUTING.md)

---

**Last Updated**: 2026-01-15  
**Maintained By**: Runicorn Development Team

