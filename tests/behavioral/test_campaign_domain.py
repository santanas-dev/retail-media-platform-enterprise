"""
Behavioral tests — Campaign domain read-only (Phase 4.1b).

Tests campaigns, flights, creatives, placements, approvals, status history
with two-layer defense: app-layer require_scoped_permission + PostgreSQL RLS.
Requires: RUN_BEHAVIORAL_TESTS=1, migrations applied, seed run.
"""

import pytest
from fastapi.testclient import TestClient

from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(app, db_available, test_users):
    reset_security_config()
    return TestClient(app)


@pytest.fixture
def user_ids(test_users):
    return test_users


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _token(sub):
    return create_access_token(sub, "local_advertiser")


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------


class TestCampaigns:
    """App-layer scoped permission + DB RLS on campaigns."""

    @pytest.fixture(autouse=True)
    def setup(self, client, user_ids):
        self.client = client
        self.uid = user_ids

    def test_no_token_returns_401(self):
        resp = self.client.get("/api/v1/identity/campaigns")
        assert resp.status_code == 401

    def test_admin_sees_all_campaigns(self):
        """Unscoped admin with campaigns.read sees all campaigns."""
        token = _token(self.uid["readonly"])
        resp = self.client.get(
            "/api/v1/identity/campaigns",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)
        codes = {c["code"] for c in data}
        assert "CAMP-2026-001" in codes, f"Expected CAMP-2026-001 in {codes}"

    def test_advertiser_sees_only_own_campaigns(self):
        """Advertiser-scoped user sees only own org's campaigns."""
        token = _token(self.uid["advertiser"])
        resp = self.client.get(
            "/api/v1/identity/campaigns",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        codes = {c["code"] for c in data}
        assert "CAMP-2026-001" in codes
        for c in data:
            assert c["advertiser_organization_id"] == "00000000-0000-0000-0000-000000000200"

    def test_global_read_sees_all(self):
        """System admin with campaigns.read sees all campaigns."""
        token = _token(self.uid["readonly"])
        resp = self.client.get(
            "/api/v1/identity/campaigns",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data) >= 1

    def test_no_permission_returns_403(self):
        """User without campaigns.read gets 403.

        disabled user has no roles → no permissions at all.
        """
        token = _token(self.uid["disabled"])
        resp = self.client.get(
            "/api/v1/identity/campaigns",
            headers=_auth(token),
        )
        assert resp.status_code == 403, (
            f"Expected 403 for user without campaigns.read, got {resp.status_code}"
        )

    def test_campaign_response_has_no_pii(self):
        """Campaign response must not expose contact PII."""
        token = _token(self.uid["readonly"])
        resp = self.client.get(
            "/api/v1/identity/campaigns",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        for campaign in data:
            assert "email" not in campaign, f"email leaked in campaign: {campaign}"
            assert "phone" not in campaign, f"phone leaked in campaign: {campaign}"
            assert "contact_name" not in campaign, f"contact_name leaked in campaign: {campaign}"


# ---------------------------------------------------------------------------
# Campaign Flights
# ---------------------------------------------------------------------------


class TestCampaignFlights:
    """App-layer scoped permission + DB RLS on campaign_flights."""

    @pytest.fixture(autouse=True)
    def setup(self, client, user_ids):
        self.client = client
        self.uid = user_ids

    def test_no_token_returns_401(self):
        resp = self.client.get("/api/v1/identity/campaign-flights")
        assert resp.status_code == 401

    def test_admin_sees_all_flights(self):
        token = _token(self.uid["readonly"])
        resp = self.client.get(
            "/api/v1/identity/campaign-flights",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)
        names = {f["name"] for f in data if f.get("name")}
        assert "Основной пролёт" in names, f"Expected flight name in {names}"

    def test_advertiser_sees_own_flights(self):
        token = _token(self.uid["advertiser"])
        resp = self.client.get(
            "/api/v1/identity/campaign-flights",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # Advertiser sees flights for their campaigns only (via RLS)
        for f in data:
            assert f["campaign_id"] == "00000000-0000-0000-0000-000000000220"

    def test_no_permission_returns_403(self):
        token = _token(self.uid["disabled"])
        resp = self.client.get(
            "/api/v1/identity/campaign-flights",
            headers=_auth(token),
        )
        assert resp.status_code == 403, (
            f"Expected 403 for user without campaigns.read, got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# Creative Assets
# ---------------------------------------------------------------------------


class TestCreativeAssets:
    """Creative assets endpoint — metadata only, no storage secrets."""

    @pytest.fixture(autouse=True)
    def setup(self, client, user_ids):
        self.client = client
        self.uid = user_ids

    def test_no_token_returns_401(self):
        resp = self.client.get("/api/v1/identity/creative-assets")
        assert resp.status_code == 401

    def test_admin_sees_creative_assets(self):
        token = _token(self.uid["readonly"])
        resp = self.client.get(
            "/api/v1/identity/creative-assets",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)
        codes = {a["code"] for a in data}
        assert "CREATIVE-001" in codes

    def test_no_storage_secrets_exposed(self):
        """CreativeAssetOut must NOT expose storage_bucket, storage_key,
        or presigned URLs."""
        token = _token(self.uid["readonly"])
        resp = self.client.get(
            "/api/v1/identity/creative-assets",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        for asset in data:
            assert "storage_bucket" not in asset, (
                f"storage_bucket leaked in creative asset: {asset}"
            )
            assert "storage_key" not in asset, (
                f"storage_key leaked in creative asset: {asset}"
            )
            assert "presigned_url" not in asset, (
                f"presigned_url leaked in creative asset: {asset}"
            )

    def test_advertiser_sees_own_assets(self):
        token = _token(self.uid["advertiser"])
        resp = self.client.get(
            "/api/v1/identity/creative-assets",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        for a in data:
            assert a["advertiser_organization_id"] == "00000000-0000-0000-0000-000000000200"

    def test_no_permission_returns_403(self):
        """User without creatives.read gets 403.

        disabled user has no roles → no permissions at all.
        """
        token = _token(self.uid["disabled"])
        resp = self.client.get(
            "/api/v1/identity/creative-assets",
            headers=_auth(token),
        )
        assert resp.status_code == 403, (
            f"Expected 403 for user without creatives.read, got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# Campaign Placements
# ---------------------------------------------------------------------------


class TestCampaignPlacements:
    """App-layer scoped permission + DB RLS on campaign_placements."""

    @pytest.fixture(autouse=True)
    def setup(self, client, user_ids):
        self.client = client
        self.uid = user_ids

    def test_no_token_returns_401(self):
        resp = self.client.get("/api/v1/identity/campaign-placements")
        assert resp.status_code == 401

    def test_admin_sees_placements(self):
        token = _token(self.uid["readonly"])
        resp = self.client.get(
            "/api/v1/identity/campaign-placements",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_advertiser_sees_own_placements(self):
        token = _token(self.uid["advertiser"])
        resp = self.client.get(
            "/api/v1/identity/campaign-placements",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        for p in data:
            assert p["campaign_id"] == "00000000-0000-0000-0000-000000000220"

    def test_no_permission_returns_403(self):
        token = _token(self.uid["disabled"])
        resp = self.client.get(
            "/api/v1/identity/campaign-placements",
            headers=_auth(token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Campaign Approvals
# ---------------------------------------------------------------------------


class TestCampaignApprovals:
    """Approvals endpoint — read-only with campaigns.read."""

    @pytest.fixture(autouse=True)
    def setup(self, client, user_ids):
        self.client = client
        self.uid = user_ids

    def test_no_token_returns_401(self):
        resp = self.client.get("/api/v1/identity/campaign-approvals")
        assert resp.status_code == 401

    def test_admin_sees_approvals(self):
        """Admin with campaigns.read can list approval records."""
        token = _token(self.uid["readonly"])
        resp = self.client.get(
            "/api/v1/identity/campaign-approvals",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)
        # Seed no longer has approval row — expect empty list
        # (approvals table exists, RLS allows admin to see empty set)

    def test_no_permission_returns_403(self):
        token = _token(self.uid["disabled"])
        resp = self.client.get(
            "/api/v1/identity/campaign-approvals",
            headers=_auth(token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Campaign Status History
# ---------------------------------------------------------------------------


class TestCampaignStatusHistory:
    """Status history endpoint — scoped + RLS."""

    @pytest.fixture(autouse=True)
    def setup(self, client, user_ids):
        self.client = client
        self.uid = user_ids

    def test_no_token_returns_401(self):
        resp = self.client.get("/api/v1/identity/campaign-status-history")
        assert resp.status_code == 401

    def test_admin_sees_history(self):
        token = _token(self.uid["readonly"])
        resp = self.client.get(
            "/api/v1/identity/campaign-status-history",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)
        # Seed has one status history row (null → draft)

    def test_advertiser_sees_own_history(self):
        token = _token(self.uid["advertiser"])
        resp = self.client.get(
            "/api/v1/identity/campaign-status-history",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        for h in data:
            assert h["campaign_id"] == "00000000-0000-0000-0000-000000000220"

    def test_no_permission_returns_403(self):
        token = _token(self.uid["disabled"])
        resp = self.client.get(
            "/api/v1/identity/campaign-status-history",
            headers=_auth(token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Campaign Creatives
# ---------------------------------------------------------------------------


class TestCampaignCreatives:
    """Campaign-creative links — scoped + RLS."""

    @pytest.fixture(autouse=True)
    def setup(self, client, user_ids):
        self.client = client
        self.uid = user_ids

    def test_no_token_returns_401(self):
        resp = self.client.get("/api/v1/identity/campaign-creatives")
        assert resp.status_code == 401

    def test_admin_sees_creatives(self):
        token = _token(self.uid["readonly"])
        resp = self.client.get(
            "/api/v1/identity/campaign-creatives",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)

    def test_advertiser_sees_own_creatives(self):
        token = _token(self.uid["advertiser"])
        resp = self.client.get(
            "/api/v1/identity/campaign-creatives",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        for c in data:
            assert c["campaign_id"] == "00000000-0000-0000-0000-000000000220"

    def test_no_permission_returns_403(self):
        token = _token(self.uid["disabled"])
        resp = self.client.get(
            "/api/v1/identity/campaign-creatives",
            headers=_auth(token),
        )
        assert resp.status_code == 403
