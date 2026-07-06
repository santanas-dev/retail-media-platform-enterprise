"""
Behavioral HTTP tests — PoP Reporting Scope (Phase 4.3d P1 fix).

Tests campaign ownership check on PoP reporting endpoints:
- scoped advertiser can read own campaign PoP report
- scoped advertiser cannot read foreign campaign PoP report → 404
- admin/global can read any campaign report
- no token → 401
- user without campaigns.read → 403

Requires: RUN_BEHAVIORAL_TESTS=1, pop_fixtures seeded.
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
# Known campaign IDs
# ---------------------------------------------------------------------------
# 00000000-0000-0000-0000-000000000220 — belongs to ADV-001, visible to advertiser
# beh-pop-camp-00000000000000001 — belongs to BEH-POP-ADV, NOT visible to advertiser
OWN_CAMPAIGN = "00000000-0000-0000-0000-000000000220"
FOREIGN_CAMPAIGN = "beh-pop-camp-00000000000000001"  # seeded by pop_fixtures


_ENDPOINTS = [
    "/api/v1/identity/campaigns/{cid}/pop/summary",
    "/api/v1/identity/campaigns/{cid}/pop/by-day",
    "/api/v1/identity/campaigns/{cid}/pop/by-surface",
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPopReportingScope:
    """Campaign ownership guard on PoP reporting endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, client, user_ids, pop_fixtures):
        self.client = client
        self.uid = user_ids
        self.pf = pop_fixtures  # ensures PoP campaign + data exist

    def test_no_token_returns_401(self):
        for tmpl in _ENDPOINTS:
            url = tmpl.format(cid=OWN_CAMPAIGN)
            resp = self.client.get(url)
            assert resp.status_code == 401, f"{url}: expected 401, got {resp.status_code}"

    def test_no_permission_returns_403(self):
        """Disabled user has no roles → no campaigns.read → 403."""
        token = _token(self.uid["disabled"])
        for tmpl in _ENDPOINTS:
            url = tmpl.format(cid=OWN_CAMPAIGN)
            resp = self.client.get(url, headers=_auth(token))
            assert resp.status_code == 403, f"{url}: expected 403, got {resp.status_code}: {resp.text}"

    def test_advertiser_can_read_own_campaign(self):
        """Scoped advertiser can read PoP for their own campaign."""
        token = _token(self.uid["advertiser"])
        for tmpl in _ENDPOINTS:
            url = tmpl.format(cid=OWN_CAMPAIGN)
            resp = self.client.get(url, headers=_auth(token))
            assert resp.status_code == 200, f"{url}: expected 200, got {resp.status_code}: {resp.text}"

    def test_advertiser_cannot_read_foreign_campaign(self):
        """Scoped advertiser cannot read PoP for a campaign from another org.
        get_campaign returns None (RLS-filtered) → 404."""
        token = _token(self.uid["advertiser"])
        for tmpl in _ENDPOINTS:
            url = tmpl.format(cid=FOREIGN_CAMPAIGN)
            resp = self.client.get(url, headers=_auth(token))
            assert resp.status_code == 404, f"{url}: expected 404, got {resp.status_code}: {resp.text}"

    def test_admin_can_read_foreign_campaign(self):
        """Unscoped admin with campaigns.read can read any campaign PoP."""
        token = _token(self.uid["readonly"])  # system_admin role
        for tmpl in _ENDPOINTS:
            url = tmpl.format(cid=FOREIGN_CAMPAIGN)
            resp = self.client.get(url, headers=_auth(token))
            assert resp.status_code == 200, f"{url}: expected 200, got {resp.status_code}: {resp.text}"
