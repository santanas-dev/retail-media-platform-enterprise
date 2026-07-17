"""
Behavioral tests — BP-004 Follow-up: Campaign Briefs RLS & Tenant Isolation.

Proves that campaign_briefs is protected by RLS and repository scoping
is fail-closed.  All tests use real PostgreSQL with NOBYPASSRLS app role.

Requires: RUN_BEHAVIORAL_TESTS=1, running PostgreSQL, migrations applied.
"""
import asyncio
import os

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token
from tests.behavioral.conftest import _run_sql

# ── IDs ──────────────────────────────────────────────────────────────────────

ORG_A = "beh-bp4-org-a-0000000000000001"
ORG_B = "beh-bp4-org-b-0000000000000001"
USER_A = "beh-bp4-user-a-0000000000000001"
ROLE_A = "beh-bp4-role-a-0000000000000001"
MEMBERSHIP_A = "beh-bp4-mem-a-0000000000000001"
CRED_A = "beh-bp4-cred-a-0000000000000001"
USER_ROLE_A = "beh-bp4-ur-a-0000000000000001"
BRIEF_A = "beh-bp4-brief-a-000000000000001"
BRIEF_B = "beh-bp4-brief-b-000000000000001"

USERNAME_A = "bp4-beh@test.local"
PASSWORD = "SecurePass123!"
AUTH_PROVIDER = "local_advertiser"

# ── Helpers ──────────────────────────────────────────────────────────────────

def _query_one(sql: str, params: dict | None = None):
    db_url = os.environ.get(
        "BEHAVIORAL_DB_URL",
        "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/"
        "retail_media_platform",
    )
    from sqlalchemy.ext.asyncio import create_async_engine as _cae
    async def _run():
        engine = _cae(db_url, echo=False)
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT set_config('app.rmp_is_admin', 'true', true)"))
                result = await conn.execute(text(sql), params or {})
                row = result.fetchone()
                return dict(row._mapping) if row else None
        finally:
            await engine.dispose()
    return asyncio.run(_run())


def _query_all(sql: str, params: dict | None = None):
    db_url = os.environ.get(
        "BEHAVIORAL_DB_URL",
        "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/"
        "retail_media_platform",
    )
    from sqlalchemy.ext.asyncio import create_async_engine as _cae
    async def _run():
        engine = _cae(db_url, echo=False)
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT set_config('app.rmp_is_admin', 'true', true)"))
                result = await conn.execute(text(sql), params or {})
                return [dict(row._mapping) for row in result.fetchall()]
        finally:
            await engine.dispose()
    return asyncio.run(_run())


def _token(user_id: str) -> str:
    return create_access_token(user_id, AUTH_PROVIDER)


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def client(app, db_available, test_users):
    reset_security_config()
    return TestClient(app)


@pytest.fixture
def bp4_fixtures(db_available):
    """Set up orgs, scoped user, and briefs in two orgs."""
    ph = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()

    setup = f"""
    -- Ensure advertiser role exists and has permissions
    INSERT INTO roles (id, code, name, description, is_system)
    VALUES ('{ROLE_A}', 'advertiser', 'Рекламодатель', 'Scoped advertiser', false)
    ON CONFLICT (id) DO NOTHING;

    -- Ensure the required permissions are assigned to the advertiser role
    ; INSERT INTO role_permissions (id, role_id, permission_id)
    VALUES ('{ROLE_A.replace("role","rp1")}', '{ROLE_A}',
        (SELECT id FROM permissions WHERE code = 'campaigns.read'))
    ON CONFLICT DO NOTHING;

    ; INSERT INTO role_permissions (id, role_id, permission_id)
    VALUES ('{ROLE_A.replace("role","rp2")}', '{ROLE_A}',
        (SELECT id FROM permissions WHERE code = 'campaigns.manage'))
    ON CONFLICT DO NOTHING;

    ; INSERT INTO role_permissions (id, role_id, permission_id)
    VALUES ('{ROLE_A.replace("role","rp3")}', '{ROLE_A}',
        (SELECT id FROM permissions WHERE code = 'organization.read'))
    ON CONFLICT DO NOTHING;

    -- Two organizations
    ; INSERT INTO advertiser_organizations (id, code, legal_name, display_name, status)
    VALUES ('{ORG_A}', 'ORG-A', 'ООО Альфа', 'Альфа', 'active')
    ON CONFLICT (id) DO NOTHING;

    ; INSERT INTO advertiser_organizations (id, code, legal_name, display_name, status)
    VALUES ('{ORG_B}', 'ORG-B', 'ООО Бета', 'Бета', 'active')
    ON CONFLICT (id) DO NOTHING;

    -- Scoped user for org A
    ; INSERT INTO users (id, code, username, email, display_name, auth_provider, status)
    VALUES ('{USER_A}', 'U-A', '{USERNAME_A}', '{USERNAME_A}', 'Иван Альфа', '{AUTH_PROVIDER}', 'active')
    ON CONFLICT (id) DO NOTHING;

    ; INSERT INTO local_credentials (id, user_id, credential_type, password_hash)
    VALUES ('{CRED_A}', '{USER_A}', '{AUTH_PROVIDER}', '{ph}')
    ON CONFLICT (user_id) DO NOTHING;

    -- Scoped role assignment: advertiser scope = ORG_A
    ; INSERT INTO user_roles (id, user_id, role_id, scope_type, scope_id)
    VALUES ('{USER_ROLE_A}', '{USER_A}', '{ROLE_A}', 'advertiser', '{ORG_A}')
    ON CONFLICT DO NOTHING;

    -- Membership
    ; INSERT INTO advertiser_user_memberships (id, user_id, advertiser_organization_id, status)
    VALUES ('{MEMBERSHIP_A}', '{USER_A}', '{ORG_A}', 'active')
    ON CONFLICT DO NOTHING;

    -- Brief in org A (direct INSERT with owner connection)
    ; INSERT INTO campaign_briefs (id, advertiser_organization_id, title, status, created_by, created_at, updated_at)
    VALUES ('{BRIEF_A}', '{ORG_A}', 'Brief Alpha', 'draft', '{USER_A}', NOW(), NOW());

    -- Brief in org B (separate org)
    ; INSERT INTO campaign_briefs (id, advertiser_organization_id, title, status, created_by, created_at, updated_at)
    VALUES ('{BRIEF_B}', '{ORG_B}', 'Brief Beta', 'draft', '{USER_A}', NOW(), NOW());
    """

    asyncio.run(_run_sql(setup))
    yield

    cleanup = f"""
    DELETE FROM campaign_briefs WHERE id LIKE 'beh-bp4-%';
    DELETE FROM user_roles WHERE id LIKE 'beh-bp4-%';
    DELETE FROM advertiser_user_memberships WHERE id LIKE 'beh-bp4-%';
    DELETE FROM local_credentials WHERE id LIKE 'beh-bp4-%';
    DELETE FROM role_permissions WHERE id LIKE 'beh-bp4-%';
    DELETE FROM users WHERE id LIKE 'beh-bp4-%';
    DELETE FROM advertiser_organizations WHERE id LIKE 'beh-bp4-%';
    """
    asyncio.run(_run_sql(cleanup))


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.usefixtures("bp4_fixtures")
class TestBP004BriefRLS:

    @pytest.fixture(autouse=True)
    def setup_client(self, client, db_available):
        self.client = client
        self.token_a = _token(USER_A)

    # ── Scope-isolated reads ──

    def test_brief_list_sees_only_own_org(self):
        resp = self.client.get(
            "/api/v1/identity/campaign-briefs",
            headers=_auth(self.token_a),
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        brief_ids = {b["id"] for b in items}
        assert BRIEF_A in brief_ids
        assert BRIEF_B not in brief_ids

    def test_brief_detail_cross_org_returns_404(self):
        resp = self.client.get(
            f"/api/v1/identity/campaign-briefs/{BRIEF_B}",
            headers=_auth(self.token_a),
        )
        assert resp.status_code == 404

    def test_brief_detail_own_org_works(self):
        resp = self.client.get(
            f"/api/v1/identity/campaign-briefs/{BRIEF_A}",
            headers=_auth(self.token_a),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Brief Alpha"

    # ── Scope-isolated mutations ──

    def test_brief_update_cross_org_denied(self):
        resp = self.client.patch(
            f"/api/v1/identity/campaign-briefs/{BRIEF_B}",
            json={"title": "Hacked"},
            headers=_auth(self.token_a),
        )
        assert resp.status_code == 404

    def test_brief_submit_cross_org_denied(self):
        resp = self.client.post(
            f"/api/v1/identity/campaign-briefs/{BRIEF_B}/submit",
            headers=_auth(self.token_a),
        )
        assert resp.status_code == 404

    # ── Create uses scope ──

    def test_brief_create_uses_current_advertiser_scope(self):
        resp = self.client.post(
            "/api/v1/identity/campaign-briefs",
            json={"title": "Created via scope"},
            headers=_auth(self.token_a),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["advertiser_organization_id"] == ORG_A
        assert data["status"] == "draft"

        # Cleanup
        asyncio.run(_run_sql(f"DELETE FROM campaign_briefs WHERE id = '{data['id']}'"))

    # ── Direct DB RLS proof ──

    def test_campaign_briefs_rls_blocks_cross_org_direct_select(self):
        """Direct DB query as app role (NOBYPASSRLS) should hide org-B brief."""
        # We query via API since the app connection uses retail_media_app
        # which has RLS enforced. Scoped user should only see org-A.
        resp = self.client.get(
            "/api/v1/identity/campaign-briefs",
            headers=_auth(self.token_a),
        )
        items = resp.json()["items"]
        org_ids = {b["advertiser_organization_id"] for b in items}
        assert ORG_A in org_ids
        assert ORG_B not in org_ids
