"""
K1 — Emergency Override → Device Manifest behavioural proof.

Proves that an active global emergency override reaches the device
manifest endpoint under NOBYPASSRLS / app role.

Tests:
- No active override → emergency.active=false
- Activate emergency → emergency.active=true, activated_at + reason present
- Deactivate → emergency.active=false
- 304 does not serve stale emergency=false after activation
"""

import asyncio
import os
import sys

import pytest
from fastapi.testclient import TestClient

from tests.behavioral.conftest import _run_sql

RET_A = "beh-k1-ret-a-000000000000001"
DEVICE_A_ID = "beh-k1-dev-a-000000000000001"
STORE_A = "beh-k1-store-a-0000000000001"

_AUTH_PROV = "device"

from packages.security.jwt import create_access_token


def _token(device_id: str) -> str:
    return create_access_token(device_id, _AUTH_PROV)


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def k1_setup(db_available):
    """Retailer, store, device, manifest — same pattern as EDGE-002-FU."""
    asyncio.run(_run_sql(f"""
    INSERT INTO retailers (id, code, legal_name, display_name, status)
    VALUES ('{RET_A}', 'K1-RET-A', 'K1 Retailer', 'K1', 'active')
    ON CONFLICT (id) DO NOTHING;
    """))
    asyncio.run(_run_sql("""
    INSERT INTO branches (id, code, name, timezone, is_active)
    VALUES ('beh-k1-br-01', 'K1-BR', 'K1 Branch', 'Europe/Moscow', true)
    ON CONFLICT (code) DO NOTHING;
    """))
    asyncio.run(_run_sql("""
    INSERT INTO clusters (id, branch_id, code, name, is_active)
    VALUES ('beh-k1-cl-01', 'beh-k1-br-01', 'K1-CL', 'K1 Cluster', true)
    ON CONFLICT (code) DO NOTHING;
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO stores (id, cluster_id, code, name, is_active)
    VALUES ('{STORE_A}', 'beh-k1-cl-01', 'K1-ST-A', 'K1 Store', true)
    ON CONFLICT (code) DO NOTHING;
    """))
    asyncio.run(_run_sql("""
    INSERT INTO channels (id, code, name, is_active)
    VALUES ('beh-k1-ch-01', 'K1-CH', 'K1 Channel', true)
    ON CONFLICT (code) DO NOTHING;
    """))
    asyncio.run(_run_sql("""
    INSERT INTO device_types (id, channel_id, code, name, player_runtime)
    VALUES ('beh-k1-dt-01', 'beh-k1-ch-01', 'K1-KSO', 'K1 KSO', 'chromium')
    ON CONFLICT (code) DO NOTHING;
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO advertiser_organizations (id, code, legal_name, display_name, status, retailer_id)
    VALUES ('beh-k1-org-01', 'K1-ORG', 'K1 Org', 'K1 Org', 'active', '{RET_A}')
    ON CONFLICT (id) DO NOTHING;
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO advertiser_contracts (id, advertiser_organization_id, code, name, status, retailer_id)
    VALUES ('beh-k1-cont-01', 'beh-k1-org-01', 'K1-CONT', 'K1 Contract', 'active', '{RET_A}')
    ON CONFLICT (id) DO NOTHING;
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO campaigns (id, code, name, advertiser_organization_id,
        advertiser_contract_id, status, start_at, end_at, retailer_id)
    VALUES ('beh-k1-camp-01', 'K1-CAMP', 'K1 Campaign',
        'beh-k1-org-01', 'beh-k1-cont-01',
        'active', '2026-01-01T00:00:00Z', '2026-12-31T23:59:59Z', '{RET_A}')
    ON CONFLICT (id) DO NOTHING;
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO physical_devices (id, store_id, device_type_id, code,
        hardware_fingerprint, status, retailer_id)
    VALUES ('{DEVICE_A_ID}', '{STORE_A}', 'beh-k1-dt-01', 'K1-DEV-A',
        'k1-fp-a', 'active', '{RET_A}')
    ON CONFLICT (id) DO NOTHING;
    """))
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    asyncio.run(_run_sql(f"""
    INSERT INTO delivery_manifests (id, manifest_id, campaign_id,
        physical_device_id, manifest_version, status,
        content_hash, generated_at, created_at, retailer_id)
    VALUES ('beh-k1-dm-01', 'sha256:beh-k1-ma-01', 'beh-k1-camp-01',
        '{DEVICE_A_ID}', 1, 'generated',
        'k1-hash-abc123', '{now}', '{now}', '{RET_A}')
    ON CONFLICT (id) DO NOTHING;
    """))
    yield
    for tbl in ("delivery_manifests", "campaigns", "advertiser_contracts",
                "advertiser_organizations", "physical_devices", "device_types",
                "channels", "stores", "clusters", "branches", "retailers",
                "emergency_overrides"):
        asyncio.run(_run_sql(f"DELETE FROM {tbl} WHERE id LIKE 'beh-k1-%'"))


@pytest.mark.usefixtures("k1_setup")
class TestK1EmergencyInManifest:
    """Emergency override reaches device manifest under NOBYPASSRLS."""

    @pytest.fixture(autouse=True)
    def setup(self, db_available):
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__), "..", "..", "apps", "device-gateway"))
        import main as app_mod
        self.app_mod = app_mod
        self.client = TestClient(app_mod.app)

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _activate_emergency(reason: str = "K1 test emergency"):
        """Insert an active emergency override via owner role."""
        asyncio.run(_run_sql(f"""
        DELETE FROM emergency_overrides WHERE id LIKE 'beh-k1-%';
        INSERT INTO emergency_overrides (id, level, active, reason, activated_at)
        VALUES ('beh-k1-em-01', 'global', true, '{reason}', NOW())
        ON CONFLICT (id) DO NOTHING;
        """))

    @staticmethod
    def _deactivate_emergency():
        asyncio.run(_run_sql("""
        DELETE FROM emergency_overrides WHERE id LIKE 'beh-k1-%';
        """))

    # ── tests ─────────────────────────────────────────────────────────────

    def test_no_override_emergency_false(self):
        """Without any emergency override, manifest has active=false."""
        self._deactivate_emergency()
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(DEVICE_A_ID)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["emergency"]["active"] is False

    def test_activate_emergency_active_true(self):
        """Admin activates emergency → device manifest has active=true."""
        self._activate_emergency("K1 — test activation")
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(DEVICE_A_ID)),
        )
        assert resp.status_code == 200, \
            f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert data["emergency"]["active"] is True, \
            f"emergency.active should be True, got {data['emergency']}"
        assert data["emergency"]["reason"] == "K1 — test activation"
        assert data["emergency"]["activated_at"] is not None

    def test_deactivate_returns_to_false(self):
        """Deactivate → manifest returns to active=false."""
        self._activate_emergency("K1 — will deactivate")
        # Verify activated
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(DEVICE_A_ID)),
        )
        assert resp.json()["emergency"]["active"] is True

        # Deactivate
        self._deactivate_emergency()
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(DEVICE_A_ID)),
        )
        assert resp.status_code == 200
        assert resp.json()["emergency"]["active"] is False

    def test_304_not_stale_after_activation(self):
        """After emergency activation, 304 must not serve stale active=false."""
        # Start: no emergency
        self._deactivate_emergency()
        r1 = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(DEVICE_A_ID)),
        )
        assert r1.status_code == 200
        assert r1.json()["emergency"]["active"] is False
        etag_inactive = r1.headers.get("ETag") or r1.headers.get("etag")
        assert etag_inactive is not None

        # Activate emergency — ETag should change
        self._activate_emergency("K1 — 304 staleness")
        r2 = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(DEVICE_A_ID)),
        )
        assert r2.status_code == 200
        assert r2.json()["emergency"]["active"] is True
        etag_active = r2.headers.get("ETag") or r2.headers.get("etag")
        assert etag_active is not None
        assert etag_inactive != etag_active, \
            "ETag must change when emergency activates"

        # Send the OLD (inactive) ETag — must NOT get 304
        r3 = self.client.get(
            "/api/v1/device/manifest/latest",
            headers={
                **_auth(_token(DEVICE_A_ID)),
                "If-None-Match": etag_inactive,
            },
        )
        assert r3.status_code == 200, \
            f"Expected 200 (not 304), got {r3.status_code}. ETag should have changed."

        # Send the NEW (active) ETag — should get 304
        r4 = self.client.get(
            "/api/v1/device/manifest/latest",
            headers={
                **_auth(_token(DEVICE_A_ID)),
                "If-None-Match": etag_active,
            },
        )
        assert r4.status_code == 304, \
            f"Expected 304 with fresh ETag, got {r4.status_code}"
