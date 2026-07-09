"""
Behavioral HTTP tests — PoP Reporting Scope (Phase 4.3d P1 fix).

Tests campaign ownership check on PoP reporting endpoints:
- scoped advertiser can read own campaign PoP report
- scoped advertiser cannot read foreign campaign PoP report → 404
- admin/global can read any campaign report
- no token → 401
- user without campaigns.read → 403

Requires: RUN_BEHAVIORAL_TESTS=1, pop_fixtures seeded.

Uses TestClient for single-request tests (no event-loop conflict).
Multi-request tests (advertiser_can_read_own_campaign et al) loop over
endpoints with a fresh TestClient per endpoint to avoid the Starlette
BaseHTTPMiddleware event-loop conflict.
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _token(sub):
    return create_access_token(sub, "local_advertiser")


KNOWN_CAMPAIGNS = {
    "own":     "00000000-0000-0000-0000-000000000220",
    "foreign": "beh-pop-camp-00000000000000001",
}

_ENDPOINTS = [
    "/api/v1/identity/campaigns/{cid}/pop/summary",
    "/api/v1/identity/campaigns/{cid}/pop/by-day",
    "/api/v1/identity/campaigns/{cid}/pop/by-surface",
]


def _new_client(app):
    """Create a fresh TestClient *per request* to avoid the Starlette
    BaseHTTPMiddleware event-loop conflict on sequential calls."""
    reset_security_config()
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPopReportingScope:
    """Campaign ownership guard on PoP reporting endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, app, db_available, test_users, pop_fixtures):
        self.app = app
        self.uid = test_users

    def test_no_token_returns_401(self):
        for tmpl in _ENDPOINTS:
            url = tmpl.format(cid=KNOWN_CAMPAIGNS["own"])
            client = _new_client(self.app)
            resp = client.get(url)
            assert resp.status_code == 401, (
                f"{url}: expected 401, got {resp.status_code}"
            )

    def test_no_permission_returns_403(self):
        token = _token(self.uid["disabled"])
        for tmpl in _ENDPOINTS:
            url = tmpl.format(cid=KNOWN_CAMPAIGNS["own"])
            client = _new_client(self.app)
            resp = client.get(url, headers=_auth(token))
            assert resp.status_code == 403, (
                f"{url}: expected 403, got {resp.status_code}: {resp.text}"
            )

    def test_advertiser_can_read_own_campaign(self):
        token = _token(self.uid["advertiser"])
        for tmpl in _ENDPOINTS:
            url = tmpl.format(cid=KNOWN_CAMPAIGNS["own"])
            client = _new_client(self.app)
            resp = client.get(url, headers=_auth(token))
            assert resp.status_code == 200, (
                f"{url}: expected 200, got {resp.status_code}: {resp.text}"
            )

    def test_advertiser_cannot_read_foreign_campaign(self):
        token = _token(self.uid["advertiser"])
        for tmpl in _ENDPOINTS:
            url = tmpl.format(cid=KNOWN_CAMPAIGNS["foreign"])
            client = _new_client(self.app)
            resp = client.get(url, headers=_auth(token))
            assert resp.status_code == 404, (
                f"{url}: expected 404, got {resp.status_code}: {resp.text}"
            )

    def test_admin_can_read_foreign_campaign(self):
        token = _token(self.uid["readonly"])
        for tmpl in _ENDPOINTS:
            url = tmpl.format(cid=KNOWN_CAMPAIGNS["foreign"])
            client = _new_client(self.app)
            resp = client.get(url, headers=_auth(token))
            assert resp.status_code == 200, (
                f"{url}: expected 200, got {resp.status_code}: {resp.text}"
            )
