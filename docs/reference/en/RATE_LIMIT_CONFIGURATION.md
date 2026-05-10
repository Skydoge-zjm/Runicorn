[English](RATE_LIMIT_CONFIGURATION.md) | [简体中文](../zh/RATE_LIMIT_CONFIGURATION.md)

---

# Rate Limit Configuration Guide

**Last Updated**: 2026-05-10

## Overview

The current rate-limiting implementation has two layers:

1. configuration load/save  
   `src/runicorn/config/rate_limits.py`
2. runtime enforcement  
   `src/runicorn/security/rate_limiter.py`

This document follows those implementations rather than older examples.

## Load priority

`get_rate_limit_config()` currently loads configuration in this order:

1. `rate_limits.json` in the user config directory
2. bundled defaults at `src/runicorn/config/_defaults/rate_limits.json`
3. hardcoded fallback values in `rate_limiter.py` if loading fails

The bundled default file is copied into the user config directory on first load so users can edit it afterwards.

## Bundled defaults

Repository default file:

```text
src/runicorn/config/_defaults/rate_limits.json
```

The current default file contains verified special configuration buckets for:

- `/api/remote/connect`
- `/api/remote/status`
- `/api/metrics/gpu`
- `/api/remote/download`
- `/api/remote/sync`
- `/api/runs`

Example:

```json
{
  "default": {
    "max_requests": 6000,
    "window_seconds": 60,
    "burst_size": null
  },
  "endpoints": {
    "/api/remote/connect": {
      "max_requests": 10,
      "window_seconds": 60
    },
    "/api/remote/status": {
      "max_requests": 20000,
      "window_seconds": 60
    }
  },
  "settings": {
    "enable_rate_limiting": false,
    "log_violations": true,
    "whitelist_localhost": false
  }
}
```

## Runtime fallback

If configuration loading fails, `src/runicorn/security/rate_limiter.py` falls back to hardcoded defaults. The currently verified fallback buckets are:

- `/api/remote/connect`
- `/api/remote/status`
- `/api/remote/download`
- `/api/remote/sync`
- `/api/runs`

Two facts need to stay separate:

1. these paths are currently present in rate-limit config and fallback logic
2. that does not by itself mean the application currently exposes matching public API routes

At the time of this update, `/api/remote/download` and `/api/remote/sync` were verified only in rate-limit config and fallback logic, not in the currently registered `/api/remote/*` route set. In this guide they should therefore be treated only as rate-limit bucket examples, not as active API reference entries.

## Configuration structure

### `default`

- `max_requests`
- `window_seconds`
- `burst_size`
- `description`

### `endpoints`

Per-endpoint overrides using the same fields as `default`.

### `settings`

- `enable_rate_limiting`
- `log_violations`
- `whitelist_localhost`
- `custom_headers`

## Verified programmatic API

The current repository exports:

- `runicorn.config.get_rate_limit_config`
- `runicorn.config.save_rate_limit_config`

Example:

```python
from runicorn.config import get_rate_limit_config, save_rate_limit_config

config = get_rate_limit_config()
config["endpoints"]["/api/remote/connect"] = {
    "max_requests": 5,
    "window_seconds": 60,
    "burst_size": None,
    "description": "Tighter SSH connection limit"
}
save_rate_limit_config(config)
```

## Examples worth keeping in sync with code

### Tighten connection endpoints

```json
"/api/remote/connect": {
  "max_requests": 5,
  "window_seconds": 60
}
```

### Keep high-frequency polling permissive

```json
"/api/remote/status": {
  "max_requests": 20000,
  "window_seconds": 60
}
```

### Adjust global settings

```json
{
  "settings": {
    "enable_rate_limiting": false,
    "whitelist_localhost": true
  }
}
```

## Response headers

Header names are controlled by `custom_headers`. The current defaults are:

```text
X-RateLimit-Limit
X-RateLimit-Remaining
X-RateLimit-Reset
```

Rate-limit violations still return:

```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 45
}
```

## Maintenance rule

Update this document whenever any of the following changes:

1. the endpoint set in `src/runicorn/config/_defaults/rate_limits.json`
2. the load priority in `get_rate_limit_config()`
3. the fallback endpoints in `rate_limiter.py`
4. the exported configuration helper names

If a path exists only in rate-limit config and not as a public route, the document must label it as a configuration bucket rather than a live API capability.

---

- **[Reference Index](README.md)**
- **[API Documentation Overview](../../api/en/README.md)**
