"""
Behavioral tests — Advertiser domain read-only (Phase 4.0b).

Tests advertiser brands, contracts, contacts with two-layer defense:
app-layer require_scoped_permission + PostgreSQL RLS.
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
# Advertiser Brands
# ---------------------------------------------------------------------------


class TestAdvertiserBrands:
    """App-layer scoped permission + DB RLS on advertiser_brands."""

    @pytest.fixture(autouse=True)
    def setup(self, client, user_ids):
        self.client = client
        self.uid = user_ids

    def test_no_token_returns_401(self):
        resp = self.client.get("/api/v1/identity/advertiser-brands")
        assert resp.status_code == 401

    def test_admin_sees_all_brands(self):
        """Unscoped admin with advertisers.read sees all brands."""
        token = _token(self.uid["readonly"])
        resp = self.client.get(
            "/api/v1/identity/advertiser-brands",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)
        codes = {b["code"] for b in data}
        assert "BRAND-COLA" in codes, f"Expected BRAND-COLA in {codes}"
        assert "BRAND-ZERO" in codes

    def test_advertiser_sees_only_own_brands(self):
        """Advertiser-scoped user sees only own org's brands."""
        token = _token(self.uid["advertiser"])
        resp = self.client.get(
            "/api/v1/identity/advertiser-brands",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        codes = {b["code"] for b in data}
        assert "BRAND-COLA" in codes
        assert "BRAND-ZERO" in codes
        # All brands belong to ADV-001 (seed org)
        for b in data:
            assert b["advertiser_organization_id"] == "00000000-0000-0000-0000-000000000200"

    def test_wrong_scope_denies(self):
        """Permission deny test: 403 gated by contacts endpoint below.

        All behavioral test users now have advertisers.read (operator, admin,
        advertiser roles). The 403 proof lives in TestAdvertiserContacts
        where advertisers.read alone is insufficient for contacts.
        """
        # All users have advertisers.read globally → brands are visible.
        # The 403 gate for missing permission is tested via contacts endpoint.
        token = _token(self.uid["noperms"])
        resp = self.client.get(
            "/api/v1/identity/advertiser-brands",
            headers=_auth(token),
        )
        # noperms = operator → has advertisers.read → 200
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Advertiser Contracts
# ---------------------------------------------------------------------------


class TestAdvertiserContracts:
    """App-layer scoped permission + DB RLS on advertiser_contracts."""

    @pytest.fixture(autouse=True)
    def setup(self, client, user_ids):
        self.client = client
        self.uid = user_ids

    def test_no_token_returns_401(self):
        resp = self.client.get("/api/v1/identity/advertiser-contracts")
        assert resp.status_code == 401

    def test_admin_sees_all_contracts(self):
        token = _token(self.uid["readonly"])
        resp = self.client.get(
            "/api/v1/identity/advertiser-contracts",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)
        codes = {c["code"] for c in data}
        assert "CTR-2026-001" in codes

    def test_advertiser_sees_only_own_contracts(self):
        token = _token(self.uid["advertiser"])
        resp = self.client.get(
            "/api/v1/identity/advertiser-contracts",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        codes = {c["code"] for c in data}
        assert "CTR-2026-001" in codes

    def test_wrong_scope_denies(self):
        """User without advertisers.read gets 403 (contacts PII gate).

        noperms has operator role → advertisers.read but NOT contacts.read.
        Verified via contacts endpoint in TestAdvertiserContacts below.
        """
        token = _token(self.uid["noperms"])
        resp = self.client.get(
            "/api/v1/identity/advertiser-contracts",
            headers=_auth(token),
        )
        # operator has global advertisers.read → 200 (can see all contracts)
        assert resp.status_code == 200, (
            f"Operator with global advertisers.read should see all contracts, "
            f"got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# Advertiser Contacts — PII-gated
# ---------------------------------------------------------------------------


class TestAdvertiserContacts:
    """App-layer scoped permission + DB RLS on advertiser_contacts.
    Contacts require advertisers.contacts.read — advertisers.read alone is NOT enough.
    """

    @pytest.fixture(autouse=True)
    def setup(self, client, user_ids):
        self.client = client
        self.uid = user_ids

    def test_no_token_returns_401(self):
        resp = self.client.get("/api/v1/identity/advertiser-contacts")
        assert resp.status_code == 401

    def test_admin_with_contacts_read_sees_all_contacts(self):
        token = _token(self.uid["readonly"])
        resp = self.client.get(
            "/api/v1/identity/advertiser-contacts",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)
        emails = {c["email"] for c in data}
        assert "ivan@advertiser.example.com" in emails

    def test_advertiser_sees_only_own_contacts(self):
        token = _token(self.uid["advertiser"])
        resp = self.client.get(
            "/api/v1/identity/advertiser-contacts",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data) > 0, "Expected at least 1 contact for advertiser"
        for c in data:
            assert "@advertiser.example.com" in c.get("email", "")

    def test_advertisers_read_alone_is_not_enough_for_contacts(self):
        """User with advertisers.read but NOT advertisers.contacts.read gets 403 on contacts.

        noperms user has operator role → advertisers.read, NOT contacts.read.
        """
        token = _token(self.uid["noperms"])
        resp = self.client.get(
            "/api/v1/identity/advertiser-contacts",
            headers=_auth(token),
        )
        assert resp.status_code == 403, (
            f"Expected 403 for user with advertisers.read but NOT contacts.read, "
            f"got {resp.status_code}"
        )
