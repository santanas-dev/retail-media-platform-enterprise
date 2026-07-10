"""
Retail Media Platform - Identity API Router.

Phase 3.0: Read-only endpoints for users, roles, permissions, audit events.
Phase 3.3: Endpoints now protected with JWT + permission checks.
Phase 3.5b: Advertiser organizations endpoint with RLS.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from packages.api.dependencies import (
    get_current_active_user,
    get_db,
    get_scope_context,
    require_permission,
    require_scoped_permission,
    set_rls_context,
)
from packages.domain import repository
from packages.domain.scopes import ScopeContext
from packages.domain.schemas import (
    AdvertiserBrandOut,
    AdvertiserContactOut,
    AdvertiserContractOut,
    AdvertiserOrganizationOut,
    AuditEventOut,
    BranchOut,
    CampaignApprovalOut,
    CampaignCreativeOut,
    CampaignFlightOut,
    CampaignOut,
    CampaignPlacementOut,
    CampaignPopByDayOut,
    CampaignPopBySurfaceOut,
    CampaignPopSummaryOut,
    CampaignStatusHistoryOut,
    ClusterOut,
    CreativeAssetOut,
    DisplaySurfaceOut,
    MAX_LIMIT,
    DEFAULT_LIMIT,
    PaginatedAuditEvents,
    PaginatedUsers,
    PermissionOut,
    RoleOut,
    StoreOut,
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


# ---------------------------------------------------------------------------
# Campaign Mutations (Phase 4.1c — ADR-015)
# ---------------------------------------------------------------------------

from packages.domain.schemas import (
    CampaignArchiveResponse,
    CampaignCreateRequest,
    CampaignUpdateRequest,
)
from packages.domain.repository import (
    archive_campaign,
    create_campaign,
    enqueue_outbox_event,
    get_campaign,
    update_campaign,
)
from packages.domain.exceptions import (
    CrossOrgReferenceError,
    ScopeError,
)


def _scope_ids(scope) -> frozenset[str] | None:
    """Return advertiser scope IDs for scoped users, None for admins."""
    if scope.is_admin:
        return None  # admin — no scope restriction
    ids = scope.advertiser_scope_ids if scope else set()
    return frozenset(ids) if ids else frozenset()


@router.post("/campaigns", response_model=CampaignOut, status_code=201)
async def create_campaign_endpoint(
    body: CampaignCreateRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Create a draft campaign. Writes status history + outbox event."""
    user_id = claims["sub"]
    try:
        campaign_id = await create_campaign(
            db,
            advertiser_organization_id=body.advertiser_organization_id,
            advertiser_brand_id=body.advertiser_brand_id,
            advertiser_contract_id=body.advertiser_contract_id,
            code=body.code,
            name=body.name,
            description=body.description,
            created_by=user_id,
            start_at=body.start_at,
            end_at=body.end_at,
            timezone=body.timezone,
            budget_limit_amount=body.budget_limit_amount,
            budget_limit_currency=body.budget_limit_currency,
            priority=body.priority,
            scope_advertiser_ids=_scope_ids(scope),
        )
    except CrossOrgReferenceError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ScopeError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await enqueue_outbox_event(
        db,
        event_type="campaign.created",
        aggregate_type="campaign",
        aggregate_id=campaign_id,
        partition_key=body.advertiser_organization_id,
        payload={
            "campaign_id": campaign_id,
            "advertiser_organization_id": body.advertiser_organization_id,
            "code": body.code,
            "status": "draft",
        },
        headers={"source_service": "control-api"},
    )
    campaign = await get_campaign(db, campaign_id)
    return _serialize_campaign(campaign)


@router.patch("/campaigns/{campaign_id}", response_model=CampaignOut)
async def update_campaign_endpoint(
    campaign_id: str,
    body: CampaignUpdateRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Update a draft campaign. Only draft status allowed."""
    user_id = claims["sub"]
    try:
        status = await update_campaign(
            db,
            campaign_id,
            changed_by=user_id,
            scope_advertiser_ids=_scope_ids(scope),
            **body.model_dump(exclude_unset=True),
        )
    except ScopeError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if status is None:
        raise HTTPException(status_code=409, detail="Campaign not found or not in draft status")
    await enqueue_outbox_event(
        db,
        event_type="campaign.updated",
        aggregate_type="campaign",
        aggregate_id=campaign_id,
        payload={
            "campaign_id": campaign_id,
            "updated_fields": list(body.model_dump(exclude_unset=True).keys()),
        },
        headers={"source_service": "control-api"},
    )
    campaign = await get_campaign(db, campaign_id)
    return _serialize_campaign(campaign)


@router.post("/campaigns/{campaign_id}/archive", response_model=CampaignArchiveResponse)
async def archive_campaign_endpoint(
    campaign_id: str,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Archive a draft or rejected campaign. Writes status history + outbox event."""
    user_id = claims["sub"]
    try:
        old_status, new_status = await archive_campaign(
            db,
            campaign_id,
            changed_by=user_id,
            scope_advertiser_ids=_scope_ids(scope),
        )
    except ScopeError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if old_status is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if old_status == new_status:
        raise HTTPException(status_code=409, detail=f"Cannot archive campaign in status '{old_status}'")
    await enqueue_outbox_event(
        db,
        event_type="campaign.archived",
        aggregate_type="campaign",
        aggregate_id=campaign_id,
        payload={
            "campaign_id": campaign_id,
            "old_status": old_status,
            "new_status": "archived",
        },
        headers={"source_service": "control-api"},
    )
    return CampaignArchiveResponse(
        campaign_id=campaign_id,
        old_status=old_status,
        new_status="archived",
    )


# ---------------------------------------------------------------------------
# Campaign Approval Workflow (Phase 4.1d — ADR-015)
# ---------------------------------------------------------------------------

from packages.domain.schemas import (
    CampaignApprovalResponse,
    CampaignRejectRequest,
)
from packages.domain.repository import (
    approve_campaign,
    reject_campaign,
    request_campaign_approval,
)


@router.post("/campaigns/{campaign_id}/request-approval",
             response_model=CampaignApprovalResponse)
async def request_approval_endpoint(
    campaign_id: str,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Request approval for a draft campaign. Requires ≥1 flight + ≥1 placement + ≥1 creative."""
    user_id = claims["sub"]
    try:
        old_status, new_status = await request_campaign_approval(
            db,
            campaign_id,
            changed_by=user_id,
            scope_advertiser_ids=_scope_ids(scope),
        )
    except ScopeError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if old_status is None:
        raise HTTPException(
            status_code=409,
            detail="Campaign not found or not in draft status",
        )
    if old_status == new_status:
        raise HTTPException(
            status_code=422,
            detail="Campaign validation failed: ensure at least one flight, one placement, and one creative with uploaded files exist. Metadata-only creatives (no file uploaded) cannot be approved.",
        )
    await enqueue_outbox_event(
        db,
        event_type="campaign.approval_requested",
        aggregate_type="campaign",
        aggregate_id=campaign_id,
        payload={
            "campaign_id": campaign_id,
            "old_status": old_status,
            "new_status": new_status,
        },
        headers={"source_service": "control-api"},
    )
    return CampaignApprovalResponse(
        message="Approval requested",
        campaign_id=campaign_id,
        old_status=old_status,
        new_status=new_status,
    )


@router.post("/campaigns/{campaign_id}/approve",
             response_model=CampaignApprovalResponse)
async def approve_endpoint(
    campaign_id: str,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.approve", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Approve a pending_approval campaign. Requires campaigns.approve permission."""
    user_id = claims["sub"]
    try:
        old_status, new_status = await approve_campaign(
            db,
            campaign_id,
            reviewed_by=user_id,
            scope_advertiser_ids=_scope_ids(scope),
        )
    except ScopeError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if old_status is None:
        raise HTTPException(
            status_code=409,
            detail="Campaign not found or not in pending_approval status",
        )
    await enqueue_outbox_event(
        db,
        event_type="campaign.approved",
        aggregate_type="campaign",
        aggregate_id=campaign_id,
        payload={
            "campaign_id": campaign_id,
            "old_status": old_status,
            "new_status": new_status,
        },
        headers={"source_service": "control-api"},
    )
    return CampaignApprovalResponse(
        message="Campaign approved",
        campaign_id=campaign_id,
        old_status=old_status,
        new_status=new_status,
    )


@router.post("/campaigns/{campaign_id}/reject",
             response_model=CampaignApprovalResponse)
async def reject_endpoint(
    campaign_id: str,
    body: CampaignRejectRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.approve", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Reject a pending_approval campaign. Requires campaigns.approve + reason."""
    user_id = claims["sub"]
    try:
        old_status, new_status = await reject_campaign(
            db,
            campaign_id,
            reviewed_by=user_id,
            reason=body.reason,
            scope_advertiser_ids=_scope_ids(scope),
        )
    except ScopeError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if old_status is None:
        raise HTTPException(
            status_code=409,
            detail="Campaign not found or not in pending_approval status",
        )
    await enqueue_outbox_event(
        db,
        event_type="campaign.rejected",
        aggregate_type="campaign",
        aggregate_id=campaign_id,
        payload={
            "campaign_id": campaign_id,
            "old_status": old_status,
            "new_status": new_status,
            "rejection_reason": body.reason[:200],
        },
        headers={"source_service": "control-api"},
    )
    return CampaignApprovalResponse(
        message="Campaign rejected",
        campaign_id=campaign_id,
        old_status=old_status,
        new_status=new_status,
    )


# ---------------------------------------------------------------------------
# Campaign Setup Mutations — Flights / Placements / Creatives (Pilot B1)
# ---------------------------------------------------------------------------

from packages.domain.schemas import (
    CampaignFlightCreateRequest,
    CampaignFlightUpdateRequest,
    CampaignPlacementCreateRequest,
    CampaignPlacementUpdateRequest,
    CampaignCreativeCreateRequest,
    CampaignCreativeAttachRequest,
    CreativeAssetCreateRequest,
)
from packages.domain.repository import (
    create_campaign_flight,
    create_campaign_placement,
    create_campaign_creative,
    update_campaign_flight,
    update_campaign_placement,
)


async def _require_draft_campaign(db, campaign_id: str, scope):
    """Load campaign, raise 404/409 if not found or not in draft.

    Returns the Campaign object so callers that need advertiser_organization_id
    can avoid a second lookup.
    """
    campaign = await repository.get_campaign(db, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail={"code": "CAMPAIGN_NOT_FOUND"})
    if campaign.status != "draft":
        raise HTTPException(status_code=409, detail="Campaign is not in draft status")
    if not scope.is_admin:
        org_str = str(campaign.advertiser_organization_id)
        if org_str not in (scope.advertiser_scope_ids or frozenset()):
            raise HTTPException(status_code=404, detail={"code": "CAMPAIGN_NOT_FOUND"})
    return campaign


# ── Flights ──


async def _validate_flight_dates(
    db, campaign, start_at, end_at,
) -> str | None:
    """Validate flight start/end against contract window. Returns error string or None.

    Checks:
    - start_at < end_at
    - start_at >= contract.valid_from
    - end_at <= contract.valid_until (if not NULL)
    """
    if start_at >= end_at:
        return "Flight start_at must be before end_at"

    contract = await repository.get_advertiser_contract(
        db, str(campaign.advertiser_contract_id),
    )
    if contract is None:
        return "Campaign contract not found"

    if contract.valid_from and start_at < contract.valid_from:
        return "Flight start_at is before contract valid_from"

    if contract.valid_until is not None and end_at > contract.valid_until:
        return "Flight end_at is after contract valid_until"

    return None


@router.post("/campaigns/{campaign_id}/flights",
             response_model=CampaignFlightOut, status_code=201)
async def create_flight_endpoint(
    campaign_id: str,
    body: CampaignFlightCreateRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Create a flight for a draft campaign."""
    campaign = await _require_draft_campaign(db, campaign_id, scope)

    err = await _validate_flight_dates(db, campaign, body.start_at, body.end_at)
    if err is not None:
        raise HTTPException(status_code=422, detail=err)

    flight_id = await create_campaign_flight(
        db,
        campaign_id=campaign_id,
        name=body.name,
        start_at=body.start_at,
        end_at=body.end_at,
        dayparting_json=body.dayparting_json,
        days_of_week=body.days_of_week,
        priority=body.priority,
        scope_advertiser_ids=_scope_ids(scope),
    )
    if flight_id is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    await enqueue_outbox_event(
        db,
        event_type="campaign.flight.changed",
        aggregate_type="campaign",
        aggregate_id=campaign_id,
        payload={"campaign_id": campaign_id, "flight_id": flight_id},
        headers={"source_service": "control-api"},
    )
    flight = await repository.get_campaign_flight(db, flight_id)
    return CampaignFlightOut.model_validate(flight)


@router.patch("/campaigns/{campaign_id}/flights/{flight_id}",
              response_model=CampaignFlightOut)
async def update_flight_endpoint(
    campaign_id: str,
    flight_id: str,
    body: CampaignFlightUpdateRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Partial update of a flight."""
    campaign = await _require_draft_campaign(db, campaign_id, scope)

    # Resolve effective dates: new values from body, fall back to current flight
    current = await repository.get_campaign_flight(db, flight_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Flight not found")
    effective_start = body.start_at if body.start_at is not None else current.start_at
    effective_end = body.end_at if body.end_at is not None else current.end_at

    err = await _validate_flight_dates(db, campaign, effective_start, effective_end)
    if err is not None:
        raise HTTPException(status_code=422, detail=err)

    result_campaign_id = await update_campaign_flight(
        db,
        flight_id,
        scope_advertiser_ids=_scope_ids(scope),
        **body.model_dump(exclude_unset=True),
    )
    if result_campaign_id is None:
        raise HTTPException(status_code=404, detail="Flight not found or campaign not in draft")

    if str(result_campaign_id) != str(campaign_id):
        raise HTTPException(status_code=404, detail="Flight does not belong to this campaign")

    await enqueue_outbox_event(
        db,
        event_type="campaign.flight.changed",
        aggregate_type="campaign",
        aggregate_id=campaign_id,
        payload={"campaign_id": campaign_id, "flight_id": flight_id},
        headers={"source_service": "control-api"},
    )
    flight = await repository.get_campaign_flight(db, flight_id)
    return CampaignFlightOut.model_validate(flight)


# ── Placements ──


@router.post("/campaigns/{campaign_id}/placements",
             response_model=CampaignPlacementOut, status_code=201)
async def create_placement_endpoint(
    campaign_id: str,
    body: CampaignPlacementCreateRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Create a placement for a draft campaign. At least one target required."""
    await _require_draft_campaign(db, campaign_id, scope)

    if not any([
        body.display_surface_id, body.store_id, body.cluster_id, body.branch_id,
    ]):
        raise HTTPException(status_code=422, detail="At least one target is required")

    placement_id = await create_campaign_placement(
        db,
        campaign_id=campaign_id,
        display_surface_id=body.display_surface_id,
        store_id=body.store_id,
        cluster_id=body.cluster_id,
        branch_id=body.branch_id,
        share_of_voice_pct=body.share_of_voice_pct,
        max_impressions=body.max_impressions,
        scope_advertiser_ids=_scope_ids(scope),
    )
    if placement_id is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    await enqueue_outbox_event(
        db,
        event_type="campaign.placement.changed",
        aggregate_type="campaign",
        aggregate_id=campaign_id,
        payload={"campaign_id": campaign_id, "placement_id": placement_id},
        headers={"source_service": "control-api"},
    )
    placement = await repository.get_campaign_placement(db, placement_id)
    return CampaignPlacementOut.model_validate(placement)


@router.patch("/campaigns/{campaign_id}/placements/{placement_id}",
              response_model=CampaignPlacementOut)
async def update_placement_endpoint(
    campaign_id: str,
    placement_id: str,
    body: CampaignPlacementUpdateRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Partial update of a placement."""
    await _require_draft_campaign(db, campaign_id, scope)

    result_campaign_id = await update_campaign_placement(
        db,
        placement_id,
        scope_advertiser_ids=_scope_ids(scope),
        **body.model_dump(exclude_unset=True),
    )
    if result_campaign_id is None:
        raise HTTPException(status_code=404, detail="Placement not found or campaign not in draft")

    if str(result_campaign_id) != str(campaign_id):
        raise HTTPException(status_code=404, detail="Placement does not belong to this campaign")

    await enqueue_outbox_event(
        db,
        event_type="campaign.placement.changed",
        aggregate_type="campaign",
        aggregate_id=campaign_id,
        payload={"campaign_id": campaign_id, "placement_id": placement_id},
        headers={"source_service": "control-api"},
    )
    placement = await repository.get_campaign_placement(db, placement_id)
    return CampaignPlacementOut.model_validate(placement)


# ── Creatives ──


@router.post("/campaigns/{campaign_id}/creatives",
             response_model=CreativeAssetOut, status_code=201)
async def create_creative_endpoint(
    campaign_id: str,
    body: CampaignCreativeCreateRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Create a creative asset and attach it to a draft campaign.

    Storage bucket/key are pilot-safe auto-filled values — never returned
    in the response.
    """
    user_id = claims["sub"]
    campaign = await _require_draft_campaign(db, campaign_id, scope)

    try:
        result = await create_campaign_creative(
            db,
            campaign_id=campaign_id,
            advertiser_organization_id=str(campaign.advertiser_organization_id),
            code=body.code,
            name=body.name,
            media_type=body.media_type,
            sha256_checksum=body.sha256_checksum,
            file_size_bytes=body.file_size_bytes,
            duration_ms=body.duration_ms,
            resolution_w=body.resolution_w,
            resolution_h=body.resolution_h,
            sort_order=body.sort_order,
            duration_override_ms=body.duration_override_ms,
            scope_advertiser_ids=_scope_ids(scope),
            created_by=user_id,
        )
    except CrossOrgReferenceError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if result is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    asset_id, _link_id = result

    await enqueue_outbox_event(
        db,
        event_type="campaign.creative.changed",
        aggregate_type="campaign",
        aggregate_id=campaign_id,
        payload={"campaign_id": campaign_id, "creative_asset_id": asset_id},
        headers={"source_service": "control-api"},
    )
    asset = await repository.get_creative_asset(db, asset_id)
    return _serialize_creative_asset(asset)


@router.post("/campaigns/{campaign_id}/creatives/attach",
             response_model=CreativeAssetOut, status_code=201)
async def attach_creative_endpoint(
    campaign_id: str,
    body: CampaignCreativeAttachRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Attach an existing creative asset to a draft campaign.

    Same-org only. Cross-org → 422. Non-draft → 409.
    Duplicate attach → 200 with existing result (idempotent).
    """
    campaign = await _require_draft_campaign(db, campaign_id, scope)

    try:
        link = await repository.attach_creative_to_campaign(
            db,
            campaign_id=campaign_id,
            creative_asset_id=body.creative_asset_id,
            sort_order=body.sort_order,
            scope_advertiser_ids=_scope_ids(scope),
        )
    except CrossOrgReferenceError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if link is None:
        # Campaign check passed but asset not found
        raise HTTPException(status_code=404, detail={"code": "ASSET_NOT_FOUND",
                                                     "message": "Creative asset not found"})

    # Outbox on new attachment only (not on duplicate)
    asset = await repository.get_creative_asset(db, body.creative_asset_id)
    await enqueue_outbox_event(
        db,
        event_type="campaign.creative.changed",
        aggregate_type="campaign",
        aggregate_id=campaign_id,
        payload={"campaign_id": campaign_id, "creative_asset_id": body.creative_asset_id},
        headers={"source_service": "control-api"},
    )
    return _serialize_creative_asset(asset)


@router.post("/creative-assets",
             response_model=CreativeAssetOut, status_code=201)
async def create_creative_asset_endpoint(
    body: CreativeAssetCreateRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Create a creative asset in the library (metadata only, no file upload).

    Standalone asset intake — does NOT attach to a campaign.
    The asset appears in the creative library picker and can be attached
    to any draft campaign later via POST .../creatives/attach.

    advertiser_organization_id is derived from JWT scope for scoped users.
    Admins must provide it explicitly.
    """
    scope_ids = _scope_ids(scope)
    org_id = body.advertiser_organization_id

    if org_id:
        # Explicit org — validate against scope if scoped
        if scope_ids is not None and org_id not in scope_ids:
            raise HTTPException(status_code=422, detail="Advertiser organization not in scope")
    elif scope_ids is not None:
        # Scoped user — derive from token
        if not scope_ids:
            raise HTTPException(status_code=403, detail="No advertiser scope")
        org_id = next(iter(scope_ids))
    else:
        # Admin without explicit org
        raise HTTPException(status_code=422, detail="Advertiser organization required for admin users")

    try:
        asset_id = await repository.create_creative_asset_metadata(
            db,
            advertiser_organization_id=org_id,
            code=body.code,
            name=body.name,
            media_type=body.media_type,
            sha256_checksum=body.sha256_checksum,
            file_size_bytes=body.file_size_bytes,
            resolution_w=body.resolution_w,
            resolution_h=body.resolution_h,
            duration_ms=body.duration_ms,
            scope_advertiser_ids=scope_ids,
            created_by=claims["sub"],
        )
    except CrossOrgReferenceError as e:
        raise HTTPException(status_code=422, detail=str(e))

    await enqueue_outbox_event(
        db,
        event_type="creative_asset.created",
        aggregate_type="creative_asset",
        aggregate_id=asset_id,
        payload={"creative_asset_id": asset_id},
        headers={"source_service": "control-api"},
    )
    asset = await repository.get_creative_asset(db, asset_id)
    return _serialize_creative_asset(asset)


# ---------------------------------------------------------------------------
# PoP Reporting Endpoints (Phase 4.3d — ADR-017 §6)
# ---------------------------------------------------------------------------


async def _require_campaign_visible(
    db, campaign_id: str, scope: ScopeContext,
):
    """Return campaign if visible to caller, else raise 404.

    Checks both RLS (via get_campaign) and explicit org scope for defense-in-depth.
    Admin users bypass the org-id check.
    """
    campaign = await repository.get_campaign(db, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail={"code": "CAMPAIGN_NOT_FOUND", "message": "Campaign not found"})
    if not scope.is_admin:
        if str(campaign.advertiser_organization_id) not in scope.advertiser_scope_ids:
            raise HTTPException(status_code=404, detail={"code": "CAMPAIGN_NOT_FOUND", "message": "Campaign not found"})
    return campaign


@router.get("/campaigns/{campaign_id}/pop/summary", response_model=CampaignPopSummaryOut)
async def get_campaign_pop_summary(
    campaign_id: str,
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Billing-grade PoP summary for a campaign.

    Only accepted, campaign_verified, playback_result=success events count.
    Quarantined, rejected, duplicate, fallback events are excluded.
    """
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
    """Daily PoP breakdown for a campaign. Ordered by date ascending."""
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
    """Per-surface PoP breakdown for a campaign. Ordered by impressions descending."""
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
# S-009h — Reference data (branches, clusters, stores, surfaces)
# ---------------------------------------------------------------------------


@router.get("/branches", response_model=list[BranchOut])
async def list_branches(
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("campaigns.read")),
    _rls=Depends(set_rls_context),
):
    """List branches — read-only, JWT + perm + RLS."""
    items = await repository.list_branches(db)
    return [BranchOut.model_validate(b) for b in items]


@router.get("/clusters", response_model=list[ClusterOut])
async def list_clusters(
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("campaigns.read")),
    _rls=Depends(set_rls_context),
):
    """List clusters — read-only, JWT + perm + RLS."""
    items = await repository.list_clusters(db)
    return [ClusterOut.model_validate(c) for c in items]


@router.get("/stores", response_model=list[StoreOut])
async def list_stores(
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("campaigns.read")),
    _rls=Depends(set_rls_context),
):
    """List stores — read-only, JWT + perm + RLS."""
    items = await repository.list_stores(db)
    return [StoreOut.model_validate(s) for s in items]


@router.get("/display-surfaces", response_model=list[DisplaySurfaceOut])
async def list_display_surfaces(
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("campaigns.read")),
    _rls=Depends(set_rls_context),
):
    """List display surfaces — read-only, JWT + perm + RLS."""
    items = await repository.list_display_surfaces(db)
    return [DisplaySurfaceOut.model_validate(ds) for ds in items]
