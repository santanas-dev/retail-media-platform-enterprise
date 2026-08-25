"""
Commerce Contour 2 API — tariff versions, price items, quotes, orders.

COMMERCE-CONTUR2-001A2: backend API/RLS/order CRUD foundation.
No UI — operator-only endpoints for tariff/price management and order tracking.
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from packages.api.dependencies import (
    get_db,
    require_scoped_permission,
    set_rls_context,
    get_current_active_user,
)
from packages.api.identity_routes.common import _scope_ids
from packages.domain import commerce_repository as crepo
from packages.domain.exceptions import ScopeError
from packages.domain.schemas import (
    CommerceTariffVersionCreate,
    CommerceTariffVersionOut,
    CommerceTariffVersionUpdate,
    CommercePriceItemCreate,
    CommercePriceItemOut,
    CommercePriceItemUpdate,
    CommerceOrderCreate,
    CommerceOrderOut,
    CommerceOrderUpdate,
    CommerceOrderLineOut,
    CommerceQuoteRequest,
    CommerceQuoteResponse,
)

router = APIRouter()


# ── Tariff versions ──


@router.get("/commerce/tariff-versions", response_model=list[CommerceTariffVersionOut])
async def list_tariff_versions(
    db=Depends(get_db, scope="function"),
    _perm=Depends(require_scoped_permission("commerce.tariff_read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items = await crepo.list_tariff_versions(db)
    return [CommerceTariffVersionOut.model_validate(tv) for tv in items]


@router.post("/commerce/tariff-versions", response_model=CommerceTariffVersionOut, status_code=201)
async def create_tariff_version(
    body: CommerceTariffVersionCreate,
    db=Depends(get_db, scope="function"),
    _perm=Depends(require_scoped_permission("commerce.tariff_manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    tv = await crepo.create_tariff_version(
        db,
        code=body.code,
        name=body.name,
        valid_from=body.valid_from,
        valid_to=body.valid_to,
        currency=body.currency,
    )
    return CommerceTariffVersionOut.model_validate(tv)


@router.patch("/commerce/tariff-versions/{tariff_id}", response_model=CommerceTariffVersionOut)
async def update_tariff_version(
    tariff_id: str,
    body: CommerceTariffVersionUpdate,
    db=Depends(get_db, scope="function"),
    _perm=Depends(require_scoped_permission("commerce.tariff_manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    tv = await crepo.update_tariff_version(
        db,
        tariff_id,
        name=body.name,
        status=body.status,
        valid_from=body.valid_from,
        valid_to=body.valid_to,
    )
    if tv is None:
        raise HTTPException(status_code=404, detail="Tariff version not found")
    return CommerceTariffVersionOut.model_validate(tv)


# ── Price items ──


@router.get("/commerce/price-items", response_model=list[CommercePriceItemOut])
async def list_price_items(
    tariff_version_id: str = Query(...),
    db=Depends(get_db, scope="function"),
    _perm=Depends(require_scoped_permission("commerce.tariff_read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items = await crepo.list_price_items_for_tariff(db, tariff_version_id)
    return [CommercePriceItemOut.model_validate(pi) for pi in items]


@router.post("/commerce/price-items", response_model=CommercePriceItemOut, status_code=201)
async def create_price_item(
    body: CommercePriceItemCreate,
    tariff_version_id: str = Query(...),
    db=Depends(get_db, scope="function"),
    _perm=Depends(require_scoped_permission("commerce.tariff_manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    pi = await crepo.create_price_item(
        db,
        tariff_version_id=tariff_version_id,
        surface_id=body.surface_id,
        unit_price_amount=body.unit_price_amount,
        currency=body.currency,
        billing_unit=body.billing_unit,
    )
    return CommercePriceItemOut.model_validate(pi)


@router.patch("/commerce/price-items/{price_item_id}", response_model=CommercePriceItemOut)
async def update_price_item(
    price_item_id: str,
    body: CommercePriceItemUpdate,
    db=Depends(get_db, scope="function"),
    _perm=Depends(require_scoped_permission("commerce.tariff_manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    pi = await crepo.update_price_item(
        db,
        price_item_id,
        unit_price_amount=body.unit_price_amount,
        billing_unit=body.billing_unit,
    )
    if pi is None:
        raise HTTPException(status_code=404, detail="Price item not found")
    return CommercePriceItemOut.model_validate(pi)


# ── Quote ──


@router.post("/commerce/quote", response_model=CommerceQuoteResponse)
async def quote(
    body: CommerceQuoteRequest,
    db=Depends(get_db, scope="function"),
    _perm=Depends(require_scoped_permission("commerce.order_read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    quote = await crepo.calculate_order_quote(db, body)
    return quote


# ── Orders ──


def _serialize_order(order) -> CommerceOrderOut:
    return CommerceOrderOut(
        id=order.id,
        advertiser_organization_id=order.advertiser_organization_id,
        code=order.code,
        status=order.status,
        payment_status=order.payment_status,
        tariff_version_id=order.tariff_version_id,
        total_amount=float(order.total_amount) if order.total_amount else None,
        currency=order.currency,
        created_at=order.created_at,
        updated_at=order.updated_at,
        lines=[
            CommerceOrderLineOut(
                id=ln.id,
                order_id=ln.order_id,
                surface_id=ln.surface_id,
                date_from=ln.date_from,
                date_to=ln.date_to,
                quantity_days=ln.quantity_days,
                unit_price_amount=float(ln.unit_price_amount),
                line_amount=float(ln.line_amount),
            )
            for ln in (order.lines or [])
        ],
    )


@router.get("/commerce/orders", response_model=list[CommerceOrderOut])
async def list_orders(
    db=Depends(get_db, scope="function"),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("commerce.order_read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    orders = await crepo.list_orders(db, scope_advertiser_ids=_scope_ids(scope))
    return [_serialize_order(o) for o in orders]


@router.post("/commerce/orders", response_model=CommerceOrderOut, status_code=201)
async def create_order(
    body: CommerceOrderCreate,
    db=Depends(get_db, scope="function"),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("commerce.order_manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    try:
        order = await crepo.create_order(
            db,
            advertiser_organization_id=body.advertiser_organization_id,
            tariff_version_id=body.tariff_version_id or "",
            lines=body.lines,
            scope_advertiser_ids=_scope_ids(scope),
        )
    except ScopeError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _serialize_order(order)


@router.get("/commerce/orders/{order_id}", response_model=CommerceOrderOut)
async def get_order(
    order_id: str,
    db=Depends(get_db, scope="function"),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("commerce.order_read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    try:
        order = await crepo.get_order(db, order_id, scope_advertiser_ids=_scope_ids(scope))
    except ScopeError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return _serialize_order(order)


@router.patch("/commerce/orders/{order_id}", response_model=CommerceOrderOut)
async def update_order(
    order_id: str,
    body: CommerceOrderUpdate,
    db=Depends(get_db, scope="function"),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("commerce.order_manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Update order status or payment status. Enforces transition guard."""
    if body.new_status is None and body.payment_status is None:
        raise HTTPException(status_code=422, detail="At least one of new_status or payment_status required")
    try:
        order = await crepo.update_order_status(
            db,
            order_id,
            new_status=body.new_status or "",
            payment_status=body.payment_status,
            scope_advertiser_ids=_scope_ids(scope),
        )
    except ScopeError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return _serialize_order(order)
