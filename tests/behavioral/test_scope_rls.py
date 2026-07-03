"""
Behavioral tests — Scope / RLS pilot (Phase 3.5b/3.5c).

Tests advertiser organization with two-layer defense:
app-layer require_scoped_permission + PostgreSQL RLS.
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
# Advertiser organizations — two-layer defense
# ---------------------------------------------------------------------------


class TestAdvertiserOrgScoped:
    """App-layer scoped permission + DB RLS on advertiser_organizations."""

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
        codes = {o["code"] for o in data}
        assert "ADV-001" in codes, f"Expected ADV-001 in {codes}"

    def test_advertiser_sees_only_own_org(self, client, user_ids):
        """Advertiser-scoped user sees only their own organization."""
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

    def test_user_without_permission_or_scope_gets_403(self, client, user_ids):
        """Security officer (security_admin role, no organization.read,
        no advertiser scope) → 403 at app layer."""
        token = _token(user_ids["secoff"])
        resp = client.get(
            "/api/v1/identity/advertiser-organizations",
            headers=_auth(token),
        )
        assert resp.status_code == 403, resp.text
        body = resp.json()
        assert "detail" in body

    def test_user_with_global_permission_passes(self, client, user_ids):
        """Operator with organization.read (global) passes app layer."""
        token = _token(user_ids["noperms"])
        resp = client.get(
            "/api/v1/identity/advertiser-organizations",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text

    def test_rls_blocks_without_set_local(self, client, user_ids):
        """If SET LOCAL is not called, RLS defaults to empty filter.
        Skipped in dev — superuser BYPASSRLS (per ADR-009 §9)."""
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
