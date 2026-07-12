"""
Retail Media Platform - Phase 3.0/3.3 Identity API Tests.

Phase 3.3 update: tests now provide JWT tokens and mock authz dependencies
since identity endpoints are protected.

Tests: endpoints return correct shapes, pagination enforced, no secrets exposed.
Uses mocked sessions - no real database required.
"""

import importlib.util
import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-identity-tests-32bytes"

from fastapi.testclient import TestClient

from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(**overrides):
    return type("User", (), {
        "id": "u-1", "code": "U-001", "username": "testuser",
        "email": "test@example.com", "display_name": "Test User",
        "auth_provider": "local", "status": "active",
        "is_break_glass": False,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        **overrides,
    })()


def _make_role(**overrides):
    return type("Role", (), {
        "id": "r-1", "code": "system_admin", "name": "System Admin",
        "description": "", "is_system": True,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        **overrides,
    })()


def _make_permission(**overrides):
    return type("Permission", (), {
        "id": "p-1", "code": "users.read", "name": "Read Users",
        "description": "", "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        **overrides,
    })()


def _make_audit(**overrides):
    return type("AuditEvent", (), {
        "id": "a-1", "actor_user_id": "u-1", "action": "user.login",
        "target_type": "users", "target_id": "u-1",
        "correlation_id": "corr-1", "ip_address": "127.0.0.1",
        "details_json": {"method": "local"},
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        **overrides,
    })()


_APP = None


def _get_app():
    """Import the FastAPI app via importlib (hyphens in dir name)."""
    global _APP
    if _APP is None:
        path = os.path.join(os.path.dirname(__file__), "..", "apps", "control-api", "main.py")
        spec = importlib.util.spec_from_file_location("control_api_main", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _APP = mod.app
    return _APP


# ---------------------------------------------------------------------------
# Authz mock helper (Phase 3.3)
# ---------------------------------------------------------------------------

class _MockActiveUser:
    def __init__(self, user_id="u-1", status="active"):
        self.id = user_id
        self.status = status


def _setup_authz_mocks(test_case, perms=None, user=_MockActiveUser("u-1")):
    """Mock repository.find_user_by_id and get_user_permissions so authz passes."""
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

    # Also mock get_scope_context and set_rls_context so
    # endpoints that require them (list_users) resolve cleanly.
    app = _get_app()
    from packages.api.dependencies import get_scope_context, set_rls_context
    from packages.domain.scopes import ScopeContext

    async def _fake_scope():
        return ScopeContext(
            user_id=user.id,
            is_admin=True,
            role_codes={"system_admin"},
            global_permissions=perms or set(),
            all_permissions=perms or set(),
        )

    async def _fake_set_rls(db=None, scope=None):
        return None

    app.dependency_overrides[get_scope_context] = _fake_scope
    app.dependency_overrides[set_rls_context] = _fake_set_rls

    test_case.addCleanup(patcher_find.stop)
    test_case.addCleanup(patcher_perms.stop)
    test_case.addCleanup(lambda: app.dependency_overrides.clear())

    return mock_find, mock_perms


def _token(sub="u-1"):
    return create_access_token(sub, "local_advertiser")


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Mixin: provides setUp/tearDown with env + authz mocks
# ---------------------------------------------------------------------------

class AuthzMixin:
    """Shared setup for protected identity tests."""

    def setUp(self):
        reset_security_config()
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test-jwt-secret-for-identity-tests-32bytes"
        self._setup_authz()

    def tearDown(self):
        reset_security_config()

    def _setup_authz(self, perms=None, user=None):
        if user is None:
            user = _MockActiveUser("u-1", "active")
        if perms is None:
            perms = {"users.read", "roles.read", "audit.read"}
        return _setup_authz_mocks(self, perms=perms, user=user)

    def _get(self, url, **kwargs):
        """GET with default JWT auth."""
        headers = kwargs.pop("headers", {})
        headers.update(_auth(_token()))
        return TestClient(_get_app()).get(url, headers=headers, **kwargs)


# ---------------------------------------------------------------------------
# Users endpoint
# ---------------------------------------------------------------------------


class TestListUsers(AuthzMixin, unittest.TestCase):
    """GET /api/v1/identity/users"""

    @patch("packages.api.identity.repository.list_users", new_callable=AsyncMock)
    def test_returns_paginated_shape(self, mock_repo):
        mock_repo.return_value = ([_make_user()], 1)
        resp = self._get("/api/v1/identity/users")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("items", data)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["limit"], 20)
        self.assertEqual(data["offset"], 0)
        self.assertEqual(len(data["items"]), 1)

    @patch("packages.api.identity.repository.list_users", new_callable=AsyncMock)
    def test_limit_enforced(self, mock_repo):
        mock_repo.return_value = ([], 0)
        resp = self._get("/api/v1/identity/users?limit=200")
        self.assertEqual(resp.status_code, 422)  # exceeds max

    @patch("packages.api.identity.repository.list_users", new_callable=AsyncMock)
    def test_limit_max_accepted(self, mock_repo):
        mock_repo.return_value = ([], 0)
        resp = self._get("/api/v1/identity/users?limit=100")
        self.assertEqual(resp.status_code, 200)

    @patch("packages.api.identity.repository.list_users", new_callable=AsyncMock)
    def test_no_password_field(self, mock_repo):
        mock_repo.return_value = ([_make_user()], 1)
        resp = self._get("/api/v1/identity/users")
        data = resp.json()
        user = data["items"][0]
        self.assertNotIn("password", user)
        self.assertNotIn("password_hash", user)
        self.assertNotIn("secret", user)
        self.assertNotIn("token", user)

    @patch("packages.api.identity.repository.list_users", new_callable=AsyncMock)
    def test_no_external_subject_exposed(self, mock_repo):
        """external_subject (AD GUID) is omitted from UserOut schema."""
        mock_repo.return_value = ([_make_user()], 1)
        resp = self._get("/api/v1/identity/users")
        user = resp.json()["items"][0]
        self.assertNotIn("external_subject", user)

    @patch("packages.api.identity.repository.list_users", new_callable=AsyncMock)
    def test_expected_fields_present(self, mock_repo):
        mock_repo.return_value = ([_make_user()], 1)
        resp = self._get("/api/v1/identity/users")
        user = resp.json()["items"][0]
        expected = {"id", "code", "username", "email", "display_name",
                     "auth_provider", "status", "is_break_glass"}
        self.assertTrue(expected <= set(user.keys()),
                        f"Missing fields: {expected - set(user.keys())}")


# ---------------------------------------------------------------------------
# Roles endpoint
# ---------------------------------------------------------------------------


class TestListRoles(AuthzMixin, unittest.TestCase):
    """GET /api/v1/identity/roles"""

    @patch("packages.api.identity.repository.list_roles", new_callable=AsyncMock)
    def test_returns_list(self, mock_repo):
        mock_repo.return_value = [_make_role(), _make_role(code="operator", name="Operator", is_system=False)]
        resp = self._get("/api/v1/identity/roles")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["code"], "system_admin")


# ---------------------------------------------------------------------------
# Permissions endpoint
# ---------------------------------------------------------------------------


class TestListPermissions(AuthzMixin, unittest.TestCase):
    """GET /api/v1/identity/permissions"""

    @patch("packages.api.identity.repository.list_permissions", new_callable=AsyncMock)
    def test_returns_list(self, mock_repo):
        mock_repo.return_value = [_make_permission(), _make_permission(code="users.manage", name="Manage Users")]
        resp = self._get("/api/v1/identity/permissions")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)


# ---------------------------------------------------------------------------
# Audit events endpoint
# ---------------------------------------------------------------------------


class TestListAuditEvents(AuthzMixin, unittest.TestCase):
    """GET /api/v1/identity/audit-events"""

    @patch("packages.api.identity.repository.list_audit_events", new_callable=AsyncMock)
    def test_returns_paginated_shape(self, mock_repo):
        mock_repo.return_value = ([_make_audit()], 1)
        resp = self._get("/api/v1/identity/audit-events")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("items", data)
        self.assertEqual(data["total"], 1)

    @patch("packages.api.identity.repository.list_audit_events", new_callable=AsyncMock)
    def test_details_json_present(self, mock_repo):
        mock_repo.return_value = ([_make_audit()], 1)
        resp = self._get("/api/v1/identity/audit-events")
        event = resp.json()["items"][0]
        self.assertIsNotNone(event.get("details_json"))
        self.assertEqual(event["details_json"]["method"], "local")

    @patch("packages.api.identity.repository.list_audit_events", new_callable=AsyncMock)
    def test_limit_enforced(self, mock_repo):
        mock_repo.return_value = ([], 0)
        resp = self._get("/api/v1/identity/audit-events?limit=200")
        self.assertEqual(resp.status_code, 422)


# ---------------------------------------------------------------------------
# Health endpoints still work
# ---------------------------------------------------------------------------


class TestHealthStillWorks(unittest.TestCase):
    """Phase 2 health endpoints unchanged."""

    def test_live_returns_200(self):
        client = TestClient(_get_app())
        resp = client.get("/health/live")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")


# ---------------------------------------------------------------------------
# No old backend dependency in new files
# ---------------------------------------------------------------------------


class TestNoOldBackendDependency(unittest.TestCase):
    """New Phase 3 files must not import from old backend."""

    def test_schemas_no_backend(self):
        with open("packages/domain/schemas.py") as f:
            self.assertNotIn("from backend", f.read())

    def test_repository_no_backend(self):
        with open("packages/domain/repository.py") as f:
            self.assertNotIn("from backend", f.read())

    def test_identity_router_no_backend(self):
        with open("packages/api/identity.py") as f:
            self.assertNotIn("from backend", f.read())


if __name__ == "__main__":
    unittest.main()
