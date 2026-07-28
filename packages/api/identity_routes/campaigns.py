"""
Identity API — Campaigns: reads, mutations, approval, flights, placements, creatives.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from packages.api.dependencies import (
    get_current_active_user,
    get_db,
    require_permission,
    require_scoped_permission,
    set_rls_context,
    get_pagination_params,
    PaginationParams,
)
from packages.domain import repository
from packages.domain.schemas import (
    CampaignApprovalOut,
    CampaignApprovalQueueItem,
    CampaignApprovalResponse,
    CampaignArchiveResponse,
    CampaignCreateRequest,
    CampaignCreativeCreateRequest,
    CampaignCreativeAttachRequest,
    CampaignCreativeOut,
    CampaignFlightCreateRequest,
    CampaignFlightOut,
    CampaignFlightUpdateRequest,
    CampaignOut,
    CampaignPlacementCreateRequest,
    CampaignPlacementOut,
    CampaignPlacementUpdateRequest,
    CampaignRejectRequest,
    CampaignStatusHistoryOut,
    CampaignUpdateRequest,
    CampaignInventoryReservationOut,
    CampaignInventoryReservationsResponse,
    CreativeAssetOut,
    PaginatedResponse,
)
# Use repository.XXX() style so @patch("packages.api.identity.repository.XXX")
# targets work — see creatives.py for the established pattern.
from packages.domain import repository  # noqa: F401 — patched by tests
from packages.domain.exceptions import (
    CrossOrgReferenceError,
    ScopeError,
)

from .common import (
    _scope_ids,
    _serialize_campaign,
    _serialize_creative_asset,
    _require_draft_campaign,
    _validate_flight_dates,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Campaign Reads (Phase 4.1b — ADR-015)
# ---------------------------------------------------------------------------


@router.get("/campaigns", response_model=PaginatedResponse[CampaignOut])
async def list_campaigns(
    db=Depends(get_db),
    pagination: PaginationParams = Depends(get_pagination_params),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items, total = await repository.list_campaigns_paginated(
        db, limit=pagination.limit, offset=pagination.offset,
    )
    return PaginatedResponse(
        items=[_serialize_campaign(item) for item in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get("/campaign-flights", response_model=list[CampaignFlightOut])
async def list_campaign_flights(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_campaign_flights(db)
    return [CampaignFlightOut.model_validate(item) for item in items]


@router.get("/campaign-creatives", response_model=list[CampaignCreativeOut])
async def list_campaign_creatives(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_campaign_creatives(db)
    return [CampaignCreativeOut.model_validate(item) for item in items]


@router.get("/creative-assets", response_model=list[CreativeAssetOut])
async def list_creative_assets(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("creatives.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    from packages.domain.schemas import CreativeAssetOut as CAO
    items = await repository.list_creative_assets(db)
    return [_serialize_creative_asset(item) for item in items]


@router.get("/campaign-placements", response_model=list[CampaignPlacementOut])
async def list_campaign_placements(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_campaign_placements(db)
    return [CampaignPlacementOut.model_validate(item) for item in items]


@router.get("/campaign-approvals", response_model=list[CampaignApprovalOut])
async def list_campaign_approvals(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_campaign_approvals(db)
    return [CampaignApprovalOut.model_validate(item) for item in items]


@router.get("/campaign-status-history", response_model=list[CampaignStatusHistoryOut])
async def list_campaign_status_history(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_campaign_status_history(db)
    return [CampaignStatusHistoryOut.model_validate(item) for item in items]


# ---------------------------------------------------------------------------
# Campaign Mutations (Phase 4.1c — ADR-015)
# ---------------------------------------------------------------------------


@router.post("/campaigns", response_model=CampaignOut, status_code=201)
async def create_campaign_endpoint(
    body: CampaignCreateRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    user_id = claims["sub"]
    try:
        campaign_id = await repository.create_campaign(
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
            placement_basis=body.placement_basis,
            scope_advertiser_ids=_scope_ids(scope),
        )
    except CrossOrgReferenceError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ScopeError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await repository.enqueue_outbox_event(
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
    campaign = await repository.get_campaign(db, campaign_id)
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
    user_id = claims["sub"]
    try:
        status = await repository.update_campaign(
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
    await repository.enqueue_outbox_event(
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
    campaign = await repository.get_campaign(db, campaign_id)
    return _serialize_campaign(campaign)


@router.post("/campaigns/{campaign_id}/archive", response_model=CampaignArchiveResponse)
async def archive_campaign_endpoint(
    campaign_id: str,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    user_id = claims["sub"]
    try:
        old_status, new_status = await repository.archive_campaign(
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
    await repository.enqueue_outbox_event(
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


@router.post("/campaigns/{campaign_id}/request-approval",
             response_model=CampaignApprovalResponse)
async def request_approval_endpoint(
    campaign_id: str,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    user_id = claims["sub"]
    try:
        old_status, new_status = await repository.request_campaign_approval(
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
    await repository.enqueue_outbox_event(
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
    user_id = claims["sub"]
    try:
        old_status, new_status = await repository.approve_campaign(
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
    # Audit (S-052)
    from packages.domain.repository import create_audit_event
    await create_audit_event(
        db,
        actor_user_id=user_id,
        action="campaign.approved",
        target_type="campaign",
        target_id=campaign_id,
        details={
            "old_status": old_status,
            "new_status": new_status,
        },
    )
    await repository.enqueue_outbox_event(
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
    user_id = claims["sub"]
    try:
        old_status, new_status = await repository.reject_campaign(
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
    # Audit (S-052)
    from packages.domain.repository import create_audit_event
    await create_audit_event(
        db,
        actor_user_id=user_id,
        action="campaign.rejected",
        target_type="campaign",
        target_id=campaign_id,
        details={
            "old_status": old_status,
            "new_status": new_status,
            "rejection_reason": body.reason[:200],
        },
    )
    await repository.enqueue_outbox_event(
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
# Campaign Lifecycle — activate / pause (Wave 4)
# ---------------------------------------------------------------------------


@router.post("/campaigns/{campaign_id}/activate",
             response_model=CampaignApprovalResponse)
async def activate_endpoint(
    campaign_id: str,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    user_id = claims["sub"]
    try:
        old_status, new_status = await repository.activate_campaign(
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
            detail="Campaign not found or not in approved status",
        )
    from packages.domain.repository import create_audit_event
    await create_audit_event(
        db,
        actor_user_id=user_id,
        action="campaign.activated",
        target_type="campaign",
        target_id=campaign_id,
        details={
            "old_status": old_status,
            "new_status": new_status,
        },
    )
    await repository.enqueue_outbox_event(
        db,
        event_type="campaign.activated",
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
        message="Campaign activated",
        campaign_id=campaign_id,
        old_status=old_status,
        new_status=new_status,
    )


@router.post("/campaigns/{campaign_id}/pause",
             response_model=CampaignApprovalResponse)
async def pause_endpoint(
    campaign_id: str,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    user_id = claims["sub"]
    try:
        old_status, new_status = await repository.pause_campaign(
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
            detail="Campaign not found or not in active status",
        )
    from packages.domain.repository import create_audit_event
    await create_audit_event(
        db,
        actor_user_id=user_id,
        action="campaign.paused",
        target_type="campaign",
        target_id=campaign_id,
        details={
            "old_status": old_status,
            "new_status": new_status,
        },
    )
    await repository.enqueue_outbox_event(
        db,
        event_type="campaign.paused",
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
        message="Campaign paused",
        campaign_id=campaign_id,
        old_status=old_status,
        new_status=new_status,
    )


# ---------------------------------------------------------------------------
# S-038 — Campaign Approval Queue
# ---------------------------------------------------------------------------


@router.get("/campaigns/approval-queue",
            response_model=PaginatedResponse[CampaignApprovalQueueItem])
async def approval_queue_endpoint(
    status_filter: str = Query("pending_approval", alias="status"),
    db=Depends(get_db),
    pagination: PaginationParams = Depends(get_pagination_params),
    _claims: dict = Depends(require_permission("campaigns.approve")),
    _rls=Depends(set_rls_context),
):
    valid = {"pending_approval", "approved", "rejected", "all"}
    if status_filter not in valid:
        raise HTTPException(status_code=422, detail=f"Invalid status filter: {status_filter}")

    items, total = await repository.list_approval_queue_paginated(
        db,
        status_filter=status_filter,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return PaginatedResponse(
        items=[CampaignApprovalQueueItem(**item) for item in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


# ---------------------------------------------------------------------------
# Campaign Setup Mutations — Flights / Placements / Creatives (Pilot B1)
# ---------------------------------------------------------------------------


# ── Flights ──


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
    campaign = await _require_draft_campaign(db, campaign_id, scope)

    err = await _validate_flight_dates(db, campaign, body.start_at, body.end_at)
    if err is not None:
        raise HTTPException(status_code=422, detail=err)

    flight_id = await repository.create_campaign_flight(
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

    await repository.enqueue_outbox_event(
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
    campaign = await _require_draft_campaign(db, campaign_id, scope)

    current = await repository.get_campaign_flight(db, flight_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Flight not found")
    effective_start = body.start_at if body.start_at is not None else current.start_at
    effective_end = body.end_at if body.end_at is not None else current.end_at

    err = await _validate_flight_dates(db, campaign, effective_start, effective_end)
    if err is not None:
        raise HTTPException(status_code=422, detail=err)

    result_campaign_id = await repository.update_campaign_flight(
        db,
        flight_id,
        scope_advertiser_ids=_scope_ids(scope),
        **body.model_dump(exclude_unset=True),
    )
    if result_campaign_id is None:
        raise HTTPException(status_code=404, detail="Flight not found or campaign not in draft")

    if str(result_campaign_id) != str(campaign_id):
        raise HTTPException(status_code=404, detail="Flight does not belong to this campaign")

    await repository.enqueue_outbox_event(
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
    await _require_draft_campaign(db, campaign_id, scope)

    if not any([
        body.display_surface_id, body.store_id, body.cluster_id, body.branch_id,
    ]):
        raise HTTPException(status_code=422, detail="At least one target is required")

    placement_id = await repository.create_campaign_placement(
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

    await repository.enqueue_outbox_event(
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
    await _require_draft_campaign(db, campaign_id, scope)

    result_campaign_id = await repository.update_campaign_placement(
        db,
        placement_id,
        scope_advertiser_ids=_scope_ids(scope),
        **body.model_dump(exclude_unset=True),
    )
    if result_campaign_id is None:
        raise HTTPException(status_code=404, detail="Placement not found or campaign not in draft")

    if str(result_campaign_id) != str(campaign_id):
        raise HTTPException(status_code=404, detail="Placement does not belong to this campaign")

    await repository.enqueue_outbox_event(
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
    from packages.domain.schemas import CreativeAssetOut as CAO
    user_id = claims["sub"]
    campaign = await _require_draft_campaign(db, campaign_id, scope)

    try:
        result = await repository.create_campaign_creative(
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

    await repository.enqueue_outbox_event(
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
        raise HTTPException(status_code=404, detail={"code": "ASSET_NOT_FOUND",
                                                     "message": "Creative asset not found"})

    asset = await repository.get_creative_asset(db, body.creative_asset_id)
    await repository.enqueue_outbox_event(
        db,
        event_type="campaign.creative.changed",
        aggregate_type="campaign",
        aggregate_id=campaign_id,
        payload={"campaign_id": campaign_id, "creative_asset_id": body.creative_asset_id},
        headers={"source_service": "control-api"},
    )
    return _serialize_creative_asset(asset)


# ---------------------------------------------------------------------------
# S-079 — Campaign Inventory Reservations
# ---------------------------------------------------------------------------


@router.get("/campaigns/{campaign_id}/inventory-reservations",
            response_model=CampaignInventoryReservationsResponse)
async def list_campaign_inventory_reservations(
    campaign_id: str,
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("inventory.read")),
    _rls=Depends(set_rls_context),
):
    """List all inventory bookings for a campaign."""
    bookings = await repository.get_inventory_reservations_for_campaign(
        db, campaign_id,
    )
    return CampaignInventoryReservationsResponse(
        campaign_id=campaign_id,
        reservations=[
            CampaignInventoryReservationOut(**b) for b in bookings
        ],
        total=len(bookings),
    )
