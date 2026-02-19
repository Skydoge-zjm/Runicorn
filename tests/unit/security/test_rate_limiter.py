"""Unit tests for runicorn.security.rate_limiter."""
from __future__ import annotations

import threading
from unittest.mock import patch

import pytest

from runicorn.security.rate_limiter import EndpointRateLimiter, RateLimiter


# ---------------------------------------------------------------------------
# RateLimiter (sliding window)
# ---------------------------------------------------------------------------

class TestSlidingWindowBasic:
    """test_sliding_window_basic — requests within limit are allowed."""

    def test_first_request_allowed(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        allowed, retry_after = limiter.is_allowed("client_a")
        assert allowed is True
        assert retry_after is None

    def test_within_limit_all_allowed(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            allowed, _ = limiter.is_allowed("client_a")
            assert allowed is True

    def test_exceeds_limit_blocked(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.is_allowed("client_a")

        allowed, retry_after = limiter.is_allowed("client_a")
        assert allowed is False
        assert retry_after is not None
        assert retry_after > 0

    def test_different_clients_independent(self):
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        a_ok, _ = limiter.is_allowed("client_a")
        b_ok, _ = limiter.is_allowed("client_b")
        assert a_ok is True
        assert b_ok is True

    def test_get_usage(self):
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        limiter.is_allowed("c1")
        limiter.is_allowed("c1")
        usage = limiter.get_usage("c1")
        assert usage["used"] == 2
        assert usage["remaining"] == 8
        assert usage["limit"] == 10

    def test_reset_clears_client(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed("c1")
        limiter.is_allowed("c1")
        limiter.reset("c1")
        allowed, _ = limiter.is_allowed("c1")
        assert allowed is True


class TestSlidingWindowExpired:
    """test_sliding_window_expired — old requests outside window not counted."""

    def test_expired_requests_not_counted(self):
        limiter = RateLimiter(max_requests=2, window_seconds=10)

        # Manually insert old timestamps
        import time
        now = time.time()
        limiter._requests["c1"].append(now - 20)  # 20s ago — expired
        limiter._requests["c1"].append(now - 15)  # 15s ago — expired

        # Should be allowed since both requests are expired
        allowed, _ = limiter.is_allowed("c1")
        assert allowed is True

    def test_mixed_old_and_new(self):
        limiter = RateLimiter(max_requests=2, window_seconds=10)

        import time
        now = time.time()
        limiter._requests["c1"].append(now - 20)  # expired
        limiter._requests["c1"].append(now - 1)   # still valid

        allowed, _ = limiter.is_allowed("c1")
        assert allowed is True
        # Now we have 2 valid requests (the recent one + the new one)
        usage = limiter.get_usage("c1")
        assert usage["used"] == 2


# ---------------------------------------------------------------------------
# EndpointRateLimiter
# ---------------------------------------------------------------------------

class TestEndpointRateLimiterDifferentEndpoints:
    """test_endpoint_rate_limiter_different_endpoints — per-endpoint limits."""

    def test_separate_limits(self):
        erl = EndpointRateLimiter()
        erl.configure_endpoint("/api/connect", max_requests=2, window_seconds=60)
        erl.configure_endpoint("/api/status", max_requests=100, window_seconds=60)

        # Exhaust /api/connect
        erl.is_allowed("/api/connect", "c1")
        erl.is_allowed("/api/connect", "c1")
        blocked, _ = erl.is_allowed("/api/connect", "c1")
        assert blocked is False

        # /api/status should still be allowed
        allowed, _ = erl.is_allowed("/api/status", "c1")
        assert allowed is True

    def test_default_limiter_used_for_unconfigured(self):
        erl = EndpointRateLimiter()
        limiter = erl.get_limiter("/api/unknown")
        assert limiter is erl._default_limiter

    def test_prefix_matching(self):
        erl = EndpointRateLimiter()
        erl.configure_endpoint("/api/remote", max_requests=5, window_seconds=60)
        limiter = erl.get_limiter("/api/remote/connect")
        assert limiter.max_requests == 5

    def test_disable_rate_limiting(self):
        erl = EndpointRateLimiter()
        erl.configure_endpoint("/api/test", max_requests=1, window_seconds=60)
        erl.update_settings({"enable_rate_limiting": False})

        erl.is_allowed("/api/test", "c1")
        allowed, _ = erl.is_allowed("/api/test", "c1")
        assert allowed is True  # rate limiting disabled

    def test_get_and_update_settings(self):
        erl = EndpointRateLimiter()
        original = erl.get_settings()
        assert original["enable_rate_limiting"] is True

        erl.update_settings({"log_violations": False})
        updated = erl.get_settings()
        assert updated["log_violations"] is False
        assert updated["enable_rate_limiting"] is True


class TestLocalhostWhitelist:
    """test_localhost_whitelist — localhost requests bypass rate limiting."""

    @pytest.mark.parametrize("client_id", ["127.0.0.1", "::1", "localhost"])
    def test_whitelisted_when_enabled(self, client_id: str):
        erl = EndpointRateLimiter()
        erl.configure_endpoint("/api/test", max_requests=1, window_seconds=60)
        erl.update_settings({"whitelist_localhost": True})

        # Exhaust the limit
        erl.is_allowed("/api/test", client_id)
        # Should still be allowed due to whitelist
        allowed, _ = erl.is_allowed("/api/test", client_id)
        assert allowed is True

    def test_not_whitelisted_by_default(self):
        erl = EndpointRateLimiter()
        erl.configure_endpoint("/api/test", max_requests=1, window_seconds=60)
        # Default: whitelist_localhost = False

        erl.is_allowed("/api/test", "127.0.0.1")
        allowed, _ = erl.is_allowed("/api/test", "127.0.0.1")
        assert allowed is False

    def test_non_localhost_not_whitelisted(self):
        erl = EndpointRateLimiter()
        erl.configure_endpoint("/api/test", max_requests=1, window_seconds=60)
        erl.update_settings({"whitelist_localhost": True})

        erl.is_allowed("/api/test", "192.168.1.100")
        allowed, _ = erl.is_allowed("/api/test", "192.168.1.100")
        assert allowed is False


class TestRateLimiterThreadSafety:
    """test_rate_limiter_thread_safety — concurrent access doesn't corrupt state."""

    def test_concurrent_requests(self):
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        results = []
        errors = []

        def make_requests():
            try:
                for _ in range(20):
                    allowed, _ = limiter.is_allowed("shared_client")
                    results.append(allowed)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=make_requests) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        # 100 requests allowed, 5 threads × 20 = 100 total
        allowed_count = sum(1 for r in results if r)
        assert allowed_count == 100
        denied_count = sum(1 for r in results if not r)
        assert denied_count == 0

    def test_concurrent_different_clients(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        results = {}
        lock = threading.Lock()

        def make_requests(client_id: str):
            local_results = []
            for _ in range(5):
                allowed, _ = limiter.is_allowed(client_id)
                local_results.append(allowed)
            with lock:
                results[client_id] = local_results

        threads = [
            threading.Thread(target=make_requests, args=(f"client_{i}",))
            for i in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each client should have all 5 requests allowed
        for client_id, client_results in results.items():
            assert all(client_results), f"{client_id} had denied requests"
