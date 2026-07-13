"""
Identity API — Reference Data and Inventory (S-009h, S-037).
"""

from fastapi import APIRouter, Depends, HTTPException

from packages.api.dependencies import (
    get_db,
    require_permission,
    set_rls_context,
)
from packages.domain import repository
from packages.domain.schemas import (
    BranchOut,
    ClusterOut,
    DisplaySurfaceOut,
    InventoryStoreOut,
    InventorySurfaceOut,
    InventorySurfacePatchRequest,
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


@router.get("/inventory/stores", response_model=list[InventoryStoreOut])
async def list_inventory_stores(
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("inventory.read")),
):
    items = await repository.get_inventory_stores(db)
    return [InventoryStoreOut(**item) for item in items]


@router.get("/inventory/surfaces", response_model=list[InventorySurfaceOut])
async def list_inventory_surfaces(
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("inventory.read")),
):
    items = await repository.get_inventory_surfaces(db)
    return [InventorySurfaceOut(**item) for item in items]


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
