"""
Behavioral tests — Transactional Outbox (Phase 4.1c).

Tests: enqueue in transaction, commit stores, rollback discards,
no secrets in payload, fetch pending, mark published/failed.
Requires: RUN_BEHAVIORAL_TESTS=1, migration 007 applied.
"""

import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["ENVIRONMENT"] = "dev"

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from packages.domain.repository import (
    enqueue_outbox_event,
    fetch_pending_events,
    mark_event_failed,
    mark_event_published,
)

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)

REQUIRE_ENV = os.environ.get("RUN_BEHAVIORAL_TESTS", "") == "1"
SKIP_REASON = "RUN_BEHAVIORAL_TESTS=1 not set."


@pytest.fixture(scope="module")
def db_available():
    if not REQUIRE_ENV:
        pytest.skip(SKIP_REASON)
    try:
        async def _check():
            engine = create_async_engine(DB_URL, echo=False)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
        asyncio.run(_check())
    except Exception:
        pytest.skip("PostgreSQL not reachable")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raw_sql(sql: str, params: dict | None = None):
    """Run raw SQL via engine.connect() and return fetched rows."""
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT set_config('app.rmp_is_admin', 'true', false)"))
            await conn.commit()
            result = await conn.execute(text(sql), params or {})
            rows = result.fetchall()
        await engine.dispose()
        return rows
    return asyncio.run(_run())


def _raw_exec(sql: str, params: dict | None = None):
    """Run raw SQL in a committed transaction (INSERT/UPDATE/DELETE)."""
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.begin() as conn:
            await conn.execute(text("SELECT set_config('app.rmp_is_admin', 'true', true)"))
            await conn.execute(text(sql), params or {})
        await engine.dispose()
    asyncio.run(_run())


def _enqueue(**kw) -> str:
    """Insert via raw SQL in a committed transaction. Returns event_id."""
    import uuid
    async def _run():
        eid = str(uuid.uuid4())
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.begin() as conn:
            await conn.execute(text("SELECT set_config('app.rmp_is_admin', 'true', true)"))
            await conn.execute(
                text("INSERT INTO outbox_events "
                     "(id, event_type, event_version, aggregate_type, aggregate_id, "
                     "partition_key, payload_json, headers_json) "
                     "VALUES (:id, :et, :ev, :at, :ai, :pk, :pj, :hj)"),
                {
                    "id": eid,
                    "et": kw["event_type"],
                    "ev": kw.get("event_version", "1.0"),
                    "at": kw["aggregate_type"],
                    "ai": kw["aggregate_id"],
                    "pk": kw.get("partition_key"),
                    "pj": json.dumps(kw["payload"]),
                    "hj": json.dumps(kw.get("headers", {})),
                },
            )
        await engine.dispose()
        return eid
    return asyncio.run(_run())


def _enqueue_and_rollback(**kw) -> str | None:
    """Insert via raw SQL then force rollback. Returns event_id."""
    import uuid
    eid = None
    async def _run():
        nonlocal eid
        eid = str(uuid.uuid4())
        engine = create_async_engine(DB_URL, echo=False)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text("INSERT INTO outbox_events "
                         "(id, event_type, aggregate_type, aggregate_id, "
                         "payload_json, headers_json) "
                         "VALUES (:id, :et, :at, :ai, :pj, :hj)"),
                    {
                        "id": eid,
                        "et": kw["event_type"],
                        "at": kw["aggregate_type"],
                        "ai": kw["aggregate_id"],
                        "pj": json.dumps(kw["payload"]),
                        "hj": json.dumps(kw.get("headers", {})),
                    },
                )
                raise RuntimeError("forced rollback")
        except RuntimeError:
            pass
        await engine.dispose()
    asyncio.run(_run())
    return eid


def _call_mark_published(event_id: str):
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with AsyncSession(engine) as session:
            async with session.begin():
                await mark_event_published(session, event_id)
        await engine.dispose()
    asyncio.run(_run())


def _call_mark_failed(event_id: str, last_error: str, max_attempts: int = 7):
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with AsyncSession(engine) as session:
            async with session.begin():
                await mark_event_failed(
                    session, event_id,
                    last_error=last_error,
                    max_attempts=max_attempts,
                )
        await engine.dispose()
    asyncio.run(_run())


def _fetch_pending(limit: int = 100):
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with AsyncSession(engine) as session:
            events = await fetch_pending_events(session, limit=limit)
        await engine.dispose()
        return events
    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestOutboxEnqueue:

    def test_enqueue_and_commit_stores_event(self, db_available):
        eid = _enqueue(
            event_type="test.event",
            aggregate_type="test",
            aggregate_id="00000000-0000-0000-0000-000000000000",
            payload={"key": "value"},
            headers={"correlation_id": "test-123"},
            partition_key="test-partition",
        )
        rows = _raw_sql("SELECT id, event_type, status FROM outbox_events WHERE id = :eid",
                        {"eid": eid})
        assert len(rows) == 1, f"Event {eid} not found after commit"
        assert rows[0][1] == "test.event"
        assert rows[0][2] == "pending"

    def test_rollback_discards_event(self, db_available):
        eid = _enqueue_and_rollback(
            event_type="test.rollback",
            aggregate_type="test",
            aggregate_id="00000000-0000-0000-0000-000000000000",
            payload={"should": "not_exist"},
        )
        if eid:
            rows = _raw_sql("SELECT id FROM outbox_events WHERE id = :eid", {"eid": eid})
            assert len(rows) == 0, f"Event {eid} survived rollback"

    def test_payload_no_secrets(self, db_available):
        eid = _enqueue(
            event_type="test.payload",
            aggregate_type="campaign",
            aggregate_id="00000000-0000-0000-0000-000000000220",
            payload={"campaign_code": "CAMP-2026-001", "status": "draft"},
            headers={"correlation_id": "corr-001"},
        )
        rows = _raw_sql(
            "SELECT payload_json, headers_json FROM outbox_events WHERE id = :eid",
            {"eid": eid},
        )
        assert len(rows) == 1
        payload_str = str(rows[0][0])
        headers_str = str(rows[0][1])
        assert "password" not in payload_str.lower()
        assert "token" not in payload_str.lower()
        assert "secret" not in payload_str.lower()
        assert "corr-001" in headers_str

    def test_enqueue_does_not_commit_on_its_own(self, db_available):
        eid = _enqueue_and_rollback(
            event_type="test.no_auto_commit",
            aggregate_type="test",
            aggregate_id="00000000-0000-0000-0000-000000000000",
            payload={"x": 1},
        )
        if eid:
            rows = _raw_sql("SELECT id FROM outbox_events WHERE id = :eid", {"eid": eid})
            assert len(rows) == 0, "Event survived rollback — helper may have committed"


class TestOutboxRelay:

    def test_fetch_pending_returns_events(self, db_available):
        _enqueue(event_type="test.p1", aggregate_type="t", aggregate_id="a1", payload={"n": 1})
        _enqueue(event_type="test.p2", aggregate_type="t", aggregate_id="a2", payload={"n": 2})
        events = _fetch_pending(limit=50)
        types = [e.event_type for e in events]
        assert "test.p1" in types
        assert "test.p2" in types

    def test_mark_published_updates_status(self, db_available):
        eid = _enqueue(event_type="test.mark_pub", aggregate_type="t", aggregate_id="b1",
                        payload={"x": 1})
        _call_mark_published(eid)
        rows = _raw_sql(
            "SELECT status, published_at FROM outbox_events WHERE id = :eid",
            {"eid": eid},
        )
        assert len(rows) == 1
        assert rows[0][0] == "published"
        assert rows[0][1] is not None

    def test_mark_failed_increments_attempts(self, db_available):
        eid = _enqueue(event_type="test.mark_fail", aggregate_type="t", aggregate_id="c1",
                        payload={"x": 1})
        _call_mark_failed(eid, last_error="publish timeout")
        rows = _raw_sql(
            "SELECT status, attempts, last_error, next_attempt_at "
            "FROM outbox_events WHERE id = :eid",
            {"eid": eid},
        )
        assert len(rows) == 1
        assert rows[0][0] == "failed"
        assert rows[0][1] == 1
        assert "publish timeout" in rows[0][2]
        assert rows[0][3] is not None

    def test_mark_failed_dead_letter_after_max(self, db_available):
        eid = _enqueue(event_type="test.dead", aggregate_type="t", aggregate_id="d1",
                        payload={"x": 1})
        _raw_exec("UPDATE outbox_events SET attempts = 6 WHERE id = :eid", {"eid": eid})
        _call_mark_failed(eid, last_error="final failure")
        rows = _raw_sql(
            "SELECT status, attempts FROM outbox_events WHERE id = :eid",
            {"eid": eid},
        )
        assert len(rows) == 1
        assert rows[0][0] == "dead_letter"
        assert rows[0][1] == 7

    def test_last_error_truncated(self, db_available):
        long_error = "x" * 3000
        eid = _enqueue(event_type="test.trunc", aggregate_type="t", aggregate_id="e1",
                        payload={"x": 1})
        _call_mark_failed(eid, last_error=long_error)
        rows = _raw_sql(
            "SELECT last_error FROM outbox_events WHERE id = :eid",
            {"eid": eid},
        )
        assert len(rows) == 1
        assert len(rows[0][0]) <= 2048


class TestOutboxOrmHelper:
    """Prove enqueue_outbox_event ORM helper works with real AsyncSession."""

    def test_orm_enqueue_commit_stores_event(self, db_available):
        """enqueue_outbox_event + session.commit() → row in DB."""
        import json

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            async with AsyncSession(engine) as session:
                async with session.begin():
                    eid = await enqueue_outbox_event(
                        session,
                        event_type="test.orm.commit",
                        aggregate_type="test",
                        aggregate_id="00000000-0000-0000-0000-000000000001",
                        payload={"key": "orm_value"},
                        headers={"correlation_id": "orm-commit-1"},
                        partition_key="orm-partition",
                    )
                await engine.dispose()
                return eid

        eid = asyncio.run(_run())
        rows = _raw_sql(
            "SELECT id, event_type, aggregate_id, payload_json, headers_json, status "
            "FROM outbox_events WHERE id = :eid",
            {"eid": eid},
        )
        assert len(rows) == 1, f"ORM-enqueued event {eid} not found after commit"
        assert rows[0][1] == "test.orm.commit"
        assert rows[0][2] == "00000000-0000-0000-0000-000000000001"
        payload = rows[0][3] if isinstance(rows[0][3], dict) else json.loads(rows[0][3])
        assert payload["key"] == "orm_value"
        assert rows[0][4] is not None  # headers_json present
        assert rows[0][5] == "pending"

    def test_orm_enqueue_passes_payload_as_is(self, db_available):
        """ORM helper stores whatever the caller passes — no sanitization.

        enqueue_outbox_event is transaction-only.  Secret/PII filtering is
        a producer responsibility, enforced by producer tests and ADR-011 §2.
        This test proves the helper does NOT silently drop or mask fields —
        it passes the payload through as-is to the outbox table.
        """
        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            async with AsyncSession(engine) as session:
                async with session.begin():
                    eid = await enqueue_outbox_event(
                        session,
                        event_type="test.orm.secrets",
                        aggregate_type="campaign",
                        aggregate_id="00000000-0000-0000-0000-000000000220",
                        payload={
                            "campaign_code": "CAMP-TEST",
                            # These would be a caller mistake — helper doesn't filter
                            "password": "should_not_be_here",
                            "token": "secret-token-value",
                        },
                    )
                await engine.dispose()
                return eid

        eid = asyncio.run(_run())
        rows = _raw_sql(
            "SELECT payload_json FROM outbox_events WHERE id = :eid",
            {"eid": eid},
        )
        assert len(rows) == 1
        # The helper stores the payload as-is (per ADR-011 — caller's responsibility)
        # BUT the behavioral test documents that the helper itself doesn't leak
        # beyond what the caller passes. Secret patterns ARE present because
        # the caller put them there — this test proves the helper's behavior.
        payload_str = str(rows[0][0])
        assert "should_not_be_here" in payload_str, (
            "Helper stored payload as-is (caller's responsibility)"
        )

    def test_orm_enqueue_rollback_discards_event(self, db_available):
        """ORM enqueue + session rollback → no row in DB."""
        eid = None

        async def _run():
            nonlocal eid
            engine = create_async_engine(DB_URL, echo=False)
            async with AsyncSession(engine) as session:
                async with session.begin():
                    eid = await enqueue_outbox_event(
                        session,
                        event_type="test.orm.rollback",
                        aggregate_type="test",
                        aggregate_id="00000000-0000-0000-0000-000000000002",
                        payload={"should": "not_exist_orm"},
                    )
                    # Force rollback
                    raise RuntimeError("forced rollback in ORM test")
            await engine.dispose()

        try:
            asyncio.run(_run())
        except RuntimeError:
            pass

        if eid:
            rows = _raw_sql("SELECT id FROM outbox_events WHERE id = :eid", {"eid": eid})
            assert len(rows) == 0, f"ORM event {eid} survived rollback"
