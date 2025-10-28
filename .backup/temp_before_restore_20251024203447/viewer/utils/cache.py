"""
Caching Utilities for Viewer

Provides caching mechanisms for expensive operations like metrics aggregation.
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MetricsCache:
    """
    Thread-safe cache for metrics data with file modification tracking.
    
    Automatically invalidates cache when source file is modified.
    """
    
    def __init__(self, max_size: int = 100, ttl: int = 600):
        """
        Initialize metrics cache.
        
        Args:
            max_size: Maximum number of cached entries
            ttl: Time-to-live for cache entries in seconds (default: 10 minutes)
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Tuple[float, float, Any]] = {}  # key -> (mtime, cached_at, data)
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, file_path: Path) -> Optional[Tuple[List[str], List[Dict[str, Any]]]]:
        """
        Get cached metrics data if available and valid.
        
        Args:
            file_path: Path to the events file
            
        Returns:
            Cached data if valid, None otherwise
        """
        cache_key = str(file_path)
        
        try:
            # Get current file modification time
            if not file_path.exists():
                return None
            
            current_mtime = file_path.stat().st_mtime
        except Exception as e:
            logger.debug(f"Failed to get file mtime: {e}")
            return None
        
        with self._lock:
            if cache_key not in self._cache:
                self._misses += 1
                return None
            
            cached_mtime, cached_at, cached_data = self._cache[cache_key]
            
            # Check if file has been modified
            if cached_mtime != current_mtime:
                logger.debug(f"Cache invalidated for {cache_key} (file modified)")
                del self._cache[cache_key]
                self._misses += 1
                return None
            
            # Check TTL
            if time.time() - cached_at > self.ttl:
                logger.debug(f"Cache expired for {cache_key} (TTL exceeded)")
                del self._cache[cache_key]
                self._misses += 1
                return None
            
            self._hits += 1
            logger.debug(f"Cache hit for {cache_key} (hit rate: {self.hit_rate():.1%})")
            return cached_data
    
    def set(self, file_path: Path, data: Tuple[List[str], List[Dict[str, Any]]]) -> None:
        """
        Store metrics data in cache.
        
        Args:
            file_path: Path to the events file
            data: Metrics data to cache (columns, rows)
        """
        cache_key = str(file_path)
        
        try:
            current_mtime = file_path.stat().st_mtime
        except Exception as e:
            logger.debug(f"Failed to cache data: {e}")
            return
        
        with self._lock:
            # Evict oldest entry if cache is full
            if len(self._cache) >= self.max_size:
                # Find oldest entry by cached_at time
                oldest_key = min(self._cache.items(), key=lambda x: x[1][1])[0]
                del self._cache[oldest_key]
                logger.debug(f"Evicted oldest cache entry: {oldest_key}")
            
            # Store new entry
            self._cache[cache_key] = (current_mtime, time.time(), data)
            logger.debug(f"Cached data for {cache_key} (cache size: {len(self._cache)})")
    
    def invalidate(self, file_path: Path) -> None:
        """
        Manually invalidate cache for a file.
        
        Args:
            file_path: Path to the events file
        """
        cache_key = str(file_path)
        with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.debug(f"Manually invalidated cache for {cache_key}")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info("Cache cleared")
    
    def hit_rate(self) -> float:
        """
        Get cache hit rate.
        
        Returns:
            Hit rate as a fraction (0.0 to 1.0)
        """
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self.hit_rate(),
                "ttl": self.ttl,
            }


# Global metrics cache instance
_metrics_cache = MetricsCache(max_size=100, ttl=600)


def get_metrics_cache() -> MetricsCache:
    """Get the global metrics cache instance."""
    return _metrics_cache
