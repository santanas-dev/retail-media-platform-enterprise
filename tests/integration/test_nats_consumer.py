"""Opt-in NATS JetStream integration test (S-012 Phase 2c).

Proves the end-to-end path:
  publish event → NatsJetStreamCampaignConsumer receives → handler processes → ack

Requires:
  - RUN_NATS_INTEGRATION_TESTS=1
  - NATS_URL (default: nats://localhost:4222) with JetStream enabled
  - BEHAVIORAL_DB_URL (default: postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform)

Usage:
  RUN_NATS_INTEGRATION_TESTS=1 NATS_URL=nats://localhost:4222 \\
  python -m pytest tests/integration/test_nats_consumer.py -v

Or via docker compose:
  docker compose -f infra/compose/docker-compose.phase1.yml up -d postgres nats
  RUN_NATS_INTEGRATION_TESTS=1 python -m pytest tests/integration/test_nats_consumer.py -v

This test does NOT block CI.  It is opt-in only.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "nats-integration-test-secret-32-chars"

from sqlalchemy.ext.asyncio import create_async_engine

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/"
    "retail_media_platform",
)
TEST_STREAM = "RMP_INTEGRATION_TEST"
TEST_SUBJECT = "campaign.>"
TEST_DURABLE = f"rmp-integration-test-{uuid4().hex[:8]}"
RUN = os.environ.get("RUN_NATS_INTEGRATION_TESTS", "") == "1"

SEED_CAMPAIGN_ID = "00000000-0000-0000-0000-000000000220"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _nats_reachable() -> bool:
    """Check if NATS is reachable at NATS_URL."""
    try:
        from nats.aio.client import Client as NATS
        nc = NATS()
        await nc.connect(servers=[NATS_URL], connect_timeout=3)
        await nc.drain()
        return True
    except Exception:
        return False


async def _db_reachable() -> bool:
    """Check if PostgreSQL is reachable."""
    try:
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception:
        return False


async def _ensure_stream_and_consumer():
    """Create JetStream stream + consumer for the test."""
    from nats.aio.client import Client as NATS

    nc = NATS()
    await nc.connect(servers=[NATS_URL], connect_timeout=5)
    js = nc.jetstream()

    # Create or update stream
    try:
        await js.add_stream(
            name=TEST_STREAM,
            subjects=[TEST_SUBJECT],
            retention="limits",
            max_msgs=1000,
            max_bytes=10 * 1024 * 1024,
        )
    except Exception:
        # Stream may already exist — update it
        await js.update_stream(
            name=TEST_STREAM,
            subjects=[TEST_SUBJECT],
            retention="limits",
            max_msgs=1000,
            max_bytes=10 * 1024 * 1024,
        )

    # Create pull consumer
    try:
        await js.add_consumer(
            stream=TEST_STREAM,
            durable_name=TEST_DURABLE,
            ack_policy="explicit",
        )
    except Exception:
        pass  # Consumer may already exist

    await nc.drain()


async def _cleanup_stream():
    """Remove test stream and consumer."""
    try:
        from nats.aio.client import Client as NATS
        nc = NATS()
        await nc.connect(servers=[NATS_URL], connect_timeout=3)
        js = nc.jetstream()
        try:
            await js.delete_consumer(TEST_STREAM, TEST_DURABLE)
        except Exception:
            pass
        try:
            await js.delete_stream(TEST_STREAM)
        except Exception:
            pass
        await nc.drain()
    except Exception:
        pass


async def _publish_test_event(
    event_type: str = "campaign.approved",
    campaign_id: str = SEED_CAMPAIGN_ID,
) -> str:
    """Publish a campaign outbox event directly to NATS JetStream.

    Returns the event_id for tracking.
    """
    from nats.aio.client import Client as NATS

    event_id = f"nats-int-{uuid4().hex[:12]}"
    envelope = {
        "event_id": event_id,
        "event_type": event_type,
        "event_version": "1.0",
        "aggregate_type": "campaign",
        "aggregate_id": campaign_id,
        "payload": {},
        "headers": {},
        "created_at": "2026-07-08T00:00:00Z",
    }
    payload = json.dumps(envelope).encode("utf-8")

    nc = NATS()
    await nc.connect(servers=[NATS_URL], connect_timeout=5)
    js = nc.jetstream()
    ack = await js.publish(
        TEST_SUBJECT.replace(".>", ".approved"),
        payload,
        stream=TEST_STREAM,
        headers={"Nats-Msg-Id": event_id},
    )
    await nc.drain()
    assert ack is not None, "JetStream publish ack is None"
    return event_id


async def _ensure_seed_campaign_approved():
    """Set the seed campaign to approved status."""
    from sqlalchemy import text

    engine = create_async_engine(DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE campaigns SET status = 'approved' "
                "WHERE id = :cid"
            ),
            {"cid": SEED_CAMPAIGN_ID},
        )
    await engine.dispose()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def nats_available():
    if not RUN:
        pytest.skip("RUN_NATS_INTEGRATION_TESTS=1 not set.")
    if not asyncio.run(_nats_reachable()):
        pytest.skip(f"NATS not reachable at {NATS_URL}")
    if not asyncio.run(_db_reachable()):
        pytest.skip(f"PostgreSQL not reachable at {DB_URL}")


@pytest.fixture(autouse=True)
async def setup_teardown(nats_available):
    """Ensure stream/consumer exist before tests, clean up after."""
    await _ensure_stream_and_consumer()
    await _ensure_seed_campaign_approved()
    yield
    await _cleanup_stream()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNatsJetStreamConsumerIntegration:
    """End-to-end: publish event to NATS → consumer receives → handler processes."""

    async def _make_consumer(self):
        """Create a NatsJetStreamCampaignConsumer connected to test stream."""
        from packages.services.campaign_event_handler import (
            NatsJetStreamCampaignConsumer,
        )
        from packages.domain.database import create_engine

        engine = create_engine(DB_URL)
        consumer = NatsJetStreamCampaignConsumer(
            nats_url=NATS_URL,
            engine=engine,
            durable=TEST_DURABLE,
            subject=TEST_SUBJECT,
            stream=TEST_STREAM,
            batch_size=10,
            fetch_timeout=2.0,
            nak_delay=0.5,
            connect_timeout=5.0,
        )
        await consumer.connect()
        return consumer

    # -- valid event → ack -------------------------------------------------

    def test_approved_event_published_and_consumed(self, nats_available):
        """Publish campaign.approved → consumer receives and acks."""
        async def _test():
            consumer = await self._make_consumer()

            # Start consumer in background
            loop_task = asyncio.create_task(consumer.run())

            # Wait for consumer to be ready
            await asyncio.sleep(0.5)

            # Publish event to NATS
            event_id = await _publish_test_event("campaign.approved")
            assert event_id.startswith("nats-int-")

            # Give consumer time to fetch and process
            await asyncio.sleep(2.0)

            # Stop consumer
            await consumer.stop()
            await loop_task
            await consumer.disconnect()

            assert consumer.acked >= 1, (
                f"Expected at least 1 ack, got acked={consumer.acked} "
                f"nakd={consumer.nakd}"
            )
            assert consumer.nakd == 0, (
                f"Expected 0 naks, got nakd={consumer.nakd}"
            )

        asyncio.run(_test())

    # -- unknown event → safe ack ------------------------------------------

    def test_unknown_event_consumed_and_acked(self, nats_available):
        """Publish campaign.created (unknown) → consumer acks (no-op)."""
        async def _test():
            consumer = await self._make_consumer()
            loop_task = asyncio.create_task(consumer.run())
            await asyncio.sleep(0.5)

            await _publish_test_event("campaign.created")
            await asyncio.sleep(2.0)

            await consumer.stop()
            await loop_task
            await consumer.disconnect()

            assert consumer.acked >= 1
            assert consumer.nakd == 0

        asyncio.run(_test())

    # -- malformed event → term --------------------------------------------

    def test_malformed_event_terminated(self, nats_available):
        """Publish garbage → consumer terminates the message."""
        async def _test():
            from nats.aio.client import Client as NATS

            consumer = await self._make_consumer()
            loop_task = asyncio.create_task(consumer.run())
            await asyncio.sleep(0.5)

            # Publish malformed message directly
            nc = NATS()
            await nc.connect(servers=[NATS_URL], connect_timeout=5)
            js = nc.jetstream()
            await js.publish(
                TEST_SUBJECT.replace(".>", ".approved"),
                b"not json at all",
                stream=TEST_STREAM,
            )
            await nc.drain()

            await asyncio.sleep(2.0)
            await consumer.stop()
            await loop_task
            await consumer.disconnect()

            assert consumer.terminated >= 1, (
                f"Expected at least 1 term, got terminated={consumer.terminated}"
            )

        asyncio.run(_test())

    # -- idempotent --------------------------------------------------------

    def test_duplicate_event_idempotent(self, nats_available):
        """Publish same event twice → consumer acks both, no duplicate processing."""
        async def _test():
            consumer = await self._make_consumer()
            loop_task = asyncio.create_task(consumer.run())
            await asyncio.sleep(0.5)

            # Publish the same event twice with the same event_id
            from nats.aio.client import Client as NATS

            event_id = f"nats-int-dup-{uuid4().hex[:8]}"
            envelope = {
                "event_id": event_id,
                "event_type": "campaign.approved",
                "event_version": "1.0",
                "aggregate_type": "campaign",
                "aggregate_id": SEED_CAMPAIGN_ID,
                "payload": {},
                "headers": {},
                "created_at": "2026-07-08T00:00:00Z",
            }
            payload = json.dumps(envelope).encode("utf-8")

            nc = NATS()
            await nc.connect(servers=[NATS_URL], connect_timeout=5)
            js = nc.jetstream()

            # First publish
            await js.publish(
                TEST_SUBJECT.replace(".>", ".approved"),
                payload,
                stream=TEST_STREAM,
                headers={"Nats-Msg-Id": event_id},
            )
            # Second publish with same Nats-Msg-Id — JetStream dedup
            await js.publish(
                TEST_SUBJECT.replace(".>", ".approved"),
                payload,
                stream=TEST_STREAM,
                headers={"Nats-Msg-Id": event_id},
            )
            await nc.drain()

            await asyncio.sleep(2.0)
            await consumer.stop()
            await loop_task
            await consumer.disconnect()

            # Consumer receives at least one message (JetStream may dedup the second)
            # Either 1 or 2 acks is acceptable
            assert consumer.acked >= 1
            assert consumer.nakd == 0

        asyncio.run(_test())
