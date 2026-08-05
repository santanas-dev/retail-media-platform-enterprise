"""
Commerce Contour 2 Repository — async helpers + pricing choke-point.

COMMERCE-CONTUR2-001A1: backend foundation without UI.
"""
from datetime import date, datetime
from decimal import Decimal
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
    CommerceOrderLineCreate,
)
from packages.domain.repository import _assert_org_in_scope


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


# ── Tariff CRUD ──


async def create_tariff_version(
    session: AsyncSession,
    *,
    code: str,
    name: str,
    valid_from: date,
    valid_to: date | None = None,
    currency: str = "RUB",
) -> CommerceTariffVersion:
    tv = CommerceTariffVersion(
        id=_new_uuid(),
        code=code,
        name=name,
        status=CommerceTariffStatus.DRAFT,
        valid_from=valid_from,
        valid_to=valid_to,
        currency=currency,
    )
    session.add(tv)
    await session.flush()
    return tv


async def list_tariff_versions(
    session: AsyncSession,
) -> list[CommerceTariffVersion]:
    stmt = select(CommerceTariffVersion).order_by(CommerceTariffVersion.valid_from.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_tariff_version(
    session: AsyncSession, tariff_id: str,
) -> CommerceTariffVersion | None:
    stmt = select(CommerceTariffVersion).where(CommerceTariffVersion.id == tariff_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_tariff_version(
    session: AsyncSession,
    tariff_id: str,
    *,
    name: str | None = None,
    status: str | None = None,
    valid_from: date | None = None,
    valid_to: date | None = None,
) -> CommerceTariffVersion | None:
    tv = await get_tariff_version(session, tariff_id)
    if tv is None:
        return None
    if name is not None:
        tv.name = name
    if status is not None:
        tv.status = status
    if valid_from is not None:
        tv.valid_from = valid_from
    if valid_to is not None:
        tv.valid_to = valid_to
    tv.updated_at = _utcnow_compat()
    return tv


# ── Price item CRUD ──


async def create_price_item(
    session: AsyncSession,
    *,
    tariff_version_id: str,
    surface_id: str,
    unit_price_amount: float,
    currency: str = "RUB",
    billing_unit: str = "surface_day",
) -> CommercePriceItem:
    pi = CommercePriceItem(
        id=_new_uuid(),
        tariff_version_id=tariff_version_id,
        surface_id=surface_id,
        billing_unit=billing_unit,
        unit_price_amount=Decimal(str(unit_price_amount)),
        currency=currency,
    )
    session.add(pi)
    await session.flush()
    return pi


async def list_price_items_for_tariff(
    session: AsyncSession, tariff_version_id: str,
) -> list[CommercePriceItem]:
    stmt = (
        select(CommercePriceItem)
        .where(CommercePriceItem.tariff_version_id == tariff_version_id)
        .order_by(CommercePriceItem.surface_id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_price_item(
    session: AsyncSession, price_item_id: str,
) -> CommercePriceItem | None:
    stmt = select(CommercePriceItem).where(CommercePriceItem.id == price_item_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_price_item(
    session: AsyncSession,
    price_item_id: str,
    *,
    unit_price_amount: float | None = None,
    billing_unit: str | None = None,
) -> CommercePriceItem | None:
    pi = await get_price_item(session, price_item_id)
    if pi is None:
        return None
    if unit_price_amount is not None:
        pi.unit_price_amount = Decimal(str(unit_price_amount))
    if billing_unit is not None:
        pi.billing_unit = billing_unit
    pi.updated_at = _utcnow_compat()
    return pi


# ── Status transition guard ──


_ORDER_TRANSITIONS: dict[str, set[str]] = {
    CommerceOrderStatus.DRAFT: {CommerceOrderStatus.OFFERED},
    CommerceOrderStatus.OFFERED: {CommerceOrderStatus.BOOKED, CommerceOrderStatus.CANCELLED},
    CommerceOrderStatus.BOOKED: {CommerceOrderStatus.CONFIRMED, CommerceOrderStatus.CANCELLED},
    CommerceOrderStatus.CONFIRMED: {CommerceOrderStatus.CLOSED, CommerceOrderStatus.CANCELLED},
    CommerceOrderStatus.CLOSED: set(),
    CommerceOrderStatus.CANCELLED: set(),
}

_VALID_PAYMENT_STATUSES = frozenset({
    CommercePaymentStatus.NOT_REQUIRED,
    CommercePaymentStatus.UNPAID,
    CommercePaymentStatus.PARTIAL,
    CommercePaymentStatus.PAID,
    CommercePaymentStatus.OVERDUE,
})


def validate_order_transition(current_status: str, new_status: str) -> None:
    """Raise ValueError if the transition is not allowed."""
    allowed = _ORDER_TRANSITIONS.get(current_status)
    if allowed is None:
        raise ValueError(f"Unknown order status: {current_status}")
    if new_status not in allowed:
        raise ValueError(
            f"Cannot transition order from {current_status} to {new_status}. "
            f"Allowed: {sorted(allowed)}"
        )


# ── Order CRUD ──


async def create_order(
    session: AsyncSession,
    *,
    advertiser_organization_id: str,
    tariff_version_id: str,
    lines: list[CommerceOrderLineCreate],
    scope_advertiser_ids: frozenset[str] | None = None,
) -> CommerceOrder:
    """Create an order with lines. Pricing goes through calculate_order_quote()."""
    from datetime import datetime as dt, timezone as tz

    _assert_org_in_scope(advertiser_organization_id, scope_advertiser_ids)

    # 1. Validate tariff
    tariff = await get_active_tariff_version(session, tariff_version_id)
    if tariff is None:
        raise ValueError(f"Tariff version {tariff_version_id} is not active")

    # 2. Calculate quote
    quote_request = CommerceQuoteRequest(
        tariff_version_id=tariff_version_id,
        advertiser_organization_id=advertiser_organization_id,
        lines=lines,
    )
    quote = await calculate_order_quote(session, quote_request)
    if quote.errors:
        raise ValueError(f"Quote errors: {'; '.join(quote.errors)}")

    # 3. Generate order code
    now = dt.now(tz.utc)
    code = f"ORD-{now.strftime('%Y%m%d')}-{_new_uuid()[:8].upper()}"

    order = CommerceOrder(
        id=_new_uuid(),
        advertiser_organization_id=advertiser_organization_id,
        code=code,
        status=CommerceOrderStatus.DRAFT,
        payment_status=CommercePaymentStatus.NOT_REQUIRED,
        tariff_version_id=tariff_version_id,
        total_amount=Decimal(str(quote.total_amount)),
        currency=tariff.currency,
    )
    session.add(order)

    # 4. Create order lines from quote
    for ql in quote.lines:
        line = CommerceOrderLine(
            id=_new_uuid(),
            order_id=order.id,
            surface_id=ql.surface_id,
            date_from=ql.date_from,
            date_to=ql.date_to,
            quantity_days=ql.quantity_days,
            unit_price_amount=Decimal(str(ql.unit_price_amount)),
            line_amount=Decimal(str(ql.line_amount)),
        )
        session.add(line)

    await session.flush()
    # Eager-load lines so serialization doesn't lazy-load outside session scope
    await session.refresh(order, ["lines"])
    return order


async def list_orders(
    session: AsyncSession,
    scope_advertiser_ids: frozenset[str] | None = None,
) -> list[CommerceOrder]:
    stmt = select(CommerceOrder).options(selectinload(CommerceOrder.lines)).order_by(CommerceOrder.created_at.desc())
    result = await session.execute(stmt)
    orders = result.scalars().all()

    if scope_advertiser_ids is not None:
        orders = [
            o for o in orders
            if o.advertiser_organization_id in scope_advertiser_ids
        ]
    return list(orders)


async def get_order(
    session: AsyncSession,
    order_id: str,
    scope_advertiser_ids: frozenset[str] | None = None,
) -> CommerceOrder | None:
    stmt = select(CommerceOrder).options(selectinload(CommerceOrder.lines)).where(CommerceOrder.id == order_id)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    if order is None:
        return None
    _assert_org_in_scope(order.advertiser_organization_id, scope_advertiser_ids)
    return order


async def update_order_status(
    session: AsyncSession,
    order_id: str,
    *,
    new_status: str,
    payment_status: str | None = None,
    scope_advertiser_ids: frozenset[str] | None = None,
) -> CommerceOrder | None:
    """Transition order to a new status. Enforces the transition guard."""
    stmt = select(CommerceOrder).options(selectinload(CommerceOrder.lines)).where(CommerceOrder.id == order_id)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    if order is None:
        return None

    _assert_org_in_scope(order.advertiser_organization_id, scope_advertiser_ids)

    if new_status:
        validate_order_transition(order.status, new_status)
        order.status = new_status
        order.updated_at = _utcnow_compat()

    if payment_status is not None:
        if payment_status not in _VALID_PAYMENT_STATUSES:
            raise ValueError(f"Invalid payment status: {payment_status}")
        order.payment_status = payment_status

    return order


def _utcnow_compat() -> datetime:
    from datetime import datetime as dt, timezone as tz
    return dt.now(tz.utc)
