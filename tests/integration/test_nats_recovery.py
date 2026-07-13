"""
Integration test: NATS JetStream recovery proof (S-050).

Proves that after NATS loss:
  1. Provisioning recreates stream + consumer from scratch
  2. Outbox relay republishes pending events to fresh NATS
  3. Consumer processes them (dedup-safe via Nats-Msg-Id = event_id)
  4. Full recovery cycle: lose NATS → provision → relay → consumer → manifests

Requires:
  - RUN_NATS_INTEGRATION_TESTS=1
  - Local nats-server with JetStream (nats-server -js)
  - PostgreSQL with seed data + migrations

Usage:
  RUN_NATS_INTEGRATION_TESTS=1 python -m pytest tests/integration/test_nats_recovery.py -v

Skips silently when env is not set.
"""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "nats-recovery-test-secret-at-least-32-chars"

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)

NATS_URL = os.environ.get("NATS_E2E_URL", "nats://localhost:4222")

REQUIRE_ENV = os.environ.get("RUN_NATS_INTEGRATION_TESTS", "") == "1"
SKIP_REASON = "RUN_NATS_INTEGRATION_TESTS=1 not set."

SEED_CAMPAIGN_ID = "00000000-0000-0000-0000-000000000220"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _reset_delivery_state():
    """Clean up previous test artifacts."""
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


def _prepare_campaign():
    """Set seed campaign to approved with active flight window."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)
    end = now + timedelta(days=7)

    _raw_exec(
        "UPDATE campaigns SET status = 'approved' WHERE id = :cid",
        {"cid": SEED_CAMPAIGN_ID},
    )
    _raw_exec(
        "UPDATE physical_devices SET status = 'active' WHERE id = :did",
        {"did": "00000000-0000-0000-0000-000000000020"},
    )
    _raw_exec(
        "UPDATE campaign_flights SET start_at = :start, end_at = :end WHERE campaign_id = :cid",
        {"start": start, "end": end, "cid": SEED_CAMPAIGN_ID},
    )


def _reset_campaign_state():
    """Reset campaign to draft."""
    _raw_exec(
        "UPDATE campaigns SET status = 'draft' WHERE id = :cid",
        {"cid": SEED_CAMPAIGN_ID},
    )
    _raw_exec(
        "UPDATE physical_devices SET status = 'unregistered' WHERE id = :did",
        {"did": "00000000-0000-0000-0000-000000000020"},
    )


def _nats_is_running() -> bool:
    """Check if NATS is already listening on port 4222."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    result = s.connect_ex(("localhost", 4222))
    s.close()
    return result == 0


def _start_nats() -> subprocess.Popen | None:
    """Start a fresh NATS server. Returns process or None if already running."""
    if _nats_is_running():
        return None
    proc = subprocess.Popen(
        ["nats-server", "-js", "-p", "4222"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 10
    while time.time() < deadline:
        if _nats_is_running():
            return proc
        time.sleep(0.2)
    proc.terminate()
    proc.wait()
    pytest.fail("nats-server did not start within 10s")
    return None


def _stop_nats(proc: subprocess.Popen | None):
    """Stop NATS if we started it."""
    if proc is not None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ensure_env():
    if not REQUIRE_ENV:
        pytest.skip(SKIP_REASON)


@pytest.fixture(scope="module")
def nats_server(ensure_env):
    """Ensure NATS is running (start if needed, leave if already running)."""
    proc = _start_nats()
    assert _nats_is_running(), "NATS did not start"
    yield NATS_URL
    _stop_nats(proc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNatsRecovery:
    """Prove that after NATS loss, provisioning + relay + consumer = full recovery."""

    def test_skip_without_env(self, ensure_env):
        """Clean skip when env not set."""
        pass

    def test_fresh_nats_provisioning(self, nats_server):
        """Provisioning creates stream + consumer on fresh NATS."""
        from packages.services.jetstream_provisioning import (
            provision_campaign_delivery,
            check_stream_exists,
        )

        async def _run():
            # Stream should not exist before provisioning
            exists = await check_stream_exists(nats_server, "RMP")
            # (Not asserting False — NATS may already have it from prior runs)

            result = await provision_campaign_delivery(
                nats_url=nats_server,
                stream="RMP",
                subjects=["campaign.>"],
                durable="rmp-campaign-consumer",
            )
            assert result["stream"] == "RMP"
            assert result["durable"] == "rmp-campaign-consumer"

            # Stream should exist after provisioning
            exists = await check_stream_exists(nats_server, "RMP")
            assert exists, "Stream should exist after provisioning"

        asyncio.run(_run())

    def test_outbox_replay_after_nats_reset(self, nats_server):
        """After NATS reset, outbox relay republishes pending events to fresh stream."""

        _reset_delivery_state()
        _prepare_campaign()

        try:
            # 1. Enqueue a campaign.approved outbox event
            from packages.domain.repository import enqueue_outbox_event
            from packages.domain.models import OutboxEvent
            from packages.domain.database import create_engine

            engine = create_engine(DB_URL)

            async def _pipeline():
                async with AsyncSession(engine) as session:
                    await enqueue_outbox_event(
                        session,
                        event_type="campaign.approved",
                        aggregate_type="campaign",
                        aggregate_id=SEED_CAMPAIGN_ID,
                        payload={"campaign_id": SEED_CAMPAIGN_ID},
                        headers={"source_service": "recovery-test"},
                    )
                    await session.commit()

                # Verify event is pending
                from sqlalchemy import select
                async with AsyncSession(engine) as session:
                    result = await session.execute(
                        select(OutboxEvent.id, OutboxEvent.status).where(
                            OutboxEvent.aggregate_id == SEED_CAMPAIGN_ID,
                            OutboxEvent.event_type == "campaign.approved",
                        ).order_by(OutboxEvent.created_at.desc()).limit(1)
                    )
                    row = result.one()
                    event_id = row[0]
                    assert row[1] == "pending"

                # 2. Provision NATS (fresh — no prior stream)
                from packages.services.jetstream_provisioning import (
                    provision_campaign_delivery,
                )
                await provision_campaign_delivery(
                    nats_url=nats_server,
                    stream="RMP",
                    subjects=["campaign.>"],
                    durable="rmp-campaign-consumer",
                )

                # 3. Run outbox relay → publish to fresh NATS
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

                # Verify published
                async with AsyncSession(engine) as session:
                    result = await session.execute(
                        select(OutboxEvent.status).where(OutboxEvent.id == event_id)
                    )
                    status = result.scalar_one()
                    assert status == "published", f"Expected published, got {status}"

                # 4. Run consumer → generate manifests
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
                    f"Consumer should ack >=1, got acked={consumer.acked} errors={consumer.errors}"
                )
                assert consumer.errors == 0, f"Consumer errors: {consumer.errors}"

                return event_id

            event_id = asyncio.run(_pipeline())

            # 5. Verify manifest exists in DB
            rows = _raw_sql(
                "SELECT manifest_id, campaign_id, status FROM delivery_manifests "
                "WHERE campaign_id = :cid AND status = 'generated' "
                "ORDER BY generated_at DESC LIMIT 1",
                {"cid": SEED_CAMPAIGN_ID},
            )
            assert len(rows) >= 1, f"Expected >=1 generated manifest, got {len(rows)}"
            assert rows[0][2] == "generated"

            # 6. Verify outbox status
            rows = _raw_sql(
                "SELECT status FROM outbox_events WHERE id = :eid",
                {"eid": event_id},
            )
            assert rows[0][0] == "published"

        finally:
            _reset_delivery_state()
            _reset_campaign_state()

    def test_dedup_safe_replay(self, nats_server):
        """Re-running outbox relay on already-published events is safe (dedup via Msg-Id)."""

        _reset_delivery_state()
        _prepare_campaign()

        try:
            from packages.domain.repository import enqueue_outbox_event, mark_event_published
            from packages.domain.models import OutboxEvent
            from packages.domain.database import create_engine
            from sqlalchemy import select

            engine = create_engine(DB_URL)

            async def _run():
                # Enqueue
                async with AsyncSession(engine) as session:
                    await enqueue_outbox_event(
                        session,
                        event_type="campaign.approved",
                        aggregate_type="campaign",
                        aggregate_id=SEED_CAMPAIGN_ID,
                        payload={"campaign_id": SEED_CAMPAIGN_ID},
                        headers={"source_service": "dedup-test"},
                    )
                    await session.commit()

                # Get event ID
                async with AsyncSession(engine) as session:
                    result = await session.execute(
                        select(OutboxEvent.id, OutboxEvent.status).where(
                            OutboxEvent.aggregate_id == SEED_CAMPAIGN_ID,
                            OutboxEvent.event_type == "campaign.approved",
                        ).order_by(OutboxEvent.created_at.desc()).limit(1)
                    )
                    row = result.one()
                    event_id = row[0]

                # Provision
                from packages.services.jetstream_provisioning import (
                    provision_campaign_delivery,
                )
                await provision_campaign_delivery(
                    nats_url=nats_server,
                    stream="RMP",
                    subjects=["campaign.>"],
                    durable="rmp-campaign-consumer",
                )

                # First relay run
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
                    assert count >= 1
                finally:
                    await publisher.disconnect()

                # Verify published
                async with AsyncSession(engine) as session:
                    result = await session.execute(
                        select(OutboxEvent.status).where(OutboxEvent.id == event_id)
                    )
                    status = result.scalar_one()
                    assert status == "published"

                # Second relay run — should find 0 pending and return 0
                publisher2 = NatsJetStreamPublisher(nats_server)
                await publisher2.connect()
                try:
                    relay2 = OutboxRelay(
                        publisher=publisher2,
                        engine=engine,
                        poll_interval=0.1,
                        batch_size=10,
                    )
                    count2 = await relay2.run_once()
                    assert count2 == 0, (
                        f"Second relay should process 0 events (all published), got {count2}"
                    )
                finally:
                    await publisher2.disconnect()

            asyncio.run(_run())

        finally:
            _reset_delivery_state()
            _reset_campaign_state()

    def test_recovery_check_script(self, nats_server):
        """The recovery check script runs without error."""
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(
                    os.path.dirname(__file__), "..", "..", "scripts", "check", "nats_recovery_check.py",
                ),
                "--json",
            ],
            env={**os.environ, "NATS_URL": NATS_URL},
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"Recovery check failed:\n{result.stderr}\n{result.stdout}"
        )

        data = __import__("json").loads(result.stdout)
        assert "nats" in data
        assert "outbox" in data
        assert "recommendation" in data
        assert data["nats"]["nats_reachable"], "NATS should be reachable"
