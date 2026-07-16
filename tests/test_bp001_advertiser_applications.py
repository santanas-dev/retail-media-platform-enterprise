"""
BP-001 — Advertiser Applications Backend Tests.

Tests: public submit, admin list/detail, approve/review, validation,
permissions, audit events.
"""

import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-bp001-tests-32ch"

from fastapi.testclient import TestClient

from tests.test_phase3_identity_api import AuthzMixin, _get_app, _auth, _token


def _mock_app(**kw) -> object:
    """Return a mock AdvertiserApplication-like object."""
    defaults = {
        "id": "app-001",
        "company_name": "ООО Тестовая Компания",
        "contact_name": "Иван Петров",
        "email": "ivan@test-company.ru",
        "phone": "+79991234567",
        "website": "https://test-company.ru",
        "comment": "Хотим размещать рекламу",
        "consent": True,
        "status": "new",
        "reviewer_id": None,
        "review_reason": "",
        "reviewed_at": None,
        "created_at": datetime(2026, 7, 17, 10, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 7, 17, 10, 0, 0, tzinfo=timezone.utc),
    }
    defaults.update(kw)
    return type("AdvertiserApplication", (), defaults)()


# ── Public Submit ──


class TestPublicSubmit(unittest.TestCase):

    @patch(
        "packages.api.public_routes.applications.repository.create_advertiser_application",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.public_routes.applications.repository.create_audit_event",
        new_callable=AsyncMock,
    )
    def test_submit_success(self, mock_audit, mock_create):
        mock_create.return_value = _mock_app()
        mock_audit.return_value = None
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/public/advertiser-applications",
            json={
                "company_name": "ООО Тест",
                "contact_name": "Иван",
                "email": "ivan@test.ru",
                "consent": True,
            },
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["company_name"], "ООО Тестовая Компания")
        self.assertEqual(body["status"], "new")

    def test_submit_rejects_no_consent(self):
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/public/advertiser-applications",
            json={
                "company_name": "ООО Тест",
                "contact_name": "Иван",
                "email": "ivan@test.ru",
                "consent": False,
            },
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("согласие", resp.json()["detail"].lower() or "")

    def test_submit_requires_fields(self):
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/public/advertiser-applications",
            json={
                "company_name": "",
                "contact_name": "",
                "email": "",
                "consent": True,
            },
        )
        self.assertEqual(resp.status_code, 422)

    @patch(
        "packages.api.public_routes.applications.repository.create_advertiser_application",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.public_routes.applications.repository.create_audit_event",
        new_callable=AsyncMock,
    )
    def test_submit_no_auth_required(self, mock_audit, mock_create):
        """Public endpoint — no token needed."""
        mock_create.return_value = _mock_app()
        mock_audit.return_value = None
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/public/advertiser-applications",
            json={
                "company_name": "ООО Тест",
                "contact_name": "Иван",
                "email": "ivan@test.ru",
                "consent": True,
            },
        )
        # Should NOT return 401/403
        self.assertNotIn(resp.status_code, (401, 403))


# ── Admin List ──


class TestAdminList(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.list_advertiser_applications",
        new_callable=AsyncMock,
    )
    def test_list_success(self, mock_list):
        mock_list.return_value = ([_mock_app()], 1)
        self._setup_authz(perms={"advertiser_applications.read"})
        client = TestClient(_get_app())
        resp = client.get(
            "/api/v1/identity/advertiser-applications",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(len(body["items"]), 1)

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.list_advertiser_applications",
        new_callable=AsyncMock,
    )
    def test_list_denied_without_permission(self, mock_list):
        self._setup_authz(perms={"campaigns.read"})
        client = TestClient(_get_app())
        resp = client.get(
            "/api/v1/identity/advertiser-applications",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 403)


# ── Admin Detail ──


class TestAdminDetail(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.get_advertiser_application",
        new_callable=AsyncMock,
    )
    def test_detail_success(self, mock_get):
        mock_get.return_value = _mock_app()
        self._setup_authz(perms={"advertiser_applications.read"})
        client = TestClient(_get_app())
        resp = client.get(
            "/api/v1/identity/advertiser-applications/app-001",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["company_name"], "ООО Тестовая Компания")

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.get_advertiser_application",
        new_callable=AsyncMock,
    )
    def test_detail_404(self, mock_get):
        mock_get.return_value = None
        self._setup_authz(perms={"advertiser_applications.read"})
        client = TestClient(_get_app())
        resp = client.get(
            "/api/v1/identity/advertiser-applications/app-999",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 404)


# ── Admin Review ──


class TestAdminReview(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.review_advertiser_application",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.create_audit_event",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.create_advertiser_from_application",
        new_callable=AsyncMock,
    )
    def test_approve_success(self, mock_create_org, mock_audit, mock_review):
        mock_review.return_value = _mock_app(status="approved")
        mock_create_org.return_value = "org-001"
        mock_audit.return_value = None
        self._setup_authz(perms={"advertiser_applications.review"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/advertiser-applications/app-001/review",
            json={"action": "approve", "reason": "Всё в порядке"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "approved")

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.review_advertiser_application",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.create_audit_event",
        new_callable=AsyncMock,
    )
    def test_reject_success(self, mock_audit, mock_review):
        mock_review.return_value = _mock_app(status="rejected")
        mock_audit.return_value = None
        self._setup_authz(perms={"advertiser_applications.review"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/advertiser-applications/app-001/review",
            json={"action": "reject", "reason": "Недостаточно информации"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "rejected")

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.review_advertiser_application",
        new_callable=AsyncMock,
    )
    def test_review_denied_without_permission(self, mock_review):
        self._setup_authz(perms={"advertiser_applications.read"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/advertiser-applications/app-001/review",
            json={"action": "approve", "reason": "OK"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 403)

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.review_advertiser_application",
        new_callable=AsyncMock,
    )
    def test_review_already_reviewed_409(self, mock_review):
        mock_review.side_effect = ValueError(
            "Application cannot be reviewed — current status: approved"
        )
        self._setup_authz(perms={"advertiser_applications.review"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/advertiser-applications/app-001/review",
            json={"action": "approve", "reason": "Повторно"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 409)


# ── No secrets in response ──


class TestNoSecretsInResponse(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.get_advertiser_application",
        new_callable=AsyncMock,
    )
    def test_no_secrets_in_detail(self, mock_get):
        mock_get.return_value = _mock_app()
        self._setup_authz(perms={"advertiser_applications.read"})
        client = TestClient(_get_app())
        resp = client.get(
            "/api/v1/identity/advertiser-applications/app-001",
            headers=_auth(_token()),
        )
        body = resp.json()
        for secret in ("password", "token", "hmac", "key", "secret", "private"):
            self.assertNotIn(secret, str(body).lower())


if __name__ == "__main__":
    unittest.main()
