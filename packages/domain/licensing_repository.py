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

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.domain.licensing import LicenseGrant, LicenseSeat
from packages.domain.models import PhysicalDevice, Store

# Effective license state strings (computed).
ACTIVE = "active"
GRACE = "grace"
EXPIRED = "expired"
REVOKED = "revoked"
MISSING = "missing"


def effective_grant_query(lock: bool = False):
    """Build the single effective-grant query.

    The effective grant is **status-prioritized**: the 'current' grant always
    outranks any 'revoked' grant, regardless of ``issued_at``. Only when no
    'current' row exists is the most recent 'revoked' grant chosen (a revoked
    license still blocks enrollment and must be reported as REVOKED, not
    MISSING). 'superseded' grants are history and never effective.

    ``issued_at DESC`` breaks ties only WITHIN the same status. When ``lock``
    is True the selected row is locked with ``SELECT ... FOR UPDATE`` so that
    concurrent enrollments serialize on it. This is the single source of truth
    for effective-grant selection — the read model
    (:func:`get_effective_license`) and the enrollment choke-point
    (``licensing_service.lock_current_grant``) both delegate here so the two
    can never diverge again.
    """
    stmt = (
        select(LicenseGrant)
        .where(LicenseGrant.status.in_(["current", "revoked"]))
        .order_by(
            case((LicenseGrant.status == "current", 0), else_=1),
            LicenseGrant.issued_at.desc(),
        )
        .limit(1)
    )
    if lock:
        stmt = stmt.with_for_update()
    return stmt


async def get_effective_license(session: AsyncSession) -> LicenseGrant | None:
    """Return the single effective grant, or None.

    Priority is status-based (see :func:`effective_grant_query`): 'current'
    outranks 'revoked' regardless of ``issued_at``; 'revoked' is chosen only
    when no 'current' exists. 'superseded' grants are history and never
    effective. The partial unique index (uq_license_grants_single_current)
    guarantees at most one 'current' row.

    If the RLS context is not admin, the DB policy hides the row and this
    returns None (same as a missing license under app role without
    service/admin context).
    """
    result = await session.execute(effective_grant_query(lock=False))
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


# ---------------------------------------------------------------------------
# Exact monthly peak (SCOPE D — 001A3)
# ---------------------------------------------------------------------------


def _month_bounds(
    year: int,
    month: int,
    tz: timezone = timezone.utc,
) -> tuple[datetime, datetime]:
    """Validate and return the half-open calendar-month window.

    Returns ``(month_start, next_month_start)`` where the month is
    ``[month_start, next_month_start)``. Raises ``ValueError`` with a clear
    message for an invalid ``year``/``month`` so the caller can surface a
    controlled validation error (never a raw ``ValueError`` from
    ``datetime(…)``).
    """
    if not isinstance(year, int) or isinstance(year, bool) or not 1 <= year <= 9999:
        raise ValueError(f"year must be an integer in 1..9999, got {year!r}")
    if not isinstance(month, int) or isinstance(month, bool) or not 1 <= month <= 12:
        raise ValueError(f"month must be an integer in 1..12, got {month!r}")

    month_start = datetime(year, month, 1, tzinfo=tz)
    if month == 12:
        next_month_start = datetime(year + 1, 1, 1, tzinfo=tz)
    else:
        next_month_start = datetime(year, month + 1, 1, tzinfo=tz)
    return month_start, next_month_start


def _peak_from_intervals(
    intervals: list[tuple[datetime, datetime | None]],
    month_start: datetime,
    next_month_start: datetime,
) -> int:
    """Exact maximum of concurrently open seat intervals over a month window.

    Canonical half-open policy (design freeze §6):
    - seat interval is ``[reserved_at, released_at)``; an open seat
      (``released_at is None``) is treated as occupied through
      ``next_month_start``;
    - ``released_at == month_start`` is NOT included;
    - ``reserved_at == next_month_start`` is NOT included;
    - an interval that began before the month and is still open at
      ``month_start`` is counted from ``month_start``;
    - events sharing the same timestamp are grouped with ends before starts,
      so a release+reserve at one instant never fabricates a false peak.

    The result is the maximum number of simultaneously open intervals — not a
    current count and not a daily snapshot.
    """
    events: list[tuple[datetime, int]] = []
    for reserved_at, released_at in intervals:
        s = reserved_at
        e = released_at if released_at is not None else next_month_start
        if s < month_start:
            s = month_start
        if e > next_month_start:
            e = next_month_start
        if s >= e:
            continue  # zero-length or entirely outside the month
        events.append((s, +1))
        events.append((e, -1))

    # Same-timestamp grouping: a release (-1) sorts before a reserve (+1), so
    # a seat handed from one device to another at the same instant is counted
    # once, not twice.
    events.sort(key=lambda ev: (ev[0], ev[1]))

    current = 0
    peak = 0
    for _ts, delta in events:
        current += delta
        if current > peak:
            peak = current
    return peak


async def peak_seats_for_month(
    session: AsyncSession,
    *,
    license_id: str,
    year: int,
    month: int,
    timezone: timezone = timezone.utc,
) -> int:
    """Exact maximum of concurrently open seats for ``license_id`` in a month.

    ``license_id`` is the internal ``license_grants.id`` (the FK target of
    ``license_seats.license_id``), NOT the business ``license_id`` string.

    The query is restricted to ``license_id`` and to intervals that overlap the
    month (``reserved_at < next_month_start AND (released_at IS NULL OR
    released_at > month_start)``) — it never loads the whole seat history of
    every license. The peak is computed from those intervals via
    :func:`_peak_from_intervals`.

    Under NOBYPASSRLS the caller must already have set the service/admin RLS
    context (the DB RLS policy on ``license_seats`` enforces it) — this
    function does not set GUCs.
    """
    month_start, next_month_start = _month_bounds(year, month, timezone)

    result = await session.execute(
        select(LicenseSeat.reserved_at, LicenseSeat.released_at)
        .where(LicenseSeat.license_id == license_id)
        .where(LicenseSeat.reserved_at < next_month_start)
        .where(or_(LicenseSeat.released_at.is_(None), LicenseSeat.released_at > month_start))
    )
    intervals = [(r, e) for r, e in result.all()]
    return _peak_from_intervals(intervals, month_start, next_month_start)


# ---------------------------------------------------------------------------
# License report read model (SCOPE B — 001A4)
# ---------------------------------------------------------------------------


@dataclass
class LicenseReportLicense:
    """License section of the report (single effective grant)."""

    effective_state: str  # active/grace/expired/revoked/missing
    license_id: str | None = None
    licensee_id: str | None = None
    licensee_name: str | None = None
    tier: str | None = None
    source: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    grace_days: int = 0
    capacity: int = 0
    days_remaining: int | None = None
    over_capacity_by: int = 0


@dataclass
class LicenseReportUsage:
    """Usage section: occupancy + exact monthly peak."""

    occupied: int = 0
    free: int = 0
    peak: int = 0
    year: int = 0
    month: int = 0
    timezone: str = "UTC"


@dataclass
class LicenseReportSeat:
    """A single currently-open seat with its device + authoritative store."""

    seat_id: str
    license_id: str
    device_id: str
    device_code: str
    device_status: str
    reserved_at: datetime
    last_heartbeat_at: datetime | None = None
    store_id: str | None = None
    store_code: str | None = None
    store_name: str | None = None
    anomaly_flags: list[str] = field(default_factory=list)


@dataclass
class LicenseReport:
    """Read-only license report (no mutation, no secrets)."""

    license: LicenseReportLicense
    usage: LicenseReportUsage
    seats: list[LicenseReportSeat] = field(default_factory=list)


def _days_remaining(
    state: str,
    grant: "LicenseGrant | None",
    now: datetime,
) -> int | None:
    """UTC ceil days until the effective window ends.

    - active → ceil to ``valid_until``;
    - grace  → ceil to ``valid_until + grace_days``;
    - expired/revoked → 0;
    - perpetual (no ``valid_until``) / missing → None.
    """
    if state == MISSING:
        return None
    if state in (EXPIRED, REVOKED):
        return 0
    if grant is None or grant.valid_until is None:
        return None  # perpetual / defensive
    deadline = grant.valid_until if state == ACTIVE else grant.valid_until + timedelta(days=grant.grace_days)
    seconds = (deadline - now).total_seconds()
    if seconds <= 0:
        return 0
    return math.ceil(seconds / 86400)


async def _load_open_seats(
    session: AsyncSession,
    *,
    current_grant_id: str | None,
) -> list[LicenseReportSeat]:
    """Load currently-open seats joined to device + authoritative store.

    Store fields come only from ``physical_devices.store_id → stores`` (the
    authoritative device/inventory identity relation) — never advertiser or
    commerce tables.
    """
    result = await session.execute(
        select(LicenseSeat, PhysicalDevice, Store)
        .join(PhysicalDevice, LicenseSeat.device_id == PhysicalDevice.id)
        .outerjoin(Store, PhysicalDevice.store_id == Store.id)
        .where(LicenseSeat.released_at.is_(None))
    )

    seats: list[LicenseReportSeat] = []
    for seat, device, store in result.all():
        flags: list[str] = []
        if device.status != "active":
            flags.append("device_not_active")
        if current_grant_id is not None and seat.license_id != current_grant_id:
            flags.append("seat_under_noncurrent_grant")
        seats.append(LicenseReportSeat(
            seat_id=seat.id,
            license_id=seat.license_id,
            device_id=device.id,
            device_code=device.code,
            device_status=device.status,
            reserved_at=seat.reserved_at,
            last_heartbeat_at=device.last_heartbeat_at,
            store_id=store.id if store else None,
            store_code=store.code if store else None,
            store_name=store.name if store else None,
            anomaly_flags=flags,
        ))
    return seats


async def get_license_report(
    session: AsyncSession,
    *,
    year: int,
    month: int,
    now: datetime,
) -> LicenseReport:
    """Single read-only license report (license + usage + open seats).

    Never sets RLS GUCs — the caller (report route / service boundary) must
    already have applied the service/admin context. Reads only license tables,
    ``physical_devices`` and ``stores`` (device/inventory identity) — never
    ``commerce_*`` or advertiser-commercial tables. Missing license produces a
    controlled ``effective_state="missing"`` report, not a 500 and not a
    fabricated grant.
    """
    grant = await get_effective_license(session)
    state = compute_effective_state(grant, now)

    occupied = await count_occupied_seats(session)
    capacity = capacity_of(grant) if grant is not None else 0
    free = max(capacity - occupied, 0)
    over_capacity_by = max(occupied - capacity, 0)

    peak = 0
    if grant is not None:
        peak = await peak_seats_for_month(
            session, license_id=grant.id, year=year, month=month,
        )

    seats = await _load_open_seats(
        session, current_grant_id=grant.id if grant is not None else None,
    )

    license_section = LicenseReportLicense(
        effective_state=state,
        license_id=grant.license_id if grant is not None else None,
        licensee_id=grant.licensee_id if grant is not None else None,
        licensee_name=grant.licensee_name if grant is not None else None,
        tier=grant.tier if grant is not None else None,
        source=grant.source if grant is not None else None,
        valid_from=grant.valid_from if grant is not None else None,
        valid_until=grant.valid_until if grant is not None else None,
        grace_days=grant.grace_days if grant is not None else 0,
        capacity=capacity,
        days_remaining=_days_remaining(state, grant, now),
        over_capacity_by=over_capacity_by,
    )

    return LicenseReport(
        license=license_section,
        usage=LicenseReportUsage(
            occupied=occupied,
            free=free,
            peak=peak,
            year=year,
            month=month,
            timezone="UTC",
        ),
        seats=seats,
    )
