"""
Behavioral test — S-064 Approval Concurrency Proof.

Uses the existing API fixture to create a campaign, then runs two
concurrent approve_campaign calls and asserts exactly one wins.
"""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ["ENVIRONMENT"] = "dev"

from fastapi.testclient import TestClient
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

ADV1_ORG_ID = "00000000-0000-0000-0000-000000000200"
ADV1_CONTRACT_ID = "00000000-0000-0000-0000-000000000212"
ADV1_USER_ID = "00000000-0000-0000-0000-000000000202"


def _adv_token() -> str:
    return create_access_token(ADV1_USER_ID, "local_advertiser")


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
    client = TestClient(app)
    token = _adv_token()

    # Create campaign
    resp = client.post("/api/v1/campaigns", json={
        "advertiser_organization_id": ADV1_ORG_ID,
        "advertiser_contract_id": ADV1_CONTRACT_ID,
        "name": "Concurrency Test",
        "status": "draft",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    cid = resp.json()["id"]

    # Add flight
    resp = client.post(f"/api/v1/campaigns/{cid}/flights", json={
        "name": "cf", "start_at": "2026-01-01T00:00:00Z",
        "end_at": "2027-01-01T00:00:00Z",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text

    # Add placement
    resp = client.post(f"/api/v1/campaigns/{cid}/placements", json={
        "store_id": "00000000-0000-0000-0000-000000000003",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text

    # Create creative + attach
    cr = client.post("/api/v1/creative-assets/with-upload", json={
        "name": "cc", "media_type": "video/mp4",
        "storage_bucket": "t", "storage_key": f"k-{cid[:8]}.mp4",
        "sha256_checksum": "sha256:" + "ab" * 32, "file_size_bytes": 1024,
        "duration_ms": 5000,
    }, headers={"Authorization": f"Bearer {token}"})
    caid = cr.json()["id"]
    client.post(f"/api/v1/campaigns/{cid}/creatives/{caid}",
                headers={"Authorization": f"Bearer {token}"})

    # Request approval
    client.post(f"/api/v1/campaigns/{cid}/approval-request",
                headers={"Authorization": f"Bearer {token}"})

    # Concurrent approve via direct repo
    engine = create_async_engine(DB_URL, echo=False)
    Sess = sa_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _approve(reviewer: str):
        s = Sess()
        try:
            async with s.begin():
                return await approve_campaign(s, cid, reviewed_by=reviewer)
        finally:
            await s.close()

    t1 = asyncio.create_task(_approve("reviewer-a"))
    t2 = asyncio.create_task(_approve("reviewer-b"))
    r1, r2 = await asyncio.gather(t1, t2)
    await engine.dispose()

    success = [r for r in (r1, r2) if r[0] is not None]
    assert len(success) == 1, f"Expected 1 winner: {r1=}, {r2=}"
    assert success[0] == ("pending_approval", "approved")
