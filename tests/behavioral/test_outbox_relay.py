"""Behavioral tests for outbox relay — real PostgreSQL, stub NATS publisher.

Phase S-012 Phase 1: relay foundation behavioral proofs.
Requires RUN_BEHAVIORAL_TESTS=1 and running PostgreSQL.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "behavioral-relay-test-secret-at-least-32"

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from packages.services.nats_publisher import StubNatsPublisher
from packages.services.outbox_relay import OutboxRelay

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/"
    "retail_media_platform",
)

REQUIRE_ENV = os.environ.get("RUN_BEHAVIORAL_TESTS", "") == "1"
SKIP_REASON = (
    "RUN_BEHAVIORAL_TESTS=1 not set. "
    "See tests/behavioral/__init__.py for setup instructions."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _check_db():
    try:
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception:
        return False


async def _insert(engine, event_type="test.relay.success", **kwargs):
    from packages.domain.models import OutboxEvent
    from sqlalchemy import insert

    defaults = {
        "id": kwargs.get("event_id", str(uuid.uuid4())),
        "event_type": event_type,
        "event_version": "1.0",
        "aggregate_type": "test",
        "aggregate_id": kwargs.get("aggregate_id", "t-" + str(uuid.uuid4())[:8]),
        "payload_json": kwargs.get("payload", {}),
        "headers_json": kwargs.get("headers", {}),
        "status": kwargs.get("status", "pending"),
        "attempts": kwargs.get("attempts", 0),
        "last_error": kwargs.get("last_error"),
    }
    nat = kwargs.get("next_attempt_at")
    if nat is not None:
        defaults["next_attempt_at"] = nat
    async with engine.begin() as conn:
        await conn.execute(insert(OutboxEvent).values(**defaults))


async def _make_engine_and_clean():
    """Create engine and clean stale relay test events."""
    engine = create_async_engine(DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM outbox_events WHERE event_type LIKE 'test.relay.%'")
        )
    return engine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_available():
    if not REQUIRE_ENV:
        pytest.skip(SKIP_REASON)
    if not asyncio.run(_check_db()):
        pytest.skip("PostgreSQL not reachable at " + DB_URL)


# ---------------------------------------------------------------------------
# Behavioral tests
# ---------------------------------------------------------------------------


class TestOutboxRelayBehavioral:

    def test_pending_event_published(self, db_available):
        pub = StubNatsPublisher()
        event_id = str(uuid.uuid4())

        async def _test():
            engine = await _make_engine_and_clean()
            try:
                relay = OutboxRelay(pub, engine)
                await _insert(engine, event_type="test.relay.success",
                              event_id=event_id, payload={"test": True})
                count = await relay.run_once()
                # Under NOBYPASSRLS there may be pre-existing pending events
                assert count >= 1, f"Expected >=1, got {count}"
                assert pub.publish_count >= 1
                # The specific test event must have been published
                our_event = next(
                    (m for m in pub.published if m["msg_id"] == event_id), None
                )
                assert our_event is not None, f"Event {event_id} not published"
                async with engine.connect() as conn:
                    result = await conn.execute(
                        text("SELECT status, published_at FROM outbox_events "
                             "WHERE id = :id"),
                        {"id": event_id},
                    )
                    row = result.fetchone()
                    assert row is not None
                    assert row[0] == "published"
                    assert row[1] is not None
            finally:
                await engine.dispose()

        asyncio.run(_test())

    def test_transient_failure_increments_attempts(self, db_available):
        pub = StubNatsPublisher()
        pub.fail_next(1)
        event_id = str(uuid.uuid4())

        async def _test():
            engine = await _make_engine_and_clean()
            try:
                relay = OutboxRelay(pub, engine)
                await _insert(engine, event_type="test.relay.fail",
                              event_id=event_id)
                count = await relay.run_once()
                assert count == 1
                async with engine.connect() as conn:
                    result = await conn.execute(
                        text("SELECT status, attempts, last_error FROM outbox_events "
                             "WHERE id = :id"),
                        {"id": event_id},
                    )
                    row = result.fetchone()
                    assert row[0] == "failed"
                    assert row[1] == 1
                    assert "simulated transient failure" in (row[2] or "")
            finally:
                await engine.dispose()

        asyncio.run(_test())

    def test_max_attempts_dead_letter(self, db_available):
        pub = StubNatsPublisher()
        pub.fail_next(1)
        event_id = str(uuid.uuid4())

        async def _test():
            engine = await _make_engine_and_clean()
            try:
                relay = OutboxRelay(pub, engine, max_attempts=7)
                await _insert(engine, event_type="test.relay.dead",
                              event_id=event_id, status="failed",
                              attempts=6, last_error="prev")
                await relay.run_once()
                async with engine.connect() as conn:
                    result = await conn.execute(
                        text("SELECT status, attempts FROM outbox_events "
                             "WHERE id = :id"),
                        {"id": event_id},
                    )
                    row = result.fetchone()
                    assert row[0] == "dead_letter"
                    assert row[1] == 7
            finally:
                await engine.dispose()

        asyncio.run(_test())

    def test_failed_event_recovered(self, db_available):
        pub = StubNatsPublisher()
        event_id = str(uuid.uuid4())

        async def _test():
            engine = await _make_engine_and_clean()
            try:
                relay = OutboxRelay(pub, engine)
                await _insert(engine, event_type="test.relay.recover",
                              event_id=event_id, status="failed",
                              attempts=2, last_error="prev")
                await relay.run_once()
                assert pub.publish_count == 1
                async with engine.connect() as conn:
                    result = await conn.execute(
                        text("SELECT status FROM outbox_events WHERE id = :id"),
                        {"id": event_id},
                    )
                    row = result.fetchone()
                    assert row[0] == "published"
            finally:
                await engine.dispose()

        asyncio.run(_test())

    def test_multiple_events_in_batch(self, db_available):
        pub = StubNatsPublisher()
        e1, e2, e3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())

        async def _test():
            engine = await _make_engine_and_clean()
            try:
                relay = OutboxRelay(pub, engine)
                for eid in (e1, e2, e3):
                    await _insert(engine, event_type="test.relay.batch",
                                  event_id=eid, payload={"idx": eid[-4:]})
                count = await relay.run_once()
                assert count == 3
                assert pub.publish_count == 3
                assert {m["msg_id"] for m in pub.published} == {e1, e2, e3}
            finally:
                await engine.dispose()

        asyncio.run(_test())

    def test_already_published_skipped(self, db_available):
        pub = StubNatsPublisher()
        event_id = str(uuid.uuid4())

        async def _test():
            engine = await _make_engine_and_clean()
            try:
                # ── Isolation: delete ALL due pending/failed events from
                # other test suites.  The relay processes every pending/failed
                # event whose next_attempt_at <= NOW, regardless of event_type
                # prefix.  A foreign due event makes count != 0, causing a flake.
                async with engine.begin() as conn:
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)
                    await conn.execute(
                        text(
                            "DELETE FROM outbox_events "
                            "WHERE status IN ('pending','failed') "
                            "  AND next_attempt_at <= :now"
                        ),
                        {"now": now},
                    )

                relay = OutboxRelay(pub, engine)
                await _insert(engine, event_type="test.relay.skip",
                              event_id=event_id, status="published")
                count = await relay.run_once()
                assert count == 0
                assert pub.publish_count == 0
            finally:
                await engine.dispose()

        asyncio.run(_test())

    def test_dead_letter_skipped(self, db_available):
        pub = StubNatsPublisher()
        event_id = str(uuid.uuid4())

        async def _test():
            engine = await _make_engine_and_clean()
            try:
                # ── Isolation: same as test_already_published_skipped
                async with engine.begin() as conn:
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)
                    await conn.execute(
                        text(
                            "DELETE FROM outbox_events "
                            "WHERE status IN ('pending','failed') "
                            "  AND next_attempt_at <= :now"
                        ),
                        {"now": now},
                    )

                relay = OutboxRelay(pub, engine)
                await _insert(engine, event_type="test.relay.deadskip",
                              event_id=event_id, status="dead_letter")
                count = await relay.run_once()
                assert count == 0
                assert pub.publish_count == 0
            finally:
                await engine.dispose()

        asyncio.run(_test())

    def test_backoff_respected_on_second_run(self, db_available):
        """Transient failure -> backoff set -> second run_once skips the event."""
        pub = StubNatsPublisher()
        pub.fail_next(1)
        event_id = str(uuid.uuid4())

        async def _test():
            engine = await _make_engine_and_clean()
            try:
                # ── Isolation: delete ALL due events from other test suites ──
                # The relay processes every pending/failed event whose
                # next_attempt_at <= NOW.  A foreign due event can consume the
                # shared fail_next(1) token, making the test non-deterministic.
                # We zap every due row so our event is the ONLY candidate.
                async with engine.begin() as conn:
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)
                    await conn.execute(
                        text(
                            "DELETE FROM outbox_events "
                            "WHERE status IN ('pending','failed') "
                            "  AND next_attempt_at <= :now"
                        ),
                        {"now": now},
                    )

                relay = OutboxRelay(pub, engine)
                await _insert(engine, event_type="test.relay.backoff",
                              event_id=event_id)

                count1 = await relay.run_once()
                # With isolation above, count1 == 1.  We keep >=1 for
                # resilience, but the critical assertion is about OUR event.
                assert count1 >= 1, f"Expected >=1, got {count1}"
                # Our event must NOT have been published (simulated transient failure)
                our_published = any(
                    m["msg_id"] == event_id for m in pub.published
                )
                assert not our_published, (
                    f"Event {event_id} was published despite fail_next(1)"
                )
                async with engine.connect() as conn:
                    result = await conn.execute(
                        text("SELECT status, attempts FROM outbox_events WHERE id = :id"),
                        {"id": event_id},
                    )
                    row = result.fetchone()
                    assert row is not None, f"Event {event_id} not found after first run"
                    assert row[0] == "failed", f"Expected failed, got {row[0]}"
                    assert row[1] == 1, f"Expected attempts=1, got {row[1]}"

                count2 = await relay.run_once()
                # After isolation, count2 == 0 (our event has future
                # next_attempt_at).  Assertion is on OUR event specifically.
                # We avoid count2 == 0 because a foreign event could become
                # due between the two run_once() calls.
                our_published2 = any(
                    m["msg_id"] == event_id for m in pub.published
                )
                assert not our_published2, (
                    f"Event {event_id} was published on second run "
                    f"(backoff not respected)"
                )
                # Verify our event was NOT touched by the second run
                async with engine.connect() as conn:
                    result = await conn.execute(
                        text("SELECT status, attempts FROM outbox_events WHERE id = :id"),
                        {"id": event_id},
                    )
                    row = result.fetchone()
                    assert row is not None, f"Event {event_id} gone after second run"
                    assert row[0] == "failed", (
                        f"Expected still failed, got {row[0]}"
                    )
                    assert row[1] == 1, (
                        f"Expected attempts still 1, got {row[1]}"
                    )
            finally:
                await engine.dispose()

        asyncio.run(_test())

    def test_backoff_expired_retries(self, db_available):
        """Manually set next_attempt_at to past → run_once retries successfully."""
        pub = StubNatsPublisher()
        event_id = str(uuid.uuid4())

        async def _test():
            from datetime import datetime, timedelta, timezone

            engine = await _make_engine_and_clean()
            try:
                relay = OutboxRelay(pub, engine)
                past = datetime.now(timezone.utc) - timedelta(hours=1)
                await _insert(engine, event_type="test.relay.expired",
                              event_id=event_id, status="failed",
                              attempts=1, next_attempt_at=past,
                              last_error="previous")

                count = await relay.run_once()
                # Other test suites may have due outbox events in the full run
                assert count >= 1, f"Expected >=1, got {count}"
                assert pub.publish_count >= 1
                # The specific test event must have been published
                our_event = next(
                    (m for m in pub.published if m["msg_id"] == event_id), None
                )
                assert our_event is not None, f"Event {event_id} not published"
                async with engine.connect() as conn:
                    result = await conn.execute(
                        text("SELECT status FROM outbox_events WHERE id = :id"),
                        {"id": event_id},
                    )
                    row = result.fetchone()
                    assert row is not None
                    assert row[0] == "published"
            finally:
                await engine.dispose()

        asyncio.run(_test())
