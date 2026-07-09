"""
Behavioral tests — Manifest Generation Worker Skeleton (Phase 4.2c).

Tests: approved campaign generates manifests, unapproved -> no-op,
idempotency, rollback, outbox events, broad store placement resolution.

Requires: RUN_BEHAVIORAL_TESTS=1, seed data, migration 008 applied.
"""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["ENVIRONMENT"] = "dev"

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)

REQUIRE_ENV = os.environ.get("RUN_BEHAVIORAL_TESTS", "") == "1"
SKIP_REASON = "RUN_BEHAVIORAL_TESTS=1 not set."

# Seed IDs — must match apps/control-api/seed.py
SEED_CAMPAIGN_ID = "00000000-0000-0000-0000-000000000220"
SEED_DEVICE_ID = "00000000-0000-0000-0000-000000000020"
SEED_SURFACE_ID = "00000000-0000-0000-0000-000000000031"
SEED_STORE_ID = "00000000-0000-0000-0000-000000000003"
SEED_ADV_ORG_ID = "00000000-0000-0000-0000-000000000200"
SEED_PLACEMENT_ID = "00000000-0000-0000-0000-000000000224"


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


def _raw_exec(sql: str, params=None):
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.begin() as conn:
            await conn.execute(text("SELECT set_config('app.rmp_is_admin', 'true', true)"))
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


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------


def _prepare_approved_campaign():
    """Set campaign to approved, device to active, flights to current window."""
    _raw_exec(
        "UPDATE campaigns SET status = 'approved' WHERE id = :cid",
        {"cid": SEED_CAMPAIGN_ID},
    )
    _raw_exec(
        "UPDATE physical_devices SET status = 'active' WHERE id = :did",
        {"did": SEED_DEVICE_ID},
    )
    # Update flight window to current time range
    from datetime import datetime, timezone as _tz, timedelta
    now = datetime.now(_tz.utc)
    start = now - timedelta(days=1)
    end = now + timedelta(days=7)
    _raw_exec(
        "UPDATE campaign_flights SET start_at = :start, end_at = :end "
        "WHERE campaign_id = :cid",
        {"start": start, "end": end, "cid": SEED_CAMPAIGN_ID},
    )


def _reset_manifest_state():
    """Remove any generated manifests/plans/outbox from previous test runs."""
    _raw_exec("""
        DELETE FROM delivery_attempts;
        DELETE FROM delivery_manifest_assets;
        DELETE FROM delivery_manifest_surfaces;
        DELETE FROM delivery_manifests;
        DELETE FROM delivery_plans;
        DELETE FROM outbox_events WHERE event_type LIKE 'delivery.manifest.%';
    """)


def _count_manifests():
    rows = _raw_sql("SELECT COUNT(*) FROM delivery_manifests")
    return rows[0][0] if rows else 0


def _count_outbox(event_type: str):
    rows = _raw_sql(
        "SELECT COUNT(*) FROM outbox_events WHERE event_type = :et",
        {"et": event_type},
    )
    return rows[0][0] if rows else 0


# ── RLS scope helper ──
# Sets the session's RLS scope to the seed advertiser org so campaigns
# are visible under retail_media_app (NOBYPASSRLS) behavioral tests.


async def _set_rls_scope(session):
    await session.execute(
        text("SELECT set_config('app.rmp_scope_advertiser_ids', :ids, false)"),
        {"ids": SEED_ADV_ORG_ID},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestApprovedCampaignGeneratesManifest:

    def test_generates_manifest_for_approved_campaign(self, db_available):
        from packages.domain.delivery import generate_manifests_for_campaign

        _prepare_approved_campaign()
        _reset_manifest_state()

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await _set_rls_scope(session)
                result = await generate_manifests_for_campaign(
                    session, SEED_CAMPAIGN_ID,
                )
                await session.commit()
                return result
            await engine.dispose()

        result = asyncio.run(_run())

        assert result.eligible is True
        assert result.device_count >= 1
        assert result.manifest_count >= 1
        assert result.failure_count == 0
        assert len(result.manifest_ids) >= 1

        # Verify persistence
        manifests = _count_manifests()
        assert manifests >= 1

        # Verify outbox event
        assert _count_outbox("delivery.manifest.generated") >= 1

    def test_unapproved_campaign_no_manifest(self, db_available):
        """Campaign with status=draft must not generate manifests."""
        from packages.domain.delivery import generate_manifests_for_campaign

        _prepare_approved_campaign()
        _reset_manifest_state()
        # Set status back to draft
        _raw_exec(
            "UPDATE campaigns SET status = 'draft' WHERE id = :cid",
            {"cid": SEED_CAMPAIGN_ID},
        )

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await _set_rls_scope(session)
                result = await generate_manifests_for_campaign(
                    session, SEED_CAMPAIGN_ID,
                )
                await session.commit()
                return result
            await engine.dispose()

        result = asyncio.run(_run())

        assert result.eligible is False
        assert "draft" in (result.skip_reason or "")
        assert result.manifest_count == 0
        assert _count_manifests() == 0
        # No generated outbox event
        assert _count_outbox("delivery.manifest.generated") == 0

    def test_idempotent_generation(self, db_available):
        """Repeated generation must not create duplicate manifest records."""
        from packages.domain.delivery import generate_manifests_for_campaign

        _prepare_approved_campaign()
        _reset_manifest_state()

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await _set_rls_scope(session)
                result1 = await generate_manifests_for_campaign(
                    session, SEED_CAMPAIGN_ID,
                )
                await session.commit()
                return result1.manifest_count
            await engine.dispose()

        count1 = asyncio.run(_run())

        # Second run
        async def _run2():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await _set_rls_scope(session)
                result2 = await generate_manifests_for_campaign(
                    session, SEED_CAMPAIGN_ID,
                )
                await session.commit()
                return result2
            await engine.dispose()

        result2 = asyncio.run(_run2())

        assert result2.eligible is True
        # Second run should create NO new manifests (idempotent)
        assert result2.manifest_count == 0
        assert result2.skip_reason is None  # Not skipped — just all duplicates
        # Total count unchanged
        assert _count_manifests() == count1

    def test_rollback_creates_no_partial_state(self, db_available):
        """Rollback after generation must leave no manifest records."""
        from packages.domain.delivery import generate_manifests_for_campaign

        _prepare_approved_campaign()
        _reset_manifest_state()

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await _set_rls_scope(session)
                result = await generate_manifests_for_campaign(
                    session, SEED_CAMPAIGN_ID,
                )
                await session.rollback()
                return result
            await engine.dispose()

        result = asyncio.run(_run())

        # Generation happened in-memory but was rolled back
        assert result.eligible is True
        assert result.manifest_count >= 1

        # Nothing persisted
        assert _count_manifests() == 0
        assert _count_outbox("delivery.manifest.generated") == 0

    def test_outbox_event_on_success(self, db_available):
        """Generation success writes delivery.manifest.generated outbox event."""
        from packages.domain.delivery import generate_manifests_for_campaign

        _prepare_approved_campaign()
        _reset_manifest_state()

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await _set_rls_scope(session)
                result = await generate_manifests_for_campaign(
                    session, SEED_CAMPAIGN_ID,
                )
                await session.commit()
                return result
            await engine.dispose()

        result = asyncio.run(_run())

        assert result.manifest_count >= 1
        # At least one outbox event per generated manifest
        assert _count_outbox("delivery.manifest.generated") >= result.manifest_count

    def test_no_outbox_generated_for_unapproved(self, db_available):
        """Unapproved campaign must not produce delivery.manifest.generated events."""
        from packages.domain.delivery import generate_manifests_for_campaign

        _prepare_approved_campaign()
        _reset_manifest_state()
        _raw_exec(
            "UPDATE campaigns SET status = 'draft' WHERE id = :cid",
            {"cid": SEED_CAMPAIGN_ID},
        )

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await _set_rls_scope(session)
                result = await generate_manifests_for_campaign(
                    session, SEED_CAMPAIGN_ID,
                )
                await session.commit()
                return result
            await engine.dispose()

        result = asyncio.run(_run())

        assert result.eligible is False
        assert result.manifest_count == 0
        assert _count_outbox("delivery.manifest.generated") == 0
        assert _count_outbox("delivery.manifest.failed") == 0

    def test_completed_status_no_manifest(self, db_available):
        """Campaign with status=completed must not generate manifests per ADR-016 §1."""
        from packages.domain.delivery import generate_manifests_for_campaign

        _prepare_approved_campaign()
        _reset_manifest_state()
        _raw_exec(
            "UPDATE campaigns SET status = 'completed' WHERE id = :cid",
            {"cid": SEED_CAMPAIGN_ID},
        )

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await _set_rls_scope(session)
                result = await generate_manifests_for_campaign(
                    session, SEED_CAMPAIGN_ID,
                )
                await session.commit()
                return result
            await engine.dispose()

        result = asyncio.run(_run())

        assert result.eligible is False
        assert "completed" in (result.skip_reason or "")
        assert result.manifest_count == 0
        assert _count_manifests() == 0
        assert _count_outbox("delivery.manifest.generated") == 0

    def test_live_status_no_manifest(self, db_available):
        """Unknown/noncanonical status 'live' must not generate manifests."""
        from packages.domain.delivery import generate_manifests_for_campaign

        _prepare_approved_campaign()
        _reset_manifest_state()
        _raw_exec(
            "UPDATE campaigns SET status = 'live' WHERE id = :cid",
            {"cid": SEED_CAMPAIGN_ID},
        )

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await _set_rls_scope(session)
                result = await generate_manifests_for_campaign(
                    session, SEED_CAMPAIGN_ID,
                )
                await session.commit()
                return result
            await engine.dispose()

        result = asyncio.run(_run())

        assert result.eligible is False
        assert "live" in (result.skip_reason or "")
        assert result.manifest_count == 0
        assert _count_manifests() == 0
        assert _count_outbox("delivery.manifest.generated") == 0

    def test_one_device_one_manifest(self, db_available):
        """One physical device gets one manifest with surfaces inside."""
        from packages.domain.delivery import generate_manifests_for_campaign

        _prepare_approved_campaign()
        _reset_manifest_state()

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await _set_rls_scope(session)
                result = await generate_manifests_for_campaign(
                    session, SEED_CAMPAIGN_ID,
                )
                await session.commit()
                return result
            await engine.dispose()

        result = asyncio.run(_run())

        # Count manifests for this campaign
        rows = _raw_sql(
            "SELECT DISTINCT physical_device_id FROM delivery_manifests"
        )
        device_ids = [r[0] for r in rows]
        # Should be exactly one device
        assert len(device_ids) == 1
        assert SEED_DEVICE_ID in device_ids

        # Verify manifest surfaces reference the correct display surface
        manifest_rows = _raw_sql(
            "SELECT dm.manifest_id, dms.display_surface_id "
            "FROM delivery_manifests dm "
            "JOIN delivery_manifest_surfaces dms ON dms.manifest_id = dm.id"
        )
        surface_ids = {r[1] for r in manifest_rows}
        assert SEED_SURFACE_ID in surface_ids

    def test_no_targets_produces_failed_outbox(self, db_available):
        """Campaign with no resolvable placements → delivery.manifest.failed."""
        from packages.domain.delivery import generate_manifests_for_campaign

        _prepare_approved_campaign()
        _reset_manifest_state()
        # Set device to inactive so no surfaces resolve
        _raw_exec(
            "UPDATE physical_devices SET status = 'offline' WHERE id = :did",
            {"did": SEED_DEVICE_ID},
        )

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await _set_rls_scope(session)
                result = await generate_manifests_for_campaign(
                    session, SEED_CAMPAIGN_ID,
                )
                await session.commit()
                return result
            await engine.dispose()

        result = asyncio.run(_run())

        # Eligible but no resolvable targets
        assert result.eligible is True
        assert result.skip_reason is not None
        assert result.manifest_count == 0
        assert _count_outbox("delivery.manifest.failed") >= 1

    def test_store_placement_resolves(self, db_available):
        """Store-level placement resolves to display_surfaces → manifests."""
        from packages.domain.delivery import generate_manifests_for_campaign

        _prepare_approved_campaign()
        _reset_manifest_state()
        # Change placement to target store_id instead of display_surface_id
        _raw_exec(
            "UPDATE campaign_placements "
            "SET display_surface_id = NULL, store_id = :sid "
            "WHERE id = :pid",
            {"sid": SEED_STORE_ID, "pid": SEED_PLACEMENT_ID},
        )

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await _set_rls_scope(session)
                result = await generate_manifests_for_campaign(
                    session, SEED_CAMPAIGN_ID,
                )
                await session.commit()
                return result
            await engine.dispose()

        result = asyncio.run(_run())

        assert result.eligible is True
        assert result.device_count >= 1
        assert result.manifest_count >= 1
        assert result.failure_count == 0

        # Verify manifest surface references the correct surface (resolved via store)
        manifest_rows = _raw_sql(
            "SELECT dm.manifest_id, dms.display_surface_id "
            "FROM delivery_manifests dm "
            "JOIN delivery_manifest_surfaces dms ON dms.manifest_id = dm.id"
        )
        surface_ids = {r[1] for r in manifest_rows}
        assert SEED_SURFACE_ID in surface_ids

        # Restore placement to original state
        _raw_exec(
            "UPDATE campaign_placements "
            "SET display_surface_id = :surface_id, store_id = NULL "
            "WHERE id = :pid",
            {"surface_id": SEED_SURFACE_ID, "pid": SEED_PLACEMENT_ID},
        )

    def test_plan_idempotent_on_rerun(self, db_available):
        """Repeated generation with no changes must not duplicate delivery_plans or outbox."""
        from packages.domain.delivery import generate_manifests_for_campaign

        _prepare_approved_campaign()
        _reset_manifest_state()

        # First run — creates manifests, plan, outbox
        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await _set_rls_scope(session)
                result = await generate_manifests_for_campaign(
                    session, SEED_CAMPAIGN_ID,
                )
                await session.commit()
                return result
            await engine.dispose()

        result1 = asyncio.run(_run())
        plan_count_1 = _raw_sql("SELECT COUNT(*) FROM delivery_plans")[0][0]
        gen_count_1 = _count_outbox("delivery.manifest.generated")

        assert result1.manifest_count >= 1
        assert plan_count_1 >= 1
        assert gen_count_1 >= 1

        # Second run — idempotent, no new manifests/plans/outbox
        async def _run2():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await _set_rls_scope(session)
                result = await generate_manifests_for_campaign(
                    session, SEED_CAMPAIGN_ID,
                )
                await session.commit()
                return result
            await engine.dispose()

        result2 = asyncio.run(_run2())

        plan_count_2 = _raw_sql("SELECT COUNT(*) FROM delivery_plans")[0][0]
        gen_count_2 = _count_outbox("delivery.manifest.generated")

        assert result2.manifest_count == 0
        # No new delivery_plan rows
        assert plan_count_2 == plan_count_1
        # No new outbox events
        assert gen_count_2 == gen_count_1
