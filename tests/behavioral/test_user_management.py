"""
Behavioral tests - S-033 Admin User Management (Phase 3.4+).

Tests against real PostgreSQL with actual Alembic schema.
Requires: RUN_BEHAVIORAL_TESTS=1, running PostgreSQL, migrations applied.
"""

import pytest
from fastapi.testclient import TestClient

from packages.security.config import reset_security_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# S-033 — Create scoped advertiser user
# ---------------------------------------------------------------------------


class TestCreateAdvertiserUserBehavioral:
    """Admin creates a local advertiser user scoped to ADV-001."""

    ADV_001_ID = "00000000-0000-0000-0000-000000000200"

    def test_admin_creates_advertiser_user(self, app, test_users):
        """Admin creates local advertiser user → 201, one_time_password returned."""
        reset_security_config()
        client = TestClient(app)

        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-readonly",
            "password": test_users["password"],
            "auth_provider": "local_advertiser",
        })
        assert resp.status_code == 200, resp.text
        admin_jwt = resp.json()["access_token"]

        username = "beh-test-av-new"
        resp = client.post(
            "/api/v1/identity/users/local-advertiser",
            json={
                "username": username,
                "display_name": "Beh Test Advertiser New",
                "advertiser_organization_id": self.ADV_001_ID,
                "auto_generate_password": True,
                "must_change_password": False,
                "is_active": True,
            },
            headers=_auth(admin_jwt),
        )
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        body = resp.json()
        assert body["username"] == username
        assert "one_time_password" in body
        assert body["one_time_password"] is not None
        assert len(body["one_time_password"]) >= 16
        assert "password_hash" not in body

    def test_duplicate_username_returns_409(self, app, test_users):
        """Duplicate username → 409."""
        reset_security_config()
        client = TestClient(app)

        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-readonly",
            "password": test_users["password"],
            "auth_provider": "local_advertiser",
        })
        admin_jwt = resp.json()["access_token"]

        resp = client.post(
            "/api/v1/identity/users/local-advertiser",
            json={
                "username": "beh-advertiser",
                "display_name": "Dup",
                "advertiser_organization_id": self.ADV_001_ID,
                "auto_generate_password": True,
            },
            headers=_auth(admin_jwt),
        )
        assert resp.status_code == 409

    def test_created_user_can_login(self, app, test_users):
        """Created user can login with one-time password, /me returns correct data."""
        reset_security_config()
        client = TestClient(app)

        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-readonly",
            "password": test_users["password"],
            "auth_provider": "local_advertiser",
        })
        admin_jwt = resp.json()["access_token"]

        username = "beh-test-av-login"
        create_resp = client.post(
            "/api/v1/identity/users/local-advertiser",
            json={
                "username": username,
                "display_name": "Beh Login Test",
                "advertiser_organization_id": self.ADV_001_ID,
                "auto_generate_password": True,
                "must_change_password": False,
                "is_active": True,
            },
            headers=_auth(admin_jwt),
        )
        assert create_resp.status_code == 201, create_resp.text
        otp = create_resp.json()["one_time_password"]

        login_resp = client.post("/api/v1/auth/login", json={
            "username_or_email": username,
            "password": otp,
            "auth_provider": "local_advertiser",
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        user_jwt = login_resp.json()["access_token"]

        me_resp = client.get("/api/v1/auth/me", headers=_auth(user_jwt))
        assert me_resp.status_code == 200, me_resp.text
        me = me_resp.json()
        assert me["username"] == username
        assert me["display_name"] == "Beh Login Test"
        assert me["auth_provider"] == "local_advertiser"


# ---------------------------------------------------------------------------
# S-033 — Scope enforcement
# ---------------------------------------------------------------------------


class TestAdvertiserScopeBehavioral:
    """Created advertiser user is scoped to ADV-001 only."""

    ADV_001_ID = "00000000-0000-0000-0000-000000000200"

    def test_cross_org_cannot_access_other_advertiser(self, app, test_users):
        """Created ADV-001 user can only see ADV-001 campaigns."""
        reset_security_config()
        client = TestClient(app)

        username = "beh-test-scope-xorg"
        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-readonly",
            "password": test_users["password"],
            "auth_provider": "local_advertiser",
        })
        admin_jwt = resp.json()["access_token"]

        create_resp = client.post(
            "/api/v1/identity/users/local-advertiser",
            json={
                "username": username,
                "display_name": "Beh Scope Cross-Org",
                "advertiser_organization_id": self.ADV_001_ID,
                "auto_generate_password": True,
                "must_change_password": False,
                "is_active": True,
            },
            headers=_auth(admin_jwt),
        )
        assert create_resp.status_code == 201, create_resp.text
        otp = create_resp.json()["one_time_password"]

        login_resp = client.post("/api/v1/auth/login", json={
            "username_or_email": username,
            "password": otp,
            "auth_provider": "local_advertiser",
        })
        user_jwt = login_resp.json()["access_token"]

        campaigns_resp = client.get(
            "/api/v1/identity/campaigns?limit=50",
            headers=_auth(user_jwt),
        )
        assert campaigns_resp.status_code == 200, (
            f"Expected 200, got {campaigns_resp.status_code}: {campaigns_resp.text}"
        )
        body = campaigns_resp.json()
        # ListCampaigns returns a list (legacy) or {"items": [...]}
        items = body if isinstance(body, list) else body.get("items", [])
        for item in items:
            org_id = item.get("advertiser_organization_id", "")
            assert org_id == self.ADV_001_ID, (
                f"Scoped user saw campaign from org {org_id}, expected {self.ADV_001_ID}"
            )

    def test_advertiser_cannot_call_user_management(self, app, test_users):
        """Advertiser user cannot access GET /users."""
        reset_security_config()
        client = TestClient(app)

        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-advertiser",
            "password": test_users["password"],
            "auth_provider": "local_advertiser",
        })
        user_jwt = resp.json()["access_token"]

        resp = client.get("/api/v1/identity/users", headers=_auth(user_jwt))
        assert resp.status_code == 403, (
            f"Expected 403, got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# S-033 — Reset password
# ---------------------------------------------------------------------------


class TestResetPasswordBehavioral:
    """Admin reset password → old session revoked, new password works."""

    ADV_001_ID = "00000000-0000-0000-0000-000000000200"

    def test_reset_password_revokes_old_session(self, app, test_users):
        """After reset, old refresh token is invalid, new password works."""
        reset_security_config()
        client = TestClient(app)

        username = "beh-test-reset-sess"
        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-readonly",
            "password": test_users["password"],
            "auth_provider": "local_advertiser",
        })
        admin_jwt = resp.json()["access_token"]

        create_resp = client.post(
            "/api/v1/identity/users/local-advertiser",
            json={
                "username": username,
                "display_name": "Beh Reset Session",
                "advertiser_organization_id": self.ADV_001_ID,
                "auto_generate_password": True,
                "must_change_password": False,
                "is_active": True,
            },
            headers=_auth(admin_jwt),
        )
        assert create_resp.status_code == 201, create_resp.text
        old_otp = create_resp.json()["one_time_password"]

        login_resp = client.post("/api/v1/auth/login", json={
            "username_or_email": username,
            "password": old_otp,
            "auth_provider": "local_advertiser",
        })
        assert login_resp.status_code == 200
        old_cookie = login_resp.cookies.get("refresh_token")
        assert old_cookie

        user_id = create_resp.json()["user_id"]
        reset_resp = client.post(
            f"/api/v1/identity/users/{user_id}/reset-password",
            json={"auto_generate_password": True, "revoke_sessions": True},
            headers=_auth(admin_jwt),
        )
        assert reset_resp.status_code == 200, reset_resp.text
        body = reset_resp.json()
        assert body["must_change_password"] is True
        new_otp = body["one_time_password"]

        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": old_cookie},
        )
        assert refresh_resp.status_code in (401, 403), (
            f"Expected 401/403 after session revoke, got {refresh_resp.status_code}"
        )

        login2 = client.post("/api/v1/auth/login", json={
            "username_or_email": username,
            "password": new_otp,
            "auth_provider": "local_advertiser",
        })
        assert login2.status_code == 200, (
            f"Login with new password failed: {login2.text}"
        )


# ---------------------------------------------------------------------------
# S-033 — Deactivate / Reactivate
# ---------------------------------------------------------------------------


class TestDeactivateReactivateBehavioral:
    """Admin deactivates → login blocked. Admin reactivates → login works."""

    ADV_001_ID = "00000000-0000-0000-0000-000000000200"

    def test_deactivate_blocks_login(self, app, test_users):
        """Deactivated user cannot login."""
        reset_security_config()
        client = TestClient(app)

        username = "beh-test-deact"
        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-readonly",
            "password": test_users["password"],
            "auth_provider": "local_advertiser",
        })
        admin_jwt = resp.json()["access_token"]

        create_resp = client.post(
            "/api/v1/identity/users/local-advertiser",
            json={
                "username": username,
                "display_name": "Beh Deact",
                "advertiser_organization_id": self.ADV_001_ID,
                "auto_generate_password": True,
                "must_change_password": False,
                "is_active": True,
            },
            headers=_auth(admin_jwt),
        )
        assert create_resp.status_code == 201, create_resp.text
        otp = create_resp.json()["one_time_password"]
        user_id = create_resp.json()["user_id"]

        login1 = client.post("/api/v1/auth/login", json={
            "username_or_email": username,
            "password": otp,
            "auth_provider": "local_advertiser",
        })
        assert login1.status_code == 200, f"Pre-deact login failed: {login1.text}"

        deact_resp = client.post(
            f"/api/v1/identity/users/{user_id}/deactivate",
            headers=_auth(admin_jwt),
        )
        assert deact_resp.status_code == 200, (
            f"Deactivate failed: {deact_resp.text}"
        )
        assert deact_resp.json()["status"] == "inactive"

        login2 = client.post("/api/v1/auth/login", json={
            "username_or_email": username,
            "password": otp,
            "auth_provider": "local_advertiser",
        })
        assert login2.status_code in (401, 403), (
            f"Expected 401/403 after deactivate, got {login2.status_code}"
        )

    def test_reactivate_restores_login(self, app, test_users):
        """Reactivated user can login again."""
        reset_security_config()
        client = TestClient(app)

        username = "beh-test-react"
        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-readonly",
            "password": test_users["password"],
            "auth_provider": "local_advertiser",
        })
        admin_jwt = resp.json()["access_token"]

        create_resp = client.post(
            "/api/v1/identity/users/local-advertiser",
            json={
                "username": username,
                "display_name": "Beh React",
                "advertiser_organization_id": self.ADV_001_ID,
                "auto_generate_password": True,
                "must_change_password": False,
                "is_active": True,
            },
            headers=_auth(admin_jwt),
        )
        assert create_resp.status_code == 201, create_resp.text
        otp = create_resp.json()["one_time_password"]
        user_id = create_resp.json()["user_id"]

        client.post(
            f"/api/v1/identity/users/{user_id}/deactivate",
            headers=_auth(admin_jwt),
        )

        act_resp = client.post(
            f"/api/v1/identity/users/{user_id}/activate",
            headers=_auth(admin_jwt),
        )
        assert act_resp.status_code == 200, f"Activate failed: {act_resp.text}"
        assert act_resp.json()["status"] == "active"

        login_resp = client.post("/api/v1/auth/login", json={
            "username_or_email": username,
            "password": otp,
            "auth_provider": "local_advertiser",
        })
        assert login_resp.status_code == 200, (
            f"Post-reactivate login failed: {login_resp.text}"
        )


# ---------------------------------------------------------------------------
# S-033 — Response safety
# ---------------------------------------------------------------------------


class TestUserManagementResponseSafety:
    """No secrets leaked in user management responses."""

    ADV_001_ID = "00000000-0000-0000-0000-000000000200"

    def test_create_response_no_hash(self, app, test_users):
        """Create response has no password_hash."""
        reset_security_config()
        client = TestClient(app)

        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-readonly",
            "password": test_users["password"],
            "auth_provider": "local_advertiser",
        })
        admin_jwt = resp.json()["access_token"]

        create_resp = client.post(
            "/api/v1/identity/users/local-advertiser",
            json={
                "username": "beh-test-safety",
                "display_name": "Beh Safety",
                "advertiser_organization_id": self.ADV_001_ID,
                "auto_generate_password": True,
                "must_change_password": False,
                "is_active": True,
            },
            headers=_auth(admin_jwt),
        )
        assert create_resp.status_code == 201, create_resp.text
        body = create_resp.json()
        assert "password_hash" not in body
        assert "password" not in body

    def test_list_users_no_secrets(self, app, test_users):
        """GET /users list must not leak password_hash on any user."""
        reset_security_config()
        client = TestClient(app)

        resp = client.post("/api/v1/auth/login", json={
            "username_or_email": "beh-readonly",
            "password": test_users["password"],
            "auth_provider": "local_advertiser",
        })
        admin_jwt = resp.json()["access_token"]

        users_resp = client.get(
            "/api/v1/identity/users?limit=50",
            headers=_auth(admin_jwt),
        )
        assert users_resp.status_code == 200, users_resp.text
        body = users_resp.json()
        for user in body.get("items", []):
            assert "password_hash" not in user, (
                f"User {user.get('username')} leaked password_hash"
            )
            assert "password" not in user
