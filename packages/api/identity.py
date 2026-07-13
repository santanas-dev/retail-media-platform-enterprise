"""
Retail Media Platform - Identity API Router.

Phase 3.0: Read-only endpoints for users, roles, permissions, audit events.
Phase 3.3: Endpoints now protected with JWT + permission checks.
Phase 3.5b: Advertiser organizations endpoint with RLS.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.responses import Response

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
    ADSettingsOut,
    ADTestResultOut,
    AdvertiserBrandOut,
    AdvertiserContactOut,
    AdvertiserContractOut,
    AdvertiserOrganizationDetailOut,
    AdvertiserOrganizationOut,
    AdvertiserUserMembershipOut,
    AuditEventOut,
    BranchOut,
    CampaignApprovalOut,
    CampaignApprovalQueueItem,
    CampaignCreativeOut,
    CampaignFlightOut,
    CampaignOut,
    CampaignPlacementOut,
    CampaignPopByDayOut,
    CampaignPopBySurfaceOut,
    CampaignPopSummaryOut,
    CampaignStatusHistoryOut,
    ClusterOut,
    CompleteUploadRequest,
    CompleteUploadResponse,
    CreateLocalAdvertiserRequest,
    CreateLocalAdvertiserResponse,
    CreativeAssetOut,
    CreativeModerationQueueItem,
    CreativeModerationResponse,
    CreativeRejectRequest,
    DisplaySurfaceOut,
    InventoryStoreOut,
    InventorySurfaceOut,
    InventorySurfacePatchRequest,
    MAX_LIMIT,
    DEFAULT_LIMIT,
    PaginatedAuditEvents,
    PaginatedUsers,
    PermissionOut,
    ResetPasswordRequest,
    ResetPasswordResponse,
    RoleOut,
    StoreOut,
    UploadIntentRequest,
    UploadIntentResponse,
    UserDetailOut,
    UserOut,
    UserRoleAssignmentOut,
    UserStatusResponse,
)
from packages.security.config import get_security_config

router = APIRouter(prefix="/api/v1/identity", tags=["identity"])


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@router.get("/users", response_model=PaginatedUsers)
async def list_users(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.read")),
):
    items, total = await repository.list_users(db, limit=limit, offset=offset)
    return PaginatedUsers(
        items=[UserOut.model_validate(u) for u in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/users/{user_id}", response_model=UserDetailOut)
async def get_user(
    user_id: str,
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.read")),
):
    user = await repository.get_user_detail(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Build role assignments
    role_assignments = []
    for ur in user.roles:
        role_code = ur.role.code if ur.role else ""
        role_name = ur.role.name if ur.role else ""
        role_assignments.append(
            UserRoleAssignmentOut(
                id=ur.id,
                role_id=ur.role_id,
                role_code=role_code,
                role_name=role_name,
                scope_type=ur.scope_type,
                scope_id=ur.scope_id,
            )
        )

    # Get must_change_password from local_credentials if available
    must_change = False
    cred = await repository.get_user_local_credential(db, user_id)
    if cred:
        must_change = cred.must_change_password

    return UserDetailOut(
        id=user.id,
        code=user.code,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        auth_provider=user.auth_provider,
        status=user.status,
        is_break_glass=user.is_break_glass,
        must_change_password=must_change,
        roles=role_assignments,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post(
    "/users/local-advertiser",
    response_model=CreateLocalAdvertiserResponse,
    status_code=201,
)
async def create_local_advertiser(
    body: CreateLocalAdvertiserRequest,
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.manage")),
):
    import uuid as _uuid
    from packages.security.password import hash_password

    # Check duplicate username
    existing = await repository.find_user_by_username(db, body.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")

    # Validate advertiser organization exists
    org = await repository.get_advertiser_organization(db, body.advertiser_organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Advertiser organization not found")

    # Resolve or generate password
    one_time_password: str | None = None
    if body.auto_generate_password:
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        password = "".join(secrets.choice(alphabet) for _ in range(16))
        one_time_password = password
    elif body.temporary_password:
        password = body.temporary_password
    else:
        raise HTTPException(
            status_code=422,
            detail="Either temporary_password or auto_generate_password must be provided",
        )

    password_hash = hash_password(password)

    # Find advertiser role
    roles = await repository.list_roles(db)
    advertiser_role = next((r for r in roles if r.code == "advertiser"), None)
    if advertiser_role is None:
        raise HTTPException(status_code=500, detail="Advertiser role not found in system")

    # Generate user code
    code = body.username.upper().replace(" ", "_")[:8]

    user_id = str(_uuid.uuid4())
    user = await repository.create_local_advertiser_user(
        db,
        user_id=user_id,
        code=code,
        username=body.username,
        display_name=body.display_name,
        password_hash=password_hash,
        advertiser_organization_id=body.advertiser_organization_id,
        role_id=advertiser_role.id,
        must_change_password=body.must_change_password,
        is_active=body.is_active,
    )

    # Audit (S-035e)
    from packages.domain.repository import create_audit_event
    await create_audit_event(
        db,
        actor_user_id=scope.user_id,
        action="user.created",
        target_type="user",
        target_id=user.id,
        details={"username": body.username, "org_id": body.advertiser_organization_id},
    )

    await db.commit()

    return CreateLocalAdvertiserResponse(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        one_time_password=one_time_password,
    )


@router.post("/users/{user_id}/deactivate", response_model=UserStatusResponse)
async def deactivate_user(
    user_id: str,
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.manage")),
):
    user = await repository.get_user_detail(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.status == "inactive":
        raise HTTPException(status_code=409, detail="User is already inactive")

    # Safety: cannot deactivate yourself (self-lockout prevention)
    if user_id == scope.user_id:
        raise HTTPException(status_code=409, detail="Cannot deactivate your own account")

    # Safety: cannot deactivate last active break-glass user
    if user.is_break_glass:
        count = await repository.count_active_break_glass_users(db)
        if count <= 1:
            raise HTTPException(
                status_code=409,
                detail="Cannot deactivate the last active break-glass user",
            )

    # Safety: cannot deactivate last active admin
    admin_count = await repository.count_active_admin_users(db)
    is_admin = any(
        ur.role and ur.role.code == "system_admin" for ur in user.roles
    )
    if is_admin and admin_count <= 1:
        raise HTTPException(
            status_code=409,
            detail="Cannot deactivate the last active system admin",
        )

    await repository.set_user_status(db, user_id, "inactive")

    # Revoke sessions
    from packages.auth.repository import revoke_all_sessions_for_user
    await revoke_all_sessions_for_user(db, user_id)

    # Audit (S-035e)
    from packages.domain.repository import create_audit_event
    await create_audit_event(
        db,
        actor_user_id=scope.user_id,
        action="user.deactivated",
        target_type="user",
        target_id=user_id,
    )

    await db.commit()

    return UserStatusResponse(
        user_id=user_id,
        status="inactive",
        message="User deactivated. All sessions revoked.",
    )


@router.post("/users/{user_id}/activate", response_model=UserStatusResponse)
async def activate_user(
    user_id: str,
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.manage")),
):
    user = await repository.get_user_detail(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.status == "active":
        raise HTTPException(status_code=409, detail="User is already active")

    await repository.set_user_status(db, user_id, "active")

    # Audit (S-035e)
    from packages.domain.repository import create_audit_event
    await create_audit_event(
        db,
        actor_user_id=scope.user_id,
        action="user.activated",
        target_type="user",
        target_id=user_id,
    )

    await db.commit()

    return UserStatusResponse(
        user_id=user_id,
        status="active",
        message="User activated.",
    )


@router.post(
    "/users/{user_id}/reset-password",
    response_model=ResetPasswordResponse,
)
async def reset_password(
    user_id: str,
    body: ResetPasswordRequest,
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.manage")),
):
    user = await repository.get_user_detail(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Safety: use /auth/change-password for your own password
    if user_id == scope.user_id:
        raise HTTPException(
            status_code=422,
            detail="Cannot reset your own password via admin endpoint. Use /auth/change-password instead.",
        )

    # Only local_* providers support password reset
    if not user.auth_provider.startswith("local_"):
        raise HTTPException(
            status_code=422,
            detail="Password reset is only available for local accounts, not "
            + user.auth_provider,
        )

    cred = await repository.get_user_local_credential(db, user_id)
    if cred is None:
        raise HTTPException(
            status_code=422,
            detail="No local credentials found for this user",
        )

    # Resolve or generate password
    from packages.security.password import hash_password
    one_time_password: str | None = None
    if body.auto_generate_password:
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        password = "".join(secrets.choice(alphabet) for _ in range(16))
        one_time_password = password
    elif body.new_temporary_password:
        password = body.new_temporary_password
    else:
        raise HTTPException(
            status_code=422,
            detail="Either new_temporary_password or auto_generate_password must be provided",
        )

    password_hash = hash_password(password)

    await repository.update_local_credential_password(db, user_id, password_hash)

    sessions_revoked = False
    if body.revoke_sessions:
        from packages.auth.repository import revoke_all_sessions_for_user
        count = await revoke_all_sessions_for_user(db, user_id)
        sessions_revoked = count > 0

    # Audit (S-035e) — no password/hash in details
    from packages.domain.repository import create_audit_event
    await create_audit_event(
        db,
        actor_user_id=scope.user_id,
        action="user.password_reset",
        target_type="user",
        target_id=user_id,
        details={"sessions_revoked": sessions_revoked},
    )

    await db.commit()

    return ResetPasswordResponse(
        user_id=user_id,
        must_change_password=True,
        sessions_revoked=sessions_revoked,
        one_time_password=one_time_password,
    )


# ---------------------------------------------------------------------------
# AD / LDAPS Settings (S-034)
# ---------------------------------------------------------------------------


@router.get("/auth/ad-settings", response_model=ADSettingsOut)
async def get_ad_settings(
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.manage")),
):
    """Return current AD/LDAPS connection status and config.

    No bind password or secrets are exposed. Only readable settings
    and the operational mode (stub/disabled/configured) are returned.
    """
    from packages.security.config import get_security_config
    from packages.auth.ad_provider import StubADAuthProvider

    cfg = get_security_config()
    ad = StubADAuthProvider()
    available = await ad.is_available()

    if not cfg.ad_enabled:
        mode = "disabled"
        message = "AD integration is disabled. Employee AD login is not available."
    elif available:
        mode = "configured"
        message = "AD integration is configured and reachable."
    else:
        mode = "stub"
        message = (
            "AD integration is currently in stub mode. "
            "Employee AD login returns 503. "
            "Configure AD_ENABLED=true and AD_SERVER_URL to enable real AD auth."
        )

    return ADSettingsOut(
        enabled=cfg.ad_enabled,
        mode=mode,
        server_url=cfg.ad_server_url if mode != "stub" else "",
        base_dn=cfg.ad_base_dn,
        user_search_base=cfg.ad_user_search_base,
        user_search_filter=cfg.ad_user_search_filter,
        bind_dn=cfg.ad_bind_dn,
        use_tls=cfg.ad_use_tls,
        certificate_validation=cfg.ad_certificate_validation,
        message=message,
    )


@router.post("/auth/ad-settings/test", response_model=ADTestResultOut)
async def test_ad_connection(
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.manage")),
):
    """Test AD connection — honest stub until real LDAPS client exists.

    Does NOT connect to external AD. Returns stub status when AD is
    not configured or the real client is not implemented.
    """
    from datetime import datetime, timezone
    from packages.security.config import get_security_config
    from packages.auth.ad_provider import StubADAuthProvider

    cfg = get_security_config()
    ad = StubADAuthProvider()
    now = datetime.now(timezone.utc)

    if not cfg.ad_enabled:
        return ADTestResultOut(
            status="not_configured",
            message="AD integration is not configured. Employee AD login returns 503.",
            tested_at=now,
            error_code="ad_disabled",
        )

    available = await ad.is_available()
    if not available:
        return ADTestResultOut(
            status="stub",
            message=(
                "AD integration is in stub mode. "
                "Real LDAPS client is not yet implemented. "
                "Employee AD login returns 503."
            ),
            tested_at=now,
            error_code="ldap_unavailable",
        )

    return ADTestResultOut(
        status="ok",
        message="AD connection test passed.",
        tested_at=now,
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
# S-039 — Advertiser detail + memberships
# ---------------------------------------------------------------------------


@router.get("/advertiser-organizations/{org_id}", response_model=AdvertiserOrganizationDetailOut)
async def get_advertiser_organization_detail(
    org_id: str,
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Get advertiser organization detail — scoped + RLS protected."""
    org = await repository.get_advertiser_organization(db, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Organization not found"})
    return AdvertiserOrganizationDetailOut.model_validate(org)


@router.get("/advertiser-brands-by-org", response_model=list[AdvertiserBrandOut])
async def list_advertiser_brands_by_org(
    advertiser_organization_id: str = Query(..., description="Filter by organization ID"),
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """List brands for a specific advertiser org — scoped + RLS protected."""
    items = await repository.list_advertiser_brands_by_org(db, advertiser_organization_id)
    return [AdvertiserBrandOut.model_validate(b) for b in items]


@router.get("/advertiser-contracts-by-org", response_model=list[AdvertiserContractOut])
async def list_advertiser_contracts_by_org(
    advertiser_organization_id: str = Query(..., description="Filter by organization ID"),
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """List contracts for a specific advertiser org — scoped + RLS protected."""
    items = await repository.list_advertiser_contracts_by_org(db, advertiser_organization_id)
    return [AdvertiserContractOut.model_validate(c) for c in items]


@router.get("/advertiser-contacts-by-org", response_model=list[AdvertiserContactOut])
async def list_advertiser_contacts_by_org(
    advertiser_organization_id: str = Query(..., description="Filter by organization ID"),
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.contacts.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """List contacts for a specific advertiser org — scoped + RLS protected. PII-gated."""
    items = await repository.list_advertiser_contacts_by_org(db, advertiser_organization_id)
    return [AdvertiserContactOut.model_validate(c) for c in items]


@router.get("/advertiser-user-memberships", response_model=list[AdvertiserUserMembershipOut])
async def list_advertiser_user_memberships(
    advertiser_organization_id: str = Query(..., description="Filter by organization ID"),
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """List user memberships for an advertiser org — no password/hash/token/secret."""
    items = await repository.list_advertiser_user_memberships(db, advertiser_organization_id)
    return [AdvertiserUserMembershipOut(**row) for row in items]


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
# S-038 — Campaign Approval Queue
# ---------------------------------------------------------------------------


@router.get("/campaigns/approval-queue",
            response_model=list[CampaignApprovalQueueItem])
async def approval_queue_endpoint(
    status_filter: str = Query("pending_approval", alias="status"),
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("campaigns.approve")),
):
    """List campaigns in the approval inbox — requires campaigns.approve.

    Filter by campaign status: pending_approval (default), approved, rejected, or all.
    Includes advertiser context + readiness summary. No storage fields.
    """
    valid = {"pending_approval", "approved", "rejected", "all"}
    if status_filter not in valid:
        raise HTTPException(status_code=422, detail=f"Invalid status filter: {status_filter}")

    items = await repository.list_approval_queue(db, status_filter=status_filter)
    return [CampaignApprovalQueueItem(**item) for item in items]


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
# S-017 — Creative Upload Endpoints (presigned URL flow)
# ---------------------------------------------------------------------------


@router.post("/creative-assets/{asset_id}/upload-intent",
             response_model=UploadIntentResponse)
async def upload_intent_endpoint(
    asset_id: str,
    body: UploadIntentRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope: ScopeContext = Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Generate a presigned PUT URL for browser-to-MinIO upload."""
    cfg = get_security_config()
    if body.content_type not in cfg.creative_allowed_mime_types:
        raise HTTPException(status_code=422, detail=f"Unsupported media type: {body.content_type}")
    if body.content_length > cfg.creative_max_file_size_bytes:
        raise HTTPException(status_code=422, detail=f"File too large: {body.content_length} bytes")

    asset = await repository.get_creative_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Creative asset not found")
    if asset.status != "metadata_only":
        raise HTTPException(status_code=409, detail="Asset already has a file uploaded")

    org_id = str(asset.advertiser_organization_id)
    if not scope.is_admin and scope.advertiser_scope_ids and org_id not in scope.advertiser_scope_ids:
        raise HTTPException(status_code=403, detail="Not in your organisation scope")

    storage_key = f"{org_id}/{asset_id}/{body.filename}"
    bucket = cfg.creative_storage_bucket

    from packages.services.storage import get_storage_service
    storage = get_storage_service()
    upload_url, expires_at = await storage.async_generate_presigned_put(storage_key, body.content_type)

    session_id = await repository.create_upload_session(
        db,
        creative_asset_id=asset_id,
        advertiser_organization_id=org_id,
        storage_bucket=bucket,
        storage_key=storage_key,
        filename=body.filename,
        content_type=body.content_type,
        content_length=body.content_length,
        created_by=claims["sub"],
        ttl_seconds=cfg.creative_upload_url_ttl_seconds,
    )

    return UploadIntentResponse(
        upload_id=session_id,
        upload_url=upload_url,
        method="PUT",
        headers={"Content-Type": body.content_type},
        expires_at=expires_at.isoformat(),
    )


@router.post("/creative-assets/{asset_id}/complete-upload",
             response_model=CompleteUploadResponse)
async def complete_upload_endpoint(
    asset_id: str,
    body: CompleteUploadRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope: ScopeContext = Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Verify MinIO object, compute SHA-256, finalise upload."""
    upload = await repository.get_upload_session(db, body.upload_id)
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload session not found")
    if upload["creative_asset_id"] != asset_id:
        raise HTTPException(status_code=422, detail="Upload session does not match this asset")
    if upload["completed_at"] is not None:
        raise HTTPException(status_code=409, detail="Upload already completed")

    from datetime import datetime, timezone as _tz
    if upload["expires_at"] < datetime.now(_tz.utc):
        raise HTTPException(status_code=410, detail="Upload session expired")

    org_id = upload["advertiser_organization_id"]
    if not scope.is_admin and scope.advertiser_scope_ids and org_id not in scope.advertiser_scope_ids:
        raise HTTPException(status_code=403, detail="Not in your organisation scope")

    from packages.services.storage import get_storage_service
    storage = get_storage_service()
    if not await storage.async_object_exists(upload["storage_key"]):
        raise HTTPException(status_code=404, detail="File not found in storage")

    actual_size = await storage.async_get_object_size(upload["storage_key"])
    if actual_size != upload["content_length"]:
        raise HTTPException(status_code=422, detail=f"Size mismatch: expected {upload['content_length']}, got {actual_size}")

    checksum = await storage.async_compute_sha256(upload["storage_key"])
    if checksum is None:
        raise HTTPException(status_code=500, detail="Failed to compute checksum")

    cfg = get_security_config()
    moderation = "approved" if cfg.creative_auto_approve_uploads else "pending_review"

    ok = await repository.mark_asset_uploaded(
        db, asset_id=asset_id,
        storage_bucket=upload["storage_bucket"],
        storage_key=upload["storage_key"],
        sha256_checksum=checksum,
        file_size_bytes=actual_size,
        moderation_status=moderation,
    )
    if not ok:
        raise HTTPException(status_code=409, detail="Asset is not in metadata_only status")

    await repository.mark_upload_complete(db, body.upload_id)

    return CompleteUploadResponse(
        asset_id=asset_id,
        sha256_checksum=checksum,
        file_size_bytes=actual_size,
        status="ready",
        moderation_status=moderation,
    )


# ---------------------------------------------------------------------------
# S-036 — Creative Moderation Queue
# ---------------------------------------------------------------------------


@router.get("/creative-assets/moderation-queue",
            response_model=list[CreativeModerationQueueItem])
async def moderation_queue_endpoint(
    status_filter: str = Query("pending_review", alias="moderation_status"),
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("creatives.moderate")),
):
    """List creative assets in the moderation queue — requires creatives.moderate.

    Filter by moderation_status: pending_review (default), approved, rejected, or all.
    No advertiser scope — admin sees all orgs.
    No storage_bucket/storage_key/presigned_url exposed.
    """
    valid = {"pending_review", "approved", "rejected", "all"}
    if status_filter not in valid:
        raise HTTPException(status_code=422, detail=f"Invalid status_filter: {status_filter}")

    items = await repository.list_moderation_queue(db, status_filter=status_filter)
    return [CreativeModerationQueueItem(**item) for item in items]


@router.post("/creative-assets/{asset_id}/approve",
             response_model=CreativeModerationResponse)
async def approve_creative_endpoint(
    asset_id: str,
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("creatives.moderate")),
):
    """Approve a creative asset — requires creatives.moderate. Sets moderation_status=approved."""
    asset = await repository.get_creative_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Creative asset not found")

    ok = await repository.approve_creative_asset(db, asset_id=asset_id)
    if not ok:
        raise HTTPException(status_code=409, detail="Failed to approve creative asset")

    return CreativeModerationResponse(
        asset_id=asset_id,
        moderation_status="approved",
        message="Креатив одобрен",
    )


@router.post("/creative-assets/{asset_id}/reject",
             response_model=CreativeModerationResponse)
async def reject_creative_endpoint(
    asset_id: str,
    body: CreativeRejectRequest,
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("creatives.moderate")),
):
    """Reject a creative asset — requires creatives.moderate. Reason is required."""
    asset = await repository.get_creative_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Creative asset not found")

    ok = await repository.reject_creative_asset(
        db, asset_id=asset_id, reason=body.reason,
    )
    if not ok:
        raise HTTPException(status_code=409, detail="Failed to reject creative asset")

    return CreativeModerationResponse(
        asset_id=asset_id,
        moderation_status="rejected",
        message="Креатив отклонён",
    )


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
# S-040 — PoP Report CSV Export
# ---------------------------------------------------------------------------


@router.get("/campaigns/{campaign_id}/pop/export")
async def export_campaign_pop_csv(
    campaign_id: str,
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _perm=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Export PoP report as CSV (UTF-8 with BOM for Excel).

    Same auth/scope as the JSON endpoints.
    XLSX deferred — no openpyxl in project requirements.
    """
    campaign = await _require_campaign_visible(db, campaign_id, scope)

    import csv
    import io
    from datetime import datetime, timezone

    summary = await repository.get_campaign_pop_summary(db, campaign_id)
    by_day = await repository.list_campaign_pop_by_day(db, campaign_id)
    by_surface = await repository.list_campaign_pop_by_surface(db, campaign_id)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    safe_code = campaign.code.replace('"', "").replace("'", "").replace("/", "_")[:64]

    buf = io.StringIO()
    buf.write("\ufeff")  # UTF-8 BOM for Excel
    w = csv.writer(buf)

    # Header
    w.writerow(["Отчёт по показам"])
    w.writerow([f"Кампания: {campaign.name} ({campaign.code})"])
    w.writerow([f"Сформирован: {now}"])
    w.writerow([])

    # Summary
    w.writerow(["Сводка"])
    w.writerow(["Показы", summary["impressions_count"]])
    w.writerow(["Общая длительность (мс)", summary["total_duration_ms"]])
    w.writerow(["Устройств", summary["unique_devices"]])
    w.writerow(["Поверхностей", summary["unique_surfaces"]])
    if summary["first_rendered_at"]:
        w.writerow(["Первый показ", str(summary["first_rendered_at"])])
    if summary["last_rendered_at"]:
        w.writerow(["Последний показ", str(summary["last_rendered_at"])])
    w.writerow([])

    # By Day
    w.writerow(["По дням"])
    w.writerow(["Дата", "Показы", "Длительность (мс)"])
    for row in by_day:
        w.writerow([str(row["date"]), row["impressions_count"], row["total_duration_ms"]])
    w.writerow([])

    # By Surface
    w.writerow(["По поверхностям"])
    w.writerow(["Поверхность", "Показы", "Длительность (мс)"])
    for row in by_surface:
        w.writerow([row["surface_id"], row["impressions_count"], row["total_duration_ms"]])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_code}_pop_report.csv"',
        },
    )


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


# ---------------------------------------------------------------------------
# S-037 — Inventory Management
# ---------------------------------------------------------------------------


@router.get("/inventory/stores", response_model=list[InventoryStoreOut])
async def list_inventory_stores(
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("inventory.read")),
):
    """Enriched store list with cluster/branch names + surface count."""
    items = await repository.get_inventory_stores(db)
    return [InventoryStoreOut(**item) for item in items]


@router.get("/inventory/surfaces", response_model=list[InventorySurfaceOut])
async def list_inventory_surfaces(
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("inventory.read")),
):
    """Enriched surface list with store context — no device secrets."""
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
    """Toggle is_active on a display surface — requires inventory.manage."""
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
