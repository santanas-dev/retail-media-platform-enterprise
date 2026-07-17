"""
BP-002 — Advertiser Invite Backend Tests.

Tests: create invite, get invite, accept invite, token validation,
cross-org isolation, approval requirement.
"""

import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-bp002-tests-32ch"

from fastapi.testclient import TestClient

from tests.test_phase3_identity_api import AuthzMixin, _get_app, _auth, _token


def _mock_invite(**kw) -> object:
    defaults = {
        "id": "inv-001",
        "advertiser_application_id": "app-001",
        "advertiser_organization_id": "org-001",
        "token": "a" * 64,
        "contact_email": "ivan@test.ru",
        "status": "pending",
        "created_by": "u-admin",
        "created_at": datetime(2026, 7, 17, 10, 0, 0, tzinfo=timezone.utc),
        "expires_at": datetime(2026, 7, 24, 10, 0, 0, tzinfo=timezone.utc),
        "accepted_at": None,
        "accepted_by_user_id": None,
    }
    defaults.update(kw)
    return type("AdvertiserInvite", (), defaults)()


def _mock_app(**kw) -> object:
    """Mock AdvertiserApplication with org_id."""
    defaults = {
        "id": "app-001",
        "company_name": "ООО Тест",
        "contact_name": "Иван",
        "email": "ivan@test.ru",
        "phone": "",
        "website": "",
        "comment": "",
        "consent": True,
        "status": "approved",
        "organization_id": "org-001",
        "reviewer_id": None,
        "review_reason": "",
        "reviewed_at": None,
        "created_at": datetime(2026, 7, 17, 10, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 7, 17, 10, 0, 0, tzinfo=timezone.utc),
    }
    defaults.update(kw)
    return type("AdvertiserApplication", (), defaults)()


# ── Create Invite ──


class TestCreateInvite(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.get_advertiser_application",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.create_advertiser_invite",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.create_audit_event",
        new_callable=AsyncMock,
    )
    def test_create_invite_for_approved(self, mock_audit, mock_create_invite, mock_get_app):
        mock_get_app.return_value = _mock_app(status="approved")
        mock_create_invite.return_value = _mock_invite()
        mock_audit.return_value = None
        self._setup_authz(perms={"advertiser_applications.review"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/advertiser-applications/app-001/invite",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["status"], "pending")
        self.assertEqual(resp.json()["token"], "a" * 64)

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.get_advertiser_application",
        new_callable=AsyncMock,
    )
    def test_cannot_create_invite_for_new(self, mock_get_app):
        mock_get_app.return_value = _mock_app(status="new")
        self._setup_authz(perms={"advertiser_applications.review"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/advertiser-applications/app-001/invite",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 409)

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.get_advertiser_application",
        new_callable=AsyncMock,
    )
    def test_cannot_create_invite_for_rejected(self, mock_get_app):
        mock_get_app.return_value = _mock_app(status="rejected")
        self._setup_authz(perms={"advertiser_applications.review"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/advertiser-applications/app-001/invite",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 409)

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.get_advertiser_application",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.create_advertiser_invite",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.create_audit_event",
        new_callable=AsyncMock,
    )
    def test_create_invite_denied_without_permission(self, mock_audit, mock_create_invite, mock_get_app):
        self._setup_authz(perms={"advertiser_applications.read"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/advertiser-applications/app-001/invite",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 403)

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.get_advertiser_application",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.create_advertiser_invite",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.create_audit_event",
        new_callable=AsyncMock,
    )
    def test_create_invite_requires_org_id(self, mock_audit, mock_create_invite, mock_get_app):
        """Approved app without organization_id should get 409."""
        mock_get_app.return_value = _mock_app(status="approved", organization_id=None)
        self._setup_authz(perms={"advertiser_applications.review"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/advertiser-applications/app-001/invite",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 409)


# ── Get Invite ──


class TestGetInvite(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.get_invite_for_application",
        new_callable=AsyncMock,
    )
    def test_get_invite_returns_invite(self, mock_get_invite):
        mock_get_invite.return_value = _mock_invite()
        self._setup_authz(perms={"advertiser_applications.read"})
        client = TestClient(_get_app())
        resp = client.get(
            "/api/v1/identity/advertiser-applications/app-001/invite",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "pending")

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.get_invite_for_application",
        new_callable=AsyncMock,
    )
    def test_get_invite_returns_none(self, mock_get_invite):
        mock_get_invite.return_value = None
        self._setup_authz(perms={"advertiser_applications.read"})
        client = TestClient(_get_app())
        resp = client.get(
            "/api/v1/identity/advertiser-applications/app-001/invite",
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json())


# ── Accept Invite ──


class TestAcceptInvite(unittest.TestCase):

    @patch(
        "packages.api.public_routes.applications.repository.accept_advertiser_invite",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.public_routes.applications.repository.create_audit_event",
        new_callable=AsyncMock,
    )
    def test_accept_invite_success(self, mock_audit, mock_accept):
        mock_accept.return_value = _mock_invite(status="accepted", accepted_at=datetime.now(timezone.utc), accepted_by_user_id="u-new")
        mock_audit.return_value = None
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/public/advertiser-invites/aaaa/accept",
            json={"password": "securepass123"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")

    @patch(
        "packages.api.public_routes.applications.repository.accept_advertiser_invite",
        new_callable=AsyncMock,
    )
    def test_accept_invite_invalid_token(self, mock_accept):
        mock_accept.side_effect = ValueError("Недействительный код приглашения")
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/public/advertiser-invites/bad/accept",
            json={"password": "securepass123"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Недействительный", resp.json()["detail"])

    @patch(
        "packages.api.public_routes.applications.repository.accept_advertiser_invite",
        new_callable=AsyncMock,
    )
    def test_accept_invite_already_used(self, mock_accept):
        mock_accept.side_effect = ValueError("Приглашение уже использовано")
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/public/advertiser-invites/aaaa/accept",
            json={"password": "securepass123"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("использовано", resp.json()["detail"])

    @patch(
        "packages.api.public_routes.applications.repository.accept_advertiser_invite",
        new_callable=AsyncMock,
    )
    def test_accept_invite_expired(self, mock_accept):
        mock_accept.side_effect = ValueError("Срок действия приглашения истёк")
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/public/advertiser-invites/aaaa/accept",
            json={"password": "securepass123"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("истёк", resp.json()["detail"])

    def test_accept_invite_password_too_short(self):
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/public/advertiser-invites/aaaa/accept",
            json={"password": "1234567"},
        )
        self.assertEqual(resp.status_code, 422)


# ── No secrets in invite response ──


class TestNoSecretsInInvite(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.advertiser_applications.repository.get_invite_for_application",
        new_callable=AsyncMock,
    )
    def test_no_secrets_in_invite(self, mock_get_invite):
        mock_get_invite.return_value = _mock_invite()
        self._setup_authz(perms={"advertiser_applications.read"})
        client = TestClient(_get_app())
        resp = client.get(
            "/api/v1/identity/advertiser-applications/app-001/invite",
            headers=_auth(_token()),
        )
        body = resp.json()
        for secret in ("password", "hash", "hmac", "secret", "private", "credential"):
            self.assertNotIn(secret, str(body).lower())


if __name__ == "__main__":
    unittest.main()
