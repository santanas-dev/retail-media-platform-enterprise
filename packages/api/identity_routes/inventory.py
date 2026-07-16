"""
Identity API — Reference Data and Inventory (S-009h, S-037).
"""

from fastapi import APIRouter, Depends, HTTPException

from packages.api.dependencies import (
    get_db,
    require_permission,
    set_rls_context,
    get_pagination_params,
    PaginationParams,
)
from packages.domain import repository
from packages.domain.schemas import (
    BranchOut,
    ClusterOut,
    DisplaySurfaceOut,
    InventoryAvailabilityRequest,
    InventoryAvailabilityResponse,
    InventorySlotAvailability,
    InventoryConflictCheckRequest,
    InventoryConflictCheckResponse,
    InventoryConflictItem,
    InventoryStoreOut,
    InventorySurfaceOut,
    InventorySurfacePatchRequest,
    PaginatedResponse,
    StoreOut,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Reference data (branches, clusters, stores, surfaces)
# ---------------------------------------------------------------------------


@router.get("/branches", response_model=list[BranchOut])
async def list_branches(
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("campaigns.read")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_branches(db)
    return [BranchOut.model_validate(b) for b in items]


@router.get("/clusters", response_model=list[ClusterOut])
async def list_clusters(
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("campaigns.read")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_clusters(db)
    return [ClusterOut.model_validate(c) for c in items]


@router.get("/stores", response_model=list[StoreOut])
async def list_stores(
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("campaigns.read")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_stores(db)
    return [StoreOut.model_validate(s) for s in items]


@router.get("/display-surfaces", response_model=list[DisplaySurfaceOut])
async def list_display_surfaces(
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("campaigns.read")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_display_surfaces(db)
    return [DisplaySurfaceOut.model_validate(ds) for ds in items]


# ---------------------------------------------------------------------------
# S-037 — Inventory Management
# ---------------------------------------------------------------------------


@router.get("/inventory/stores", response_model=PaginatedResponse[InventoryStoreOut])
async def list_inventory_stores(
    db=Depends(get_db),
    pagination: PaginationParams = Depends(get_pagination_params),
    _claims: dict = Depends(require_permission("inventory.read")),
):
    items, total = await repository.get_inventory_stores_paginated(
        db, limit=pagination.limit, offset=pagination.offset,
    )
    return PaginatedResponse(
        items=[InventoryStoreOut(**item) for item in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get("/inventory/surfaces", response_model=PaginatedResponse[InventorySurfaceOut])
async def list_inventory_surfaces(
    db=Depends(get_db),
    pagination: PaginationParams = Depends(get_pagination_params),
    _claims: dict = Depends(require_permission("inventory.read")),
):
    items, total = await repository.get_inventory_surfaces_paginated(
        db, limit=pagination.limit, offset=pagination.offset,
    )
    return PaginatedResponse(
        items=[InventorySurfaceOut(**item) for item in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.patch("/inventory/surfaces/{surface_id}",
              response_model=InventorySurfaceOut)
async def patch_inventory_surface(
    surface_id: str,
    body: InventorySurfacePatchRequest,
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("inventory.manage")),
):
    surface = await repository.get_display_surface(db, surface_id)
    if surface is None:
        raise HTTPException(status_code=404, detail="Surface not found")

    if body.is_active is not None:
        ok = await repository.toggle_surface_active(
            db, surface_id=surface_id, is_active=body.is_active,
        )
        if ok:
            surface.is_active = body.is_active

    return InventorySurfaceOut(
        id=surface.id,
        code=surface.code,
        store_id=surface.store_id,
        store_code=surface.store_code if hasattr(surface, "store_code") else None,
        store_name=surface.store_name if hasattr(surface, "store_name") else None,
        resolution_w=surface.resolution_w,
        resolution_h=surface.resolution_h,
        is_active=surface.is_active,
    )


# ---------------------------------------------------------------------------
# S-078 — Inventory Availability
# ---------------------------------------------------------------------------


@router.post(
    "/inventory/availability",
    response_model=InventoryAvailabilityResponse,
)
async def check_availability(
    body: InventoryAvailabilityRequest,
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("inventory.read")),
):
    """Check if a surface has enough inventory capacity over a time range.

    Expands the requested period into hourly slots, creates unconfigured
    slots with *INVENTORY_DEFAULT_SLOT_CAPACITY* (env, default 100), and
    checks each slot against booked + reserved capacity.
    """
    from packages.security.config import SecurityConfig

    config = SecurityConfig()
    result = await repository.compute_inventory_availability(
        db,
        display_surface_id=body.surface_id,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        requested_capacity_units=body.requested_capacity_units,
        requested_sov_percent=body.requested_sov_percent,
        default_total_capacity=config.inventory_default_slot_capacity,
    )
    return InventoryAvailabilityResponse(
        surface_id=result["display_surface_id"],
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        all_available=result["all_available"],
        total_requested=result["total_requested"],
        total_available=result["total_available"],
        slots=[InventorySlotAvailability(**s) for s in result["slots"]],
        conflicts=[InventorySlotAvailability(**c) for c in result["conflicts"]],
    )


# ---------------------------------------------------------------------------
# S-080 — Inventory Conflict Detection
# ---------------------------------------------------------------------------


@router.post("/inventory/conflicts/check",
             response_model=InventoryConflictCheckResponse)
async def check_inventory_conflicts(
    body: InventoryConflictCheckRequest,
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("inventory.read")),
    _rls=Depends(set_rls_context),
):
    """Check for inventory conflicts before reservation/approval.

    Detects: surface inactive, blackout rules, internal blocks,
    max SOV violations, capacity overbooking.
    """
    from packages.security.config import SecurityConfig

    config = SecurityConfig()
    result = await repository.detect_inventory_conflicts(
        db,
        display_surface_id=body.surface_id,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        requested_capacity_units=body.requested_capacity_units,
        requested_sov_percent=body.requested_sov_percent,
        campaign_id=body.campaign_id,
        default_total_capacity=config.inventory_default_slot_capacity,
    )
    return InventoryConflictCheckResponse(
        has_conflicts=result["has_conflicts"],
        blocking=[InventoryConflictItem(**b) for b in result["blocking"]],
        warnings=[InventoryConflictItem(**w) for w in result["warnings"]],
    )


@router.get("/campaigns/{campaign_id}/inventory-conflicts",
            response_model=InventoryConflictCheckResponse)
async def get_campaign_inventory_conflicts(
    campaign_id: str,
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("inventory.read")),
    _rls=Depends(set_rls_context),
):
    """Get inventory conflicts for all placements in a campaign."""
    from packages.security.config import SecurityConfig

    config = SecurityConfig()
    result = await repository.get_inventory_conflicts_for_campaign(
        db, campaign_id,
        default_total_capacity=config.inventory_default_slot_capacity,
    )
    return InventoryConflictCheckResponse(
        has_conflicts=result["has_conflicts"],
        blocking=[InventoryConflictItem(**b) for b in result["blocking"]],
        warnings=[InventoryConflictItem(**w) for w in result["warnings"]],
    )
