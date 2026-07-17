"""
EDGE-001 — Device Onboarding endpoint.

POST /api/v1/device/onboard — no JWT, device_code + hardware_fingerprint.
Returns device_id + access_token + status.

Also: admin endpoint for creating onboarding codes.
Requires: devices.manage permission.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from packages.api.dependencies import get_current_active_user, get_db, require_permission
from packages.domain import repository
from packages.domain.schemas import (
    DeviceCodeCreateRequest,
    DeviceCodeOut,
    DeviceOnboardRequest,
    DeviceOnboardResponse,
)
from packages.security.jwt import create_access_token

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Public — Device self-onboarding
# ---------------------------------------------------------------------------


@router.post("/device/onboard", response_model=DeviceOnboardResponse)
async def device_onboard(
    body: DeviceOnboardRequest,
    db=Depends(get_db),
):
    """Register a physical device using a one-time onboarding code.

    No JWT required — the device_code is the authorization.
    Atomic: UPDATE ... WHERE status='active' RETURNING prevents races.
    Fail-closed: invalid, expired, revoked, or already-used codes are rejected.
    Idempotent: same code + same fingerprint returns existing device identity.
    Cross-retailer: code from retailer A cannot onboard a device in retailer B.
    """
    # Atomic consume: claim the code in one DB round-trip.
    # If two requests race for the same code, only one wins.
    claimed_code = await repository.claim_onboarding_code(db, body.device_code)
    if claimed_code is None:
        # Code not found or not in 'active' state — diagnose why
        code = await repository.get_onboarding_code(db, body.device_code)
        if code is None:
            raise HTTPException(status_code=403, detail={"code": "INVALID_CODE", "message": "Device code not found"})
        now = datetime.now(timezone.utc)
        if code.status == "revoked":
            raise HTTPException(status_code=403, detail={"code": "CODE_REVOKED", "message": "Device code has been revoked"})
        if code.status == "used":
            existing = await repository.get_device_by_fingerprint(db, body.hardware_fingerprint)
            if existing and str(existing.id) == str(code.physical_device_id):
                token = create_access_token(str(existing.id), "device")
                return DeviceOnboardResponse(device_id=str(existing.id), status=existing.status, access_token=token)
            raise HTTPException(status_code=403, detail={"code": "CODE_ALREADY_USED", "message": "Device code has already been used"})
        if code.status == "expired" or (code.expires_at and code.expires_at < now):
            raise HTTPException(status_code=403, detail={"code": "CODE_EXPIRED", "message": "Device code has expired"})
        raise HTTPException(status_code=403, detail={"code": "INVALID_CODE", "message": "Device code is not active"})

    # Code claimed — now validate fingerprint
    existing_device = await repository.get_device_by_fingerprint(db, body.hardware_fingerprint)
    if existing_device:
        # Already registered — idempotent: associate and return existing
        await repository.bind_code_to_device(db, body.device_code, existing_device, body.hardware_fingerprint)
        token = create_access_token(str(existing_device.id), "device")
        return DeviceOnboardResponse(device_id=str(existing_device.id), status=existing_device.status, access_token=token)

    # New device — create and bind
    code = await repository.get_onboarding_code(db, body.device_code)
    device = await repository.create_physical_device_onboard(
        db,
        store_id=code.store_id or "00000000-0000-0000-0000-000000000003",
        device_type_id=code.device_type_id,
        hardware_fingerprint=body.hardware_fingerprint,
        retailer_id=code.retailer_id,
    )
    await db.flush()
    await repository.bind_code_to_device(db, body.device_code, device, body.hardware_fingerprint)

    token = create_access_token(str(device.id), "device")
    logger.info("Device onboarded: %s (retailer=%s, fingerprint=%s...)", device.id, code.retailer_id, body.hardware_fingerprint[:16])
    return DeviceOnboardResponse(device_id=str(device.id), status=device.status, access_token=token)


# ---------------------------------------------------------------------------
# Admin — Create onboarding codes
# ---------------------------------------------------------------------------


@router.post("/identity/device-codes", response_model=DeviceCodeOut, status_code=201)
async def create_device_code(
    body: DeviceCodeCreateRequest,
    db=Depends(get_db),
    _user: dict = Depends(get_current_active_user),
    _perm=Depends(require_permission("devices.manage")),
):
    """Admin: create a one-time device onboarding code.

    Requires: devices.manage permission (system_admin/security_admin).
    The code is bound to a retailer and optionally a store/device_type.
    """
    code = await repository.create_device_onboarding_code(
        db,
        retailer_id=body.retailer_id,
        store_id=body.store_id,
        device_type_id=body.device_type_id,
        created_by=_user["sub"],
        ttl_hours=body.ttl_hours,
    )
    await db.flush()
    return DeviceCodeOut.model_validate(code)
