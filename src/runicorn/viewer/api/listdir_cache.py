"""
UI Listdir Rate Limiting and Caching (L6)

Provides rate limiting and in-memory caching for SSH listdir operations
to avoid overwhelming remote servers with rapid requests.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CachedListdirResult:
    """Cached listdir result with TTL."""
    items: List[Dict[str, Any]]
    cached_at: float
    ttl_seconds: float
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.cached_at > self.ttl_seconds


class ListdirRateLimiter:
    """
    Rate limiter for listdir operations.
    
    L6 Hardening:
    - Limits listdir rate to max 0.5 QPS (1 request per 2 seconds)
    - In-memory cache with 5 second TTL
    - Per-connection tracking
    """
    
    DEFAULT_MIN_INTERVAL_SECONDS = 2.0  # 0.5 QPS
    DEFAULT_CACHE_TTL_SECONDS = 5.0
    
    def __init__(
        self,
        min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS,
        cache_ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
        max_cache_entries: int = 1000
    ):
        """
        Initialize rate limiter with caching.
        
        Args:
            min_interval_seconds: Minimum seconds between requests (default: 2s = 0.5 QPS)
            cache_ttl_seconds: Cache TTL in seconds (default: 5s)
            max_cache_entries: Maximum cache entries before eviction (default: 1000)
        """
        self.min_interval = min_interval_seconds
        self.cache_ttl = cache_ttl_seconds
        self.max_cache_entries = max_cache_entries
        
        # Track last request time per connection+path
        self._last_request: Dict[str, float] = {}
        
        # In-memory cache
        self._cache: Dict[str, CachedListdirResult] = {}
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'rate_limited': 0,
            'evictions': 0,
        }
        
        logger.info(
            f"ListdirRateLimiter initialized: "
            f"min_interval={min_interval_seconds}s, "
            f"cache_ttl={cache_ttl_seconds}s, "
            f"max_entries={max_cache_entries}"
        )
    
    def check_rate_limit(
        self,
        connection_id: str,
        path: str
    ) -> Tuple[bool, Optional[float]]:
        """
        Check if request should be rate limited.
        
        Args:
            connection_id: SSH connection identifier
            path: Remote path being listed
            
        Returns:
            (allowed, wait_seconds) tuple
            - allowed: True if request can proceed
            - wait_seconds: Seconds to wait if rate limited
        """
        with self._lock:
            key = f"{connection_id}:{path}"
            now = time.time()
            
            last_time = self._last_request.get(key, 0)
            elapsed = now - last_time
            
            if elapsed < self.min_interval:
                # Rate limited
                wait_seconds = self.min_interval - elapsed
                self.stats['rate_limited'] += 1
                logger.debug(
                    f"Rate limited: {connection_id} path={path}, "
                    f"wait={wait_seconds:.2f}s"
                )
                return False, wait_seconds
            
            # Update last request time
            self._last_request[key] = now
            return True, None
    
    def get_cached(
        self,
        connection_id: str,
        path: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached listdir result if available and not expired.
        
        Args:
            connection_id: SSH connection identifier
            path: Remote path being listed
            
        Returns:
            Cached items list or None if not cached/expired
        """
        with self._lock:
            self.stats['total_requests'] += 1
            
            cache_key = f"{connection_id}:{path}"
            cached = self._cache.get(cache_key)
            
            if cached and not cached.is_expired():
                self.stats['cache_hits'] += 1
                logger.debug(
                    f"Cache hit: {connection_id} path={path}, "
                    f"age={time.time() - cached.cached_at:.1f}s"
                )
                return cached.items
            
            self.stats['cache_misses'] += 1
            return None
    
    def put_cache(
        self,
        connection_id: str,
        path: str,
        items: List[Dict[str, Any]]
    ) -> None:
        """
        Cache listdir result.
        
        Args:
            connection_id: SSH connection identifier
            path: Remote path being listed
            items: List of directory items
        """
        with self._lock:
            cache_key = f"{connection_id}:{path}"
            
            # Evict oldest entries if cache is full
            if len(self._cache) >= self.max_cache_entries:
                self._evict_oldest()
            
            # Store in cache
            self._cache[cache_key] = CachedListdirResult(
                items=items,
                cached_at=time.time(),
                ttl_seconds=self.cache_ttl
            )
            
            logger.debug(
                f"Cached: {connection_id} path={path}, "
                f"items={len(items)}, cache_size={len(self._cache)}"
            )
    
    def _evict_oldest(self) -> None:
        """Evict oldest cache entries to make room."""
        if not self._cache:
            return
        
        # Find and remove oldest 10% of entries
        entries = list(self._cache.items())
        entries.sort(key=lambda x: x[1].cached_at)
        
        evict_count = max(1, len(entries) // 10)
        for i in range(evict_count):
            key, _ = entries[i]
            del self._cache[key]
            self.stats['evictions'] += 1
        
        logger.debug(f"Evicted {evict_count} cache entries")
    
    def invalidate(
        self,
        connection_id: Optional[str] = None,
        path: Optional[str] = None
    ) -> int:
        """
        Invalidate cache entries.
        
        Args:
            connection_id: If provided, only invalidate this connection
            path: If provided, only invalidate this path
            
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            if connection_id is None and path is None:
                # Invalidate all
                count = len(self._cache)
                self._cache.clear()
                self._last_request.clear()
                logger.info(f"Invalidated entire cache ({count} entries)")
                return count
            
            # Selective invalidation
            keys_to_remove = []
            for key in self._cache.keys():
                conn_id, cache_path = key.split(':', 1)
                
                if connection_id and conn_id != connection_id:
                    continue
                if path and cache_path != path:
                    continue
                
                keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._cache[key]
                if key in self._last_request:
                    del self._last_request[key]
            
            logger.info(
                f"Invalidated {len(keys_to_remove)} cache entries "
                f"(connection={connection_id}, path={path})"
            )
            return len(keys_to_remove)
    
    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, cached in self._cache.items()
                if cached.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        with self._lock:
            hit_rate = (
                self.stats['cache_hits'] / self.stats['total_requests']
                if self.stats['total_requests'] > 0 else 0
            )
            
            return {
                **self.stats,
                'cache_size': len(self._cache),
                'cache_hit_rate': hit_rate,
                'tracked_paths': len(self._last_request),
            }


# Global instance
_global_rate_limiter: Optional[ListdirRateLimiter] = None
_global_lock = threading.Lock()


def get_global_rate_limiter() -> ListdirRateLimiter:
    """Get or create global rate limiter instance."""
    global _global_rate_limiter
    
    with _global_lock:
        if _global_rate_limiter is None:
            _global_rate_limiter = ListdirRateLimiter()
        return _global_rate_limiter


async def rate_limited_listdir(
    connection_id: str,
    path: str,
    listdir_func: callable,
    use_cache: bool = True,
    rate_limiter: Optional[ListdirRateLimiter] = None
) -> List[Dict[str, Any]]:
    """
    Perform rate-limited and cached listdir operation.
    
    Args:
        connection_id: SSH connection identifier
        path: Remote path to list
        listdir_func: Function to call for actual listdir (if not cached)
        use_cache: Whether to use caching (default: True)
        rate_limiter: Rate limiter instance (uses global if None)
        
    Returns:
        List of directory items
        
    Raises:
        Exception: If rate limited or listdir fails
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    if rate_limiter is None:
        rate_limiter = get_global_rate_limiter()
    
    # Check cache first
    if use_cache:
        cached_result = rate_limiter.get_cached(connection_id, path)
        if cached_result is not None:
            return cached_result
    
    # Check rate limit
    allowed, wait_seconds = rate_limiter.check_rate_limit(connection_id, path)
    if not allowed:
        raise Exception(
            f"Rate limited: please wait {wait_seconds:.1f} seconds before retrying"
        )
    
    # Perform actual listdir in thread pool to avoid blocking event loop
    try:
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, listdir_func)
    except Exception as e:
        logger.error(f"Listdir failed for {connection_id}:{path}: {e}")
        raise
    
    # Cache result
    if use_cache:
        rate_limiter.put_cache(connection_id, path, items)
    
    return items
