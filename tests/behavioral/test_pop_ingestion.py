"""Behavioral tests — PoP Ingestion (Phase 4.3c).

Tests: valid event ingestion, duplicates, quarantine, cross-entity
rejection, schema_version, playback_result, duration bounds.

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

from packages.domain.pop_ingestion import ingest_pop_event, ingest_pop_batch
from packages.domain.repository import insert_pop_dedup_key
from packages.domain.schemas import PopEventIn

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


_TEST_EVENT_BASE = "beh-pop-ing-00000000000000001"
_NOW = datetime.now(timezone.utc)


def _make_event(pop_fixtures, idx=1, **overrides):
    """Create a PopEventIn with fixture IDs matching the seeded manifest."""
    data = {
        "event_id": f"{_TEST_EVENT_BASE}-{idx:03d}",
        "device_id": pop_fixtures["device"],
        "manifest_id": pop_fixtures["manifest"],
        "campaign_id": pop_fixtures["campaign"],
        "creative_asset_id": pop_fixtures["creative"],
        "surface_id": pop_fixtures["surface"],
        "duration_ms": 5000,
        "playback_result": "success",
        "rendered_at": _NOW - timedelta(minutes=1),
        "event_recorded_at": _NOW - timedelta(minutes=1),
    }
    data.update(overrides)
    return PopEventIn(**data)


async def _run_in_session(fn):
    """Run fn(session) inside an AsyncSession with commit."""
    engine = create_async_engine(DB_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await fn(session)
    await engine.dispose()
    return result


class TestPopIngestionAccept:

    def test_valid_event_accepted(self, db_available, pop_fixtures):
        event = _make_event(pop_fixtures, 1)

        async def _fn(session):
            return await ingest_pop_event(session, event, jwt_device_id=pop_fixtures["device"], now=_NOW)
        result = asyncio.run(_run_in_session(_fn))
        assert result["status"] == "accepted"

        raw = _raw_sql("SELECT status, campaign_verified FROM pop_events_raw WHERE event_id = :eid", {"eid": event.event_id})
        assert len(raw) == 1
        assert raw[0].status == "accepted"
        assert raw[0].campaign_verified is True

        dedup = _raw_sql("SELECT event_id FROM pop_dedup_index WHERE event_id = :eid", {"eid": event.event_id})
        assert len(dedup) == 1

        outbox = _raw_sql("SELECT event_type FROM outbox_events WHERE aggregate_id = :eid", {"eid": event.event_id})
        assert any(r.event_type == "pop.event.accepted" for r in outbox)


class TestPopIngestionReject:

    def test_unsupported_schema_rejected(self, db_available, pop_fixtures):
        event = _make_event(pop_fixtures, 10, schema_version="2.0")

        async def _fn(session):
            return await ingest_pop_event(session, event, jwt_device_id=pop_fixtures["device"], now=_NOW)
        result = asyncio.run(_run_in_session(_fn))
        assert result["status"] == "rejected"
        assert result["reason"] == "unsupported_schema_version"

    def test_device_mismatch_rejected(self, db_available, pop_fixtures):
        event = _make_event(pop_fixtures, 11)

        async def _fn(session):
            return await ingest_pop_event(session, event, jwt_device_id="wrong-device-id", now=_NOW)
        result = asyncio.run(_run_in_session(_fn))
        assert result["status"] == "rejected"
        assert result["reason"] == "device_mismatch"

    def test_non_success_playback_rejected(self, db_available, pop_fixtures):
        event = _make_event(pop_fixtures, 12, playback_result="fallback")

        async def _fn(session):
            return await ingest_pop_event(session, event, jwt_device_id=pop_fixtures["device"], now=_NOW)
        result = asyncio.run(_run_in_session(_fn))
        assert result["status"] == "rejected"
        assert result["reason"] == "non_success_playback"

    def test_campaign_mismatch_rejected(self, db_available, pop_fixtures):
        event = _make_event(pop_fixtures, 14, campaign_id="wrong-campaign-id")

        async def _fn(session):
            return await ingest_pop_event(session, event, jwt_device_id=pop_fixtures["device"], now=_NOW)
        result = asyncio.run(_run_in_session(_fn))
        assert result["status"] == "rejected"
        assert result["reason"] == "campaign_mismatch"

    def test_surface_not_in_manifest_rejected(self, db_available, pop_fixtures):
        event = _make_event(pop_fixtures, 15, surface_id="not-in-manifest-surface")

        async def _fn(session):
            return await ingest_pop_event(session, event, jwt_device_id=pop_fixtures["device"], now=_NOW)
        result = asyncio.run(_run_in_session(_fn))
        assert result["status"] == "rejected"
        assert result["reason"] == "surface_not_in_manifest"

    def test_asset_not_in_manifest_rejected(self, db_available, pop_fixtures):
        event = _make_event(pop_fixtures, 16, creative_asset_id="not-in-manifest-asset")

        async def _fn(session):
            return await ingest_pop_event(session, event, jwt_device_id=pop_fixtures["device"], now=_NOW)
        result = asyncio.run(_run_in_session(_fn))
        assert result["status"] == "rejected"
        assert result["reason"] == "asset_not_in_manifest"

    # --- P2 #1: missing behavioral proofs ---

    def test_device_manifest_mismatch_rejected(self, db_available, pop_fixtures):
        """Event device_id matches JWT, but resolved manifest belongs to a
        different physical_device — must reject, not quarantine."""
        event = _make_event(
            pop_fixtures, 17,
            manifest_id=pop_fixtures["manifest_mismatch"],
            campaign_id=pop_fixtures["campaign"],
        )

        async def _fn(session):
            return await ingest_pop_event(session, event, jwt_device_id=pop_fixtures["device"], now=_NOW)
        result = asyncio.run(_run_in_session(_fn))
        assert result["status"] == "rejected"
        assert result["reason"] == "device_manifest_mismatch"

        # No raw row persisted for rejected events
        raw = _raw_sql("SELECT count(*) AS c FROM pop_events_raw WHERE event_id = :eid", {"eid": event.event_id})
        assert raw[0].c == 0

    def test_stale_event_rejected(self, db_available, pop_fixtures):
        """Event rendered_at older than 30 days — must reject."""
        stale_time = _NOW - timedelta(days=31)
        event = _make_event(
            pop_fixtures, 18,
            rendered_at=stale_time,
            event_recorded_at=stale_time,
        )

        async def _fn(session):
            return await ingest_pop_event(session, event, jwt_device_id=pop_fixtures["device"], now=_NOW)
        result = asyncio.run(_run_in_session(_fn))
        assert result["status"] == "rejected"
        assert result["reason"] == "stale_event"

    def test_duration_out_of_range_rejected(self, db_available, pop_fixtures):
        """Service-layer duration guard — bypass Pydantic to hit domain check.
        duration_ms=0 triggers service-level rejection."""
        # Use model_construct to bypass Pydantic validation and exercise the
        # service-level duration check in pop_ingestion.py line 97-98.
        from packages.domain.schemas import POP_MAX_DURATION_MS
        event = PopEventIn.model_construct(
            event_id=f"{_TEST_EVENT_BASE}-019",
            schema_version="1.0",
            device_id=pop_fixtures["device"],
            manifest_id=pop_fixtures["manifest"],
            campaign_id=pop_fixtures["campaign"],
            creative_asset_id=pop_fixtures["creative"],
            surface_id=pop_fixtures["surface"],
            duration_ms=0,
            playback_result="success",
            rendered_at=_NOW - timedelta(minutes=1),
            event_recorded_at=_NOW - timedelta(minutes=1),
        )

        async def _fn(session):
            return await ingest_pop_event(session, event, jwt_device_id=pop_fixtures["device"], now=_NOW)
        result = asyncio.run(_run_in_session(_fn))
        assert result["status"] == "rejected"
        assert result["reason"] == "invalid_duration"


class TestPopIngestionQuarantine:

    def test_unknown_manifest_quarantined(self, db_available, pop_fixtures):
        event = _make_event(pop_fixtures, 20, manifest_id="unknown-manifest-never-seeded")

        async def _fn(session):
            return await ingest_pop_event(session, event, jwt_device_id=pop_fixtures["device"], now=_NOW)
        result = asyncio.run(_run_in_session(_fn))
        assert result["status"] == "quarantined"
        assert result["reason"] == "unknown_manifest"

        raw = _raw_sql("SELECT status, campaign_verified, quarantine_reason, expires_at FROM pop_events_raw WHERE event_id = :eid", {"eid": event.event_id})
        assert len(raw) == 1
        assert raw[0].status == "quarantined"
        assert raw[0].campaign_verified is False
        assert raw[0].quarantine_reason == "unknown_manifest"
        assert raw[0].expires_at is not None

    # --- P2 #1: clock drift quarantine ---

    def test_clock_drift_quarantined(self, db_available, pop_fixtures):
        """Event rendered_at is > server_time + 5 min — must quarantine
        per ADR-017 clock drift handling."""
        from packages.domain.schemas import POP_CLOCK_DRIFT_MINUTES
        drift_time = _NOW + timedelta(minutes=POP_CLOCK_DRIFT_MINUTES + 2)
        event = _make_event(
            pop_fixtures, 21,
            rendered_at=drift_time,
            event_recorded_at=drift_time,
        )

        async def _fn(session):
            return await ingest_pop_event(session, event, jwt_device_id=pop_fixtures["device"], now=_NOW)
        result = asyncio.run(_run_in_session(_fn))
        assert result["status"] == "quarantined"
        assert result["reason"] == "clock_drift"

        raw = _raw_sql(
            "SELECT status, campaign_verified, quarantine_reason, expires_at FROM pop_events_raw WHERE event_id = :eid",
            {"eid": event.event_id},
        )
        assert len(raw) == 1
        assert raw[0].status == "quarantined"
        assert raw[0].campaign_verified is False
        assert raw[0].quarantine_reason == "clock_drift"
        assert raw[0].expires_at is not None

        outbox = _raw_sql("SELECT event_type FROM outbox_events WHERE aggregate_id = :eid", {"eid": event.event_id})
        assert any(r.event_type == "pop.event.quarantined" for r in outbox)


class TestPopIngestionDup:

    def test_duplicate_marked(self, db_available, pop_fixtures):
        event = _make_event(pop_fixtures, 30)

        async def _fn(session):
            r1 = await ingest_pop_event(session, event, jwt_device_id=pop_fixtures["device"], now=_NOW)
            r2 = await ingest_pop_event(session, event, jwt_device_id=pop_fixtures["device"], now=_NOW)
            return r1, r2
        r1, r2 = asyncio.run(_run_in_session(_fn))
        assert r1["status"] == "accepted"
        assert r2["status"] == "duplicate"
        assert r2["reason"] == "duplicate_event_id"

        raw = _raw_sql("SELECT count(*) AS c FROM pop_events_raw WHERE event_id = :eid", {"eid": event.event_id})
        assert raw[0].c == 1


class TestPopIngestionBatch:

    def test_batch_mixed_results(self, db_available, pop_fixtures):
        valid = _make_event(pop_fixtures, 40)
        bad_schema = _make_event(pop_fixtures, 41, schema_version="9.9")
        unknown = _make_event(pop_fixtures, 42, manifest_id="unknown-batch-manifest")

        async def _fn(session):
            return await ingest_pop_batch(
                session,
                [valid, bad_schema, unknown],
                jwt_device_id=pop_fixtures["device"],
                now=_NOW,
                batch_id="beh-pop-batch-test-001",
            )
        result = asyncio.run(_run_in_session(_fn))
        assert result["accepted_count"] == 1
        assert result["rejected_count"] == 1
        assert result["quarantined_count"] == 1
        assert result["duplicate_count"] == 0
        assert len(result["results"]) == 3

        outbox = _raw_sql("SELECT event_type FROM outbox_events WHERE aggregate_id = :eid", {"eid": "beh-pop-batch-test-001"})
        assert any(r.event_type == "pop.batch.ingested" for r in outbox)

    def test_batch_duplicate_in_batch(self, db_available, pop_fixtures):
        """Two events with same event_id in one batch — first accepted, second duplicate."""
        first = _make_event(pop_fixtures, 50)
        second = _make_event(pop_fixtures, 50)  # same idx → same event_id

        async def _fn(session):
            return await ingest_pop_batch(
                session,
                [first, second],
                jwt_device_id=pop_fixtures["device"],
                now=_NOW,
                batch_id="beh-pop-batch-dedup-test",
            )
        result = asyncio.run(_run_in_session(_fn))
        assert result["accepted_count"] == 1
        assert result["duplicate_count"] == 1
        assert result["rejected_count"] == 0
        assert result["quarantined_count"] == 0
        assert len(result["results"]) == 2
        assert result["results"][0]["status"] == "accepted"
        assert result["results"][1]["status"] == "duplicate"
        assert result["results"][1]["reason"] == "duplicate_event_id"

        # Only one raw event row persisted
        raw = _raw_sql("SELECT count(*) AS c FROM pop_events_raw WHERE event_id = :eid", {"eid": first.event_id})
        assert raw[0].c == 1


# ---------------------------------------------------------------------------
# Retry robustness — savepoint-based dedup on concurrent/retried events
# ---------------------------------------------------------------------------


class TestPopIngestionRetry:
    """Events retried across sessions must not duplicate raw data or outbox."""

    def test_retry_accepted_returns_duplicate(self, db_available, pop_fixtures):
        """First ingest accepted → retry returns duplicate, no new raw/outbox."""
        event = _make_event(pop_fixtures, 60)

        # First ingest — accepted
        r1 = asyncio.run(_run_in_session(
            lambda s: ingest_pop_event(s, event,
                                       jwt_device_id=pop_fixtures["device"],
                                       now=_NOW),
        ))
        assert r1["status"] == "accepted"

        # Retry — must be duplicate across a new session
        r2 = asyncio.run(_run_in_session(
            lambda s: ingest_pop_event(s, event,
                                       jwt_device_id=pop_fixtures["device"],
                                       now=_NOW),
        ))
        assert r2["status"] == "duplicate"
        assert r2["reason"] == "duplicate_event_id"

        # Only one raw event
        raw = _raw_sql(
            "SELECT count(*) AS c FROM pop_events_raw WHERE event_id = :eid",
            {"eid": event.event_id},
        )
        assert raw[0].c == 1

        # Only one outbox event (accepted, not duplicate)
        outbox = _raw_sql(
            "SELECT event_type FROM outbox_events WHERE aggregate_id = :eid",
            {"eid": event.event_id},
        )
        assert len(outbox) == 1
        assert outbox[0].event_type == "pop.event.accepted"

    def test_retry_quarantined_returns_duplicate(self, db_available, pop_fixtures):
        """First ingest quarantined → retry returns duplicate, no new raw/outbox."""
        event = _make_event(pop_fixtures, 61,
                            manifest_id="unknown-retry-manifest")

        # First ingest — quarantined (unknown manifest)
        r1 = asyncio.run(_run_in_session(
            lambda s: ingest_pop_event(s, event,
                                       jwt_device_id=pop_fixtures["device"],
                                       now=_NOW),
        ))
        assert r1["status"] == "quarantined"

        # Retry — must be duplicate
        r2 = asyncio.run(_run_in_session(
            lambda s: ingest_pop_event(s, event,
                                       jwt_device_id=pop_fixtures["device"],
                                       now=_NOW),
        ))
        assert r2["status"] == "duplicate"
        assert r2["reason"] == "duplicate_event_id"

        # Only one raw event
        raw = _raw_sql(
            "SELECT count(*) AS c FROM pop_events_raw WHERE event_id = :eid",
            {"eid": event.event_id},
        )
        assert raw[0].c == 1

        # Only one outbox event (quarantined, not duplicate)
        outbox = _raw_sql(
            "SELECT event_type FROM outbox_events WHERE aggregate_id = :eid",
            {"eid": event.event_id},
        )
        assert len(outbox) == 1
        assert outbox[0].event_type == "pop.event.quarantined"

    def test_mixed_batch_valid_plus_duplicate(self, db_available, pop_fixtures):
        """Batch with valid + duplicate events — valid persists, dup reported."""
        event = _make_event(pop_fixtures, 62)

        # Ingest once to make it duplicate for the batch
        asyncio.run(_run_in_session(
            lambda s: ingest_pop_event(s, event,
                                       jwt_device_id=pop_fixtures["device"],
                                       now=_NOW),
        ))

        # Now batch with the same event + a new valid event
        new_event = _make_event(pop_fixtures, 63)
        batch_events = [event, new_event]

        result = asyncio.run(_run_in_session(
            lambda s: ingest_pop_batch(
                s, batch_events,
                jwt_device_id=pop_fixtures["device"],
                now=_NOW,
                batch_id="beh-pop-batch-retry-test",
            ),
        ))
        assert result["accepted_count"] == 1
        assert result["duplicate_count"] == 1
        assert len(result["results"]) == 2
        assert result["results"][0]["status"] == "duplicate"
        assert result["results"][1]["status"] == "accepted"

        # Both events have exactly 1 raw row each
        raw1 = _raw_sql(
            "SELECT count(*) AS c FROM pop_events_raw WHERE event_id = :eid",
            {"eid": event.event_id},
        )
        raw2 = _raw_sql(
            "SELECT count(*) AS c FROM pop_events_raw WHERE event_id = :eid",
            {"eid": new_event.event_id},
        )
        assert raw1[0].c == 1
        assert raw2[0].c == 1

    def test_forced_same_batch_duplicate_does_not_abort(self, db_available,
                                                         pop_fixtures):
        """Two identical events in one batch — both reported, batch commits."""
        event = _make_event(pop_fixtures, 64)

        result = asyncio.run(_run_in_session(
            lambda s: ingest_pop_batch(
                s, [event, event],
                jwt_device_id=pop_fixtures["device"],
                now=_NOW,
                batch_id="beh-pop-batch-same-dup",
            ),
        ))
        assert result["accepted_count"] == 1
        assert result["duplicate_count"] == 1
        assert len(result["results"]) == 2

        # Only 1 raw row
        raw = _raw_sql(
            "SELECT count(*) AS c FROM pop_events_raw WHERE event_id = :eid",
            {"eid": event.event_id},
        )
        assert raw[0].c == 1
