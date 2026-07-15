"""
Behavioral tests — Approval Concurrency (S-064).

Tests: concurrent approve, approve-vs-reject race, concurrent reject.
Uses real PostgreSQL with asyncio.gather + separate AsyncSessions.
Requires: RUN_BEHAVIORAL_TESTS=1, migrations applied, seed run.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["ENVIRONMENT"] = "dev"

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from packages.domain.repository import (
    approve_campaign,
    reject_campaign,
    request_campaign_approval,
)

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)

REQUIRE_ENV = os.environ.get("RUN_BEHAVIORAL_TESTS", "") == "1"
SKIP_REASON = "RUN_BEHAVIORAL_TESTS=1 not set."

ADV1_ORG_ID = "00000000-0000-0000-0000-000000000200"
ADV1_CONTRACT_ID = "00000000-0000-0000-0000-000000000212"

_CAMPAIGN_ID = "beh-concur-camp-000000000000001"
_CREATIVE_ID = "beh-concur-cr-00000000000001"


@pytest.fixture
def db_available():
    if not REQUIRE_ENV:
        pytest.skip(SKIP_REASON)


async def _run_sql(sql: str) -> None:
    engine = create_async_engine(DB_URL, echo=False)
    async with engine.begin() as conn:
        for stmt in sql.split(";"):
            s = stmt.strip()
            if s and not s.startswith("--"):
                await conn.execute(text(s))
    await engine.dispose()


def _engine_factory():
    return create_async_engine(DB_URL, echo=False)


def _utc_str(offset_days: int) -> str:
    return (datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0,
    )).strftime("%Y-%m-%d")


_SEED = f"""
INSERT INTO advertiser_organizations (id, code, legal_name, display_name, status)
VALUES ('{ADV1_ORG_ID}', 'BEH-CONCUR-ADV', 'Concurrency Advertiser', 'Concurrency Test', 'active')
ON CONFLICT (code) DO NOTHING
;
INSERT INTO advertiser_contracts (id, advertiser_organization_id, code, name, valid_from, status)
VALUES ('{ADV1_CONTRACT_ID}', '{ADV1_ORG_ID}', 'BEH-CONCUR-CTR', 'Concurrency Contract', NOW(), 'active')
ON CONFLICT (advertiser_organization_id, code) DO NOTHING
;
INSERT INTO campaigns (id, advertiser_organization_id, advertiser_contract_id, code, name, status, created_by)
VALUES ('{_CAMPAIGN_ID}', '{ADV1_ORG_ID}', '{ADV1_CONTRACT_ID}', 'BEH-CONCUR-CAMP', 'Concurrency Campaign', 'draft', NULL)
ON CONFLICT (advertiser_organization_id, code) DO NOTHING
;
INSERT INTO creative_assets (id, advertiser_organization_id, code, name, media_type,
    storage_bucket, storage_key, sha256_checksum, file_size_bytes, duration_ms, status, moderation_status)
VALUES ('{_CREATIVE_ID}', '{ADV1_ORG_ID}', 'BEH-CONCUR-CR', 'Concurrency Creative', 'video/mp4',
   'test-bucket', 'test-key.mp4', 'sha256:deadbeef', 1024, 5000, 'ready', 'approved')
ON CONFLICT (advertiser_organization_id, code) DO NOTHING
;
INSERT INTO campaign_flights (id, campaign_id, code, flight_type, start_at, end_at)
VALUES ('beh-concur-fl-000000000000001', '{_CAMPAIGN_ID}', 'BEH-CONCUR-FL', 'guaranteed',
        '{_utc_str(-30)}', '{_utc_str(365)}')
ON CONFLICT DO NOTHING
;
INSERT INTO campaign_placements (id, campaign_id, code)
VALUES ('beh-concur-pl-000000000000001', '{_CAMPAIGN_ID}', 'BEH-CONCUR-PL')
ON CONFLICT DO NOTHING
;
INSERT INTO campaign_creatives (id, campaign_id, creative_asset_id)
VALUES ('beh-concur-cc-000000000000001', '{_CAMPAIGN_ID}', '{_CREATIVE_ID}')
ON CONFLICT DO NOTHING
"""

_CLEANUP = f"""
DELETE FROM campaign_approvals WHERE campaign_id = '{_CAMPAIGN_ID}'
;
DELETE FROM campaign_status_history WHERE campaign_id = '{_CAMPAIGN_ID}'
;
DELETE FROM outbox WHERE aggregate_id = '{_CAMPAIGN_ID}'
;
DELETE FROM audit_events_operational WHERE target_id = '{_CAMPAIGN_ID}'
;
DELETE FROM campaign_creatives WHERE campaign_id = '{_CAMPAIGN_ID}'
;
DELETE FROM campaign_placements WHERE campaign_id = '{_CAMPAIGN_ID}'
;
DELETE FROM campaign_flights WHERE campaign_id = '{_CAMPAIGN_ID}'
;
DELETE FROM campaigns WHERE id = '{_CAMPAIGN_ID}'
;
DELETE FROM creative_assets WHERE id = '{_CREATIVE_ID}'
;
DELETE FROM advertiser_contracts WHERE id = '{ADV1_CONTRACT_ID}'
;
DELETE FROM advertiser_organizations WHERE code = 'BEH-CONCUR-ADV'
"""


async def _count_rows(session: AsyncSession, table: str, campaign_id: str) -> int:
    result = await session.execute(
        text(f"SELECT count(*) FROM {table} WHERE campaign_id = :cid"),
        {"cid": campaign_id},
    )
    return result.scalar_one()


class TestApproveConcurrency:
    """S-064: concurrent approve atomicity — SELECT FOR UPDATE proof."""

    @pytest.fixture(autouse=True)
    async def _setup_teardown(self, db_available):
        await _run_sql(_SEED)
        # Move campaign to pending_approval via request_campaign_approval
        engine = _engine_factory()
        async with sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as s:
            async with s.begin():
                old, new = await request_campaign_approval(s, _CAMPAIGN_ID, changed_by="fixture")
                assert old == "draft" and new == "pending_approval", \
                    f"request_approval: old={old}, new={new}"
        await engine.dispose()
        yield
        await _run_sql(_CLEANUP)

    async def _run_approve(self, reviewer: str) -> tuple[str | None, str | None]:
        engine = _engine_factory()
        session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)()
        try:
            async with session.begin():
                return await approve_campaign(
                    session, _CAMPAIGN_ID, reviewed_by=reviewer,
                )
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_concurrent_approve_exactly_one_wins(self):
        """Two concurrent approves: exactly one succeeds, one returns (None, None)."""
        t1 = asyncio.create_task(self._run_approve("reviewer-a"))
        t2 = asyncio.create_task(self._run_approve("reviewer-b"))

        r1, r2 = await asyncio.gather(t1, t2)

        success = [r for r in (r1, r2) if r[0] is not None]
        failure = [r for r in (r1, r2) if r[0] is None]
        assert len(success) == 1, f"Expected 1 success, got: {r1=}, {r2=}"
        assert len(failure) == 1
        assert success[0] == ("pending_approval", "approved")
        assert failure[0] == (None, None)

    @pytest.mark.asyncio
    async def test_no_duplicate_approval_records(self):
        """After concurrent approve, exactly 1 CampaignApproval row."""
        t1 = asyncio.create_task(self._run_approve("reviewer-a"))
        t2 = asyncio.create_task(self._run_approve("reviewer-b"))
        await asyncio.gather(t1, t2)

        engine = _engine_factory()
        session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)()
        try:
            count = await _count_rows(session, "campaign_approvals", _CAMPAIGN_ID)
            assert count == 1, f"Expected 1 approval row, got {count}"
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_no_duplicate_status_history(self):
        """After concurrent approve, exactly 1 'pending_approval→approved' transition."""
        t1 = asyncio.create_task(self._run_approve("reviewer-a"))
        t2 = asyncio.create_task(self._run_approve("reviewer-b"))
        await asyncio.gather(t1, t2)

        engine = _engine_factory()
        session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)()
        try:
            result = await session.execute(text(
                "SELECT count(*) FROM campaign_status_history "
                "WHERE campaign_id = :cid AND old_status = 'pending_approval' "
                "AND new_status = 'approved'"
            ), {"cid": _CAMPAIGN_ID})
            count = result.scalar_one()
            assert count == 1, f"Expected 1 approve transition, got {count}"
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_no_duplicate_outbox(self):
        """After concurrent approve, at most 1 outbox event."""
        t1 = asyncio.create_task(self._run_approve("reviewer-a"))
        t2 = asyncio.create_task(self._run_approve("reviewer-b"))
        await asyncio.gather(t1, t2)

        engine = _engine_factory()
        session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)()
        try:
            count = await _count_rows(session, "outbox", _CAMPAIGN_ID)
            assert count <= 1, f"Expected ≤1 outbox event, got {count}"
        finally:
            await session.close()
            await engine.dispose()


class TestApproveVsRejectRace:
    """S-064: approve vs reject race — only one terminal transition."""

    @pytest.fixture(autouse=True)
    async def _setup_teardown(self, db_available):
        await _run_sql(_SEED)
        engine = _engine_factory()
        async with sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as s:
            async with s.begin():
                old, new = await request_campaign_approval(s, _CAMPAIGN_ID, changed_by="fixture")
                assert old == "draft" and new == "pending_approval"
        await engine.dispose()
        yield
        await _run_sql(_CLEANUP)

    async def _run_approve(self) -> tuple[str | None, str | None]:
        engine = _engine_factory()
        session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)()
        try:
            async with session.begin():
                return await approve_campaign(
                    session, _CAMPAIGN_ID, reviewed_by="approver",
                )
        finally:
            await session.close()
            await engine.dispose()

    async def _run_reject(self) -> tuple[str | None, str | None]:
        engine = _engine_factory()
        session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)()
        try:
            async with session.begin():
                return await reject_campaign(
                    session, _CAMPAIGN_ID, reviewed_by="rejector",
                    reason="test reject",
                )
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_approve_vs_reject_exactly_one_wins(self):
        """Concurrent approve+reject: exactly one succeeds."""
        t_approve = asyncio.create_task(self._run_approve())
        t_reject = asyncio.create_task(self._run_reject())
        r_approve, r_reject = await asyncio.gather(t_approve, t_reject)

        success = [r for r in (r_approve, r_reject) if r[0] is not None]
        failure = [r for r in (r_approve, r_reject) if r[0] is None]
        assert len(success) == 1, f"Expected 1 winner: approve={r_approve}, reject={r_reject}"
        assert len(failure) == 1
        assert failure[0] == (None, None)
        old, new = success[0]
        assert old == "pending_approval"
        assert new in ("approved", "rejected")

    @pytest.mark.asyncio
    async def test_approve_vs_reject_no_contradictory_approvals(self):
        """After race, CampaignApproval has at most 1 row with consistent decision."""
        t_approve = asyncio.create_task(self._run_approve())
        t_reject = asyncio.create_task(self._run_reject())
        await asyncio.gather(t_approve, t_reject)

        engine = _engine_factory()
        session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)()
        try:
            result = await session.execute(
                text("SELECT count(*), decision FROM campaign_approvals "
                     "WHERE campaign_id = :cid GROUP BY decision"),
                {"cid": _CAMPAIGN_ID},
            )
            rows = result.fetchall()
            total = sum(r[0] for r in rows)
            assert total <= 1, f"Expected ≤1 approval row, got {total}: {rows}"
        finally:
            await session.close()
            await engine.dispose()


class TestRejectConcurrency:
    """S-064: concurrent reject atomicity."""

    @pytest.fixture(autouse=True)
    async def _setup_teardown(self, db_available):
        await _run_sql(_SEED)
        engine = _engine_factory()
        async with sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as s:
            async with s.begin():
                old, new = await request_campaign_approval(s, _CAMPAIGN_ID, changed_by="fixture")
                assert old == "draft" and new == "pending_approval"
        await engine.dispose()
        yield
        await _run_sql(_CLEANUP)

    async def _run_reject(self, reviewer: str) -> tuple[str | None, str | None]:
        engine = _engine_factory()
        session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)()
        try:
            async with session.begin():
                return await reject_campaign(
                    session, _CAMPAIGN_ID, reviewed_by=reviewer,
                    reason="concurrent reject",
                )
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_concurrent_reject_exactly_one_wins(self):
        """Two concurrent rejects: exactly one succeeds."""
        t1 = asyncio.create_task(self._run_reject("rejector-1"))
        t2 = asyncio.create_task(self._run_reject("rejector-2"))
        r1, r2 = await asyncio.gather(t1, t2)

        success = [r for r in (r1, r2) if r[0] is not None]
        failure = [r for r in (r1, r2) if r[0] is None]
        assert len(success) == 1, f"Expected 1 success: {r1=}, {r2=}"
        assert len(failure) == 1
        assert success[0] == ("pending_approval", "rejected")
