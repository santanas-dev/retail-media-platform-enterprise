"""
EDGE-002-FU v4 — Behavioural proof: real device-gateway endpoint under NOBYPASSRLS.

v4: Production-safe bootstrap.  set_device_rls_context uses app.rmp_device_id
(migration 023) to look up the device's retailer_id on the REQUEST session
(app role).  No owner/bypass session in the request path.  RLS policy on
physical_devices allows SELECT when id = app.rmp_device_id.

Proves: device JWT → 200/304/401/404 through the real endpoint.
+ Direct DB RLS proof: app role with app.rmp_device_id sees only its own device row.
"""

import asyncio
import os
import sys

import pytest
from fastapi.testclient import TestClient

from packages.security.jwt import create_access_token
from tests.behavioral.conftest import _run_sql

RET_A = "beh-e002fu-ret-a-00000000000001"
RET_B = "beh-e002fu-ret-b-00000000000002"
STORE_A = "beh-e002fu-store-a-0000000000001"
STORE_B = "beh-e002fu-store-b-0000000000002"
DEVICE_A_ID = "beh-e002fu-dev-a-00000000000001"
DEVICE_B_ID = "beh-e002fu-dev-b-00000000000002"

_AUTH_PROV = "device"


def _token(device_id: str) -> str:
    return create_access_token(device_id, _AUTH_PROV)


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def e002fu_setup(db_available):
    """Two retailers: A (with store/device/manifest) and B (store/device, NO manifest)."""
    # ── Retailer A ──
    asyncio.run(_run_sql(f"""
    INSERT INTO retailers (id, code, legal_name, display_name, status)
    VALUES ('{RET_A}', 'E002FU-RET-A', 'Retailer Alpha', 'Alpha', 'active')
    ON CONFLICT (id) DO NOTHING;
    """))
    # ── Retailer B ──
    asyncio.run(_run_sql(f"""
    INSERT INTO retailers (id, code, legal_name, display_name, status)
    VALUES ('{RET_B}', 'E002FU-RET-B', 'Retailer Beta', 'Beta', 'active')
    ON CONFLICT (id) DO NOTHING;
    """))
    # ── Branch → Cluster → Store A ──
    asyncio.run(_run_sql("""
    INSERT INTO branches (id, code, name, timezone, is_active)
    VALUES ('beh-e002fu-br-01', 'E002FU-BR', 'Test Branch', 'Europe/Moscow', true)
    ON CONFLICT (code) DO NOTHING;
    """))
    asyncio.run(_run_sql("""
    INSERT INTO clusters (id, branch_id, code, name, is_active)
    VALUES ('beh-e002fu-cl-01', 'beh-e002fu-br-01', 'E002FU-CL', 'Test Cluster', true)
    ON CONFLICT (code) DO NOTHING;
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO stores (id, cluster_id, code, name, is_active)
    VALUES ('{STORE_A}', 'beh-e002fu-cl-01', 'E002FU-ST-A', 'Store A', true)
    ON CONFLICT (code) DO NOTHING;
    """))
    # ── Store B (different cluster, same branch) ──
    asyncio.run(_run_sql(f"""
    INSERT INTO stores (id, cluster_id, code, name, is_active, retailer_id)
    VALUES ('{STORE_B}', 'beh-e002fu-cl-01', 'E002FU-ST-B', 'Store B', true, '{RET_B}')
    ON CONFLICT (code) DO NOTHING;
    """))
    # ── Channel → Device Type ──
    asyncio.run(_run_sql("""
    INSERT INTO channels (id, code, name, is_active)
    VALUES ('beh-e002fu-ch-01', 'E002FU-CH', 'Test Channel', true)
    ON CONFLICT (code) DO NOTHING;
    """))
    asyncio.run(_run_sql("""
    INSERT INTO device_types (id, channel_id, code, name, player_runtime)
    VALUES ('beh-e002fu-dt-01', 'beh-e002fu-ch-01', 'E002FU-KSO',
            'KSO Test', 'chromium')
    ON CONFLICT (code) DO NOTHING;
    """))
    # ── Org → Contract → Campaign ──
    asyncio.run(_run_sql(f"""
    INSERT INTO advertiser_organizations (id, code, legal_name, display_name, status, retailer_id)
    VALUES ('beh-e002fu-org-01', 'E002FU-ORG', 'Test Org', 'Test Org', 'active', '{RET_A}')
    ON CONFLICT (id) DO NOTHING;
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO advertiser_contracts (id, advertiser_organization_id, code, name, status, retailer_id)
    VALUES ('beh-e002fu-cont-01', 'beh-e002fu-org-01', 'E002FU-CONT', 'Test Contract', 'active', '{RET_A}')
    ON CONFLICT (id) DO NOTHING;
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO campaigns (id, code, name, advertiser_organization_id,
        advertiser_contract_id, status, start_at, end_at, retailer_id)
    VALUES ('beh-e002fu-camp-01', 'E002FU-CAMP', 'Test Campaign',
        'beh-e002fu-org-01', 'beh-e002fu-cont-01',
        'active', '2026-01-01T00:00:00Z', '2026-12-31T23:59:59Z', '{RET_A}')
    ON CONFLICT (id) DO NOTHING;
    """))
    # ── Device A (retailer A, active) + Device B (retailer B, active, NO manifest) ──
    asyncio.run(_run_sql(f"""
    INSERT INTO physical_devices (id, store_id, device_type_id, code,
        hardware_fingerprint, status, retailer_id)
    VALUES ('{DEVICE_A_ID}', '{STORE_A}', 'beh-e002fu-dt-01', 'E002FU-DEV-A',
        'e002fu-fp-a', 'active', '{RET_A}')
    ON CONFLICT (id) DO NOTHING;
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO physical_devices (id, store_id, device_type_id, code,
        hardware_fingerprint, status, retailer_id)
    VALUES ('{DEVICE_B_ID}', '{STORE_B}', 'beh-e002fu-dt-01', 'E002FU-DEV-B',
        'e002fu-fp-b', 'active', '{RET_B}')
    ON CONFLICT (id) DO NOTHING;
    """))
    # ── Manifest for Device A only ──
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    asyncio.run(_run_sql(f"""
    INSERT INTO delivery_manifests (id, manifest_id, campaign_id,
        physical_device_id, manifest_version, status,
        content_hash, generated_at, created_at, retailer_id)
    VALUES ('beh-e002fu-dm-01', 'sha256:beh-e002fu-ma-01', 'beh-e002fu-camp-01',
        '{DEVICE_A_ID}', 1, 'generated',
        'e002fu-hash-abc123', '{now}', '{now}', '{RET_A}')
    ON CONFLICT (id) DO NOTHING;
    """))
    yield
    for tbl in ("delivery_manifests", "campaigns", "advertiser_contracts",
                "advertiser_organizations", "physical_devices", "device_types",
                "channels", "stores", "clusters", "branches", "retailers"):
        asyncio.run(_run_sql(f"DELETE FROM {tbl} WHERE id LIKE 'beh-e002fu-%'"))


@pytest.mark.usefixtures("e002fu_setup")
class TestEDGE002FURealEndpoint:
    """Real device-gateway endpoint under behavioural PostgreSQL / NOBYPASSRLS."""

    @pytest.fixture(autouse=True)
    def setup(self, db_available):
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__), "..", "..", "apps", "device-gateway"))
        import main as app_mod
        self.app_mod = app_mod
        self.client = TestClient(app_mod.app)

    # ── Positive paths ────────────────────────────────────────────────────

    def test_device_a_200_manifest(self):
        """Device A (has manifest) → strict 200 with retailer_id + emergency."""
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(DEVICE_A_ID)),
        )
        assert resp.status_code == 200, \
            f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert data["device_id"] == DEVICE_A_ID
        assert data["retailer_id"] == RET_A
        assert "emergency" in data
        assert isinstance(data["emergency"], dict)
        assert "manifest_id" in data
        # Note: surfaces may be empty if no display surfaces exist for this
        # device — that's a valid manifest, not an error.

    def test_304_etag_strict(self):
        """First request → 200 + ETag. Second with If-None-Match → strict 304."""
        # First request: must be 200
        r1 = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(DEVICE_A_ID)),
        )
        assert r1.status_code == 200, \
            f"First request expected 200, got {r1.status_code}: {r1.text[:300]}"
        etag = r1.headers.get("ETag") or r1.headers.get("etag")
        assert etag is not None, "ETag header missing on 200 response"
        assert len(etag) > 0, "ETag header is empty"

        # Second request with If-None-Match: must be 304
        r2 = self.client.get(
            "/api/v1/device/manifest/latest",
            headers={**_auth(_token(DEVICE_A_ID)), "If-None-Match": etag},
        )
        assert r2.status_code == 304, \
            f"Second request expected 304, got {r2.status_code}: {r2.text[:300]}"

    # ── Cross-retailer tenant proof ───────────────────────────────────────

    def test_device_b_no_manifest_cross_retailer(self):
        """Device B (retailer B, no manifest) cannot see retailer A's manifest.

        Under NOBYPASSRLS, RLS filters delivery_manifests to retailer B rows only.
        Device B has NO manifest → 404. Device B MUST NOT see Device A's manifest.
        """
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(DEVICE_B_ID)),
        )
        assert resp.status_code == 404, \
            f"Device B expected 404 (no manifest in its retailer scope), got {resp.status_code}: {resp.text[:300]}"

    def test_device_b_token_cannot_access_device_a_endpoint(self):
        """Token for device B must not return device A's manifest data."""
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(DEVICE_B_ID)),
        )
        # Device B has no manifest → 404. But if it ever returned 200,
        # the body must NOT contain device A's data.
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("device_id") != DEVICE_A_ID, \
                "Device B token returned device A's manifest — cross-retailer leak!"
            assert data.get("retailer_id") != RET_A, \
                f"Device B token returned retailer A data: {data.get('retailer_id')}"
        else:
            assert resp.status_code == 404, \
                f"Expected 404, got {resp.status_code}: {resp.text[:300]}"

    # ── Client-supplied retailer_id/device_id ignored ─────────────────────

    def test_client_retailer_id_ignored(self):
        """Client sends ?retailer_id=X in query — server MUST ignore it.

        Device A always gets retailer A data regardless of what the client sends.
        """
        resp = self.client.get(
            "/api/v1/device/manifest/latest?retailer_id=evil-retailer",
            headers=_auth(_token(DEVICE_A_ID)),
        )
        assert resp.status_code == 200, \
            f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        # Server must return device A's real retailer, not the query param
        assert data["retailer_id"] == RET_A, \
            f"retailer_id from query leaked into response: {data['retailer_id']}"

    def test_client_device_id_in_body_ignored(self):
        """Client sends device_id in JSON body via POST-like query — server
        MUST use JWT sub, not the client-supplied value.

        (GET request, but we test that body params don't override JWT claims.)
        """
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers={**_auth(_token(DEVICE_A_ID)), "Content-Type": "application/json"},
            params={"device_id": "evil-device-id"},
        )
        # Should still work — server ignores the param
        assert resp.status_code == 200, \
            f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert data["device_id"] == DEVICE_A_ID, \
            f"device_id param leaked into response: {data['device_id']}"

    # ── Negative paths ────────────────────────────────────────────────────

    def test_missing_auth_401(self):
        resp = self.client.get("/api/v1/device/manifest/latest")
        assert resp.status_code == 401

    def test_invalid_token_401(self):
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers={"Authorization": "Bearer garbage"},
        )
        assert resp.status_code == 401

    def test_user_token_rejected_401(self):
        """A user JWT (auth_provider != 'device') must be rejected."""
        user_token = create_access_token("user-123", "local_advertiser")
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(user_token),
        )
        assert resp.status_code == 401

    def test_unknown_device_404(self):
        token = _token("00000000-0000-0000-0000-000000000099")
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(token),
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Direct DB RLS proof — app role with app.rmp_device_id bootstrap
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.usefixtures("e002fu_setup")
class TestEDGE002FUDirectDBRLS:
    """Direct DB RLS proof: app-role with app.rmp_device_id sees only own device.

    These tests bypass the HTTP layer and connect directly to PostgreSQL
    as the app role (retail_media_app, NOBYPASSRLS).  They prove that:

    - app.rmp_device_id = DEVICE_A → SELECT sees device A row only
    - app.rmp_device_id = '' → SELECT sees ZERO rows (no scope, no bootstrap)
    - app.rmp_device_id = DEVICE_A → device B row is NOT visible
    """

    @pytest.fixture(autouse=True)
    async def _app_connection(self, db_available):
        """Create a direct asyncpg connection as the app role (NOBYPASSRLS)."""
        import asyncpg
        import os

        app_db_url = os.environ.get("DATABASE_URL", "").strip()
        if not app_db_url:
            pytest.skip("DATABASE_URL not set")
        # asyncpg expects plain postgresql://, not postgresql+asyncpg://
        app_db_url = app_db_url.replace("postgresql+asyncpg://", "postgresql://")

        self._conn = await asyncpg.connect(app_db_url)
        yield
        await self._conn.close()

    @pytest.mark.asyncio
    async def test_bootstrap_sees_only_device_a(self):
        """app.rmp_device_id = A → sees device A row, NOT device B."""
        await self._conn.execute(
            "SELECT set_config('app.rmp_device_id', $1, true)", DEVICE_A_ID,
        )
        try:
            rows = await self._conn.fetch("SELECT id FROM physical_devices")
            ids = [r[0] for r in rows]
            assert DEVICE_A_ID in ids, \
                f"Device A ({DEVICE_A_ID}) not visible with bootstrap"
            assert DEVICE_B_ID not in ids, \
                f"Device B ({DEVICE_B_ID}) leaked via device A bootstrap"
            assert len(ids) == 1, \
                f"Expected exactly 1 device, got {len(ids)}: {ids}"
        finally:
            await self._conn.execute(
                "SELECT set_config('app.rmp_device_id', '', true)",
            )

    @pytest.mark.asyncio
    async def test_no_bootstrap_sees_zero_devices(self):
        """Without app.rmp_device_id, app role sees ZERO physical_devices
        (no scope, no bootstrap → RLS denies all)."""
        rows = await self._conn.fetch("SELECT id FROM physical_devices")
        ids = [r[0] for r in rows]
        assert ids == [], \
            f"Expected empty list (RLS deny all), got: {ids}"

    @pytest.mark.asyncio
    async def test_bootstrap_b_sees_device_b_not_a(self):
        """app.rmp_device_id = B → sees device B, not device A."""
        await self._conn.execute(
            "SELECT set_config('app.rmp_device_id', $1, true)", DEVICE_B_ID,
        )
        try:
            rows = await self._conn.fetch("SELECT id FROM physical_devices")
            ids = [r[0] for r in rows]
            assert DEVICE_B_ID in ids, \
                f"Device B ({DEVICE_B_ID}) not visible with bootstrap"
            assert DEVICE_A_ID not in ids, \
                f"Device A ({DEVICE_A_ID}) leaked via device B bootstrap"
        finally:
            await self._conn.execute(
                "SELECT set_config('app.rmp_device_id', '', true)",
            )
