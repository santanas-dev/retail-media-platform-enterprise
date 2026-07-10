"""
Behavioral tests — Dual Auth Readiness (S-016).

Tests local_advertiser login, break_glass_admin login with audit,
/me truthfulness (DB-backed), refresh/logout cycle, AD stub 503.

Requires: RUN_BEHAVIORAL_TESTS=1, running PostgreSQL, migrations + seed applied.
"""

import asyncio
import os

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from packages.security.config import reset_security_config


# ---------------------------------------------------------------------------
# Client fixture (per-file — not in conftest)
# ---------------------------------------------------------------------------


@pytest.fixture
def client(app, db_available, test_users):
    """Provide a TestClient with a fresh SecurityConfig."""
    reset_security_config()
    return TestClient(app)


# ---------------------------------------------------------------------------
# DB query helper
# ---------------------------------------------------------------------------


def _query_one(sql: str, params: dict | None = None):
    """Execute a query against the behavioral DB and return first row as dict."""
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
                result = await conn.execute(text(sql), params or {})
                row = result.fetchone()
                return dict(row._mapping) if row else None
        finally:
            await engine.dispose()

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# Fixtures — break_glass_admin + AD test users
# ---------------------------------------------------------------------------

_BG_USER_ID = "beh-bg-00000000000000000010"
_BG_CRED_ID = "beh-bg-lc-000000000000000010"
_BG_PASSWORD = "BreakGlassTest123!"
_AD_USER_ID = "beh-ad-00000000000000000020"


@pytest.fixture
def bg_credentials(db_available):
    """Create break_glass_admin + AD test users for S-016 dual auth tests."""
    ph = bcrypt.hashpw(
        _BG_PASSWORD.encode(), bcrypt.gensalt(rounds=4)
    ).decode()

    from tests.behavioral.conftest import _run_sql

    sql = f"""
    DELETE FROM login_attempts WHERE username_or_email_hash LIKE 'beh-test-bg-%';
    DELETE FROM refresh_sessions WHERE user_id IN ('{_BG_USER_ID}', '{_AD_USER_ID}');
    DELETE FROM local_credentials WHERE user_id IN ('{_BG_USER_ID}', '{_AD_USER_ID}');
    DELETE FROM user_roles WHERE user_id IN ('{_BG_USER_ID}', '{_AD_USER_ID}');
    DELETE FROM audit_events_operational WHERE actor_user_id IN ('{_BG_USER_ID}', '{_AD_USER_ID}');
    DELETE FROM users WHERE id IN ('{_BG_USER_ID}', '{_AD_USER_ID}');
    DELETE FROM advertiser_user_memberships WHERE user_id IN ('{_BG_USER_ID}', '{_AD_USER_ID}');
    INSERT INTO users (id, code, username, email, display_name, auth_provider, status, is_break_glass)
    VALUES ('{_BG_USER_ID}', 'BEH-BG', 'beh-breakglass', 'bg@test.local',
            'Break-Glass Test Admin', 'local_break_glass', 'active', true);
    INSERT INTO local_credentials (id, user_id, credential_type, password_hash,
        password_hash_algorithm, must_change_password, status)
    VALUES ('{_BG_CRED_ID}', '{_BG_USER_ID}', 'local_break_glass',
            '{ph}', 'bcrypt', true, 'active');
    INSERT INTO user_roles (id, user_id, role_id)
    SELECT 'ur-beh-bg', '{_BG_USER_ID}', id FROM roles WHERE code='system_admin';
    INSERT INTO users (id, code, username, email, display_name, auth_provider, status)
    VALUES ('{_AD_USER_ID}', 'BEH-AD', 'beh-ad-staff', 'ad@test.local',
            'AD Test Staff', 'ad', 'active');
    INSERT INTO user_roles (id, user_id, role_id)
    SELECT 'ur-beh-ad', '{_AD_USER_ID}', id FROM roles WHERE code='system_admin';
    """
    asyncio.run(_run_sql(sql))
    yield {"user_id": _BG_USER_ID, "password": _BG_PASSWORD}

    # Cleanup
    cleanup = f"""
    DELETE FROM audit_events_operational WHERE actor_user_id IN ('{_BG_USER_ID}', '{_AD_USER_ID}');
    DELETE FROM login_attempts WHERE username_or_email_hash LIKE 'beh-test-bg-%';
    DELETE FROM refresh_sessions WHERE user_id IN ('{_BG_USER_ID}', '{_AD_USER_ID}');
    DELETE FROM local_credentials WHERE user_id IN ('{_BG_USER_ID}', '{_AD_USER_ID}');
    DELETE FROM user_roles WHERE user_id IN ('{_BG_USER_ID}', '{_AD_USER_ID}');
    DELETE FROM users WHERE id IN ('{_BG_USER_ID}', '{_AD_USER_ID}');
    """
    asyncio.run(_run_sql(cleanup))


# ---------------------------------------------------------------------------
# Tests — Dual Auth Login
# ---------------------------------------------------------------------------


class TestDualAuthLogin:
    """Both local_advertiser and local_break_glass login work."""

    def test_advertiser_login_success_and_me(self, client, test_users):
        """Advertiser user logs in, /me returns DB-backed truthful data."""
        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-advertiser",
            "password": test_users["password"],
            "auth_provider": "local_advertiser",
        })
        assert resp.status_code == 200, resp.text
        body = resp.json()
        token = body["access_token"]

        # /me returns DB-backed truthful data
        me = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert me.status_code == 200, me.text
        me_body = me.json()
        assert me_body["sub"] == test_users["advertiser"]
        assert me_body["username"] == "beh-advertiser"
        assert me_body["display_name"] == "Beh AV"
        assert me_body["auth_provider"] == "local_advertiser"
        assert len(me_body["permissions"]) > 0
        # Conftest credentials have must_change_password=False (default)
        assert me_body.get("must_change_password") is False

    def test_break_glass_login_success(self, client, bg_credentials):
        """Break-glass admin logs in successfully."""
        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-breakglass",
            "password": bg_credentials["password"],
            "auth_provider": "local_break_glass",
        })
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "Bearer"
        assert "refresh_token" not in body

    def test_break_glass_me_truthful(self, client, bg_credentials):
        """Break-glass /me returns truthful data from DB."""
        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-breakglass",
            "password": bg_credentials["password"],
            "auth_provider": "local_break_glass",
        })
        token = resp.json()["access_token"]

        me = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert me.status_code == 200, me.text
        body = me.json()
        assert body["username"] == "beh-breakglass"
        assert body["display_name"] == "Break-Glass Test Admin"
        assert "users.read" in body["permissions"]
        assert "campaigns.read" in body["permissions"]
        # bg_credentials fixture sets must_change_password=True
        assert body.get("must_change_password") is True

    def test_ad_stub_returns_503(self, client, bg_credentials):
        """AD auth provider is a stub — returns honest 503 for existing AD user."""
        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-ad-staff",
            "password": "AnyPassword123!",
            "auth_provider": "ad",
        })
        assert resp.status_code == 503, (
            f"AD stub: expected 503 SERVICE_UNAVAILABLE, got {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert body["detail"]["code"] == "SERVICE_UNAVAILABLE"
        assert "unavailable" in body["detail"]["message"].lower()


# ---------------------------------------------------------------------------
# Tests — Refresh / Logout cycle
# ---------------------------------------------------------------------------


class TestRefreshLogoutCycle:
    """Full auth cycle: login → refresh → logout."""

    def test_refresh_rotates_token(self, client, test_users):
        """Login → refresh → new access token, new cookie."""
        login = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-advertiser",
            "password": test_users["password"],
            "auth_provider": "local_advertiser",
        })
        assert login.status_code == 200
        old_cookie = login.cookies.get("refresh_token")
        assert old_cookie

        refresh = client.post("/api/v1/auth/refresh")
        assert refresh.status_code == 200, refresh.text
        body = refresh.json()
        assert "access_token" in body
        new_cookie = refresh.cookies.get("refresh_token")
        assert new_cookie and new_cookie != old_cookie

    def test_refresh_replay_protection(self, client, test_users):
        """Using the same refresh token twice → second attempt fails."""
        login = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-advertiser",
            "password": test_users["password"],
            "auth_provider": "local_advertiser",
        })
        old_cookie = login.cookies.get("refresh_token")

        # First refresh — works
        client.cookies.set("refresh_token", old_cookie)
        r1 = client.post("/api/v1/auth/refresh")
        assert r1.status_code == 200

        # Second refresh with same cookie — fails (replay)
        client.cookies.set("refresh_token", old_cookie)
        r2 = client.post("/api/v1/auth/refresh")
        assert r2.status_code == 401, f"Expected 401 for replay, got {r2.status_code}: {r2.text}"

    def test_logout_clears_session(self, client, test_users):
        """Login → access token → logout → cookie cleared."""
        login = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-advertiser",
            "password": test_users["password"],
            "auth_provider": "local_advertiser",
        })
        token = login.json()["access_token"]
        refresh_cookie = login.cookies.get("refresh_token")

        # Verify /me works before logout
        me_before = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert me_before.status_code == 200

        # Logout
        client.cookies.set("refresh_token", refresh_cookie)
        logout = client.post("/api/v1/auth/logout")
        assert logout.status_code == 200

        cleared = logout.cookies.get("refresh_token")
        assert cleared == "" or cleared is None


# ---------------------------------------------------------------------------
# Tests — Break-glass audit
# ---------------------------------------------------------------------------


class TestBreakGlassAudit:
    """Successful break-glass login writes an audit event in login_attempts."""

    def test_break_glass_login_audit_event(self, client, bg_credentials):
        """Break-glass login success → login_attempt persisted."""
        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-breakglass",
            "password": bg_credentials["password"],
            "auth_provider": "local_break_glass",
        })
        assert resp.status_code == 200

        # Verify login_attempt was recorded
        from packages.auth.repository import hash_identifier
        from tests.behavioral.test_auth_rbac_behavior import _db_login_attempts

        h = hash_identifier("beh-breakglass")
        attempts = _db_login_attempts(h)
        assert len(attempts) >= 1
        last = attempts[0]
        assert last["success"] is True
        assert last["auth_provider"] == "local_break_glass"
