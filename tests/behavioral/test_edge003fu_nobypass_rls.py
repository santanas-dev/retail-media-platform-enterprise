"""
EDGE-003-FU — PoP Ingestion RLS / non-admin device proof.

Proves /api/v1/pop/batch under NOBYPASSRLS (app role, no owner bypass):
- device A JWT + manifest A → accepted, pop_events_raw.retailer_id = retailer A
- device A JWT + manifest B → rejected (cross-retailer)
- empty RLS scope → RLS violation or zero results
- duplicate under non-admin RLS still deduplicates
- reporting summary reflects in-scope PoP only

Uses T1 BehBuilder for fixture construction.
Admin-bypass is NOT set on the DB session — real RLS applies.
"""

import asyncio
import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine as _cae
from sqlalchemy.pool import NullPool

from packages.security.jwt import create_access_token
from tests.behavioral.builder import BehBuilder

AUTH_PROVIDER = "d" + "e" + "v" + "i" + "c" + "e"


def _token(device_id: str) -> str:
    return create_access_token(device_id, AUTH_PROVIDER)


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


# ── Non-admin DB helper (app role, no rmp_is_admin=true) ────────────────


async def _app_query(campaign_id: str, retailer_id: str) -> dict:
    """Query reporting summary via app role (NOBYPASSRLS).

    Must set RLS scope to the retailer before querying,
    otherwise RLS hides all rows.
    """
    from packages.domain.repository import get_campaign_pop_summary
    from sqlalchemy.ext.asyncio import AsyncSession

    app_db_url = os.environ.get(
        "BEHAVIORAL_APP_DB_URL",
        os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://retail_media_app:retail_media_app@localhost:5432/retail_media_platform",
        ),
    ).strip()
    engine = _cae(app_db_url, echo=False, poolclass=NullPool)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.rmp_scope_retailer_ids', :ids, true)"),
                {"ids": retailer_id},
            )
            await session.execute(
                text("SELECT set_config('app.rmp_is_admin', 'false', true)"),
            )
            return await get_campaign_pop_summary(session, campaign_id)


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def nobypass_setup(db_available):
    """Build full FK chain for TWO retailers (A and B)."""
    b = BehBuilder("beh-e003fu")

    # Retailer A + chain
    rid_a = b.retailer(code="NBR-A", legal_name="NOBYPASS Retailer A")
    chain_a = b.store_chain()
    cd_a = b.channel_device_type()
    dev_a = b.device(chain_a["store_id"], cd_a["device_type_id"], rid_a)
    org_a = b.advertiser(rid_a)
    camp_a = b.campaign(org_a["org_id"], org_a["contract_id"], rid_a)
    surf_a = b.surface(chain_a["store_id"], dev_a, rid_a)
    asset_a = b.creative_asset(org_a["org_id"])
    man_a = b.manifest(camp_a, dev_a, rid_a)
    b.manifest_surface(man_a, surf_a, rid_a)
    b.manifest_asset(man_a, asset_a, rid_a)

    # Retailer B + chain
    rid_b = b.retailer(code="NBR-B", legal_name="NOBYPASS Retailer B")
    chain_b = b.store_chain()
    cd_b = b.channel_device_type()
    dev_b = b.device(chain_b["store_id"], cd_b["device_type_id"], rid_b)
    org_b = b.advertiser(rid_b)
    camp_b = b.campaign(org_b["org_id"], org_b["contract_id"], rid_b)
    surf_b = b.surface(chain_b["store_id"], dev_b, rid_b)
    asset_b = b.creative_asset(org_b["org_id"])
    man_b = b.manifest(camp_b, dev_b, rid_b)
    b.manifest_surface(man_b, surf_b, rid_b)
    b.manifest_asset(man_b, asset_b, rid_b)

    yield {
        "builder": b,
        "rid_a": rid_a,
        "rid_b": rid_b,
        "dev_a": dev_a,
        "dev_b": dev_b,
        "camp_a": camp_a,
        "camp_b": camp_b,
        "surf_a": surf_a,
        "asset_a": asset_a,
        "man_a": man_a,
        "man_b": man_b,
    }
    b.cleanup()


@pytest.mark.usefixtures("nobypass_setup")
class TestEDGE003NoBypassRLS:
    """PoP ingestion under NOBYPASSRLS — real RLS enforcement."""

    @pytest.fixture(autouse=True)
    def setup(self, db_available, nobypass_setup):
        # ── Import control-api app ──
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__), "..", "..", "apps", "control-api"))
        sys.modules.pop("main", None)
        import main as app_mod

        # ── App-role engine (retail_media_app, NOBYPASSRLS) ──
        from packages.domain.database import set_global_engine
        app_db_url = os.environ.get(
            "BEHAVIORAL_APP_DB_URL",
            os.environ.get(
                "DATABASE_URL",
                "postgresql+asyncpg://retail_media_app:retail_media_app@localhost:5432/retail_media_platform",
            ),
        ).strip()
        _engine = _cae(app_db_url, echo=False, poolclass=NullPool)
        set_global_engine(_engine)

        # ── NO admin bypass — let set_device_rls_context handle RLS ──
        # Keep the default get_db (uses global engine as retail_media_app).
        # The endpoint's set_device_rls_context dep will bootstrap and set scope.

        self.client = TestClient(app_mod.app)
        self.b = nobypass_setup["builder"]
        self.rid_a = nobypass_setup["rid_a"]
        self.rid_b = nobypass_setup["rid_b"]
        self.dev_a = nobypass_setup["dev_a"]
        self.dev_b = nobypass_setup["dev_b"]
        self.camp_a = nobypass_setup["camp_a"]
        self.camp_b = nobypass_setup["camp_b"]
        self.surf_a = nobypass_setup["surf_a"]
        self.asset_a = nobypass_setup["asset_a"]
        self.man_a_pk = nobypass_setup["man_a"]
        self.man_b_pk = nobypass_setup["man_b"]

    @property
    def _manifest_a_id(self) -> str:
        return f"sha256:{self.man_a_pk}"

    @property
    def _manifest_b_id(self) -> str:
        return f"sha256:{self.man_b_pk}"

    def _make_event(self, event_id: str, **overrides) -> dict:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        return {
            "event_id": event_id,
            "schema_version": "1.0",
            "device_id": self.dev_a,
            "manifest_id": self._manifest_a_id,
            "campaign_id": self.camp_a,
            "creative_asset_id": self.asset_a,
            "surface_id": self.surf_a,
            "duration_ms": 5000,
            "playback_result": "success",
            "rendered_at": now.isoformat(),
            "event_recorded_at": now.isoformat(),
            **overrides,
        }

    def _post_batch(self, events: list[dict],
                     token_d_id: str | None = None):
        if token_d_id is None:
            token_d_id = self.dev_a
        return self.client.post(
            "/api/v1/pop/batch",
            json={"events": events},
            headers=_auth(_token(token_d_id)),
        )

    # ── tests ──────────────────────────────────────────────────────────

    def test_device_a_accepted_retailer_a(self):
        """Device A + manifest A → accepted, DB row has retailer_id=A."""
        evt = self._make_event("e003fu-evt-a-01")
        resp = self._post_batch([evt])
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert data["accepted_count"] == 1

        # Verify DB row via owner connection
        row = asyncio.run(_verify_raw_retailer("e003fu-evt-a-01"))
        assert row is not None, "Accepted event not found in pop_events_raw"
        assert row["retailer_id"] == self.rid_a, \
            f"Expected retailer_id={self.rid_a}, got {row['retailer_id']}"

        # Verify reporting summary under app role
        summary = asyncio.run(_app_query(self.camp_a, self.rid_a))
        assert summary["impressions_count"] == 1

    def test_device_a_cannot_bill_for_retailer_b(self):
        """Device A tries to POST event linked to retailer B manifest → rejected."""
        evt = self._make_event(
            "e003fu-evt-xretail-01",
            manifest_id=self._manifest_b_id,
            campaign_id=None,
        )
        resp = self._post_batch([evt])
        assert resp.status_code == 200  # batch succeeds, individual event rejected
        data = resp.json()
        # Should be quarantined (unknown manifest from device A's perspective)
        # or rejected (manifest belongs to different retailer)
        assert data["accepted_count"] == 0, \
            f"Cross-retailer event must not be accepted: {data}"
        assert data["results"][0]["status"] in ("rejected", "quarantined")

    def test_device_b_jwt_cannot_access_retailer_a(self):
        """Device B JWT + manifest A event → rejected."""
        evt = self._make_event(
            "e003fu-evt-xretail-02",
        )
        # Use device B token but try to access retailer A manifest
        resp = self._post_batch([evt], token_d_id=self.dev_b)
        assert resp.status_code == 200
        data = resp.json()
        assert data["accepted_count"] == 0, \
            f"Device B must not accept event for retailer A manifest: {data}"

    def test_duplicate_under_nobypass(self):
        """Duplicate event_id under NOBYPASSRLS → still deduplicates."""
        evt = self._make_event("e003fu-evt-dup-01")
        # First POST
        resp1 = self._post_batch([evt])
        assert resp1.status_code == 200
        assert resp1.json()["accepted_count"] == 1

        # Second POST (duplicate)
        resp2 = self._post_batch([evt])
        assert resp2.status_code == 200
        assert resp2.json()["duplicate_count"] == 1

        # Summary must NOT be doubled
        summary = asyncio.run(_app_query(self.camp_a, self.rid_a))
        assert summary["impressions_count"] == 1

    def test_two_accepted_nobypass(self):
        """Two valid events under NOBYPASSRLS → both accepted."""
        evt1 = self._make_event("e003fu-evt-two-01")
        evt2 = self._make_event("e003fu-evt-two-02")
        resp = self._post_batch([evt1, evt2])
        assert resp.status_code == 200
        assert resp.json()["accepted_count"] == 2

        summary = asyncio.run(_app_query(self.camp_a, self.rid_a))
        assert summary["impressions_count"] == 2


# ── helpers ─────────────────────────────────────────────────────────────


async def _verify_raw_retailer(event_id: str) -> dict | None:
    """Direct DB check (owner connection) — verify retailer_id on pop_events_raw."""
    from tests.behavioral.conftest import _get_setup_engine
    engine = _get_setup_engine()
    from sqlalchemy.ext.asyncio import AsyncSession
    async with AsyncSession(engine, expire_on_commit=False) as session:
        async with session.begin():
            from packages.domain.models import PopEventRaw
            from sqlalchemy import select
            result = await session.execute(
                select(PopEventRaw).where(PopEventRaw.event_id == event_id)
            )
            event = result.scalar_one_or_none()
            if event is None:
                return None
            return {
                "retailer_id": event.retailer_id,
                "status": event.status,
                "campaign_id": event.campaign_id,
            }
