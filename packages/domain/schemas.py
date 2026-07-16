"""
Retail Media Platform — Pydantic API Schemas.

Phase 3.0: Read-only identity/RBAC response models.
Phase 3.2d: Auth API request/response DTOs.
No secret/password fields exposed.
"""

from datetime import date as date_type, datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


class UserOut(BaseModel):
    """Public user representation — no password/secret fields."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    username: str
    email: str | None = None
    display_name: str
    auth_provider: str
    status: str
    is_break_glass: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    description: str = ""
    is_system: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    description: str = ""
    created_at: datetime | None = None


class AuditEventOut(BaseModel):
    """Operational audit event — details_json returned as-is (no secrets by contract)."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_user_id: str | None = None
    action: str
    target_type: str
    target_id: str | None = None
    correlation_id: str | None = None
    ip_address: str = ""
    details_json: Any | None = None
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

MAX_LIMIT = 200
DEFAULT_LIMIT = 50

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response — items + metadata."""
    items: list[T]
    total: int
    limit: int
    offset: int


class PaginatedUsers(BaseModel):
    items: list[UserOut]
    total: int
    limit: int
    offset: int


class PaginatedAuditEvents(BaseModel):
    items: list[AuditEventOut]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# S-033 — Admin User Management Schemas
# ---------------------------------------------------------------------------

class UserRoleAssignmentOut(BaseModel):
    """Role assigned to a user, with optional advertiser scope."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    role_id: str
    role_code: str = ""
    role_name: str = ""
    scope_type: str | None = None
    scope_id: str | None = None


class UserDetailOut(BaseModel):
    """Detailed user view for admin — roles, scopes, credential status."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    code: str
    username: str
    email: str | None = None
    display_name: str
    auth_provider: str
    status: str
    is_break_glass: bool = False
    must_change_password: bool = False
    roles: list[UserRoleAssignmentOut] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CreateLocalAdvertiserRequest(BaseModel):
    """Create a local advertiser user with scoped role."""
    username: str = Field(..., min_length=3, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=255)
    advertiser_organization_id: str = Field(..., min_length=1, max_length=36)
    temporary_password: str | None = Field(default=None, min_length=8, max_length=128)
    auto_generate_password: bool = False
    must_change_password: bool = True
    is_active: bool = True


class CreateLocalAdvertiserResponse(BaseModel):
    """Response after creating a local advertiser user."""
    user_id: str
    username: str
    display_name: str
    # Only returned once if auto_generate_password=True. Null otherwise.
    one_time_password: str | None = None
    message: str = "User created successfully."


class ResetPasswordRequest(BaseModel):
    """Admin-initiated password reset for a local user."""
    new_temporary_password: str | None = Field(default=None, min_length=8, max_length=128)
    auto_generate_password: bool = False
    revoke_sessions: bool = True


class ResetPasswordResponse(BaseModel):
    """Response after password reset."""
    user_id: str
    must_change_password: bool = True
    sessions_revoked: bool = True
    one_time_password: str | None = None
    message: str = "Password reset successfully."


class UserStatusResponse(BaseModel):
    """Response after activate/deactivate."""
    user_id: str
    status: str
    message: str


# ---------------------------------------------------------------------------
# Auth API — Request / Response DTOs (Phase 3.2d)
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """Login request body."""
    username_or_email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=256)
    auth_provider: Literal["ad", "local_advertiser", "local_break_glass"]


class LoginResponse(BaseModel):
    """Login success response — never includes refresh_token in JSON."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: "UserRefOut"


class UserRefOut(BaseModel):
    """Minimal user reference returned in login/me responses."""
    sub: str  # user_id
    auth_provider: str
    username: str = ""
    display_name: str = ""


class RefreshResponse(BaseModel):
    """Token refresh success — access_token only, refresh goes to cookie."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class LogoutResponse(BaseModel):
    """Logout response — idempotent success."""
    message: str = "Logged out"


class ChangePasswordRequest(BaseModel):
    """Change own password — only for local providers."""
    current_password: str
    new_password: str


class ChangePasswordResponse(BaseModel):
    """Password change result — no secrets."""
    message: str = "Password changed"


class MeResponse(BaseModel):
    """Current user profile — loaded from DB, not JWT claims."""
    sub: str
    auth_provider: str
    username: str = ""
    display_name: str = ""
    permissions: list[str] = []
    must_change_password: bool = False


# ---------------------------------------------------------------------------
# Phase 3.5b — Advertiser organization (RLS pilot)
# ---------------------------------------------------------------------------


class AdvertiserOrganizationOut(BaseModel):
    """Public advertiser organization — no internal fields."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    legal_name: str
    display_name: str
    status: str


# ---------------------------------------------------------------------------
# Phase 4.0b — Advertiser domain (brands, contracts, contacts)
# ---------------------------------------------------------------------------


class AdvertiserBrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    advertiser_organization_id: str
    code: str
    name: str
    description: str | None = None
    status: str


class AdvertiserContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    advertiser_organization_id: str
    code: str
    name: str
    contract_number: str | None = None
    budget_limit_amount: float | None = None
    budget_limit_currency: str
    valid_from: datetime
    valid_until: datetime | None = None
    status: str
    terms_url: str | None = None


class AdvertiserContactOut(BaseModel):
    """Public contact — PII-gated by permission check in router.

    email/phone exposed only after require_scoped_permission('advertisers.contacts.read').
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    advertiser_organization_id: str
    contact_type: str
    full_name: str
    email: str
    phone: str | None = None
    is_primary: bool
    status: str


class AdvertiserUserMembershipOut(BaseModel):
    """Safe membership view — no password/hash/token/secret."""
    model_config = ConfigDict(from_attributes=False)

    id: str
    user_id: str
    username: str
    display_name: str
    email: str | None = None
    auth_provider: str
    user_status: str
    must_change_password: bool
    membership_status: str
    membership_created_at: datetime | None = None


class AdvertiserOrganizationDetailOut(BaseModel):
    """Organization detail — enriched with timestamps + counts."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    legal_name: str
    display_name: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Campaign Domain (Phase 4.1b — ADR-015)
# ---------------------------------------------------------------------------


class CampaignOut(BaseModel):
    """Campaign read-only DTO. No PII, no storage secrets."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    advertiser_organization_id: str
    advertiser_brand_id: str | None = None
    advertiser_contract_id: str
    code: str
    name: str
    description: str | None = None
    status: str
    priority: int = 0
    budget_limit_amount: float | None = None
    budget_limit_currency: str = "RUB"
    start_at: datetime | None = None
    end_at: datetime | None = None
    timezone: str = "Europe/Moscow"
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime


class CampaignFlightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    name: str | None = None
    start_at: datetime
    end_at: datetime
    dayparting_json: Any | None = None
    days_of_week: list[int] | None = None
    priority: int = 0
    created_at: datetime


class CreativeAssetOut(BaseModel):
    """Creative asset metadata DTO. No presigned URLs, no raw binary."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    advertiser_organization_id: str
    code: str
    name: str
    media_type: str
    sha256_checksum: str
    file_size_bytes: int
    duration_ms: int | None = None
    resolution_w: int | None = None
    resolution_h: int | None = None
    status: str
    moderation_status: str
    moderation_notes: str | None = None
    created_at: datetime
    updated_at: datetime


class CampaignCreativeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    creative_asset_id: str
    sort_order: int = 0
    duration_override_ms: int | None = None
    created_at: datetime


class CampaignPlacementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    display_surface_id: str | None = None
    store_id: str | None = None
    cluster_id: str | None = None
    branch_id: str | None = None
    share_of_voice_pct: int = 100
    max_impressions: int | None = None
    impressions_delivered: int = 0
    status: str
    created_at: datetime


class CampaignApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    requested_by: str
    requested_at: datetime
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    decision: str | None = None
    rejection_reason: str | None = None
    created_at: datetime


class CampaignStatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    old_status: str | None = None
    new_status: str
    changed_by: str
    changed_at: datetime
    reason: str | None = None


# ---------------------------------------------------------------------------
# Campaign Mutation Schemas (Phase 4.1c — ADR-015)
# ---------------------------------------------------------------------------


class CampaignCreateRequest(BaseModel):
    """Create a draft campaign. No PII, no storage secrets."""
    advertiser_organization_id: str
    advertiser_brand_id: str | None = None
    advertiser_contract_id: str
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    timezone: str = "Europe/Moscow"
    budget_limit_amount: float | None = None
    budget_limit_currency: str = "RUB"
    priority: int = 0


class CampaignUpdateRequest(BaseModel):
    """Update a draft campaign. All fields optional — partial update."""
    advertiser_brand_id: str | None = None
    advertiser_contract_id: str | None = None
    code: str | None = Field(None, min_length=1, max_length=64)
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    timezone: str | None = None
    budget_limit_amount: float | None = None
    budget_limit_currency: str | None = None
    priority: int | None = None


class CampaignArchiveResponse(BaseModel):
    """Response after archiving a campaign."""
    message: str = "Campaign archived"
    campaign_id: str
    old_status: str
    new_status: str = "archived"


# ── Campaign Flight / Placement / Creative Mutation Schemas (Pilot B1) ──


class CampaignFlightCreateRequest(BaseModel):
    """Create a flight for a draft campaign."""
    name: str | None = Field(None, max_length=255)
    start_at: datetime
    end_at: datetime
    dayparting_json: Any | None = None
    days_of_week: list[int] | None = None
    priority: int = 0


class CampaignFlightUpdateRequest(BaseModel):
    """Partial update for a flight. All fields optional."""
    name: str | None = Field(None, max_length=255)
    start_at: datetime | None = None
    end_at: datetime | None = None
    dayparting_json: Any | None = None
    days_of_week: list[int] | None = None
    priority: int | None = None


class CampaignPlacementCreateRequest(BaseModel):
    """Create a placement for a draft campaign. At least one target required."""
    display_surface_id: str | None = None
    store_id: str | None = None
    cluster_id: str | None = None
    branch_id: str | None = None
    share_of_voice_pct: int = Field(default=100, ge=0, le=100)
    max_impressions: int | None = Field(None, ge=0)


class CampaignPlacementUpdateRequest(BaseModel):
    """Partial update for a placement. All fields optional."""
    display_surface_id: str | None = None
    store_id: str | None = None
    cluster_id: str | None = None
    branch_id: str | None = None
    share_of_voice_pct: int | None = Field(None, ge=0, le=100)
    max_impressions: int | None = Field(None, ge=0)


class CampaignCreativeCreateRequest(BaseModel):
    """Create a creative asset and attach it to a draft campaign.

    Storage fields (storage_bucket, storage_key) are auto-filled with
    pilot-safe defaults.  The response (CreativeAssetOut) never exposes
    them.

    S-017: sha256_checksum and file_size_bytes are OPTIONAL and IGNORED.
    Assets are always created as metadata_only/pending_review.
    The only path to ready/approved is complete-upload with server SHA-256.
    """
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    media_type: str = Field(..., min_length=1, max_length=32)
    sha256_checksum: str = Field("", max_length=64)
    file_size_bytes: int = Field(0, ge=0)
    duration_ms: int | None = Field(None, ge=1)
    resolution_w: int | None = Field(None, ge=1)
    resolution_h: int | None = Field(None, ge=1)
    sort_order: int = 0
    duration_override_ms: int | None = Field(None, ge=1)


class CampaignCreativeAttachRequest(BaseModel):
    """Attach an existing creative asset to a draft campaign.

    Cross-org and non-draft attachment is rejected by the handler.
    """
    creative_asset_id: str = Field(..., min_length=1, max_length=36)
    sort_order: int = 0


class CreativeAssetCreateRequest(BaseModel):
    """Create a creative asset in the library (metadata only, no file upload).

    Business-friendly: name + code + human media_type label required.
    Technical params (checksum, dimensions, duration, file size) are optional
    and rendered in a collapsed section in the UI.  Storage bucket/key are
    never part of this schema — they are auto-filled on creation and never
    returned in CreativeAssetOut per ADR-008.

    advertiser_organization_id is optional.  When absent, the endpoint
    derives it from the caller's JWT scope.  Admins (no scope) must
    provide it explicitly.
    """

    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    media_type: str = Field(..., min_length=1, max_length=32)
    advertiser_organization_id: str | None = Field(None, max_length=36)
    sha256_checksum: str = Field(
        default="",
        min_length=0,
        max_length=64,
        description="Auto-filled if empty (pilot-safe placeholder).",
    )
    file_size_bytes: int | None = Field(None, ge=0)
    resolution_w: int | None = Field(None, ge=1)
    resolution_h: int | None = Field(None, ge=1)
    duration_ms: int | None = Field(None, ge=1)


# ---------------------------------------------------------------------------
# Approval Workflow Schemas (Phase 4.1d — ADR-015)
# ---------------------------------------------------------------------------


class CampaignRejectRequest(BaseModel):
    """Reject a pending_approval campaign. Reason is required per ADR-015."""
    reason: str = Field(..., min_length=1, max_length=1000)


class CampaignApprovalResponse(BaseModel):
    """Response after an approval action (approve/reject/request)."""
    message: str
    campaign_id: str
    old_status: str
    new_status: str


# ---------------------------------------------------------------------------
# S-038 — Campaign Approval Queue Schemas
# ---------------------------------------------------------------------------


class CampaignApprovalQueueItem(BaseModel):
    """Campaign in the approval inbox — includes advertiser context + readiness summary."""
    campaign_id: str
    campaign_code: str
    campaign_name: str
    campaign_status: str
    advertiser_org_id: str | None = None
    advertiser_org_name: str | None = None
    advertiser_brand_name: str | None = None
    requested_at: datetime | None = None
    requested_by: str | None = None
    # Readiness summary
    has_flight: bool = False
    has_placement: bool = False
    has_creative: bool = False
    all_creatives_ready: bool = False
    all_creatives_approved: bool = False
    rejection_reason: str | None = None


# ---------------------------------------------------------------------------
# PoP Ingestion Schemas (Phase 4.3c — ADR-017)
# ---------------------------------------------------------------------------

POP_MAX_BATCH_SIZE = 500
POP_SCHEMA_VERSION = "1.0"
POP_MAX_DURATION_MS = 86_400_000
POP_QUARANTINE_TTL_HOURS = 72
POP_CLOCK_DRIFT_MINUTES = 5


class PopEventIn(BaseModel):
    """Single PoP event in a batch request. Device-submitted, validated server-side."""
    event_id: str = Field(..., min_length=1, max_length=64)
    schema_version: str = Field(default=POP_SCHEMA_VERSION, min_length=1, max_length=8)
    device_id: str = Field(..., min_length=1, max_length=64)
    manifest_id: str | None = Field(default=None, max_length=128)
    campaign_id: str | None = Field(default=None, max_length=64)
    creative_asset_id: str = Field(..., min_length=1, max_length=64)
    surface_id: str = Field(..., min_length=1, max_length=64)
    duration_ms: int = Field(..., ge=1, le=POP_MAX_DURATION_MS)
    playback_result: Literal["success", "fallback", "interrupted", "failed"]
    rendered_at: datetime
    event_recorded_at: datetime


class PopBatchRequest(BaseModel):
    """Batch of PoP events from a device."""
    events: list[PopEventIn] = Field(..., min_length=1, max_length=POP_MAX_BATCH_SIZE)


class PopEventResult(BaseModel):
    """Per-event ingestion result."""
    event_id: str
    status: Literal["accepted", "quarantined", "rejected", "duplicate"]
    reason: str | None = None


class PopBatchResponse(BaseModel):
    """Batch ingestion response."""
    accepted_count: int = 0
    rejected_count: int = 0
    quarantined_count: int = 0
    duplicate_count: int = 0
    results: list[PopEventResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# PoP Reporting Schemas (Phase 4.3d — ADR-017 §6)
# ---------------------------------------------------------------------------


class CampaignPopSummaryOut(BaseModel):
    """Billing-grade campaign PoP summary. No PII, no secrets."""
    campaign_id: str
    impressions_count: int = 0
    total_duration_ms: int = 0
    first_rendered_at: datetime | None = None
    last_rendered_at: datetime | None = None
    unique_devices: int = 0
    unique_surfaces: int = 0


class CampaignPopByDayOut(BaseModel):
    """Daily PoP breakdown row."""
    date: str  # YYYY-MM-DD
    impressions_count: int = 0
    total_duration_ms: int = 0


class CampaignPopBySurfaceOut(BaseModel):
    """Per-surface PoP breakdown row."""
    surface_id: str
    impressions_count: int = 0
    total_duration_ms: int = 0


# ── S-009h: Reference data read-only DTOs ──

class BranchOut(BaseModel):
    """Branch reference — no PII, no secrets."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    code: str
    name: str
    is_active: bool = True


class ClusterOut(BaseModel):
    """Cluster reference — includes parent branch."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    branch_id: str
    code: str
    name: str
    is_active: bool = True


class StoreOut(BaseModel):
    """Store reference — includes parent cluster + address."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    cluster_id: str
    code: str
    name: str
    address: str
    is_active: bool = True


class DisplaySurfaceOut(BaseModel):
    """Display surface reference — surface code + store + resolution."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    store_id: str
    code: str
    resolution_w: int = 1920
    resolution_h: int = 1080
    is_active: bool = True


# ---------------------------------------------------------------------------
# S-037 — Inventory Management Schemas
# ---------------------------------------------------------------------------


class InventoryStoreOut(BaseModel):
    """Enriched store view — includes cluster/branch names + surface count."""
    id: str
    code: str
    name: str
    address: str
    is_active: bool
    cluster_name: str | None = None
    branch_name: str | None = None
    surface_count: int = 0


class InventorySurfaceOut(BaseModel):
    """Enriched display surface view — includes store context, no device secrets."""
    id: str
    code: str
    store_id: str
    store_code: str | None = None
    store_name: str | None = None
    resolution_w: int = 1920
    resolution_h: int = 1080
    is_active: bool = True


class InventorySurfacePatchRequest(BaseModel):
    """Partial update for a display surface — only safe fields for pilot."""
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# S-036 — Creative Moderation Queue Schemas
# ---------------------------------------------------------------------------


class CreativeModerationQueueItem(BaseModel):
    """Item in the moderation queue — includes advertiser context, no storage secrets."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    advertiser_organization_id: str
    code: str
    name: str
    media_type: str
    file_size_bytes: int
    duration_ms: int | None = None
    resolution_w: int | None = None
    resolution_h: int | None = None
    status: str
    moderation_status: str
    moderation_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    # Joined advertiser context
    advertiser_name: str | None = None
    advertiser_code: str | None = None


class CreativeRejectRequest(BaseModel):
    """Reject a creative asset — reason is required."""
    reason: str = Field(..., min_length=1, max_length=1000)


class CreativeModerationResponse(BaseModel):
    """Response after approve/reject action."""
    asset_id: str
    moderation_status: str
    message: str


# ---------------------------------------------------------------------------
# S-017 — Creative Upload Schemas
# ---------------------------------------------------------------------------


class UploadIntentRequest(BaseModel):
    """Request a presigned upload URL for a creative asset."""
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=1, max_length=64)
    content_length: int = Field(..., gt=0)


class UploadIntentResponse(BaseModel):
    """Response with presigned PUT URL — browser uploads directly to MinIO."""
    upload_id: str
    upload_url: str
    method: str = "PUT"
    headers: dict[str, str] = Field(default_factory=dict)
    expires_at: str


class CompleteUploadRequest(BaseModel):
    """Confirm upload completion by upload session ID."""
    upload_id: str = Field(..., min_length=1, max_length=36)


class CompleteUploadResponse(BaseModel):
    """Response after server computes SHA-256 from MinIO object."""
    asset_id: str
    sha256_checksum: str
    file_size_bytes: int
    status: str
    moderation_status: str


# ---------------------------------------------------------------------------
# S-034 — AD / LDAPS Settings
# ---------------------------------------------------------------------------


class ADSettingsOut(BaseModel):
    """Safe AD connection settings — never exposes bind password or secrets."""

    enabled: bool
    mode: str  # "stub" | "disabled" | "configured"
    server_url: str = ""  # masked for security — only shown in dev/stub
    base_dn: str = ""
    user_search_base: str = ""
    user_search_filter: str = "(sAMAccountName={username})"
    bind_dn: str = ""  # shown, but password is never included
    use_tls: bool = True
    certificate_validation: str = "required"
    message: str = ""


class ADTestResultOut(BaseModel):
    """Result of a test AD connection."""

    status: str  # "ok" | "stub" | "not_configured" | "error"
    message: str
    tested_at: datetime | None = None
    error_code: str | None = None


# ---------------------------------------------------------------------------
# S-070 — Fleet / Device Health
# ---------------------------------------------------------------------------


class DeviceOut(BaseModel):
    """Safe device representation — no secrets/tokens/HMAC keys."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    store_id: str
    device_type_id: str
    code: str
    serial_number: str = ""
    os_version: str = ""
    ip_address: str = ""
    status: str
    last_seen_at: datetime | None = None
    current_manifest_id: str | None = None
    cache_size_bytes: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DeviceSummaryOut(BaseModel):
    """Aggregated fleet health summary."""

    total: int = 0
    active: int = 0
    inactive: int = 0
    error: int = 0
    unregistered: int = 0


class PaginatedDevices(BaseModel):
    items: list[DeviceOut]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# S-071 — Emergency Override
# ---------------------------------------------------------------------------


class EmergencyStatusOut(BaseModel):
    """Current emergency override status."""

    active: bool = False
    reason: str = ""
    activated_by: str | None = None
    activated_at: datetime | None = None


class EmergencyActivateRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class EmergencyDeactivateRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


# ---------------------------------------------------------------------------
# Inventory Domain (v0.7 Foundation — S-077)
# ---------------------------------------------------------------------------


class InventorySlotOut(BaseModel):
    """Single inventory slot — one hour of one display surface."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_surface_id: str
    slot_date: date_type
    slot_hour: int
    total_capacity: int = 0
    booked_capacity: int = 0
    reserved_capacity: int = 0
    internal_blocked_capacity: int = 0
    emergency_blocked_capacity: int = 0
    status: str = "available"
    created_at: datetime
    updated_at: datetime


class InventorySlotCreate(BaseModel):
    """Create or get-or-create a slot for a surface/date/hour."""
    display_surface_id: str
    slot_date: date_type
    slot_hour: int = Field(ge=0, le=23)
    total_capacity: int = Field(default=0, ge=0)


class InventoryBookingOut(BaseModel):
    """Booking linking a campaign placement to an inventory slot."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str | None = None
    campaign_placement_id: str | None = None
    inventory_slot_id: str
    capacity_units: int
    status: str = "reserved"
    reserved_until: datetime | None = None
    committed_at: datetime | None = None
    released_at: datetime | None = None
    release_reason: str = ""
    created_at: datetime
    updated_at: datetime


class InventoryBookingCreate(BaseModel):
    """Reserve capacity on a slot."""
    campaign_id: str | None = None
    campaign_placement_id: str | None = None
    inventory_slot_id: str
    capacity_units: int = Field(gt=0)


class InventoryRuleOut(BaseModel):
    """Business rule for inventory."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    scope_type: str = "global"
    scope_id: str | None = None
    rule_type: str
    priority: int = 100
    value_json: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class InventoryRuleCreate(BaseModel):
    """Create an inventory rule."""
    scope_type: str = "global"
    scope_id: str | None = None
    rule_type: str
    priority: int = Field(default=100, ge=0)
    value_json: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class InventoryRuleUpdate(BaseModel):
    """Partial update — only provided fields are changed."""
    scope_type: str | None = None
    scope_id: str | None = None
    rule_type: str | None = None
    priority: int | None = Field(default=None, ge=0)
    value_json: dict[str, Any] | None = None
    is_active: bool | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


# ---------------------------------------------------------------------------
# Inventory Availability (S-078)
# ---------------------------------------------------------------------------


class InventoryAvailabilityRequest(BaseModel):
    """Request availability check for a surface over a time range."""
    surface_id: str
    starts_at: datetime
    ends_at: datetime
    requested_capacity_units: int | None = Field(None, ge=1)
    requested_sov_percent: int | None = Field(None, ge=1, le=100)


class InventorySlotAvailability(BaseModel):
    """Per-slot availability info."""
    slot_id: str
    slot_date: date_type
    slot_hour: int
    total_capacity: int
    booked_capacity: int
    reserved_capacity: int
    available_capacity: int
    requested_capacity: int
    available: bool
    sold_out: bool
    blocked: bool


class InventoryAvailabilityResponse(BaseModel):
    """Aggregate availability result for a time range."""
    surface_id: str
    starts_at: datetime
    ends_at: datetime
    all_available: bool
    total_requested: int
    total_available: int
    slots: list[InventorySlotAvailability]
    conflicts: list[InventorySlotAvailability]


# ---------------------------------------------------------------------------
# S-079 — Inventory Reservation schemas
# ---------------------------------------------------------------------------


class CampaignInventoryReservationOut(BaseModel):
    """Single inventory booking row for a campaign."""
    booking_id: str
    campaign_id: str | None = None
    placement_id: str | None = None
    slot_id: str
    capacity_units: int
    status: str
    reserved_until: str | None = None
    committed_at: str | None = None
    released_at: str | None = None
    release_reason: str = ""
    created_at: str | None = None


class CampaignInventoryReservationsResponse(BaseModel):
    """List of inventory reservations for a campaign."""
    campaign_id: str
    reservations: list[CampaignInventoryReservationOut]
    total: int


# ---------------------------------------------------------------------------
# S-080 — Inventory Conflict Detection schemas
# ---------------------------------------------------------------------------


class InventoryConflictItem(BaseModel):
    """Single conflict found during availability/reservation check."""
    conflict_type: str
    severity: str  # "blocking" | "warning"
    surface_id: str
    message: str
    rule_id: str | None = None
    rule_type: str | None = None
    slot_date: str | None = None
    slot_hour: int | None = None
    available_capacity: int | None = None
    requested_capacity: int | None = None
    max_sov_percent: int | None = None
    requested_sov_percent: int | None = None
    capacity_units: int | None = None
    placement_id: str | None = None


class InventoryConflictCheckRequest(BaseModel):
    """Request to check for inventory conflicts."""
    surface_id: str
    starts_at: datetime
    ends_at: datetime
    requested_capacity_units: int | None = Field(None, ge=1)
    requested_sov_percent: int | None = Field(None, ge=1, le=100)
    campaign_id: str | None = None


class InventoryConflictCheckResponse(BaseModel):
    """Result of conflict detection check."""
    has_conflicts: bool
    blocking: list[InventoryConflictItem] = Field(default_factory=list)
    warnings: list[InventoryConflictItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# S-087 — Inventory Alternatives
# ---------------------------------------------------------------------------


class InventoryAlternative(BaseModel):
    """Single suggested alternative placement."""
    alternative_type: str  # SAME_STORE_SURFACE | SAME_SURFACE_TIME | LOWER_SOV | LATER_TIME
    surface_id: str
    surface_code: str | None = None
    surface_name: str | None = None
    store_id: str | None = None
    store_code: str | None = None
    store_name: str | None = None
    starts_at: str
    ends_at: str
    available_capacity: int
    suggested_capacity_units: int | None = None
    suggested_sov_percent: int | None = None
    reason: str
    score: int  # higher = better match


class InventoryAlternativesRequest(BaseModel):
    """Request alternatives for an unavailable placement."""
    surface_id: str
    starts_at: datetime
    ends_at: datetime
    requested_capacity_units: int | None = Field(None, ge=1)
    requested_sov_percent: int | None = Field(None, ge=1, le=100)
    max_results: int = Field(5, ge=1, le=20)


class InventoryAlternativesResponse(BaseModel):
    """Suggested alternatives when a placement is unavailable."""
    surface_id: str
    alternatives: list[InventoryAlternative] = Field(default_factory=list)
    total_found: int


# ---------------------------------------------------------------------------
# S-089 — Inventory Simulation
# ---------------------------------------------------------------------------


class InventorySimulationRequest(BaseModel):
    """Request a pre-approval inventory simulation for a campaign."""
    campaign_id: str


class InventorySimulationPlacementResult(BaseModel):
    """Per-placement simulation result."""
    placement_id: str
    surface_id: str
    surface_code: str | None = None
    surface_name: str | None = None
    store_code: str | None = None
    store_name: str | None = None
    fit: bool
    slot_fill_percent: float = Field(0.0, ge=0.0)
    total_requested: int = 0
    total_available: int = 0
    conflicts: list[InventoryConflictItem] = Field(default_factory=list)
    applied_rules: list[dict] = Field(default_factory=list)


class InventorySimulationResponse(BaseModel):
    """Full pre-approval simulation result for a campaign."""
    campaign_id: str
    overall_fit: bool
    placements: list[InventorySimulationPlacementResult] = Field(default_factory=list)
    blocking_count: int = 0
    warning_count: int = 0
