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
