"""
Incremental Metrics Cache Module

Provides an incremental caching mechanism for metrics data that efficiently handles
continuously growing files (e.g., during active training). Instead of re-parsing
the entire file on each request, it only reads newly appended data.

Key Features:
- File size-based cache invalidation (instead of mtime)
- Incremental reading from last known position
- Thread-safe operations for concurrent access
- Automatic cache eviction with LRU strategy

Performance Characteristics:
- Cache hit (no file change): O(1)
- Incremental update: O(n) where n is new lines only
- Full parse (cache miss): O(N) where N is total lines
"""
from __future__ import annotations

import json
import logging
import math
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class IncrementalCacheEntry:
    """
    Represents a single cache entry with incremental update support.
    
    Attributes:
        file_size: File size at last read (bytes)
        read_position: File position after last read (bytes)
        columns: Set of all metric column names discovered
        step_rows: Mapping from step number to row data
        cached_at: Timestamp when entry was last updated
        hit_count: Number of cache hits for statistics
    """
    file_size: int = 0
    read_position: int = 0
    columns: Set[str] = field(default_factory=set)
    step_rows: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    cached_at: float = field(default_factory=time.time)
    hit_count: int = 0


class IncrementalMetricsCache:
    """
    Thread-safe incremental cache for metrics data.
    
    This cache is specifically designed for JSONL event files that are
    continuously appended during training. It tracks file size and read
    position to enable efficient incremental updates.
    
    Usage:
        cache = IncrementalMetricsCache(max_size=100)
        columns, rows = cache.get_or_update(events_path)
    
    Thread Safety:
        All public methods are thread-safe and can be called concurrently.
    """
    
    def __init__(self, max_size: int = 100, stale_threshold: int = 3600):
        """
        Initialize the incremental metrics cache.
        
        Args:
            max_size: Maximum number of cached entries before eviction
            stale_threshold: Time in seconds before an entry is considered stale
        """
        self._max_size = max_size
        self._stale_threshold = stale_threshold
        self._cache: Dict[str, IncrementalCacheEntry] = {}
        self._lock = threading.RLock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._incremental_updates = 0
    
    def get_or_update(
        self, 
        file_path: Path
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Get cached metrics data, performing incremental update if needed.
        
        This method handles three scenarios:
        1. Cache hit (file unchanged): Return cached data immediately
        2. Incremental update (file grew): Read only new data and merge
        3. Cache miss (new file or truncated): Full parse required
        
        Args:
            file_path: Path to the events.jsonl file
            
        Returns:
            Tuple of (column_names, row_data)
        """
        if not file_path.exists():
            return [], []
        
        cache_key = str(file_path.resolve())
        
        try:
            current_size = file_path.stat().st_size
        except OSError as e:
            logger.warning(f"Failed to stat file {file_path}: {e}")
            return [], []
        
        with self._lock:
            entry = self._cache.get(cache_key)
            
            # Case 1: Cache hit - file size unchanged
            if entry is not None and current_size == entry.file_size:
                self._hits += 1
                entry.hit_count += 1
                logger.debug(
                    f"Cache hit for {file_path.name} "
                    f"(hits: {entry.hit_count}, size: {current_size})"
                )
                return self._build_result(entry)
            
            # Case 2: Incremental update - file has grown
            if entry is not None and current_size > entry.file_size:
                self._incremental_updates += 1
                bytes_added = current_size - entry.file_size
                logger.debug(
                    f"Incremental update for {file_path.name} "
                    f"(+{bytes_added} bytes)"
                )
                self._incremental_read(file_path, entry, current_size)
                return self._build_result(entry)
            
            # Case 3: Cache miss - new file, truncated, or not cached
            self._misses += 1
            if entry is not None:
                logger.debug(
                    f"Cache invalidated for {file_path.name} "
                    f"(size changed: {entry.file_size} -> {current_size})"
                )
            
            # Evict if at capacity
            self._evict_if_needed()
            
            # Full parse
            entry = self._full_read(file_path)
            self._cache[cache_key] = entry
            return self._build_result(entry)
    
    def invalidate(self, file_path: Path) -> bool:
        """
        Manually invalidate cache for a specific file.
        
        Args:
            file_path: Path to the file to invalidate
            
        Returns:
            True if entry was found and removed, False otherwise
        """
        cache_key = str(file_path.resolve())
        with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.debug(f"Manually invalidated cache for {file_path.name}")
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries and reset statistics."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._incremental_updates = 0
            logger.info("Incremental metrics cache cleared")
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses + self._incremental_updates
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "incremental_updates": self._incremental_updates,
                "hit_rate": self._hits / total_requests if total_requests > 0 else 0.0,
                "incremental_rate": (
                    self._incremental_updates / total_requests 
                    if total_requests > 0 else 0.0
                ),
            }
    
    def _incremental_read(
        self, 
        file_path: Path, 
        entry: IncrementalCacheEntry,
        new_size: int
    ) -> None:
        """
        Read only the newly appended portion of the file.
        
        Args:
            file_path: Path to the events file
            entry: Existing cache entry to update
            new_size: Current file size
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(entry.read_position)
                
                lines_parsed = 0
                for line in f:
                    line = line.strip()
                    if line:
                        self._parse_event_line(line, entry)
                        lines_parsed += 1
                
                entry.read_position = f.tell()
                entry.file_size = new_size
                entry.cached_at = time.time()
                
                logger.debug(
                    f"Incremental read: {lines_parsed} new lines from {file_path.name}"
                )
        except Exception as e:
            logger.error(f"Error during incremental read of {file_path}: {e}")
            # On error, invalidate entry to force full re-read next time
            entry.file_size = -1
    
    def _full_read(self, file_path: Path) -> IncrementalCacheEntry:
        """
        Perform a full parse of the events file.
        
        Args:
            file_path: Path to the events file
            
        Returns:
            New cache entry with all parsed data
        """
        entry = IncrementalCacheEntry()
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines_parsed = 0
                for line in f:
                    line = line.strip()
                    if line:
                        self._parse_event_line(line, entry)
                        lines_parsed += 1
                
                entry.read_position = f.tell()
            
            entry.file_size = file_path.stat().st_size
            entry.cached_at = time.time()
            
            logger.debug(
                f"Full read: {lines_parsed} lines, "
                f"{len(entry.step_rows)} steps from {file_path.name}"
            )
        except Exception as e:
            logger.error(f"Error during full read of {file_path}: {e}")
        
        return entry
    
    def _parse_event_line(
        self, 
        line: str, 
        entry: IncrementalCacheEntry
    ) -> None:
        """
        Parse a single JSONL event line and update the cache entry.
        
        Args:
            line: Raw JSON line to parse
            entry: Cache entry to update
        """
        try:
            evt = json.loads(line)
            
            # Only process metrics events
            if not isinstance(evt, dict) or evt.get("type") != "metrics":
                return
            
            data = evt.get("data")
            if not isinstance(data, dict):
                return
            
            # Extract step value (prefer global_step over step)
            step_val = data.get("global_step")
            if step_val is None:
                step_val = data.get("step")
            if step_val is None:
                return
            
            try:
                step = int(step_val)
            except (ValueError, TypeError):
                return
            
            # Get or create row for this step
            if step not in entry.step_rows:
                entry.step_rows[step] = {"global_step": step}
            
            row = entry.step_rows[step]
            
            # Merge metrics data
            for key, value in data.items():
                if key in ("global_step", "step", "epoch"):
                    continue
                
                # Only store valid metric values
                if isinstance(value, (int, float)):
                    # Sanitize NaN/Inf values for JSON compatibility
                    if math.isnan(value) or math.isinf(value):
                        value = None
                    row[key] = value
                    entry.columns.add(key)
                elif isinstance(value, str) or value is None:
                    row[key] = value
                    entry.columns.add(key)
                    
        except json.JSONDecodeError:
            pass  # Skip malformed JSON lines
        except Exception as e:
            logger.debug(f"Error parsing event line: {e}")
    
    def _build_result(
        self, 
        entry: IncrementalCacheEntry
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Build the final result tuple from a cache entry.
        
        Args:
            entry: Cache entry to convert
            
        Returns:
            Tuple of (columns, rows) with consistent column ordering
        """
        if not entry.step_rows:
            return [], []
        
        # Build sorted column list with global_step first
        columns = ["global_step"] + sorted(entry.columns)
        
        # Build rows sorted by step, ensuring all columns are present
        rows = []
        for step in sorted(entry.step_rows.keys()):
            row = entry.step_rows[step].copy()
            # Ensure all columns exist in each row
            for col in columns:
                row.setdefault(col, None)
            rows.append(row)
        
        return columns, rows
    
    def _evict_if_needed(self) -> None:
        """
        Evict entries if cache is at capacity.
        
        Uses a combination of:
        1. Remove stale entries (not accessed recently)
        2. LRU eviction based on hit count and cache time
        """
        if len(self._cache) < self._max_size:
            return
        
        current_time = time.time()
        
        # First pass: remove stale entries
        stale_keys = [
            key for key, entry in self._cache.items()
            if current_time - entry.cached_at > self._stale_threshold
        ]
        
        for key in stale_keys:
            del self._cache[key]
            logger.debug(f"Evicted stale cache entry: {key}")
        
        # If still over capacity, use LRU
        while len(self._cache) >= self._max_size:
            # Find entry with lowest hit count, break ties by oldest cached_at
            worst_key = min(
                self._cache.items(),
                key=lambda x: (x[1].hit_count, -x[1].cached_at)
            )[0]
            del self._cache[worst_key]
            logger.debug(f"Evicted LRU cache entry: {worst_key}")


# Global singleton instance
_incremental_cache: Optional[IncrementalMetricsCache] = None
_cache_lock = threading.Lock()


def get_incremental_metrics_cache() -> IncrementalMetricsCache:
    """
    Get the global incremental metrics cache instance.
    
    Returns:
        The singleton IncrementalMetricsCache instance
    """
    global _incremental_cache
    
    if _incremental_cache is None:
        with _cache_lock:
            if _incremental_cache is None:
                _incremental_cache = IncrementalMetricsCache(
                    max_size=100,
                    stale_threshold=3600
                )
    
    return _incremental_cache
