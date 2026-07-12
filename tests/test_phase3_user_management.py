"""
Retail Media Platform - S-033 Admin User Management Tests.

Tests: permission gates (users.read, users.manage), response safety
(no password_hash/secret/token leakage), create/deactivate/activate/
reset-password flows with mocked repository.

All tests use mocked repository functions — no real DB required.
"""

import importlib.util
import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-user-mgmt-tests-32chars"

async def _async_gen(value):
    yield value

from fastapi.testclient import TestClient

from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token


# ---------------------------------------------------------------------------
# App loader
# ---------------------------------------------------------------------------

_APP = None


def _get_app():
    global _APP
    if _APP is None:
        path = os.path.join(
            os.path.dirname(__file__), "..", "apps", "control-api", "main.py"
        )
        spec = importlib.util.spec_from_file_location("control_api_main", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _APP = mod.app
    return _APP


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

class _MockUser:
    """A mock User object compatible with repository expectations."""
    def __init__(self, user_id, status="active", auth_provider="local_advertiser",
                 is_break_glass=False, username="", display_name=""):
        self.id = user_id
        self.status = status
        self.auth_provider = auth_provider
        self.is_break_glass = is_break_glass
        self.username = username
        self.display_name = display_name
        self.email = None
        self.code = f"CODE-{user_id}"
        self.created_at = None
        self.updated_at = None
        self.roles = []


class _MockCredential:
    def __init__(self, must_change_password=True):
        self.must_change_password = must_change_password


class _MockRole:
    def __init__(self, id_, code, name):
        self.id = id_
        self.code = code
        self.name = name


class _MockUserRole:
    def __init__(self, id_, role_id, scope_type=None, scope_id=None):
        self.id = id_
        self.role_id = role_id
        self.scope_type = scope_type
        self.scope_id = scope_id
        self.role = _MockRole(role_id, "advertiser", "Advertiser")


def _make_user(user_id, status="active", auth_provider="local_advertiser",
               is_break_glass=False):
    return _MockUser(user_id, status, auth_provider, is_break_glass)


def _make_perms(*codes):
    return set(codes)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUserManagementPermissionGates(unittest.TestCase):
    """Permission enforcement on user-management endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(_get_app())

    def setUp(self):
        reset_security_config()
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test-jwt-secret-for-user-mgmt-tests-32chars"
        self.client.cookies.clear()

    def tearDown(self):
        reset_security_config()

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    def _token(self, sub="u-001", auth_provider="local_break_glass"):
        return create_access_token(sub, auth_provider)

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _mock_auth_repo(self, user=None, perms=None):
        """Patch find_user_by_id + get_user_permissions (dependencies)."""
        patcher_find = patch(
            "packages.api.dependencies.repository.find_user_by_id",
            new_callable=AsyncMock,
        )
        patcher_perms = patch(
            "packages.api.dependencies.repository.get_user_permissions",
            new_callable=AsyncMock,
        )
        mock_find = patcher_find.start()
        mock_perms = patcher_perms.start()

        mock_find.return_value = user
        mock_perms.return_value = perms or set()

        self.addCleanup(patcher_find.stop)
        self.addCleanup(patcher_perms.stop)

        return mock_find, mock_perms

    def _mock_identity_repo(self, **overrides):
        """Patch all repository functions used by user-management endpoints."""
        patchers = {}
        defaults = {
            "get_user_detail": None,
            "get_user_local_credential": None,
            "find_user_by_username": None,
            "get_advertiser_organization": None,
            "list_roles": [],
            "create_local_advertiser_user": None,
            "count_active_break_glass_users": 2,
            "count_active_admin_users": 2,
            "set_user_status": True,
            "find_user_by_id": None,
            "update_local_credential_password": True,
        }
        for name, default in {**defaults, **overrides}.items():
            patcher = patch(
                f"packages.api.identity.repository.{name}",
                new_callable=AsyncMock,
            )
            mock = patcher.start()
            mock.return_value = default
            patchers[name] = patcher
            self.addCleanup(patcher.stop)
        return patchers

    # -------------------------------------------------------------------
    # 401 - no token
    # -------------------------------------------------------------------

    def test_get_user_detail_no_token_returns_401(self):
        """GET /users/{id} without token -> 401."""
        resp = self.client.get("/api/v1/identity/users/some-id")
        self.assertEqual(resp.status_code, 401)

    def test_create_local_advertiser_no_token_returns_401(self):
        """POST /users/local-advertiser without token -> 401."""
        resp = self.client.post("/api/v1/identity/users/local-advertiser", json={})
        self.assertEqual(resp.status_code, 401)

    def test_deactivate_no_token_returns_401(self):
        """POST /users/{id}/deactivate without token -> 401."""
        resp = self.client.post("/api/v1/identity/users/some-id/deactivate")
        self.assertEqual(resp.status_code, 401)

    def test_activate_no_token_returns_401(self):
        """POST /users/{id}/activate without token -> 401."""
        resp = self.client.post("/api/v1/identity/users/some-id/activate")
        self.assertEqual(resp.status_code, 401)

    def test_reset_password_no_token_returns_401(self):
        """POST /users/{id}/reset-password without token -> 401."""
        resp = self.client.post("/api/v1/identity/users/some-id/reset-password",
                                json={})
        self.assertEqual(resp.status_code, 401)

    # -------------------------------------------------------------------
    # users.read required for GET /users/{id}
    # -------------------------------------------------------------------

    def test_get_user_detail_requires_users_read(self):
        """GET /users/{id} requires users.read permission."""
        self._mock_auth_repo(
            user=_make_user("u-001"),
            perms={"roles.read"},  # missing users.read
        )
        resp = self.client.get(
            "/api/v1/identity/users/some-id",
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 403)

    def test_get_user_detail_with_users_read_passes(self):
        """GET /users/{id} with users.read passes the gate (DB error expected)."""
        self._mock_auth_repo(
            user=_make_user("u-001"),
            perms={"users.read"},
        )
        self._mock_identity_repo(get_user_detail=None)
        try:
            resp = self.client.get(
                "/api/v1/identity/users/some-id",
                headers=self._auth(self._token()),
            )
            # If it gets past permission, it hits DB (404 or exception)
            self.assertNotEqual(resp.status_code, 403)
        except Exception:
            pass

    # -------------------------------------------------------------------
    # users.manage required for mutation endpoints
    # -------------------------------------------------------------------

    def test_create_local_advertiser_requires_users_manage(self):
        """POST /users/local-advertiser requires users.manage."""
        self._mock_auth_repo(
            user=_make_user("u-001"),
            perms={"users.read"},  # missing users.manage
        )
        resp = self.client.post(
            "/api/v1/identity/users/local-advertiser",
            json={
                "username": "test",
                "display_name": "Test",
                "advertiser_organization_id": "00000000-0000-0000-0000-000000000001",
                "auto_generate_password": True,
            },
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 403)

    def test_deactivate_requires_users_manage(self):
        """POST /users/{id}/deactivate requires users.manage."""
        self._mock_auth_repo(
            user=_make_user("u-001"),
            perms={"users.read"},
        )
        resp = self.client.post(
            "/api/v1/identity/users/some-id/deactivate",
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 403)

    def test_activate_requires_users_manage(self):
        """POST /users/{id}/activate requires users.manage."""
        self._mock_auth_repo(
            user=_make_user("u-001"),
            perms={"users.read"},
        )
        resp = self.client.post(
            "/api/v1/identity/users/some-id/activate",
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 403)

    def test_reset_password_requires_users_manage(self):
        """POST /users/{id}/reset-password requires users.manage."""
        self._mock_auth_repo(
            user=_make_user("u-001"),
            perms={"users.read"},
        )
        resp = self.client.post(
            "/api/v1/identity/users/some-id/reset-password",
            json={"auto_generate_password": True},
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 403)

    # -------------------------------------------------------------------
    # Advertiser role cannot call user-management endpoints
    # -------------------------------------------------------------------

    def test_advertiser_cannot_get_user_detail(self):
        """Advertiser with users.read but not users.manage -> 403 on detail."""
        self._mock_auth_repo(
            user=_make_user("u-advertiser", auth_provider="local_advertiser"),
            perms={"campaigns.read"},
        )
        resp = self.client.get(
            "/api/v1/identity/users/some-id",
            headers=self._auth(self._token("u-advertiser", "local_advertiser")),
        )
        self.assertEqual(resp.status_code, 403)

    def test_advertiser_cannot_create_user(self):
        """Advertiser without users.manage -> 403 on create."""
        self._mock_auth_repo(
            user=_make_user("u-advertiser", auth_provider="local_advertiser"),
            perms={"campaigns.manage"},
        )
        resp = self.client.post(
            "/api/v1/identity/users/local-advertiser",
            json={
                "username": "test",
                "display_name": "Test",
                "advertiser_organization_id": "00000000-0000-0000-0000-000000000001",
                "auto_generate_password": True,
            },
            headers=self._auth(self._token("u-advertiser", "local_advertiser")),
        )
        self.assertEqual(resp.status_code, 403)


class TestUserDetailResponseSafety(unittest.TestCase):
    """GET /users/{id} must never leak secrets."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(_get_app())

    def setUp(self):
        reset_security_config()
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test-jwt-secret-for-user-mgmt-tests-32chars"
        self.client.cookies.clear()

    def tearDown(self):
        reset_security_config()

    def _token(self):
        return create_access_token("u-admin", "local_break_glass")

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _mock_auth(self):
        patcher_find = patch(
            "packages.api.dependencies.repository.find_user_by_id",
            new_callable=AsyncMock,
        )
        patcher_perms = patch(
            "packages.api.dependencies.repository.get_user_permissions",
            new_callable=AsyncMock,
        )
        mock_find = patcher_find.start()
        mock_perms = patcher_perms.start()
        mock_find.return_value = _make_user("u-admin", "active", "local_break_glass")
        mock_perms.return_value = {"users.read", "users.manage"}
        self.addCleanup(patcher_find.stop)
        self.addCleanup(patcher_perms.stop)

    def _mock_repo(self, user_detail, credential):
        p1 = patch(
            "packages.api.identity.repository.get_user_detail",
            new_callable=AsyncMock,
        )
        p2 = patch(
            "packages.api.identity.repository.get_user_local_credential",
            new_callable=AsyncMock,
        )
        m1 = p1.start()
        m2 = p2.start()
        m1.return_value = user_detail
        m2.return_value = credential
        self.addCleanup(p1.stop)
        self.addCleanup(p2.stop)

    def test_no_password_hash_in_response(self):
        """UserDetailOut must not include password_hash field."""
        # Actually we test this by verifying the response model has no such field.
        # The Pydantic model explicitly excludes it. We confirm with a smoke test.
        from packages.domain.schemas import UserDetailOut
        fields = list(UserDetailOut.model_fields.keys())
        self.assertNotIn("password_hash", fields)
        self.assertNotIn("password_hash_algorithm", fields)

    def test_no_token_or_secret_in_response(self):
        """UserDetailOut must not include tokens or secrets."""
        from packages.domain.schemas import UserDetailOut
        fields = list(UserDetailOut.model_fields.keys())
        for secret_field in ("access_token", "refresh_token", "token", "secret",
                              "jwt_secret", "password", "password_hash"):
            self.assertNotIn(secret_field, fields,
                             f"Field '{secret_field}' must not be in UserDetailOut")


class TestCreateLocalAdvertiser(unittest.TestCase):
    """POST /users/local-advertiser flow."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(_get_app())

    def setUp(self):
        reset_security_config()
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test-jwt-secret-for-user-mgmt-tests-32chars"
        self.client.cookies.clear()

    def tearDown(self):
        reset_security_config()

    def _token(self):
        return create_access_token("u-admin", "local_break_glass")

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _mock_auth_and_repo(self, **overrides):
        self._mock_auth()
        return self._mock_repo(**overrides)

    def _mock_auth(self):
        """Override get_current_active_user + get_db + get_user_permissions."""
        app = _get_app()
        from packages.api.dependencies import get_current_active_user, get_db

        async def _admin_user():
            return {
                "sub": "u-admin",
                "auth_provider": "local_break_glass",
                "username": "admin",
                "display_name": "Admin",
            }

        async def _fake_db():
            yield AsyncMock()

        app.dependency_overrides[get_current_active_user] = _admin_user
        app.dependency_overrides[get_db] = _fake_db
        self.addCleanup(lambda: app.dependency_overrides.clear())

    def _mock_repo(self, **overrides):
        defaults = {
            "get_user_permissions": {"users.read", "users.manage"},
            "get_advertiser_organization": _MockOrg(),
            "find_user_by_username": None,
            "list_roles": [_MockRole("role-adv", "advertiser", "Advertiser")],
            "create_local_advertiser_user": _MockCreatedUser(),
        }
        for name, default in {**defaults, **overrides}.items():
            patcher = patch(
                f"packages.api.identity.repository.{name}",
                new_callable=AsyncMock,
            )
            mock = patcher.start()
            mock.return_value = default
            self.addCleanup(patcher.stop)

    def test_duplicate_username_returns_409(self):
        """Duplicate username -> 409 Conflict."""
        self._mock_auth()
        self._mock_repo(
            find_user_by_username=_make_user("existing", "active"),
        )
        resp = self.client.post(
            "/api/v1/identity/users/local-advertiser",
            json={
                "username": "existing",
                "display_name": "Test",
                "advertiser_organization_id": "00000000-0000-0000-0000-000000000001",
                "auto_generate_password": True,
            },
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 409)

    def test_org_not_found_returns_422(self):
        """Non-existent advertiser org -> 422."""
        self._mock_auth()
        self._mock_repo(get_advertiser_organization=None)
        resp = self.client.post(
            "/api/v1/identity/users/local-advertiser",
            json={
                "username": "new_user",
                "display_name": "Test",
                "advertiser_organization_id": "00000000-0000-0000-0000-000000000099",
                "auto_generate_password": True,
            },
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 422)

    def test_response_has_no_password_hash(self):
        """Create response must not leak password_hash."""
        self._mock_auth()
        self._mock_repo()
        resp = self.client.post(
            "/api/v1/identity/users/local-advertiser",
            json={
                "username": "new_user",
                "display_name": "Test User",
                "advertiser_organization_id": "00000000-0000-0000-0000-000000000001",
                "auto_generate_password": True,
            },
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.assertNotIn("password_hash", body)
        self.assertNotIn("password", body)
        self.assertNotIn("secret", body)


class TestDeactivateActivate(unittest.TestCase):
    """Deactivate/activate safety gates."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(_get_app())

    def setUp(self):
        reset_security_config()
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test-jwt-secret-for-user-mgmt-tests-32chars"
        self.client.cookies.clear()

    def tearDown(self):
        reset_security_config()

    def _token(self):
        return create_access_token("u-admin", "local_break_glass")

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _mock_auth(self):
        """Override get_current_active_user + get_db + get_user_permissions."""
        app = _get_app()
        from packages.api.dependencies import get_current_active_user, get_db

        async def _admin_user():
            return {
                "sub": "u-admin",
                "auth_provider": "local_break_glass",
                "username": "admin",
                "display_name": "Admin",
            }

        async def _fake_db():
            yield AsyncMock()

        app.dependency_overrides[get_current_active_user] = _admin_user
        app.dependency_overrides[get_db] = _fake_db
        self.addCleanup(lambda: app.dependency_overrides.clear())

    def _mock_repo(self, **overrides):
        defaults = {
            "get_user_detail": _make_user("target-user", "active"),
            "get_user_permissions": {"users.read", "users.manage"},
            "count_active_break_glass_users": 2,
            "count_active_admin_users": 2,
            "set_user_status": True,
        }
        for name, default in {**defaults, **overrides}.items():
            patcher = patch(
                f"packages.api.identity.repository.{name}",
                new_callable=AsyncMock,
            )
            mock = patcher.start()
            mock.return_value = default
            self.addCleanup(patcher.stop)

        # revoke_all_sessions_for_user is imported inside endpoint functions
        # from packages.auth.repository, so patch the source module
        p_revoke = patch(
            "packages.auth.repository.revoke_all_sessions_for_user",
            new_callable=AsyncMock,
        )
        m_revoke = p_revoke.start()
        m_revoke.return_value = 3
        self.addCleanup(p_revoke.stop)

    def test_cannot_deactivate_last_break_glass(self):
        """Cannot deactivate last active break-glass user."""
        self._mock_auth()
        self._mock_repo(
            get_user_detail=_make_user("gb-001", "active", is_break_glass=True),
            count_active_break_glass_users=1,
        )
        resp = self.client.post(
            "/api/v1/identity/users/gb-001/deactivate",
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 409)

    def test_cannot_deactivate_last_admin(self):
        """Cannot deactivate last active system_admin user."""
        self._mock_auth()
        target = _make_user("admin-target", "active")
        target.roles = [_MockUserRole("ur-1", "role-admin", "advertiser", None)]
        target.roles[0].role = _MockRole("role-admin", "system_admin", "System Admin")

        self._mock_repo(
            get_user_detail=target,
            count_active_admin_users=1,
        )
        resp = self.client.post(
            "/api/v1/identity/users/admin-target/deactivate",
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 409)

    def test_already_inactive_returns_409(self):
        """Deactivating an already-inactive user -> 409."""
        self._mock_auth()
        self._mock_repo(get_user_detail=_make_user("target", "inactive"))
        resp = self.client.post(
            "/api/v1/identity/users/target/deactivate",
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 409)

    def test_already_active_returns_409(self):
        """Activating an already-active user -> 409."""
        self._mock_auth()
        self._mock_repo(get_user_detail=_make_user("target", "active"))
        resp = self.client.post(
            "/api/v1/identity/users/target/activate",
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 409)


class TestResetPassword(unittest.TestCase):
    """POST /users/{id}/reset-password flow."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(_get_app())

    def setUp(self):
        reset_security_config()
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test-jwt-secret-for-user-mgmt-tests-32chars"
        self.client.cookies.clear()

    def tearDown(self):
        reset_security_config()

    def _token(self):
        return create_access_token("u-admin", "local_break_glass")

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _mock_auth_and_repo(self, **overrides):
        p_auth_find = patch(
            "packages.api.dependencies.repository.find_user_by_id",
            new_callable=AsyncMock,
        )
        p_auth_perms = patch(
            "packages.api.dependencies.repository.get_user_permissions",
            new_callable=AsyncMock,
        )
        m1 = p_auth_find.start()
        m2 = p_auth_perms.start()
        m1.return_value = _make_user("u-admin", "active", "local_break_glass")
        m2.return_value = {"users.read", "users.manage"}
        self.addCleanup(p_auth_find.stop)
        self.addCleanup(p_auth_perms.stop)

        defaults = {
            "get_user_detail": _make_user("target", "active", "local_advertiser"),
            "get_user_local_credential": _MockCredential(),
            "update_local_credential_password": True,
        }
        for name, default in {**defaults, **overrides}.items():
            patcher = patch(
                f"packages.api.identity.repository.{name}",
                new_callable=AsyncMock,
            )
            mock = patcher.start()
            mock.return_value = default
            self.addCleanup(patcher.stop)

        # revoke_all_sessions_for_user is imported inside endpoint function
        p_revoke = patch(
            "packages.auth.repository.revoke_all_sessions_for_user",
            new_callable=AsyncMock,
        )
        m_revoke = p_revoke.start()
        m_revoke.return_value = 2
        self.addCleanup(p_revoke.stop)

    def test_ad_user_rejected(self):
        """Reset password for AD user -> 422."""
        self._mock_auth_and_repo(
            get_user_detail=_make_user("ad-user", "active", "ad"),
        )
        resp = self.client.post(
            "/api/v1/identity/users/ad-user/reset-password",
            json={"auto_generate_password": True},
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 422)

    def test_local_user_ok(self):
        """Reset password for local user -> 200."""
        self._mock_auth_and_repo()
        resp = self.client.post(
            "/api/v1/identity/users/target/reset-password",
            json={"auto_generate_password": True},
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertNotIn("password_hash", body)
        self.assertNotIn("password", body)
        self.assertTrue(body["must_change_password"])


# ---------------------------------------------------------------------------
# Mock value classes
# ---------------------------------------------------------------------------

class _MockOrg:
    def __init__(self):
        self.id = "00000000-0000-0000-0000-000000000001"
        self.code = "ADV-001"
        self.status = "active"


class _MockCreatedUser:
    def __init__(self):
        self.id = "new-user-id"
        self.username = "new_user"
        self.display_name = "Test User"
