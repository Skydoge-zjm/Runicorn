"""Tests for runicorn.viewer.api.listdir_cache — ListdirRateLimiter."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from runicorn.viewer.api.listdir_cache import ListdirRateLimiter


@pytest.fixture
def limiter():
    return ListdirRateLimiter(
        min_interval_seconds=0.5,
        cache_ttl_seconds=1.0,
        max_cache_entries=5,
    )


class TestRateLimit:
    def test_first_request_allowed(self, limiter: ListdirRateLimiter):
        """First request is always allowed."""
        allowed, wait = limiter.check_rate_limit("conn1", "/home")
        assert allowed is True
        assert wait is None

    def test_rapid_second_request_rejected(self, limiter: ListdirRateLimiter):
        """Second request within min_interval is rate-limited."""
        limiter.check_rate_limit("conn1", "/home")
        allowed, wait = limiter.check_rate_limit("conn1", "/home")
        assert allowed is False
        assert wait is not None and wait > 0

    def test_different_paths_independent(self, limiter: ListdirRateLimiter):
        """Different connection+path combinations are independent."""
        limiter.check_rate_limit("conn1", "/path_a")
        allowed, _ = limiter.check_rate_limit("conn1", "/path_b")
        assert allowed is True


class TestCache:
    def test_cache_miss_then_hit(self, limiter: ListdirRateLimiter):
        """First get_cached returns None, after put_cache returns items."""
        assert limiter.get_cached("conn1", "/data") is None

        items = [{"name": "file1"}, {"name": "file2"}]
        limiter.put_cache("conn1", "/data", items)

        cached = limiter.get_cached("conn1", "/data")
        assert cached == items
        assert limiter.stats["cache_hits"] == 1

    def test_cache_expiry(self, limiter: ListdirRateLimiter):
        """Expired cache entries return None."""
        items = [{"name": "old"}]
        limiter.put_cache("conn1", "/expire", items)

        # Manually expire by patching cached_at
        entry = limiter._cache["conn1:/expire"]
        entry.cached_at = time.time() - 10  # well past TTL

        assert limiter.get_cached("conn1", "/expire") is None
        assert limiter.stats["cache_misses"] >= 1

    def test_cache_eviction_on_max(self, limiter: ListdirRateLimiter):
        """When cache exceeds max_cache_entries, oldest are evicted."""
        for i in range(6):  # max is 5
            limiter.put_cache("conn1", f"/dir{i}", [{"n": i}])

        assert len(limiter._cache) <= 5
        assert limiter.stats["evictions"] >= 1

    def test_invalidate_all(self, limiter: ListdirRateLimiter):
        """invalidate() with no args clears everything."""
        limiter.put_cache("c1", "/a", [{"x": 1}])
        limiter.put_cache("c2", "/b", [{"x": 2}])
        removed = limiter.invalidate()
        assert removed == 2
        assert len(limiter._cache) == 0

    def test_get_stats(self, limiter: ListdirRateLimiter):
        """get_stats returns expected fields."""
        limiter.get_cached("c1", "/a")  # miss
        limiter.put_cache("c1", "/a", [{"x": 1}])
        limiter.get_cached("c1", "/a")  # hit

        stats = limiter.get_stats()
        assert stats["total_requests"] == 2
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
        assert 0 < stats["cache_hit_rate"] < 1
