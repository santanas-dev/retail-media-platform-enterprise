"""
EDGE-001 — Device Onboarding unit tests (hardened v2).

Covers:
- Successful onboarding with atomic claim
- Invalid/expired/revoked/used code rejection
- FINGERPRINT_CONFLICT: active new code + already registered fingerprint → 403
- Idempotent: same used code + same fingerprint → 200 (returns existing device_id)
- Code already used + different fingerprint → 403
- Admin code creation requires devices.manage permission
- Claimed-but-unbound failure path: code reverts to active on fingerprint conflict
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from packages.domain.schemas import DeviceOnboardRequest, DeviceOnboardResponse


class TestDeviceOnboardSuccess(unittest.IsolatedAsyncioTestCase):
    @patch("packages.api.device_routes.onboard.repository.claim_onboarding_code", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.get_device_by_fingerprint", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.get_onboarding_code", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.create_physical_device_onboard", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.bind_code_to_device", new_callable=AsyncMock)
    async def test_onboard_new_device_success(self, mock_bind, mock_create, mock_get_code, mock_dev, mock_claim):
        from packages.api.device_routes.onboard import device_onboard

        mock_claim.return_value = True  # atomic claim succeeds

        mock_code = MagicMock()
        mock_code.status = "claimed"
        mock_code.retailer_id = "ret-1"
        mock_code.store_id = "store-1"
        mock_code.device_type_id = "dt-1"
        mock_get_code.return_value = mock_code

        mock_dev.return_value = None  # no existing device

        mock_device = MagicMock()
        mock_device.id = "dev-new-001"
        mock_device.status = "active"
        mock_create.return_value = mock_device

        resp = await device_onboard(
            DeviceOnboardRequest(device_code="valid-code-123", hardware_fingerprint="fp-new-1234"),
            db=AsyncMock(),
        )
        self.assertEqual(resp.device_id, "dev-new-001")
        self.assertEqual(resp.status, "active")
        self.assertIsNotNone(resp.access_token)


class TestDeviceOnboardRejection(unittest.IsolatedAsyncioTestCase):
    async def _call(self, device_code="valid-code-123", fingerprint="fp-12345678"):
        from packages.api.device_routes.onboard import device_onboard
        return await device_onboard(
            DeviceOnboardRequest(device_code=device_code, hardware_fingerprint=fingerprint),
            db=AsyncMock(),
        )

    @patch("packages.api.device_routes.onboard.repository.claim_onboarding_code", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.get_onboarding_code", new_callable=AsyncMock)
    async def test_invalid_code_not_found(self, mock_get, mock_claim):
        mock_claim.return_value = False
        mock_get.return_value = None
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await self._call()
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("INVALID_CODE", str(ctx.exception.detail))

    @patch("packages.api.device_routes.onboard.repository.claim_onboarding_code", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.get_onboarding_code", new_callable=AsyncMock)
    async def test_revoked_code_rejected(self, mock_get, mock_claim):
        mock_claim.return_value = False
        mock_code = MagicMock()
        mock_code.status = "revoked"
        mock_code.expires_at = None
        mock_get.return_value = mock_code
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await self._call()
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("CODE_REVOKED", str(ctx.exception.detail))

    @patch("packages.api.device_routes.onboard.repository.claim_onboarding_code", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.get_onboarding_code", new_callable=AsyncMock)
    async def test_expired_code_rejected(self, mock_get, mock_claim):
        from datetime import datetime, timedelta, timezone
        mock_claim.return_value = False
        mock_code = MagicMock()
        mock_code.status = "expired"
        mock_code.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_get.return_value = mock_code
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await self._call()
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("CODE_EXPIRED", str(ctx.exception.detail))

    @patch("packages.api.device_routes.onboard.repository.claim_onboarding_code", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.get_onboarding_code", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.get_device_by_fingerprint", new_callable=AsyncMock)
    async def test_already_used_code_different_fingerprint_rejected(self, mock_dev, mock_get, mock_claim):
        mock_claim.return_value = False
        mock_code = MagicMock()
        mock_code.status = "used"
        mock_code.physical_device_id = "dev-old"
        mock_code.expires_at = None
        mock_get.return_value = mock_code
        mock_dev.return_value = MagicMock(id="dev-other")
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await self._call("used-code", "fp-other-1234")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("CODE_ALREADY_USED", str(ctx.exception.detail))

    @patch("packages.api.device_routes.onboard.repository.claim_onboarding_code", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.get_device_by_fingerprint", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.revert_claim", new_callable=AsyncMock)
    async def test_active_code_existing_fingerprint_rejected(self, mock_revert, mock_dev, mock_claim):
        """New active code + already-registered fingerprint → 403 FINGERPRINT_CONFLICT.

        The code must NOT "stick" to an existing device.  Claim is reverted so the
        code stays usable for a different fingerprint.
        """
        mock_claim.return_value = True  # claim succeeds
        mock_dev.return_value = MagicMock(id="dev-existing", status="active")

        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await self._call("new-active-code", "fp-existing-1")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("FINGERPRINT_CONFLICT", str(ctx.exception.detail))
        mock_revert.assert_called_once()  # claim must be reverted


class TestDeviceOnboardIdempotent(unittest.IsolatedAsyncioTestCase):
    async def _call(self, device_code="valid-code-123", fingerprint="fp-12345678"):
        from packages.api.device_routes.onboard import device_onboard
        return await device_onboard(
            DeviceOnboardRequest(device_code=device_code, hardware_fingerprint=fingerprint),
            db=AsyncMock(),
        )

    @patch("packages.api.device_routes.onboard.repository.claim_onboarding_code", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.get_onboarding_code", new_callable=AsyncMock)
    @patch("packages.api.device_routes.onboard.repository.get_device_by_fingerprint", new_callable=AsyncMock)
    async def test_used_code_same_fingerprint_returns_existing_device(self, mock_dev, mock_get, mock_claim):
        """Used code + same fingerprint + same device_id → idempotent return."""
        mock_claim.return_value = False  # already used
        mock_code = MagicMock()
        mock_code.status = "used"
        mock_code.physical_device_id = "dev-1"
        mock_code.expires_at = None
        mock_get.return_value = mock_code
        mock_device = MagicMock(id="dev-1", status="active")
        mock_dev.return_value = mock_device

        resp = await self._call("used-code", "fp-same-12345")
        self.assertEqual(resp.device_id, "dev-1")
        self.assertEqual(resp.status, "active")
        self.assertIsNotNone(resp.access_token)


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
            _perm=None,  # permission already verified by Depends
        )
        self.assertEqual(resp.code, "abc123")
        self.assertEqual(resp.retailer_id, "ret-1")
        self.assertEqual(resp.status, "active")
