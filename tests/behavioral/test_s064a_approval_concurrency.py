"""
Behavioral concurrency proof — Campaign Approval (S-064a).

Proves that .with_for_update() prevents race conditions on
approve_campaign / reject_campaign at the repository layer.

Three scenarios:
  1. Two concurrent approve attempts → exactly one succeeds
  2. Concurrent approve vs reject → exactly one terminal transition
  3. Two concurrent reject attempts → exactly one succeeds

NOTE: This tests the repository layer directly. Outbox events are
created in the API router layer, not the repository — they are not
asserted here.

Requires: RUN_BEHAVIORAL_TESTS=1, migrations applied, seed run.
"""
from __future__ import annotations

import asyncio
import os
import sys
from contextlib import asynccontextmanager

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["ENVIRONMENT"] = "dev"

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncConnection

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)

REQUIRE_ENV = os.environ.get("RUN_BEHAVIORAL_TESTS", "") == "1"
SKIP_REASON = "RUN_BEHAVIORAL_TESTS=1 not set."

SEED_CAMPAIGN_ID = "00000000-0000-0000-0000-000000000220"


# ---------------------------------------------------------------------------
# Async DB helpers
# ---------------------------------------------------------------------------


async def _async_sql(sql: str) -> None:
    """Execute SQL against owner DB (bypasses RLS)."""
    engine = create_async_engine(DB_URL, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("SELECT set_config('app.rmp_is_admin', 'true', true)")
            )
            for stmt in sql.split(";"):
                s = stmt.strip()
                if s and not s.startswith("--"):
                    await conn.execute(text(s))
    finally:
        await engine.dispose()


async def _async_rows(sql: str) -> list:
    """Run SELECT, return all rows as list."""
    engine = create_async_engine(DB_URL, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(
                text("SELECT set_config('app.rmp_is_admin', 'true', false)")
            )
            await conn.commit()
            result = await conn.execute(text(sql))
            return list(result.fetchall())
    finally:
        await engine.dispose()


async def _setup_pending_approval() -> str:
    """Set CAMP-2026-001 to pending_approval. Returns campaign id."""
    await _async_sql(f"""
        UPDATE creative_assets SET
            sha256_checksum = 'ff61a0aee58f05289a5d6f0eba484cbbc397777ad2bb9b12ba6e9ba154f40513',
            file_size_bytes = 245760,
            storage_key = 'adv-001/creatives/001/welcome.png',
            moderation_status = 'approved',
            status = 'ready'
        WHERE code = 'CREATIVE-001';
        UPDATE campaigns SET status = 'draft' WHERE code = 'CAMP-2026-001';
        DELETE FROM outbox_events WHERE aggregate_id = '{SEED_CAMPAIGN_ID}';
        DELETE FROM campaign_approvals WHERE campaign_id = '{SEED_CAMPAIGN_ID}';
        DELETE FROM campaign_status_history
            WHERE campaign_id = '{SEED_CAMPAIGN_ID}' AND changed_by LIKE 'beh-%'
    """)
    await _async_sql(f"""
        UPDATE campaigns SET status = 'pending_approval'
        WHERE code = 'CAMP-2026-001';
        INSERT INTO campaign_status_history
            (id, campaign_id, old_status, new_status, changed_by, changed_at, reason)
        SELECT gen_random_uuid(), id, 'draft', 'pending_approval',
            '00000000-0000-0000-0000-000000000202', NOW(),
            'Approval requested (concurrency test)'
        FROM campaigns WHERE code = 'CAMP-2026-001'
    """)
    return SEED_CAMPAIGN_ID


async def _teardown_campaign() -> None:
    """Reset campaign to draft, clean artifacts."""
    await _async_sql(f"""
        UPDATE campaigns SET status = 'draft' WHERE code = 'CAMP-2026-001';
        DELETE FROM outbox_events WHERE aggregate_id = '{SEED_CAMPAIGN_ID}';
        DELETE FROM campaign_approvals WHERE campaign_id = '{SEED_CAMPAIGN_ID}';
        DELETE FROM campaign_status_history
            WHERE campaign_id = '{SEED_CAMPAIGN_ID}' AND changed_by LIKE 'beh-%'
    """)


@asynccontextmanager
async def _two_connections(engine):
    """Yield two independent AsyncConnections with active transactions."""
    conn1: AsyncConnection = await engine.connect().__aenter__()
    conn2: AsyncConnection = await engine.connect().__aenter__()
    try:
        yield conn1, conn2
    finally:
        await conn1.close()
        await conn2.close()


async def _approve_in_transaction(
    conn: AsyncConnection, campaign_id: str, reviewed_by: str
) -> tuple:
    """Run approve_campaign inside its own transaction (BEGIN + COMMIT)."""
    from packages.domain.repository import approve_campaign

    await conn.execute(text("BEGIN"))
    session = AsyncSession(bind=conn, expire_on_commit=False)
    try:
        result = await approve_campaign(
            session, campaign_id, reviewed_by=reviewed_by
        )
        await session.flush()
        await conn.execute(text("COMMIT"))
        return result
    finally:
        await session.close()


async def _reject_in_transaction(
    conn: AsyncConnection, campaign_id: str, reviewed_by: str, reason: str
) -> tuple:
    """Run reject_campaign inside its own transaction (BEGIN + COMMIT)."""
    from packages.domain.repository import reject_campaign

    await conn.execute(text("BEGIN"))
    session = AsyncSession(bind=conn, expire_on_commit=False)
    try:
        result = await reject_campaign(
            session, campaign_id, reviewed_by=reviewed_by, reason=reason
        )
        await session.flush()
        await conn.execute(text("COMMIT"))
        return result
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def reviewers(test_users):
    """Reviewer user IDs that exist in the DB (created by conftest)."""
    return {
        "a": test_users["secoff"],
        "b": test_users["readonly"],
    }


@pytest.fixture
def _db_check(db_available):
    """Depend on db_available to trigger skip if DB unreachable."""
    return True


# ---------------------------------------------------------------------------
# Scenario 1: Two concurrent approve_campaign calls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_approve_same_campaign(_db_check, reviewers):
    """Two concurrent approve attempts → exactly one succeeds.

    Verifies:
    - Exactly one returns success (old='pending_approval', new='approved')
    - Loser returns (None, None) — safe no-op
    - Exactly one CampaignApproval row with decision='approved'
    - Exactly one CampaignStatusHistory row with new_status='approved'
    """
    cid = await _setup_pending_approval()

    engine = create_async_engine(DB_URL, echo=False)
    try:
        async with _two_connections(engine) as (conn1, conn2):
            r1, r2 = await asyncio.gather(
                _approve_in_transaction(conn1, cid, reviewers["a"]),
                _approve_in_transaction(conn2, cid, reviewers["b"]),
            )
    finally:
        await engine.dispose()

    # Exactly one success, one safe no-op
    successes = [r for r in (r1, r2) if r != (None, None)]
    assert len(successes) == 1, f"r1={r1}, r2={r2}"
    assert successes[0] == ("pending_approval", "approved")

    losers = [r for r in (r1, r2) if r == (None, None)]
    assert len(losers) == 1

    # DB: final status
    rows = await _async_rows(
        f"SELECT status FROM campaigns WHERE id = '{cid}'"
    )
    assert rows[0][0] == "approved"

    # DB: exactly 1 CampaignApproval
    rows = await _async_rows(
        f"SELECT decision FROM campaign_approvals WHERE campaign_id = '{cid}'"
    )
    assert len(rows) == 1 and rows[0][0] == "approved", f"approvals={rows}"

    # DB: exactly 1 approved status-history
    rows = await _async_rows(
        f"SELECT new_status FROM campaign_status_history "
        f"WHERE campaign_id = '{cid}' AND new_status = 'approved'"
    )
    assert len(rows) == 1, f"history={rows}"

    await _teardown_campaign()


# ---------------------------------------------------------------------------
# Scenario 2: Concurrent approve vs reject
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_vs_reject_race(_db_check, reviewers):
    """Approve vs reject concurrently → exactly one terminal transition.

    Verifies:
    - Only one returns success
    - Final status matches winner
    - Exactly one CampaignApproval row, decision matches winner
    """
    cid = await _setup_pending_approval()

    engine = create_async_engine(DB_URL, echo=False)
    try:
        async with _two_connections(engine) as (conn1, conn2):
            r1, r2 = await asyncio.gather(
                _approve_in_transaction(conn1, cid, reviewers["a"]),
                _reject_in_transaction(
                    conn2, cid, reviewers["b"], "Rejected in race"
                ),
            )
    finally:
        await engine.dispose()

    successes = [r for r in (r1, r2) if r != (None, None)]
    assert len(successes) == 1, f"r1={r1}, r2={r2}"
    winner = successes[0]
    assert winner[0] == "pending_approval"
    assert winner[1] in ("approved", "rejected")

    # DB: status matches winner
    rows = await _async_rows(
        f"SELECT status FROM campaigns WHERE id = '{cid}'"
    )
    assert rows[0][0] == winner[1]

    # DB: exactly 1 approval, matches winner
    rows = await _async_rows(
        f"SELECT decision FROM campaign_approvals WHERE campaign_id = '{cid}'"
    )
    assert len(rows) == 1, f"approvals={rows}"
    assert rows[0][0] == winner[1]

    await _teardown_campaign()


# ---------------------------------------------------------------------------
# Scenario 3: Two concurrent reject_campaign calls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_reject_same_campaign(_db_check, reviewers):
    """Two concurrent reject attempts → exactly one succeeds.

    Verifies:
    - Exactly one returns success (old='pending_approval', new='rejected')
    - Loser returns (None, None) — safe no-op
    - Exactly one CampaignApproval row with decision='rejected'
    - Exactly one CampaignStatusHistory row with new_status='rejected'
    """
    cid = await _setup_pending_approval()

    engine = create_async_engine(DB_URL, echo=False)
    try:
        async with _two_connections(engine) as (conn1, conn2):
            r1, r2 = await asyncio.gather(
                _reject_in_transaction(conn1, cid, reviewers["a"], "By A"),
                _reject_in_transaction(conn2, cid, reviewers["b"], "By B"),
            )
    finally:
        await engine.dispose()

    successes = [r for r in (r1, r2) if r != (None, None)]
    assert len(successes) == 1, f"r1={r1}, r2={r2}"
    assert successes[0] == ("pending_approval", "rejected")

    # DB: status
    rows = await _async_rows(
        f"SELECT status FROM campaigns WHERE id = '{cid}'"
    )
    assert rows[0][0] == "rejected"

    # DB: exactly 1 rejection
    rows = await _async_rows(
        f"SELECT decision FROM campaign_approvals WHERE campaign_id = '{cid}'"
    )
    assert len(rows) == 1 and rows[0][0] == "rejected", f"approvals={rows}"

    # DB: exactly 1 rejected history
    rows = await _async_rows(
        f"SELECT new_status FROM campaign_status_history "
        f"WHERE campaign_id = '{cid}' AND new_status = 'rejected'"
    )
    assert len(rows) == 1, f"history={rows}"

    await _teardown_campaign()
