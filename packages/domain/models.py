"""
Retail Media Platform — SQLAlchemy ORM Models.

Phase 2: Foundation tables only — organization, channels, devices, surfaces.
No identity/auth, no campaigns, no content, no inventory yet.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship

__all__ = [
    "Base",
    "Branch",
    "Cluster",
    "Store",
    "Channel",
    "DeviceType",
    "CapabilityProfile",
    "PhysicalDevice",
    "DeviceCertificate",
    "DeviceStatusHistory",
    "LogicalCarrier",
    "DisplaySurface",
    "User",
    "Role",
    "Permission",
    "RolePermission",
    "UserRole",
    "AccessScope",
    "UserAccessScope",
    "AuditEventOperational",
    "AdvertiserOrganization",
    "AdvertiserUserMembership",
    "AdvertiserBrand",
    "AdvertiserContract",
    "AdvertiserContact",
    "LocalCredential",
    "RefreshSession",
    "LoginAttempt",
    "PasswordResetToken",
    "Campaign",
    "CampaignFlight",
    "CampaignPlacement",
    "CreativeAsset",
    "CampaignCreative",
    "CampaignApproval",
    "CampaignStatusHistory",
    "OutboxEvent",
    "DeliveryPlan",
    "DeliveryManifest",
    "DeliveryManifestSurface",
    "DeliveryManifestAsset",
    "DeliveryAttempt",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------

class Branch(Base):
    __tablename__ = "branches"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    code = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    timezone = Column(String(64), nullable=False, default="Europe/Moscow")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    clusters = relationship("Cluster", back_populates="branch")


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=False, index=True)
    code = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    branch = relationship("Branch", back_populates="clusters")
    stores = relationship("Store", back_populates="cluster")


class Store(Base):
    __tablename__ = "stores"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    cluster_id = Column(String(36), ForeignKey("clusters.id"), nullable=False, index=True)
    code = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=False, default="")
    timezone = Column(String(64), nullable=False, default="Europe/Moscow")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    cluster = relationship("Cluster", back_populates="stores")
    physical_devices = relationship("PhysicalDevice", back_populates="store")


# ---------------------------------------------------------------------------
# Channel Model
# ---------------------------------------------------------------------------

class Channel(Base):
    __tablename__ = "channels"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    code = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    device_types = relationship("DeviceType", back_populates="channel")


class DeviceType(Base):
    __tablename__ = "device_types"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    channel_id = Column(String(36), ForeignKey("channels.id"), nullable=False, index=True)
    code = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    player_runtime = Column(String(64), nullable=False, default="chromium")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    channel = relationship("Channel", back_populates="device_types")
    capability_profiles = relationship("CapabilityProfile", back_populates="device_type")
    physical_devices = relationship("PhysicalDevice", back_populates="device_type")


class CapabilityProfile(Base):
    __tablename__ = "capability_profiles"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    device_type_id = Column(String(36), ForeignKey("device_types.id"), nullable=False, index=True)
    code = Column(String(64), nullable=False, unique=True, index=True)
    resolution_w = Column(Integer, nullable=False, default=1920)
    resolution_h = Column(Integer, nullable=False, default=1080)
    orientation = Column(String(16), nullable=False, default="landscape")
    supported_formats = Column(ARRAY(String), nullable=False, default=[])
    max_file_size_bytes = Column(Integer, nullable=False, default=10_485_760)
    max_duration_sec = Column(Integer, nullable=False, default=30)
    supports_video = Column(Boolean, nullable=False, default=False)
    supports_animation = Column(Boolean, nullable=False, default=False)
    supports_interactive = Column(Boolean, nullable=False, default=False)
    pop_mode = Column(String(32), nullable=False, default="real_playback")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    device_type = relationship("DeviceType", back_populates="capability_profiles")


# ---------------------------------------------------------------------------
# Physical Devices
# ---------------------------------------------------------------------------

class PhysicalDevice(Base):
    __tablename__ = "physical_devices"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False, index=True)
    device_type_id = Column(String(36), ForeignKey("device_types.id"), nullable=False, index=True)
    code = Column(String(128), nullable=False, unique=True, index=True)
    serial_number = Column(String(255), nullable=False, default="")
    hardware_fingerprint = Column(String(255), nullable=False, default="")
    os_version = Column(String(64), nullable=False, default="")
    ip_address = Column(String(45), nullable=False, default="")
    status = Column(
        String(32), nullable=False, default="unregistered",
        comment="Current state CACHE. See device_status_history for authoritative transitions.",
    )
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    current_manifest_id = Column(String(36), nullable=True)
    cache_size_bytes = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    store = relationship("Store", back_populates="physical_devices")
    device_type = relationship("DeviceType", back_populates="physical_devices")
    certificates = relationship("DeviceCertificate", back_populates="device")
    status_history = relationship("DeviceStatusHistory", back_populates="device",
                                   order_by="DeviceStatusHistory.changed_at")
    logical_carriers = relationship("LogicalCarrier", back_populates="physical_device")


class DeviceCertificate(Base):
    __tablename__ = "device_certificates"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    physical_device_id = Column(String(36), ForeignKey("physical_devices.id"),
                                nullable=False, index=True)
    certificate_type = Column(String(32), nullable=False, default="ed25519")
    public_key = Column(Text, nullable=False, default="")
    fingerprint = Column(String(128), nullable=False, default="")
    issued_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    device = relationship("PhysicalDevice", back_populates="certificates")


class DeviceStatusHistory(Base):
    __tablename__ = "device_status_history"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    physical_device_id = Column(String(36), ForeignKey("physical_devices.id"),
                                nullable=False, index=True)
    old_status = Column(String(32), nullable=False, default="")
    new_status = Column(String(32), nullable=False)
    changed_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    reason = Column(String(255), nullable=False, default="")
    source = Column(String(32), nullable=False, default="manual")
    details_json = Column(JSONB, nullable=True)

    device = relationship("PhysicalDevice", back_populates="status_history")


# ---------------------------------------------------------------------------
# Logical Carriers and Display Surfaces
# ---------------------------------------------------------------------------

class LogicalCarrier(Base):
    __tablename__ = "logical_carriers"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    physical_device_id = Column(String(36), ForeignKey("physical_devices.id"),
                                nullable=False, index=True)
    code = Column(String(128), nullable=False, unique=True, index=True)
    carrier_type = Column(String(32), nullable=False, default="direct")
    vendor_name = Column(String(255), nullable=False, default="")
    vendor_config_json = Column(JSONB, nullable=True)
    labels_count = Column(Integer, nullable=True)
    led_panels_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    physical_device = relationship("PhysicalDevice", back_populates="logical_carriers")
    display_surfaces = relationship("DisplaySurface", back_populates="logical_carrier")


class DisplaySurface(Base):
    __tablename__ = "display_surfaces"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    logical_carrier_id = Column(String(36), ForeignKey("logical_carriers.id"),
                                nullable=False, index=True)
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False, index=True)
    code = Column(String(128), nullable=False, unique=True, index=True)
    zone_id = Column(String(36), nullable=True)
    shelf_id = Column(String(36), nullable=True)
    category_id = Column(String(36), nullable=True)
    sku_group_id = Column(String(36), nullable=True)
    resolution_w = Column(Integer, nullable=False, default=1920)
    resolution_h = Column(Integer, nullable=False, default=1080)
    is_active = Column(Boolean, nullable=False, default=True)
    current_manifest_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    logical_carrier = relationship("LogicalCarrier", back_populates="display_surfaces")


# ---------------------------------------------------------------------------
# Identity / RBAC / RLS / Audit (Phase 2.1)
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    code = Column(String(64), nullable=False, unique=True, index=True)
    username = Column(String(128), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True, unique=True)
    display_name = Column(String(255), nullable=False)
    auth_provider = Column(String(32), nullable=False, default="local")
    external_subject = Column(String(255), nullable=True)
    status = Column(String(32), nullable=False, default="active")
    is_break_glass = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    roles = relationship("UserRole", back_populates="user")
    access_scopes = relationship("UserAccessScope", back_populates="user")


class Role(Base):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    code = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    is_system = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    permissions = relationship("RolePermission", back_populates="role")
    user_assignments = relationship("UserRole", back_populates="role")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    code = Column(String(128), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    roles = relationship("RolePermission", back_populates="permission")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=False, index=True)
    permission_id = Column(String(36), ForeignKey("permissions.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        # scope_type and scope_id are either both NULL or both NOT NULL
        CheckConstraint(
            "(scope_type IS NULL) = (scope_id IS NULL)",
            name="ck_user_role_scope_pair",
        ),
        # Prevent duplicate scoped assignments
        UniqueConstraint("user_id", "role_id", "scope_type", "scope_id",
                         name="uq_user_role_scoped"),
        # Prevent duplicate unscoped (global) assignments
        Index("uq_user_role_unscoped", "user_id", "role_id",
              unique=True,
              postgresql_where=text("scope_type IS NULL AND scope_id IS NULL")),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=False, index=True)
    scope_type = Column(String(32), nullable=True)
    scope_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="user_assignments")


class AccessScope(Base):
    __tablename__ = "access_scopes"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    code = Column(String(64), nullable=False, unique=True, index=True)
    scope_type = Column(String(32), nullable=False)
    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=True, index=True)
    cluster_id = Column(String(36), ForeignKey("clusters.id"), nullable=True, index=True)
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, index=True)
    advertiser_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    user_assignments = relationship("UserAccessScope", back_populates="access_scope")


class UserAccessScope(Base):
    __tablename__ = "user_access_scopes"
    __table_args__ = (
        UniqueConstraint("user_id", "access_scope_id", name="uq_user_access_scope"),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    access_scope_id = Column(String(36), ForeignKey("access_scopes.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    user = relationship("User", back_populates="access_scopes")
    access_scope = relationship("AccessScope", back_populates="user_assignments")


class AuditEventOperational(Base):
    __tablename__ = "audit_events_operational"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    actor_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(128), nullable=False, index=True)
    target_type = Column(String(64), nullable=False, index=True)
    target_id = Column(String(36), nullable=True, index=True)
    correlation_id = Column(String(64), nullable=True, index=True)
    ip_address = Column(String(45), nullable=False, default="")
    details_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, index=True)


# ---------------------------------------------------------------------------
# Auth Persistence (Phase 3.2a)
# ---------------------------------------------------------------------------


class AdvertiserOrganization(Base):
    __tablename__ = "advertiser_organizations"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    code = Column(String(64), nullable=False, unique=True, index=True)
    legal_name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    memberships = relationship("AdvertiserUserMembership", back_populates="organization")


class AdvertiserUserMembership(Base):
    __tablename__ = "advertiser_user_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "advertiser_organization_id",
                         name="uq_adv_membership"),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    advertiser_organization_id = Column(
        String(36), ForeignKey("advertiser_organizations.id"), nullable=False, index=True,
    )
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    user = relationship("User", backref="advertiser_memberships")
    organization = relationship("AdvertiserOrganization", back_populates="memberships")


class AdvertiserBrand(Base):
    __tablename__ = "advertiser_brands"
    __table_args__ = (
        UniqueConstraint("advertiser_organization_id", "code",
                         name="uq_adv_brand_code_per_org"),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    advertiser_organization_id = Column(
        String(36), ForeignKey("advertiser_organizations.id"), nullable=False, index=True,
    )
    code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="draft")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class AdvertiserContract(Base):
    __tablename__ = "advertiser_contracts"
    __table_args__ = (
        UniqueConstraint("advertiser_organization_id", "code",
                         name="uq_adv_contract_code_per_org"),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    advertiser_organization_id = Column(
        String(36), ForeignKey("advertiser_organizations.id"), nullable=False, index=True,
    )
    code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    contract_number = Column(String(128), nullable=True)
    budget_limit_amount = Column(Numeric(18, 2), nullable=True)
    budget_limit_currency = Column(String(3), nullable=False, default="RUB")
    valid_from = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, default="draft")
    terms_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class AdvertiserContact(Base):
    __tablename__ = "advertiser_contacts"
    __table_args__ = (
        Index("ix_adv_contacts_primary",
              "advertiser_organization_id", "contact_type",
              unique=True,
              postgresql_where=text("is_primary IS TRUE AND status = 'active'")),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    advertiser_organization_id = Column(
        String(36), ForeignKey("advertiser_organizations.id"), nullable=False, index=True,
    )
    contact_type = Column(String(32), nullable=False, default="primary")
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(32), nullable=True)
    is_primary = Column(Boolean, nullable=False, default=False)
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


# ---------------------------------------------------------------------------
# Campaign Domain (Phase 4.1 — ADR-015)
# ---------------------------------------------------------------------------


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        UniqueConstraint("advertiser_organization_id", "code",
                         name="uq_campaign_code_per_org"),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    advertiser_organization_id = Column(
        String(36), ForeignKey("advertiser_organizations.id"), nullable=False, index=True,
    )
    advertiser_brand_id = Column(
        String(36), ForeignKey("advertiser_brands.id"), nullable=True,
    )
    advertiser_contract_id = Column(
        String(36), ForeignKey("advertiser_contracts.id"), nullable=False,
    )
    code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="draft")
    priority = Column(Integer, nullable=False, default=0)
    budget_limit_amount = Column(Numeric(18, 2), nullable=True)
    budget_limit_currency = Column(String(3), nullable=False, default="RUB")
    start_at = Column(DateTime(timezone=True), nullable=True)
    end_at = Column(DateTime(timezone=True), nullable=True)
    timezone = Column(String(64), nullable=False, default="Europe/Moscow")
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class CampaignFlight(Base):
    __tablename__ = "campaign_flights"
    __table_args__ = (
        CheckConstraint(
            "start_at < end_at",
            name="ck_cf_start_before_end",
        ),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    campaign_id = Column(
        String(36), ForeignKey("campaigns.id"), nullable=False, index=True,
    )
    name = Column(String(255), nullable=True)
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    dayparting_json = Column(JSONB, nullable=True)
    days_of_week = Column(ARRAY(Integer), nullable=True)
    priority = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class CampaignPlacement(Base):
    __tablename__ = "campaign_placements"
    __table_args__ = (
        CheckConstraint(
            "display_surface_id IS NOT NULL OR store_id IS NOT NULL "
            "OR cluster_id IS NOT NULL OR branch_id IS NOT NULL",
            name="ck_cp_at_least_one_target",
        ),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    campaign_id = Column(
        String(36), ForeignKey("campaigns.id"), nullable=False, index=True,
    )
    display_surface_id = Column(
        String(36), ForeignKey("display_surfaces.id"), nullable=True,
    )
    store_id = Column(
        String(36), ForeignKey("stores.id"), nullable=True,
    )
    cluster_id = Column(
        String(36), ForeignKey("clusters.id"), nullable=True,
    )
    branch_id = Column(
        String(36), ForeignKey("branches.id"), nullable=True,
    )
    share_of_voice_pct = Column(Integer, nullable=False, default=100)
    max_impressions = Column(BigInteger, nullable=True)
    impressions_delivered = Column(BigInteger, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class CreativeAsset(Base):
    __tablename__ = "creative_assets"
    __table_args__ = (
        UniqueConstraint("advertiser_organization_id", "code",
                         name="uq_creative_asset_code_per_org"),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    advertiser_organization_id = Column(
        String(36), ForeignKey("advertiser_organizations.id"), nullable=False, index=True,
    )
    code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    media_type = Column(String(32), nullable=False)
    storage_bucket = Column(String(128), nullable=False)
    storage_key = Column(String(512), nullable=False)
    sha256_checksum = Column(String(64), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    duration_ms = Column(Integer, nullable=True)
    resolution_w = Column(Integer, nullable=True)
    resolution_h = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, default="ready")
    moderation_status = Column(String(32), nullable=False, default="approved")
    moderation_notes = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class CampaignCreative(Base):
    __tablename__ = "campaign_creatives"
    __table_args__ = (
        UniqueConstraint("campaign_id", "creative_asset_id",
                         name="uq_campaign_creative"),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    campaign_id = Column(
        String(36), ForeignKey("campaigns.id"), nullable=False, index=True,
    )
    creative_asset_id = Column(
        String(36), ForeignKey("creative_assets.id"), nullable=False,
    )
    sort_order = Column(Integer, nullable=False, default=0)
    duration_override_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class CampaignApproval(Base):
    __tablename__ = "campaign_approvals"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    campaign_id = Column(
        String(36), ForeignKey("campaigns.id"), nullable=False, index=True,
    )
    requested_by = Column(
        String(36), ForeignKey("users.id"), nullable=False,
    )
    requested_at = Column(DateTime(timezone=True), nullable=False)
    reviewed_by = Column(
        String(36), ForeignKey("users.id"), nullable=True,
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    decision = Column(String(32), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class CampaignStatusHistory(Base):
    __tablename__ = "campaign_status_history"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    campaign_id = Column(
        String(36), ForeignKey("campaigns.id"), nullable=False, index=True,
    )
    old_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=False)
    changed_by = Column(
        String(36), ForeignKey("users.id"), nullable=False,
    )
    changed_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    reason = Column(Text, nullable=True)


class LocalCredential(Base):
    __tablename__ = "local_credentials"
    __table_args__ = (
        CheckConstraint(
            "credential_type IN ('local_advertiser', 'local_break_glass')",
            name="ck_lc_credential_type",
        ),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False,
                     unique=True, index=True)
    credential_type = Column(String(32), nullable=False)
    password_hash = Column(String(255), nullable=False, default="")
    password_hash_algorithm = Column(String(32), nullable=False, default="bcrypt")
    password_changed_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    must_change_password = Column(Boolean, nullable=False, default=False)
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(128), nullable=False, unique=True, index=True)
    token_family_id = Column(String(36), nullable=False, index=True)
    issued_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    rotated_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    username_or_email_hash = Column(String(128), nullable=False, index=True)
    auth_provider = Column(String(32), nullable=False, index=True)
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(64), nullable=True)
    ip_address = Column(String(45), nullable=True)
    correlation_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, index=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(128), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


# ---------------------------------------------------------------------------
# Transactional Outbox (Phase 4.1c — ADR-011)
# ---------------------------------------------------------------------------


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','publishing','published','failed','dead_letter')",
            name="ck_outbox_status",
        ),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    event_type = Column(String(128), nullable=False)
    event_version = Column(String(16), nullable=False, default="1.0")
    aggregate_type = Column(String(64), nullable=False)
    aggregate_id = Column(String(36), nullable=False)
    partition_key = Column(String(128), nullable=True)
    payload_json = Column(JSONB, nullable=False)
    headers_json = Column(JSONB, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    published_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


# ---------------------------------------------------------------------------
# Required Table Count
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Delivery Foundation (Phase 4.2b — ADR-016)
# ---------------------------------------------------------------------------
# Worker-owned tables.  No RLS — delivery workers need cross-tenant
# visibility to generate manifests for any campaign/device.  These tables
# are not exposed through user-facing API endpoints.


class DeliveryPlan(Base):
    __tablename__ = "delivery_plans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned','in_progress','completed','failed')",
            name="ck_dp_status",
        ),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    campaign_id = Column(
        String(36), ForeignKey("campaigns.id"), nullable=False, index=True,
    )
    campaign_version_hash = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False, default="planned")
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow,
                        onupdate=_utcnow)


class DeliveryManifest(Base):
    __tablename__ = "delivery_manifests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned','generated','delivered','failed','revoked')",
            name="ck_dm_status",
        ),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    manifest_id = Column(String(128), nullable=False, unique=True, index=True)
    campaign_id = Column(
        String(36), ForeignKey("campaigns.id"), nullable=False, index=True,
    )
    physical_device_id = Column(
        String(36), ForeignKey("physical_devices.id"), nullable=False, index=True,
    )
    content_hash = Column(String(128), nullable=False)
    manifest_version = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="planned")
    generated_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class DeliveryManifestSurface(Base):
    __tablename__ = "delivery_manifest_surfaces"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    manifest_id = Column(
        String(36), ForeignKey("delivery_manifests.id"), nullable=False, index=True,
    )
    display_surface_id = Column(
        String(36), ForeignKey("display_surfaces.id"), nullable=False, index=True,
    )
    slot_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class DeliveryManifestAsset(Base):
    __tablename__ = "delivery_manifest_assets"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    manifest_id = Column(
        String(36), ForeignKey("delivery_manifests.id"), nullable=False, index=True,
    )
    creative_asset_id = Column(
        String(36), ForeignKey("creative_assets.id"), nullable=False, index=True,
    )
    sha256_checksum = Column(String(64), nullable=False)
    duration_ms = Column(Integer, nullable=True)
    media_type = Column(String(32), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','delivered','failed')",
            name="ck_da_status",
        ),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    manifest_id = Column(
        String(36), ForeignKey("delivery_manifests.id"), nullable=False, index=True,
    )
    status = Column(String(32), nullable=False, default="pending")
    attempted_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


REQUIRED_TABLES = frozenset({
    "branches", "clusters", "stores",
    "channels", "device_types", "capability_profiles",
    "physical_devices", "device_certificates", "device_status_history",
    "logical_carriers", "display_surfaces",
    "users", "roles", "permissions", "role_permissions", "user_roles",
    "access_scopes", "user_access_scopes", "audit_events_operational",
    "advertiser_organizations", "advertiser_user_memberships",
    "advertiser_brands", "advertiser_contracts", "advertiser_contacts",
    "local_credentials", "refresh_sessions",
    "login_attempts", "password_reset_tokens",
    "campaigns", "campaign_flights", "campaign_placements",
    "creative_assets", "campaign_creatives",
    "campaign_approvals", "campaign_status_history",
    "outbox_events",
    "delivery_plans", "delivery_manifests",
    "delivery_manifest_surfaces", "delivery_manifest_assets",
    "delivery_attempts",
})
