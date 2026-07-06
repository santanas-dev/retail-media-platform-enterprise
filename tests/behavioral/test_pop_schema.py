"""Behavioral tests — PoP Persistence Schema (Phase 4.3b).

Tests: accepted event commit, rollback safety, duplicate dedup,
quarantine with campaign_verified=false, duration constraint,
no secrets stored.

Requires: RUN_BEHAVIORAL_TESTS=1, migration 009 applied.
Fixture: pop_fixtures (from conftest) seeds device/creative/campaign chain.
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


@pytest.fixture
def db_available():
    if not REQUIRE_ENV:
        pytest.skip(SKIP_REASON)


_TEST_EVENT_BASE = "beh-pop-00000000000000000001"
_NOW = datetime.now(timezone.utc)


def _ids(pop_fixtures):
    """Extract typed fixture IDs from pop_fixtures dict."""
    return (
        pop_fixtures["device"],
        pop_fixtures["creative"],
        pop_fixtures["campaign"],
        pop_fixtures["manifest"],
    )


# ---------------------------------------------------------------------------
# TestPopEventCommit
# ---------------------------------------------------------------------------


class TestPopEventCommit:

    def test_accept_commit_stores_raw_and_dedup(self, db_available, pop_fixtures):
        dev_id, cr_id, camp_id, man_id = _ids(pop_fixtures)
        now = _NOW
        event_id = f"{_TEST_EVENT_BASE}-commit"

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await accept_pop_event(
                        session, event_id=event_id, schema_version="1.0",
                        device_id=dev_id, manifest_id=man_id, campaign_id=camp_id,
                        creative_asset_id=cr_id, surface_id="surface-01",
                        rendered_at=now, event_recorded_at=now, duration_ms=5000,
                    )
                    await insert_pop_dedup_key(session, event_id)
            await engine.dispose()
        asyncio.run(_run())

        raw = _raw_sql("SELECT id, event_id, status, campaign_verified FROM pop_events_raw WHERE event_id = :eid", {"eid": event_id})
        assert len(raw) == 1
        assert raw[0].status == "accepted"
        assert raw[0].campaign_verified is True

        dedup = _raw_sql("SELECT event_id FROM pop_dedup_index WHERE event_id = :eid", {"eid": event_id})
        assert len(dedup) == 1

    def test_rollback_creates_nothing(self, db_available, pop_fixtures):
        dev_id, cr_id, camp_id, man_id = _ids(pop_fixtures)
        now = _NOW
        event_id = f"{_TEST_EVENT_BASE}-rollback"

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with AsyncSessionLocal() as session:
                async with session.begin() as txn:
                    await accept_pop_event(
                        session, event_id=event_id, schema_version="1.0",
                        device_id=dev_id, manifest_id=man_id, campaign_id=camp_id,
                        creative_asset_id=cr_id, surface_id="surface-01",
                        rendered_at=now, event_recorded_at=now, duration_ms=5000,
                    )
                    await insert_pop_dedup_key(session, event_id)
                    await txn.rollback()
            await engine.dispose()
        asyncio.run(_run())

        assert len(_raw_sql("SELECT id FROM pop_events_raw WHERE event_id = :eid", {"eid": event_id})) == 0
        assert len(_raw_sql("SELECT event_id FROM pop_dedup_index WHERE event_id = :eid", {"eid": event_id})) == 0


# ---------------------------------------------------------------------------
# TestPopDedup
# ---------------------------------------------------------------------------


class TestPopDedup:

    def test_duplicate_detected(self, db_available, pop_fixtures):
        dev_id, cr_id, camp_id, man_id = _ids(pop_fixtures)
        now = _NOW
        event_id = f"{_TEST_EVENT_BASE}-dedup"

        async def _insert():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await record_pop_raw_event(
                        session, event_id=event_id, schema_version="1.0",
                        device_id=dev_id, manifest_id=man_id, campaign_id=camp_id,
                        campaign_verified=True, creative_asset_id=cr_id,
                        surface_id="surface-01", rendered_at=now, event_recorded_at=now,
                        duration_ms=5000, playback_result="success", status="accepted",
                    )
                    await insert_pop_dedup_key(session, event_id)
            await engine.dispose()
        asyncio.run(_insert())

        async def _check():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with AsyncSessionLocal() as session:
                return await is_pop_event_duplicate(session, event_id)
            await engine.dispose()
        assert asyncio.run(_check()) is True

        assert _raw_sql("SELECT count(*) AS c FROM pop_events_raw WHERE event_id = :eid", {"eid": event_id})[0].c == 1

    def test_new_event_id_not_duplicate(self, db_available, pop_fixtures):
        async def _check():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with AsyncSessionLocal() as session:
                return await is_pop_event_duplicate(session, "never-seen-event-id-00000000")
            await engine.dispose()
        assert asyncio.run(_check()) is False


# ---------------------------------------------------------------------------
# TestPopQuarantine
# ---------------------------------------------------------------------------


class TestPopQuarantine:

    def test_quarantine_sets_campaign_verified_false(self, db_available, pop_fixtures):
        dev_id, cr_id, _, _ = _ids(pop_fixtures)
        now = _NOW
        event_id = f"{_TEST_EVENT_BASE}-quar"
        expires = now + timedelta(hours=72)

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await quarantine_pop_event(
                        session, event_id=event_id, schema_version="1.0",
                        device_id=dev_id, manifest_id=None, campaign_id=None,
                        creative_asset_id=cr_id, surface_id="surface-01",
                        rendered_at=now, event_recorded_at=now, duration_ms=5000,
                        playback_result="success", quarantine_reason="unknown_manifest",
                        expires_at=expires,
                    )
                    await insert_pop_dedup_key(session, event_id)
            await engine.dispose()
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

    def test_quarantine_with_campaign_from_payload(self, db_available, pop_fixtures):
        dev_id, cr_id, camp_id, _ = _ids(pop_fixtures)
        now = _NOW
        event_id = f"{_TEST_EVENT_BASE}-quar-cid"
        expires = now + timedelta(hours=72)

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await quarantine_pop_event(
                        session, event_id=event_id, schema_version="1.0",
                        device_id=dev_id, manifest_id="some-unknown-manifest",
                        campaign_id=camp_id, creative_asset_id=cr_id,
                        surface_id="surface-01", rendered_at=now, event_recorded_at=now,
                        duration_ms=5000, playback_result="success",
                        quarantine_reason="unknown_manifest", expires_at=expires,
                    )
                    await insert_pop_dedup_key(session, event_id)
            await engine.dispose()
        asyncio.run(_run())

        raw = _raw_sql(
            "SELECT campaign_id, campaign_verified, manifest_id FROM pop_events_raw WHERE event_id = :eid",
            {"eid": event_id},
        )
        assert len(raw) == 1
        assert raw[0].campaign_id == camp_id
        assert raw[0].campaign_verified is False
        assert raw[0].manifest_id == "some-unknown-manifest"

    def test_expire_quarantine_events(self, db_available, pop_fixtures):
        dev_id, cr_id, _, _ = _ids(pop_fixtures)
        now = _NOW
        past_expiry = now - timedelta(hours=1)
        event_id = f"{_TEST_EVENT_BASE}-expire"

        async def _insert():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await quarantine_pop_event(
                        session, event_id=event_id, schema_version="1.0",
                        device_id=dev_id, manifest_id=None, campaign_id=None,
                        creative_asset_id=cr_id, surface_id="surface-01",
                        rendered_at=now - timedelta(days=3),
                        event_recorded_at=now - timedelta(days=3),
                        duration_ms=5000, playback_result="success",
                        quarantine_reason="unknown_manifest", expires_at=past_expiry,
                    )
                    await insert_pop_dedup_key(session, event_id)
            await engine.dispose()
        asyncio.run(_insert())

        before = _raw_sql("SELECT status FROM pop_events_raw WHERE event_id = :eid", {"eid": event_id})
        assert len(before) == 1
        assert before[0].status == "quarantined"

        async def _expire():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    return await expire_pop_quarantine_events(session, before=now)
            await engine.dispose()
        assert asyncio.run(_expire()) == 1

        after = _raw_sql("SELECT status, quarantine_reason FROM pop_events_raw WHERE event_id = :eid", {"eid": event_id})
        assert after[0].status == "rejected"
        assert after[0].quarantine_reason == "quarantine_expired"


# ---------------------------------------------------------------------------
# TestPopConstraints
# ---------------------------------------------------------------------------


class TestPopConstraints:

    def test_duration_too_small_rejected(self, db_available, pop_fixtures):
        dev_id, cr_id, camp_id, man_id = _ids(pop_fixtures)
        now = _NOW
        event_id = f"{_TEST_EVENT_BASE}-dur0"

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await record_pop_raw_event(
                        session, event_id=event_id, schema_version="1.0",
                        device_id=dev_id, manifest_id=man_id, campaign_id=camp_id,
                        campaign_verified=True, creative_asset_id=cr_id,
                        surface_id="surface-01", rendered_at=now, event_recorded_at=now,
                        duration_ms=0, playback_result="success", status="accepted",
                    )
            await engine.dispose()
        with pytest.raises(Exception):
            asyncio.run(_run())

    def test_duration_too_large_rejected(self, db_available, pop_fixtures):
        dev_id, cr_id, camp_id, man_id = _ids(pop_fixtures)
        now = _NOW
        event_id = f"{_TEST_EVENT_BASE}-dur-max"

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await record_pop_raw_event(
                        session, event_id=event_id, schema_version="1.0",
                        device_id=dev_id, manifest_id=man_id, campaign_id=camp_id,
                        campaign_verified=True, creative_asset_id=cr_id,
                        surface_id="surface-01", rendered_at=now, event_recorded_at=now,
                        duration_ms=86400001, playback_result="success", status="accepted",
                    )
            await engine.dispose()
        with pytest.raises(Exception):
            asyncio.run(_run())

    def test_invalid_status_rejected(self, db_available, pop_fixtures):
        dev_id, cr_id, camp_id, man_id = _ids(pop_fixtures)
        now = _NOW
        event_id = f"{_TEST_EVENT_BASE}-bad-status"

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await record_pop_raw_event(
                        session, event_id=event_id, schema_version="1.0",
                        device_id=dev_id, manifest_id=man_id, campaign_id=camp_id,
                        campaign_verified=True, creative_asset_id=cr_id,
                        surface_id="surface-01", rendered_at=now, event_recorded_at=now,
                        duration_ms=5000, playback_result="success", status="invalid_status_value",
                    )
            await engine.dispose()
        with pytest.raises(Exception):
            asyncio.run(_run())

    def test_accepted_event_must_be_success(self, db_available, pop_fixtures):
        dev_id, cr_id, camp_id, man_id = _ids(pop_fixtures)
        now = _NOW
        event_id = f"{_TEST_EVENT_BASE}-acc-succ"

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await accept_pop_event(
                        session, event_id=event_id, schema_version="1.0",
                        device_id=dev_id, manifest_id=man_id, campaign_id=camp_id,
                        creative_asset_id=cr_id, surface_id="surface-01",
                        rendered_at=now, event_recorded_at=now, duration_ms=5000,
                    )
                    await insert_pop_dedup_key(session, event_id)
            await engine.dispose()
        asyncio.run(_run())

        raw = _raw_sql("SELECT playback_result FROM pop_events_raw WHERE event_id = :eid", {"eid": event_id})
        assert len(raw) == 1
        assert raw[0].playback_result == "success"

    def test_no_secret_values_stored(self, db_available, pop_fixtures):
        dev_id, cr_id, camp_id, man_id = _ids(pop_fixtures)
        now = _NOW
        event_id = f"{_TEST_EVENT_BASE}-nosec"

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await accept_pop_event(
                        session, event_id=event_id, schema_version="1.0",
                        device_id=dev_id, manifest_id=man_id, campaign_id=camp_id,
                        creative_asset_id=cr_id, surface_id="surface-01",
                        rendered_at=now, event_recorded_at=now, duration_ms=5000,
                    )
                    await insert_pop_dedup_key(session, event_id)
            await engine.dispose()
        asyncio.run(_run())

        raw = _raw_sql("SELECT * FROM pop_events_raw WHERE event_id = :eid", {"eid": event_id})
        assert len(raw) == 1
        assert raw[0].device_id == dev_id
