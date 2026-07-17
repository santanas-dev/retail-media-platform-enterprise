"""
BP-001 — Advertiser Applications Backend Tests.

Tests: public submit, admin list/detail, approve/review, validation,
permissions, audit events.
"""

import importlib
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
        "creator_id": None,
        "reviewer_id": None,
        "review_reason": "",
        "reviewed_at": None,
        "organization_id": None,
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
    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.create_advertiser_from_application",
        new_callable=AsyncMock,
    )
    def test_approve_creates_org_but_not_user_access(self, mock_create_org, mock_audit, mock_review):
        """Proof: approve creates AdvertiserOrganization but no user/login access."""
        mock_review.return_value = _mock_app(status="approved")
        mock_create_org.return_value = "org-001"
        mock_audit.return_value = None
        self._setup_authz(perms={"advertiser_applications.review"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/advertiser-applications/app-001/review",
            json={"action": "approve", "reason": "OK"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)

        # Organization WAS created
        mock_create_org.assert_called_once()

        # Check that the router's approve block does NOT call user/membership/credential creation.
        # We inspect the router source to confirm no create_user/create_credential/create_membership
        # in the approve path. This is a structural proof, not a mock-based one.
        router_path = os.path.join(
            os.path.dirname(__file__),
            "..", "packages", "api", "identity_routes", "advertiser_applications.py",
        )
        with open(router_path) as f:
            source = f.read()

        # The approve block should reference create_advertiser_from_application
        self.assertIn("create_advertiser_from_application", source)
        # But must NOT reference user/membership/credential creation
        banned = [
            "create_user", "create_advertiser_user_membership",
            "create_credential", "create_local_credential",
            "AdvertiserUserMembership", "send_invite",
        ]
        for func in banned:
            self.assertNotIn(func, source, f"Approve path must not create user access: {func} found")

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
    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.create_audit_event",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.create_advertiser_from_application",
        new_callable=AsyncMock,
    )
    def test_reviewing_transition(self, mock_create_org, mock_audit, mock_review):
        """new → reviewing → approved transition chain."""
        mock_review.return_value = _mock_app(status="reviewing")
        mock_audit.return_value = None
        self._setup_authz(perms={"advertiser_applications.review"})
        client = TestClient(_get_app())
        # Step 1: new → reviewing
        resp = client.post(
            "/api/v1/identity/advertiser-applications/app-001/review",
            json={"action": "reviewing", "reason": "Беру в работу"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "reviewing")

        # Step 2: reviewing → approve
        mock_review.return_value = _mock_app(status="approved")
        mock_create_org.return_value = "org-001"
        resp = client.post(
            "/api/v1/identity/advertiser-applications/app-001/review",
            json={"action": "approve", "reason": "OK"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "approved")

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.review_advertiser_application",
        new_callable=AsyncMock,
    )
    def test_cannot_reviewing_from_approved(self, mock_review):
        mock_review.side_effect = ValueError(
            "Cannot start review — current status: approved"
        )
        self._setup_authz(perms={"advertiser_applications.review"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/advertiser-applications/app-001/review",
            json={"action": "reviewing", "reason": ""},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 409)

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.review_advertiser_application",
        new_callable=AsyncMock,
    )
    def test_review_already_reviewed_409(self, mock_review):
        mock_review.side_effect = ValueError(
            "Cannot approve — current status: approved"
        )
        self._setup_authz(perms={"advertiser_applications.review"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/advertiser-applications/app-001/review",
            json={"action": "approve", "reason": "Повторно"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 409)


# ── Rate limiting ──


class TestPublicRateLimit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["RATE_LIMIT_ENABLED"] = "true"
        os.environ["PUBLIC_APPLICATION_RATE_LIMIT"] = "3"
        import importlib
        import packages.observability.rate_limit as rl
        importlib.reload(rl)
        import packages.api.public_routes.applications as pra
        importlib.reload(pra)
        cls.rl = rl

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("RATE_LIMIT_ENABLED", None)
        os.environ.pop("PUBLIC_APPLICATION_RATE_LIMIT", None)
        import packages.observability.rate_limit as rl
        rl._buckets.clear()
        importlib.reload(rl)
        import packages.api.public_routes.applications as pra
        importlib.reload(pra)

    @patch(
        "packages.api.public_routes.applications.repository.create_advertiser_application",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.public_routes.applications.repository.create_audit_event",
        new_callable=AsyncMock,
    )
    def test_rate_limit_returns_429(self, mock_audit, mock_create):
        mock_create.return_value = _mock_app()
        mock_audit.return_value = None
        client = TestClient(_get_app())
        # Exhaust the rate limit: 3 allowed, 4th returns 429
        for _ in range(3):
            resp = client.post(
                "/api/v1/public/advertiser-applications",
                json={"company_name": "Test", "contact_name": "C", "email": "t@t.ru", "consent": True},
            )
        resp = client.post(
            "/api/v1/public/advertiser-applications",
            json={"company_name": "Test", "contact_name": "C", "email": "t@t.ru", "consent": True},
        )
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Too many requests", resp.json()["detail"])

    @patch(
        "packages.api.public_routes.applications.repository.create_advertiser_application",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.public_routes.applications.repository.create_audit_event",
        new_callable=AsyncMock,
    )
    def test_rate_limit_429_no_detail_leak(self, mock_audit, mock_create):
        """429 response must not expose internal state (bucket size, key, etc.)."""
        mock_create.return_value = _mock_app()
        mock_audit.return_value = None
        client = TestClient(_get_app())
        for _ in range(3):
            client.post(
                "/api/v1/public/advertiser-applications",
                json={"company_name": "Test", "contact_name": "C", "email": "t@t.ru", "consent": True},
            )
        resp = client.post(
            "/api/v1/public/advertiser-applications",
            json={"company_name": "Test", "contact_name": "C", "email": "t@t.ru", "consent": True},
        )
        self.assertEqual(resp.status_code, 429)
        body = resp.json()
        for leak in ("bucket", "token", "rate", "RATE_LIMIT", "remaining", "retry-after"):
            self.assertNotIn(leak, str(body).lower())


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
# BP-001 follow-up CI trigger
