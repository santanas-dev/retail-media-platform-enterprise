"""
Retail Media Platform - Identity API Router.

Phase 3.0: Read-only endpoints for users, roles, permissions, audit events.
Phase 3.3: Endpoints now protected with JWT + permission checks.
Phase 3.5b: Advertiser organizations endpoint with RLS.
"""

from fastapi import APIRouter, Depends, Query

from packages.api.dependencies import (
    get_current_active_user,
    get_db,
    require_permission,
    require_scoped_permission,
    set_rls_context,
)
from packages.domain import repository
from packages.domain.schemas import (
    CampaignApprovalOut,
    CampaignCreativeOut,
    CampaignFlightOut,
    CampaignOut,
    CampaignPlacementOut,
    CampaignStatusHistoryOut,
    CreativeAssetOut,
    MAX_LIMIT,
    DEFAULT_LIMIT,
    AdvertiserBrandOut,
    AdvertiserContactOut,
    AdvertiserContractOut,
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
    _perm=Depends(require_scoped_permission("organization.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """List advertiser organizations — scoped + RLS protected.

    Two-layer defense:
    - App: require_scoped_permission("organization.read", "advertiser")
      → global permission OR advertiser scope
    - DB: PostgreSQL RLS filters rows by app.rmp_scope_advertiser_ids
    """
    items = await repository.list_advertiser_organizations(db)
    return [AdvertiserOrganizationOut.model_validate(o) for o in items]


# ---------------------------------------------------------------------------
# Advertiser Brands (Phase 4.0b)
# ---------------------------------------------------------------------------


@router.get("/advertiser-brands", response_model=list[AdvertiserBrandOut])
async def list_advertiser_brands(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """List advertiser brands — scoped + RLS protected."""
    items = await repository.list_advertiser_brands(db)
    return [AdvertiserBrandOut.model_validate(b) for b in items]


# ---------------------------------------------------------------------------
# Advertiser Contracts (Phase 4.0b)
# ---------------------------------------------------------------------------


@router.get("/advertiser-contracts", response_model=list[AdvertiserContractOut])
async def list_advertiser_contracts(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """List advertiser contracts — scoped + RLS protected."""
    items = await repository.list_advertiser_contracts(db)
    return [AdvertiserContractOut.model_validate(c) for c in items]


# ---------------------------------------------------------------------------
# Advertiser Contacts (Phase 4.0b)
# ---------------------------------------------------------------------------


@router.get("/advertiser-contacts", response_model=list[AdvertiserContactOut])
async def list_advertiser_contacts(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.contacts.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """List advertiser contacts — scoped + RLS protected. PII-gated."""
    items = await repository.list_advertiser_contacts(db)
    return [AdvertiserContactOut.model_validate(c) for c in items]


# ---------------------------------------------------------------------------

def _serialize_campaign(c):
    """Safe serialization — strip storage_pii fields if any."""
    return CampaignOut.model_validate(c)


def _serialize_creative_asset(c):
    """Safe serialization — never expose storage_bucket/storage_key."""
    return CreativeAssetOut.model_validate(c)


# Campaign Domain (Phase 4.1b — ADR-015)
# ---------------------------------------------------------------------------

@router.get("/campaigns", response_model=list[CampaignOut])
async def list_campaigns(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """List campaigns — scoped + RLS protected."""
    items = await repository.list_campaigns(db)
    return [_serialize_campaign(item) for item in items]


@router.get("/campaign-flights", response_model=list[CampaignFlightOut])
async def list_campaign_flights(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """List campaign flights — scoped + RLS protected."""
    items = await repository.list_campaign_flights(db)
    return [CampaignFlightOut.model_validate(item) for item in items]


@router.get("/campaign-creatives", response_model=list[CampaignCreativeOut])
async def list_campaign_creatives(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """List campaign-creative links — scoped + RLS protected."""
    items = await repository.list_campaign_creatives(db)
    return [CampaignCreativeOut.model_validate(item) for item in items]


@router.get("/creative-assets", response_model=list[CreativeAssetOut])
async def list_creative_assets(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("creatives.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """List creative assets (metadata only) — scoped + RLS protected.

    No presigned URLs or storage keys exposed.
    """
    items = await repository.list_creative_assets(db)
    return [_serialize_creative_asset(item) for item in items]


@router.get("/campaign-placements", response_model=list[CampaignPlacementOut])
async def list_campaign_placements(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """List campaign placements — scoped + RLS protected."""
    items = await repository.list_campaign_placements(db)
    return [CampaignPlacementOut.model_validate(item) for item in items]


@router.get("/campaign-approvals", response_model=list[CampaignApprovalOut])
async def list_campaign_approvals(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """List campaign approvals — scoped + RLS protected."""
    items = await repository.list_campaign_approvals(db)
    return [CampaignApprovalOut.model_validate(item) for item in items]


@router.get("/campaign-status-history", response_model=list[CampaignStatusHistoryOut])
async def list_campaign_status_history(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """List campaign status history — scoped + RLS protected."""
    items = await repository.list_campaign_status_history(db)
    return [CampaignStatusHistoryOut.model_validate(item) for item in items]
