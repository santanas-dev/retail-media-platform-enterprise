"""
Redis-backed manifest cache (S-067).

Fail-open design: if Redis is unavailable or not configured, all operations
gracefully degrade to no-op — the caller falls back to the DB path.

Config is read from environment; no hard dependency on Redis being present.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level lazy client — created on first use, survives across requests
# ---------------------------------------------------------------------------

_client: Any = None
_client_error: str | None = None


def _get_config():
    """Read Redis config from environment."""
    return {
        "url": os.getenv("REDIS_URL", ""),
        "enabled": os.getenv("MANIFEST_CACHE_ENABLED", "0").lower() in ("1", "true", "yes"),
        "ttl_seconds": int(os.getenv("MANIFEST_CACHE_TTL_SECONDS", "300")),
    }


def _build_client():
    """Lazily build Redis client. Returns client or None on any error."""
    global _client, _client_error

    if _client is not None:
        return _client
    if _client_error is not None:
        return None

    cfg = _get_config()
    if not cfg["enabled"] or not cfg["url"]:
        _client_error = "Redis not configured or disabled"
        return None

    try:
        import redis.asyncio as aioredis
        _client = aioredis.from_url(
            cfg["url"],
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
        logger.info("Redis manifest cache connected to %s", _mask_url(cfg["url"]))
    except Exception as exc:
        _client_error = str(exc)
        logger.warning("Redis manifest cache unavailable: %s", exc)
        return None

    return _client


def _mask_url(url: str) -> str:
    """Mask password in Redis URL for logging."""
    if "@" in url:
        return url.split("@")[0].rsplit(":", 1)[0] + ":***@" + url.split("@")[1]
    return url


async def get_manifest_cache(device_id: str) -> dict | None:
    """Return cached manifest payload for device_id, or None on miss/error."""
    client = _build_client()
    if client is None:
        return None

    cfg = _get_config()
    key = _cache_key(device_id)
    try:
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning("Redis get error for device %s: %s", device_id[:8], exc)
        return None


async def set_manifest_cache(device_id: str, payload: dict) -> None:
    """Cache manifest payload for device_id. Silently ignores errors."""
    client = _build_client()
    if client is None:
        return

    cfg = _get_config()
    key = _cache_key(device_id)
    try:
        await client.setex(key, cfg["ttl_seconds"], json.dumps(payload))
    except Exception as exc:
        logger.warning("Redis set error for device %s: %s", device_id[:8], exc)


def _cache_key(device_id: str) -> str:
    """Stable cache key for device manifest."""
    return f"manifest:latest:{device_id}"
