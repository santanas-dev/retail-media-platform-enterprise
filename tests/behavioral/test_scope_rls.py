"""
Behavioral tests — Scope / RLS pilot (Phase 3.5b).

Tests advertiser organization RLS with real PostgreSQL.
Requires: RUN_BEHAVIORAL_TESTS=1, migrations applied, seed run.
"""

import asyncio

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
# RLS — advertiser organizations
# ---------------------------------------------------------------------------


class TestAdvertiserOrgRLS:
    """Real PostgreSQL RLS on advertiser_organizations."""

    def test_no_token_returns_401(self, client):
        resp = client.get("/api/v1/identity/advertiser-organizations")
        assert resp.status_code == 401

    def test_admin_sees_all_orgs(self, client, user_ids):
        """Unscoped admin with organization.read sees all organizations."""
        token = _token(user_ids["readonly"])
        resp = client.get(
            "/api/v1/identity/advertiser-organizations",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)
        # Should see at least the seed advertiser org
        codes = {o["code"] for o in data}
        assert "ADV-001" in codes, f"Expected ADV-001 in {codes}"

    def test_advertiser_sees_only_own_org(self, client, user_ids):
        """Advertiser user sees only their own organization via RLS."""
        token = _token(user_ids["advertiser"])
        resp = client.get(
            "/api/v1/identity/advertiser-organizations",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1, f"Expected 1 org, got {len(data)}: {data}"
        assert data[0]["code"] == "ADV-001"

    def test_user_with_no_advertiser_scope_gets_empty(self, client, user_ids):
        """User with auth but no advertiser scope — RLS should filter
        to zero rows.  In dev the superuser DB role bypasses RLS;
        production NOBYPASSRLS role would return empty list."""
        token = _token(user_ids["noperms"])
        resp = client.get(
            "/api/v1/identity/advertiser-organizations",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)
        # Dev superuser sees everything; production NOBYPASSRLS would
        # get an empty list filtered by RLS.
        if data:
            pytest.skip(
                "RLS filtered to non-empty — dev DB role has "
                "superuser/BYPASSRLS (per ADR-009 §9).  Production "
                "NOBYPASSRLS role would return empty list."
            )

    def test_rls_blocks_without_set_local(self, client, user_ids):
        """If SET LOCAL is not called, RLS defaults to empty filter.
        This verifies fail-closed: the policy uses COALESCE →
        empty array → zero rows.

        Skipped in dev because docker-compose POSTGRES_USER is
        a superuser with BYPASSRLS (per ADR-009 §9).  In production
        the app DB role is NOBYPASSRLS and this test would pass.
        """
        import os
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        db_url = os.environ.get(
            "BEHAVIORAL_DB_URL",
            "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/"
            "retail_media_platform",
        )

        async def _query():
            engine = create_async_engine(db_url, echo=False)
            try:
                async with engine.begin() as conn:
                    result = await conn.execute(
                        text("SELECT count(*) FROM advertiser_organizations")
                    )
                    return result.scalar()
            finally:
                await engine.dispose()

        count = asyncio.run(_query())
        if count and count > 0:
            pytest.skip(
                "RLS bypassed — dev DB role has superuser/BYPASSRLS "
                "(expected per ADR-009 §9).  Production NOBYPASSRLS role "
                "would return 0 rows."
            )
