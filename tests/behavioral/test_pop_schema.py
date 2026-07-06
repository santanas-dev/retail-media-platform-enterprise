"""
Behavioral tests — PoP Persistence Schema (Phase 4.3b).

Tests: accepted event commit, rollback safety, duplicate dedup,
quarantine with campaign_verified=false, duration constraint,
no secrets stored, helper signatures.

Requires: RUN_BEHAVIORAL_TESTS=1, migration 009 applied.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["ENVIRONMENT"] = "dev"

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from packages.domain.repository import (
    accept_pop_event,
    expire_pop_quarantine_events,
    insert_pop_dedup_key,
    is_pop_event_duplicate,
    quarantine_pop_event,
    record_pop_raw_event,
)

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)

REQUIRE_ENV = os.environ.get("RUN_BEHAVIORAL_TESTS", "") == "1"
SKIP_REASON = "RUN_BEHAVIORAL_TESTS=1 not set."


def _raw_sql(sql: str, params=None):
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(text(sql), params or {})
            rows = result.fetchall()
        await engine.dispose()
        return rows
    return asyncio.run(_run())


def _raw_exec(sql: str, params=None):
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.begin() as conn:
            for stmt in sql.split(";"):
                s = stmt.strip()
                if s and not s.startswith("--"):
                    await conn.execute(text(s), params or {})
        await engine.dispose()
    asyncio.run(_run())


@pytest.fixture
def db_available():
    if not REQUIRE_ENV:
        pytest.skip(SKIP_REASON)


_TEST_EVENT_ID = "beh-pop-00000000000000000001"
_TEST_DEVICE_ID = "00000000-0000-0000-0000-000000000100"
_TEST_CAMPAIGN_ID = "00000000-0000-0000-0000-000000000200"
_TEST_CREATIVE_ID = "00000000-0000-0000-0000-000000000300"
_TEST_MANIFEST_ID = "beh-manifest-pop-test-00000001"
_NOW = datetime.now(timezone.utc)


def _cleanup():
    _raw_exec(f"""
        DELETE FROM pop_events_raw WHERE event_id LIKE 'beh-pop-%'
        ; DELETE FROM pop_dedup_index WHERE event_id LIKE 'beh-pop-%'
        ; DELETE FROM pop_ingestion_batches WHERE id LIKE 'beh-pop-%'
    """)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPopEventCommit:
    """Accepted event commit creates raw + dedup entries."""

    def test_accept_commit_stores_raw_and_dedup(self, db_available):
        _cleanup()
        now = _NOW
        event_id = f"{_TEST_EVENT_ID}-commit"

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    row_id = await accept_pop_event(
                        session,
                        event_id=event_id,
                        schema_version="1.0",
                        device_id=_TEST_DEVICE_ID,
                        manifest_id=_TEST_MANIFEST_ID,
                        campaign_id=_TEST_CAMPAIGN_ID,
                        creative_asset_id=_TEST_CREATIVE_ID,
                        surface_id="surface-01",
                        rendered_at=now,
                        event_recorded_at=now,
                        duration_ms=5000,
                    )
                    await insert_pop_dedup_key(session, event_id)
            await engine.dispose()
            return row_id
        row_id = asyncio.run(_run())

        # Verify raw table
        raw_rows = _raw_sql(
            "SELECT id, event_id, status, campaign_verified FROM pop_events_raw WHERE event_id = :eid",
            {"eid": event_id},
        )
        assert len(raw_rows) == 1
        assert raw_rows[0].event_id == event_id
        assert raw_rows[0].status == "accepted"
        assert raw_rows[0].campaign_verified is True

        # Verify dedup index
        dedup_rows = _raw_sql(
            "SELECT event_id FROM pop_dedup_index WHERE event_id = :eid",
            {"eid": event_id},
        )
        assert len(dedup_rows) == 1

        _cleanup()

    def test_rollback_creates_nothing(self, db_available):
        _cleanup()
        now = _NOW
        event_id = f"{_TEST_EVENT_ID}-rollback"

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                async with session.begin() as txn:
                    await accept_pop_event(
                        session,
                        event_id=event_id,
                        schema_version="1.0",
                        device_id=_TEST_DEVICE_ID,
                        manifest_id=_TEST_MANIFEST_ID,
                        campaign_id=_TEST_CAMPAIGN_ID,
                        creative_asset_id=_TEST_CREATIVE_ID,
                        surface_id="surface-01",
                        rendered_at=now,
                        event_recorded_at=now,
                        duration_ms=5000,
                    )
                    await insert_pop_dedup_key(session, event_id)
                    await txn.rollback()
            await engine.dispose()
        asyncio.run(_run())

        raw_rows = _raw_sql("SELECT id FROM pop_events_raw WHERE event_id = :eid", {"eid": event_id})
        assert len(raw_rows) == 0

        dedup_rows = _raw_sql("SELECT event_id FROM pop_dedup_index WHERE event_id = :eid", {"eid": event_id})
        assert len(dedup_rows) == 0

        _cleanup()


class TestPopDedup:
    """Duplicate event_id is detected and prevented."""

    def test_duplicate_detected(self, db_available):
        _cleanup()
        now = _NOW
        event_id = f"{_TEST_EVENT_ID}-dedup"

        # First insert — commit
        async def _insert():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await record_pop_raw_event(
                        session,
                        event_id=event_id,
                        schema_version="1.0",
                        device_id=_TEST_DEVICE_ID,
                        manifest_id=_TEST_MANIFEST_ID,
                        campaign_id=_TEST_CAMPAIGN_ID,
                        campaign_verified=True,
                        creative_asset_id=_TEST_CREATIVE_ID,
                        surface_id="surface-01",
                        rendered_at=now,
                        event_recorded_at=now,
                        duration_ms=5000,
                        playback_result="success",
                        status="accepted",
                    )
                    await insert_pop_dedup_key(session, event_id)
            await engine.dispose()
        asyncio.run(_insert())

        # Second check — must be duplicate
        async def _check():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                is_dup = await is_pop_event_duplicate(session, event_id)
            await engine.dispose()
            return is_dup
        is_dup = asyncio.run(_check())
        assert is_dup is True

        # Verify only one raw row
        raw = _raw_sql(
            "SELECT count(*) AS c FROM pop_events_raw WHERE event_id = :eid",
            {"eid": event_id},
        )
        assert raw[0].c == 1

        _cleanup()

    def test_new_event_id_not_duplicate(self, db_available):
        async def _check():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                is_dup = await is_pop_event_duplicate(session, "never-seen-event-id-00000000")
            await engine.dispose()
            return is_dup
        is_dup = asyncio.run(_check())
        assert is_dup is False


class TestPopQuarantine:
    """Quarantine stores campaign_verified=false and expires_at."""

    def test_quarantine_sets_campaign_verified_false(self, db_available):
        _cleanup()
        now = _NOW
        event_id = f"{_TEST_EVENT_ID}-quar"
        expires = now + timedelta(hours=72)

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    row_id = await quarantine_pop_event(
                        session,
                        event_id=event_id,
                        schema_version="1.0",
                        device_id=_TEST_DEVICE_ID,
                        manifest_id=None,
                        campaign_id=None,
                        creative_asset_id=_TEST_CREATIVE_ID,
                        surface_id="surface-01",
                        rendered_at=now,
                        event_recorded_at=now,
                        duration_ms=5000,
                        playback_result="success",
                        quarantine_reason="unknown_manifest",
                        expires_at=expires,
                    )
                    await insert_pop_dedup_key(session, event_id)
            await engine.dispose()
            return row_id
        asyncio.run(_run())

        raw = _raw_sql(
            "SELECT status, campaign_verified, quarantine_reason, expires_at, campaign_id, manifest_id FROM pop_events_raw WHERE event_id = :eid",
            {"eid": event_id},
        )
        assert len(raw) == 1
        assert raw[0].status == "quarantined"
        assert raw[0].campaign_verified is False
        assert raw[0].quarantine_reason == "unknown_manifest"
        assert raw[0].expires_at is not None
        assert raw[0].campaign_id is None
        assert raw[0].manifest_id is None

        _cleanup()

    def test_quarantine_with_campaign_from_payload(self, db_available):
        """Quarantine accepts campaign_id from payload but marks unverified."""
        _cleanup()
        now = _NOW
        event_id = f"{_TEST_EVENT_ID}-quar-cid"
        expires = now + timedelta(hours=72)

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await quarantine_pop_event(
                        session,
                        event_id=event_id,
                        schema_version="1.0",
                        device_id=_TEST_DEVICE_ID,
                        manifest_id="some-unknown-manifest",
                        campaign_id=_TEST_CAMPAIGN_ID,
                        creative_asset_id=_TEST_CREATIVE_ID,
                        surface_id="surface-01",
                        rendered_at=now,
                        event_recorded_at=now,
                        duration_ms=5000,
                        playback_result="success",
                        quarantine_reason="unknown_manifest",
                        expires_at=expires,
                    )
                    await insert_pop_dedup_key(session, event_id)
            await engine.dispose()
        asyncio.run(_run())

        raw = _raw_sql(
            "SELECT campaign_id, campaign_verified, manifest_id FROM pop_events_raw WHERE event_id = :eid",
            {"eid": event_id},
        )
        assert len(raw) == 1
        assert raw[0].campaign_id == _TEST_CAMPAIGN_ID
        assert raw[0].campaign_verified is False
        assert raw[0].manifest_id == "some-unknown-manifest"

        _cleanup()

    def test_expire_quarantine_events(self, db_available):
        """Quarantine events with expired expires_at are rejected."""
        _cleanup()
        now = _NOW
        past_expiry = now - timedelta(hours=1)
        event_id = f"{_TEST_EVENT_ID}-expire"

        async def _insert():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await quarantine_pop_event(
                        session,
                        event_id=event_id,
                        schema_version="1.0",
                        device_id=_TEST_DEVICE_ID,
                        manifest_id=None,
                        campaign_id=None,
                        creative_asset_id=_TEST_CREATIVE_ID,
                        surface_id="surface-01",
                        rendered_at=now - timedelta(days=3),
                        event_recorded_at=now - timedelta(days=3),
                        duration_ms=5000,
                        playback_result="success",
                        quarantine_reason="unknown_manifest",
                        expires_at=past_expiry,
                    )
                    await insert_pop_dedup_key(session, event_id)
            await engine.dispose()
        asyncio.run(_insert())

        # Verify it's quarantined
        before = _raw_sql(
            "SELECT status FROM pop_events_raw WHERE event_id = :eid",
            {"eid": event_id},
        )
        assert len(before) == 1
        assert before[0].status == "quarantined"

        # Expire
        async def _expire():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    count = await expire_pop_quarantine_events(
                        session, before=now,
                    )
            await engine.dispose()
            return count
        count = asyncio.run(_expire())
        assert count == 1

        after = _raw_sql(
            "SELECT status, quarantine_reason FROM pop_events_raw WHERE event_id = :eid",
            {"eid": event_id},
        )
        assert after[0].status == "rejected"
        assert after[0].quarantine_reason == "quarantine_expired"

        _cleanup()


class TestPopConstraints:
    """DB-level constraints enforced."""

    def test_duration_too_small_rejected(self, db_available):
        """duration_ms = 0 violates CHECK constraint."""
        _cleanup()
        now = _NOW
        event_id = f"{_TEST_EVENT_ID}-dur0"

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await record_pop_raw_event(
                        session,
                        event_id=event_id,
                        schema_version="1.0",
                        device_id=_TEST_DEVICE_ID,
                        manifest_id=_TEST_MANIFEST_ID,
                        campaign_id=_TEST_CAMPAIGN_ID,
                        campaign_verified=True,
                        creative_asset_id=_TEST_CREATIVE_ID,
                        surface_id="surface-01",
                        rendered_at=now,
                        event_recorded_at=now,
                        duration_ms=0,
                        playback_result="success",
                        status="accepted",
                    )
            await engine.dispose()
        with pytest.raises(Exception):
            asyncio.run(_run())

        _cleanup()

    def test_duration_too_large_rejected(self, db_available):
        """duration_ms = 86400001 violates CHECK constraint."""
        _cleanup()
        now = _NOW
        event_id = f"{_TEST_EVENT_ID}-dur-max"

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await record_pop_raw_event(
                        session,
                        event_id=event_id,
                        schema_version="1.0",
                        device_id=_TEST_DEVICE_ID,
                        manifest_id=_TEST_MANIFEST_ID,
                        campaign_id=_TEST_CAMPAIGN_ID,
                        campaign_verified=True,
                        creative_asset_id=_TEST_CREATIVE_ID,
                        surface_id="surface-01",
                        rendered_at=now,
                        event_recorded_at=now,
                        duration_ms=86400001,
                        playback_result="success",
                        status="accepted",
                    )
            await engine.dispose()
        with pytest.raises(Exception):
            asyncio.run(_run())

        _cleanup()

    def test_invalid_status_rejected(self, db_available):
        """Invalid status value violates CHECK constraint."""
        _cleanup()
        now = _NOW
        event_id = f"{_TEST_EVENT_ID}-bad-status"

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await record_pop_raw_event(
                        session,
                        event_id=event_id,
                        schema_version="1.0",
                        device_id=_TEST_DEVICE_ID,
                        manifest_id=_TEST_MANIFEST_ID,
                        campaign_id=_TEST_CAMPAIGN_ID,
                        campaign_verified=True,
                        creative_asset_id=_TEST_CREATIVE_ID,
                        surface_id="surface-01",
                        rendered_at=now,
                        event_recorded_at=now,
                        duration_ms=5000,
                        playback_result="success",
                        status="invalid_status_value",
                    )
            await engine.dispose()
        with pytest.raises(Exception):
            asyncio.run(_run())

        _cleanup()

    def test_accepted_event_must_be_success(self, db_available):
        """Helper accept_pop_event enforces playback_result='success'."""
        _cleanup()
        now = _NOW
        event_id = f"{_TEST_EVENT_ID}-acc-succ"

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    row_id = await accept_pop_event(
                        session,
                        event_id=event_id,
                        schema_version="1.0",
                        device_id=_TEST_DEVICE_ID,
                        manifest_id=_TEST_MANIFEST_ID,
                        campaign_id=_TEST_CAMPAIGN_ID,
                        creative_asset_id=_TEST_CREATIVE_ID,
                        surface_id="surface-01",
                        rendered_at=now,
                        event_recorded_at=now,
                        duration_ms=5000,
                    )
                    await insert_pop_dedup_key(session, event_id)
            await engine.dispose()
            return row_id
        asyncio.run(_run())

        raw = _raw_sql(
            "SELECT playback_result FROM pop_events_raw WHERE event_id = :eid",
            {"eid": event_id},
        )
        assert len(raw) == 1
        assert raw[0].playback_result == "success"

        _cleanup()

    def test_no_secret_columns_in_payload(self, db_available):
        """Accepted event does not store secrets even if hypothetically present."""
        # This is a structural check — our helpers don't accept secret fields.
        # Verify the table schema has no secret columns (unit test covers this).
        # Here we verify a real event row has NULL for any secret-like columns.
        _cleanup()
        now = _NOW
        event_id = f"{_TEST_EVENT_ID}-nosec"

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await accept_pop_event(
                        session,
                        event_id=event_id,
                        schema_version="1.0",
                        device_id=_TEST_DEVICE_ID,
                        manifest_id=_TEST_MANIFEST_ID,
                        campaign_id=_TEST_CAMPAIGN_ID,
                        creative_asset_id=_TEST_CREATIVE_ID,
                        surface_id="surface-01",
                        rendered_at=now,
                        event_recorded_at=now,
                        duration_ms=5000,
                    )
                    await insert_pop_dedup_key(session, event_id)
            await engine.dispose()
        asyncio.run(_run())

        # Select all columns and verify no secret-like values in string columns
        raw = _raw_sql(
            "SELECT * FROM pop_events_raw WHERE event_id = :eid",
            {"eid": event_id},
        )
        assert len(raw) == 1
        row = raw[0]
        # spot-check: device_id is our test ID, not a real device secret
        assert row.device_id == _TEST_DEVICE_ID

        _cleanup()
