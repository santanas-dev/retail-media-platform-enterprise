"""
Identity API — Fleet / Device Health (S-070).
"""

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
    db=Depends(get_db),
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
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("devices.read")),
    _rls=Depends(set_rls_context),
):
    counts = await repository.get_device_summary(db)
    return DeviceSummaryOut(**counts)


@router.get("/devices/{device_id}", response_model=DeviceOut)
async def get_device(
    device_id: str,
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("devices.read")),
    _rls=Depends(set_rls_context),
):
    device = await repository.get_device(db, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return DeviceOut.model_validate(device)
