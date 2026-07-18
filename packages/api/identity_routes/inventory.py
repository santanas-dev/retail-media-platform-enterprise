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
    InventoryAlternative,
    InventoryAlternativesRequest,
    InventoryAlternativesResponse,
    InventoryRuleOut,
    InventoryRuleCreate,
    InventoryRuleUpdate,
    InventoryAvailabilityRequest,
    InventoryAvailabilityResponse,
    InventorySlotAvailability,
    InventoryConflictCheckRequest,
    InventoryConflictCheckResponse,
    InventoryConflictItem,
    InventoryStoreOut,
    InventorySurfaceOut,
    InventorySurfacePatchRequest,
    InventorySimulationRequest,
    InventorySimulationResponse,
    InventorySimulationPlacementResult,
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


# ---------------------------------------------------------------------------
# S-087 — Inventory Alternatives
# ---------------------------------------------------------------------------


@router.post(
    "/inventory/alternatives",
    response_model=InventoryAlternativesResponse,
)
async def suggest_alternatives(
    body: InventoryAlternativesRequest,
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("inventory.read")),
):
    """Suggest alternative surfaces/slots when a placement is unavailable.

    Prioritises: same store different surface → nearby time → lower SOV
    → later date.  Returns up to max_results alternatives sorted by score.
    """
    from packages.security.config import SecurityConfig

    config = SecurityConfig()
    alternatives = await repository.suggest_inventory_alternatives(
        db,
        display_surface_id=body.surface_id,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        requested_capacity_units=body.requested_capacity_units,
        requested_sov_percent=body.requested_sov_percent,
        max_results=body.max_results,
        default_total_capacity=config.inventory_default_slot_capacity,
    )
    return InventoryAlternativesResponse(
        surface_id=body.surface_id,
        alternatives=[InventoryAlternative(**a) for a in alternatives],
        total_found=len(alternatives),
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


# ---------------------------------------------------------------------------
# S-088 — Inventory Rules Management
# ---------------------------------------------------------------------------

_RULE_TYPES = frozenset(["blackout", "internal_block", "max_sov"])
_SCOPE_TYPES = frozenset(["global", "branch", "cluster", "store", "surface"])


def _validate_rule(body) -> None:
    """Validate rule payload — raises HTTPException on failure."""
    rt = body.rule_type
    if rt is not None and rt not in _RULE_TYPES:
        raise HTTPException(422, f"Unsupported rule_type: '{rt}'. Must be one of: {', '.join(sorted(_RULE_TYPES))}")

    st = body.scope_type
    if st is not None and st not in _SCOPE_TYPES:
        raise HTTPException(422, f"Unsupported scope_type: '{st}'. Must be one of: {', '.join(sorted(_SCOPE_TYPES))}")

    if st is not None and st != "global" and body.scope_id is None:
        raise HTTPException(422, f"scope_id is required for scope_type '{st}'")

    if body.starts_at is not None and body.ends_at is not None and body.starts_at >= body.ends_at:
        raise HTTPException(422, "starts_at must be before ends_at")

    vj = body.value_json
    if vj is not None:
        _validate_value_json(rt or "", vj)


def _validate_value_json(rule_type: str, value: dict) -> None:
    """Validate value_json per rule_type."""
    if rule_type == "internal_block":
        cap = value.get("capacity_units")
        if cap is None or not isinstance(cap, int) or cap <= 0:
            raise HTTPException(422, "internal_block requires capacity_units > 0")
    elif rule_type == "max_sov":
        pct = value.get("max_sov_percent")
        if pct is None or not isinstance(pct, int) or not (0 < pct <= 100):
            raise HTTPException(422, "max_sov requires max_sov_percent in (0, 100]")
    elif rule_type == "blackout":
        pass


@router.get("/inventory/rules", response_model=list[InventoryRuleOut])
async def list_rules(
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("inventory.read")),
):
    """List all inventory rules, ordered by priority desc."""
    items = await repository.list_inventory_rules(db)
    return [InventoryRuleOut.model_validate(r) for r in items]


@router.post("/inventory/rules", response_model=InventoryRuleOut, status_code=201)
async def create_rule(
    body: InventoryRuleCreate,
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("inventory.manage")),
):
    """Create a new inventory rule."""
    _validate_rule(body)
    rule = await repository.create_inventory_rule(
        db,
        scope_type=body.scope_type,
        scope_id=body.scope_id,
        rule_type=body.rule_type,
        priority=body.priority,
        value_json=body.value_json,
        is_active=body.is_active,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
    )
    await db.flush()
    return InventoryRuleOut.model_validate(rule)


@router.patch("/inventory/rules/{rule_id}", response_model=InventoryRuleOut)
async def update_rule(
    rule_id: str,
    body: InventoryRuleUpdate,
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("inventory.manage")),
):
    """Partial update of an inventory rule."""
    _validate_rule(body)
    rule = await repository.update_inventory_rule(
        db,
        rule_id=rule_id,
        scope_type=body.scope_type,
        scope_id=body.scope_id,
        rule_type=body.rule_type,
        priority=body.priority,
        value_json=body.value_json,
        is_active=body.is_active,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
    )
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.flush()
    return InventoryRuleOut.model_validate(rule)


@router.post("/inventory/rules/{rule_id}/activate", response_model=InventoryRuleOut)
async def activate_rule(
    rule_id: str,
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("inventory.manage")),
):
    """Activate an inventory rule."""
    rule = await repository.set_inventory_rule_active(db, rule_id=rule_id, is_active=True)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.flush()
    return InventoryRuleOut.model_validate(rule)


@router.post("/inventory/rules/{rule_id}/deactivate", response_model=InventoryRuleOut)
async def deactivate_rule(
    rule_id: str,
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("inventory.manage")),
):
    """Deactivate an inventory rule."""
    rule = await repository.set_inventory_rule_active(db, rule_id=rule_id, is_active=False)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.flush()
    return InventoryRuleOut.model_validate(rule)


# ---------------------------------------------------------------------------
# S-089 — Inventory Simulation
# ---------------------------------------------------------------------------


@router.post(
    "/inventory/simulate",
    response_model=InventorySimulationResponse,
)
async def simulate_inventory(
    body: InventorySimulationRequest,
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("inventory.read")),
    _rls=Depends(set_rls_context),
):
    """Run pre-approval inventory simulation for a campaign."""
    from packages.security.config import SecurityConfig

    config = SecurityConfig()
    result = await repository.simulate_campaign_inventory(
        db,
        campaign_id=body.campaign_id,
        default_total_capacity=config.inventory_default_slot_capacity,
    )
    return InventorySimulationResponse(
        campaign_id=result["campaign_id"],
        overall_fit=result["overall_fit"],
        placements=[
            InventorySimulationPlacementResult(**p)
            for p in result["placements"]
        ],
        blocking_count=result["blocking_count"],
        warning_count=result["warning_count"],
    )
