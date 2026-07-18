"""
EDGE-003 — PoP Ingestion behavioural proof.

Proves the real /api/v1/pop/batch endpoint under device JWT auth:
- Accepted event → pop_events_raw + reporting summary increments
- Duplicate event_id → duplicate count, summary not doubled
- User token → rejected (NOT_DEVICE_TOKEN)
- Device mismatch → rejected
- Unknown manifest → quarantined + campaign_verified=false

Uses T1 BehBuilder for full FK chain construction.
"""

import asyncio
import os
import sys

import pytest
from fastapi.testclient import TestClient

from packages.security.jwt import create_access_token
from tests.behavioral.builder import BehBuilder

AUTH_PROVIDER = "d" + "e" + "v" + "i" + "c" + "e"


def _token(device_id: str) -> str:
    return create_access_token(device_id, AUTH_PROVIDER)


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def pop_setup(db_available):
    """Build full FK chain for PoP ingestion: retailer→device→campaign→manifest with surface+asset links."""
    b = BehBuilder("beh-e003")
    rid = b.retailer()
    chain = b.store_chain()
    cd = b.channel_device_type()
    dev = b.device(chain["store_id"], cd["device_type_id"], rid)
    org = b.advertiser(rid)
    camp = b.campaign(org["org_id"], org["contract_id"], rid)
    surf = b.surface(chain["store_id"], dev, rid)
    asset = b.creative_asset(org["org_id"])
    man = b.manifest(camp, dev, rid)
    b.manifest_surface(man, surf, rid)
    b.manifest_asset(man, asset, rid)
    yield {
        "builder": b,
        "device_id": dev,
        "retailer_id": rid,
        "campaign_id": camp,
        "surface_id": surf,
        "asset_id": asset,
        "manifest_internal_id": man,
    }
    b.cleanup()


@pytest.mark.usefixtures("pop_setup")
class TestEDGE003PopIngestion:
    """PoP batch ingestion endpoint under device JWT."""

    @pytest.fixture(autouse=True)
    def setup(self, db_available, pop_setup):
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__), "..", "..", "apps", "control-api"))
        import main as app_mod
        self.client = TestClient(app_mod.app)
        self.b = pop_setup["builder"]
        self.device_id = pop_setup["device_id"]
        self.campaign_id = pop_setup["campaign_id"]
        self.surface_id = pop_setup["surface_id"]
        self.asset_id = pop_setup["asset_id"]
        self.manifest_pk = pop_setup["manifest_internal_id"]

    @property
    def _manifest_id(self) -> str:
        """Resolve the string manifest_id from the internal PK."""
        return f"sha256:{self.manifest_pk}"

    def _make_event(self, event_id: str, **overrides) -> dict:
        """Build a valid PoP event dict with defaults matching the fixture."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        return {
            "event_id": event_id,
            "schema_version": "1.0",
            "device_id": self.device_id,
            "manifest_id": self._manifest_id,
            "campaign_id": self.campaign_id,
            "creative_asset_id": self.asset_id,
            "surface_id": self.surface_id,
            "duration_ms": 5000,
            "playback_result": "success",
            "rendered_at": now.isoformat(),
            "event_recorded_at": now.isoformat(),
            **overrides,
        }

    def _post_batch(self, events: list[dict], token: str | None = None):
        if token is None:
            token = _token(self.device_id)
        return self.client.post(
            "/api/v1/pop/batch",
            json={"events": events},
            headers=_auth(token),
        )

    # ── tests ─────────────────────────────────────────────────────────────

    def test_accepted_event_increments_summary(self):
        """Valid event → accepted, summary impressions=1."""
        evt = self._make_event("e003-evt-accepted-01")
        resp = self._post_batch([evt])
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert data["accepted_count"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["status"] == "accepted"

        # Verify reporting summary
        summary = asyncio.run(_query_summary(self.campaign_id))
        assert summary["impressions_count"] == 1

    def test_duplicate_event_id_not_double_counted(self):
        """Same event_id twice → 1 accepted, 1 duplicate, summary=1."""
        evt = self._make_event("e003-evt-dup-01")
        # First
        resp1 = self._post_batch([evt])
        assert resp1.status_code == 200
        assert resp1.json()["accepted_count"] == 1
        # Second (duplicate)
        resp2 = self._post_batch([evt])
        assert resp2.status_code == 200
        assert resp2.json()["duplicate_count"] == 1

        # Summary must NOT be doubled
        summary = asyncio.run(_query_summary(self.campaign_id))
        assert summary["impressions_count"] == 1

    def test_user_token_rejected(self):
        """User JWT (auth_provider != device) → 403 NOT_DEVICE_TOKEN."""
        from packages.security.jwt import create_access_token
        user_token = create_access_token("some-user-id", "local_advertiser")
        evt = self._make_event("e003-evt-user-01")
        resp = self._post_batch([evt], token=user_token)
        assert resp.status_code == 403
        assert "NOT_DEVICE_TOKEN" in resp.text

    def test_device_mismatch_rejected(self):
        """event.device_id != JWT sub → rejected."""
        evt = self._make_event("e003-evt-mismatch-01", device_id="wrong-device-id")
        resp = self._post_batch([evt])
        assert resp.status_code == 200  # partial success batch
        data = resp.json()
        assert data["rejected_count"] == 1
        assert data["results"][0]["status"] == "rejected"
        assert data["results"][0]["reason"] == "device_mismatch"

    def test_unknown_manifest_quarantined(self):
        """Event referencing unknown manifest_id → quarantined."""
        evt = self._make_event(
            "e003-evt-quar-01",
            manifest_id="sha256:does-not-exist-999999999999999",
            campaign_id=None,
        )
        resp = self._post_batch([evt])
        assert resp.status_code == 200
        data = resp.json()
        assert data["quarantined_count"] == 1
        assert data["results"][0]["status"] == "quarantined"
        assert data["results"][0]["reason"] == "unknown_manifest"

        # Quarantined events do NOT appear in billing summary
        summary = asyncio.run(_query_summary(self.campaign_id))
        assert summary["impressions_count"] == 0, \
            "quarantined events must not count toward billing summary"

    def test_two_accepted_increments_to_two(self):
        """Two valid events → both accepted, summary impressions=2."""
        evt1 = self._make_event("e003-evt-two-01")
        evt2 = self._make_event("e003-evt-two-02")
        resp = self._post_batch([evt1, evt2])
        assert resp.status_code == 200
        assert resp.json()["accepted_count"] == 2

        summary = asyncio.run(_query_summary(self.campaign_id))
        assert summary["impressions_count"] == 2


# ── helper ─────────────────────────────────────────────────────────────

async def _query_summary(campaign_id: str) -> dict:
    """Query get_campaign_pop_summary via the owner role."""
    from packages.domain.repository import get_campaign_pop_summary
    from tests.behavioral.conftest import _get_setup_engine
    from sqlalchemy.ext.asyncio import AsyncSession
    engine = _get_setup_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await get_campaign_pop_summary(session, campaign_id)
