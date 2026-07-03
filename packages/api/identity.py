"""
Retail Media Platform - Identity API Router.

Phase 3.0: Read-only endpoints for users, roles, permissions, audit events.
Phase 3.3: Endpoints now protected with JWT + permission checks.
Phase 3.5b: Advertiser organizations endpoint with RLS.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from packages.api.dependencies import (
    get_current_active_user,
    get_db,
    require_permission,
    set_rls_context,
)
from packages.domain import repository
from packages.domain.models import AdvertiserOrganization
from packages.domain.schemas import (
    MAX_LIMIT,
    DEFAULT_LIMIT,
    AdvertiserOrganizationOut,
    AuditEventOut,
    PaginatedAuditEvents,
    PaginatedUsers,
    PermissionOut,
    RoleOut,
    UserOut,
)

router = APIRouter(prefix="/api/v1/identity", tags=["identity"])


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@router.get("/users", response_model=PaginatedUsers)
async def list_users(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("users.read")),
):
    items, total = await repository.list_users(db, limit=limit, offset=offset)
    return PaginatedUsers(
        items=[UserOut.model_validate(u) for u in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("roles.read")),
):
    items = await repository.list_roles(db)
    return [RoleOut.model_validate(r) for r in items]


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------


@router.get("/permissions", response_model=list[PermissionOut])
async def list_permissions(
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("roles.read")),
):
    """List all permissions. Requires roles.read (least privilege —
    reading permissions is an admin/role-management concern, not a
    separate permission)."""
    items = await repository.list_permissions(db)
    return [PermissionOut.model_validate(p) for p in items]


# ---------------------------------------------------------------------------
# Audit Events
# ---------------------------------------------------------------------------


@router.get("/audit-events", response_model=PaginatedAuditEvents)
async def list_audit_events(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("audit.read")),
):
    items, total = await repository.list_audit_events(db, limit=limit, offset=offset)
    return PaginatedAuditEvents(
        items=[AuditEventOut.model_validate(e) for e in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Advertiser Organizations (Phase 3.5b — RLS pilot)
# ---------------------------------------------------------------------------


@router.get("/advertiser-organizations", response_model=list[AdvertiserOrganizationOut])
async def list_advertiser_organizations(
    db=Depends(get_db),
    _user: dict = Depends(get_current_active_user),
    _rls=Depends(set_rls_context),
):
    """List advertiser organizations visible through RLS.

    Protected by:
    - JWT + active user (get_current_active_user)
    - PostgreSQL RLS: rows filtered by app.rmp_scope_advertiser_ids

    NOTE: Phase 3.5b pilot uses RLS-only filtering.  Phase 3.5c will add
    require_scoped_permission for the app-layer defense.
    """
    result = await db.execute(select(AdvertiserOrganization))
    items = result.scalars().all()
    return [AdvertiserOrganizationOut.model_validate(o) for o in items]
