"""
Retail Media Platform — S-034 AD / LDAPS Settings Tests.

Tests: permission gates (users.manage), response safety (no bind_password/secret),
honest stub mode, test endpoint returns stub without pretending success.
"""

import importlib.util
import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-ad-settings-32chars"

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
    def __init__(self, user_id="u-admin", status="active", auth_provider="local_break_glass"):
        self.id = user_id
        self.status = status
        self.auth_provider = auth_provider


def _make_user(user_id, status="active", auth_provider="local_break_glass"):
    return _MockUser(user_id, status, auth_provider)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestADSettingsPermissionGates(unittest.TestCase):
    """Permission enforcement on AD settings endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(_get_app())

    def setUp(self):
        reset_security_config()
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test-jwt-secret-for-ad-settings-32chars"
        self.client.cookies.clear()

    def tearDown(self):
        reset_security_config()

    def _token(self, sub="u-admin", auth_provider="local_break_glass"):
        return create_access_token(sub, auth_provider)

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _mock_auth(self, user=None, perms=None):
        """Patch repository.find_user_by_id + get_user_permissions + scope/rls."""
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

        mock_find.return_value = user or _make_user("u-admin")
        mock_perms.return_value = perms or {"users.read", "users.manage"}

        # Mock scope + rls deps
        app = _get_app()
        from packages.api.dependencies import get_scope_context, set_rls_context
        from packages.domain.scopes import ScopeContext

        async def _fake_scope():
            return ScopeContext(
                user_id="u-admin",
                is_admin=True,
                role_codes={"system_admin"},
                global_permissions=perms or {"users.read", "users.manage"},
                all_permissions=perms or {"users.read", "users.manage"},
            )

        async def _fake_set_rls(db=None, scope=None):
            return None

        app.dependency_overrides[get_scope_context] = _fake_scope
        app.dependency_overrides[set_rls_context] = _fake_set_rls

        self.addCleanup(patcher_find.stop)
        self.addCleanup(patcher_perms.stop)
        self.addCleanup(lambda: app.dependency_overrides.clear())

        return mock_find, mock_perms

    def test_requires_users_manage(self):
        """User without users.manage -> 403."""
        self._mock_auth(perms={"users.read"})
        resp = self.client.get(
            "/api/v1/identity/auth/ad-settings",
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 403)

    def test_advertiser_cannot_read_settings(self):
        """Advertiser without users.manage -> 403."""
        self._mock_auth(
            user=_make_user("u-adv", auth_provider="local_advertiser"),
            perms={"campaigns.read"},
        )
        resp = self.client.get(
            "/api/v1/identity/auth/ad-settings",
            headers=self._auth(self._token("u-adv", "local_advertiser")),
        )
        self.assertEqual(resp.status_code, 403)

    def test_advertiser_cannot_test_connection(self):
        """Advertiser cannot test AD connection."""
        self._mock_auth(
            user=_make_user("u-adv", auth_provider="local_advertiser"),
            perms={"campaigns.read"},
        )
        resp = self.client.post(
            "/api/v1/identity/auth/ad-settings/test",
            headers=self._auth(self._token("u-adv", "local_advertiser")),
        )
        self.assertEqual(resp.status_code, 403)

    def test_no_token_returns_401(self):
        """No token -> 401."""
        resp = self.client.get("/api/v1/identity/auth/ad-settings")
        self.assertEqual(resp.status_code, 401)


class TestADSettingsResponseSafety(unittest.TestCase):
    """AD settings response must never leak bind_password or secrets."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(_get_app())

    def setUp(self):
        reset_security_config()
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test-jwt-secret-for-ad-settings-32chars"
        self.client.cookies.clear()
        self._setup_mocks()

    def tearDown(self):
        reset_security_config()

    def _setup_mocks(self):
        app = _get_app()
        from packages.api.dependencies import (
            get_current_active_user,
            get_db,
            get_scope_context,
            set_rls_context,
        )
        from packages.domain.scopes import ScopeContext

        async def _admin_user():
            return {
                "sub": "u-admin",
                "auth_provider": "local_break_glass",
                "username": "admin",
                "display_name": "Admin",
            }

        async def _fake_db():
            yield AsyncMock()

        async def _fake_scope():
            return ScopeContext(
                user_id="u-admin",
                is_admin=True,
                role_codes={"system_admin"},
                global_permissions={"users.manage"},
                all_permissions={"users.manage"},
            )

        async def _fake_set_rls(db=None, scope=None):
            return None

        patcher_find = patch(
            "packages.api.dependencies.repository.find_user_by_id",
            new_callable=AsyncMock,
            return_value=_make_user("u-admin"),
        )
        patcher_perms = patch(
            "packages.api.dependencies.repository.get_user_permissions",
            new_callable=AsyncMock,
            return_value={"users.manage"},
        )
        patcher_find.start()
        patcher_perms.start()

        app.dependency_overrides[get_current_active_user] = _admin_user
        app.dependency_overrides[get_db] = _fake_db
        app.dependency_overrides[get_scope_context] = _fake_scope
        app.dependency_overrides[set_rls_context] = _fake_set_rls

        self.addCleanup(lambda: app.dependency_overrides.clear())

    def _token(self):
        return create_access_token("u-admin", "local_break_glass")

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_settings_no_bind_password(self):
        """GET ad-settings must not include bind_password."""
        resp = self.client.get(
            "/api/v1/identity/auth/ad-settings",
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertNotIn("bind_password", body)
        self.assertNotIn("ad_bind_password", body)
        self.assertNotIn("password", body)

    def test_settings_no_secret_values(self):
        """GET ad-settings must not leak any secret fields."""
        resp = self.client.get(
            "/api/v1/identity/auth/ad-settings",
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        for key in body:
            self.assertNotIn("secret", key.lower())
            self.assertNotIn("token", key.lower())

    def test_settings_mode_is_disabled(self):
        """In default dev mode, AD should be disabled."""
        resp = self.client.get(
            "/api/v1/identity/auth/ad-settings",
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["mode"], "disabled")
        self.assertFalse(body["enabled"])

    def test_test_endpoint_returns_stub(self):
        """Test connection returns stub/not_configured, never ok by default."""
        resp = self.client.post(
            "/api/v1/identity/auth/ad-settings/test",
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertIn(body["status"], {"stub", "not_configured"})
        self.assertNotEqual(body["status"], "ok")
        self.assertIsNotNone(body["tested_at"])
        self.assertIn("503", body["message"])

    def test_test_endpoint_no_external_calls(self):
        """Test endpoint completes without external network (stub)."""
        resp = self.client.post(
            "/api/v1/identity/auth/ad-settings/test",
            headers=self._auth(self._token()),
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn(body["status"], {"stub", "not_configured"})
