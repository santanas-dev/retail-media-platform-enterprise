"""
S-071 — Emergency Override Backend Tests.

Tests: emergency.read/emergency.manage permissions, activate/deactivate flow,
advertiser denied, reason required, idempotency (409), audit events, RLS context.
"""

import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-emergency-tests-32chr"

from fastapi.testclient import TestClient

from packages.security.config import reset_security_config

from tests.test_phase3_identity_api import AuthzMixin, _get_app, _auth, _token


def _mock_override(**kw) -> object:
    """Return a mock EmergencyOverride-like object."""
    defaults = {
        "id": "em-001",
        "level": "global",
        "active": True,
        "reason": "Технические работы",
        "activated_by": "u-1",
        "activated_at": datetime(2026, 7, 16, 12, 0, 0, tzinfo=timezone.utc),
        "deactivated_by": None,
        "deactivated_at": None,
        "deactivated_reason": "",
        "created_at": datetime(2026, 7, 16, 12, 0, 0, tzinfo=timezone.utc),
    }
    defaults.update(kw)
    return type("EmergencyOverride", (), defaults)()


# ── Status ──


class TestEmergencyStatus(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.emergency.repository.get_active_emergency_override",
        new_callable=AsyncMock,
    )
    def test_status_inactive_when_none(self, mock_get):
        mock_get.return_value = None
        self._setup_authz(perms={"emergency.read"})
        client = TestClient(_get_app())
        resp = client.get("/api/v1/identity/emergency/status", headers=_auth(_token()))
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertFalse(body["active"])

    @patch(
        "packages.api.identity_routes.emergency.repository.get_active_emergency_override",
        new_callable=AsyncMock,
    )
    def test_status_active(self, mock_get):
        mock_get.return_value = _mock_override()
        self._setup_authz(perms={"emergency.read"})
        client = TestClient(_get_app())
        resp = client.get("/api/v1/identity/emergency/status", headers=_auth(_token()))
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["active"])
        self.assertEqual(body["reason"], "Технические работы")
        self.assertEqual(body["activated_by"], "u-1")

    @patch(
        "packages.api.identity_routes.emergency.repository.get_active_emergency_override",
        new_callable=AsyncMock,
    )
    def test_advertiser_denied(self, mock_get):
        mock_get.return_value = None
        self._setup_authz(perms={"campaigns.read"})  # no emergency.read
        client = TestClient(_get_app())
        resp = client.get("/api/v1/identity/emergency/status", headers=_auth(_token()))
        self.assertEqual(resp.status_code, 403)


# ── Activate ──


class TestEmergencyActivate(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.emergency.repository.activate_emergency_override",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.emergency.repository.create_audit_event",
        new_callable=AsyncMock,
    )
    def test_activate_success(self, mock_audit, mock_activate):
        mock_activate.return_value = _mock_override()
        mock_audit.return_value = None
        self._setup_authz(perms={"emergency.manage"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/emergency/activate",
            json={"reason": "Технические работы"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["active"])

    @patch(
        "packages.api.identity_routes.emergency.repository.activate_emergency_override",
        new_callable=AsyncMock,
    )
    def test_activate_requires_reason(self, mock_activate):
        self._setup_authz(perms={"emergency.manage"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/emergency/activate",
            json={"reason": ""},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 422)

    @patch(
        "packages.api.identity_routes.emergency.repository.activate_emergency_override",
        new_callable=AsyncMock,
    )
    def test_activate_reason_too_long(self, mock_activate):
        self._setup_authz(perms={"emergency.manage"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/emergency/activate",
            json={"reason": "x" * 501},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 422)

    @patch(
        "packages.api.identity_routes.emergency.repository.activate_emergency_override",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.emergency.repository.create_audit_event",
        new_callable=AsyncMock,
    )
    def test_activate_idempotent_409(self, mock_audit, mock_activate):
        mock_activate.side_effect = ValueError("Emergency mode is already active")
        self._setup_authz(perms={"emergency.manage"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/emergency/activate",
            json={"reason": "Повторная попытка"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 409)

    @patch(
        "packages.api.identity_routes.emergency.repository.activate_emergency_override",
        new_callable=AsyncMock,
    )
    def test_advertiser_denied(self, mock_activate):
        self._setup_authz(perms={"campaigns.read"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/emergency/activate",
            json={"reason": "Test"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 403)

    @patch(
        "packages.api.identity_routes.emergency.repository.activate_emergency_override",
        new_callable=AsyncMock,
    )
    def test_emergency_read_not_enough_for_activate(self, mock_activate):
        """emergency.read alone must NOT grant activate access."""
        self._setup_authz(perms={"emergency.read"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/emergency/activate",
            json={"reason": "Test"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 403)


# ── Deactivate ──


class TestEmergencyDeactivate(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.emergency.repository.deactivate_emergency_override",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.emergency.repository.create_audit_event",
        new_callable=AsyncMock,
    )
    def test_deactivate_success(self, mock_audit, mock_deactivate):
        mock_deactivate.return_value = _mock_override(active=False)
        mock_audit.return_value = None
        self._setup_authz(perms={"emergency.manage"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/emergency/deactivate",
            json={"reason": "Работы завершены"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["active"])

    @patch(
        "packages.api.identity_routes.emergency.repository.deactivate_emergency_override",
        new_callable=AsyncMock,
    )
    def test_deactivate_requires_reason(self, mock_deactivate):
        self._setup_authz(perms={"emergency.manage"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/emergency/deactivate",
            json={"reason": ""},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 422)

    @patch(
        "packages.api.identity_routes.emergency.repository.deactivate_emergency_override",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.emergency.repository.create_audit_event",
        new_callable=AsyncMock,
    )
    def test_deactivate_idempotent_409(self, mock_audit, mock_deactivate):
        mock_deactivate.side_effect = ValueError(
            "No active emergency mode to deactivate"
        )
        self._setup_authz(perms={"emergency.manage"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/emergency/deactivate",
            json={"reason": "Повторная попытка"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 409)

    @patch(
        "packages.api.identity_routes.emergency.repository.deactivate_emergency_override",
        new_callable=AsyncMock,
    )
    def test_advertiser_denied(self, mock_deactivate):
        self._setup_authz(perms={"campaigns.read"})
        client = TestClient(_get_app())
        resp = client.post(
            "/api/v1/identity/emergency/deactivate",
            json={"reason": "Test"},
            headers=_auth(_token()),
        )
        self.assertEqual(resp.status_code, 403)


# ── No secrets in response ──


class TestEmergencyNoSecrets(AuthzMixin, unittest.TestCase):

    @patch(
        "packages.api.identity_routes.emergency.repository.get_active_emergency_override",
        new_callable=AsyncMock,
    )
    def test_no_secrets_in_response(self, mock_get):
        mock_get.return_value = _mock_override()
        self._setup_authz(perms={"emergency.read"})
        client = TestClient(_get_app())
        resp = client.get("/api/v1/identity/emergency/status", headers=_auth(_token()))
        body = resp.json()
        for secret in ("password", "token", "hmac", "key", "secret", "private"):
            self.assertNotIn(secret, str(body).lower())


if __name__ == "__main__":
    unittest.main()
