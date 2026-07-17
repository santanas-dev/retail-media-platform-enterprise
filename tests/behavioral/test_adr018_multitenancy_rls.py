"""
Behavioral tests — ADR-018: Multitenancy RLS (retailer + advertiser).

Creates dedicated scoped users per retailer to prove:
  - retailer A sees only retailer A data
  - retailer A does NOT see retailer B campaigns/briefs/orgs
  - two advertisers inside same retailer are still isolated by advertiser scope
  - same advertiser-like data in another retailer is hidden
  - empty retailer scope deny-all
  - admin bypass sees both retailers
  - direct DB proof under retail_media_app/NOBYPASSRLS with SET LOCAL

Every assertion is concrete: specific status codes, specific IDs present/absent.
No "200 or 403" ambiguity.

Requires: RUN_BEHAVIORAL_TESTS=1, PostgreSQL, migrations.
"""

import asyncio
import os

import pytest
from fastapi.testclient import TestClient

from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token
from tests.behavioral.conftest import _run_sql, USER_IDS

RET_A = "beh-018-ret-a-000000000000001"
RET_B = "beh-018-ret-b-000000000000001"
ORG_A = "beh-018-org-a-000000000000001"
ORG_A2 = "beh-018-org-a2-000000000000001"
ORG_B = "beh-018-org-b-000000000000001"
BRIEF_A = "beh-018-brief-a-0000000000001"
BRIEF_A2 = "beh-018-brief-a2-0000000000001"
BRIEF_B = "beh-018-brief-b-0000000000001"
AUTH_PROVIDER = "local_advertiser"
USER_SCOPED_A = "beh-018-usr-scoped-a-00000001"
USER_SCOPED_A2 = "beh-018-usr-scoped-a2-00000001"
USER_NO_SCOPE = "beh-018-usr-no-scope-000001"


def _token(user_id: str) -> str:
    return create_access_token(user_id, AUTH_PROVIDER)


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(app, db_available, test_users):
    reset_security_config()
    return TestClient(app)


@pytest.fixture
def adr018_setup(db_available, test_users):
    """Two retailers, three orgs (two in RET_A, one in RET_B), briefs,
    two scoped users, one no-scope user."""
    # Each group is a separate _run_sql call — no comment/semicolon splitter issues.
    asyncio.run(_run_sql(f"""
    INSERT INTO retailers (id, code, legal_name, display_name, status)
    VALUES ('{RET_A}', 'RETAILER-A', 'Retailer Alpha', 'Alpha', 'active')
    ON CONFLICT (id) DO NOTHING
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO retailers (id, code, legal_name, display_name, status)
    VALUES ('{RET_B}', 'RETAILER-B', 'Retailer Beta', 'Beta', 'active')
    ON CONFLICT (id) DO NOTHING
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO advertiser_organizations (id, code, legal_name, display_name, status, retailer_id)
    VALUES ('{ORG_A}', 'ADR018-ORG-A', 'Org Alpha', 'Org Alpha', 'active', '{RET_A}')
    ON CONFLICT (code) DO NOTHING
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO advertiser_organizations (id, code, legal_name, display_name, status, retailer_id)
    VALUES ('{ORG_A2}', 'ADR018-ORG-A2', 'Org Alpha 2', 'Org Alpha 2', 'active', '{RET_A}')
    ON CONFLICT (code) DO NOTHING
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO advertiser_organizations (id, code, legal_name, display_name, status, retailer_id)
    VALUES ('{ORG_B}', 'ADR018-ORG-B', 'Org Beta', 'Org Beta', 'active', '{RET_B}')
    ON CONFLICT (code) DO NOTHING
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO campaign_briefs (id, advertiser_organization_id, title, status, created_by, created_at, updated_at)
    VALUES ('{BRIEF_A}', '{ORG_A}', 'Brief Alpha RetA', 'draft', '{USER_IDS["advertiser"]}', NOW(), NOW())
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO campaign_briefs (id, advertiser_organization_id, title, status, created_by, created_at, updated_at)
    VALUES ('{BRIEF_A2}', '{ORG_A2}', 'Brief Alpha2 RetA', 'draft', '{USER_IDS["advertiser"]}', NOW(), NOW())
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO campaign_briefs (id, advertiser_organization_id, title, status, created_by, created_at, updated_at)
    VALUES ('{BRIEF_B}', '{ORG_B}', 'Brief Beta RetB', 'draft', '{USER_IDS["advertiser"]}', NOW(), NOW())
    """))
    # Ensure advertiser role + permissions exist
    asyncio.run(_run_sql("""
    INSERT INTO roles (id, code, name, description, is_system)
    SELECT '00000000-0000-0000-0000-000000000114', 'advertiser', 'Advertiser',
           'Advertiser cabinet user', false
    WHERE NOT EXISTS (SELECT 1 FROM roles WHERE code='advertiser')
    """))
    asyncio.run(_run_sql("""
    INSERT INTO permissions (id, code, name) VALUES
    ('00000000-0000-0000-0000-00000000010c', 'campaigns.read', 'READ_CAMPAIGNS')
    ON CONFLICT (code) DO NOTHING
    """))
    asyncio.run(_run_sql("""
    INSERT INTO permissions (id, code, name) VALUES
    ('00000000-0000-0000-0000-00000000010f', 'creatives.read', 'READ_CREATIVES')
    ON CONFLICT (code) DO NOTHING
    """))
    asyncio.run(_run_sql("""
    INSERT INTO role_permissions (id, role_id, permission_id)
    SELECT 'rp-018-adv-cr',
           (SELECT id FROM roles WHERE code='advertiser'),
           (SELECT id FROM permissions WHERE code='campaigns.read')
    WHERE NOT EXISTS (
      SELECT 1 FROM role_permissions
      WHERE role_id=(SELECT id FROM roles WHERE code='advertiser')
      AND permission_id=(SELECT id FROM permissions WHERE code='campaigns.read')
    )
    """))
    asyncio.run(_run_sql("""
    INSERT INTO role_permissions (id, role_id, permission_id)
    SELECT 'rp-018-adv-creatr',
           (SELECT id FROM roles WHERE code='advertiser'),
           (SELECT id FROM permissions WHERE code='creatives.read')
    WHERE NOT EXISTS (
      SELECT 1 FROM role_permissions
      WHERE role_id=(SELECT id FROM roles WHERE code='advertiser')
      AND permission_id=(SELECT id FROM permissions WHERE code='creatives.read')
    )
    """))
    # Scoped user A (ORG_A, RET_A)
    asyncio.run(_run_sql(f"""
    INSERT INTO users (id, code, username, email, display_name, auth_provider, status)
    VALUES ('{USER_SCOPED_A}', 'BEH-018-SA', 'beh-018-scoped-a',
            'beh-018-sa@t.local', 'Scoped A', '{AUTH_PROVIDER}', 'active')
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO local_credentials (id, user_id, credential_type, password_hash, status)
    VALUES ('lc-018-sa', '{USER_SCOPED_A}', '{AUTH_PROVIDER}',
            '$2b$04$aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'active')
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO user_roles (id, user_id, role_id, scope_type, scope_id)
    SELECT 'ur-018-sa', '{USER_SCOPED_A}',
           (SELECT id FROM roles WHERE code='advertiser'),
           'advertiser', '{ORG_A}'
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO advertiser_user_memberships (id, user_id, advertiser_organization_id, status)
    VALUES ('aum-018-sa', '{USER_SCOPED_A}', '{ORG_A}', 'active')
    """))
    # Scoped user A2 (ORG_A2, same retailer RET_A)
    asyncio.run(_run_sql(f"""
    INSERT INTO users (id, code, username, email, display_name, auth_provider, status)
    VALUES ('{USER_SCOPED_A2}', 'BEH-018-SA2', 'beh-018-scoped-a2',
            'beh-018-sa2@t.local', 'Scoped A2', '{AUTH_PROVIDER}', 'active')
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO local_credentials (id, user_id, credential_type, password_hash, status)
    VALUES ('lc-018-sa2', '{USER_SCOPED_A2}', '{AUTH_PROVIDER}',
            '$2b$04$aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'active')
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO user_roles (id, user_id, role_id, scope_type, scope_id)
    SELECT 'ur-018-sa2', '{USER_SCOPED_A2}',
           (SELECT id FROM roles WHERE code='advertiser'),
           'advertiser', '{ORG_A2}'
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO advertiser_user_memberships (id, user_id, advertiser_organization_id, status)
    VALUES ('aum-018-sa2', '{USER_SCOPED_A2}', '{ORG_A2}', 'active')
    """))
    # No-scope user (operator role, no advertiser scope)
    asyncio.run(_run_sql(f"""
    INSERT INTO users (id, code, username, email, display_name, auth_provider, status)
    VALUES ('{USER_NO_SCOPE}', 'BEH-018-NS', 'beh-018-noscope',
            'beh-018-ns@t.local', 'NoScope', '{AUTH_PROVIDER}', 'active')
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO local_credentials (id, user_id, credential_type, password_hash, status)
    VALUES ('lc-018-ns', '{USER_NO_SCOPE}', '{AUTH_PROVIDER}',
            '$2b$04$aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'active')
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO user_roles (id, user_id, role_id)
    SELECT 'ur-018-ns', '{USER_NO_SCOPE}',
           (SELECT id FROM roles WHERE code='operator')
    """))
    yield {
        "ret_a": RET_A, "ret_b": RET_B,
        "org_a": ORG_A, "org_a2": ORG_A2, "org_b": ORG_B,
        "brief_a": BRIEF_A, "brief_a2": BRIEF_A2, "brief_b": BRIEF_B,
        "user_scoped_a": USER_SCOPED_A, "user_scoped_a2": USER_SCOPED_A2,
        "user_no_scope": USER_NO_SCOPE,
    }
    # Cleanup
    asyncio.run(_run_sql(f"""
    DELETE FROM refresh_sessions WHERE user_id LIKE 'beh-018-%'
    """))
    asyncio.run(_run_sql("DELETE FROM advertiser_user_memberships WHERE id LIKE 'aum-018-%'"))
    asyncio.run(_run_sql("DELETE FROM user_roles WHERE id LIKE 'ur-018-%'"))
    asyncio.run(_run_sql("DELETE FROM local_credentials WHERE id LIKE 'lc-018-%'"))
    asyncio.run(_run_sql("DELETE FROM campaign_briefs WHERE id LIKE 'beh-018-%'"))
    asyncio.run(_run_sql("DELETE FROM advertiser_organizations WHERE id LIKE 'beh-018-%'"))
    asyncio.run(_run_sql("DELETE FROM users WHERE id LIKE 'beh-018-%'"))
    asyncio.run(_run_sql("DELETE FROM retailers WHERE id LIKE 'beh-018-%'"))


@pytest.mark.usefixtures("adr018_setup")
class TestADR018MultitenancyRLS:

    @pytest.fixture(autouse=True)
    def setup(self, client, db_available, adr018_setup):
        self.client = client
        self.data = adr018_setup
        self.token_scoped_a = _token(self.data["user_scoped_a"])
        self.token_scoped_a2 = _token(self.data["user_scoped_a2"])
        self.token_admin = _token(USER_IDS["readonly"])
        self.token_no_scope = _token(self.data["user_no_scope"])

    def test_retailer_a_sees_only_own_briefs(self):
        """Scoped to ORG_A — sees BRIEF_A, NOT BRIEF_B or BRIEF_A2."""
        resp = self.client.get(
            "/api/v1/identity/campaign-briefs",
            headers=_auth(self.token_scoped_a),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        items = resp.json()["items"]
        brief_ids = {b["id"] for b in items}
        assert self.data["brief_a"] in brief_ids, f"Missing BRIEF_A: {brief_ids}"
        assert self.data["brief_b"] not in brief_ids, f"BRIEF_B leaked: {brief_ids}"
        assert self.data["brief_a2"] not in brief_ids, f"BRIEF_A2 leaked: {brief_ids}"

    def test_retailer_a_cannot_get_retailer_b_brief(self):
        """Cross-retailer brief detail → 404 (RLS hides the resource)."""
        resp = self.client.get(
            f"/api/v1/identity/campaign-briefs/{self.data['brief_b']}",
            headers=_auth(self.token_scoped_a),
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def test_same_retailer_advertiser_scope_isolation(self):
        """Scoped to ORG_A2 — sees BRIEF_A2, NOT BRIEF_A (same retailer)."""
        resp = self.client.get(
            "/api/v1/identity/campaign-briefs",
            headers=_auth(self.token_scoped_a2),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        items = resp.json()["items"]
        brief_ids = {b["id"] for b in items}
        assert self.data["brief_a2"] in brief_ids, f"Missing BRIEF_A2: {brief_ids}"
        assert self.data["brief_a"] not in brief_ids, f"BRIEF_A leaked: {brief_ids}"
        assert self.data["brief_b"] not in brief_ids, f"BRIEF_B leaked: {brief_ids}"

    def test_same_retailer_cross_org_brief_detail_404(self):
        """Scoped to ORG_A2 — gets 404 for ORG_A brief detail."""
        resp = self.client.get(
            f"/api/v1/identity/campaign-briefs/{self.data['brief_a']}",
            headers=_auth(self.token_scoped_a2),
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def test_same_data_other_retailer_hidden(self):
        """Brief in RET_B is invisible to user scoped to RET_A."""
        resp = self.client.get(
            "/api/v1/identity/campaign-briefs",
            headers=_auth(self.token_scoped_a),
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        brief_ids = {b["id"] for b in items}
        assert self.data["brief_b"] not in brief_ids, f"BRIEF_B leaked: {brief_ids}"
        assert self.data["brief_a"] in brief_ids

    def test_empty_scope_denies_all(self):
        """Dedicated no-scope user (operator, no advertiser scope) → 403."""
        resp = self.client.get(
            "/api/v1/identity/campaign-briefs",
            headers=_auth(self.token_no_scope),
        )
        assert resp.status_code == 403, (
            f"Expected 403 for no-scope user, got {resp.status_code}: {resp.text[:200]}"
        )

    def test_admin_sees_both_retailers(self):
        """system_admin bypasses RLS — sees briefs from both retailers."""
        resp = self.client.get(
            "/api/v1/identity/campaign-briefs",
            headers=_auth(self.token_admin),
        )
        assert resp.status_code == 200, f"Admin list failed: {resp.status_code}"
        items = resp.json()["items"]
        brief_ids = {b["id"] for b in items}
        assert self.data["brief_a"] in brief_ids, "Admin missing BRIEF_A"
        assert self.data["brief_b"] in brief_ids, "Admin missing BRIEF_B"
        assert self.data["brief_a2"] in brief_ids, "Admin missing BRIEF_A2"

    def test_direct_db_rls_proof_retailer_isolation(self):
        """Connect as retail_media_app (NOBYPASSRLS).

        campaign_briefs uses TWO_LEVEL RLS (retailer_id AND advertiser_organization_id).
        SET LOCAL both scopes → scope A returns A rows, NOT B rows.
        Empty scope → deny-all. Admin bypass → all rows.
        """
        import asyncpg

        APP_DB_URL = os.environ.get(
            "BEHAVIORAL_APP_DB_URL",
            "postgresql://retail_media_app:***@localhost:5432/retail_media_platform",
        )
        _pass = "retail_media_app"
        APP_DB_URL = APP_DB_URL.replace("***", _pass)

        async def _prove():
            conn = await asyncpg.connect(APP_DB_URL)
            try:
                await conn.execute("SET app.rmp_scope_retailer_ids = $1", RET_A)
                await conn.execute("SET app.rmp_scope_advertiser_ids = $1", f"{ORG_A},{ORG_A2}")
                await conn.execute("SET app.rmp_is_admin = 'false'")
                rows_a = await conn.fetch("SELECT id FROM campaign_briefs ORDER BY id")
                ids_a = {r["id"] for r in rows_a}
                assert BRIEF_A in ids_a, f"RET_A scope missing BRIEF_A: {ids_a}"
                assert BRIEF_A2 in ids_a, f"RET_A scope missing BRIEF_A2: {ids_a}"
                assert BRIEF_B not in ids_a, f"RET_A scope leaked BRIEF_B: {ids_a}"

                await conn.execute("SET app.rmp_scope_retailer_ids = $1", RET_B)
                await conn.execute("SET app.rmp_scope_advertiser_ids = $1", ORG_B)
                rows_b = await conn.fetch("SELECT id FROM campaign_briefs ORDER BY id")
                ids_b = {r["id"] for r in rows_b}
                assert BRIEF_B in ids_b, f"RET_B scope missing BRIEF_B: {ids_b}"
                assert BRIEF_A not in ids_b, f"RET_B scope leaked BRIEF_A: {ids_b}"
                assert BRIEF_A2 not in ids_b, f"RET_B scope leaked BRIEF_A2: {ids_b}"

                await conn.execute("SET app.rmp_scope_retailer_ids = ''")
                await conn.execute("SET app.rmp_scope_advertiser_ids = ''")
                await conn.execute("SET app.rmp_is_admin = 'false'")
                rows_empty = await conn.fetch("SELECT id FROM campaign_briefs ORDER BY id")
                assert len(rows_empty) == 0, f"Empty scope deny-all failed: {[r['id'] for r in rows_empty]}"

                await conn.execute("SET app.rmp_scope_retailer_ids = ''")
                await conn.execute("SET app.rmp_scope_advertiser_ids = ''")
                await conn.execute("SET app.rmp_is_admin = 'true'")
                rows_admin = await conn.fetch("SELECT id FROM campaign_briefs ORDER BY id")
                ids_admin = {r["id"] for r in rows_admin}
                assert BRIEF_A in ids_admin, "Admin missing BRIEF_A"
                assert BRIEF_B in ids_admin, "Admin missing BRIEF_B"
                assert BRIEF_A2 in ids_admin, "Admin missing BRIEF_A2"
            finally:
                await conn.close()

        asyncio.run(_prove())
