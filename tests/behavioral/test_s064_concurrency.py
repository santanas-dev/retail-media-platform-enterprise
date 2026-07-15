"""
Behavioral test — S-064 Approval Concurrency Proof.

Uses the existing seed campaign (CAMP-2026-001) to test that
two concurrent approve_campaign calls result in exactly one winner.
"""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ["ENVIRONMENT"] = "dev"

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker as sa_sessionmaker

from packages.domain.repository import approve_campaign
from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)
REQUIRE_ENV = os.environ.get("RUN_BEHAVIORAL_TESTS", "") == "1"

CAMP_ID = "00000000-0000-0000-0000-000000000220"
ADV_USER_ID = "00000000-0000-0000-0000-000000000202"
CREATIVE_ID = "00000000-0000-0000-0000-000000000230"
STORE_ID = "00000000-0000-0000-0000-000000000003"


def _adv_token() -> str:
    return create_access_token(ADV_USER_ID, "local_advertiser")


async def _raw_sql(sql_str, params=None):
    """Execute SQL via async engine (for setup/teardown within async test)."""
    e = create_async_engine(DB_URL, echo=False)
    async with e.begin() as c:
        await c.execute(text("SELECT set_config('app.rmp_is_admin', 'true', true)"))
        r = await c.execute(text(sql_str), params or {})
        rows = r.fetchall()
    await e.dispose()
    return rows


async def _reset_campaign():
    """Reset campaign to draft + clean up flights/placements/approvals."""
    await _raw_sql(f"""
    DELETE FROM campaign_approvals WHERE campaign_id = '{CAMP_ID}'
    """)
    await _raw_sql(f"""
    DELETE FROM campaign_status_history WHERE campaign_id = '{CAMP_ID}'
      AND new_status IN ('pending_approval', 'approved', 'rejected')
    """)
    await _raw_sql(f"""
    DELETE FROM campaign_creatives WHERE campaign_id = '{CAMP_ID}'
    """)
    await _raw_sql(f"""
    DELETE FROM campaign_placements WHERE campaign_id = '{CAMP_ID}'
    """)
    await _raw_sql(f"""
    DELETE FROM campaign_flights WHERE campaign_id = '{CAMP_ID}'
    """)
    await _raw_sql(f"""
    UPDATE campaigns SET status = 'draft' WHERE id = '{CAMP_ID}'
    """)


@pytest.fixture
def app(db_available):
    import importlib.util
    reset_security_config()
    main_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "apps", "control-api", "main.py",
    )
    spec = importlib.util.spec_from_file_location("control_api_main", main_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.app


@pytest.fixture
def db_available():
    if not REQUIRE_ENV:
        pytest.skip("RUN_BEHAVIORAL_TESTS=1 not set.")


@pytest.mark.asyncio
async def test_concurrent_approve_exactly_one_wins(db_available, app):
    """S-064: two concurrent approve_campaign calls → exactly one succeeds."""
    await _reset_campaign()
    client = TestClient(app)
    token = _adv_token()

    # Add flight
    resp = client.post(f"/api/v1/identity/campaigns/{CAMP_ID}/flights", json={
        "name": "concur-flight",
        "start_at": "2026-01-01T00:00:00Z",
        "end_at": "2027-01-01T00:00:00Z",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"flight: {resp.text}"

    # Add placement
    resp = client.post(f"/api/v1/identity/campaigns/{CAMP_ID}/placements", json={
        "store_id": STORE_ID,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"placement: {resp.text}"

    # Attach existing creative
    resp = client.post(f"/api/v1/identity/campaigns/{CAMP_ID}/creatives/{CREATIVE_ID}",
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"creative: {resp.text}"

    # Request approval
    resp = client.post(f"/api/v1/identity/campaigns/{CAMP_ID}/approval-request",
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"approval-request: {resp.text}"

    # Concurrent approve via direct repo access
    engine = create_async_engine(DB_URL, echo=False)
    Sess = sa_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _approve(reviewer: str):
        s = Sess()
        try:
            async with s.begin():
                return await approve_campaign(s, CAMP_ID, reviewed_by=reviewer)
        finally:
            await s.close()

    t1 = asyncio.create_task(_approve("00000000-0000-0000-0000-000000000150"))
    t2 = asyncio.create_task(_approve("00000000-0000-0000-0000-000000000150"))
    r1, r2 = await asyncio.gather(t1, t2)
    await engine.dispose()

    success = [r for r in (r1, r2) if r[0] is not None]
    failure = [r for r in (r1, r2) if r[0] is None]
    assert len(success) == 1, (
        f"S-064: Expected 1 concurrent approve winner, got success={len(success)} "
        f"failure={len(failure)}: {r1=}, {r2=}"
    )
    assert success[0] == ("pending_approval", "approved")
    assert failure[0] == (None, None)
