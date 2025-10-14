"""
Rate Limiting Module

Provides rate limiting for API endpoints to prevent abuse.
"""
from __future__ import annotations

import time
import logging
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple, Any
import threading

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window.
    
    For production, consider using Redis-based rate limiting.
    """
    
    def __init__(
        self,
        max_requests: int = 60,
        window_seconds: int = 60,
        burst_size: Optional[int] = None
    ):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
            burst_size: Optional burst size (defaults to max_requests)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.burst_size = burst_size or max_requests
        
        # Store request timestamps for each client
        self._requests: Dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()
    
    def is_allowed(self, client_id: str) -> Tuple[bool, Optional[int]]:
        """
        Check if a request from a client is allowed.
        
        Args:
            client_id: Client identifier (e.g., IP address)
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        with self._lock:
            now = time.time()
            requests = self._requests[client_id]
            
            # Remove old requests outside the window
            cutoff = now - self.window_seconds
            while requests and requests[0] < cutoff:
                requests.popleft()
            
            # Check if limit is exceeded
            if len(requests) >= self.max_requests:
                # Calculate when the oldest request will expire
                oldest = requests[0]
                retry_after = int(oldest + self.window_seconds - now) + 1
                return False, retry_after
            
            # Check burst limit
            if self.burst_size < self.max_requests:
                # Check requests in last second for burst limiting
                burst_cutoff = now - 1
                burst_count = sum(1 for t in requests if t >= burst_cutoff)
                if burst_count >= self.burst_size:
                    return False, 1
            
            # Allow the request
            requests.append(now)
            return True, None
    
    def reset(self, client_id: str) -> None:
        """
        Reset rate limit for a specific client.
        
        Args:
            client_id: Client identifier
        """
        with self._lock:
            if client_id in self._requests:
                del self._requests[client_id]
    
    def get_usage(self, client_id: str) -> Dict[str, int]:
        """
        Get current usage statistics for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dictionary with usage statistics
        """
        with self._lock:
            now = time.time()
            requests = self._requests.get(client_id, deque())
            
            # Remove old requests
            cutoff = now - self.window_seconds
            valid_requests = [t for t in requests if t > cutoff]
            
            return {
                "used": len(valid_requests),
                "limit": self.max_requests,
                "remaining": max(0, self.max_requests - len(valid_requests)),
                "reset_in": self.window_seconds
            }


class EndpointRateLimiter:
    """
    Rate limiter with different limits per endpoint.
    """
    
    def __init__(self):
        """Initialize endpoint rate limiter."""
        self._limiters: Dict[str, RateLimiter] = {}
        self._default_limiter = RateLimiter(60, 60)  # 60 requests per minute default
        self._settings: Dict[str, Any] = {
            "enable_rate_limiting": True,
            "log_violations": True,
            "whitelist_localhost": False
        }
    
    def configure_endpoint(
        self,
        endpoint: str,
        max_requests: int,
        window_seconds: int,
        burst_size: Optional[int] = None
    ) -> None:
        """
        Configure rate limit for a specific endpoint.
        
        Args:
            endpoint: Endpoint path or pattern
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
            burst_size: Optional burst size
        """
        self._limiters[endpoint] = RateLimiter(
            max_requests, 
            window_seconds, 
            burst_size
        )
    
    def get_limiter(self, endpoint: str) -> RateLimiter:
        """
        Get rate limiter for an endpoint.
        
        Args:
            endpoint: Endpoint path
            
        Returns:
            Rate limiter for the endpoint
        """
        # Check for exact match
        if endpoint in self._limiters:
            return self._limiters[endpoint]
        
        # Check for pattern match (simple prefix matching)
        for pattern, limiter in self._limiters.items():
            if endpoint.startswith(pattern):
                return limiter
        
        # Use default limiter
        return self._default_limiter
    
    def is_allowed(self, endpoint: str, client_id: str) -> Tuple[bool, Optional[int]]:
        """
        Check if a request is allowed.
        
        Args:
            endpoint: Endpoint path
            client_id: Client identifier
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        # Check if rate limiting is enabled
        if not self._settings.get("enable_rate_limiting", True):
            return True, None
        
        # Check if localhost should be whitelisted
        if self._settings.get("whitelist_localhost", False) and client_id in ["127.0.0.1", "::1", "localhost"]:
            return True, None
        
        limiter = self.get_limiter(endpoint)
        allowed, retry_after = limiter.is_allowed(client_id)
        
        # Log violations if enabled
        if not allowed and self._settings.get("log_violations", True):
            logger.warning(f"Rate limit exceeded for {client_id} on {endpoint}, retry after {retry_after}s")
        
        return allowed, retry_after
    
    def get_settings(self) -> Dict[str, Any]:
        """Get current rate limiter settings."""
        return self._settings.copy()
    
    def update_settings(self, settings: Dict[str, Any]) -> None:
        """Update rate limiter settings."""
        self._settings.update(settings)


# Global instance
_endpoint_limiter: Optional[EndpointRateLimiter] = None


def get_rate_limiter() -> EndpointRateLimiter:
    """
    Get the global rate limiter instance.
    
    Returns:
        EndpointRateLimiter instance
    """
    global _endpoint_limiter
    if _endpoint_limiter is None:
        _endpoint_limiter = EndpointRateLimiter()
        
        # Load configuration from file
        try:
            from ..config import get_rate_limit_config
            config = get_rate_limit_config()
            
            # Configure default limiter
            default_config = config.get("default", {})
            if default_config:
                _endpoint_limiter._default_limiter = RateLimiter(
                    max_requests=default_config.get("max_requests", 60),
                    window_seconds=default_config.get("window_seconds", 60),
                    burst_size=default_config.get("burst_size")
                )
                logger.info(f"Configured default rate limit: {default_config.get('max_requests')}/{default_config.get('window_seconds')}s")
            
            # Configure specific endpoints
            endpoints = config.get("endpoints", {})
            for endpoint, endpoint_config in endpoints.items():
                _endpoint_limiter.configure_endpoint(
                    endpoint=endpoint,
                    max_requests=endpoint_config.get("max_requests", 60),
                    window_seconds=endpoint_config.get("window_seconds", 60),
                    burst_size=endpoint_config.get("burst_size")
                )
                logger.debug(f"Configured {endpoint}: {endpoint_config.get('max_requests')}/{endpoint_config.get('window_seconds')}s")
            
            # Store settings
            _endpoint_limiter._settings = config.get("settings", {})
            
            logger.info(f"Loaded rate limit configuration with {len(endpoints)} custom endpoints")
            
        except Exception as e:
            logger.warning(f"Failed to load rate limit config, using defaults: {e}")
            # Fallback to hardcoded defaults
            _endpoint_limiter.configure_endpoint("/api/remote/connect", 10, 60)
            _endpoint_limiter.configure_endpoint("/api/unified/connect", 10, 60)
            _endpoint_limiter.configure_endpoint("/api/ssh/connect", 10, 60)
            _endpoint_limiter.configure_endpoint("/api/unified/status", 200, 60)
            _endpoint_limiter.configure_endpoint("/api/remote/status", 200, 60)
            _endpoint_limiter.configure_endpoint("/api/ssh/sessions", 200, 60)
            _endpoint_limiter.configure_endpoint("/api/ssh/mirror/list", 200, 60)
            _endpoint_limiter.configure_endpoint("/api/remote/download", 30, 60)
            _endpoint_limiter.configure_endpoint("/api/remote/sync", 20, 60)
        
    return _endpoint_limiter
