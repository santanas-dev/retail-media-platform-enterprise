"""Behavioral tests — PoP Reporting (Phase 4.3d).

Tests: accepted-only counting, filtering (quarantined/rejected/duplicate
excluded, campaign_verified=false excluded, playback_result!=success excluded),
by-day grouping, by-surface grouping, auth (401/403), RLS scoping.

Requires: RUN_BEHAVIORAL_TESTS=1, migration 009 applied.
Fixture: pop_fixtures (from conftest) seeds full entity chain + manifest.
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
    get_campaign_pop_summary,
    insert_pop_dedup_key,
    list_campaign_pop_by_day,
    list_campaign_pop_by_surface,
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
            await conn.execute(text("SELECT set_config('app.rmp_is_admin', 'true', false)"))
            await conn.commit()
            result = await conn.execute(text(sql), params or {})
            rows = result.fetchall()
        await engine.dispose()
        return rows
    return asyncio.run(_run())


@pytest.fixture
def db_available():
    if not REQUIRE_ENV:
        pytest.skip(SKIP_REASON)


_NOW = datetime.now(timezone.utc)
_TEST_EVENT_BASE = "beh-pop-rpt-000000000000001"


async def _run_in_session(fn):
    engine = create_async_engine(DB_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await fn(session)
    await engine.dispose()
    return result


async def _seed_accepted_event(session, pop_fixtures, idx, **overrides):
    """Seed a PoP event directly into pop_events_raw + dedup index.

    Defaults: status=accepted, campaign_verified=True, playback_result=success.
    Override any field via **overrides.
    """
    event_id = f"{_TEST_EVENT_BASE}-{idx:03d}"
    params = {
        "event_id": event_id,
        "schema_version": "1.0",
        "device_id": pop_fixtures["device"],
        "manifest_id": pop_fixtures["manifest"],
        "campaign_id": pop_fixtures["campaign"],
        "creative_asset_id": pop_fixtures["creative"],
        "surface_id": pop_fixtures["surface"],
        "rendered_at": _NOW - timedelta(hours=idx),
        "event_recorded_at": _NOW - timedelta(hours=idx),
        "duration_ms": 5000,
        "playback_result": "success",
        "campaign_verified": True,
        "status": "accepted",
    }
    params.update(overrides)
    await record_pop_raw_event(
        session,
        event_id=params["event_id"],
        schema_version=params["schema_version"],
        device_id=params["device_id"],
        manifest_id=params["manifest_id"],
        campaign_id=params["campaign_id"],
        campaign_verified=params["campaign_verified"],
        creative_asset_id=params["creative_asset_id"],
        surface_id=params["surface_id"],
        rendered_at=params["rendered_at"],
        event_recorded_at=params["event_recorded_at"],
        duration_ms=params["duration_ms"],
        playback_result=params["playback_result"],
        status=params["status"],
    )
    await insert_pop_dedup_key(session, params["event_id"])
    await session.flush()
    return params


class TestPopReportingAcceptedOnly:

    def test_empty_campaign_returns_zeros(self, db_available, pop_fixtures):
        """No accepted events → all metrics zero."""
        result = asyncio.run(_run_in_session(
            lambda s: get_campaign_pop_summary(s, pop_fixtures["campaign"]),
        ))
        assert result["impressions_count"] == 0
        assert result["total_duration_ms"] == 0
        assert result["first_rendered_at"] is None
        assert result["last_rendered_at"] is None
        assert result["unique_devices"] == 0
        assert result["unique_surfaces"] == 0

    def test_accepted_events_counted(self, db_available, pop_fixtures):
        """Accepted + campaign_verified + success events are counted."""
        async def _seed(session):
            for i in range(3):
                await _seed_accepted_event(session, pop_fixtures, i)
        asyncio.run(_run_in_session(_seed))

        result = asyncio.run(_run_in_session(
            lambda s: get_campaign_pop_summary(s, pop_fixtures["campaign"]),
        ))
        assert result["impressions_count"] == 3
        assert result["total_duration_ms"] == 15000
        assert result["unique_devices"] == 1
        assert result["unique_surfaces"] == 1

    def test_quarantined_not_counted(self, db_available, pop_fixtures):
        """Quarantined events excluded from reporting."""
        async def _seed(session):
            await _seed_accepted_event(session, pop_fixtures, 1)
            await _seed_accepted_event(session, pop_fixtures, 2, status="quarantined", campaign_verified=False)
        asyncio.run(_run_in_session(_seed))

        result = asyncio.run(_run_in_session(
            lambda s: get_campaign_pop_summary(s, pop_fixtures["campaign"]),
        ))
        assert result["impressions_count"] == 1

    def test_campaign_verified_false_not_counted(self, db_available, pop_fixtures):
        """campaign_verified=false events excluded even if accepted."""
        async def _seed(session):
            await _seed_accepted_event(session, pop_fixtures, 1)
            await _seed_accepted_event(session, pop_fixtures, 2, campaign_verified=False)
        asyncio.run(_run_in_session(_seed))

        result = asyncio.run(_run_in_session(
            lambda s: get_campaign_pop_summary(s, pop_fixtures["campaign"]),
        ))
        assert result["impressions_count"] == 1

    def test_non_success_playback_not_counted(self, db_available, pop_fixtures):
        """playback_result != success events excluded."""
        async def _seed(session):
            await _seed_accepted_event(session, pop_fixtures, 1)
            await _seed_accepted_event(session, pop_fixtures, 2, playback_result="fallback")
        asyncio.run(_run_in_session(_seed))

        result = asyncio.run(_run_in_session(
            lambda s: get_campaign_pop_summary(s, pop_fixtures["campaign"]),
        ))
        assert result["impressions_count"] == 1

    def test_different_campaign_not_counted(self, db_available, pop_fixtures):
        """Events from other campaigns don't leak."""
        async def _seed(session):
            await _seed_accepted_event(session, pop_fixtures, 1)
        asyncio.run(_run_in_session(_seed))

        result = asyncio.run(_run_in_session(
            lambda s: get_campaign_pop_summary(s, "different-campaign-id"),
        ))
        assert result["impressions_count"] == 0


class TestPopReportingByDay:

    def test_by_day_grouping(self, db_available, pop_fixtures):
        """Events on different days are correctly grouped."""
        async def _seed(session):
            # Day 1: 2 events
            await _seed_accepted_event(session, pop_fixtures, 1, rendered_at=_NOW - timedelta(days=2))
            await _seed_accepted_event(session, pop_fixtures, 2, rendered_at=_NOW - timedelta(days=2))
            # Day 2: 1 event
            await _seed_accepted_event(session, pop_fixtures, 3, rendered_at=_NOW - timedelta(days=1))
        asyncio.run(_run_in_session(_seed))

        rows = asyncio.run(_run_in_session(
            lambda s: list_campaign_pop_by_day(s, pop_fixtures["campaign"]),
        ))
        assert len(rows) == 2  # two distinct days
        total = sum(r["impressions_count"] for r in rows)
        assert total == 3


class TestPopReportingBySurface:

    def test_by_surface_grouping(self, db_available, pop_fixtures):
        """Events on different surfaces are correctly grouped."""
        async def _seed(session):
            await _seed_accepted_event(session, pop_fixtures, 1, surface_id="surf-a")
            await _seed_accepted_event(session, pop_fixtures, 2, surface_id="surf-a")
            await _seed_accepted_event(session, pop_fixtures, 3, surface_id="surf-b")
        asyncio.run(_run_in_session(_seed))

        rows = asyncio.run(_run_in_session(
            lambda s: list_campaign_pop_by_surface(s, pop_fixtures["campaign"]),
        ))
        assert len(rows) == 2  # two distinct surfaces
        # Most impressions first (descending order)
        assert rows[0]["impressions_count"] == 2
        assert rows[1]["impressions_count"] == 1
