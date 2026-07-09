"""
E2E integration test: NATS delivery pipeline (B2).

Proves the full path:
  campaign approved → outbox relay → NATS JetStream →
  campaign consumer → manifest generation.

The manifest row is verified in the delivery_manifests table.
Device gateway HTTP fetch is deferred to B3.

Requires:
  - RUN_NATS_INTEGRATION_TESTS=1
  - Local nats-server with JetStream (nats-server -js)
  - PostgreSQL with seed data + migrations
  - Behavioral seed (RUN_BEHAVIORAL_TESTS=1 setup already done)

Usage:
  RUN_NATS_INTEGRATION_TESTS=1 python -m pytest tests/integration/test_nats_e2e.py -v

Skips silently when env is not set.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "nats-e2e-test-secret-at-least-32-chars"

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)

NATS_URL = os.environ.get("NATS_E2E_URL", "nats://localhost:4222")

REQUIRE_ENV = os.environ.get("RUN_NATS_INTEGRATION_TESTS", "") == "1"
SKIP_REASON = "RUN_NATS_INTEGRATION_TESTS=1 not set."

# Seed IDs — must match apps/control-api/seed.py
SEED_CAMPAIGN_ID = "00000000-0000-0000-0000-000000000220"
SEED_DEVICE_ID = "00000000-0000-0000-0000-000000000020"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raw_sql(sql: str, params=None):
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.connect() as conn:
            await conn.execute(
                text("SELECT set_config('app.rmp_is_admin', 'true', false)")
            )
            await conn.commit()
            result = await conn.execute(text(sql), params or {})
            rows = result.fetchall()
        await engine.dispose()
        return rows

    return asyncio.run(_run())


def _raw_exec(sql: str, params=None):
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.begin() as conn:
            await conn.execute(
                text("SELECT set_config('app.rmp_is_admin', 'true', true)")
            )
            for stmt in sql.split(";"):
                s = stmt.strip()
                if s and not s.startswith("--"):
                    await conn.execute(text(s), params or {})
        await engine.dispose()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ensure_env():
    if not REQUIRE_ENV:
        pytest.skip(SKIP_REASON)


@pytest.fixture(scope="module")
def nats_server(ensure_env):
    """Start a local nats-server with JetStream for the test module."""
    import subprocess
    import time

    import socket

    # Check if NATS is already running
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    result = s.connect_ex(("localhost", 4222))
    s.close()
    if result == 0:
        # NATS already running — don't start another
        yield NATS_URL
        return

    proc = subprocess.Popen(
        ["nats-server", "-js", "-p", "4222"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Wait for it to be ready
    deadline = time.time() + 10
    started = False
    while time.time() < deadline:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        if s.connect_ex(("localhost", 4222)) == 0:
            s.close()
            started = True
            break
        s.close()
        time.sleep(0.2)
    if not started:
        proc.terminate()
        proc.wait()
        pytest.fail("nats-server did not start within 10s")

    yield NATS_URL

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# ---------------------------------------------------------------------------
# Prepare seed campaign for delivery
# ---------------------------------------------------------------------------


def _prepare_campaign():
    """Set seed campaign to approved, device to active, flight to current window."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)
    end = now + timedelta(days=7)

    _raw_exec(
        """
        UPDATE campaigns SET status = 'approved' WHERE id = :cid
        """,
        {"cid": SEED_CAMPAIGN_ID},
    )
    _raw_exec(
        """
        UPDATE physical_devices SET status = 'active' WHERE id = :did
        """,
        {"did": SEED_DEVICE_ID},
    )
    _raw_exec(
        """
        UPDATE campaign_flights SET start_at = :start, end_at = :end
        WHERE campaign_id = :cid
        """,
        {"start": start, "end": end, "cid": SEED_CAMPAIGN_ID},
    )


def _reset_delivery_state():
    """Remove previously generated manifests/outbox events."""
    _raw_exec(
        """
        DELETE FROM delivery_attempts;
        DELETE FROM delivery_manifest_assets;
        DELETE FROM delivery_manifest_surfaces;
        DELETE FROM delivery_manifests;
        DELETE FROM delivery_plans;
        DELETE FROM outbox_events WHERE event_type LIKE 'delivery.manifest.%';
        DELETE FROM outbox_events WHERE event_type = 'campaign.approved'
            AND aggregate_id = :cid;
    """,
        {"cid": SEED_CAMPAIGN_ID},
    )


def _reset_campaign_state():
    """Reset campaign to draft, device to unregistered."""
    _raw_exec(
        "UPDATE campaigns SET status = 'draft' WHERE id = :cid",
        {"cid": SEED_CAMPAIGN_ID},
    )
    _raw_exec(
        "UPDATE physical_devices SET status = 'unregistered' WHERE id = :did",
        {"did": SEED_DEVICE_ID},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNatsE2EPipeline:
    """End-to-end: approval → relay → NATS → consumer → manifest row in DB."""

    def test_approval_to_manifest_via_nats(
        self, nats_server
    ):
        """Full pipeline: real NATS JetStream from outbox to manifest to device fetch."""
        # ── 0. Setup ─────────────────────────────────────────────────
        _reset_delivery_state()
        _prepare_campaign()

        try:
            # ── 1. Write campaign.approved outbox event ──────────────
            from packages.domain.repository import enqueue_outbox_event
            from packages.domain.database import create_engine

            engine = create_engine(DB_URL)

            # ── Run entire NATS pipeline in a single event loop ─────
            async def _pipeline():
                # 1a. Enqueue outbox
                async with AsyncSession(engine) as session:
                    await enqueue_outbox_event(
                        session,
                        event_type="campaign.approved",
                        aggregate_type="campaign",
                        aggregate_id=SEED_CAMPAIGN_ID,
                        payload={"campaign_id": SEED_CAMPAIGN_ID},
                        headers={"source_service": "e2e-test"},
                    )
                    await session.commit()

                # 1b. Read back event ID
                from sqlalchemy import select, text as sqla_text
                from packages.domain.models import OutboxEvent
                async with AsyncSession(engine) as session:
                    result = await session.execute(
                        select(OutboxEvent.id, OutboxEvent.status).where(
                            OutboxEvent.aggregate_id == SEED_CAMPAIGN_ID,
                            OutboxEvent.event_type == "campaign.approved",
                        ).order_by(OutboxEvent.created_at.desc()).limit(1)
                    )
                    row = result.one()
                    event_id = row[0]
                    assert row[1] == "pending", f"Expected pending, got {row[1]}"

                # 2. Provision NATS JetStream
                from packages.services.jetstream_provisioning import (
                    provision_campaign_delivery,
                )
                provision_result = await provision_campaign_delivery(
                    nats_url=nats_server,
                    stream="RMP",
                    subjects=["campaign.>"],
                    durable="rmp-campaign-consumer",
                )
                assert provision_result["stream"] == "RMP"

                # 3. Run outbox relay → publish to NATS
                from packages.services.outbox_relay import OutboxRelay
                from packages.services.nats_publisher import NatsJetStreamPublisher

                publisher = NatsJetStreamPublisher(nats_server)
                await publisher.connect()
                try:
                    relay = OutboxRelay(
                        publisher=publisher,
                        engine=engine,
                        poll_interval=0.1,
                        batch_size=10,
                    )
                    count = await relay.run_once()
                    assert count >= 1, f"Relay should process >=1 event, got {count}"
                finally:
                    await publisher.disconnect()

                # Verify outbox event marked published
                async with AsyncSession(engine) as session:
                    result = await session.execute(
                        select(OutboxEvent.status).where(
                            OutboxEvent.id == event_id,
                        )
                    )
                    status = result.scalar_one()
                    assert status == "published", f"Expected published, got {status}"

                # 4. Run campaign consumer → generate manifests
                from packages.services.campaign_event_handler import (
                    NatsJetStreamCampaignConsumer,
                )

                consumer = NatsJetStreamCampaignConsumer(
                    nats_url=nats_server,
                    engine=engine,
                    durable="rmp-campaign-consumer",
                    subject="campaign.>",
                    stream="RMP",
                    batch_size=1,
                    fetch_timeout=5.0,
                )
                await consumer.connect()
                try:
                    task = asyncio.create_task(consumer.run())
                    deadline = asyncio.get_event_loop().time() + 10.0
                    while asyncio.get_event_loop().time() < deadline:
                        if consumer.acked > 0 or consumer.errors > 0:
                            break
                        await asyncio.sleep(0.2)
                    await consumer.stop()
                    try:
                        await asyncio.wait_for(task, timeout=5.0)
                    except asyncio.TimeoutError:
                        pass
                finally:
                    await consumer.disconnect()

                assert consumer.acked >= 1, (
                    f"Consumer should ack >=1, got acked={consumer.acked} "
                    f"errors={consumer.errors}"
                )
                assert consumer.errors == 0, f"Consumer errors: {consumer.errors}"

                return event_id

            event_id = asyncio.run(_pipeline())

            # ── 5. Verify delivery manifest exists ──────────────────
            rows = _raw_sql(
                "SELECT manifest_id, campaign_id, status FROM delivery_manifests "
                "WHERE campaign_id = :cid AND status = 'generated' "
                "ORDER BY generated_at DESC LIMIT 1",
                {"cid": SEED_CAMPAIGN_ID},
            )
            assert len(rows) >= 1, (
                f"Expected >=1 generated manifest, got {len(rows)}"
            )
            manifest_id = rows[0][0]
            assert rows[0][1] == SEED_CAMPAIGN_ID, (
                f"Wrong campaign_id: {rows[0][1]}"
            )
            assert rows[0][2] == "generated"

            # ── 6. Verify outbox event marked published ─────────────
            rows = _raw_sql(
                "SELECT status FROM outbox_events WHERE id = :eid",
                {"eid": event_id},
            )
            assert rows[0][0] == "published", (
                f"Expected published, got {rows[0][0]}"
            )

        finally:
            # ── Cleanup ────────────────────────────────────────────
            _reset_delivery_state()
            _reset_campaign_state()
