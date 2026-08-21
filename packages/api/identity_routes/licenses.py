"""EPIC-L — Licensing report API (Layer 1, task 001A4).

``GET /licenses/report?year=YYYY&month=M`` — read-only license + usage + open
seats. Requires ``license.read`` (system_admin/security_admin). The server-side
service/admin RLS context is applied via the accepted ``set_rls_context``
dependency; under NOBYPASSRLS the license tables and ``physical_devices`` are
only visible with that context. The report performs NO commit/mutation.
"""

from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from packages.api.dependencies import get_db, require_permission, set_rls_context
from packages.domain.licensing_repository import (
    _month_bounds,
    get_license_report,
)
from packages.domain.schemas import LicenseReportOut

router = APIRouter()


@router.get("/licenses/report", response_model=LicenseReportOut)
async def license_report(
    year: int,
    month: int,
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("license.read")),
    _rls=Depends(set_rls_context),
):
    """Read-only license report for the given calendar month (UTC)."""
    try:
        _month_bounds(year, month)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_MONTH", "message": str(exc)},
        )

    now = datetime.now(timezone.utc)
    report = await get_license_report(db, year=year, month=month, now=now)
    return LicenseReportOut(**asdict(report))
