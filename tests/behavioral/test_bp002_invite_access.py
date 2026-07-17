"""
Behavioral tests — BP-002 Follow-up: Advertiser Invite Access Proof.

Proves that invite acceptance creates real DB entities, the invited user
can log in, and access is scoped to a single organization.

Requires: RUN_BEHAVIORAL_TESTS=1, running PostgreSQL, migrations + seed applied.
"""

import asyncio
import concurrent.futures
import os



import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from packages.security.config import reset_security_config
from tests.behavioral.conftest import _run_sql

# ── IDs ────────────────────────────────────────────────────────────────────

_ORG_A_ID = "beh-bp2-org-a-000000000000001"
_ORG_B_ID = "beh-bp2-org-b-000000000000001"
_APP_ID = "beh-bp2-app-00000000000000001"
_INVITE_ID = "beh-bp2-inv-00000000000000001"
_TOKEN = "bp2-behavioral-test-token-64-chars-x-aaaaaaaaaaaaaaaaaaaaaaaaaaa"
_CONTACT_EMAIL = "ivan-bp2@test.local"

_PASSWORD = "SecurePass123!"


# ── DB query helper ────────────────────────────────────────────────────────

def _query_one(sql: str, params: dict | None = None):
    """Execute query against behavioral DB (owner), return first row as dict."""
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
                await conn.execute(
                    text("SELECT set_config('app.rmp_is_admin', 'true', true)")
                )
                result = await conn.execute(text(sql), params or {})
                row = result.fetchone()
                return dict(row._mapping) if row else None
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def _query_all(sql: str, params: dict | None = None):
    """Return all rows as list of dicts."""
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
                await conn.execute(
                    text("SELECT set_config('app.rmp_is_admin', 'true', true)")
                )
                result = await conn.execute(text(sql), params or {})
                return [dict(row._mapping) for row in result.fetchall()]
        finally:
            await engine.dispose()

    return asyncio.run(_run())


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def client(app, db_available, test_users):
    reset_security_config()
    return TestClient(app)


@pytest.fixture
def bp2_fixtures(db_available):
    """Set up orgs, application, invite for BP-002 behavioral tests."""
    ph = bcrypt.hashpw(
        _PASSWORD.encode(), bcrypt.gensalt(rounds=4)
    ).decode()

    setup_sql = f"""
    -- Cleanup previous BP-002 test data
    ; DELETE FROM advertiser_invites WHERE id LIKE 'beh-bp2-%'
    ; DELETE FROM advertiser_applications WHERE id LIKE 'beh-bp2-%'
    ; DELETE FROM refresh_sessions WHERE user_id LIKE 'beh-bp2-%'
    ; DELETE FROM advertiser_user_memberships WHERE user_id LIKE 'beh-bp2-%'
    ; DELETE FROM local_credentials WHERE user_id LIKE 'beh-bp2-%'
    ; DELETE FROM user_roles WHERE user_id LIKE 'beh-bp2-%'
    ; DELETE FROM audit_events_operational WHERE actor_user_id LIKE 'beh-bp2-%'
       OR target_id LIKE 'beh-bp2-%'
    ; DELETE FROM users WHERE id LIKE 'beh-bp2-%'
    ; DELETE FROM advertiser_user_memberships WHERE advertiser_organization_id LIKE 'beh-bp2-%'
    ; DELETE FROM user_roles WHERE scope_id LIKE 'beh-bp2-%'
    ; DELETE FROM local_credentials WHERE user_id IN (SELECT id FROM users WHERE username = 'ivan-bp2@test.local')
    ; DELETE FROM users WHERE username = 'ivan-bp2@test.local'
    ; DELETE FROM advertiser_organizations WHERE id LIKE 'beh-bp2-%'

    -- Two advertiser organizations
    ; INSERT INTO advertiser_organizations (id, code, legal_name, display_name, status) VALUES
      ('{_ORG_A_ID}', 'BP2-ORG-A', 'ООО БП2-А', 'BP2 Org A', 'active'),
      ('{_ORG_B_ID}', 'BP2-ORG-B', 'ООО БП2-Б', 'BP2 Org B', 'active')
      ON CONFLICT (code) DO NOTHING

    -- Ensure advertiser role exists (idempotent)
    ; INSERT INTO roles (id, code, name, description, is_system)
      SELECT '00000000-0000-0000-0000-000000000114', 'advertiser', 'Advertiser',
             'Advertiser cabinet user', false
      WHERE NOT EXISTS (SELECT 1 FROM roles WHERE code='advertiser')

    -- Ensure organization.read permission exists + assigned to advertiser
    ; INSERT INTO permissions (id, code, name) VALUES
      ('00000000-0000-0000-0000-0000000000ff', 'organization.read', 'Просмотр организации')
      ON CONFLICT (code) DO NOTHING
    ; INSERT INTO role_permissions (id, role_id, permission_id)
      SELECT 'rp-bp2-org-read',
             (SELECT id FROM roles WHERE code='advertiser'),
             (SELECT id FROM permissions WHERE code='organization.read')
      WHERE NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_id=(SELECT id FROM roles WHERE code='advertiser')
          AND permission_id=(SELECT id FROM permissions WHERE code='organization.read')
      )

    -- Ensure advertisers.read permission for advertiser role
    ; INSERT INTO permissions (id, code, name) VALUES
      ('00000000-0000-0000-0000-000000000108', 'advertisers.read', 'Просмотр рекламодателей')
      ON CONFLICT (code) DO NOTHING
    ; INSERT INTO role_permissions (id, role_id, permission_id)
      SELECT 'rp-bp2-adv-read',
             (SELECT id FROM roles WHERE code='advertiser'),
             (SELECT id FROM permissions WHERE code='advertisers.read')
      WHERE NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_id=(SELECT id FROM roles WHERE code='advertiser')
          AND permission_id=(SELECT id FROM permissions WHERE code='advertisers.read')
      )

    -- Ensure campaigns.read permission for advertiser role
    ; INSERT INTO permissions (id, code, name) VALUES
      ('00000000-0000-0000-0000-00000000010c', 'campaigns.read', 'Просмотр кампаний')
      ON CONFLICT (code) DO NOTHING
    ; INSERT INTO role_permissions (id, role_id, permission_id)
      SELECT 'rp-bp2-camp-read',
             (SELECT id FROM roles WHERE code='advertiser'),
             (SELECT id FROM permissions WHERE code='campaigns.read')
      WHERE NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_id=(SELECT id FROM roles WHERE code='advertiser')
          AND permission_id=(SELECT id FROM permissions WHERE code='campaigns.read')
      )

    -- Approved application with org_id pointing to org-A
    ; INSERT INTO advertiser_applications
        (id, company_name, contact_name, email, status, organization_id)
      VALUES
        ('{_APP_ID}', 'ООО БП2 Тест', 'Иван', '{_CONTACT_EMAIL}',
         'approved', '{_ORG_A_ID}')

    -- Pending invite (created_by=NULL — FK to users, admin user not needed for test)
    ; INSERT INTO advertiser_invites
        (id, advertiser_application_id, advertiser_organization_id,
         token, contact_email, status, expires_at, created_by)
      VALUES
        ('{_INVITE_ID}', '{_APP_ID}', '{_ORG_A_ID}',
         '{_TOKEN}', '{_CONTACT_EMAIL}', 'pending',
         NOW() + INTERVAL '7 days', NULL)
    """
    asyncio.run(_run_sql(setup_sql))
    yield {
        "org_a_id": _ORG_A_ID,
        "org_b_id": _ORG_B_ID,
        "app_id": _APP_ID,
        "invite_id": _INVITE_ID,
        "token": _TOKEN,
        "password": _PASSWORD,
    }

    cleanup_sql = f"""
    DELETE FROM advertiser_invites WHERE id LIKE 'beh-bp2-%'
    ; DELETE FROM advertiser_applications WHERE id LIKE 'beh-bp2-%'
    ; DELETE FROM refresh_sessions WHERE user_id LIKE 'beh-bp2-%'
    ; DELETE FROM advertiser_user_memberships WHERE user_id LIKE 'beh-bp2-%'
    ; DELETE FROM local_credentials WHERE user_id LIKE 'beh-bp2-%'
    ; DELETE FROM user_roles WHERE user_id LIKE 'beh-bp2-%'
    ; DELETE FROM audit_events_operational WHERE actor_user_id LIKE 'beh-bp2-%'
       OR target_id LIKE 'beh-bp2-%'
    ; DELETE FROM users WHERE id LIKE 'beh-bp2-%'
    ; DELETE FROM advertiser_user_memberships WHERE advertiser_organization_id LIKE 'beh-bp2-%'
    ; DELETE FROM user_roles WHERE scope_id LIKE 'beh-bp2-%'
    ; DELETE FROM local_credentials WHERE user_id IN (SELECT id FROM users WHERE username = 'ivan-bp2@test.local')
    ; DELETE FROM users WHERE username = 'ivan-bp2@test.local'
    ; DELETE FROM advertiser_organizations WHERE id LIKE 'beh-bp2-%'
    """
    asyncio.run(_run_sql(cleanup_sql))


@pytest.fixture
def expired_invite(db_available):
    """Create an expired invite for negative-path tests."""
    expired_token = "bp2-expired-token-64-chars-x-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

    setup = f"""
    DELETE FROM advertiser_invites WHERE token = '{expired_token}'
    ; DELETE FROM advertiser_organizations WHERE id = 'beh-bp2-exp-org-0000001'
    ; DELETE FROM advertiser_applications WHERE id = 'beh-bp2-exp-app-0000001'

    ; INSERT INTO advertiser_organizations (id, code, legal_name, display_name, status) VALUES
      ('beh-bp2-exp-org-0000001', 'BP2-EXP', 'Expired Org', 'Expired', 'active')
      ON CONFLICT (code) DO NOTHING

    ; INSERT INTO advertiser_applications
        (id, company_name, contact_name, email, status, organization_id)
      VALUES
        ('beh-bp2-exp-app-0000001', 'Expired Co', 'Test', 'exp@t.local',
         'approved', 'beh-bp2-exp-org-0000001')

    ; INSERT INTO advertiser_invites
        (id, advertiser_application_id, advertiser_organization_id,
         token, contact_email, status, expires_at, created_by)
      VALUES
        ('beh-bp2-exp-inv-0000001', 'beh-bp2-exp-app-0000001',
         'beh-bp2-exp-org-0000001', '{expired_token}', 'exp@t.local',
         'pending', NOW() - INTERVAL '1 hour', NULL)
    """
    asyncio.run(_run_sql(setup))
    yield expired_token

    cleanup = f"""
    DELETE FROM advertiser_invites WHERE token = '{expired_token}'
    ; DELETE FROM advertiser_applications WHERE id = 'beh-bp2-exp-app-0000001'
    ; DELETE FROM advertiser_organizations WHERE id = 'beh-bp2-exp-org-0000001'
    """
    asyncio.run(_run_sql(cleanup))


# ── Helpers ────────────────────────────────────────────────────────────────


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


# ── Test 1: Accept creates real DB access entities ─────────────────────────


class TestInviteAcceptCreatesRealAccess:
    """Prove that accept_invite creates User + Credential + UserRole + Membership."""

    @pytest.fixture(autouse=True)
    def setup(self, client, bp2_fixtures):
        self.client = client
        self.fix = bp2_fixtures

    def test_accept_creates_real_advertiser_access(self):
        """Accept invite → verify DB entities exist with correct scope."""
        token = self.fix["token"]
        password = self.fix["password"]
        org_a = self.fix["org_a_id"]

        # Before: no BP-002 user
        users_before = _query_one(
            "SELECT COUNT(*) AS cnt FROM users WHERE username = 'ivan-bp2@test.local'"
        )
        assert users_before["cnt"] == 0, "No BP-002 users should exist before accept"

        # Accept the invite
        resp = self.client.post(
            f"/api/v1/public/advertiser-invites/{token}/accept",
            json={"password": password},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "ok"

        # After: user created (username = contact email from the invite)
        user = _query_one(
            "SELECT id, username, display_name, auth_provider, status "
            "FROM users WHERE username = :username",
            {"username": _CONTACT_EMAIL},
        )
        assert user is not None, "User should exist after accept"
        assert user["auth_provider"] == "local_advertiser"
        assert user["status"] == "active"
        user_id = user["id"]

        # Credential created
        cred = _query_one(
            "SELECT * FROM local_credentials WHERE user_id = :uid", {"uid": user_id}
        )
        assert cred is not None, "Credential should exist"
        assert cred["credential_type"] == "local_advertiser"
        assert cred["status"] == "active"

        # UserRole with scope=advertiser, scope_id=org_A
        role = _query_one(
            "SELECT ur.*, r.code AS role_code FROM user_roles ur "
            "JOIN roles r ON r.id = ur.role_id "
            "WHERE ur.user_id = :uid", {"uid": user_id}
        )
        assert role is not None, "UserRole should exist"
        assert role["role_code"] == "advertiser"
        assert role["scope_type"] == "advertiser"
        assert role["scope_id"] == org_a, (
            f"Scope should be org-A ({org_a}), got {role['scope_id']}"
        )

        # Membership created
        member = _query_one(
            "SELECT * FROM advertiser_user_memberships WHERE user_id = :uid",
            {"uid": user_id}
        )
        assert member is not None, "Membership should exist"
        assert member["advertiser_organization_id"] == org_a
        assert member["status"] == "active"

        # Invite marked accepted
        invite = _query_one(
            "SELECT status, accepted_by_user_id FROM advertiser_invites "
            "WHERE token = :tok", {"tok": token}
        )
        assert invite["status"] == "accepted"
        assert invite["accepted_by_user_id"] == user_id


# ── Test 2: Invited advertiser can login ───────────────────────────────────


class TestInvitedAdvertiserCanLogin:
    """Prove that after accept, the advertiser user can authenticate."""

    @pytest.fixture(autouse=True)
    def setup(self, client, bp2_fixtures):
        self.client = client
        self.fix = bp2_fixtures
        self.password = self.fix["password"]

    def _accept_and_get_username(self):
        """Accept invite and return the created username (email)."""
        resp = self.client.post(
            f"/api/v1/public/advertiser-invites/{self.fix['token']}/accept",
            json={"password": self.password},
        )
        assert resp.status_code == 200, f"Accept failed: {resp.text}"

        user = _query_one(
            "SELECT username FROM users WHERE username = 'ivan-bp2@test.local'"
        )
        assert user is not None
        return user["username"]

    def test_invited_advertiser_can_login(self):
        """After accept, user can login with the set password."""
        username = self._accept_and_get_username()

        resp = self.client.post("/api/v1/auth/login", json={
            "username_or_email": username,
            "password": self.password,
            "auth_provider": "local_advertiser",
        })
        assert resp.status_code == 200, (
            f"Login failed: {resp.status_code} — {resp.text}"
        )
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "Bearer"

    def test_invited_advertiser_me_returns_scoped_data(self):
        """After login, /me returns correct user info and permissions."""
        username = self._accept_and_get_username()

        # Login
        login_resp = self.client.post("/api/v1/auth/login", json={
            "username_or_email": username,
            "password": self.password,
            "auth_provider": "local_advertiser",
        })
        token = login_resp.json()["access_token"]

        # /me
        me = self.client.get("/api/v1/auth/me", headers=_auth(token))
        assert me.status_code == 200, me.text
        me_body = me.json()
        assert me_body["username"] == username
        assert me_body["auth_provider"] == "local_advertiser"
        assert "organization.read" in me_body.get("permissions", [])
        assert len(me_body["permissions"]) > 0, (
            "Advertiser should have at least organization.read"
        )


# ── Test 3: Cross-org isolation ────────────────────────────────────────────


class TestCrossOrgIsolation:
    """Prove accepted user can only access own org, not org-B."""

    @pytest.fixture(autouse=True)
    def setup(self, client, bp2_fixtures):
        self.client = client
        self.fix = bp2_fixtures
        self.password = self.fix["password"]

    def _accept_and_get_token(self):
        """Accept invite and return JWT access token."""
        resp = self.client.post(
            f"/api/v1/public/advertiser-invites/{self.fix['token']}/accept",
            json={"password": self.password},
        )
        assert resp.status_code == 200, f"Accept failed: {resp.text}"

        user = _query_one(
            "SELECT username FROM users WHERE username = 'ivan-bp2@test.local'"
        )
        login_resp = self.client.post("/api/v1/auth/login", json={
            "username_or_email": user["username"],
            "password": self.password,
            "auth_provider": "local_advertiser",
        })
        return login_resp.json()["access_token"]

    def test_invited_advertiser_sees_own_org_only(self):
        """Scoped user sees only org-A data, not org-B."""
        token = self._accept_and_get_token()

        # Check /me organization_id is org-A
        me = self.client.get("/api/v1/auth/me", headers=_auth(token))
        assert me.status_code == 200
        me_body = me.json()
        assert me_body.get("advertiser_organization_id") == self.fix["org_a_id"], (
            f"Expected org-A ({self.fix['org_a_id']}), "
            f"got {me_body.get('advertiser_organization_id')}"
        )

    def test_cross_org_data_not_accessible(self):
        """Scoped user cannot see org-B in brand/contract listings."""
        token = self._accept_and_get_token()

        # Try advertiser brands — should only see org-A brands (or empty
        # since the org has no brands yet). The point is org-B is invisible.
        resp = self.client.get(
            "/api/v1/identity/advertiser-brands",
            headers=_auth(token),
        )
        # Should succeed but only return org-A-scoped results
        assert resp.status_code == 200, resp.text
        data = resp.json() if isinstance(resp.json(), list) else resp.json().get("items", [])
        for item in data:
            assert item.get("advertiser_organization_id") != self.fix["org_b_id"], (
                f"Cross-org leak! Found org-B data: {item}"
            )


# ── Test 4: Token reuse rejected ───────────────────────────────────────────


class TestTokenReuseRejected:
    """Prove token is single-use — second accept returns 400."""

    @pytest.fixture(autouse=True)
    def setup(self, client, bp2_fixtures):
        self.client = client
        self.fix = bp2_fixtures

    def test_invite_token_cannot_be_reused(self):
        """First accept succeeds, second accept returns 400."""
        token = self.fix["token"]
        password = self.fix["password"]

        # First accept
        resp1 = self.client.post(
            f"/api/v1/public/advertiser-invites/{token}/accept",
            json={"password": password},
        )
        assert resp1.status_code == 200, f"First accept: {resp1.text}"

        # Second accept — must fail
        resp2 = self.client.post(
            f"/api/v1/public/advertiser-invites/{token}/accept",
            json={"password": "OtherPass123!"},
        )
        assert resp2.status_code == 400, (
            f"Second accept should be 400, got {resp2.status_code}: {resp2.text}"
        )
        assert "использовано" in resp2.json()["detail"].lower()

        # Verify only ONE user created
        users = _query_all(
            "SELECT id FROM users WHERE username = 'ivan-bp2@test.local'"
        )
        assert len(users) == 1, (
            f"Token reuse created {len(users)} users, expected 1"
        )

    def test_invalid_token_rejected(self):
        """Non-existent token returns 400."""
        resp = self.client.post(
            "/api/v1/public/advertiser-invites/nonexistent-token-00000000000000000000/accept",
            json={"password": "SomePass123!"},
        )
        assert resp.status_code == 400, resp.text
        assert "Недействительный" in resp.json()["detail"]

    def test_expired_token_rejected(self, expired_invite):
        """Expired token returns 400 with expiry message."""
        resp = self.client.post(
            f"/api/v1/public/advertiser-invites/{expired_invite}/accept",
            json={"password": "SomePass123!"},
        )
        assert resp.status_code == 400, resp.text
        assert "истёк" in resp.json()["detail"].lower()


# ── Test 5: Concurrent double-accept race condition ────────────────────────


class TestConcurrentAccept:
    """Prove SELECT ... FOR UPDATE prevents double user creation."""

    @pytest.fixture(autouse=True)
    def setup(self, client, bp2_fixtures):
        self.client = client
        self.fix = bp2_fixtures

    def test_concurrent_invite_accept_creates_single_access(self, app):
        """Two simultaneous accepts → exactly ONE user created."""
        token = self.fix["token"]
        password = self.fix["password"]

        def do_accept():
            """Run accept in thread (TestClient is sync, not async-safe)."""
            # Create a fresh TestClient per thread to avoid shared state
            from fastapi.testclient import TestClient as TC
            tc = TC(app)
            return tc.post(
                f"/api/v1/public/advertiser-invites/{token}/accept",
                json={"password": password},
            )

        # Fire two concurrent accepts in threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(do_accept) for _ in range(2)]
            results = [f.result() for f in futures]

        # One must succeed (200), one must fail (400 — already used)
        statuses = {r.status_code for r in results}
        assert 200 in statuses, (
            f"At least one accept should succeed, got {statuses}: {[r.text for r in results]}"
        )
        assert 400 in statuses, (
            f"Second accept should be 400 (already used), got {statuses}"
        )

        # Verify exactly ONE user created
        users = _query_all(
            "SELECT id, username FROM users WHERE username = 'ivan-bp2@test.local'"
        )
        assert len(users) == 1, (
            f"Concurrent accept created {len(users)} users! IDs: {[u['id'] for u in users]}"
        )

        # Verify exactly ONE credential
        creds = _query_all(
            "SELECT id FROM local_credentials WHERE user_id IN (SELECT id FROM users WHERE username = 'ivan-bp2@test.local')"
        )
        assert len(creds) == 1, f"Expected 1 credential, got {len(creds)}"

        # Verify exactly ONE membership
        members = _query_all(
            "SELECT id FROM advertiser_user_memberships WHERE user_id IN (SELECT id FROM users WHERE username = 'ivan-bp2@test.local')"
        )
        assert len(members) == 1, f"Expected 1 membership, got {len(members)}"

        # Verify exactly ONE user_role
        roles = _query_all(
            "SELECT id FROM user_roles WHERE user_id IN (SELECT id FROM users WHERE username = 'ivan-bp2@test.local')"
        )
        assert len(roles) == 1, f"Expected 1 user_role, got {len(roles)}"
