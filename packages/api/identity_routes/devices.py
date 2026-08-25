"""
Identity API — Fleet / Device Health (S-070).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from packages.api.dependencies import (
    get_db,
    require_permission,
    set_rls_context,
)
from packages.domain import repository
from packages.domain.schemas import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    DeviceDecommissionRequest,
    DeviceDecommissionResponse,
    DeviceOut,
    DeviceSummaryOut,
    PaginatedDevices,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Device fleet
# ---------------------------------------------------------------------------


@router.get("/devices", response_model=PaginatedDevices)
async def list_devices(
    status: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    db=Depends(get_db, scope="function"),
    _claims: dict = Depends(require_permission("devices.read")),
    _rls=Depends(set_rls_context),
):
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    items, total = await repository.list_devices(
        db, limit=limit, offset=offset, status=status,
    )
    return PaginatedDevices(
        items=[DeviceOut.model_validate(d) for d in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/devices/summary", response_model=DeviceSummaryOut)
async def device_summary(
    db=Depends(get_db, scope="function"),
    _claims: dict = Depends(require_permission("devices.read")),
    _rls=Depends(set_rls_context),
):
    counts = await repository.get_device_summary(db)
    return DeviceSummaryOut(**counts)


@router.get("/devices/{device_id}", response_model=DeviceOut)
async def get_device(
    device_id: str,
    db=Depends(get_db, scope="function"),
    _claims: dict = Depends(require_permission("devices.read")),
    _rls=Depends(set_rls_context),
):
    device = await repository.get_device(db, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return DeviceOut.model_validate(device)


@router.post("/devices/{device_id}/decommission", response_model=DeviceDecommissionResponse)
async def decommission_device(
    device_id: str,
    body: DeviceDecommissionRequest,
    db=Depends(get_db, scope="function"),
    _claims: dict = Depends(require_permission("devices.manage")),
    _rls=Depends(set_rls_context),
):
    """Decommission a device: confirmed ``active → inactive`` transition.

    Requires ``devices.manage`` (system_admin/security_admin). Releasing the
    device's open license seat is a side effect of the confirmed transition —
    there is no separate manual seat-release endpoint. The license state
    (expired/revoked/missing) never blocks decommission.
    """
    from packages.domain import licensing_service

    result = await licensing_service.decommission_device(
        db,
        device_id=device_id,
        changed_by=_claims["sub"],
        reason=body.reason,
        now=datetime.now(timezone.utc),
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Device not found")
    if result.error:
        raise HTTPException(
            status_code=409,
            detail={"code": result.error, "message": result.message},
        )
    return DeviceDecommissionResponse(
        device_id=result.device_id,
        status=result.status,
        seat_released=result.seat_released,
        released_at=result.released_at,
        transitioned=result.transitioned,
        anomaly=result.anomaly,
    )
