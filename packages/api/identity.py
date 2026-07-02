"""
Retail Media Platform — Identity API Router.

Phase 3.0: Read-only endpoints for users, roles, permissions, audit events.

TODO(auth): All endpoints are unprotected. Add JWT/SSO auth dependency
and permission checks (users.read, roles.read, audit.read) in Phase 3.1.
"""

from fastapi import APIRouter, Depends, Query

from packages.api.dependencies import get_db
from packages.domain import repository
from packages.domain.schemas import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
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
async def list_roles(db=Depends(get_db)):
    items = await repository.list_roles(db)
    return [RoleOut.model_validate(r) for r in items]


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------


@router.get("/permissions", response_model=list[PermissionOut])
async def list_permissions(db=Depends(get_db)):
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
):
    items, total = await repository.list_audit_events(db, limit=limit, offset=offset)
    return PaginatedAuditEvents(
        items=[AuditEventOut.model_validate(e) for e in items],
        total=total,
        limit=limit,
        offset=offset,
    )
