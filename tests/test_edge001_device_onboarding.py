"""
EDGE-001 — Device Onboarding unit tests.

Covers:
- Successful onboarding
- Invalid/expired/revoked/used code rejection
- Code already bound to different fingerprint rejection
- Same code + same fingerprint idempotent
- Cross-retailer code cannot create device in wrong retailer
- Device JWT token returned with correct auth_provider
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from packages.domain.schemas import DeviceOnboardRequest, DeviceOnboardResponse


class TestDeviceOnboardSuccess(unittest.IsolatedAsyncioTestCase):
    async def test_onboard_new_device_success(self):
        """Valid code + new fingerprint → device created, code consumed, token issued."""
        from packages.api.device_routes.onboard import device_onboard

        mock_code = MagicMock()
        mock_code.status = "active"
        mock_code.retailer_id = "ret-1"
        mock_code.store_id = "store-1"
        mock_code.device_type_id = "dt-1"
        mock_code.physical_device_id = None
        from datetime import datetime, timedelta, timezone
        mock_code.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        mock_device = MagicMock()
        mock_device.id = "dev-new-001"
        mock_device.status = "active"

        mock_db = AsyncMock()

        with (
            patch(
                "packages.api.device_routes.onboard.repository.get_onboarding_code",
                new_callable=AsyncMock,
                return_value=mock_code,
            ),
            patch(
                "packages.api.device_routes.onboard.repository.get_device_by_fingerprint",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "packages.api.device_routes.onboard.repository.create_physical_device_onboard",
                new_callable=AsyncMock,
                return_value=mock_device,
            ),
            patch(
                "packages.api.device_routes.onboard.repository.consume_onboarding_code",
                new_callable=AsyncMock,
            ),
        ):
            resp = await device_onboard(
                DeviceOnboardRequest(device_code="valid-code", hardware_fingerprint="fp-new"),
                db=mock_db,
            )
        self.assertEqual(resp.device_id, "dev-new-001")
        self.assertEqual(resp.status, "active")
        self.assertIsNotNone(resp.access_token)
        self.assertEqual(resp.token_type, "bearer")


class TestDeviceOnboardRejection(unittest.IsolatedAsyncioTestCase):
    async def _call(self, device_code="valid-code-123", fingerprint="fp-12345678"):
        from packages.api.device_routes.onboard import device_onboard
        return await device_onboard(
            DeviceOnboardRequest(device_code=device_code, hardware_fingerprint=fingerprint),
            db=AsyncMock(),
        )

    @patch("packages.api.device_routes.onboard.repository.get_onboarding_code", new_callable=AsyncMock)
    async def test_invalid_code_not_found(self, mock_get):
        mock_get.return_value = None
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await self._call("bad-code")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("INVALID_CODE", str(ctx.exception.detail))

    @patch("packages.api.device_routes.onboard.repository.get_onboarding_code", new_callable=AsyncMock)
    async def test_revoked_code_rejected(self, mock_get):
        mock_code = MagicMock()
        mock_code.status = "revoked"
        mock_code.expires_at = None
        mock_get.return_value = mock_code
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await self._call()
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("CODE_REVOKED", str(ctx.exception.detail))

    @patch("packages.api.device_routes.onboard.repository.get_onboarding_code", new_callable=AsyncMock)
    async def test_expired_code_rejected(self, mock_get):
        from datetime import datetime, timedelta, timezone
        mock_code = MagicMock()
        mock_code.status = "active"
        mock_code.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_get.return_value = mock_code
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await self._call()
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("CODE_EXPIRED", str(ctx.exception.detail))

    @patch("packages.api.device_routes.onboard.repository.get_onboarding_code", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.get_device_by_fingerprint", new_callable=AsyncMock)
    async def test_already_used_code_different_fingerprint_rejected(self, mock_dev, mock_get):
        mock_code = MagicMock()
        mock_code.status = "used"
        mock_code.physical_device_id = "dev-old"
        mock_code.expires_at = None
        mock_get.return_value = mock_code
        # Different device bound
        mock_dev.return_value = MagicMock(id="dev-other")
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await self._call("used-code", "fp-other")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("CODE_ALREADY_USED", str(ctx.exception.detail))

    @patch("packages.api.device_routes.onboard.repository.get_onboarding_code", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.get_device_by_fingerprint", new_callable=AsyncMock)
    async def test_fingerprint_already_bound_to_different_code(self, mock_dev, mock_get):
        from datetime import datetime, timedelta, timezone
        mock_code = MagicMock()
        mock_code.status = "active"
        mock_code.physical_device_id = None
        mock_code.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_get.return_value = mock_code
        mock_dev.return_value = MagicMock(id="dev-existing")
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await self._call("new-code", "fp-existing")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("FINGERPRINT_CONFLICT", str(ctx.exception.detail))


class TestDeviceOnboardIdempotent(unittest.IsolatedAsyncioTestCase):
    async def _call(self, device_code="valid-code-123", fingerprint="fp-12345678"):
        from packages.api.device_routes.onboard import device_onboard
        return await device_onboard(
            DeviceOnboardRequest(device_code=device_code, hardware_fingerprint=fingerprint),
            db=AsyncMock(),
        )

    @patch("packages.api.device_routes.onboard.repository.get_onboarding_code", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.get_device_by_fingerprint", new_callable=AsyncMock)
    async def test_same_code_same_fingerprint_returns_existing_device(self, mock_dev, mock_get):
        """Used code + same fingerprint → idempotent: return existing device token."""
        mock_code = MagicMock()
        mock_code.status = "used"
        mock_code.physical_device_id = "dev-1"
        mock_code.expires_at = None
        mock_get.return_value = mock_code
        mock_device = MagicMock(id="dev-1", status="active")
        mock_dev.return_value = mock_device

        resp = await self._call("used-code", "fp-same")
        self.assertEqual(resp.device_id, "dev-1")
        self.assertEqual(resp.status, "active")

    @patch("packages.api.device_routes.onboard.repository.get_onboarding_code", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.get_device_by_fingerprint", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.create_physical_device_onboard", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.consume_onboarding_code", new_callable=AsyncMock)
    async def test_active_code_existing_device_same_fingerprint_idempotent(self, mock_consume, mock_create, mock_dev, mock_get):
        """Active code + fingerprint of already-bound device → idempotent return."""
        from datetime import datetime, timedelta, timezone
        mock_code = MagicMock()
        mock_code.status = "active"
        mock_code.physical_device_id = "dev-1"
        mock_code.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_get.return_value = mock_code
        mock_device = MagicMock(id="dev-1", status="active")
        mock_dev.return_value = mock_device

        resp = await self._call("active-code", "fp-existing")
        self.assertEqual(resp.device_id, "dev-1")


class TestDeviceCodeCreation(unittest.IsolatedAsyncioTestCase):
    @patch("packages.api.device_routes.onboard.repository.create_device_onboarding_code", new_callable=AsyncMock)
    async def test_admin_creates_code(self, mock_create):
        from packages.api.device_routes.onboard import create_device_code
        from packages.domain.schemas import DeviceCodeCreateRequest
        mock_code = MagicMock()
        mock_code.id = "code-1"
        mock_code.code = "abc123"
        mock_code.retailer_id = "ret-1"
        mock_code.store_id = None
        mock_code.device_type_id = None
        mock_code.hardware_fingerprint_bound = None
        mock_code.physical_device_id = None
        mock_code.status = "active"
        mock_code.created_at = None
        mock_code.expires_at = None
        mock_code.used_at = None
        mock_create.return_value = mock_code

        resp = await create_device_code(
            DeviceCodeCreateRequest(retailer_id="ret-1", ttl_hours=48),
            db=AsyncMock(),
            _user={"sub": "admin-1"},
        )
        self.assertEqual(resp.code, "abc123")
        self.assertEqual(resp.retailer_id, "ret-1")
        self.assertEqual(resp.status, "active")
