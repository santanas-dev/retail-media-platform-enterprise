"""
Behavioral tests - Auth (Phase 3.4).

Tests against real PostgreSQL with actual Alembic schema.
Requires: RUN_BEHAVIORAL_TESTS=1, running PostgreSQL, migrations applied.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token


# ---------------------------------------------------------------------------
# DB helper — must be called AFTER client.post() (which fires app lifespan)
# ---------------------------------------------------------------------------


def _db_login_attempts(username_hash: str):
    """Query login_attempts via raw SQL — sync wrapper, call after TestClient use."""
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
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(
                        "SELECT success, failure_reason, auth_provider, "
                        "username_or_email_hash "
                        "FROM login_attempts "
                        "WHERE username_or_email_hash = :h "
                        "ORDER BY created_at DESC LIMIT 5"
                    ),
                    {"h": username_hash},
                )
                return [dict(row._mapping) for row in result.fetchall()]
        finally:
            await engine.dispose()

    return asyncio.run(_query())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(app, db_available, test_users):
    """Provide a TestClient with a fresh SecurityConfig."""
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


def _token(sub="u-001", auth_provider="local_advertiser"):
    return create_access_token(sub, auth_provider)


# ---------------------------------------------------------------------------
# Health - open
# ---------------------------------------------------------------------------


class TestHealthBehavioral:
    """Health endpoints must be open without any auth."""

    def test_live_returns_200(self, client):
        resp = client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Auth - login
# ---------------------------------------------------------------------------


class TestLoginBehavioral:
    """Login endpoint against real DB credentials."""

    @pytest.fixture(autouse=True)
    def setup_config(self):
        reset_security_config()

    def test_advertiser_login_success(self, client, user_ids):
        """Advertiser user with correct password gets access_token + cookie."""
        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-advertiser",
            "password": user_ids["password"],
            "auth_provider": "local_advertiser",
        })
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "Bearer"
        assert body["expires_in"] > 0
        assert "refresh_token" not in body
        # Cookie must be set
        assert "refresh_token" in resp.cookies

    def test_wrong_password_returns_401(self, client, user_ids):
        """Wrong password -> generic 401, login_attempt persisted in DB."""
        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-advertiser",
            "password": "WrongPassword!",
            "auth_provider": "local_advertiser",
        })
        assert resp.status_code == 401, resp.text
        body = resp.json()
        assert body["detail"]["code"] == "INVALID_CREDENTIALS"
        # No cookie on failure
        assert "refresh_token" not in resp.cookies

        # Verify login_attempt row was actually persisted.
        # Query AFTER client.post() — app lifespan fires on first request.
        from packages.auth.repository import hash_identifier

        attempts = _db_login_attempts(hash_identifier("beh-advertiser"))
        assert len(attempts) >= 1, "Expected at least one login_attempt row"
        last = attempts[0]
        assert last["success"] is False
        assert last["failure_reason"] == "wrong_password"
        assert last["auth_provider"] == "local_advertiser"

    def test_unknown_user_returns_401(self, client):
        """Unknown username -> generic 401, login_attempt with hashed identifier."""
        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "nonexistent-user",
            "password": "AnyPassword123!",
            "auth_provider": "local_advertiser",
        })
        assert resp.status_code == 401, resp.text
        body = resp.json()
        assert body["detail"]["code"] == "INVALID_CREDENTIALS"
        # Must not reveal "user not found"
        assert "not found" not in str(body).lower()

        # Verify login_attempt row was persisted with hashed identifier
        from packages.auth.repository import hash_identifier

        expected_hash = hash_identifier("nonexistent-user")
        attempts = _db_login_attempts(expected_hash)
        assert len(attempts) >= 1, "Expected at least one login_attempt row"
        last = attempts[0]
        assert last["success"] is False
        assert last["failure_reason"] == "user_not_found"
        assert last["auth_provider"] == "unknown"
        # Raw email/username MUST NOT be stored — hash only
        stored = last["username_or_email_hash"].lower()
        assert "nonexistent-user" not in stored
        assert "@" not in stored


# ---------------------------------------------------------------------------
# Auth - refresh
# ---------------------------------------------------------------------------


class TestRefreshBehavioral:
    """Refresh token rotation with real DB."""

    def test_refresh_rotates_token(self, client, user_ids):
        """Login -> extract refresh cookie -> refresh -> new cookie."""
        # Login — cookie is stored automatically by TestClient
        login_resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-advertiser",
            "password": user_ids["password"],
            "auth_provider": "local_advertiser",
        })
        assert login_resp.status_code == 200
        old_cookie = login_resp.cookies.get("refresh_token")
        assert old_cookie

        # Cookie from login is already in client.cookies
        refresh_resp = client.post("/api/v1/auth/refresh")
        assert refresh_resp.status_code == 200, refresh_resp.text
        body = refresh_resp.json()
        assert "access_token" in body
        assert "refresh_token" not in body

        new_cookie = refresh_resp.cookies.get("refresh_token")
        assert new_cookie
        assert new_cookie != old_cookie


# ---------------------------------------------------------------------------
# Auth - logout
# ---------------------------------------------------------------------------


class TestLogoutBehavioral:
    """Logout with real DB."""

    def test_logout_revokes_and_clears(self, client, user_ids):
        """Login -> logout -> cookie cleared."""
        login_resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-advertiser",
            "password": user_ids["password"],
            "auth_provider": "local_advertiser",
        })
        assert login_resp.status_code == 200
        refresh_token = login_resp.cookies.get("refresh_token")
        assert refresh_token

        client.cookies.set("refresh_token", refresh_token)
        logout_resp = client.post("/api/v1/auth/logout")
        assert logout_resp.status_code == 200
        assert logout_resp.json()["message"] == "Logged out"
        # Cookie should be cleared (empty or expired)
        cleared = logout_resp.cookies.get("refresh_token")
        assert cleared == "" or cleared is None


# ---------------------------------------------------------------------------
# RBAC - identity endpoints
# ---------------------------------------------------------------------------


class TestRBACBehavioral:
    """RBAC enforcement with real DB users and permissions."""

    def test_missing_token_returns_401(self, client):
        """No token on identity endpoint -> 401."""
        resp = client.get("/api/v1/identity/users")
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "NOT_AUTHENTICATED"

    def test_garbage_token_returns_401(self, client):
        """Garbage token -> 401."""
        resp = client.get(
            "/api/v1/identity/users",
            headers=_auth("not.a.real.jwt"),
        )
        assert resp.status_code == 401

    def test_no_permission_returns_403(self, client, user_ids):
        """User with role but no permissions -> 403."""
        token = _token(user_ids["noperms"])
        resp = client.get(
            "/api/v1/identity/users",
            headers=_auth(token),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "PERMISSION_DENIED"

    def test_with_permission_returns_200(self, client, user_ids):
        """User with users.read -> 200."""
        token = _token(user_ids["readonly"])
        resp = client.get(
            "/api/v1/identity/users",
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_disabled_user_returns_403(self, client, user_ids):
        """Disabled user with valid JWT -> 403."""
        token = _token(user_ids["disabled"])
        resp = client.get(
            "/api/v1/identity/users",
            headers=_auth(token),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "USER_DISABLED"

    def test_deny_by_default_empty_permissions(self, client, user_ids):
        """User with role but role has no permissions -> 403 on all endpoints."""
        token = _token(user_ids["noperms"])
        endpoints = [
            "/api/v1/identity/users",
            "/api/v1/identity/roles",
            "/api/v1/identity/permissions",
            "/api/v1/identity/audit-events",
        ]
        for ep in endpoints:
            resp = client.get(ep, headers=_auth(token))
            assert resp.status_code == 403, f"Expected 403 on {ep}, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Auth - login rate limiting (ADR-006 §8)
# ---------------------------------------------------------------------------


class TestLoginRateLimitBehavioral:
    """Login rate limiting — real DB, real login attempts."""

    RATE_LIMIT_USER = "beh-ratelimit-test-user"
    RATE_LIMIT_ALT_USER = "beh-ratelimit-other-user"

    @pytest.fixture(autouse=True)
    def setup_config(self):
        reset_security_config()

    def test_five_wrong_then_429(self, client):
        """5 wrong attempts → 401 each, 6th → 429."""
        for i in range(5):
            resp = client.post("/api/v1/auth/login", json={
                "username_or_email": self.RATE_LIMIT_USER,
                "password": f"WrongPassword{i}!",
                "auth_provider": "local_advertiser",
            })
            assert resp.status_code == 401, (
                f"Attempt {i+1}: expected 401, got {resp.status_code}: {resp.text}"
            )

        # 6th attempt → rate limited
        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": self.RATE_LIMIT_USER,
            "password": "WrongPassword5!",
            "auth_provider": "local_advertiser",
        })
        assert resp.status_code == 429, (
            f"6th attempt: expected 429, got {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert body["detail"]["code"] == "TOO_MANY_REQUESTS"

    def test_different_username_not_blocked(self, client):
        """Rate limit for user-A does not block user-B."""
        # Rate-limit user A
        for _ in range(5):
            client.post("/api/v1/auth/login", json={
                "username_or_email": self.RATE_LIMIT_USER,
                "password": "WrongPassword!",
                "auth_provider": "local_advertiser",
            })
        # Verify A is rate-limited
        resp_a = client.post("/api/v1/auth/login", json={
            "username_or_email": self.RATE_LIMIT_USER,
            "password": "WrongPassword!",
            "auth_provider": "local_advertiser",
        })
        assert resp_a.status_code == 429

        # User B — still gets 401 (wrong password, not rate-limited)
        resp_b = client.post("/api/v1/auth/login", json={
            "username_or_email": self.RATE_LIMIT_ALT_USER,
            "password": "WrongPassword!",
            "auth_provider": "local_advertiser",
        })
        assert resp_b.status_code == 401, (
            f"User B: expected 401, got {resp_b.status_code}: {resp_b.text}"
        )

    def test_rate_limited_attempts_persisted(self, client):
        """Rate-limited attempts appear in login_attempts."""
        # Exhaust rate limit
        for _ in range(5):
            client.post("/api/v1/auth/login", json={
                "username_or_email": self.RATE_LIMIT_USER,
                "password": "WrongPassword!",
                "auth_provider": "local_advertiser",
            })
        # 6th — rate-limited
        client.post("/api/v1/auth/login", json={
            "username_or_email": self.RATE_LIMIT_USER,
            "password": "WrongPassword!",
            "auth_provider": "local_advertiser",
        })

        from packages.auth.repository import hash_identifier

        h = hash_identifier(self.RATE_LIMIT_USER)
        attempts = _db_login_attempts(h)
        assert len(attempts) >= 6, f"Expected ≥6 attempts, got {len(attempts)}"
        # Last attempt should be rate-limited
        last = attempts[0]
        assert last["success"] is False
        assert last["failure_reason"] == "rate_limited"

    def test_no_enumeration_on_rate_limit(self, client):
        """429 response is generic — no user enumeration."""
        # Rate-limit with a completely unknown username
        for _ in range(5):
            client.post("/api/v1/auth/login", json={
                "username_or_email": "totally-unknown-user-xyz",
                "password": "WrongPassword!",
                "auth_provider": "local_advertiser",
            })
        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "totally-unknown-user-xyz",
            "password": "WrongPassword!",
            "auth_provider": "local_advertiser",
        })
        assert resp.status_code == 429
        body = resp.json()
        assert body["detail"]["code"] == "TOO_MANY_REQUESTS"
        # Must not reveal whether user exists
        assert "not found" not in str(body).lower()
        assert "unknown" not in str(body).lower()
