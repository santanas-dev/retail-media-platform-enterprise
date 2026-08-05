"""
Commerce Contour 2 Repository — async helpers + pricing choke-point.

COMMERCE-CONTUR2-001A1: backend foundation without UI.
"""
from datetime import date, datetime
from decimal import Decimal
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from packages.domain import (
    CommerceOrderStatus,
    CommercePaymentStatus,
    CommerceTariffStatus,
    BillingUnit,
)
from packages.domain.models import (
    CommerceTariffVersion,
    CommercePriceItem,
    CommerceOrder,
    CommerceOrderLine,
    DisplaySurface,
)
from packages.domain.schemas import (
    CommerceQuoteLine,
    CommerceQuoteRequest,
    CommerceQuoteResponse,
)


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ── Tariff helpers ──


async def get_active_tariff_version(
    session: AsyncSession, tariff_version_id: str | None = None,
) -> CommerceTariffVersion | None:
    """Return the active tariff version or raise if not found/not active."""
    if tariff_version_id:
        stmt = select(CommerceTariffVersion).where(
            CommerceTariffVersion.id == tariff_version_id,
            CommerceTariffVersion.status == CommerceTariffStatus.ACTIVE,
        )
    else:
        # Pick the latest active tariff version valid today
        today = date.today()
        stmt = (
            select(CommerceTariffVersion)
            .where(
                CommerceTariffVersion.status == CommerceTariffStatus.ACTIVE,
                CommerceTariffVersion.valid_from <= today,
            )
            .order_by(CommerceTariffVersion.valid_from.desc())
            .limit(1)
        )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_price_items(
    session: AsyncSession, tariff_version_id: str, surface_ids: list[str],
) -> dict[str, CommercePriceItem]:
    """Return {surface_id: CommercePriceItem} for the given tariff version and surfaces."""
    stmt = select(CommercePriceItem).where(
        CommercePriceItem.tariff_version_id == tariff_version_id,
        CommercePriceItem.surface_id.in_(surface_ids),
    )
    result = await session.execute(stmt)
    return {pi.surface_id: pi for pi in result.scalars().all()}


# ── Pricing choke-point ──


async def calculate_order_quote(
    session: AsyncSession,
    request: CommerceQuoteRequest,
) -> CommerceQuoteResponse:
    """Single pricing choke-point for all commerce flows.

    Returns a quote with per-line amounts and total.  Errors are accumulated
    per-line (missing price, inactive tariff) and returned in .errors.
    """
    errors: list[str] = []
    quote_lines: list[CommerceQuoteLine] = []

    # 1. Validate tariff version
    tariff = await get_active_tariff_version(session, request.tariff_version_id)
    if tariff is None:
        return CommerceQuoteResponse(
            tariff_version_id=request.tariff_version_id,
            currency="RUB",
            errors=[f"Tariff version {request.tariff_version_id} not found or not active"],
        )

    currency = tariff.currency

    # 2. Collect surface IDs from request lines
    surface_ids = list({line.surface_id for line in request.lines})

    # 3. Load price items
    price_map = await list_price_items(session, tariff.id, surface_ids)

    # 4. Verify surfaces exist
    stmt = select(DisplaySurface.id).where(DisplaySurface.id.in_(surface_ids))
    result = await session.execute(stmt)
    existing_surfaces = {row[0] for row in result.all()}

    # 5. Calculate per-line
    total = Decimal("0.00")
    for req_line in request.lines:
        if req_line.surface_id not in existing_surfaces:
            quote_lines.append(CommerceQuoteLine(
                surface_id=req_line.surface_id,
                date_from=req_line.date_from,
                date_to=req_line.date_to,
                quantity_days=req_line.quantity_days,
                unit_price_amount=0.0,
                line_amount=0.0,
                error=f"Surface {req_line.surface_id} not found",
            ))
            errors.append(f"Surface {req_line.surface_id} not found")
            continue

        price_item = price_map.get(req_line.surface_id)
        if price_item is None:
            quote_lines.append(CommerceQuoteLine(
                surface_id=req_line.surface_id,
                date_from=req_line.date_from,
                date_to=req_line.date_to,
                quantity_days=req_line.quantity_days,
                unit_price_amount=0.0,
                line_amount=0.0,
                error=f"No price for surface {req_line.surface_id} in tariff {tariff.code}",
            ))
            errors.append(
                f"No price for surface {req_line.surface_id} in tariff {tariff.code}"
            )
            continue

        unit_price = Decimal(str(price_item.unit_price_amount))
        line_amount = unit_price * req_line.quantity_days
        total += line_amount

        quote_lines.append(CommerceQuoteLine(
            surface_id=req_line.surface_id,
            date_from=req_line.date_from,
            date_to=req_line.date_to,
            quantity_days=req_line.quantity_days,
            unit_price_amount=float(unit_price),
            line_amount=float(line_amount),
        ))

    return CommerceQuoteResponse(
        tariff_version_id=tariff.id,
        currency=currency,
        lines=quote_lines,
        total_amount=float(total),
        errors=errors,
    )
