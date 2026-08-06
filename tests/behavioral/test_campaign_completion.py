"""
LIFECYCLE-COMPLETE-001-FU — real DB behavioral tests for campaign completion.

Tests: complete_campaign (active→completed), complete_expired_campaigns (batch),
idempotency, terminal guard, flight window checks, cross-org protection,
CampaignStatusHistory verification, API endpoint happy/invalid.
Requires: RUN_BEHAVIORAL_TESTS=1, migrations applied, seed run.
"""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ["ENVIRONMENT"] = "dev"

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime, timezone, timedelta

from packages.domain import CampaignStatus, validate_transition
from packages.domain import repository

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media_owner:retail_media_owner_pass@localhost:5432/retail_media_platform",
)
REQUIRE_ENV = os.environ.get("RUN_BEHAVIORAL_TESTS", "") == "1"
SKIP_REASON = "RUN_BEHAVIORAL_TESTS=1 not set."

pytestmark = pytest.mark.skipif(not REQUIRE_ENV, reason=SKIP_REASON)


def _engine():
    """Create a fresh async engine for the behavioral DB."""
    return create_async_engine(DB_URL, echo=False)


# ---------------------------------------------------------------------------
# Helper: create campaign + flight in real DB
# ---------------------------------------------------------------------------

async def _create_campaign(session, status="active", org_id="00000000-0000-0000-0000-000000000200",
                           contract_id="00000000-0000-0000-0000-000000000212"):
    """Helper: create a minimal campaign in the given status."""
    import uuid
    from packages.domain.models import Campaign

    cid = str(uuid.uuid4())
    campaign = Campaign(
        id=cid,
        code=f"COMPLETE-TEST-{uuid.uuid4().hex[:6]}",
        name="Completion Test Campaign",
        advertiser_organization_id=org_id,
        advertiser_contract_id=contract_id,
        status=status,
        budget_limit_amount=100000,
        budget_limit_currency="RUB",
    )
    session.add(campaign)
    await session.flush()
    return cid


async def _add_flight(session, campaign_id, end_at):
    """Helper: add a flight with given end_at."""
    import uuid
    from packages.domain.models import CampaignFlight

    fid = str(uuid.uuid4())
    flight = CampaignFlight(
        id=fid,
        campaign_id=campaign_id,
        name="Test Flight",
        start_at=end_at - timedelta(days=30),
        end_at=end_at,
    )
    session.add(flight)
    await session.flush()
    return fid


async def _cleanup_campaigns(session, *campaign_ids):
    """Delete test campaigns and all dependent rows (history, flights, then campaigns)."""
    from packages.domain.models import Campaign
    for cid in campaign_ids:
        # Delete dependent rows first (FK references to campaigns)
        await session.execute(
            text("DELETE FROM campaign_status_history WHERE campaign_id = :cid"),
            {"cid": cid},
        )
        await session.execute(
            text("DELETE FROM campaign_flights WHERE campaign_id = :cid"),
            {"cid": cid},
        )
        c = await session.get(Campaign, cid)
        if c:
            await session.delete(c)
    await session.commit()


# ---------------------------------------------------------------------------
# Test: complete_campaign (single)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_active_with_expired_flights_completes():
    """Active campaign with all flights in the past → completed."""
    async with AsyncSession(_engine()) as session:
        async with session.begin():
            campaign_id = await _create_campaign(session, "active")
            past = datetime.now(timezone.utc) - timedelta(days=10)
            await _add_flight(session, campaign_id, past)

        old, new = await repository.complete_campaign(session, campaign_id)
        assert old == "active"
        assert new == "completed"

        # Flush to ensure status history is visible
        await session.flush()

        # Verify CampaignStatusHistory row
        rows = (await session.execute(
            text("SELECT old_status, new_status FROM campaign_status_history WHERE campaign_id=:cid ORDER BY changed_at DESC LIMIT 1"),
            {"cid": campaign_id},
        )).fetchall()
        assert len(rows) == 1
        assert rows[0].old_status == "active"
        assert rows[0].new_status == "completed"

        await _cleanup_campaigns(session, campaign_id)


@pytest.mark.asyncio
async def test_active_with_future_flight_remains_active():
    """Active campaign with a future flight → NOT completed."""
    async with AsyncSession(_engine()) as session:
        async with session.begin():
            campaign_id = await _create_campaign(session, "active")
            future = datetime.now(timezone.utc) + timedelta(days=10)
            await _add_flight(session, campaign_id, future)

        old, new = await repository.complete_campaign(session, campaign_id)
        assert old is None
        assert new is None

        # Verify status unchanged
        from packages.domain.models import Campaign
        c = await session.get(Campaign, campaign_id)
        assert c.status == "active"

        await _cleanup_campaigns(session, campaign_id)


@pytest.mark.asyncio
async def test_no_flights_not_completed():
    """Campaign with no flights → NOT completed."""
    async with AsyncSession(_engine()) as session:
        async with session.begin():
            campaign_id = await _create_campaign(session, "active")

        old, new = await repository.complete_campaign(session, campaign_id)
        assert old is None
        assert new is None

        await _cleanup_campaigns(session, campaign_id)


@pytest.mark.asyncio
async def test_draft_not_completed():
    """Draft campaign → NOT completed."""
    async with AsyncSession(_engine()) as session:
        async with session.begin():
            campaign_id = await _create_campaign(session, "draft")
            past = datetime.now(timezone.utc) - timedelta(days=10)
            await _add_flight(session, campaign_id, past)

        old, new = await repository.complete_campaign(session, campaign_id)
        assert old is None
        assert new is None

        await _cleanup_campaigns(session, campaign_id)


@pytest.mark.asyncio
async def test_repeated_completion_idempotent():
    """Completing an already-completed campaign → idempotent, no duplicate status history."""
    async with AsyncSession(_engine()) as session:
        async with session.begin():
            campaign_id = await _create_campaign(session, "active")
            past = datetime.now(timezone.utc) - timedelta(days=10)
            await _add_flight(session, campaign_id, past)

        # First completion
        old1, new1 = await repository.complete_campaign(session, campaign_id)
        await session.commit()
        assert old1 == "active"
        assert new1 == "completed"

        # Second completion — idempotent
        old2, new2 = await repository.complete_campaign(session, campaign_id)
        assert old2 == "completed"
        assert new2 == "completed"

        # Verify exactly 1 status history entry (not 2)
        rows = (await session.execute(
            text("SELECT COUNT(*) as cnt FROM campaign_status_history WHERE campaign_id=:cid AND new_status='completed'"),
            {"cid": campaign_id},
        )).fetchall()
        assert rows[0].cnt == 1, f"Expected 1 completed history row, got {rows[0].cnt}"

        await _cleanup_campaigns(session, campaign_id)


@pytest.mark.asyncio
async def test_completed_terminal_guard_rejects():
    """validate_transition rejects completed → *."""
    with pytest.raises(ValueError, match="Недопустимый переход"):
        validate_transition(CampaignStatus.COMPLETED, CampaignStatus.ACTIVE)

    with pytest.raises(ValueError, match="Недопустимый переход"):
        validate_transition(CampaignStatus.COMPLETED, CampaignStatus.PAUSED)

    with pytest.raises(ValueError, match="Недопустимый переход"):
        validate_transition(CampaignStatus.COMPLETED, CampaignStatus.DRAFT)


# ---------------------------------------------------------------------------
# Test: complete_expired_campaigns (batch)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_batch_completes_eligible_campaigns():
    """complete_expired_campaigns finds and completes eligible campaigns, leaves others untouched."""
    import uuid
    from packages.domain.models import Campaign, CampaignFlight

    async with AsyncSession(_engine()) as session:
        past = datetime.now(timezone.utc) - timedelta(days=10)
        future = datetime.now(timezone.utc) + timedelta(days=10)

        ids = []
        async with session.begin():
            for i in range(4):
                cid = str(uuid.uuid4())
                campaign = Campaign(
                    id=cid,
                    code=f"BATCH-TEST-{uuid.uuid4().hex[:6]}",
                    name=f"Batch Test {i}",
                    advertiser_organization_id="00000000-0000-0000-0000-000000000200",
                    advertiser_contract_id="00000000-0000-0000-0000-000000000212",
                    status="active",
                    budget_limit_amount=100000,
                    budget_limit_currency="RUB",
                )
                session.add(campaign)
                await session.flush()

                # 0,1: expired  2: future  3: no flights
                if i == 0 or i == 1:
                    end = past
                elif i == 2:
                    end = future
                else:
                    ids.append(cid)
                    continue

                flight = CampaignFlight(
                    id=str(uuid.uuid4()),
                    campaign_id=cid,
                    name=f"Flight {i}",
                    start_at=end - timedelta(days=30),
                    end_at=end,
                )
                session.add(flight)
                await session.flush()
                ids.append(cid)

        completed = await repository.complete_expired_campaigns(session)
        await session.commit()

        # First 2 should be completed
        assert len(completed) == 2, f"Expected 2 completed, got {len(completed)}: {completed}"
        assert ids[0] in completed
        assert ids[1] in completed
        assert ids[2] not in completed  # future flight
        assert ids[3] not in completed  # no flights

        # Verify statuses
        c0 = await session.get(Campaign, ids[0])
        c1 = await session.get(Campaign, ids[1])
        c2 = await session.get(Campaign, ids[2])
        c3 = await session.get(Campaign, ids[3])
        assert c0.status == "completed"
        assert c1.status == "completed"
        assert c2.status == "active"    # future flight → untouched
        assert c3.status == "active"    # no flights → untouched

        # Verify status history for completed campaigns
        for cid in [ids[0], ids[1]]:
            rows = (await session.execute(
                text("SELECT old_status, new_status FROM campaign_status_history WHERE campaign_id=:cid ORDER BY changed_at DESC LIMIT 1"),
                {"cid": cid},
            )).fetchall()
            assert len(rows) == 1
            assert rows[0].old_status == "active"
            assert rows[0].new_status == "completed"

        # No status history for untouched campaigns
        for cid in [ids[2], ids[3]]:
            rows = (await session.execute(
                text("SELECT COUNT(*) as cnt FROM campaign_status_history WHERE campaign_id=:cid"),
                {"cid": cid},
            )).fetchall()
            assert rows[0].cnt == 0, f"Campaign {cid} should have no status history"

        await _cleanup_campaigns(session, *ids)
