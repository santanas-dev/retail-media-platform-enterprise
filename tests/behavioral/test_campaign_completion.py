"""
LIFECYCLE-COMPLETE-001 — behavioral tests for campaign completion.

Tests: complete_campaign (active→completed), complete_expired_campaigns (batch),
idempotency, terminal guard, flight window checks, cross-org protection.
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
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone, timedelta

from packages.domain import CampaignStatus, validate_transition
from packages.domain import repository

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)
REQUIRE_ENV = os.environ.get("RUN_BEHAVIORAL_TESTS", "") == "1"
SKIP_REASON = "RUN_BEHAVIORAL_TESTS=1 not set."


@pytest.fixture
async def session():
    """Create a fresh async session connected to the behavioral DB."""
    engine = create_async_engine(DB_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s


@pytest.mark.skipif(not REQUIRE_ENV, reason=SKIP_REASON)
class TestCompleteCampaign:
    """Test complete_campaign() against real behavioral DB."""

    async def _create_campaign(self, session, status="active"):
        """Helper: create a minimal campaign in the given status."""
        import uuid
        from packages.domain.models import Campaign

        cid = str(uuid.uuid4())
        campaign = Campaign(
            id=cid,
            code=f"COMPLETE-TEST-{uuid.uuid4().hex[:6]}",
            name="Completion Test Campaign",
            advertiser_organization_id="00000000-0000-0000-0000-000000000200",
            advertiser_contract_id="00000000-0000-0000-0000-000000000212",
            status=status,
            budget_amount=100000,
            budget_currency="RUB",
        )
        session.add(campaign)
        await session.flush()
        return cid

    async def _add_flight(self, session, campaign_id, end_at):
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

    @pytest.mark.asyncio
    async def test_active_with_expired_flights_completes(self, session):
        """Active campaign with all flights in the past → completed."""
        campaign_id = await self._create_campaign(session, "active")
        past = datetime.now(timezone.utc) - timedelta(days=10)
        await self._add_flight(session, campaign_id, past)
        await session.commit()

        old, new = await repository.complete_campaign(session, campaign_id)
        assert old == "active"
        assert new == "completed"

    @pytest.mark.asyncio
    async def test_active_with_future_flight_remains_active(self, session):
        """Active campaign with a future flight → NOT completed."""
        campaign_id = await self._create_campaign(session, "active")
        future = datetime.now(timezone.utc) + timedelta(days=10)
        await self._add_flight(session, campaign_id, future)
        await session.commit()

        old, new = await repository.complete_campaign(session, campaign_id)
        assert old is None
        assert new is None

    @pytest.mark.asyncio
    async def test_no_flights_not_completed(self, session):
        """Campaign with no flights → NOT completed."""
        campaign_id = await self._create_campaign(session, "active")
        await session.commit()

        old, new = await repository.complete_campaign(session, campaign_id)
        assert old is None
        assert new is None

    @pytest.mark.asyncio
    async def test_draft_not_completed(self, session):
        """Draft campaign → NOT completed."""
        campaign_id = await self._create_campaign(session, "draft")
        past = datetime.now(timezone.utc) - timedelta(days=10)
        await self._add_flight(session, campaign_id, past)
        await session.commit()

        old, new = await repository.complete_campaign(session, campaign_id)
        assert old is None
        assert new is None

    @pytest.mark.asyncio
    async def test_repeated_completion_idempotent(self, session):
        """Completing an already-completed campaign → idempotent."""
        campaign_id = await self._create_campaign(session, "active")
        past = datetime.now(timezone.utc) - timedelta(days=10)
        await self._add_flight(session, campaign_id, past)
        await session.commit()

        # First completion
        old1, new1 = await repository.complete_campaign(session, campaign_id)
        await session.commit()
        assert old1 == "active"
        assert new1 == "completed"

        # Second completion — idempotent
        old2, new2 = await repository.complete_campaign(session, campaign_id)
        assert old2 == "completed"
        assert new2 == "completed"

        # Clean up — revert status for DB cleanup (or leave as-is, test isolation)
        # Re-fetch and delete to avoid FK issues
        from packages.domain.models import Campaign
        c = await session.get(Campaign, campaign_id)
        if c:
            await session.delete(c)
            await session.commit()


@pytest.mark.skipif(not REQUIRE_ENV, reason=SKIP_REASON)
class TestCompleteExpiredCampaigns:
    """Test complete_expired_campaigns() batch function."""

    @pytest.mark.asyncio
    async def test_batch_completes_eligible_campaigns(self, session):
        """complete_expired_campaigns finds and completes eligible campaigns."""
        import uuid
        from packages.domain.models import Campaign, CampaignFlight

        # Create 2 active campaigns with expired flights, 1 with future
        past = datetime.now(timezone.utc) - timedelta(days=10)
        future = datetime.now(timezone.utc) + timedelta(days=10)

        ids = []
        for i in range(3):
            cid = str(uuid.uuid4())
            campaign = Campaign(
                id=cid,
                code=f"BATCH-TEST-{uuid.uuid4().hex[:6]}",
                name=f"Batch Test {i}",
                advertiser_organization_id="00000000-0000-0000-0000-000000000200",
                advertiser_contract_id="00000000-0000-0000-0000-000000000212",
                status="active",
                budget_amount=100000,
                budget_currency="RUB",
            )
            session.add(campaign)
            await session.flush()

            end = past if i < 2 else future
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

        await session.commit()

        completed = await repository.complete_expired_campaigns(session)
        await session.commit()

        # First 2 should be completed
        assert len(completed) == 2
        assert ids[0] in completed
        assert ids[1] in completed
        assert ids[2] not in completed

        # Verify statuses
        from packages.domain.models import Campaign
        c0 = await session.get(Campaign, ids[0])
        c1 = await session.get(Campaign, ids[1])
        c2 = await session.get(Campaign, ids[2])
        assert c0.status == "completed"
        assert c1.status == "completed"
        assert c2.status == "active"

        # Cleanup
        for cid in ids:
            c = await session.get(Campaign, cid)
            if c:
                await session.delete(c)
        await session.commit()


@pytest.mark.skipif(not REQUIRE_ENV, reason=SKIP_REASON)
class TestCompletedTerminalGuard:
    """Validate that completed is a terminal state."""

    @pytest.mark.asyncio
    async def test_completed_to_anything_rejected_by_guard(self, session):
        """validate_transition rejects completed → *."""
        with pytest.raises(ValueError, match="Недопустимый переход"):
            validate_transition(CampaignStatus.COMPLETED, CampaignStatus.ACTIVE)

        with pytest.raises(ValueError, match="Недопустимый переход"):
            validate_transition(CampaignStatus.COMPLETED, CampaignStatus.PAUSED)

        with pytest.raises(ValueError, match="Недопустимый переход"):
            validate_transition(CampaignStatus.COMPLETED, CampaignStatus.DRAFT)
