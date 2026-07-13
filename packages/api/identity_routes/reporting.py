"""
Identity API — PoP Reporting (Phase 4.3d — ADR-017 §6).
"""

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from starlette.responses import Response

from packages.api.dependencies import (
    get_db,
    get_scope_context,
    require_scoped_permission,
    set_rls_context,
)
from packages.domain import repository
from packages.domain.scopes import ScopeContext
from packages.domain.schemas import (
    CampaignPopByDayOut,
    CampaignPopBySurfaceOut,
    CampaignPopSummaryOut,
)

from .common import _require_campaign_visible

router = APIRouter()


@router.get("/campaigns/{campaign_id}/pop/summary", response_model=CampaignPopSummaryOut)
async def get_campaign_pop_summary(
    campaign_id: str,
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    await _require_campaign_visible(db, campaign_id, scope)
    result = await repository.get_campaign_pop_summary(db, campaign_id)
    return CampaignPopSummaryOut(
        campaign_id=campaign_id,
        impressions_count=result["impressions_count"],
        total_duration_ms=result["total_duration_ms"],
        first_rendered_at=result["first_rendered_at"],
        last_rendered_at=result["last_rendered_at"],
        unique_devices=result["unique_devices"],
        unique_surfaces=result["unique_surfaces"],
    )


@router.get("/campaigns/{campaign_id}/pop/by-day", response_model=list[CampaignPopByDayOut])
async def get_campaign_pop_by_day(
    campaign_id: str,
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    await _require_campaign_visible(db, campaign_id, scope)
    rows = await repository.list_campaign_pop_by_day(db, campaign_id)
    return [
        CampaignPopByDayOut(
            date=str(row["date"]),
            impressions_count=row["impressions_count"],
            total_duration_ms=row["total_duration_ms"],
        )
        for row in rows
    ]


@router.get("/campaigns/{campaign_id}/pop/by-surface", response_model=list[CampaignPopBySurfaceOut])
async def get_campaign_pop_by_surface(
    campaign_id: str,
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    await _require_campaign_visible(db, campaign_id, scope)
    rows = await repository.list_campaign_pop_by_surface(db, campaign_id)
    return [
        CampaignPopBySurfaceOut(
            surface_id=row["surface_id"],
            impressions_count=row["impressions_count"],
            total_duration_ms=row["total_duration_ms"],
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# S-040 — PoP Report CSV Export
# ---------------------------------------------------------------------------


@router.get("/campaigns/{campaign_id}/pop/export")
async def export_campaign_pop_csv(
    campaign_id: str,
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    campaign = await _require_campaign_visible(db, campaign_id, scope)

    summary = await repository.get_campaign_pop_summary(db, campaign_id)
    by_day = await repository.list_campaign_pop_by_day(db, campaign_id)
    by_surface = await repository.list_campaign_pop_by_surface(db, campaign_id)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    safe_code = campaign.code.replace('"', "").replace("'", "").replace("/", "_")[:64]

    buf = io.StringIO()
    buf.write("\ufeff")  # UTF-8 BOM for Excel
    w = csv.writer(buf)

    # Header
    w.writerow(["Отчёт по показам"])
    w.writerow([f"Кампания: {campaign.name} ({campaign.code})"])
    w.writerow([f"Сформирован: {now}"])
    w.writerow([])

    # Summary
    w.writerow(["Сводка"])
    w.writerow(["Показы", summary["impressions_count"]])
    w.writerow(["Общая длительность (мс)", summary["total_duration_ms"]])
    w.writerow(["Устройств", summary["unique_devices"]])
    w.writerow(["Поверхностей", summary["unique_surfaces"]])
    if summary["first_rendered_at"]:
        w.writerow(["Первый показ", str(summary["first_rendered_at"])])
    if summary["last_rendered_at"]:
        w.writerow(["Последний показ", str(summary["last_rendered_at"])])
    w.writerow([])

    # By Day
    w.writerow(["По дням"])
    w.writerow(["Дата", "Показы", "Длительность (мс)"])
    for row in by_day:
        w.writerow([str(row["date"]), row["impressions_count"], row["total_duration_ms"]])
    w.writerow([])

    # By Surface
    w.writerow(["По поверхностям"])
    w.writerow(["Поверхность", "Показы", "Длительность (мс)"])
    for row in by_surface:
        w.writerow([row["surface_id"], row["impressions_count"], row["total_duration_ms"]])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_code}_pop_report.csv"',
        },
    )
