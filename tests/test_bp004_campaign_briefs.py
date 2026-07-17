"""
BP-004 — Campaign Briefs Backend Tests.

Tests: advertiser-scoped list/detail/create/update/submit,
cross-org isolation, status transitions, permissions.
"""
import os
import sys
import unittest
from datetime import datetime, timezone, date
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-bp004-tests-32ch"

from fastapi.testclient import TestClient

from tests.test_phase3_identity_api import AuthzMixin, _get_app, _auth, _token


def _mock_brief(**kw) -> object:
    defaults = {
        "id": "brief-001",
        "advertiser_organization_id": "org-a",
        "title": "Продвижение молочной продукции",
        "objective": "Повысить продажи в магазинах сети",
        "product_category": "Молочная продукция",
        "target_period_from": date(2026, 8, 1),
        "target_period_to": date(2026, 9, 30),
        "budget_amount": 150000.0,
        "budget_currency": "RUB",
        "preferred_channels": "LED-экраны, прикассовая зона",
        "comment": "Пилотный запуск",
        "status": "draft",
        "created_by": "user-1",
        "created_at": datetime(2026, 7, 17, 10, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 7, 17, 10, 0, 0, tzinfo=timezone.utc),
    }
    defaults.update(kw)
    return type("CampaignBrief", (), defaults)()


# ── List ──


class TestBriefList(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.briefs.repository.list_campaign_briefs",
        new_callable=AsyncMock,
    )
    def test_list_success(self, mock_list):
        mock_list.return_value = ([_mock_brief()], 1)
        self._setup_authz(perms={"campaigns.read"})
        client = TestClient(_get_app())
        resp = client.get(
            "/api/v1/identity/campaign-briefs",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["items"][0]["title"], "Продвижение молочной продукции")

    @patch(
        "packages.api.identity_routes.briefs.repository.list_campaign_briefs",
        new_callable=AsyncMock,
    )
    def test_empty_list(self, mock_list):
        mock_list.return_value = ([], 0)
        self._setup_authz(perms={"campaigns.read"})
        client = TestClient(_get_app())
        resp = client.get(
            "/api/v1/identity/campaign-briefs",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["total"], 0)

    @patch(
        "packages.api.identity_routes.briefs.repository.list_campaign_briefs",
        new_callable=AsyncMock,
    )
    def test_list_denied_without_permission(self, mock_list):
        self._setup_authz(perms={"organization.read"})
        client = TestClient(_get_app())
        resp = client.get(
            "/api/v1/identity/campaign-briefs",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 403)


# ── Detail ──


class TestBriefDetail(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.briefs.repository.get_campaign_brief",
        new_callable=AsyncMock,
    )
    def test_detail_success(self, mock_get):
        mock_get.return_value = _mock_brief()
        self._setup_authz(perms={"campaigns.read"})
        client = TestClient(_get_app())
        resp = client.get(
            "/api/v1/identity/campaign-briefs/brief-001",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "draft")

    @patch(
        "packages.api.identity_routes.briefs.repository.get_campaign_brief",
        new_callable=AsyncMock,
    )
    def test_detail_404(self, mock_get):
        mock_get.return_value = None
        self._setup_authz(perms={"campaigns.read"})
        client = TestClient(_get_app())
        resp = client.get(
            "/api/v1/identity/campaign-briefs/brief-999",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 404)


# ── Create (requires scoped advertiser context) ──


def _scoped_create_setup(test_case, app):
    """Override scope to return advertiser-scoped context (non-admin)."""
    from packages.api.dependencies import get_scope_context
    from packages.domain.scopes import ScopeContext

    async def _fake_scoped():
        return ScopeContext(
            user_id="u-1",
            is_admin=False,
            role_codes={"advertiser"},
            global_permissions={"campaigns.manage"},
            all_permissions={"campaigns.manage"},
            advertiser_scope_ids={"org-a"},
        )

    app.dependency_overrides[get_scope_context] = _fake_scoped
    test_case.addCleanup(lambda: app.dependency_overrides.clear())


class TestBriefCreate(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.briefs.repository.create_campaign_brief",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.briefs.repository.get_campaign_brief",
        new_callable=AsyncMock,
    )
    def test_create_draft_success(self, mock_get, mock_create):
        self._setup_authz(perms={"campaigns.manage"})
        app = _get_app()
        _scoped_create_setup(self, app)
        mock_create.return_value = "brief-new"
        mock_get.return_value = _mock_brief(id="brief-new")
        client = TestClient(app)
        resp = client.post(
            "/api/v1/identity/campaign-briefs",
            json={
                "title": "Тестовая заявка",
                "objective": "Цель теста",
                "budget_amount": 100000,
            },
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["status"], "draft")

    @patch(
        "packages.api.identity_routes.briefs.repository.create_campaign_brief",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.briefs.repository.get_campaign_brief",
        new_callable=AsyncMock,
    )
    def test_create_rejects_empty_title(self, mock_get, mock_create):
        self._setup_authz(perms={"campaigns.manage"})
        app = _get_app()
        _scoped_create_setup(self, app)
        client = TestClient(app)
        resp = client.post(
            "/api/v1/identity/campaign-briefs",
            json={"title": ""},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 422)

    @patch(
        "packages.api.identity_routes.briefs.repository.create_campaign_brief",
        new_callable=AsyncMock,
    )
    def test_create_denied_without_permission(self, mock_create):
        self._setup_authz(perms={"campaigns.read"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/campaign-briefs",
            json={"title": "Тест"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 403)


# ── Update ──


class TestBriefUpdate(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.briefs.repository.update_campaign_brief",
        new_callable=AsyncMock,
    )
    def test_update_draft_success(self, mock_update):
        mock_update.return_value = _mock_brief(title="Обновлённый заголовок")
        self._setup_authz(perms={"campaigns.manage"})
        client = TestClient(_get_app())
        resp = client.patch(
            "/api/v1/identity/campaign-briefs/brief-001",
            json={"title": "Обновлённый заголовок"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "Обновлённый заголовок")

    @patch(
        "packages.api.identity_routes.briefs.repository.update_campaign_brief",
        new_callable=AsyncMock,
    )
    def test_update_submitted_rejected(self, mock_update):
        mock_update.side_effect = ValueError(
            "Cannot update brief in status: submitted"
        )
        self._setup_authz(perms={"campaigns.manage"})
        client = TestClient(_get_app())
        resp = client.patch(
            "/api/v1/identity/campaign-briefs/brief-001",
            json={"title": "Новый заголовок"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 409)
        self.assertIn("submitted", resp.json()["detail"])

    @patch(
        "packages.api.identity_routes.briefs.repository.update_campaign_brief",
        new_callable=AsyncMock,
    )
    def test_update_404(self, mock_update):
        mock_update.return_value = None
        self._setup_authz(perms={"campaigns.manage"})
        client = TestClient(_get_app())
        resp = client.patch(
            "/api/v1/identity/campaign-briefs/brief-999",
            json={"title": "X"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 404)


# ── Submit ──


class TestBriefSubmit(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.briefs.repository.submit_campaign_brief",
        new_callable=AsyncMock,
    )
    def test_submit_success(self, mock_submit):
        mock_submit.return_value = _mock_brief(status="submitted")
        self._setup_authz(perms={"campaigns.manage"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/campaign-briefs/brief-001/submit",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "submitted")

    @patch(
        "packages.api.identity_routes.briefs.repository.submit_campaign_brief",
        new_callable=AsyncMock,
    )
    def test_submit_already_submitted(self, mock_submit):
        mock_submit.side_effect = ValueError(
            "Cannot submit brief in status: submitted"
        )
        self._setup_authz(perms={"campaigns.manage"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/campaign-briefs/brief-001/submit",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 409)

    @patch(
        "packages.api.identity_routes.briefs.repository.submit_campaign_brief",
        new_callable=AsyncMock,
    )
    def test_submit_404(self, mock_submit):
        mock_submit.return_value = None
        self._setup_authz(perms={"campaigns.manage"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/campaign-briefs/brief-999/submit",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 404)


# ── Cross-org isolation ──


class TestBriefCrossOrgIsolation(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.briefs.repository.get_campaign_brief",
        new_callable=AsyncMock,
    )
    def test_cross_org_detail_returns_none(self, mock_get):
        """Scoped user gets None for another org's brief → 404."""
        mock_get.return_value = None
        self._setup_authz(perms={"campaigns.read"})
        client = TestClient(_get_app())
        resp = client.get(
            "/api/v1/identity/campaign-briefs/other-org-brief",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 404)


# ── No secrets in response ──


class TestNoSecrets(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.briefs.repository.get_campaign_brief",
        new_callable=AsyncMock,
    )
    def test_no_secrets_in_detail(self, mock_get):
        mock_get.return_value = _mock_brief()
        self._setup_authz(perms={"campaigns.read"})
        client = TestClient(_get_app())
        resp = client.get(
            "/api/v1/identity/campaign-briefs/brief-001",
            headers=_auth(_token()),
        )
        body = resp.json()
        for secret in ("password", "token", "hmac", "key", "secret", "private"):
            self.assertNotIn(secret, str(body).lower())


if __name__ == "__main__":
    unittest.main()
