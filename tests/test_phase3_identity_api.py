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
        self.assertEqual(data["limit"], 50)
        self.assertEqual(data["offset"], 0)
        self.assertEqual(len(data["items"]), 1)

    @patch("packages.api.identity.repository.list_users", new_callable=AsyncMock)
    def test_limit_enforced(self, mock_repo):
        mock_repo.return_value = ([], 0)
        resp = self._get("/api/v1/identity/users?limit=999")
        self.assertEqual(resp.status_code, 422)  # exceeds max

    @patch("packages.api.identity.repository.list_users", new_callable=AsyncMock)
    def test_limit_max_accepted(self, mock_repo):
        mock_repo.return_value = ([], 0)
        resp = self._get("/api/v1/identity/users?limit=200")
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
        resp = self._get("/api/v1/identity/audit-events?limit=999")
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

    @patch("packages.api.identity.repository.list_moderation_queue_paginated", new_callable=AsyncMock)
    def test_default_filter_returns_pending_review(self, mock_repo):
        self._setup_moderator()
        mock_repo.return_value = ([], 0)
        resp = self._get("/api/v1/identity/creative-assets/moderation-queue")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["items"], [])
        self.assertEqual(data["total"], 0)
        mock_repo.assert_called_once()
        self.assertEqual(mock_repo.call_args.kwargs["status_filter"], "pending_review")

    @patch("packages.api.identity.repository.list_moderation_queue_paginated", new_callable=AsyncMock)
    def test_advertiser_gets_403(self, mock_repo):
        self._setup_authz(perms={"creatives.read"})
        resp = self._get("/api/v1/identity/creative-assets/moderation-queue")
        self.assertEqual(resp.status_code, 403)
        mock_repo.assert_not_called()

    @patch("packages.api.identity.repository.list_moderation_queue_paginated", new_callable=AsyncMock)
    def test_no_storage_fields_in_response(self, mock_repo):
        self._setup_moderator()
        mock_repo.return_value = ([{
            "id": "ca-001", "advertiser_organization_id": "org-1",
            "code": "C-001", "name": "Test Creative", "media_type": "image/png",
            "file_size_bytes": 1024, "duration_ms": None,
            "resolution_w": 1920, "resolution_h": 1080,
            "status": "ready", "moderation_status": "pending_review",
            "moderation_notes": None,
            "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
            "advertiser_name": "Test Org", "advertiser_code": "TO",
        }], 1)
        resp = self._get("/api/v1/identity/creative-assets/moderation-queue")
        self.assertEqual(resp.status_code, 200)
        item = resp.json()["items"][0]
        self.assertNotIn("storage_bucket", item)
        self.assertNotIn("storage_key", item)
        self.assertNotIn("presigned_url", item)
        self.assertIn("advertiser_name", item)
        self.assertEqual(item["advertiser_name"], "Test Org")

    @patch("packages.api.identity.repository.list_moderation_queue_paginated", new_callable=AsyncMock)
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
    @patch("packages.domain.repository.create_audit_event", new_callable=AsyncMock)
    def test_approve_sets_status_to_approved(self, mock_audit, mock_approve, mock_get):
        self._setup_moderator()
        mock_get.return_value = _make_user(moderation_status="pending_review")  # any non-None
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
    @patch("packages.domain.repository.create_audit_event", new_callable=AsyncMock)
    def test_reject_requires_reason(self, mock_audit, mock_reject, mock_get):
        self._setup_moderator()
        mock_get.return_value = _make_user(moderation_status="pending_review")
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

    @patch("packages.api.identity.repository.get_inventory_stores_paginated", new_callable=AsyncMock)
    def test_returns_enriched_stores(self, mock_repo):
        self._setup_authz(perms={"inventory.read"})
        mock_repo.return_value = ([{
            "id": "s-1", "code": "ST-001", "name": "Магазин №42",
            "address": "ул. Тестовая, 1", "is_active": True,
            "cluster_name": "Кластер Москва", "branch_name": "Центральный филиал",
            "surface_count": 3,
        }], 1)
        resp = self._get("/api/v1/identity/inventory/stores")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["items"][0]
        self.assertEqual(data["code"], "ST-001")
        self.assertEqual(data["cluster_name"], "Кластер Москва")
        self.assertEqual(data["surface_count"], 3)

    @patch("packages.api.identity.repository.get_inventory_stores_paginated", new_callable=AsyncMock)
    def test_advertiser_gets_403(self, mock_repo):
        self._setup_authz(perms={"campaigns.read"})
        resp = self._get("/api/v1/identity/inventory/stores")
        self.assertEqual(resp.status_code, 403)
        mock_repo.assert_not_called()


class TestInventorySurfaces(AuthzMixin, unittest.TestCase):
    """GET /api/v1/identity/inventory/surfaces"""

    @patch("packages.api.identity.repository.get_inventory_surfaces_paginated", new_callable=AsyncMock)
    def test_returns_enriched_surfaces(self, mock_repo):
        self._setup_authz(perms={"inventory.read"})
        mock_repo.return_value = ([{
            "id": "ds-1", "code": "SURF-001", "store_id": "s-1",
            "resolution_w": 1440, "resolution_h": 1080, "is_active": True,
            "store_code": "ST-001", "store_name": "Магазин №42",
        }], 1)
        resp = self._get("/api/v1/identity/inventory/surfaces")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["items"][0]
        self.assertEqual(data["store_code"], "ST-001")
        self.assertNotIn("storage_bucket", data)
        self.assertNotIn("storage_key", data)

    @patch("packages.api.identity.repository.get_inventory_surfaces_paginated", new_callable=AsyncMock)
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

    @patch("packages.api.identity.repository.list_approval_queue_paginated", new_callable=AsyncMock)
    def test_returns_pending_campaigns(self, mock_repo):
        self._setup_authz(perms={"campaigns.approve"})
        mock_repo.return_value = ([{
            "campaign_id": "c-1", "campaign_code": "C-001", "campaign_name": "Test",
            "campaign_status": "pending_approval",
            "advertiser_org_id": "org-1", "advertiser_org_name": "Org", "advertiser_brand_name": "Brand",
            "requested_at": "2026-01-01T00:00:00", "requested_by": "u-1",
            "has_flight": True, "has_placement": True, "has_creative": True,
            "all_creatives_ready": True, "all_creatives_approved": True,
            "rejection_reason": None,
        }], 1)
        resp = self._get("/api/v1/identity/campaigns/approval-queue")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["items"][0]
        self.assertEqual(data["campaign_code"], "C-001")
        self.assertTrue(data["has_flight"])
        self.assertNotIn("storage_bucket", data)

    @patch("packages.api.identity.repository.list_approval_queue_paginated", new_callable=AsyncMock)
    def test_advertiser_gets_403(self, mock_repo):
        self._setup_authz(perms={"campaigns.read"})
        resp = self._get("/api/v1/identity/campaigns/approval-queue")
        self.assertEqual(resp.status_code, 403)
        mock_repo.assert_not_called()

    @patch("packages.api.identity.repository.list_approval_queue_paginated", new_callable=AsyncMock)
    def test_invalid_filter_rejected(self, mock_repo):
        self._setup_authz(perms={"campaigns.approve"})
        resp = self._get("/api/v1/identity/campaigns/approval-queue?status=invalid")
        self.assertEqual(resp.status_code, 422)
        mock_repo.assert_not_called()

    @patch("packages.api.identity.repository.list_approval_queue_paginated", new_callable=AsyncMock)
    def test_readiness_not_ready_shows(self, mock_repo):
        self._setup_authz(perms={"campaigns.approve"})
        mock_repo.return_value = ([{
            "campaign_id": "c-2", "campaign_code": "C-002", "campaign_name": "Not Ready",
            "campaign_status": "pending_approval",
            "advertiser_org_id": "org-1", "advertiser_org_name": "Org", "advertiser_brand_name": "Brand",
            "requested_at": "2026-01-01T00:00:00", "requested_by": "u-1",
            "has_flight": True, "has_placement": False, "has_creative": True,
            "all_creatives_ready": False, "all_creatives_approved": False,
            "rejection_reason": None,
        }], 1)
        resp = self._get("/api/v1/identity/campaigns/approval-queue")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["items"][0]
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


# ---------------------------------------------------------------------------
# S-040 — PoP Report CSV Export
# ---------------------------------------------------------------------------


class TestPopExportCsv(AuthzMixin, unittest.TestCase):
    """GET /api/v1/identity/campaigns/{id}/pop/export"""

    _POP_SUMMARY = {
        "impressions_count": 150,
        "total_duration_ms": 450000,
        "first_rendered_at": "2026-06-01T08:00:00",
        "last_rendered_at": "2026-06-15T20:00:00",
        "unique_devices": 12,
        "unique_surfaces": 3,
    }
    _POP_BY_DAY = [
        {"date": "2026-06-01", "impressions_count": 50, "total_duration_ms": 150000},
        {"date": "2026-06-02", "impressions_count": 100, "total_duration_ms": 300000},
    ]
    _POP_BY_SURFACE = [
        {"surface_id": "sf-1", "impressions_count": 80, "total_duration_ms": 240000},
        {"surface_id": "sf-2", "impressions_count": 70, "total_duration_ms": 210000},
    ]

    def _mock_campaign(self):
        """Mock get_campaign (called by _require_campaign_visible)."""
        from packages.domain.models import Campaign
        return Campaign(
            id="c-export", code="C-EXP", name="Export Campaign",
            advertiser_organization_id="org-1", advertiser_contract_id="con-1",
            status="published", priority=0, timezone="Europe/Moscow",
        )

    def _setup_pop_mocks(self):
        """Mock repository functions for PoP data + campaign lookup."""
        self._setup_authz(perms={"campaigns.read"})
        self._patch_get_campaign = patch(
            "packages.api.identity.repository.get_campaign", new_callable=AsyncMock,
        )
        self._patch_summary = patch(
            "packages.api.identity.repository.get_campaign_pop_summary", new_callable=AsyncMock,
        )
        self._patch_by_day = patch(
            "packages.api.identity.repository.list_campaign_pop_by_day", new_callable=AsyncMock,
        )
        self._patch_by_surface = patch(
            "packages.api.identity.repository.list_campaign_pop_by_surface", new_callable=AsyncMock,
        )
        self.mock_get_campaign = self._patch_get_campaign.start()
        self.mock_summary = self._patch_summary.start()
        self.mock_by_day = self._patch_by_day.start()
        self.mock_by_surface = self._patch_by_surface.start()

        self.mock_get_campaign.return_value = self._mock_campaign()
        self.mock_summary.return_value = self._POP_SUMMARY
        self.mock_by_day.return_value = self._POP_BY_DAY
        self.mock_by_surface.return_value = self._POP_BY_SURFACE

        self.addCleanup(self._patch_get_campaign.stop)
        self.addCleanup(self._patch_summary.stop)
        self.addCleanup(self._patch_by_day.stop)
        self.addCleanup(self._patch_by_surface.stop)

    def test_returns_csv_with_correct_content_type(self):
        self._setup_pop_mocks()
        resp = self._get("/api/v1/identity/campaigns/c-export/pop/export")
        self.assertEqual(resp.status_code, 200)
        ct = resp.headers.get("content-type", "")
        self.assertIn("text/csv", ct)
        self.assertIn("charset=utf-8", ct)

    def test_content_disposition_is_attachment(self):
        self._setup_pop_mocks()
        resp = self._get("/api/v1/identity/campaigns/c-export/pop/export")
        cd = resp.headers.get("content-disposition", "")
        self.assertIn("attachment", cd)
        self.assertIn("C-EXP_pop_report.csv", cd)

    def test_csv_includes_summary(self):
        self._setup_pop_mocks()
        resp = self._get("/api/v1/identity/campaigns/c-export/pop/export")
        text = resp.text
        self.assertIn("Сводка", text)
        self.assertIn("150", text)  # impressions_count
        self.assertIn("12", text)  # unique_devices

    def test_csv_includes_by_day(self):
        self._setup_pop_mocks()
        resp = self._get("/api/v1/identity/campaigns/c-export/pop/export")
        text = resp.text
        self.assertIn("По дням", text)
        self.assertIn("2026-06-01", text)
        self.assertIn("50", text)

    def test_csv_includes_by_surface(self):
        self._setup_pop_mocks()
        resp = self._get("/api/v1/identity/campaigns/c-export/pop/export")
        text = resp.text
        self.assertIn("По поверхностям", text)
        self.assertIn("sf-1", text)
        self.assertIn("80", text)

    def test_csv_includes_campaign_name(self):
        self._setup_pop_mocks()
        resp = self._get("/api/v1/identity/campaigns/c-export/pop/export")
        self.assertIn("Export Campaign", resp.text)
        self.assertIn("C-EXP", resp.text)

    def test_requires_auth(self):
        resp = TestClient(_get_app()).get("/api/v1/identity/campaigns/c-export/pop/export")
        self.assertEqual(resp.status_code, 403)

    def test_advertiser_gets_403_without_campaigns_read(self):
        self._setup_authz(perms={"users.read"})
        resp = self._get("/api/v1/identity/campaigns/c-export/pop/export")
        self.assertEqual(resp.status_code, 403)

    def test_campaign_not_found_returns_404(self):
        self._setup_authz(perms={"campaigns.read"})
        self._patch_get_campaign = patch(
            "packages.api.identity.repository.get_campaign", new_callable=AsyncMock,
        )
        mock = self._patch_get_campaign.start()
        mock.return_value = None
        self.addCleanup(self._patch_get_campaign.stop)

        resp = self._get("/api/v1/identity/campaigns/c-nonexistent/pop/export")
        self.assertEqual(resp.status_code, 404)

    def test_no_storage_fields_in_export(self):
        self._setup_pop_mocks()
        resp = self._get("/api/v1/identity/campaigns/c-export/pop/export")
        text = resp.text
        self.assertNotIn("storage_bucket", text)
        self.assertNotIn("storage_key", text)
        self.assertNotIn("presigned_url", text)
        self.assertNotIn("password_hash", text)

    def test_empty_pop_data_exports_valid_report(self):
        self._setup_pop_mocks()
        self.mock_summary.return_value = {
            "impressions_count": 0, "total_duration_ms": 0,
            "first_rendered_at": None, "last_rendered_at": None,
            "unique_devices": 0, "unique_surfaces": 0,
        }
        self.mock_by_day.return_value = []
        self.mock_by_surface.return_value = []
        resp = self._get("/api/v1/identity/campaigns/c-export/pop/export")
        self.assertEqual(resp.status_code, 200)
        text = resp.text
        self.assertIn("Сводка", text)
        self.assertIn("0", text)  # impressions_count


# ---------------------------------------------------------------------------
# S-052 — Approval & Moderation Audit Events
# ---------------------------------------------------------------------------


class TestCampaignApprovalAudit(AuthzMixin, unittest.TestCase):
    """Proof: campaign approve/reject write audit_events_operational rows."""

    def _setup_approval(self):
        return self._setup_authz(perms={"campaigns.approve"})

    @patch("packages.api.identity.repository.approve_campaign", new_callable=AsyncMock)
    @patch("packages.domain.repository.create_audit_event", new_callable=AsyncMock)
    @patch("packages.api.identity.repository.enqueue_outbox_event", new_callable=AsyncMock)
    def test_approve_writes_audit_event(self, mock_outbox, mock_audit, mock_approve):
        """Approve writes campaign.approved audit event with status details."""
        self._setup_approval()
        mock_approve.return_value = ("pending_approval", "approved")

        resp = TestClient(_get_app()).post(
            "/api/v1/identity/campaigns/c-001/approve",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs
        self.assertEqual(call_kwargs["action"], "campaign.approved")
        self.assertEqual(call_kwargs["target_type"], "campaign")
        self.assertEqual(call_kwargs["target_id"], "c-001")
        self.assertEqual(call_kwargs["actor_user_id"], "u-1")
        self.assertEqual(call_kwargs["details"]["old_status"], "pending_approval")
        self.assertEqual(call_kwargs["details"]["new_status"], "approved")

    @patch("packages.api.identity.repository.reject_campaign", new_callable=AsyncMock)
    @patch("packages.domain.repository.create_audit_event", new_callable=AsyncMock)
    @patch("packages.api.identity.repository.enqueue_outbox_event", new_callable=AsyncMock)
    def test_reject_writes_audit_event(self, mock_outbox, mock_audit, mock_reject):
        """Reject writes campaign.rejected audit event with reason."""
        self._setup_approval()
        mock_reject.return_value = ("pending_approval", "rejected")

        resp = TestClient(_get_app()).post(
            "/api/v1/identity/campaigns/c-001/reject",
            json={"reason": "Budget too high"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs
        self.assertEqual(call_kwargs["action"], "campaign.rejected")
        self.assertEqual(call_kwargs["details"]["rejection_reason"], "Budget too high")
        self.assertEqual(call_kwargs["details"]["old_status"], "pending_approval")
        self.assertEqual(call_kwargs["details"]["new_status"], "rejected")

    @patch("packages.api.identity.repository.approve_campaign", new_callable=AsyncMock)
    @patch("packages.domain.repository.create_audit_event", new_callable=AsyncMock)
    @patch("packages.api.identity.repository.enqueue_outbox_event", new_callable=AsyncMock)
    def test_approve_no_secrets_in_audit_details(self, mock_outbox, mock_audit, mock_approve):
        """Audit details must not contain password, token, secret fields."""
        self._setup_approval()
        mock_approve.return_value = ("pending_approval", "approved")

        resp = TestClient(_get_app()).post(
            "/api/v1/identity/campaigns/c-001/approve",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        call_kwargs = mock_audit.call_args.kwargs
        details_str = str(call_kwargs["details"]).lower()
        for forbidden in ("password", "token", "secret", "key", "access_token",
                          "refresh_token", "storage_bucket", "storage_key"):
            self.assertNotIn(forbidden, details_str,
                             f"Audit details must not contain '{forbidden}'")


class TestCreativeModerationAudit(AuthzMixin, unittest.TestCase):
    """Proof: creative approve/reject write audit_events_operational rows."""

    def _setup_moderator(self):
        return self._setup_authz(perms={"creatives.moderate"})

    @patch("packages.api.identity.repository.get_creative_asset", new_callable=AsyncMock)
    @patch("packages.api.identity.repository.approve_creative_asset", new_callable=AsyncMock)
    @patch("packages.domain.repository.create_audit_event", new_callable=AsyncMock)
    def test_approve_writes_audit_event(self, mock_audit, mock_approve, mock_get):
        """Approve writes creative.approved audit event."""
        self._setup_moderator()
        mock_get.return_value = _make_user(moderation_status="pending_review")
        mock_approve.return_value = True

        resp = TestClient(_get_app()).post(
            "/api/v1/identity/creative-assets/ca-001/approve",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs
        self.assertEqual(call_kwargs["action"], "creative.approved")
        self.assertEqual(call_kwargs["target_type"], "creative_asset")
        self.assertEqual(call_kwargs["target_id"], "ca-001")
        self.assertEqual(call_kwargs["details"]["previous_moderation_status"], "pending_review")
        self.assertEqual(call_kwargs["details"]["new_moderation_status"], "approved")

    @patch("packages.api.identity.repository.get_creative_asset", new_callable=AsyncMock)
    @patch("packages.api.identity.repository.reject_creative_asset", new_callable=AsyncMock)
    @patch("packages.domain.repository.create_audit_event", new_callable=AsyncMock)
    def test_reject_writes_audit_event(self, mock_audit, mock_reject, mock_get):
        """Reject writes creative.rejected audit event with reason."""
        self._setup_moderator()
        mock_get.return_value = _make_user(moderation_status="pending_review")
        mock_reject.return_value = True

        resp = TestClient(_get_app()).post(
            "/api/v1/identity/creative-assets/ca-001/reject",
            json={"reason": "Low quality"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs
        self.assertEqual(call_kwargs["action"], "creative.rejected")
        self.assertEqual(call_kwargs["details"]["rejection_reason"], "Low quality")
        self.assertEqual(call_kwargs["details"]["previous_moderation_status"], "pending_review")
        self.assertEqual(call_kwargs["details"]["new_moderation_status"], "rejected")

    @patch("packages.api.identity.repository.get_creative_asset", new_callable=AsyncMock)
    @patch("packages.api.identity.repository.reject_creative_asset", new_callable=AsyncMock)
    @patch("packages.domain.repository.create_audit_event", new_callable=AsyncMock)
    def test_reject_no_secrets_in_audit(self, mock_audit, mock_reject, mock_get):
        """Audit details must not contain password, token, or storage fields."""
        self._setup_moderator()
        mock_get.return_value = _make_user(moderation_status="pending_review")
        mock_reject.return_value = True

        resp = TestClient(_get_app()).post(
            "/api/v1/identity/creative-assets/ca-001/reject",
            json={"reason": "test"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        call_kwargs = mock_audit.call_args.kwargs
        details_str = str(call_kwargs["details"]).lower()
        for forbidden in ("password", "token", "secret", "storage_bucket", "storage_key"):
            self.assertNotIn(forbidden, details_str,
                             f"Audit details must not contain '{forbidden}'")

    @patch("packages.api.identity.repository.get_creative_asset", new_callable=AsyncMock)
    @patch("packages.api.identity.repository.approve_creative_asset", new_callable=AsyncMock)
    @patch("packages.domain.repository.create_audit_event", new_callable=AsyncMock)
    def test_403_does_not_write_audit(self, mock_audit, mock_approve, mock_get):
        """Unauthorized user must not create an audit event."""
        self._setup_authz(perms={"creatives.read"})
        resp = TestClient(_get_app()).post(
            "/api/v1/identity/creative-assets/ca-001/approve",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 403)
        mock_audit.assert_not_called()
        mock_approve.assert_not_called()


# ──────────────────────────────────────────────────────────────────────
# G2-FIX — User Role Management
# ──────────────────────────────────────────────────────────────────────


class _MockRoleAssignment:
    def __init__(self, id="ur-1", user_id="u-1", role_id="r-1",
                 scope_type=None, scope_id=None, role=None):
        self.id = id
        self.user_id = user_id
        self.role_id = role_id
        self.scope_type = scope_type
        self.scope_id = scope_id
        self.role = role or _make_role(id="r-1", code="system_admin", name="System Admin")


def _setup_role_mgmt_mocks(test_case, perms=None, user_id="u-1"):
    """Setup authz mocks + additional role management mocks."""
    mock_find, mock_perms = _setup_authz_mocks(test_case, perms=perms,
                                                user=_MockActiveUser(user_id))
    # Also mock scope/rls for role endpoints
    app = _get_app()
    from packages.api.dependencies import get_scope_context, set_rls_context
    from packages.domain.scopes import ScopeContext

    async def _fake_scope():
        return ScopeContext(
            user_id=user_id,
            is_admin=True,
            role_codes={"system_admin"},
            global_permissions=perms or set(),
            all_permissions=perms or set(),
        )

    async def _fake_set_rls(db=None, scope=None):
        return None

    app.dependency_overrides[get_scope_context] = _fake_scope
    app.dependency_overrides[set_rls_context] = _fake_set_rls
    test_case.addCleanup(lambda: app.dependency_overrides.clear())
    return mock_find, mock_perms


class TestUserRoleManagement(unittest.TestCase):

    def setUp(self):
        reset_security_config()

    # ── PUT /users/{id}/roles ──

    @patch("packages.domain.repository.get_user_detail", new_callable=AsyncMock)
    @patch("packages.domain.repository.find_role_by_code", new_callable=AsyncMock)
    @patch("packages.domain.repository.assign_user_role", new_callable=AsyncMock)
    @patch("packages.domain.repository.create_audit_event", new_callable=AsyncMock)
    def test_assign_role_success(self, mock_audit, mock_assign, mock_find_role, mock_get_user):
        """Assign role returns 201 + writes audit event."""
        _setup_role_mgmt_mocks(self, perms={"users.read", "roles.manage"})
        mock_get_user.return_value = _make_user()
        mock_find_role.return_value = _make_role(id="r-2", code="operator", name="Operator")
        mock_assign.return_value = _MockRoleAssignment(user_id="u-1", role_id="r-2")

        resp = TestClient(_get_app()).put(
            "/api/v1/identity/users/u-1/roles",
            json={"role_code": "operator"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["role_code"], "operator")
        mock_audit.assert_called_once()
        self.assertEqual(mock_audit.call_args.kwargs["action"], "user.role_assigned")

    @patch("packages.domain.repository.get_user_detail", new_callable=AsyncMock)
    def test_assign_role_user_not_found(self, mock_get_user):
        """Assign role to nonexistent user → 404."""
        _setup_role_mgmt_mocks(self, perms={"users.read", "roles.manage"})
        mock_get_user.return_value = None

        resp = TestClient(_get_app()).put(
            "/api/v1/identity/users/u-999/roles",
            json={"role_code": "operator"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 404)

    @patch("packages.domain.repository.get_user_detail", new_callable=AsyncMock)
    @patch("packages.domain.repository.find_role_by_code", new_callable=AsyncMock)
    def test_assign_role_not_found(self, mock_find_role, mock_get_user):
        """Assign nonexistent role → 404."""
        _setup_role_mgmt_mocks(self, perms={"users.read", "roles.manage"})
        mock_get_user.return_value = _make_user()
        mock_find_role.return_value = None

        resp = TestClient(_get_app()).put(
            "/api/v1/identity/users/u-1/roles",
            json={"role_code": "nonexistent"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 404)

    @patch("packages.domain.repository.get_user_detail", new_callable=AsyncMock)
    def test_assign_role_no_permission(self, mock_get_user):
        """User without roles.manage → 403."""
        _setup_role_mgmt_mocks(self, perms={"users.read"})
        mock_get_user.return_value = _make_user()

        resp = TestClient(_get_app()).put(
            "/api/v1/identity/users/u-1/roles",
            json={"role_code": "operator"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 403)

    @patch("packages.domain.repository.get_user_detail", new_callable=AsyncMock)
    @patch("packages.domain.repository.find_role_by_code", new_callable=AsyncMock)
    def test_assign_role_invalid_scope(self, mock_find_role, mock_get_user):
        """Mismatched scope_type/scope_id → 422."""
        _setup_role_mgmt_mocks(self, perms={"users.read", "roles.manage"})
        mock_get_user.return_value = _make_user()
        mock_find_role.return_value = _make_role(id="r-2", code="operator", name="Operator")

        resp = TestClient(_get_app()).put(
            "/api/v1/identity/users/u-1/roles",
            json={"role_code": "operator", "scope_type": "advertiser"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 422)

    # ── DELETE /users/{id}/roles/{assignment_id} ──

    @patch("packages.domain.repository.get_user_role_assignment", new_callable=AsyncMock)
    @patch("packages.domain.repository.remove_user_role", new_callable=AsyncMock)
    @patch("packages.domain.repository.create_audit_event", new_callable=AsyncMock)
    def test_remove_role_success(self, mock_audit, mock_remove, mock_get_assignment):
        """Remove role returns 204 + writes audit event."""
        _setup_role_mgmt_mocks(self, perms={"users.read", "roles.manage"})
        mock_get_assignment.return_value = _MockRoleAssignment(
            id="ur-1", user_id="u-1", role_id="r-1")
        mock_remove.return_value = True

        resp = TestClient(_get_app()).delete(
            "/api/v1/identity/users/u-1/roles/ur-1",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 204)
        mock_audit.assert_called_once()
        self.assertEqual(mock_audit.call_args.kwargs["action"], "user.role_removed")

    @patch("packages.domain.repository.get_user_role_assignment", new_callable=AsyncMock)
    def test_remove_role_assignment_not_found(self, mock_get_assignment):
        """Remove nonexistent role assignment → 404."""
        _setup_role_mgmt_mocks(self, perms={"users.read", "roles.manage"})
        mock_get_assignment.return_value = None

        resp = TestClient(_get_app()).delete(
            "/api/v1/identity/users/u-1/roles/ur-999",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 404)

    @patch("packages.domain.repository.get_user_role_assignment", new_callable=AsyncMock)
    def test_remove_role_wrong_user(self, mock_get_assignment):
        """Remove assignment that belongs to another user → 404."""
        _setup_role_mgmt_mocks(self, perms={"users.read", "roles.manage"})
        mock_get_assignment.return_value = _MockRoleAssignment(
            id="ur-1", user_id="u-2", role_id="r-1")  # different user

        resp = TestClient(_get_app()).delete(
            "/api/v1/identity/users/u-1/roles/ur-1",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
