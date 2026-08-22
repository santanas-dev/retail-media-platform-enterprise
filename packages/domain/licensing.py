"""
EPIC-L — Platform/Device Licensing ORM models (Layer 1, seat ledger).

Separate licensing boundary: these models depend only on the device/enrollment
domain (PhysicalDevice), never on commerce_* or advertiser-commercial tables.

Design freeze is authoritative:
docs/architecture/epic-l-licensing.md §"Layer 1 Seat Ledger Design Freeze".

- LicenseGrant: installation-level grant. Exactly one `status='current'`
  (enforced by partial unique index in migration 034). Lifetime active/grace/
  expired is COMPUTED from valid_from/valid_until/grace_days — never stored.
- LicenseSeat: per-device seat reservation interval. At most one open seat
  (released_at IS NULL) per device (partial unique index). Historical
  reserve/release intervals are preserved.

The app role (retail_media_app, NOBYPASSRLS) can only read/write these rows
when the server has set app.rmp_is_admin=true on the transaction. These models
do NOT set GUCs themselves — the RLS context is applied at the API/service
boundary (A2/A4), not here.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from packages.domain.models import Base, _new_uuid, _utcnow


class LicenseGrant(Base):
    """A single installation license grant."""

    __tablename__ = "license_grants"
    __table_args__ = (
        CheckConstraint("max_devices >= 0", name="ck_license_grants_max_devices_nonneg"),
        CheckConstraint("overage_allowance >= 0", name="ck_license_grants_overage_nonneg"),
        CheckConstraint("grace_days >= 0", name="ck_license_grants_grace_nonneg"),
        CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_license_grants_valid_window",
        ),
        CheckConstraint("source IN ('dev-ingest')", name="ck_license_grants_source_layer1"),
        CheckConstraint(
            "status IN ('current', 'revoked', 'superseded')",
            name="ck_license_grants_status",
        ),
        Index("ix_license_grants_status", "status"),
        Index("ix_license_grants_licensee", "licensee_id"),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    license_id = Column(String(128), nullable=False, unique=True)
    licensee_id = Column(String(128), nullable=False)
    licensee_name = Column(String(255), nullable=False)
    tier = Column(String(64), nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False)
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    max_devices = Column(Integer, nullable=False, default=0)
    overage_allowance = Column(Integer, nullable=False, default=0)
    grace_days = Column(Integer, nullable=False, default=0)
    features = Column(JSONB, nullable=True)
    installation_binding = Column(String(255), nullable=True)
    nonce = Column(String(255), nullable=True)
    schema_version = Column(Integer, nullable=False, default=1)
    kid = Column(String(255), nullable=True)
    source = Column(String(32), nullable=False, default="dev-ingest")
    status = Column(String(32), nullable=False, default="current")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    seats = relationship("LicenseSeat", back_populates="grant")


class LicenseSeat(Base):
    """A per-device license seat reservation interval."""

    __tablename__ = "license_seats"
    __table_args__ = (
        CheckConstraint(
            "released_at IS NULL OR released_at >= reserved_at",
            name="ck_license_seats_release_after_reserve",
        ),
        Index("ix_license_seats_license", "license_id"),
        Index("ix_license_seats_device", "device_id"),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    license_id = Column(
        String(36), ForeignKey("license_grants.id", ondelete="RESTRICT"), nullable=False,
    )
    device_id = Column(
        String(36), ForeignKey("physical_devices.id", ondelete="RESTRICT"), nullable=False,
    )
    reserved_at = Column(DateTime(timezone=True), nullable=False)
    released_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    grant = relationship("LicenseGrant", back_populates="seats")
    device = relationship("PhysicalDevice")
