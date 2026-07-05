"""
Retail Media Platform — Async Repository Helpers.

Phase 3.0: Read-only query functions for identity/RBAC tables.
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from packages.domain.models import (
    AdvertiserBrand,
    AdvertiserContact,
    AdvertiserContract,
    AdvertiserOrganization,
    AuditEventOperational,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)


async def list_users(
    session: AsyncSession,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[User], int]:
    """Return paginated users and total count."""
    total = await session.scalar(select(func.count()).select_from(User))
    stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all()), total or 0


async def list_roles(session: AsyncSession) -> list[Role]:
    """Return all roles, ordered by code."""
    stmt = select(Role).order_by(Role.code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_permissions(session: AsyncSession) -> list[Permission]:
    """Return all permissions, ordered by code."""
    stmt = select(Permission).order_by(Permission.code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_audit_events(
    session: AsyncSession,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[AuditEventOperational], int]:
    """Return paginated audit events (newest first) and total count."""
    total = await session.scalar(
        select(func.count()).select_from(AuditEventOperational)
    )
    stmt = (
        select(AuditEventOperational)
        .order_by(AuditEventOperational.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all()), total or 0


# ---------------------------------------------------------------------------
# Authz (Phase 3.3) — permission lookups for RBAC enforcement
# ---------------------------------------------------------------------------


async def find_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    """Find user by primary key."""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_permissions(
    session: AsyncSession, user_id: str
) -> set[str]:
    """Return the set of permission codes granted to a user via their roles.

    Joins: UserRole → RolePermission → Permission.
    Only considers unscoped (global) role assignments — tenant RLS deferred.
    """
    stmt = (
        select(Permission.code)
        .select_from(UserRole)
        .join(RolePermission, RolePermission.role_id == UserRole.role_id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(
            UserRole.user_id == user_id,
            UserRole.scope_type.is_(None),  # global assignments only
        )
        .distinct()
    )
    result = await session.execute(stmt)
    return {row[0] for row in result}


async def list_advertiser_organizations(
    session: AsyncSession,
) -> list[AdvertiserOrganization]:
    """Return all advertiser organizations, ordered by code."""
    stmt = select(AdvertiserOrganization).order_by(AdvertiserOrganization.code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_advertiser_brands(
    session: AsyncSession,
) -> list[AdvertiserBrand]:
    """Return all advertiser brands, ordered by code."""
    stmt = select(AdvertiserBrand).order_by(AdvertiserBrand.code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_advertiser_contracts(
    session: AsyncSession,
) -> list[AdvertiserContract]:
    """Return all advertiser contracts, ordered by code."""
    stmt = select(AdvertiserContract).order_by(AdvertiserContract.code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_advertiser_contacts(
    session: AsyncSession,
) -> list[AdvertiserContact]:
    """Return all advertiser contacts, ordered by contact_type + full_name."""
    stmt = select(AdvertiserContact).order_by(
        AdvertiserContact.contact_type, AdvertiserContact.full_name,
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Campaign Domain (Phase 4.1b — ADR-015)
# ---------------------------------------------------------------------------


async def list_campaigns(session: AsyncSession) -> list:
    """Return all campaigns, ordered by code."""
    from packages.domain.models import Campaign
    stmt = select(Campaign).order_by(Campaign.code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_campaign(
    session: AsyncSession,
    campaign_id: str,
):
    """Get a single campaign by id. Returns Campaign or None."""
    from packages.domain.models import Campaign
    result = await session.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    return result.scalar_one_or_none()


async def list_campaign_flights(session: AsyncSession) -> list:
    """Return all campaign flights, ordered by campaign_id + start_at."""
    from packages.domain.models import CampaignFlight
    stmt = select(CampaignFlight).order_by(
        CampaignFlight.campaign_id, CampaignFlight.start_at,
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_campaign_creatives(session: AsyncSession) -> list:
    """Return all campaign-creative links, ordered by campaign_id + sort_order."""
    from packages.domain.models import CampaignCreative
    stmt = select(CampaignCreative).order_by(
        CampaignCreative.campaign_id, CampaignCreative.sort_order,
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_creative_assets(session: AsyncSession) -> list:
    """Return all creative assets (metadata only), ordered by code."""
    from packages.domain.models import CreativeAsset
    stmt = select(CreativeAsset).order_by(CreativeAsset.code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_campaign_placements(session: AsyncSession) -> list:
    """Return all campaign placements, ordered by campaign_id."""
    from packages.domain.models import CampaignPlacement
    stmt = select(CampaignPlacement).order_by(CampaignPlacement.campaign_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_campaign_approvals(session: AsyncSession) -> list:
    """Return all campaign approvals, ordered by campaign_id + requested_at."""
    from packages.domain.models import CampaignApproval
    stmt = select(CampaignApproval).order_by(
        CampaignApproval.campaign_id, CampaignApproval.requested_at,
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_campaign_status_history(session: AsyncSession) -> list:
    """Return all campaign status history, ordered by campaign_id + changed_at."""
    from packages.domain.models import CampaignStatusHistory
    stmt = select(CampaignStatusHistory).order_by(
        CampaignStatusHistory.campaign_id, CampaignStatusHistory.changed_at,
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Campaign Mutations (Phase 4.1c — ADR-015)
# ---------------------------------------------------------------------------


async def _validate_contract_belongs_to_org(
    session: AsyncSession,
    contract_id: str,
    advertiser_organization_id: str,
) -> None:
    """Raise CrossOrgReferenceError if contract doesn't belong to the org.

    Does NOT distinguish between "not found" and "wrong org" —
    both return the same generic error to avoid existence oracle.
    """
    from packages.domain.models import AdvertiserContract
    from packages.domain.exceptions import CrossOrgReferenceError

    stmt = select(AdvertiserContract).where(
        AdvertiserContract.id == contract_id,
    )
    result = await session.execute(stmt)
    contract = result.scalar_one_or_none()
    if contract is None or contract.advertiser_organization_id != advertiser_organization_id:
        raise CrossOrgReferenceError("Invalid advertiser contract reference")


async def _validate_brand_belongs_to_org(
    session: AsyncSession,
    brand_id: str,
    advertiser_organization_id: str,
) -> None:
    """Raise CrossOrgReferenceError if brand doesn't belong to the org.

    Does NOT distinguish between "not found" and "wrong org" —
    both return the same generic error to avoid existence oracle.
    """
    from packages.domain.models import AdvertiserBrand
    from packages.domain.exceptions import CrossOrgReferenceError

    stmt = select(AdvertiserBrand).where(AdvertiserBrand.id == brand_id)
    result = await session.execute(stmt)
    brand = result.scalar_one_or_none()
    if brand is None or brand.advertiser_organization_id != advertiser_organization_id:
        raise CrossOrgReferenceError("Invalid advertiser brand reference")


def _assert_org_in_scope(
    advertiser_organization_id: str,
    scope_advertiser_ids: frozenset[str] | None,
) -> None:
    """Raise ScopeError if scope is set and org is not in scope."""
    from packages.domain.exceptions import ScopeError

    if scope_advertiser_ids is not None and advertiser_organization_id not in scope_advertiser_ids:
        raise ScopeError("Organization not in scope")


async def create_campaign(
    session: AsyncSession,
    *,
    advertiser_organization_id: str,
    advertiser_contract_id: str,
    code: str,
    name: str,
    created_by: str,
    advertiser_brand_id: str | None = None,
    description: str | None = None,
    start_at=None,
    end_at=None,
    timezone: str = "Europe/Moscow",
    budget_limit_amount=None,
    budget_limit_currency: str = "RUB",
    priority: int = 0,
    scope_advertiser_ids: frozenset[str] | None = None,
) -> str:
    """Create a new campaign in draft status. Returns campaign id.

    Raises:
        ScopeError: if ``scope_advertiser_ids`` is set and the org is not in scope.
        CrossOrgReferenceError: if brand/contract belong to a different org.
        EntityNotFoundError: if contract or brand does not exist.
    """
    import uuid
    from datetime import datetime, timezone as tz
    from packages.domain.models import Campaign, CampaignStatusHistory

    # --- Tenant isolation: brand/contract must belong to the request org ---
    await _validate_contract_belongs_to_org(
        session, advertiser_contract_id, advertiser_organization_id,
    )
    if advertiser_brand_id is not None:
        await _validate_brand_belongs_to_org(
            session, advertiser_brand_id, advertiser_organization_id,
        )

    # --- Tenant isolation: scoped user can only create for own org ---
    _assert_org_in_scope(advertiser_organization_id, scope_advertiser_ids)

    campaign_id = str(uuid.uuid4())
    now = datetime.now(tz.utc)

    campaign = Campaign(
        id=campaign_id,
        advertiser_organization_id=advertiser_organization_id,
        advertiser_brand_id=advertiser_brand_id,
        advertiser_contract_id=advertiser_contract_id,
        code=code,
        name=name,
        description=description,
        status="draft",
        priority=priority,
        budget_limit_amount=budget_limit_amount,
        budget_limit_currency=budget_limit_currency,
        start_at=start_at,
        end_at=end_at,
        timezone=timezone,
        created_by=created_by,
        created_at=now,
        updated_at=now,
    )
    session.add(campaign)

    # Status history
    history = CampaignStatusHistory(
        id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        old_status=None,
        new_status="draft",
        changed_by=created_by,
        changed_at=now,
        reason="Campaign created",
    )
    session.add(history)

    return campaign_id


async def update_campaign(
    session: AsyncSession,
    campaign_id: str,
    *,
    changed_by: str,
    scope_advertiser_ids: frozenset[str] | None = None,
    **kwargs,
) -> str | None:
    """Update a draft campaign. Returns new status if status changed, else None.

    Only draft campaigns can be updated.  Only non-None kwargs are applied.
    Raises ScopeError if the campaign's org is not in the caller's scope.
    """
    from packages.domain.models import Campaign
    from packages.domain.exceptions import ScopeError
    from datetime import datetime, timezone as tz

    result = await session.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        return None
    if campaign.status != "draft":
        return None

    # --- Tenant isolation: scoped user can only mutate own org ---
    _assert_org_in_scope(campaign.advertiser_organization_id, scope_advertiser_ids)

    for key, value in kwargs.items():
        if value is not None and hasattr(campaign, key):
            setattr(campaign, key, value)

    campaign.updated_at = datetime.now(tz.utc)
    return campaign.status  # still "draft"


async def archive_campaign(
    session: AsyncSession,
    campaign_id: str,
    *,
    changed_by: str,
    scope_advertiser_ids: frozenset[str] | None = None,
) -> tuple[str | None, str]:
    """Archive a draft or rejected campaign. Returns (old_status, new_status).

    Only draft and rejected campaigns can be archived.
    Raises ScopeError if the campaign's org is not in the caller's scope.
    """
    import uuid
    from datetime import datetime, timezone as tz
    from packages.domain.models import Campaign, CampaignStatusHistory

    result = await session.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        return None, "archived"
    old_status = campaign.status
    if old_status not in ("draft", "rejected"):
        return old_status, old_status  # no change

    # --- Tenant isolation: scoped user can only mutate own org ---
    _assert_org_in_scope(campaign.advertiser_organization_id, scope_advertiser_ids)

    now = datetime.now(tz.utc)
    campaign.status = "archived"
    campaign.updated_at = now

    history = CampaignStatusHistory(
        id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        old_status=old_status,
        new_status="archived",
        changed_by=changed_by,
        changed_at=now,
        reason="Campaign archived",
    )
    session.add(history)

    return old_status, "archived"


# ---------------------------------------------------------------------------
# Approval Workflow (Phase 4.1d — ADR-015)
# ---------------------------------------------------------------------------


async def request_campaign_approval(
    session: AsyncSession,
    campaign_id: str,
    *,
    changed_by: str,
    scope_advertiser_ids: frozenset[str] | None = None,
) -> tuple[str | None, str | None]:
    """Request approval for a draft campaign. Returns (old_status, new_status).

    Transition: draft → pending_approval.
    Validates: ≥1 flight, ≥1 placement, ≥1 creative, flights within contract window.

    Returns (None, None) if campaign not found or not in draft status.
    Returns (old, old) if validation fails (no flights/placements/creatives, or
        flights outside contract validity window).
    """
    import uuid
    from datetime import datetime, timezone as tz
    from packages.domain.models import (
        AdvertiserContract,
        Campaign, CampaignStatusHistory,
        CampaignFlight, CampaignPlacement, CampaignCreative,
    )

    result = await session.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        return None, None
    if campaign.status != "draft":
        return None, None

    _assert_org_in_scope(campaign.advertiser_organization_id, scope_advertiser_ids)

    # Validation: ≥1 flight, ≥1 placement, ≥1 creative
    flight_count = await session.scalar(
        select(func.count()).select_from(CampaignFlight)
        .where(CampaignFlight.campaign_id == campaign_id)
    )
    placements = await session.scalar(
        select(func.count()).select_from(CampaignPlacement)
        .where(CampaignPlacement.campaign_id == campaign_id)
    )
    creatives = await session.scalar(
        select(func.count()).select_from(CampaignCreative)
        .where(CampaignCreative.campaign_id == campaign_id)
    )
    if not flight_count or not placements or not creatives:
        return campaign.status, campaign.status  # validation failed

    # Validate flight windows against contract (ADR-015 §3.5)
    contract = await session.get(AdvertiserContract, campaign.advertiser_contract_id)
    if contract is not None:
        flights_result = await session.execute(
            select(CampaignFlight).where(CampaignFlight.campaign_id == campaign_id)
        )
        for flight in flights_result.scalars().all():
            if flight.start_at and contract.valid_from and flight.start_at < contract.valid_from:
                return campaign.status, campaign.status
            if flight.start_at and flight.end_at and flight.end_at < flight.start_at:
                return campaign.status, campaign.status
            if flight.end_at and contract.valid_until and flight.end_at > contract.valid_until:
                return campaign.status, campaign.status

    now = datetime.now(tz.utc)
    old_status = campaign.status
    campaign.status = "pending_approval"
    campaign.updated_at = now

    history = CampaignStatusHistory(
        id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        old_status=old_status,
        new_status="pending_approval",
        changed_by=changed_by,
        changed_at=now,
        reason="Approval requested",
    )
    session.add(history)

    return old_status, "pending_approval"


async def approve_campaign(
    session: AsyncSession,
    campaign_id: str,
    *,
    reviewed_by: str,
    scope_advertiser_ids: frozenset[str] | None = None,
) -> tuple[str | None, str | None]:
    """Approve a pending_approval campaign. Returns (old_status, new_status).

    Transition: pending_approval → approved.
    Creates campaign_approvals row + status history.
    ``requested_at`` is taken from the draft→pending_approval status history
    transition, not from decision time.
    """
    import uuid
    from datetime import datetime, timezone as tz
    from packages.domain.models import (
        Campaign, CampaignApproval, CampaignStatusHistory,
    )

    result = await session.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        return None, None
    if campaign.status != "pending_approval":
        return None, None

    _assert_org_in_scope(campaign.advertiser_organization_id, scope_advertiser_ids)

    # Look up the request timestamp from the draft→pending_approval transition.
    # Fail if no such transition exists (never requested approval legitimately).
    request_result = await session.execute(
        select(CampaignStatusHistory.changed_at)
        .where(
            CampaignStatusHistory.campaign_id == campaign_id,
            CampaignStatusHistory.old_status == "draft",
            CampaignStatusHistory.new_status == "pending_approval",
        )
        .order_by(CampaignStatusHistory.changed_at.desc())
        .limit(1)
    )
    request_row = request_result.scalar_one_or_none()
    if request_row is None:
        return None, None  # safety: no request transition found

    requested_at = request_row

    now = datetime.now(tz.utc)
    old_status = campaign.status
    campaign.status = "approved"
    campaign.updated_at = now

    approval = CampaignApproval(
        id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        requested_by=campaign.created_by or "",
        requested_at=requested_at,
        reviewed_by=reviewed_by,
        reviewed_at=now,
        decision="approved",
    )
    session.add(approval)

    history = CampaignStatusHistory(
        id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        old_status=old_status,
        new_status="approved",
        changed_by=reviewed_by,
        changed_at=now,
        reason="Campaign approved",
    )
    session.add(history)

    return old_status, "approved"


async def reject_campaign(
    session: AsyncSession,
    campaign_id: str,
    *,
    reviewed_by: str,
    reason: str,
    scope_advertiser_ids: frozenset[str] | None = None,
) -> tuple[str | None, str | None]:
    """Reject a pending_approval campaign. Returns (old_status, new_status).

    Transition: pending_approval → rejected.
    Creates campaign_approvals row + status history.
    ``requested_at`` is taken from the draft→pending_approval status history
    transition, not from decision time.
    """
    import uuid
    from datetime import datetime, timezone as tz
    from packages.domain.models import (
        Campaign, CampaignApproval, CampaignStatusHistory,
    )

    result = await session.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        return None, None
    if campaign.status != "pending_approval":
        return None, None

    _assert_org_in_scope(campaign.advertiser_organization_id, scope_advertiser_ids)

    # Look up the request timestamp from the draft→pending_approval transition.
    # Fail if no such transition exists (never requested approval legitimately).
    request_result = await session.execute(
        select(CampaignStatusHistory.changed_at)
        .where(
            CampaignStatusHistory.campaign_id == campaign_id,
            CampaignStatusHistory.old_status == "draft",
            CampaignStatusHistory.new_status == "pending_approval",
        )
        .order_by(CampaignStatusHistory.changed_at.desc())
        .limit(1)
    )
    request_row = request_result.scalar_one_or_none()
    if request_row is None:
        return None, None  # safety: no request transition found

    requested_at = request_row

    now = datetime.now(tz.utc)
    old_status = campaign.status
    campaign.status = "rejected"
    campaign.updated_at = now

    approval = CampaignApproval(
        id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        requested_by=campaign.created_by or "",
        requested_at=requested_at,
        reviewed_by=reviewed_by,
        reviewed_at=now,
        decision="rejected",
        rejection_reason=reason[:1000],
    )
    session.add(approval)

    history = CampaignStatusHistory(
        id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        old_status=old_status,
        new_status="rejected",
        changed_by=reviewed_by,
        changed_at=now,
        reason=f"Campaign rejected: {reason[:200]}",
    )
    session.add(history)

    return old_status, "rejected"


# ---------------------------------------------------------------------------
# Transactional Outbox (Phase 4.1c — ADR-011)
# ---------------------------------------------------------------------------


async def enqueue_outbox_event(
    session: AsyncSession,
    *,
    event_type: str,
    event_version: str = "1.0",
    aggregate_type: str,
    aggregate_id: str,
    payload: dict,
    headers: dict | None = None,
    partition_key: str | None = None,
) -> str:
    """Enqueue an outbox event in the current transaction.

    Does NOT commit — caller owns the transaction boundary.
    Does NOT publish to NATS — relay worker handles delivery.
    Returns the event id.

    The payload/headers dicts are stored as-is in JSONB columns.
    Caller is responsible for ensuring no secrets/PII in payload
    before calling this function (per ADR-011 §2).
    """
    import uuid
    from packages.domain.models import OutboxEvent

    event_id = str(uuid.uuid4())
    event = OutboxEvent(
        id=event_id,
        event_type=event_type,
        event_version=event_version,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        partition_key=partition_key,
        payload_json=payload,
        headers_json=headers or {},
    )
    session.add(event)
    return event_id


async def fetch_pending_events(
    session: AsyncSession,
    *,
    limit: int = 100,
) -> list:
    """Fetch pending/failed events for relay worker polling.

    Ordered by next_attempt_at, limited to `limit` rows.
    """
    from packages.domain.models import OutboxEvent
    from sqlalchemy import or_

    stmt = (
        select(OutboxEvent)
        .where(
            or_(
                OutboxEvent.status == "pending",
                OutboxEvent.status == "failed",
            )
        )
        .order_by(OutboxEvent.next_attempt_at)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def mark_event_published(
    session: AsyncSession,
    event_id: str,
) -> None:
    """Mark an outbox event as published."""
    from packages.domain.models import OutboxEvent
    from sqlalchemy import update
    from datetime import datetime, timezone

    await session.execute(
        update(OutboxEvent)
        .where(OutboxEvent.id == event_id)
        .values(
            status="published",
            published_at=datetime.now(timezone.utc),
        )
    )


async def mark_event_failed(
    session: AsyncSession,
    event_id: str,
    *,
    last_error: str,
    max_attempts: int = 7,
) -> None:
    """Mark an outbox event as failed, with backoff.
    Moves to dead_letter after max_attempts.
    """
    from packages.domain.models import OutboxEvent
    from sqlalchemy import update
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(OutboxEvent.attempts).where(OutboxEvent.id == event_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return
    current_attempts = row + 1

    if current_attempts >= max_attempts:
        await session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(
                status="dead_letter",
                attempts=current_attempts,
                last_error=last_error[:2048],
            )
        )
    else:
        backoff_seconds = min(2 ** (current_attempts - 1), 64)
        next_attempt = now + timedelta(seconds=backoff_seconds)
        await session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(
                status="failed",
                attempts=current_attempts,
                next_attempt_at=next_attempt,
                last_error=last_error[:2048],
            )
        )
