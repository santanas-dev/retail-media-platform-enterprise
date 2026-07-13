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


# ---------------------------------------------------------------------------
# S-036 — Creative Moderation Queue Tests
# ---------------------------------------------------------------------------


class TestModerationQueue(AuthzMixin, unittest.TestCase):
    """GET /api/v1/identity/creative-assets/moderation-queue"""

    def _setup_moderator(self):
        return self._setup_authz(perms={"creatives.moderate"})

    @patch("packages.api.identity.repository.list_moderation_queue", new_callable=AsyncMock)
    def test_default_filter_returns_pending_review(self, mock_repo):
        self._setup_moderator()
        mock_repo.return_value = []
        resp = self._get("/api/v1/identity/creative-assets/moderation-queue")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])
        mock_repo.assert_called_once()
        self.assertEqual(mock_repo.call_args.kwargs["status_filter"], "pending_review")

    @patch("packages.api.identity.repository.list_moderation_queue", new_callable=AsyncMock)
    def test_advertiser_gets_403(self, mock_repo):
        self._setup_authz(perms={"creatives.read"})
        resp = self._get("/api/v1/identity/creative-assets/moderation-queue")
        self.assertEqual(resp.status_code, 403)
        mock_repo.assert_not_called()

    @patch("packages.api.identity.repository.list_moderation_queue", new_callable=AsyncMock)
    def test_no_storage_fields_in_response(self, mock_repo):
        self._setup_moderator()
        mock_repo.return_value = [{
            "id": "ca-001", "advertiser_organization_id": "org-1",
            "code": "C-001", "name": "Test Creative", "media_type": "image/png",
            "file_size_bytes": 1024, "duration_ms": None,
            "resolution_w": 1920, "resolution_h": 1080,
            "status": "ready", "moderation_status": "pending_review",
            "moderation_notes": None,
            "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
            "advertiser_name": "Test Org", "advertiser_code": "TO",
        }]
        resp = self._get("/api/v1/identity/creative-assets/moderation-queue")
        self.assertEqual(resp.status_code, 200)
        item = resp.json()[0]
        self.assertNotIn("storage_bucket", item)
        self.assertNotIn("storage_key", item)
        self.assertNotIn("presigned_url", item)
        self.assertIn("advertiser_name", item)
        self.assertEqual(item["advertiser_name"], "Test Org")

    @patch("packages.api.identity.repository.list_moderation_queue", new_callable=AsyncMock)
    def test_invalid_filter_rejected(self, mock_repo):
        self._setup_moderator()
        resp = self._get("/api/v1/identity/creative-assets/moderation-queue?moderation_status=invalid")
        self.assertEqual(resp.status_code, 422)
        mock_repo.assert_not_called()


class TestModerationApprove(AuthzMixin, unittest.TestCase):
    """POST /api/v1/identity/creative-assets/{asset_id}/approve"""

    def _setup_moderator(self):
        return self._setup_authz(perms={"creatives.moderate"})

    @patch("packages.api.identity.repository.get_creative_asset", new_callable=AsyncMock)
    @patch("packages.api.identity.repository.approve_creative_asset", new_callable=AsyncMock)
    def test_approve_sets_status_to_approved(self, mock_approve, mock_get):
        self._setup_moderator()
        mock_get.return_value = _make_user()  # any non-None
        mock_approve.return_value = True
        resp = TestClient(_get_app()).post(
            "/api/v1/identity/creative-assets/ca-001/approve",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["moderation_status"], "approved")
        self.assertEqual(data["asset_id"], "ca-001")
        mock_approve.assert_called_once()

    @patch("packages.api.identity.repository.get_creative_asset", new_callable=AsyncMock)
    @patch("packages.api.identity.repository.approve_creative_asset", new_callable=AsyncMock)
    def test_approve_asset_not_found_returns_404(self, mock_approve, mock_get):
        self._setup_moderator()
        mock_get.return_value = None
        resp = TestClient(_get_app()).post(
            "/api/v1/identity/creative-assets/ca-999/approve",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 404)
        mock_approve.assert_not_called()

    @patch("packages.api.identity.repository.get_creative_asset", new_callable=AsyncMock)
    @patch("packages.api.identity.repository.approve_creative_asset", new_callable=AsyncMock)
    def test_approve_advertiser_gets_403(self, mock_approve, mock_get):
        self._setup_authz(perms={"creatives.read"})
        resp = TestClient(_get_app()).post(
            "/api/v1/identity/creative-assets/ca-001/approve",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 403)
        mock_get.assert_not_called()
        mock_approve.assert_not_called()


class TestModerationReject(AuthzMixin, unittest.TestCase):
    """POST /api/v1/identity/creative-assets/{asset_id}/reject"""

    def _setup_moderator(self):
        return self._setup_authz(perms={"creatives.moderate"})

    @patch("packages.api.identity.repository.get_creative_asset", new_callable=AsyncMock)
    @patch("packages.api.identity.repository.reject_creative_asset", new_callable=AsyncMock)
    def test_reject_requires_reason(self, mock_reject, mock_get):
        self._setup_moderator()
        mock_get.return_value = _make_user()
        mock_reject.return_value = True
        resp = TestClient(_get_app()).post(
            "/api/v1/identity/creative-assets/ca-001/reject",
            json={"reason": "Низкое качество изображения"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["moderation_status"], "rejected")
        self.assertEqual(data["asset_id"], "ca-001")
        mock_reject.assert_called_once()
        self.assertEqual(mock_reject.call_args.kwargs["reason"], "Низкое качество изображения")

    @patch("packages.api.identity.repository.get_creative_asset", new_callable=AsyncMock)
    @patch("packages.api.identity.repository.reject_creative_asset", new_callable=AsyncMock)
    def test_reject_empty_reason_rejected(self, mock_reject, mock_get):
        self._setup_moderator()
        resp = TestClient(_get_app()).post(
            "/api/v1/identity/creative-assets/ca-001/reject",
            json={"reason": ""},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 422)
        mock_get.assert_not_called()
        mock_reject.assert_not_called()

    @patch("packages.api.identity.repository.get_creative_asset", new_callable=AsyncMock)
    @patch("packages.api.identity.repository.reject_creative_asset", new_callable=AsyncMock)
    def test_reject_missing_reason_field_rejected(self, mock_reject, mock_get):
        self._setup_moderator()
        resp = TestClient(_get_app()).post(
            "/api/v1/identity/creative-assets/ca-001/reject",
            json={},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 422)
        mock_get.assert_not_called()
        mock_reject.assert_not_called()

    @patch("packages.api.identity.repository.get_creative_asset", new_callable=AsyncMock)
    @patch("packages.api.identity.repository.reject_creative_asset", new_callable=AsyncMock)
    def test_reject_advertiser_gets_403(self, mock_reject, mock_get):
        self._setup_authz(perms={"creatives.read"})
        resp = TestClient(_get_app()).post(
            "/api/v1/identity/creative-assets/ca-001/reject",
            json={"reason": "test"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 403)
        mock_get.assert_not_called()
        mock_reject.assert_not_called()

    @patch("packages.api.identity.repository.get_creative_asset", new_callable=AsyncMock)
    @patch("packages.api.identity.repository.reject_creative_asset", new_callable=AsyncMock)
    def test_reject_asset_not_found_returns_404(self, mock_reject, mock_get):
        self._setup_moderator()
        mock_get.return_value = None
        resp = TestClient(_get_app()).post(
            "/api/v1/identity/creative-assets/ca-999/reject",
            json={"reason": "test"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 404)
        mock_reject.assert_not_called()


# ---------------------------------------------------------------------------
# S-037 — Inventory Management Tests
# ---------------------------------------------------------------------------


class TestInventoryStores(AuthzMixin, unittest.TestCase):
    """GET /api/v1/identity/inventory/stores"""

    @patch("packages.api.identity.repository.get_inventory_stores", new_callable=AsyncMock)
    def test_returns_enriched_stores(self, mock_repo):
        self._setup_authz(perms={"inventory.read"})
        mock_repo.return_value = [{
            "id": "s-1", "code": "ST-001", "name": "Магазин №42",
            "address": "ул. Тестовая, 1", "is_active": True,
            "cluster_name": "Кластер Москва", "branch_name": "Центральный филиал",
            "surface_count": 3,
        }]
        resp = self._get("/api/v1/identity/inventory/stores")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()[0]
        self.assertEqual(data["code"], "ST-001")
        self.assertEqual(data["cluster_name"], "Кластер Москва")
        self.assertEqual(data["surface_count"], 3)

    @patch("packages.api.identity.repository.get_inventory_stores", new_callable=AsyncMock)
    def test_advertiser_gets_403(self, mock_repo):
        self._setup_authz(perms={"campaigns.read"})
        resp = self._get("/api/v1/identity/inventory/stores")
        self.assertEqual(resp.status_code, 403)
        mock_repo.assert_not_called()


class TestInventorySurfaces(AuthzMixin, unittest.TestCase):
    """GET /api/v1/identity/inventory/surfaces"""

    @patch("packages.api.identity.repository.get_inventory_surfaces", new_callable=AsyncMock)
    def test_returns_enriched_surfaces(self, mock_repo):
        self._setup_authz(perms={"inventory.read"})
        mock_repo.return_value = [{
            "id": "ds-1", "code": "SURF-001", "store_id": "s-1",
            "resolution_w": 1440, "resolution_h": 1080, "is_active": True,
            "store_code": "ST-001", "store_name": "Магазин №42",
        }]
        resp = self._get("/api/v1/identity/inventory/surfaces")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()[0]
        self.assertEqual(data["store_code"], "ST-001")
        self.assertNotIn("storage_bucket", data)
        self.assertNotIn("storage_key", data)

    @patch("packages.api.identity.repository.get_inventory_surfaces", new_callable=AsyncMock)
    def test_advertiser_gets_403(self, mock_repo):
        self._setup_authz(perms={"campaigns.read"})
        resp = self._get("/api/v1/identity/inventory/surfaces")
        self.assertEqual(resp.status_code, 403)
        mock_repo.assert_not_called()


class TestInventorySurfacePatch(AuthzMixin, unittest.TestCase):
    """PATCH /api/v1/identity/inventory/surfaces/{id}"""

    @patch("packages.api.identity.repository.toggle_surface_active", new_callable=AsyncMock)
    def test_patch_requires_inventory_manage(self, mock_toggle):
        self._setup_authz(perms={"inventory.read"})
        resp = TestClient(_get_app()).patch(
            "/api/v1/identity/inventory/surfaces/ds-1",
            json={"is_active": False},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 403)
        mock_toggle.assert_not_called()

    @patch("packages.api.identity.repository.get_display_surface", new_callable=AsyncMock)
    @patch("packages.api.identity.repository.toggle_surface_active", new_callable=AsyncMock)
    def test_patch_surface_not_found(self, mock_toggle, mock_get):
        self._setup_authz(perms={"inventory.manage"})
        mock_get.return_value = None
        resp = TestClient(_get_app()).patch(
            "/api/v1/identity/inventory/surfaces/does-not-exist",
            json={"is_active": False},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 404)
        mock_toggle.assert_not_called()


# ---------------------------------------------------------------------------
# S-038 — Campaign Approval Queue Tests
# ---------------------------------------------------------------------------


class TestApprovalQueue(AuthzMixin, unittest.TestCase):
    """GET /api/v1/identity/campaigns/approval-queue"""

    @patch("packages.api.identity.repository.list_approval_queue", new_callable=AsyncMock)
    def test_returns_pending_campaigns(self, mock_repo):
        self._setup_authz(perms={"campaigns.approve"})
        mock_repo.return_value = [{
            "campaign_id": "c-1", "campaign_code": "C-001", "campaign_name": "Test",
            "campaign_status": "pending_approval",
            "advertiser_org_id": "org-1", "advertiser_org_name": "Org", "advertiser_brand_name": "Brand",
            "requested_at": "2026-01-01T00:00:00", "requested_by": "u-1",
            "has_flight": True, "has_placement": True, "has_creative": True,
            "all_creatives_ready": True, "all_creatives_approved": True,
            "rejection_reason": None,
        }]
        resp = self._get("/api/v1/identity/campaigns/approval-queue")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()[0]
        self.assertEqual(data["campaign_code"], "C-001")
        self.assertTrue(data["has_flight"])
        self.assertNotIn("storage_bucket", data)

    @patch("packages.api.identity.repository.list_approval_queue", new_callable=AsyncMock)
    def test_advertiser_gets_403(self, mock_repo):
        self._setup_authz(perms={"campaigns.read"})
        resp = self._get("/api/v1/identity/campaigns/approval-queue")
        self.assertEqual(resp.status_code, 403)
        mock_repo.assert_not_called()

    @patch("packages.api.identity.repository.list_approval_queue", new_callable=AsyncMock)
    def test_invalid_filter_rejected(self, mock_repo):
        self._setup_authz(perms={"campaigns.approve"})
        resp = self._get("/api/v1/identity/campaigns/approval-queue?status=invalid")
        self.assertEqual(resp.status_code, 422)
        mock_repo.assert_not_called()

    @patch("packages.api.identity.repository.list_approval_queue", new_callable=AsyncMock)
    def test_readiness_not_ready_shows(self, mock_repo):
        self._setup_authz(perms={"campaigns.approve"})
        mock_repo.return_value = [{
            "campaign_id": "c-2", "campaign_code": "C-002", "campaign_name": "Not Ready",
            "campaign_status": "pending_approval",
            "advertiser_org_id": "org-1", "advertiser_org_name": "Org", "advertiser_brand_name": "Brand",
            "requested_at": "2026-01-01T00:00:00", "requested_by": "u-1",
            "has_flight": True, "has_placement": False, "has_creative": True,
            "all_creatives_ready": False, "all_creatives_approved": False,
            "rejection_reason": None,
        }]
        resp = self._get("/api/v1/identity/campaigns/approval-queue")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()[0]
        self.assertFalse(data["has_placement"])
        self.assertFalse(data["all_creatives_approved"])


# ---------------------------------------------------------------------------
# S-039 — Advertiser Organization Detail & Memberships
# ---------------------------------------------------------------------------


class TestAdvertiserOrganizationDetail(AuthzMixin, unittest.TestCase):
    """GET /api/v1/identity/advertiser-organizations/{org_id}"""

    @patch("packages.api.identity.repository.get_advertiser_organization", new_callable=AsyncMock)
    def test_returns_org_detail(self, mock_repo):
        self._setup_authz(perms={"advertisers.read"})
        from packages.domain.models import AdvertiserOrganization
        org = AdvertiserOrganization(
            id="org-1", code="ORG01", legal_name="ООО Тест",
            display_name="Тест", status="active",
        )
        mock_repo.return_value = org
        resp = self._get("/api/v1/identity/advertiser-organizations/org-1")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["code"], "ORG01")
        self.assertEqual(data["display_name"], "Тест")

    @patch("packages.api.identity.repository.get_advertiser_organization", new_callable=AsyncMock)
    def test_requires_auth(self, mock_repo):
        resp = TestClient(_get_app()).get("/api/v1/identity/advertiser-organizations/org-1")
        self.assertEqual(resp.status_code, 403)
        mock_repo.assert_not_called()

    @patch("packages.api.identity.repository.get_advertiser_organization", new_callable=AsyncMock)
    def test_advertiser_gets_403_without_perm(self, mock_repo):
        self._setup_authz(perms={"campaigns.read"})
        resp = self._get("/api/v1/identity/advertiser-organizations/org-1")
        self.assertEqual(resp.status_code, 403)
        mock_repo.assert_not_called()

    @patch("packages.api.identity.repository.get_advertiser_organization", new_callable=AsyncMock)
    def test_returns_404_for_unknown(self, mock_repo):
        self._setup_authz(perms={"advertisers.read"})
        mock_repo.return_value = None
        resp = self._get("/api/v1/identity/advertiser-organizations/nonexistent")
        self.assertEqual(resp.status_code, 404)


class TestAdvertiserBrandsByOrg(AuthzMixin, unittest.TestCase):
    """GET /api/v1/identity/advertiser-brands-by-org?advertiser_organization_id=..."""

    @patch("packages.api.identity.repository.list_advertiser_brands_by_org", new_callable=AsyncMock)
    def test_returns_brands_filtered(self, mock_repo):
        self._setup_authz(perms={"advertisers.read"})
        from packages.domain.models import AdvertiserBrand
        mock_repo.return_value = [
            AdvertiserBrand(id="b-1", advertiser_organization_id="org-1",
                           code="B01", name="Brand 1", status="active"),
        ]
        resp = self._get("/api/v1/identity/advertiser-brands-by-org?advertiser_organization_id=org-1")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["code"], "B01")

    @patch("packages.api.identity.repository.list_advertiser_brands_by_org", new_callable=AsyncMock)
    def test_advertiser_gets_403_without_perm(self, mock_repo):
        self._setup_authz(perms={"campaigns.read"})
        resp = self._get("/api/v1/identity/advertiser-brands-by-org?advertiser_organization_id=org-1")
        self.assertEqual(resp.status_code, 403)
        mock_repo.assert_not_called()


class TestAdvertiserContractsByOrg(AuthzMixin, unittest.TestCase):
    """GET /api/v1/identity/advertiser-contracts-by-org?advertiser_organization_id=..."""

    @patch("packages.api.identity.repository.list_advertiser_contracts_by_org", new_callable=AsyncMock)
    def test_returns_contracts_filtered(self, mock_repo):
        self._setup_authz(perms={"advertisers.read"})
        from packages.domain.models import AdvertiserContract
        mock_repo.return_value = [
            AdvertiserContract(id="c-1", advertiser_organization_id="org-1",
                              code="CON01", name="Contract", status="active",
                              budget_limit_currency="RUB",
                              valid_from=datetime(2026, 1, 1)),
        ]
        resp = self._get("/api/v1/identity/advertiser-contracts-by-org?advertiser_organization_id=org-1")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["code"], "CON01")


class TestAdvertiserContactsByOrg(AuthzMixin, unittest.TestCase):
    """GET /api/v1/identity/advertiser-contacts-by-org?advertiser_organization_id=..."""

    @patch("packages.api.identity.repository.list_advertiser_contacts_by_org", new_callable=AsyncMock)
    def test_returns_contacts_filtered(self, mock_repo):
        self._setup_authz(perms={"advertisers.contacts.read"})
        from packages.domain.models import AdvertiserContact
        mock_repo.return_value = [
            AdvertiserContact(id="ct-1", advertiser_organization_id="org-1",
                             contact_type="primary", full_name="Ivan Test",
                             email="ivan@test.ru", phone=None,
                             is_primary=True, status="active"),
        ]
        resp = self._get("/api/v1/identity/advertiser-contacts-by-org?advertiser_organization_id=org-1")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["full_name"], "Ivan Test")
        self.assertNotIn("password_hash", data[0])
        self.assertNotIn("hash", data[0])


class TestAdvertiserUserMemberships(AuthzMixin, unittest.TestCase):
    """GET /api/v1/identity/advertiser-user-memberships?advertiser_organization_id=..."""

    @patch("packages.api.identity.repository.list_advertiser_user_memberships", new_callable=AsyncMock)
    def test_returns_memberships(self, mock_repo):
        self._setup_authz(perms={"advertisers.read"})
        mock_repo.return_value = [{
            "id": "m-1", "user_id": "u-1", "username": "adv1",
            "display_name": "Advertiser One", "email": "a1@test.ru",
            "auth_provider": "local_advertiser", "user_status": "active",
            "must_change_password": False,
            "membership_status": "active",
            "membership_created_at": "2026-01-01T00:00:00",
        }]
        resp = self._get("/api/v1/identity/advertiser-user-memberships?advertiser_organization_id=org-1")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["username"], "adv1")
        self.assertNotIn("password_hash", data[0])
        self.assertNotIn("hash", data[0])
        self.assertNotIn("token", data[0])

    @patch("packages.api.identity.repository.list_advertiser_user_memberships", new_callable=AsyncMock)
    def test_requires_auth(self, mock_repo):
        resp = TestClient(_get_app()).get(
            "/api/v1/identity/advertiser-user-memberships?advertiser_organization_id=org-1")
        self.assertEqual(resp.status_code, 403)
        mock_repo.assert_not_called()

    @patch("packages.api.identity.repository.list_advertiser_user_memberships", new_callable=AsyncMock)
    def test_advertiser_gets_403_without_perm(self, mock_repo):
        self._setup_authz(perms={"campaigns.read"})
        resp = self._get("/api/v1/identity/advertiser-user-memberships?advertiser_organization_id=org-1")
        self.assertEqual(resp.status_code, 403)
        mock_repo.assert_not_called()


if __name__ == "__main__":
    unittest.main()
