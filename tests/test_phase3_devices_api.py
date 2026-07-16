"""
S-070 — Fleet / Device Health Backend Tests.

Tests: devices.read permission, pagination, summary, advertiser denied.
"""

import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-device-tests-32bytes-ok"

from fastapi.testclient import TestClient

from packages.security.config import reset_security_config
from packages.domain.models import PhysicalDevice

from tests.test_phase3_identity_api import AuthzMixin, _get_app, _auth, _token


def _make_device(i: int = 1, **kw) -> PhysicalDevice:
    defaults = {
        "id": f"dev-{i:03d}",
        "store_id": "store-1",
        "device_type_id": "dt-1",
        "code": f"DEV{i:03d}",
        "serial_number": f"SN{i:05d}",
        "os_version": "Linux 6.1",
        "ip_address": "10.0.0.1",
        "status": "active",
        "last_seen_at": None,
        "current_manifest_id": None,
        "cache_size_bytes": 0,
    }
    defaults.update(kw)
    return PhysicalDevice(**defaults)


# ── Device List ──

class TestListDevices(AuthzMixin, unittest.TestCase):

    @patch("packages.api.identity_routes.devices.repository.list_devices", new_callable=AsyncMock)
    def test_list_devices_returns_items(self, mock_list):
        d1 = _make_device(1)
        d2 = _make_device(2, status="inactive")
        mock_list.return_value = ([d1, d2], 2)
        self._setup_authz(perms={"devices.read"})

        resp = self._get("/api/v1/identity/devices")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["total"], 2)
        self.assertEqual(len(body["items"]), 2)
        self.assertEqual(body["items"][0]["code"], "DEV001")

    @patch("packages.api.identity_routes.devices.repository.list_devices", new_callable=AsyncMock)
    def test_list_devices_empty(self, mock_list):
        mock_list.return_value = ([], 0)
        self._setup_authz(perms={"devices.read"})
        resp = self._get("/api/v1/identity/devices")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["total"], 0)

    @patch("packages.api.identity_routes.devices.repository.list_devices", new_callable=AsyncMock)
    def test_advertiser_denied(self, mock_list):
        mock_list.return_value = ([], 0)
        self._setup_authz(perms={"campaigns.read"})
        resp = self._get("/api/v1/identity/devices")
        self.assertEqual(resp.status_code, 403)


# ── Device Summary ──

class TestDeviceSummary(AuthzMixin, unittest.TestCase):

    @patch("packages.api.identity_routes.devices.repository.get_device_summary", new_callable=AsyncMock)
    def test_summary_counts(self, mock_summary):
        mock_summary.return_value = {
            "total": 10, "active": 6, "inactive": 2, "error": 1, "unregistered": 1,
        }
        self._setup_authz(perms={"devices.read"})
        resp = self._get("/api/v1/identity/devices/summary")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["total"], 10)
        self.assertEqual(body["active"], 6)
        self.assertEqual(body["error"], 1)

    @patch("packages.api.identity_routes.devices.repository.get_device_summary", new_callable=AsyncMock)
    def test_advertiser_denied(self, mock_summary):
        mock_summary.return_value = {"total": 0, "active": 0, "inactive": 0, "error": 0, "unregistered": 0}
        self._setup_authz(perms={"campaigns.read"})
        resp = self._get("/api/v1/identity/devices/summary")
        self.assertEqual(resp.status_code, 403)


# ── Device Detail ──

class TestGetDevice(AuthzMixin, unittest.TestCase):

    @patch("packages.api.identity_routes.devices.repository.get_device", new_callable=AsyncMock)
    def test_get_device_found(self, mock_get):
        mock_get.return_value = _make_device(1)
        self._setup_authz(perms={"devices.read"})
        resp = self._get("/api/v1/identity/devices/dev-001")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["code"], "DEV001")

    @patch("packages.api.identity_routes.devices.repository.get_device", new_callable=AsyncMock)
    def test_get_device_not_found(self, mock_get):
        mock_get.return_value = None
        self._setup_authz(perms={"devices.read"})
        resp = self._get("/api/v1/identity/devices/nonexistent")
        self.assertEqual(resp.status_code, 404)

    @patch("packages.api.identity_routes.devices.repository.get_device", new_callable=AsyncMock)
    def test_no_secrets_in_response(self, mock_get):
        mock_get.return_value = _make_device(1)
        self._setup_authz(perms={"devices.read"})
        resp = self._get("/api/v1/identity/devices/dev-001")
        body = resp.json()
        for secret in ("password", "token", "hmac", "key", "secret", "private"):
            self.assertNotIn(secret, str(body).lower())


if __name__ == "__main__":
    unittest.main()
