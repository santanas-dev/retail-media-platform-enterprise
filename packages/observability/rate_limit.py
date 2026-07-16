"""
Device Gateway Rate Limiter (S-065).

In-memory token bucket per key (device ID or IP).
Redis-backed path deferred — architecture supports swapping the backend.

Config via env vars:
  RATE_LIMIT_ENABLED — "true"/"1" to enable (default: false in dev, true in production)
  DEVICE_MANIFEST_RATE_LIMIT — max requests per window (default: 60)
  DEVICE_POP_RATE_LIMIT — max requests per window (default: 120)
  RATE_LIMIT_WINDOW_SECONDS — sliding window size (default: 60)
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name, "").strip().lower()
    if val in ("true", "1", "yes"):
        return True
    if val in ("false", "0", "no"):
        return False
    return default


RATE_LIMIT_ENABLED = _env_bool(
    "RATE_LIMIT_ENABLED",
    default=(os.environ.get("ENVIRONMENT", "dev") == "production"),
)
DEVICE_MANIFEST_RATE_LIMIT = int(os.environ.get("DEVICE_MANIFEST_RATE_LIMIT", "60"))
DEVICE_POP_RATE_LIMIT = int(os.environ.get("DEVICE_POP_RATE_LIMIT", "120"))
PUBLIC_APPLICATION_RATE_LIMIT = int(os.environ.get("PUBLIC_APPLICATION_RATE_LIMIT", "3"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))


# ---------------------------------------------------------------------------
# Token bucket per key
# ---------------------------------------------------------------------------

@dataclass
class _Bucket:
    tokens: int
    last_refill: float


_lock = threading.Lock()
_buckets: dict[str, _Bucket] = {}


def _refill(bucket: _Bucket, now: float, rate: int) -> None:
    """Refill tokens based on elapsed time."""
    elapsed = now - bucket.last_refill
    new_tokens = int(elapsed * (rate / RATE_LIMIT_WINDOW_SECONDS))
    if new_tokens > 0:
        bucket.tokens = min(bucket.tokens + new_tokens, rate)
        bucket.last_refill = now


def check_rate_limit(key: str, max_requests: int) -> bool:
    """Check if a request is within the rate limit for the given key.

    Returns True if allowed, False if over limit.
    Thread-safe. In-memory only — reboots reset all buckets.
    """
    if not RATE_LIMIT_ENABLED:
        return True

    now = time.monotonic()
    with _lock:
        bucket = _buckets.get(key)
        if bucket is None:
            bucket = _Bucket(tokens=max_requests, last_refill=now)
            _buckets[key] = bucket

        _refill(bucket, now, max_requests)

        if bucket.tokens > 0:
            bucket.tokens -= 1
            return True
        return False


def get_rate_limit_key(request, device_id: Optional[str] = None) -> str:
    """Derive a rate limit key: device ID if known, else client IP."""
    if device_id:
        return f"device:{device_id}"
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    return f"ip:{ip}"


# ---------------------------------------------------------------------------
# Periodic cleanup — prevent unbounded memory growth
# ---------------------------------------------------------------------------

def _cleanup_expired() -> None:
    """Remove buckets that haven't been used in 2× the window."""
    cutoff = time.monotonic() - (2 * RATE_LIMIT_WINDOW_SECONDS)
    with _lock:
        expired = [k for k, b in _buckets.items() if b.last_refill < cutoff]
        for k in expired:
            del _buckets[k]


# Periodic cleanup runs in a daemon thread
def _cleanup_loop() -> None:
    while True:
        time.sleep(RATE_LIMIT_WINDOW_SECONDS * 2)
        _cleanup_expired()


_cleanup_thread = threading.Thread(target=_cleanup_loop, daemon=True)
_cleanup_thread.start()
