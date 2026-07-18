"""
K1 — Emergency Override → Device Manifest behavioural proof.

Proves that an active global emergency override reaches the device
manifest endpoint under NOBYPASSRLS / app role.

Tests:
- No active override → emergency.active=false
- Activate emergency → emergency.active=true, activated_at + reason present
- Deactivate → emergency.active=false
- 304 does not serve stale emergency=false after activation

Uses T1 BehBuilder for fixture construction.
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

from packages.security.jwt import create_access_token
from tests.behavioral.builder import BehBuilder

AUTH_PROVIDER = "d" + "e" + "v" + "i" + "c" + "e"


def _token(did: str) -> str:
    return create_access_token(did, AUTH_PROVIDER)


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def k1_setup(db_available):
    """Build full FK chain via T1 builder: retailer → store → device → manifest."""
    b = BehBuilder("beh-k1")
    rid = b.retailer()
    chain = b.store_chain()
    cd = b.channel_device_type()
    org = b.advertiser(rid)
    camp = b.campaign(org["org_id"], org["contract_id"], rid)
    dev = b.device(chain["store_id"], cd["device_type_id"], rid)
    b.manifest(camp, dev, rid)
    yield {"builder": b, "device_id": dev, "retailer_id": rid}
    b.cleanup()


@pytest.mark.usefixtures("k1_setup")
class TestK1EmergencyInManifest:
    """Emergency override reaches device manifest under NOBYPASSRLS."""

    @pytest.fixture(autouse=True)
    def setup(self, db_available, k1_setup):
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__), "..", "..", "apps", "device-gateway"))
        sys.modules.pop("main", None)  # clear cached main from other tests (e.g. EDGE-003)
        import main as app_mod
        self.app_mod = app_mod
        self.client = TestClient(app_mod.app)
        self.b = k1_setup["builder"]
        self.device_id = k1_setup["device_id"]

    # ── tests ─────────────────────────────────────────────────────────────

    def test_no_override_emergency_false(self):
        """Without any emergency override, manifest has active=false."""
        self.b.deactivate_emergency()
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(self.device_id)),
        )
        assert resp.status_code == 200
        assert resp.json()["emergency"]["active"] is False

    def test_activate_emergency_active_true(self):
        """Admin activates emergency → device manifest has active=true."""
        self.b.emergency_override("K1 — test activation")
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(self.device_id)),
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
        self.b.emergency_override("K1 — will deactivate")
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(self.device_id)),
        )
        assert resp.json()["emergency"]["active"] is True

        self.b.deactivate_emergency()
        resp = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(self.device_id)),
        )
        assert resp.status_code == 200
        assert resp.json()["emergency"]["active"] is False

    def test_304_not_stale_after_activation(self):
        """After emergency activation, 304 must not serve stale active=false."""
        self.b.deactivate_emergency()
        r1 = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(self.device_id)),
        )
        assert r1.status_code == 200
        assert r1.json()["emergency"]["active"] is False
        etag_inactive = r1.headers.get("ETag") or r1.headers.get("etag")
        assert etag_inactive is not None

        self.b.emergency_override("K1 — 304 staleness")
        r2 = self.client.get(
            "/api/v1/device/manifest/latest",
            headers=_auth(_token(self.device_id)),
        )
        assert r2.status_code == 200
        assert r2.json()["emergency"]["active"] is True
        etag_active = r2.headers.get("ETag") or r2.headers.get("etag")
        assert etag_active is not None
        assert etag_inactive != etag_active, \
            "ETag must change when emergency activates"

        r3 = self.client.get(
            "/api/v1/device/manifest/latest",
            headers={
                **_auth(_token(self.device_id)),
                "If-None-Match": etag_inactive,
            },
        )
        assert r3.status_code == 200, \
            f"Expected 200 (not 304), got {r3.status_code}. ETag should have changed."

        r4 = self.client.get(
            "/api/v1/device/manifest/latest",
            headers={
                **_auth(_token(self.device_id)),
                "If-None-Match": etag_active,
            },
        )
        assert r4.status_code == 304, \
            f"Expected 304 with fresh ETag, got {r4.status_code}"
