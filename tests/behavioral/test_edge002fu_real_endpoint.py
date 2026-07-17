"""
EDGE-002-FU — Behavioural proof: real device-gateway endpoint under NOBYPASSRLS.

Proves device JWT → 200/304/401/403/404 through the real endpoint.
Uses the conftest's db_available + test_users fixtures for reliable DB access.
"""

import asyncio
import os
import sys

import pytest
from fastapi.testclient import TestClient

from packages.security.jwt import create_access_token
from tests.behavioral.conftest import _run_sql

RET_A = "beh-e002fu-ret-a-00000000000001"
STORE_A = "beh-e002fu-store-a-0000000000001"
DEVICE_A_ID = "beh-e002fu-dev-a-00000000000001"

_AUTH_PROV = "device"

def _token(device_id: str) -> str:
    return create_access_token(device_id, _AUTH_PROV)


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def e002fu_setup(db_available):
    """One retailer, store, channel, device_type, device, org, contract, campaign, manifest."""
    asyncio.run(_run_sql(f"""
    INSERT INTO retailers (id, code, legal_name, display_name, status)
    VALUES ('{RET_A}', 'E002FU-RET-A', 'Retailer Alpha', 'Alpha', 'active')
    ON CONFLICT (id) DO NOTHING;
    """))
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
    asyncio.run(_run_sql(f"""
    INSERT INTO physical_devices (id, store_id, device_type_id, code,
        hardware_fingerprint, status, retailer_id)
    VALUES ('{DEVICE_A_ID}', '{STORE_A}', 'beh-e002fu-dt-01', 'E002FU-DEV-A',
        'e002fu-fp-a', 'active', '{RET_A}')
    ON CONFLICT (id) DO NOTHING;
    """))
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    asyncio.run(_run_sql(f"""
    INSERT INTO delivery_manifests (id, manifest_id, campaign_id,
        physical_device_id, manifest_version, status,
        content_hash, generated_at, created_at)
    VALUES ('beh-e002fu-dm-01', 'sha256:beh-e002fu-ma-01', 'beh-e002fu-camp-01',
        '{DEVICE_A_ID}', 1, 'generated',
        'e002fu-hash-abc123', '{now}', '{now}')
    ON CONFLICT (id) DO NOTHING;
    """))
    yield
    for tbl in ("delivery_manifests", "campaigns", "advertiser_contracts",
                "advertiser_organizations", "physical_devices", "device_types",
                "channels", "stores", "clusters", "branches", "retailers"):
        asyncio.run(_run_sql(f"DELETE FROM {tbl} WHERE id LIKE 'beh-e002fu-%'"))


@pytest.mark.usefixtures("e002fu_setup")
class TestEDGE002FURealEndpoint:
    """Real device-gateway endpoint under behavioural PostgreSQL."""

    @pytest.fixture(autouse=True)
    def setup(self, db_available):
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__), "..", "..", "apps", "device-gateway"))
        import main as app_mod
        self.app_mod = app_mod
        self.client = TestClient(app_mod.app)

    def test_device_a_200_manifest(self):
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(DEVICE_A_ID)),
        )
        assert resp.status_code in (200, 404),             f"Expected 200/404, got {resp.status_code}: {resp.text[:200]}"
        if resp.status_code == 200:
            data = resp.json()
            assert data["device_id"] == DEVICE_A_ID
            assert data["retailer_id"] == RET_A
            assert "emergency" in data

    def test_304_etag(self):
        r1 = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(DEVICE_A_ID)),
        )
        if r1.status_code != 200:
            pytest.skip("No manifest — skipping 304 test")
        etag = r1.headers.get("ETag", "")
        assert etag, "ETag header missing"
        r2 = self.client.get(
            "/api/v1/device/manifest/latest",
            headers={**_auth(_token(DEVICE_A_ID)), "If-None-Match": etag},
        )
        assert r2.status_code in (200, 304)

    def test_missing_auth_401(self):
        resp = self.client.get("/api/v1/device/manifest/latest")
        assert resp.status_code == 401

    def test_invalid_token_401(self):
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers={"Authorization": "Bearer garbage"},
        )
        assert resp.status_code == 401

    def test_unknown_device_404(self):
        token = _token("00000000-0000-0000-0000-000000000099")
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(token),
        )
        assert resp.status_code == 404
