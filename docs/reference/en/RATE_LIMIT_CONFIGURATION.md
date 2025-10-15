# Rate Limit Configuration Guide

## Overview

The rate limiting system in Runicorn is now configurable through a JSON configuration file, making it easy to adjust limits without modifying code.

## Configuration File Location

The rate limit configuration is stored at:
- Primary location: `src/runicorn/config/rate_limits.json`
- Fallback location: `src/runicorn/rate_limits.json`

## Configuration Structure

```json
{
  "_comment": "Rate limits are high for local-only API with no internet exposure",
  "default": {
    "max_requests": 6000,
    "window_seconds": 60,
    "burst_size": null,
    "description": "Default rate limit - very permissive for local use"
  },
  "endpoints": {
    "/api/endpoint/path": {
      "max_requests": 100,
      "window_seconds": 60,
      "burst_size": 20,
      "description": "Endpoint-specific configuration"
    }
  },
  "settings": {
    "enable_rate_limiting": true,
    "log_violations": true,
    "whitelist_localhost": false,
    "custom_headers": {
      "rate_limit_header": "X-RateLimit-Limit",
      "rate_limit_remaining_header": "X-RateLimit-Remaining",
      "rate_limit_reset_header": "X-RateLimit-Reset"
    }
  }
}
```

## Configuration Parameters

### Default Section
- `max_requests`: Maximum number of requests allowed in the time window
- `window_seconds`: Time window in seconds
- `burst_size`: Optional burst size limit (defaults to max_requests if null)
- `description`: Human-readable description of the limit

### Endpoints Section
Each endpoint can have its own specific configuration with the same parameters as the default section.

### Settings Section
- `enable_rate_limiting`: Master switch to enable/disable rate limiting
- `log_violations`: Whether to log rate limit violations
- `whitelist_localhost`: Whether to bypass rate limiting for localhost requests
- `custom_headers`: Custom header names for rate limit information

## Common Configurations

### 1. Connection Endpoints (Restrictive)
```json
"/api/remote/connect": {
  "max_requests": 10,
  "window_seconds": 60,
  "description": "SSH connection operations - prevent brute force"
}
```

### 2. Status Polling Endpoints (Very Permissive)
```json
"/api/unified/status": {
  "max_requests": 20000,
  "window_seconds": 60,
  "description": "Status polling - very permissive for UI updates"
}
```

### 3. Download Endpoints (Moderate)
```json
"/api/remote/download": {
  "max_requests": 3000,
  "window_seconds": 60,
  "description": "File downloads - moderately restrictive"
}
```

## Modifying Rate Limits

### 1. Edit the Configuration File
```bash
# Edit the configuration
nano src/runicorn/config/rate_limits.json
```

### 2. Restart the Application
The configuration is loaded when the rate limiter is first initialized. Restart your Runicorn viewer to apply changes:
```bash
# Restart the viewer
runicorn viewer --host 0.0.0.0 --port 5000
```

## Examples

### Increase Polling Limits
If you're experiencing rate limit issues with status polling:
```json
{
  "endpoints": {
    "/api/unified/status": {
      "max_requests": 300,  // Increased from 200
      "window_seconds": 60
    }
  }
}
```

### Disable Rate Limiting for Development
```json
{
  "settings": {
    "enable_rate_limiting": false
  }
}
```

### Whitelist Localhost
```json
{
  "settings": {
    "whitelist_localhost": true
  }
}
```

### Add Burst Protection
```json
{
  "endpoints": {
    "/api/remote/sync": {
      "max_requests": 60,
      "window_seconds": 60,
      "burst_size": 10,  // Max 10 requests per second
      "description": "Sync with burst protection"
    }
  }
}
```

## Monitoring Rate Limits

### Response Headers
Every API response includes rate limit information:
- `X-RateLimit-Limit`: Total requests allowed
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Seconds until the limit resets

### Log Messages
When `log_violations` is enabled, rate limit violations are logged:
```
WARNING - Rate limit exceeded for 192.168.1.100 on /api/remote/connect, retry after 45s
```

## Best Practices

1. **Start Conservative**: Begin with lower limits and increase as needed
2. **Monitor Logs**: Watch for legitimate users hitting limits
3. **Different Limits for Different Operations**:
   - Authentication/Connection: 5-10 per minute
   - Status/Polling: 100-300 per minute
   - Data Operations: 20-60 per minute
   - File Downloads: 10-30 per minute

4. **Consider Burst Traffic**: Use burst_size for endpoints that might receive rapid requests
5. **Whitelist Carefully**: Only whitelist localhost in development environments

## Troubleshooting

### "Rate limit exceeded" Errors
1. Check current limits in `rate_limits.json`
2. Increase limits for the affected endpoint
3. Consider if the client is making too many requests

### Configuration Not Loading
1. Check file path and permissions
2. Verify JSON syntax is valid
3. Check application logs for loading errors

### Headers Not Appearing
1. Ensure rate limiting is enabled
2. Check custom_headers configuration
3. Verify middleware is properly registered

## API Reference

### Programmatic Configuration
```python
from runicorn.config import get_rate_limit_config, save_rate_limit_config

# Get current configuration
config = get_rate_limit_config()

# Modify configuration
config["endpoints"]["/api/custom/endpoint"] = {
    "max_requests": 50,
    "window_seconds": 60
}

# Save configuration
save_rate_limit_config(config)
```

## Security Considerations

1. **Don't Set Limits Too High**: This defeats the purpose of rate limiting
2. **Protect Connection Endpoints**: Keep authentication endpoints restrictive
3. **Log Violations**: Enable logging to detect potential attacks
4. **Regular Review**: Periodically review limits based on usage patterns

## Migration from Hardcoded Limits

If you're upgrading from a version with hardcoded limits, the system will:
1. First try to load from the configuration file
2. Fall back to hardcoded defaults if the file is not found
3. Log which configuration source is being used

This ensures backward compatibility while enabling configuration flexibility.
