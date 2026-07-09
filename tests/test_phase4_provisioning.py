"""
Unit tests for JetStream provisioning (S-013, B2 fix).

Tests the _ensure_consumer reprovisioning path:
- idempotent: consumer exists → delete + recreate
- safe: missing consumer path still works
- correct params: delete_consumer called with consumer=<durable>
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — instantiate _ensure_consumer for direct testing
# ---------------------------------------------------------------------------


async def _call_ensure_consumer(js, stream="RMP", durable="test-consumer"):
    """Call the real _ensure_consumer with a mock JS context."""
    from packages.services.jetstream_provisioning import _ensure_consumer

    await _ensure_consumer(js, stream=stream, durable=durable)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEnsureConsumerIdempotent:
    """Consumer exists → delete + recreate."""

    @pytest.mark.asyncio
    async def test_add_consumer_succeeds_first_time(self):
        """First call succeeds — no delete needed."""
        js = MagicMock()
        js.add_consumer = AsyncMock(return_value=None)

        await _call_ensure_consumer(js)

        js.add_consumer.assert_called_once()
        js.delete_consumer.assert_not_called()

    @pytest.mark.asyncio
    async def test_consumer_exists_delete_and_recreate(self):
        """add_consumer fails (exists) → delete → add_consumer retry."""
        js = MagicMock()
        # First add_consumer raises (consumer exists)
        js.add_consumer = AsyncMock(
            side_effect=[Exception("consumer already exists"), None]
        )
        js.delete_consumer = AsyncMock(return_value=True)

        await _call_ensure_consumer(js)

        # Called twice: first fails, second succeeds after delete
        assert js.add_consumer.call_count == 2
        js.delete_consumer.assert_called_once_with(
            stream="RMP", consumer="test-consumer"
        )

    @pytest.mark.asyncio
    async def test_delete_uses_consumer_param_not_durable_name(self):
        """P1 fix: delete_consumer must use consumer=, not durable_name=."""
        js = MagicMock()
        js.add_consumer = AsyncMock(
            side_effect=[Exception("exists"), None]
        )

        # If consumer= is wrong param name, TypeError would propagate
        js.delete_consumer = AsyncMock(return_value=True)

        await _call_ensure_consumer(js)

        # Verify the call used consumer=, not durable_name=
        js.delete_consumer.assert_called_once_with(
            stream="RMP", consumer="test-consumer"
        )

    @pytest.mark.asyncio
    async def test_delete_failure_propagates(self):
        """If delete_consumer also fails, RuntimeError propagates."""
        js = MagicMock()
        js.add_consumer = AsyncMock(side_effect=Exception("exists"))
        js.delete_consumer = AsyncMock(
            side_effect=Exception("stream not found")
        )

        with pytest.raises(RuntimeError, match="Failed to create or update"):
            await _call_ensure_consumer(js)

    @pytest.mark.asyncio
    async def test_retry_add_after_delete_failure_propagates(self):
        """add_consumer after delete fails → RuntimeError."""
        js = MagicMock()
        js.add_consumer = AsyncMock(
            side_effect=[Exception("exists"), Exception("still fails")]
        )
        js.delete_consumer = AsyncMock(return_value=True)

        with pytest.raises(RuntimeError, match="Failed to create or update"):
            await _call_ensure_consumer(js)

    @pytest.mark.asyncio
    async def test_missing_consumer_path_safe(self):
        """When consumer doesn't exist, add_consumer succeeds first try."""
        js = MagicMock()
        js.add_consumer = AsyncMock(return_value=None)

        await _call_ensure_consumer(js)

        js.add_consumer.assert_called_once()
        js.delete_consumer.assert_not_called()
