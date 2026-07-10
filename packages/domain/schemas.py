"""
Retail Media Platform — Pydantic API Schemas.

Phase 3.0: Read-only identity/RBAC response models.
Phase 3.2d: Auth API request/response DTOs.
No secret/password fields exposed.
"""

from datetime import datetime
from typing import Any, Literal

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

MAX_LIMIT = 100
DEFAULT_LIMIT = 20


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


class MeResponse(BaseModel):
    """Current user claims from JWT, enriched with DB data."""
    sub: str
    auth_provider: str
    username: str = ""
    display_name: str = ""
    permissions: list[str] = []


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
    """
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    media_type: str = Field(..., min_length=1, max_length=32)
    sha256_checksum: str = Field(..., min_length=1, max_length=64)
    file_size_bytes: int = Field(..., ge=0)
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
    """

    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    media_type: str = Field(..., min_length=1, max_length=32)
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
