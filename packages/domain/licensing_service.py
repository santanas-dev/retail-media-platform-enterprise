"""
EPIC-L — Licensing enrollment choke-point (Layer 1, task 001A2).

Single transactional boundary between new device enrollment and the seat
ledger. The device_onboard route calls exactly ONE method here
(:func:`authorize_and_reserve_enrollment`) — there are no scattered license
checks in the route or in ``repository.py``.

Design freeze is authoritative:
docs/architecture/epic-l-licensing.md §"Layer 1 Seat Ledger Design Freeze".

Contract:
- The RLS context (``app.rmp_is_admin``) is set by THIS server code, never by
  a client parameter. The onboarding endpoint is unauthenticated (device_code),
  so the choke-point deliberately elevates to service/admin context for the
  single transaction to read the license grant + seat ledger.
- The effective grant is read with ``SELECT ... FOR UPDATE`` so concurrent
  enrollments for the same installation serialize on one grant row. A bare
  ``COUNT(*)`` before INSERT is NOT used as the capacity guarantee.
- On any denial the caller aborts the transaction; the route reverts the
  onboarding-code claim and returns HTTP 409 (see SCOPE C of the task).
- Effective state (active/grace/expired/revoked/missing) is computed from
  dates via the A1 read model — never from a stored mutable status.
- Soft enforcement: denial only blocks NEW enrollment. It never changes the
  status of already-active devices, releases their seats, or touches
  heartbeat/device-auth/player/manifest/PoP paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Awaitable, Callable

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from packages.domain.licensing import LicenseGrant, LicenseSeat
from packages.domain.licensing_repository import (
    ACTIVE,
    EXPIRED,
    GRACE,
    MISSING,
    REVOKED,
    capacity_of,
    compute_effective_state,
    count_occupied_seats,
    effective_grant_query,
    free_of,
)
from packages.domain.models import PhysicalDevice

# Stable denial codes (SCOPE C). These are the ONLY codes this layer emits.
DENIAL_MESSAGES = {
    "LICENSE_MISSING": "Лицензия не найдена. Обратитесь к оператору платформы.",
    "LICENSE_REVOKED": "Лицензия отозвана. Обратитесь к оператору платформы.",
    "LICENSE_EXPIRED": "Срок действия лицензии истёк. Обратитесь к оператору платформы.",
}

# Effective state → denial code mapping (missing/revoked/expired only; grace is
# allowed, active is allowed).
_STATE_DENIAL_CODE = {
    MISSING: "LICENSE_MISSING",
    REVOKED: "LICENSE_REVOKED",
    EXPIRED: "LICENSE_EXPIRED",
}


@dataclass
class EnrollmentDecision:
    """Result of the enrollment choke-point.

    ``allowed=False`` carries a stable ``code`` + Russian ``message`` for the
    route to surface as HTTP 409. ``allowed=True`` carries the created device
    and reserved seat; ``state``/``in_grace`` reflect the computed effective
    state so grace can be surfaced in the success response/audit.
    """

    allowed: bool
    code: str | None = None
    message: str | None = None
    state: str | None = None
    in_grace: bool = False
    grant: "LicenseGrant | None" = None
    device: "PhysicalDevice | None" = None
    seat: "LicenseSeat | None" = None
    capacity: int = 0
    occupied: int = 0
    free: int = 0

    @classmethod
    def denied(cls, code: str, *, state: str | None, capacity: int = 0,
               occupied: int = 0) -> "EnrollmentDecision":
        msg = DENIAL_MESSAGES.get(code, "Регистрация устройства отклонена.")
        return cls(
            allowed=False,
            code=code,
            message=msg,
            state=state,
            capacity=capacity,
            occupied=occupied,
            free=free_of(capacity, occupied),
        )

    @classmethod
    def seat_limit(cls, *, state: str, capacity: int, occupied: int) -> "EnrollmentDecision":
        return cls(
            allowed=False,
            code="LICENSE_SEAT_LIMIT",
            message=(
                f"Достигнут лимит {capacity} устройств. "
                "Обратитесь к оператору платформы."
            ),
            state=state,
            capacity=capacity,
            occupied=occupied,
            free=0,
        )


@dataclass
class ReconciliationResult:
    """Result of the grandfather reconciliation pass."""

    scanned_active: int
    created_seats: int
    overage: bool = False


async def set_licensing_admin_context(session: AsyncSession) -> None:
    """Set the transaction-local service/admin RLS context (server-set).

    This is the sanctioned elevation for the licensing choke-point: the
    license tables are operator/service scope (RLS = app.rmp_is_admin), and the
    onboarding endpoint is unauthenticated. The context is transaction-local
    (``set_config(..., true)``) and dies with the transaction.
    """
    await session.execute(
        text("SELECT set_config('app.rmp_is_admin', 'true', true)")
    )


async def lock_current_grant(session: AsyncSession) -> "LicenseGrant | None":
    """Return the single effective grant, locked with ``SELECT ... FOR UPDATE``.

    Priority is status-based (see
    :func:`licensing_repository.effective_grant_query`): the 'current' grant
    outranks any 'revoked' grant regardless of ``issued_at``; 'revoked' is
    chosen only when no 'current' exists. All enrollments for this installation
    serialize on this one row. Under NOBYPASSRLS the caller must already have
    set the admin context (the RLS policy admits the SELECT and the row lock is
    held until commit/rollback).
    """
    result = await session.execute(effective_grant_query(lock=True))
    return result.scalar_one_or_none()


async def reserve_seat(
    session: AsyncSession,
    *,
    grant_id: str,
    device_id: str,
    now: datetime,
) -> "LicenseSeat":
    """Reserve an open seat for a device inside the current transaction.

    ``grant_id`` is the internal ``license_grants.id`` (the FK target), NOT the
    business ``license_id`` string. The partial unique index
    ``uq_license_seats_open_per_device`` rejects a second open seat for the
    same device; a unique violation rolls the whole transaction back.
    """
    seat = LicenseSeat(
        license_id=grant_id,
        device_id=device_id,
        reserved_at=now,
    )
    session.add(seat)
    await session.flush()
    return seat


async def authorize_and_reserve_enrollment(
    session: AsyncSession,
    *,
    create_device: Callable[[], Awaitable["PhysicalDevice"]],
    now: datetime,
) -> EnrollmentDecision:
    """Single enrollment choke-point.

    In one DB transaction this:
      1. sets the transaction-local service/admin RLS context (server-set),
      2. locks the single current grant with SELECT ... FOR UPDATE,
      3. computes the effective state (active/grace/expired/revoked/missing),
      4. counts occupied seats (open seats on active devices) post-lock,
      5. enforces capacity (occupied < max_devices + overage_allowance),
      6. mints the device via the injected ``create_device`` factory,
      7. reserves a seat for the device.

    Any denial returns ``EnrollmentDecision(allowed=False)`` with the stable
    code + Russian message; the caller aborts the transaction. Device creation
    is injected so the route keeps ``repository.create_physical_device_onboard``
    as the single source of device-minting truth.
    """
    # 1. Server-set RLS context — not from client parameters.
    await set_licensing_admin_context(session)

    # 2. Row lock: serialize all enrollments for this installation.
    grant = await lock_current_grant(session)

    # 3. Effective state from dates, not status.
    state = compute_effective_state(grant, now)

    denial_code = _STATE_DENIAL_CODE.get(state)
    if denial_code is not None:
        return EnrollmentDecision.denied(denial_code, state=state)

    # grant is guaranteed non-None here: MISSING is the only state produced by
    # a None grant, and it was already denied above.
    assert grant is not None
    in_grace = state == GRACE

    # 4. Occupied seats (post-lock).
    occupied = await count_occupied_seats(session)
    capacity = capacity_of(grant)  # grant is non-None here (state is active/grace)

    # 5. Capacity check.
    if occupied >= capacity:
        return EnrollmentDecision.seat_limit(
            state=state, capacity=capacity, occupied=occupied,
        )

    # 6. Mint device (in the same transaction).
    device = await create_device()
    await session.flush()

    # 7. Reserve the seat.
    seat = await reserve_seat(
        session, grant_id=grant.id, device_id=device.id, now=now,
    )

    return EnrollmentDecision(
        allowed=True,
        state=state,
        in_grace=in_grace,
        grant=grant,
        device=device,
        seat=seat,
        capacity=capacity,
        occupied=occupied + 1,
        free=free_of(capacity, occupied + 1),
    )


async def reconcile_existing_fleet(
    session: AsyncSession,
    *,
    now: datetime,
) -> ReconciliationResult:
    """Grandfather existing active devices (SCOPE B #3).

    Idempotently creates one open seat for every ``physical_devices`` row whose
    status is 'active' and that has no open seat yet. Existing active devices
    are seated even if the fleet already exceeds the current capacity (that
    state is reported as overage and only blocks NEW enrollment). Inactive /
    unregistered devices are never seated. Re-running creates no duplicates
    (the partial unique index plus the outer-join filter are both idempotent).
    """
    await set_licensing_admin_context(session)

    grant = await lock_current_grant(session)
    if grant is None:
        return ReconciliationResult(scanned_active=0, created_seats=0)

    missing = await session.execute(
        select(PhysicalDevice.id)
        .outerjoin(
            LicenseSeat,
            (LicenseSeat.device_id == PhysicalDevice.id)
            & (LicenseSeat.released_at.is_(None)),
        )
        .where(PhysicalDevice.status == "active")
        .where(LicenseSeat.id.is_(None))
    )
    device_ids = list(missing.scalars().all())

    created = 0
    for device_id in device_ids:
        session.add(LicenseSeat(
            license_id=grant.id,
            device_id=device_id,
            reserved_at=now,
        ))
        created += 1
    await session.flush()

    occupied = await count_occupied_seats(session)
    return ReconciliationResult(
        scanned_active=len(device_ids),
        created_seats=created,
        overage=occupied > capacity_of(grant),
    )
