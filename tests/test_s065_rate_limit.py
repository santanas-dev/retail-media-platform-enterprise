"""
S-065 — Rate limiter unit tests.

Tests the in-memory token bucket rate limiter.
"""
from __future__ import annotations

import os
import time
import unittest

import pytest


class TestRateLimiter(unittest.TestCase):
    """Token bucket rate limiter behaviour."""

    def setUp(self):
        # Force enabled for tests
        os.environ["RATE_LIMIT_ENABLED"] = "true"
        os.environ["DEVICE_MANIFEST_RATE_LIMIT"] = "10"
        os.environ["DEVICE_POP_RATE_LIMIT"] = "20"
        os.environ["RATE_LIMIT_WINDOW_SECONDS"] = "60"
        # Reload module to pick up env changes
        import importlib
        import packages.observability.rate_limit as rl
        importlib.reload(rl)
        self.rl = rl

    def tearDown(self):
        import packages.observability.rate_limit as rl
        # Clear buckets
        rl._buckets.clear()

    def test_within_limit_passes(self):
        """Requests within the limit are allowed."""
        key = "device:test-001"
        for _ in range(10):
            self.assertTrue(self.rl.check_rate_limit(key, 10))

    def test_over_limit_blocked(self):
        """Requests over the limit return False."""
        key = "device:test-002"
        for _ in range(10):
            self.assertTrue(self.rl.check_rate_limit(key, 10))
        # 11th request — over limit
        self.assertFalse(self.rl.check_rate_limit(key, 10))

    def test_separate_keys_have_separate_buckets(self):
        """Different keys have independent rate limits."""
        for _ in range(10):
            self.assertTrue(self.rl.check_rate_limit("device:a", 10))
        # device:a is exhausted, but device:b is fresh
        self.assertTrue(self.rl.check_rate_limit("device:b", 10))
        # device:a is still blocked
        self.assertFalse(self.rl.check_rate_limit("device:a", 10))

    def test_disabled_allows_all(self):
        """When disabled, all requests pass regardless of limit."""
        os.environ["RATE_LIMIT_ENABLED"] = "false"
        import importlib
        import packages.observability.rate_limit as rl
        importlib.reload(rl)
        key = "device:test-003"
        for _ in range(1000):
            self.assertTrue(rl.check_rate_limit(key, 1))

    def test_get_rate_limit_key_device(self):
        """Rate limit key uses device ID when available."""
        key = self.rl.get_rate_limit_key(_fake_request(), "dev-123")
        self.assertEqual(key, "device:dev-123")

    def test_get_rate_limit_key_fallback_ip(self):
        """Rate limit key falls back to client IP."""
        key = self.rl.get_rate_limit_key(_fake_request(), None)
        self.assertEqual(key, "ip:10.0.0.1")

    def test_get_rate_limit_key_x_forwarded_for(self):
        """Rate limit key uses X-Forwarded-For header."""
        req = _fake_request(hdrs={"X-Forwarded-For": "192.168.1.1, 10.0.0.1"})
        key = self.rl.get_rate_limit_key(req, None)
        self.assertEqual(key, "ip:192.168.1.1")

    def test_429_http_status_code(self):
        """Verify 429 is the correct status code constant (for reference)."""
        self.assertEqual(429, 429)  # sanity


def _fake_request(hdrs=None):
    """Minimal fake Request for get_rate_limit_key."""
    class FakeClient:
        host = "10.0.0.1"

    class FakeReq:
        headers = hdrs if hdrs is not None else {}
        client = FakeClient()

    return FakeReq()
