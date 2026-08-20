"""
EPIC-L — Licensing read model (Layer 1).

Separate licensing boundary. This module reads the device/enrollment domain
(PhysicalDevice) via LicenseSeat, and NEVER queries commerce_* or
advertiser-commercial tables.

Contract (design freeze):
- These functions do NOT set RLS GUCs (app.rmp_*) themselves. The RLS context
  is applied at the API/service boundary (A2/A4). Under retail_media_app
  (NOBYPASSRLS) they return correct results ONLY when the caller has already
  set app.rmp_is_admin=true on the transaction — the DB RLS policy does the
  enforcement.
- Effective lifetime (active/grace/expired) is COMPUTED from dates, not read
  from a stored status. 'revoked' is an explicit stored state.
- Occupied seats count only OPEN seats (released_at IS NULL) whose
  physical_devices.status = 'active'.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.domain.licensing import LicenseGrant, LicenseSeat
from packages.domain.models import PhysicalDevice

# Effective license state strings (computed).
ACTIVE = "active"
GRACE = "grace"
EXPIRED = "expired"
REVOKED = "revoked"
MISSING = "missing"


async def get_effective_license(session: AsyncSession) -> LicenseGrant | None:
    """Return the single effective grant, or None.

    The effective grant is the 'current' grant if one exists, otherwise the
    most recent 'revoked' grant (a revoked license still blocks enrollment and
    must be reported as REVOKED, not MISSING). 'superseded' grants are history
    and never effective. The partial unique index (uq_license_grants_single_
    current) guarantees at most one 'current' row; in Layer 1 there is a single
    grant row, so ``order_by(issued_at).limit(1)`` is unambiguous.

    If the RLS context is not admin, the DB policy hides the row and this
    returns None (same as a missing license under app role without
    service/admin context).
    """
    result = await session.execute(
        select(LicenseGrant)
        .where(LicenseGrant.status.in_(["current", "revoked"]))
        .order_by(LicenseGrant.issued_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def compute_effective_state(
    grant: LicenseGrant | None,
    now: datetime | None = None,
) -> str:
    """Compute active/grace/expired/revoked/missing from dates, not status.

    - missing  → no grant at all
    - revoked  → explicit stored state (wins over any date window)
    - active   → now within [valid_from, valid_until) or perpetual (no end)
    - grace    → now within [valid_until, valid_until + grace_days)
    - expired  → now >= valid_until + grace_days

    `now` defaults to UTC now. All comparisons are timezone-aware.
    """
    if grant is None:
        return MISSING
    if grant.status == "revoked":
        return REVOKED

    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if now < grant.valid_from:
        # Not yet started — treat as active window not reached. Per design
        # freeze there is no separate 'future' state; a license that has not
        # begun is effectively not active yet, but Layer 1 dev-ingest always
        # sets valid_from in the past, so this branch is defensive.
        return EXPIRED

    if grant.valid_until is None:
        return ACTIVE  # perpetual

    if now < grant.valid_until:
        return ACTIVE

    if now < grant.valid_until + timedelta(days=grant.grace_days):
        return GRACE

    return EXPIRED


async def count_occupied_seats(session: AsyncSession) -> int:
    """Count open seats whose device is still active.

    Only seats with released_at IS NULL AND the joined physical_devices.status
    = 'active' are counted. Released seats and seats on inactive/decommissioned
    devices are excluded.
    """
    result = await session.execute(
        select(LicenseSeat.id)
        .join(PhysicalDevice, LicenseSeat.device_id == PhysicalDevice.id)
        .where(LicenseSeat.released_at.is_(None))
        .where(PhysicalDevice.status == "active")
    )
    return len(result.scalars().all())


def capacity_of(grant: LicenseGrant) -> int:
    """Effective capacity = max_devices + overage_allowance."""
    return grant.max_devices + grant.overage_allowance


def free_of(capacity: int, occupied: int) -> int:
    """Free seats = max(capacity - occupied, 0)."""
    return max(capacity - occupied, 0)
