"""
Rate Limiting Middleware

Applies rate limiting to API endpoints.
"""
from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ...security.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to apply rate limiting to requests.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and apply rate limiting.
        
        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler
            
        Returns:
            Response from the endpoint or rate limit error
        """
        # Skip rate limiting for non-API routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        
        # Skip rate limiting for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"
        
        # Check for X-Forwarded-For header if behind proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()
        
        # Get rate limiter
        limiter = get_rate_limiter()
        
        # Check if request is allowed
        endpoint = request.url.path
        is_allowed, retry_after = limiter.is_allowed(endpoint, client_ip)
        
        if not is_allowed:
            # Get custom header names from settings
            settings = limiter.get_settings()
            custom_headers = settings.get("custom_headers", {})
            limit_header = custom_headers.get("rate_limit_header", "X-RateLimit-Limit")
            remaining_header = custom_headers.get("rate_limit_remaining_header", "X-RateLimit-Remaining")
            reset_header = custom_headers.get("rate_limit_reset_header", "X-RateLimit-Reset")
            
            # Return 429 Too Many Requests
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": retry_after
                },
                headers={
                    "Retry-After": str(retry_after),
                    limit_header: str(limiter.get_limiter(endpoint).max_requests),
                    remaining_header: "0",
                    reset_header: str(retry_after)
                }
            )
        
        # Process the request
        response = await call_next(request)
        
        # Get custom header names from settings
        settings = limiter.get_settings()
        custom_headers = settings.get("custom_headers", {})
        limit_header = custom_headers.get("rate_limit_header", "X-RateLimit-Limit")
        remaining_header = custom_headers.get("rate_limit_remaining_header", "X-RateLimit-Remaining")
        reset_header = custom_headers.get("rate_limit_reset_header", "X-RateLimit-Reset")
        
        # Add rate limit headers to response
        usage = limiter.get_limiter(endpoint).get_usage(client_ip)
        response.headers[limit_header] = str(usage["limit"])
        response.headers[remaining_header] = str(usage["remaining"])
        response.headers[reset_header] = str(usage["reset_in"])
        
        return response
