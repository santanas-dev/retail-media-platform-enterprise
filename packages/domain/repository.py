"""
Retail Media Platform — Async Repository Helpers.

Phase 3.0: Read-only query functions for identity/RBAC tables.
"""

from datetime import datetime
import uuid

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from packages.domain.models import (
    AdvertiserBrand,
    AdvertiserContact,
    AdvertiserContract,
    AdvertiserOrganization,
    AdvertiserUserMembership,
    AuditEventOperational,
    Branch,
    Cluster,
    CreativeAsset,
    CampaignCreative,
    DisplaySurface,
    InventoryBooking,
    InventoryRule,
    InventorySlot,
    LocalCredential,
    Permission,
    Role,
    RolePermission,
    Store,
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


async def create_audit_event(
    session: AsyncSession,
    *,
    actor_user_id: str,
    action: str,
    target_type: str,
    target_id: str | None = None,
    correlation_id: str | None = None,
    ip_address: str = "",
    details: dict | None = None,
) -> AuditEventOperational:
    """Write an operational audit event (S-035e).

    No secrets, passwords, tokens, or hashes in details.
    """
    import uuid as _uuid
    event = AuditEventOperational(
        id=str(_uuid.uuid4()),
        actor_user_id=actor_user_id or None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        correlation_id=correlation_id,
        ip_address=ip_address,
        details_json=details,
    )
    session.add(event)
    await session.flush()
    return event


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
    Includes permissions from ALL user role assignments — both global (unscoped)
    and scoped.  Tenant-level access control is enforced separately by
    resolve_scope_context / RLS (see packages.domain.scopes).
    """
    stmt = (
        select(Permission.code)
        .select_from(UserRole)
        .join(RolePermission, RolePermission.role_id == UserRole.role_id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(
            UserRole.user_id == user_id,
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


async def get_advertiser_organization(
    session: AsyncSession, org_id: str
) -> AdvertiserOrganization | None:
    """Get advertiser organization by ID."""
    stmt = select(AdvertiserOrganization).where(
        AdvertiserOrganization.id == org_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


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


async def get_advertiser_contract(
    session: AsyncSession,
    contract_id: str,
):
    """Get a single advertiser contract by id. Returns AdvertiserContract or None."""
    from packages.domain.models import AdvertiserContract as ContractModel
    result = await session.execute(
        select(ContractModel).where(ContractModel.id == contract_id)
    )
    return result.scalar_one_or_none()


async def list_advertiser_contacts(
    session: AsyncSession,
) -> list[AdvertiserContact]:
    """Return all advertiser contacts, ordered by contact_type + full_name."""
    stmt = select(AdvertiserContact).order_by(
        AdvertiserContact.contact_type, AdvertiserContact.full_name,
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_advertiser_brands_by_org(
    session: AsyncSession, org_id: str,
) -> list[AdvertiserBrand]:
    """Return brands for a specific advertiser org, ordered by code."""
    stmt = select(AdvertiserBrand).where(
        AdvertiserBrand.advertiser_organization_id == org_id,
    ).order_by(AdvertiserBrand.code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_advertiser_contracts_by_org(
    session: AsyncSession, org_id: str,
) -> list[AdvertiserContract]:
    """Return contracts for a specific advertiser org, ordered by code."""
    stmt = select(AdvertiserContract).where(
        AdvertiserContract.advertiser_organization_id == org_id,
    ).order_by(AdvertiserContract.code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_advertiser_contacts_by_org(
    session: AsyncSession, org_id: str,
) -> list[AdvertiserContact]:
    """Return contacts for a specific advertiser org, ordered by contact_type + full_name."""
    stmt = select(AdvertiserContact).where(
        AdvertiserContact.advertiser_organization_id == org_id,
    ).order_by(AdvertiserContact.contact_type, AdvertiserContact.full_name)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_advertiser_user_memberships(
    session: AsyncSession, org_id: str,
) -> list[dict]:
    """Return user memberships for an advertiser org — safe fields only."""
    from sqlalchemy import select as sa_select
    from packages.domain.models import LocalCredential
    stmt = sa_select(
        AdvertiserUserMembership.id,
        AdvertiserUserMembership.user_id,
        AdvertiserUserMembership.status.label("membership_status"),
        AdvertiserUserMembership.created_at.label("membership_created_at"),
        User.username,
        User.display_name,
        User.email,
        User.auth_provider,
        User.status.label("user_status"),
        LocalCredential.must_change_password,
    ).join(
        User, AdvertiserUserMembership.user_id == User.id,
    ).join(
        LocalCredential, User.id == LocalCredential.user_id, isouter=True,
    ).where(
        AdvertiserUserMembership.advertiser_organization_id == org_id,
    ).order_by(User.username)
    result = await session.execute(stmt)
    return [dict(row._mapping) for row in result]


# ---------------------------------------------------------------------------
# S-009h — Reference data (branches, clusters, stores, surfaces)
# ---------------------------------------------------------------------------


async def list_branches(session: AsyncSession) -> list[Branch]:
    """Return all active branches, ordered by code."""
    stmt = select(Branch).where(Branch.is_active == True).order_by(Branch.code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_clusters(session: AsyncSession) -> list[Cluster]:
    """Return all active clusters, ordered by code."""
    stmt = select(Cluster).where(Cluster.is_active == True).order_by(Cluster.code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_stores(session: AsyncSession) -> list[Store]:
    """Return all active stores, ordered by code."""
    stmt = select(Store).where(Store.is_active == True).order_by(Store.code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_display_surfaces(session: AsyncSession) -> list[DisplaySurface]:
    """Return all active display surfaces, ordered by code."""
    stmt = select(DisplaySurface).where(DisplaySurface.is_active == True).order_by(DisplaySurface.code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_inventory_stores(session: AsyncSession) -> list[dict]:
    """Enriched store list with cluster/branch names + surface count."""
    from packages.domain.models import Store, Cluster, Branch, DisplaySurface
    from sqlalchemy import select as sa_select, func

    surface_count_subq = (
        sa_select(DisplaySurface.store_id, func.count(DisplaySurface.id).label("cnt"))
        .group_by(DisplaySurface.store_id)
        .subquery()
    )

    stmt = (
        sa_select(
            Store.id,
            Store.code,
            Store.name,
            Store.address,
            Store.is_active,
            Cluster.name.label("cluster_name"),
            Branch.name.label("branch_name"),
            func.coalesce(surface_count_subq.c.cnt, 0).label("surface_count"),
        )
        .outerjoin(Cluster, Store.cluster_id == Cluster.id)
        .outerjoin(Branch, Cluster.branch_id == Branch.id)
        .outerjoin(surface_count_subq, Store.id == surface_count_subq.c.store_id)
        .order_by(Store.code)
    )

    result = await session.execute(stmt)
    return [dict(row._mapping) for row in result.fetchall()]


async def get_inventory_surfaces(session: AsyncSession) -> list[dict]:
    """Enriched surface list with store context, no device secrets."""
    from packages.domain.models import DisplaySurface, Store
    from sqlalchemy import select as sa_select

    stmt = (
        sa_select(
            DisplaySurface.id,
            DisplaySurface.code,
            DisplaySurface.store_id,
            DisplaySurface.resolution_w,
            DisplaySurface.resolution_h,
            DisplaySurface.is_active,
            Store.code.label("store_code"),
            Store.name.label("store_name"),
        )
        .outerjoin(Store, DisplaySurface.store_id == Store.id)
        .order_by(DisplaySurface.code)
    )

    result = await session.execute(stmt)
    return [dict(row._mapping) for row in result.fetchall()]


async def get_inventory_stores_paginated(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Paginated enriched store list — returns (items, total_count)."""
    from packages.domain.models import Store, Cluster, Branch, DisplaySurface
    from sqlalchemy import select as sa_select, func

    surface_count_subq = (
        sa_select(DisplaySurface.store_id, func.count(DisplaySurface.id).label("cnt"))
        .group_by(DisplaySurface.store_id)
        .subquery()
    )

    base_stmt = (
        sa_select(func.count())
        .select_from(Store)
    )
    total_result = await session.execute(base_stmt)
    total = total_result.scalar_one()

    stmt = (
        sa_select(
            Store.id,
            Store.code,
            Store.name,
            Store.address,
            Store.is_active,
            Cluster.name.label("cluster_name"),
            Branch.name.label("branch_name"),
            func.coalesce(surface_count_subq.c.cnt, 0).label("surface_count"),
        )
        .outerjoin(Cluster, Store.cluster_id == Cluster.id)
        .outerjoin(Branch, Cluster.branch_id == Branch.id)
        .outerjoin(surface_count_subq, Store.id == surface_count_subq.c.store_id)
        .order_by(Store.code)
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(stmt)
    items = [dict(row._mapping) for row in result.fetchall()]
    return items, total


async def get_inventory_surfaces_paginated(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Paginated enriched surface list — returns (items, total_count)."""
    from packages.domain.models import DisplaySurface, Store
    from sqlalchemy import select as sa_select, func

    total_result = await session.execute(
        sa_select(func.count()).select_from(DisplaySurface),
    )
    total = total_result.scalar_one()

    stmt = (
        sa_select(
            DisplaySurface.id,
            DisplaySurface.code,
            DisplaySurface.store_id,
            DisplaySurface.resolution_w,
            DisplaySurface.resolution_h,
            DisplaySurface.is_active,
            Store.code.label("store_code"),
            Store.name.label("store_name"),
        )
        .outerjoin(Store, DisplaySurface.store_id == Store.id)
        .order_by(DisplaySurface.code)
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(stmt)
    items = [dict(row._mapping) for row in result.fetchall()]
    return items, total


async def toggle_surface_active(
    session: AsyncSession,
    *,
    surface_id: str,
    is_active: bool,
) -> bool:
    """Toggle is_active on a display surface. Returns True if updated."""
    from datetime import datetime as _dt, timezone as _tz
    from packages.domain.models import DisplaySurface
    from sqlalchemy import update as sa_update

    result = await session.execute(
        sa_update(DisplaySurface)
        .where(DisplaySurface.id == surface_id)
        .values(is_active=is_active)
    )
    return result.rowcount > 0


async def get_display_surface(
    session: AsyncSession,
    surface_id: str,
):
    """Get a display surface with joined store context. Returns DisplaySurface or None."""
    from packages.domain.models import DisplaySurface, Store
    from sqlalchemy import select as sa_select, text

    stmt = (
        sa_select(
            DisplaySurface,
            Store.code.label("store_code"),
            Store.name.label("store_name"),
        )
        .outerjoin(Store, DisplaySurface.store_id == Store.id)
        .where(DisplaySurface.id == surface_id)
    )
    result = await session.execute(stmt)
    row = result.one_or_none()
    if row is None:
        return None
    surface = row.DisplaySurface
    surface.store_code = row.store_code
    surface.store_name = row.store_name
    return surface


# ---------------------------------------------------------------------------
# Campaign Domain (Phase 4.1b — ADR-015)
# ---------------------------------------------------------------------------


async def list_campaigns(session: AsyncSession) -> list:
    """Return all campaigns, ordered by code."""
    from packages.domain.models import Campaign
    stmt = select(Campaign).order_by(Campaign.code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_campaigns_paginated(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list, int]:
    """Paginated campaign list — returns (items, total_count)."""
    from packages.domain.models import Campaign
    from sqlalchemy import func

    total_result = await session.execute(
        select(func.count()).select_from(Campaign),
    )
    total = total_result.scalar_one()

    stmt = (
        select(Campaign)
        .order_by(Campaign.code)
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    items = list(result.scalars().all())
    return items, total


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


async def get_campaign_flight(
    session: AsyncSession,
    flight_id: str,
):
    """Get a single campaign flight by id. Returns CampaignFlight or None."""
    from packages.domain.models import CampaignFlight
    result = await session.execute(
        select(CampaignFlight).where(CampaignFlight.id == flight_id)
    )
    return result.scalar_one_or_none()


async def get_campaign_placement(
    session: AsyncSession,
    placement_id: str,
):
    """Get a single placement by id. Returns CampaignPlacement or None."""
    from packages.domain.models import CampaignPlacement
    result = await session.execute(
        select(CampaignPlacement).where(CampaignPlacement.id == placement_id)
    )
    return result.scalar_one_or_none()


async def get_creative_asset(
    session: AsyncSession,
    asset_id: str,
):
    """Get a single creative asset by id. Returns CreativeAsset or None."""
    from packages.domain.models import CreativeAsset
    result = await session.execute(
        select(CreativeAsset).where(CreativeAsset.id == asset_id)
    )
    return result.scalar_one_or_none()


def is_deliverable_checksum(sha256: str) -> bool:
    """Return True if the checksum is a valid 64-char hex string.

    Empty string means metadata-only — no file uploaded yet.
    Only a 64-char lowercase hex string qualifies as deliverable.
    Rejects the SHA-256 of the empty string (e3b0c442...) as a
    client-submitted placeholder.
    """
    if len(sha256) != 64:
        return False
    if not all(c in "0123456789abcdef" for c in sha256):
        return False
    # Reject empty-object SHA-256 — a common client placeholder
    if sha256 == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855":
        return False
    return True


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


async def list_moderation_queue(
    session: AsyncSession,
    *,
    status_filter: str = "pending_review",
) -> list:
    """List creative assets filtered by moderation_status, with advertiser context."""
    from packages.domain.models import CreativeAsset, AdvertiserOrganization
    from sqlalchemy import select as sa_select

    stmt = (
        sa_select(
            CreativeAsset.id,
            CreativeAsset.advertiser_organization_id,
            CreativeAsset.code,
            CreativeAsset.name,
            CreativeAsset.media_type,
            CreativeAsset.file_size_bytes,
            CreativeAsset.duration_ms,
            CreativeAsset.resolution_w,
            CreativeAsset.resolution_h,
            CreativeAsset.status,
            CreativeAsset.moderation_status,
            CreativeAsset.moderation_notes,
            CreativeAsset.created_at,
            CreativeAsset.updated_at,
            AdvertiserOrganization.name.label("advertiser_name"),
            AdvertiserOrganization.code.label("advertiser_code"),
        )
        .outerjoin(
            AdvertiserOrganization,
            CreativeAsset.advertiser_organization_id == AdvertiserOrganization.id,
        )
        .order_by(CreativeAsset.created_at.desc())
    )

    if status_filter != "all":
        stmt = stmt.where(CreativeAsset.moderation_status == status_filter)

    result = await session.execute(stmt)
    return [dict(row._mapping) for row in result.fetchall()]


async def list_moderation_queue_paginated(
    session: AsyncSession,
    *,
    status_filter: str = "pending_review",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list, int]:
    """Paginated creative moderation queue — returns (items, total_count)."""
    from packages.domain.models import CreativeAsset, AdvertiserOrganization
    from sqlalchemy import select as sa_select, func

    count_stmt = (
        sa_select(func.count())
        .select_from(CreativeAsset)
    )
    if status_filter != "all":
        count_stmt = count_stmt.where(CreativeAsset.moderation_status == status_filter)

    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = (
        sa_select(
            CreativeAsset.id,
            CreativeAsset.advertiser_organization_id,
            CreativeAsset.code,
            CreativeAsset.name,
            CreativeAsset.media_type,
            CreativeAsset.file_size_bytes,
            CreativeAsset.duration_ms,
            CreativeAsset.resolution_w,
            CreativeAsset.resolution_h,
            CreativeAsset.status,
            CreativeAsset.moderation_status,
            CreativeAsset.moderation_notes,
            CreativeAsset.created_at,
            CreativeAsset.updated_at,
            AdvertiserOrganization.name.label("advertiser_name"),
            AdvertiserOrganization.code.label("advertiser_code"),
        )
        .outerjoin(
            AdvertiserOrganization,
            CreativeAsset.advertiser_organization_id == AdvertiserOrganization.id,
        )
        .order_by(CreativeAsset.created_at.desc())
    )

    if status_filter != "all":
        stmt = stmt.where(CreativeAsset.moderation_status == status_filter)

    stmt = stmt.offset(offset).limit(limit)

    result = await session.execute(stmt)
    items = [dict(row._mapping) for row in result.fetchall()]
    return items, total


async def approve_creative_asset(
    session: AsyncSession,
    *,
    asset_id: str,
) -> bool:
    """Approve a creative asset — set moderation_status to approved, clear notes."""
    from datetime import datetime as _dt, timezone as _tz
    from packages.domain.models import CreativeAsset
    from sqlalchemy import update as sa_update

    result = await session.execute(
        sa_update(CreativeAsset)
        .where(CreativeAsset.id == asset_id)
        .values(
            moderation_status="approved",
            moderation_notes=None,
            updated_at=_dt.now(_tz.utc),
        )
    )
    return result.rowcount > 0


async def reject_creative_asset(
    session: AsyncSession,
    *,
    asset_id: str,
    reason: str,
) -> bool:
    """Reject a creative asset — set moderation_status to rejected, store reason."""
    from datetime import datetime as _dt, timezone as _tz
    from packages.domain.models import CreativeAsset
    from sqlalchemy import update as sa_update

    result = await session.execute(
        sa_update(CreativeAsset)
        .where(CreativeAsset.id == asset_id)
        .values(
            moderation_status="rejected",
            moderation_notes=reason,
            updated_at=_dt.now(_tz.utc),
        )
    )
    return result.rowcount > 0


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


async def list_approval_queue(
    session: AsyncSession,
    *,
    status_filter: str = "pending_approval",
) -> list[dict]:
    """Enriched approval queue with advertiser context + readiness summary."""
    from packages.domain.models import (
        Campaign, AdvertiserOrganization, AdvertiserBrand,
        CampaignFlight, CampaignPlacement, CampaignCreative, CreativeAsset,
        CampaignApproval, CampaignStatusHistory,
    )
    from sqlalchemy import select as sa_select, func

    stmt = (
        sa_select(
            Campaign.id.label("campaign_id"),
            Campaign.code.label("campaign_code"),
            Campaign.name.label("campaign_name"),
            Campaign.status.label("campaign_status"),
            Campaign.advertiser_organization_id.label("advertiser_org_id"),
            AdvertiserOrganization.name.label("advertiser_org_name"),
            AdvertiserBrand.name.label("advertiser_brand_name"),
            CampaignStatusHistory.changed_at.label("requested_at"),
            CampaignStatusHistory.changed_by.label("requested_by"),
            CampaignApproval.rejection_reason.label("rejection_reason"),
        )
        .outerjoin(AdvertiserOrganization, Campaign.advertiser_organization_id == AdvertiserOrganization.id)
        .outerjoin(AdvertiserBrand, Campaign.advertiser_brand_id == AdvertiserBrand.id)
        .outerjoin(
            CampaignApproval,
            Campaign.id == CampaignApproval.campaign_id,
        )
        .outerjoin(
            CampaignStatusHistory,
            Campaign.id == CampaignStatusHistory.campaign_id,
        )
        .where(CampaignStatusHistory.new_status == "pending_approval")
    )

    if status_filter != "all":
        stmt = stmt.where(Campaign.status == status_filter)

    stmt = stmt.order_by(CampaignStatusHistory.changed_at.desc())

    result = await session.execute(stmt)
    rows = [dict(row._mapping) for row in result.fetchall()]

    await _enrich_approval_queue_rows(session, rows)
    return rows


async def _enrich_approval_queue_rows(
    session: AsyncSession,
    rows: list[dict],
) -> None:
    """Mutate rows in-place with readiness summary per campaign."""
    from packages.domain.models import (
        CampaignFlight, CampaignPlacement, CampaignCreative, CreativeAsset,
    )
    from sqlalchemy import select as sa_select, func

    for row in rows:
        cid = row["campaign_id"]
        flight_count = await session.scalar(
            sa_select(func.count()).select_from(CampaignFlight)
            .where(CampaignFlight.campaign_id == cid)
        )
        placement_count = await session.scalar(
            sa_select(func.count()).select_from(CampaignPlacement)
            .where(CampaignPlacement.campaign_id == cid)
        )
        cc_result = await session.execute(
            sa_select(CampaignCreative.creative_asset_id)
            .where(CampaignCreative.campaign_id == cid)
        )
        asset_ids = [r[0] for r in cc_result.fetchall()]
        creative_count = len(asset_ids)
        all_ready = False
        all_approved = False
        if asset_ids:
            ca_result = await session.execute(
                sa_select(CreativeAsset.status, CreativeAsset.moderation_status)
                .where(CreativeAsset.id.in_(asset_ids))
            )
            ca_rows = ca_result.fetchall()
            all_ready = all(r[0] == "ready" for r in ca_rows)
            all_approved = all(r[1] == "approved" for r in ca_rows)

        row["has_flight"] = bool(flight_count)
        row["has_placement"] = bool(placement_count)
        row["has_creative"] = bool(creative_count)
        row["all_creatives_ready"] = all_ready
        row["all_creatives_approved"] = all_approved


async def list_approval_queue_paginated(
    session: AsyncSession,
    *,
    status_filter: str = "pending_approval",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Paginated approval queue with readiness enrichment — returns (items, total_count)."""
    from packages.domain.models import (
        Campaign,
        CampaignStatusHistory,
    )
    from sqlalchemy import select as sa_select, func

    # Count matching campaigns
    count_stmt = (
        sa_select(func.count())
        .select_from(Campaign)
        .join(CampaignStatusHistory,
              Campaign.id == CampaignStatusHistory.campaign_id)
        .where(CampaignStatusHistory.new_status == "pending_approval")
    )
    if status_filter != "all":
        count_stmt = count_stmt.where(Campaign.status == status_filter)

    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    # Get paginated IDs (no enrichment yet)
    id_stmt = (
        sa_select(Campaign.id)
        .join(CampaignStatusHistory,
              Campaign.id == CampaignStatusHistory.campaign_id)
        .where(CampaignStatusHistory.new_status == "pending_approval")
        .order_by(CampaignStatusHistory.changed_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if status_filter != "all":
        id_stmt = id_stmt.where(Campaign.status == status_filter)

    id_result = await session.execute(id_stmt)
    paginated_ids = [row[0] for row in id_result.fetchall()]

    if not paginated_ids:
        return [], total

    # Get full rows for paginated campaigns only
    rows = await _approval_queue_rows_by_ids(session, paginated_ids)
    await _enrich_approval_queue_rows(session, rows)
    return rows, total


async def _approval_queue_rows_by_ids(
    session: AsyncSession,
    campaign_ids: list[str],
) -> list[dict]:
    """Fetch approval queue rows for specific campaign IDs."""
    from packages.domain.models import (
        Campaign, AdvertiserOrganization, AdvertiserBrand,
        CampaignApproval, CampaignStatusHistory,
    )
    from sqlalchemy import select as sa_select

    stmt = (
        sa_select(
            Campaign.id.label("campaign_id"),
            Campaign.code.label("campaign_code"),
            Campaign.name.label("campaign_name"),
            Campaign.status.label("campaign_status"),
            Campaign.advertiser_organization_id.label("advertiser_org_id"),
            AdvertiserOrganization.name.label("advertiser_org_name"),
            AdvertiserBrand.name.label("advertiser_brand_name"),
            CampaignStatusHistory.changed_at.label("requested_at"),
            CampaignStatusHistory.changed_by.label("requested_by"),
            CampaignApproval.rejection_reason.label("rejection_reason"),
        )
        .outerjoin(AdvertiserOrganization, Campaign.advertiser_organization_id == AdvertiserOrganization.id)
        .outerjoin(AdvertiserBrand, Campaign.advertiser_brand_id == AdvertiserBrand.id)
        .outerjoin(CampaignApproval, Campaign.id == CampaignApproval.campaign_id)
        .outerjoin(CampaignStatusHistory, Campaign.id == CampaignStatusHistory.campaign_id)
        .where(Campaign.id.in_(campaign_ids))
        .where(CampaignStatusHistory.new_status == "pending_approval")
        .order_by(CampaignStatusHistory.changed_at.desc())
    )

    result = await session.execute(stmt)
    return [dict(row._mapping) for row in result.fetchall()]


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
        CreativeAsset,
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

    # P1 fix: reject approval if any attached creative is metadata-only
    # (empty sha256_checksum = no real file uploaded yet)
    cc_result = await session.execute(
        select(CampaignCreative.creative_asset_id)
        .where(CampaignCreative.campaign_id == campaign_id)
    )
    asset_ids = [row[0] for row in cc_result.fetchall()]
    if asset_ids:
        asset_rows = await session.execute(
            select(CreativeAsset.id, CreativeAsset.sha256_checksum,
                   CreativeAsset.status, CreativeAsset.moderation_status,
                   CreativeAsset.file_size_bytes, CreativeAsset.storage_key)
            .where(CreativeAsset.id.in_(asset_ids))
        )
        for aid, cs, st, mod_st, fsz, sk in asset_rows.fetchall():
            # S-017: full deliverability check — not just checksum
            if not is_deliverable_checksum(cs):
                return campaign.status, campaign.status  # empty/invalid checksum
            if st != "ready":
                return campaign.status, campaign.status  # not uploaded
            if mod_st != "approved":
                return campaign.status, campaign.status  # not approved
            if fsz <= 0:
                return campaign.status, campaign.status  # zero-size file
            if not sk or sk == "":
                return campaign.status, campaign.status  # no storage key

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

    S-038: re-verifies readiness at approve time — creative moderation may
    have changed since the original request_approval call.
    """
    import uuid
    from datetime import datetime, timezone as tz
    from packages.domain.models import (
        Campaign, CampaignApproval, CampaignStatusHistory,
    )

    result = await session.execute(
        select(Campaign)
        .where(Campaign.id == campaign_id)
        .with_for_update()
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        return None, None
    if campaign.status != "pending_approval":
        return None, None

    _assert_org_in_scope(campaign.advertiser_organization_id, scope_advertiser_ids)

    # S-038: re-verify readiness at approve time — creative moderation may have
    # changed since the original request_approval call.
    from packages.domain.models import (
        CampaignFlight, CampaignPlacement, CampaignCreative, CreativeAsset,
    )
    flight_count = await session.scalar(
        select(func.count()).select_from(CampaignFlight)
        .where(CampaignFlight.campaign_id == campaign_id)
    )
    placement_count = await session.scalar(
        select(func.count()).select_from(CampaignPlacement)
        .where(CampaignPlacement.campaign_id == campaign_id)
    )
    cc_result = await session.execute(
        select(CampaignCreative.creative_asset_id)
        .where(CampaignCreative.campaign_id == campaign_id)
    )
    asset_ids = [row[0] for row in cc_result.fetchall()]
    if not flight_count or not placement_count or not asset_ids:
        return None, None  # no flights/placements/creatives — cannot approve
    if asset_ids:
        ca_result = await session.execute(
            select(CreativeAsset.status, CreativeAsset.moderation_status)
            .where(CreativeAsset.id.in_(asset_ids))
        )
        for st, mod_st in ca_result.fetchall():
            if st != "ready":
                return None, None  # creative not uploaded
            if mod_st != "approved":
                return None, None  # creative not approved by moderation

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
        select(Campaign)
        .where(Campaign.id == campaign_id)
        .with_for_update()
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
# Campaign Flight / Placement / Creative  (Pilot B1)
# ---------------------------------------------------------------------------


async def create_campaign_flight(
    session: AsyncSession,
    *,
    campaign_id: str,
    name: str | None = None,
    start_at: datetime,
    end_at: datetime,
    dayparting_json: dict | None = None,
    days_of_week: list[int] | None = None,
    priority: int = 0,
    scope_advertiser_ids: frozenset[str] | None = None,
) -> str | None:
    """Create a flight for a draft campaign. Returns flight id.

    Enforces: campaign exists, status == 'draft', start_at < end_at,
    org is in scope (RLS defense-in-depth).

    Returns None if campaign not found or not in draft.
    Raises ScopeError if org is not in scope.
    """
    import uuid

    from packages.domain.models import Campaign, CampaignFlight

    campaign = (
        await session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
    ).scalar_one_or_none()
    if campaign is None or campaign.status != "draft":
        return None

    _assert_org_in_scope(campaign.advertiser_organization_id, scope_advertiser_ids)

    flight_id = str(uuid.uuid4())
    flight = CampaignFlight(
        id=flight_id,
        campaign_id=campaign_id,
        name=name,
        start_at=start_at,
        end_at=end_at,
        dayparting_json=dayparting_json,
        days_of_week=days_of_week,
        priority=priority,
    )
    session.add(flight)
    return flight_id


async def update_campaign_flight(
    session: AsyncSession,
    flight_id: str,
    *,
    scope_advertiser_ids: frozenset[str] | None = None,
    **kwargs,
) -> str | None:
    """Partial update of a flight. Returns campaign_id on success, None if blocked.

    Enforces: flight exists, owning campaign is in draft, org is in scope.
    """
    from packages.domain.models import Campaign, CampaignFlight
    from datetime import datetime, timezone as tz

    flight = (
        await session.execute(
            select(CampaignFlight).where(CampaignFlight.id == flight_id)
        )
    ).scalar_one_or_none()
    if flight is None:
        return None

    campaign = (
        await session.execute(
            select(Campaign).where(Campaign.id == flight.campaign_id)
        )
    ).scalar_one_or_none()
    if campaign is None or campaign.status != "draft":
        return None

    _assert_org_in_scope(campaign.advertiser_organization_id, scope_advertiser_ids)

    for key, value in kwargs.items():
        if value is not None and hasattr(flight, key):
            setattr(flight, key, value)

    campaign.updated_at = datetime.now(tz.utc)
    return flight.campaign_id


async def create_campaign_placement(
    session: AsyncSession,
    *,
    campaign_id: str,
    display_surface_id: str | None = None,
    store_id: str | None = None,
    cluster_id: str | None = None,
    branch_id: str | None = None,
    share_of_voice_pct: int = 100,
    max_impressions: int | None = None,
    scope_advertiser_ids: frozenset[str] | None = None,
) -> str | None:
    """Create a placement for a draft campaign. Returns placement id.

    Enforces: campaign in draft, at least one target non-null,
    org is in scope.  The DB CHECK provides the second line of defense.
    Returns None if campaign not found or not in draft.
    """
    import uuid

    from packages.domain.models import Campaign, CampaignPlacement

    campaign = (
        await session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
    ).scalar_one_or_none()
    if campaign is None or campaign.status != "draft":
        return None

    _assert_org_in_scope(campaign.advertiser_organization_id, scope_advertiser_ids)

    placement_id = str(uuid.uuid4())
    placement = CampaignPlacement(
        id=placement_id,
        campaign_id=campaign_id,
        display_surface_id=display_surface_id,
        store_id=store_id,
        cluster_id=cluster_id,
        branch_id=branch_id,
        share_of_voice_pct=share_of_voice_pct,
        max_impressions=max_impressions,
        status="active",
    )
    session.add(placement)
    return placement_id


async def update_campaign_placement(
    session: AsyncSession,
    placement_id: str,
    *,
    scope_advertiser_ids: frozenset[str] | None = None,
    **kwargs,
) -> str | None:
    """Partial update of a placement. Returns campaign_id on success, None if blocked."""
    from packages.domain.models import Campaign, CampaignPlacement
    from datetime import datetime, timezone as tz

    placement = (
        await session.execute(
            select(CampaignPlacement).where(CampaignPlacement.id == placement_id)
        )
    ).scalar_one_or_none()
    if placement is None:
        return None

    campaign = (
        await session.execute(
            select(Campaign).where(Campaign.id == placement.campaign_id)
        )
    ).scalar_one_or_none()
    if campaign is None or campaign.status != "draft":
        return None

    _assert_org_in_scope(campaign.advertiser_organization_id, scope_advertiser_ids)

    for key, value in kwargs.items():
        if value is not None and hasattr(placement, key):
            setattr(placement, key, value)

    campaign.updated_at = datetime.now(tz.utc)
    return placement.campaign_id


async def create_campaign_creative(
    session: AsyncSession,
    *,
    campaign_id: str,
    advertiser_organization_id: str,
    code: str,
    name: str,
    media_type: str,
    sha256_checksum: str,
    file_size_bytes: int,
    duration_ms: int | None = None,
    resolution_w: int | None = None,
    resolution_h: int | None = None,
    sort_order: int = 0,
    duration_override_ms: int | None = None,
    scope_advertiser_ids: frozenset[str] | None = None,
    created_by: str | None = None,
    storage_bucket: str = "pilot",
) -> tuple[str, str] | None:
    """Create a CreativeAsset + CampaignCreative in one call. Returns (asset_id, link_id).

    S-017: Always creates metadata_only / pending_review — no ready/approved bypass.
    Client-provided sha256_checksum/file_size_bytes are IGNORED (never trusted).
    The only path to ready/approved is complete-upload with server-computed SHA-256.

    Pilot: storage_key is auto-derived; storage_bucket defaults to "pilot".
    The response schemas (CreativeAssetOut) never expose storage fields.

    Enforces: campaign in draft, advertiser_organization_id matches campaign org,
    org is in scope.

    Returns None if campaign not found or not in draft.
    Raises CrossOrgReferenceError if advertiser_organization_id mismatches.
    """
    import uuid
    from datetime import datetime, timezone as tz

    from packages.domain.exceptions import CrossOrgReferenceError
    from packages.domain.models import Campaign, CampaignCreative, CreativeAsset

    campaign = (
        await session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
    ).scalar_one_or_none()
    if campaign is None or campaign.status != "draft":
        return None

    if str(campaign.advertiser_organization_id) != str(advertiser_organization_id):
        raise CrossOrgReferenceError(
            "Campaign advertiser_organization_id does not match creative owner"
        )

    _assert_org_in_scope(advertiser_organization_id, scope_advertiser_ids)

    asset_id = str(uuid.uuid4())
    storage_key = f"pilot/creatives/{asset_id}"
    now = datetime.now(tz.utc)

    # S-017 P0 fix: create_campaign_creative always creates metadata_only.
    # Client-provided sha256_checksum / file_size_bytes are ignored.
    # The only path to ready/approved is complete-upload with server SHA-256.
    asset = CreativeAsset(
        id=asset_id,
        advertiser_organization_id=advertiser_organization_id,
        code=code,
        name=name,
        media_type=media_type,
        storage_bucket=storage_bucket,
        storage_key=storage_key,
        sha256_checksum="",
        file_size_bytes=0,
        duration_ms=duration_ms,
        resolution_w=resolution_w,
        resolution_h=resolution_h,
        status="metadata_only",
        moderation_status="pending_review",
        created_by=created_by,
        created_at=now,
        updated_at=now,
    )
    session.add(asset)
    await session.flush()  # ensure asset id is visible to FK on CampaignCreative

    link_id = str(uuid.uuid4())
    link = CampaignCreative(
        id=link_id,
        campaign_id=campaign_id,
        creative_asset_id=asset_id,
        sort_order=sort_order,
        duration_override_ms=duration_override_ms,
    )
    session.add(link)

    return (asset_id, link_id)


async def create_creative_asset_metadata(
    session: AsyncSession,
    *,
    advertiser_organization_id: str,
    code: str,
    name: str,
    media_type: str,
    sha256_checksum: str = "",
    file_size_bytes: int | None = None,
    resolution_w: int | None = None,
    resolution_h: int | None = None,
    duration_ms: int | None = None,
    scope_advertiser_ids: frozenset[str] | None = None,
    created_by: str | None = None,
    storage_bucket: str = "pilot",
) -> str:
    """Create CreativeAsset metadata only — no file upload, no campaign link.

    Pilot-safe: storage_key is auto-derived; storage_bucket defaults to "pilot".
    sha256_checksum is auto-filled with a pilot-safe placeholder if empty.
    status="metadata_only" to differentiate from ready (uploaded) assets.

    Enforces: advertiser_organization_id is in scope.

    Returns the new asset_id.
    Raises CrossOrgReferenceError if advertiser_organization_id is not in scope.
    """
    import uuid
    from datetime import datetime, timezone as tz

    from packages.domain.exceptions import CrossOrgReferenceError
    from packages.domain.models import CreativeAsset

    _assert_org_in_scope(advertiser_organization_id, scope_advertiser_ids)

    asset_id = str(uuid.uuid4())
    storage_key_val = f"pilot/creatives/{asset_id}"
    # P1 fix: empty string = no real checksum — NOT a fake placeholder.
    # Only a valid 64-char hex string counts as a real file checksum.
    checksum = sha256_checksum.strip() if sha256_checksum else ""
    now = datetime.now(tz.utc)

    asset = CreativeAsset(
        id=asset_id,
        advertiser_organization_id=advertiser_organization_id,
        code=code,
        name=name,
        media_type=media_type,
        storage_bucket=storage_bucket,
        storage_key=storage_key_val,
        sha256_checksum=checksum,
        file_size_bytes=file_size_bytes or 0,
        duration_ms=duration_ms,
        resolution_w=resolution_w,
        resolution_h=resolution_h,
        status="metadata_only",
        moderation_status="pending_review",
        created_by=created_by,
        created_at=now,
        updated_at=now,
    )
    session.add(asset)
    await session.flush()  # ensure id is visible for outbox FK
    return asset_id


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

    Only returns events whose next_attempt_at has passed (ADR-011 §3).
    Ordered by next_attempt_at, limited to `limit` rows.
    """
    from datetime import datetime, timezone

    from packages.domain.models import OutboxEvent
    from sqlalchemy import and_, or_

    now = datetime.now(timezone.utc)
    stmt = (
        select(OutboxEvent)
        .where(
            and_(
                or_(
                    OutboxEvent.status == "pending",
                    OutboxEvent.status == "failed",
                ),
                OutboxEvent.next_attempt_at <= now,
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
) -> bool:
    """Mark an outbox event as failed, with backoff.
    Moves to dead_letter after max_attempts.

    Returns True if the event transitioned to dead_letter.
    """
    from packages.domain.models import OutboxEvent
    from sqlalchemy import update
    from datetime import timezone, timedelta

    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(OutboxEvent.attempts).where(OutboxEvent.id == event_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return False
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
        return True
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
        return False


# ---------------------------------------------------------------------------
# Delivery Foundation (Phase 4.2b — ADR-016)
# ---------------------------------------------------------------------------


async def create_delivery_plan(
    session: AsyncSession,
    *,
    campaign_id: str,
    campaign_version_hash: str,
    reason: str | None = None,
) -> str:
    """Create a delivery_plans row. Returns the plan id.

    Does NOT commit — caller owns the transaction boundary.
    """
    import uuid
    from packages.domain.models import DeliveryPlan

    plan_id = str(uuid.uuid4())
    plan = DeliveryPlan(
        id=plan_id,
        campaign_id=campaign_id,
        campaign_version_hash=campaign_version_hash,
        status="planned",
        reason=reason,
    )
    session.add(plan)
    return plan_id


async def create_delivery_manifest_record(
    session: AsyncSession,
    *,
    manifest_id_external: str,
    campaign_id: str,
    physical_device_id: str,
    content_hash: str,
    manifest_version: int = 1,
    surface_ids: list[str] | None = None,
    asset_records: list[dict] | None = None,
) -> str:
    """Create a delivery_manifests row with optional surfaces and assets.

    Does NOT commit — caller owns the transaction boundary.
    Does NOT publish NATS.  Does NOT generate manifest JSON.

    Returns the internal manifest id (PK).
    """
    import uuid
    from packages.domain.models import (
        DeliveryManifest,
        DeliveryManifestAsset,
        DeliveryManifestSurface,
    )

    internal_id = str(uuid.uuid4())
    manifest = DeliveryManifest(
        id=internal_id,
        manifest_id=manifest_id_external,
        campaign_id=campaign_id,
        physical_device_id=physical_device_id,
        content_hash=content_hash,
        manifest_version=manifest_version,
        status="planned",
    )
    session.add(manifest)

    if surface_ids:
        for idx, sid in enumerate(surface_ids):
            session.add(DeliveryManifestSurface(
                id=str(uuid.uuid4()),
                manifest_id=internal_id,
                display_surface_id=sid,
                slot_order=idx,
            ))

    if asset_records:
        for a in asset_records:
            session.add(DeliveryManifestAsset(
                id=str(uuid.uuid4()),
                manifest_id=internal_id,
                creative_asset_id=a["creative_asset_id"],
                sha256_checksum=a["sha256_checksum"],
                duration_ms=a.get("duration_ms"),
                media_type=a["media_type"],
            ))

    return internal_id


async def get_next_manifest_version_for_device(
    session: AsyncSession,
    physical_device_id: str,
) -> int:
    """Return the next monotonic manifest_version for a device (max + 1).

    Returns 1 if no manifests exist for this device yet.
    """
    from packages.domain.models import DeliveryManifest

    result = await session.execute(
        select(func.coalesce(func.max(DeliveryManifest.manifest_version), 0))
        .where(DeliveryManifest.physical_device_id == physical_device_id)
    )
    current_max: int = result.scalar_one()
    return current_max + 1


async def list_delivery_manifests(
    session: AsyncSession,
    *,
    campaign_id: str | None = None,
    physical_device_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list:
    """List delivery manifests, optionally filtered."""
    from packages.domain.models import DeliveryManifest

    stmt = select(DeliveryManifest).order_by(DeliveryManifest.created_at.desc())
    if campaign_id:
        stmt = stmt.where(DeliveryManifest.campaign_id == campaign_id)
    if physical_device_id:
        stmt = stmt.where(DeliveryManifest.physical_device_id == physical_device_id)
    if status:
        stmt = stmt.where(DeliveryManifest.status == status)
    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def mark_manifest_generated(
    session: AsyncSession,
    manifest_id_external: str,
    *,
    content_hash: str,
) -> None:
    """Mark a manifest as generated.  Idempotent — no-op if already generated."""
    from packages.domain.models import DeliveryManifest
    from datetime import datetime, timezone as tz
    from sqlalchemy import update as sa_update

    await session.execute(
        sa_update(DeliveryManifest)
        .where(
            DeliveryManifest.manifest_id == manifest_id_external,
            DeliveryManifest.status == "planned",
        )
        .values(
            status="generated",
            content_hash=content_hash,
            generated_at=datetime.now(tz.utc),
        )
    )


async def mark_manifest_failed(
    session: AsyncSession,
    manifest_id_external: str,
    *,
    last_error: str,
) -> None:
    """Mark a manifest as failed.  Idempotent."""
    from packages.domain.models import DeliveryManifest
    from sqlalchemy import update as sa_update

    await session.execute(
        sa_update(DeliveryManifest)
        .where(
            DeliveryManifest.manifest_id == manifest_id_external,
            DeliveryManifest.status.in_(["planned", "generated"]),
        )
        .values(
            status="failed",
            last_error=last_error[:2048],
        )
    )


async def mark_manifest_delivered(
    session: AsyncSession,
    manifest_id_external: str,
) -> None:
    """Mark a manifest as delivered.  Idempotent."""
    from packages.domain.models import DeliveryManifest
    from datetime import datetime, timezone as tz
    from sqlalchemy import update as sa_update

    await session.execute(
        sa_update(DeliveryManifest)
        .where(
            DeliveryManifest.manifest_id == manifest_id_external,
            DeliveryManifest.status.in_(["generated", "delivered"]),
        )
        .values(
            status="delivered",
            delivered_at=datetime.now(tz.utc),
        )
    )


async def create_delivery_attempt(
    session: AsyncSession,
    *,
    manifest_id_external: str,
) -> str:
    """Create a delivery_attempts row.  Returns the attempt id.

    Does NOT commit — caller owns the transaction boundary.
    """
    import uuid
    from packages.domain.models import DeliveryAttempt

    attempt_id = str(uuid.uuid4())
    attempt = DeliveryAttempt(
        id=attempt_id,
        manifest_id=manifest_id_external,
        status="pending",
    )
    session.add(attempt)
    return attempt_id




async def get_physical_device_for_manifest_delivery(
    session: AsyncSession,
    physical_device_id: str,
) -> str | None:
    """Return device status for manifest delivery gating, or None if not found.

    Returns the status string (e.g., 'active', 'online', 'offline') if the
    device exists and its assigned store is still present in the DB.
    Returns None when the device is missing, has been soft-deleted, or its
    store has been removed (orphaned device).

    Only for read-only existence + status + store check — no update.
    """
    from packages.domain.models import PhysicalDevice, Store
    device = (
        await session.execute(
            select(PhysicalDevice)
            .join(Store, PhysicalDevice.store_id == Store.id)
            .where(
                PhysicalDevice.id == physical_device_id,
            )
        )
    ).scalar_one_or_none()
    return device.status if device else None


async def get_latest_manifest_metadata(
    session: AsyncSession,
    physical_device_id: str,
) -> dict | None:
    """Return lightweight manifest metadata for ETag / cache decisions.

    Single SELECT — no surface/asset/campaign join, no HMAC signing.
    Returns ``{manifest_id, content_hash, manifest_version, generated_at}``
    or None if no generated manifest exists for this device.
    """
    from packages.domain.models import DeliveryManifest

    row = (
        await session.execute(
            select(
                DeliveryManifest.manifest_id,
                DeliveryManifest.content_hash,
                DeliveryManifest.manifest_version,
                DeliveryManifest.generated_at,
            )
            .where(
                DeliveryManifest.physical_device_id == physical_device_id,
                DeliveryManifest.status == "generated",
            )
            .order_by(DeliveryManifest.generated_at.desc())
            .limit(1)
        )
    ).first()

    if row is None:
        return None

    return {
        "manifest_id": row[0],
        "content_hash": row[1],
        "manifest_version": row[2],
        "generated_at": row[3].isoformat() if row[3] else None,
    }


async def get_latest_manifest_for_device(
    session: AsyncSession,
    physical_device_id: str,
) -> dict | None:
    """Return the latest generated manifest payload for a device, or None.

    Only returns manifests with status='generated', ordered by generated_at DESC.
    Reconstructs manifest JSON from delivery_manifests + surfaces + assets.
    Does NOT regenerate from campaign — reads from persisted delivery tables.
    """
    from packages.domain.models import (
        DeliveryManifest,
        DeliveryManifestSurface,
        DeliveryManifestAsset,
        Campaign,
        CreativeAsset,
        CampaignCreative,
        DisplaySurface,
        PhysicalDevice,
        Store,
        DeviceType,
        Channel,
    )

    manifest = (
        await session.execute(
            select(DeliveryManifest)
            .where(
                DeliveryManifest.physical_device_id == physical_device_id,
                DeliveryManifest.status == "generated",
            )
            .order_by(DeliveryManifest.generated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if manifest is None:
        return None

    # Load surfaces
    surfaces_result = await session.execute(
        select(DeliveryManifestSurface, DisplaySurface)
        .join(DisplaySurface, DeliveryManifestSurface.display_surface_id == DisplaySurface.id)
        .where(DeliveryManifestSurface.manifest_id == manifest.id)
        .order_by(DeliveryManifestSurface.slot_order)
    )
    surface_rows = surfaces_result.all()

    # Load assets
    assets_result = await session.execute(
        select(DeliveryManifestAsset)
        .where(DeliveryManifestAsset.manifest_id == manifest.id)
    )
    asset_rows = assets_result.scalars().all()

    # Load campaign
    campaign = (
        await session.execute(
            select(Campaign).where(Campaign.id == manifest.campaign_id)
        )
    ).scalar_one_or_none()

    # Load device
    device = (
        await session.execute(
            select(PhysicalDevice).where(PhysicalDevice.id == physical_device_id)
        )
    ).scalar_one_or_none()

    # Build manifest JSON
    display_surfaces = []
    for _, surf in surface_rows:
        display_surfaces.append({
            "surface_id": surf.id,
            "surface_code": surf.code,
        })

    playlist = []
    for asset in asset_rows:
        playlist.append({
            "creative_asset_id": asset.creative_asset_id,
            "sha256_checksum": asset.sha256_checksum,
            "duration_ms": asset.duration_ms,
            "media_type": asset.media_type,
        })

    device_code = device.code if device else ""
    device_store_id = device.store_id if device else ""
    store_code = ""
    if device_store_id:
        store = (
            await session.execute(
                select(Store).where(Store.id == device_store_id)
            )
        ).scalar_one_or_none()
        if store:
            store_code = store.code

    # Resolve channel_type from device → device_type → channel
    channel_type = ""
    device_type_code = ""
    if device and device.device_type_id:
        dt = (
            await session.execute(
                select(DeviceType)
                .where(DeviceType.id == device.device_type_id)
            )
        ).scalar_one_or_none()
        if dt:
            device_type_code = dt.code or ""
            ch = (
                await session.execute(
                    select(Channel)
                    .where(Channel.id == dt.channel_id)
                )
            ).scalar_one_or_none()
            if ch:
                channel_type = ch.code or ""

    result = {
        "manifest_id": manifest.manifest_id,
        "manifest_version": manifest.manifest_version,
        "schema_version": "1.0",
        "device_id": physical_device_id,
        "device_code": device_code,
        "store_id": device_store_id,
        "store_code": store_code,
        "channel_type": channel_type,
        "device_type": device_type_code,
        "display_surfaces": display_surfaces,
        "playlist": playlist,
        "media_files": [],
        "adapter_payload": {},
        "valid_from": campaign.start_at.isoformat() if campaign and campaign.start_at else None,
        "valid_to": campaign.end_at.isoformat() if campaign and campaign.end_at else None,
        "offline_ttl_hours": 168,
        "fallback_rules": {
            "on_manifest_expired": "show_fallback",
            "on_network_lost": "continue_last_valid",
            "filler_media_ids": [],
            "emit_pop": False,
        },
        "signature": {
            "algorithm": "HMAC-SHA256",
            "value": "",
        },
        "generated_at": manifest.generated_at.isoformat() if manifest.generated_at else None,
        "content_hash": manifest.content_hash,
    }

    # ── Sign manifest payload for device delivery (S-021 / S-035c) ──
    # sign_manifest_payload already runs during generation (delivery.py:717),
    # but the signature is lost because create_delivery_manifest_record only
    # stores metadata.  Re-sign here so that device-gateway serves a signed
    # manifest when MANIFEST_SIGNING_KEY is configured.
    from packages.domain.delivery import sign_manifest_payload
    from packages.security.config import get_security_config
    signing_key = get_security_config().manifest_signing_key
    if signing_key:
        sig = sign_manifest_payload(result, signing_key)
        result["signature"]["value"] = sig

    return result


# ---------------------------------------------------------------------------
# PoP Persistence (Phase 4.3b — ADR-017)
# ---------------------------------------------------------------------------


async def record_pop_raw_event(
    session: AsyncSession,
    *,
    event_id: str,
    schema_version: str,
    device_id: str,
    manifest_id: str | None,
    campaign_id: str | None,
    campaign_verified: bool,
    creative_asset_id: str,
    surface_id: str,
    rendered_at,
    event_recorded_at,
    duration_ms: int,
    playback_result: str,
    status: str,
    quarantine_reason: str | None = None,
    expires_at=None,
    batch_id: str | None = None,
) -> str:
    """Insert a raw PoP event into pop_events_raw.

    Does NOT commit — caller owns the transaction boundary.
    Does NOT insert into pop_dedup_index — caller must call
    insert_pop_dedup_key in the same transaction.
    Returns the internal row id.
    """
    from packages.domain.models import PopEventRaw
    import uuid

    row_id = str(uuid.uuid4())
    event = PopEventRaw(
        id=row_id,
        event_id=event_id,
        schema_version=schema_version,
        device_id=device_id,
        manifest_id=manifest_id,
        campaign_id=campaign_id,
        campaign_verified=campaign_verified,
        creative_asset_id=creative_asset_id,
        surface_id=surface_id,
        rendered_at=rendered_at,
        event_recorded_at=event_recorded_at,
        duration_ms=duration_ms,
        playback_result=playback_result,
        status=status,
        quarantine_reason=quarantine_reason,
        expires_at=expires_at,
        batch_id=batch_id,
    )
    session.add(event)
    return row_id


async def insert_pop_dedup_key(
    session: AsyncSession,
    event_id: str,
) -> str:
    """Insert a dedup key into pop_dedup_index.

    Does NOT commit — caller owns the transaction boundary.
    Must be called in the same transaction as record_pop_raw_event.
    Returns the event_id.
    """
    from packages.domain.models import PopDedupIndex

    dedup = PopDedupIndex(event_id=event_id)
    session.add(dedup)
    return event_id


async def is_pop_event_duplicate(
    session: AsyncSession,
    event_id: str,
) -> bool:
    """Check if event_id already exists in pop_dedup_index.

    Returns True if duplicate, False if new.
    """
    from sqlalchemy import exists
    from packages.domain.models import PopDedupIndex

    stmt = select(exists().where(PopDedupIndex.event_id == event_id))
    result = await session.execute(stmt)
    return result.scalar() is True


async def accept_pop_event(
    session: AsyncSession,
    *,
    event_id: str,
    schema_version: str,
    device_id: str,
    manifest_id: str,
    campaign_id: str,
    creative_asset_id: str,
    surface_id: str,
    rendered_at,
    event_recorded_at,
    duration_ms: int,
    batch_id: str | None = None,
) -> str:
    """Record an accepted (billing-grade) PoP event.

    Inserts pop_events_raw with status='accepted' + campaign_verified=True
    AND inserts into pop_dedup_index — in caller-owned transaction.
    Caller must commit.
    Returns the internal row id.
    """
    return await record_pop_raw_event(
        session,
        event_id=event_id,
        schema_version=schema_version,
        device_id=device_id,
        manifest_id=manifest_id,
        campaign_id=campaign_id,
        campaign_verified=True,
        creative_asset_id=creative_asset_id,
        surface_id=surface_id,
        rendered_at=rendered_at,
        event_recorded_at=event_recorded_at,
        duration_ms=duration_ms,
        playback_result="success",
        status="accepted",
        batch_id=batch_id,
    )


async def quarantine_pop_event(
    session: AsyncSession,
    *,
    event_id: str,
    schema_version: str,
    device_id: str,
    manifest_id: str | None,
    campaign_id: str | None,
    creative_asset_id: str,
    surface_id: str,
    rendered_at,
    event_recorded_at,
    duration_ms: int,
    playback_result: str,
    quarantine_reason: str,
    expires_at,
    batch_id: str | None = None,
) -> str:
    """Record a quarantined PoP event with campaign_verified=False.

    Inserts pop_events_raw with status='quarantined' + campaign_verified=False
    AND inserts into pop_dedup_index.
    Caller owns the transaction boundary.
    Returns the internal row id.
    """
    return await record_pop_raw_event(
        session,
        event_id=event_id,
        schema_version=schema_version,
        device_id=device_id,
        manifest_id=manifest_id,
        campaign_id=campaign_id,
        campaign_verified=False,
        creative_asset_id=creative_asset_id,
        surface_id=surface_id,
        rendered_at=rendered_at,
        event_recorded_at=event_recorded_at,
        duration_ms=duration_ms,
        playback_result=playback_result,
        status="quarantined",
        quarantine_reason=quarantine_reason,
        expires_at=expires_at,
        batch_id=batch_id,
    )


async def expire_pop_quarantine_events(
    session: AsyncSession,
    *,
    before,
) -> int:
    """Expire quarantine events whose expires_at has passed.

    Sets status='rejected' and quarantine_reason='quarantine_expired'
    for all quarantined events with expires_at < before.
    Caller owns the transaction boundary.
    Returns count of expired events.
    """
    from sqlalchemy import update
    from packages.domain.models import PopEventRaw

    result = await session.execute(
        update(PopEventRaw)
        .where(
            PopEventRaw.status == "quarantined",
            PopEventRaw.expires_at < before,
        )
        .values(
            status="rejected",
            quarantine_reason="quarantine_expired",
        )
    )
    return result.rowcount


# ---------------------------------------------------------------------------
# PoP Reporting Queries (Phase 4.3d — ADR-017 §6)
# ---------------------------------------------------------------------------
# All reporting queries filter:
#   status = 'accepted' AND campaign_verified = true AND playback_result = 'success'
# No quarantined, rejected, duplicate, fallback, or synthetic events count.


async def get_campaign_pop_summary(
    session: AsyncSession,
    campaign_id: str,
) -> dict:
    """Return billing-grade summary for a campaign.

    Returns dict with keys: impressions_count, total_duration_ms,
    first_rendered_at, last_rendered_at, unique_devices, unique_surfaces.
    All numbers are zero/None if no accepted events exist.
    """
    from sqlalchemy import func
    from packages.domain.models import PopEventRaw

    stmt = (
        select(
            func.count().label("impressions_count"),
            func.coalesce(func.sum(PopEventRaw.duration_ms), 0).label("total_duration_ms"),
            func.min(PopEventRaw.rendered_at).label("first_rendered_at"),
            func.max(PopEventRaw.rendered_at).label("last_rendered_at"),
            func.count(func.distinct(PopEventRaw.device_id)).label("unique_devices"),
            func.count(func.distinct(PopEventRaw.surface_id)).label("unique_surfaces"),
        )
        .where(
            PopEventRaw.campaign_id == campaign_id,
            PopEventRaw.status == "accepted",
            PopEventRaw.campaign_verified == True,
            PopEventRaw.playback_result == "success",
        )
    )
    result = await session.execute(stmt)
    row = result.one()
    return {
        "impressions_count": row.impressions_count,
        "total_duration_ms": row.total_duration_ms,
        "first_rendered_at": row.first_rendered_at,
        "last_rendered_at": row.last_rendered_at,
        "unique_devices": row.unique_devices,
        "unique_surfaces": row.unique_surfaces,
    }


async def list_campaign_pop_by_day(
    session: AsyncSession,
    campaign_id: str,
) -> list[dict]:
    """Return daily PoP breakdown for a campaign, grouped by local store day.

    Timezone resolution (S-063):
      1. Store.timezone (via surface → store)
      2. Branch.timezone (via surface → store → cluster → branch)
      3. 'Europe/Moscow' hardcoded default

    All joins are LEFT OUTER — orphaned surface_ids silently fall back
    to the default timezone rather than being dropped from the report.

    Returns list of dicts with: date, impressions_count, total_duration_ms.
    Ordered by date ascending.
    """
    from sqlalchemy import func, cast, Date
    from packages.domain.models import (
        PopEventRaw, DisplaySurface, Store, Cluster, Branch,
    )

    # Coalesce store.tz → branch.tz → Moscow default (trusted DB column, not
    # user input — safe to pass directly to PostgreSQL timezone() function).
    local_tz = func.coalesce(Store.timezone, Branch.timezone, "Europe/Moscow")
    local_date = cast(
        func.timezone(local_tz, PopEventRaw.rendered_at), Date,
    ).label("date")

    stmt = (
        select(
            local_date,
            func.count().label("impressions_count"),
            func.coalesce(func.sum(PopEventRaw.duration_ms), 0).label("total_duration_ms"),
        )
        .select_from(PopEventRaw)
        .outerjoin(DisplaySurface, PopEventRaw.surface_id == DisplaySurface.id)
        .outerjoin(Store, DisplaySurface.store_id == Store.id)
        .outerjoin(Cluster, Store.cluster_id == Cluster.id)
        .outerjoin(Branch, Cluster.branch_id == Branch.id)
        .where(
            PopEventRaw.campaign_id == campaign_id,
            PopEventRaw.status == "accepted",
            PopEventRaw.campaign_verified == True,
            PopEventRaw.playback_result == "success",
        )
        .group_by(local_date)
        .order_by(local_date.asc())
    )
    result = await session.execute(stmt)
    return [
        {
            "date": row.date,
            "impressions_count": row.impressions_count,
            "total_duration_ms": row.total_duration_ms,
        }
        for row in result.fetchall()
    ]


async def list_campaign_pop_by_surface(
    session: AsyncSession,
    campaign_id: str,
) -> list[dict]:
    """Return per-surface PoP breakdown for a campaign.

    Returns list of dicts with: surface_id, impressions_count, total_duration_ms.
    Ordered by impressions_count descending.
    """
    from sqlalchemy import func
    from packages.domain.models import PopEventRaw

    stmt = (
        select(
            PopEventRaw.surface_id,
            func.count().label("impressions_count"),
            func.coalesce(func.sum(PopEventRaw.duration_ms), 0).label("total_duration_ms"),
        )
        .where(
            PopEventRaw.campaign_id == campaign_id,
            PopEventRaw.status == "accepted",
            PopEventRaw.campaign_verified == True,
            PopEventRaw.playback_result == "success",
        )
        .group_by(PopEventRaw.surface_id)
        .order_by(func.count().desc())
    )
    result = await session.execute(stmt)
    return [
        {
            "surface_id": row.surface_id,
            "impressions_count": row.impressions_count,
            "total_duration_ms": row.total_duration_ms,
        }
        for row in result.fetchall()
    ]


# ---------------------------------------------------------------------------
# S-009i — Attach existing creative asset to campaign
# ---------------------------------------------------------------------------


async def attach_creative_to_campaign(
    session: AsyncSession,
    *,
    campaign_id: str,
    creative_asset_id: str,
    sort_order: int = 0,
    scope_advertiser_ids: frozenset[str] | None = None,
) -> CampaignCreative | None:
    """Attach an existing CreativeAsset to a draft Campaign. Returns the link or None.

    Validates:
    - Campaign exists and is in draft status.
    - CreativeAsset exists and belongs to the same advertiser_organization_id.
    - Duplicate attachment → returns existing link (idempotent).

    Raises CrossOrgReferenceError if asset org ≠ campaign org.
    Returns None if campaign not found or not in draft.
    """
    import uuid

    from packages.domain.exceptions import CrossOrgReferenceError
    from packages.domain.models import Campaign, CampaignCreative, CreativeAsset

    campaign = (
        await session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
    ).scalar_one_or_none()
    if campaign is None or campaign.status != "draft":
        return None

    asset = (
        await session.execute(
            select(CreativeAsset).where(CreativeAsset.id == creative_asset_id)
        )
    ).scalar_one_or_none()
    if asset is None:
        return None

    if str(campaign.advertiser_organization_id) != str(asset.advertiser_organization_id):
        raise CrossOrgReferenceError(
            "Creative asset does not belong to the campaign's advertiser organization"
        )

    _assert_org_in_scope(asset.advertiser_organization_id, scope_advertiser_ids)

    # Check for existing link (idempotent)
    existing = (
        await session.execute(
            select(CampaignCreative).where(
                CampaignCreative.campaign_id == campaign_id,
                CampaignCreative.creative_asset_id == creative_asset_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    link_id = str(uuid.uuid4())
    link = CampaignCreative(
        id=link_id,
        campaign_id=campaign_id,
        creative_asset_id=creative_asset_id,
        sort_order=sort_order,
    )
    session.add(link)
    return link


# ---------------------------------------------------------------------------
# Creative Upload Sessions (S-017)
# ---------------------------------------------------------------------------


async def create_upload_session(
    session: AsyncSession,
    *,
    creative_asset_id: str,
    advertiser_organization_id: str,
    storage_bucket: str,
    storage_key: str,
    filename: str,
    content_type: str,
    content_length: int,
    created_by: str | None = None,
    ttl_seconds: int = 300,
) -> str:
    """Create a creative_upload_sessions row. Returns session id."""
    import uuid as _uuid
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    from packages.domain.models import CreativeUploadSession

    now = _dt.now(_tz.utc)
    row = CreativeUploadSession(
        id=str(_uuid.uuid4()),
        creative_asset_id=creative_asset_id,
        advertiser_organization_id=advertiser_organization_id,
        storage_bucket=storage_bucket,
        storage_key=storage_key,
        filename=filename,
        content_type=content_type,
        content_length=content_length,
        expires_at=now + _td(seconds=ttl_seconds),
        created_by=created_by,
        created_at=now,
    )
    session.add(row)
    await session.flush()
    return row.id


async def get_upload_session(
    session: AsyncSession,
    upload_id: str,
):
    """Return upload session as dict or None."""
    from packages.domain.models import CreativeUploadSession
    result = await session.execute(
        select(CreativeUploadSession).where(
            CreativeUploadSession.id == upload_id,
        ),
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return {
        "id": row.id,
        "creative_asset_id": row.creative_asset_id,
        "advertiser_organization_id": row.advertiser_organization_id,
        "storage_bucket": row.storage_bucket,
        "storage_key": row.storage_key,
        "filename": row.filename,
        "content_type": row.content_type,
        "content_length": row.content_length,
        "expires_at": row.expires_at,
        "completed_at": row.completed_at,
        "created_by": row.created_by,
    }


async def mark_upload_complete(
    session: AsyncSession,
    upload_id: str,
) -> bool:
    """Mark upload session completed. Returns True on success."""
    from datetime import datetime as _dt, timezone as _tz
    from packages.domain.models import CreativeUploadSession
    from sqlalchemy import update as sa_update

    result = await session.execute(
        sa_update(CreativeUploadSession)
        .where(
            CreativeUploadSession.id == upload_id,
            CreativeUploadSession.completed_at.is_(None),
        )
        .values(completed_at=_dt.now(_tz.utc))
    )
    return result.rowcount > 0


async def mark_asset_uploaded(
    session: AsyncSession,
    *,
    asset_id: str,
    storage_bucket: str,
    storage_key: str,
    sha256_checksum: str,
    file_size_bytes: int,
    moderation_status: str = "approved",
) -> bool:
    """Update CreativeAsset after upload. Returns True on success."""
    from datetime import datetime as _dt, timezone as _tz
    from packages.domain.models import CreativeAsset
    from sqlalchemy import update as sa_update

    result = await session.execute(
        sa_update(CreativeAsset)
        .where(
            CreativeAsset.id == asset_id,
            CreativeAsset.status == "metadata_only",
        )
        .values(
            status="ready",
            moderation_status=moderation_status,
            storage_bucket=storage_bucket,
            storage_key=storage_key,
            sha256_checksum=sha256_checksum,
            file_size_bytes=file_size_bytes,
            updated_at=_dt.now(_tz.utc),
        )
    )
    return result.rowcount > 0


# ---------------------------------------------------------------------------
# S-033 — Admin User Management Repository
# ---------------------------------------------------------------------------


async def get_user_detail(session: AsyncSession, user_id: str) -> User | None:
    """Get user with eager-loaded roles and credentials."""
    from sqlalchemy.orm import selectinload

    stmt = (
        select(User)
        .options(
            selectinload(User.roles).selectinload(UserRole.role),
        )
        .where(User.id == user_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_local_credential(
    session: AsyncSession, user_id: str
) -> LocalCredential | None:
    """Get local_credentials row for a user."""
    stmt = select(LocalCredential).where(LocalCredential.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def find_user_by_username(
    session: AsyncSession, username: str
) -> User | None:
    """Find user by exact username."""
    stmt = select(User).where(User.username == username)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_local_advertiser_user(
    session: AsyncSession,
    *,
    user_id: str,
    code: str,
    username: str,
    display_name: str,
    password_hash: str,
    advertiser_organization_id: str,
    role_id: str,
    must_change_password: bool = True,
    is_active: bool = True,
) -> User:
    """Create user + local_credentials + scoped role + advertiser membership."""
    from datetime import timezone

    now = datetime.now(timezone.utc)
    status = "active" if is_active else "inactive"

    # 1. Create User — flush immediately so FK references resolve
    user = User(
        id=user_id,
        code=code,
        username=username,
        display_name=display_name,
        auth_provider="local_advertiser",
        status=status,
        is_break_glass=False,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.flush()

    # 2. Create LocalCredential
    cred = LocalCredential(
        id=str(uuid.uuid4()),
        user_id=user_id,
        credential_type="local_advertiser",
        password_hash=password_hash,
        password_hash_algorithm="bcrypt",
        password_changed_at=now,
        must_change_password=must_change_password,
        status=status,
        created_at=now,
        updated_at=now,
    )
    session.add(cred)

    # 3. Assign scoped advertiser role
    user_role = UserRole(
        id=str(uuid.uuid4()),
        user_id=user_id,
        role_id=role_id,
        scope_type="advertiser",
        scope_id=advertiser_organization_id,
        created_at=now,
    )
    session.add(user_role)

    # 4. Create advertiser_user_membership
    membership = AdvertiserUserMembership(
        id=str(uuid.uuid4()),
        user_id=user_id,
        advertiser_organization_id=advertiser_organization_id,
        status="active",
        created_at=now,
    )
    session.add(membership)

    await session.flush()
    return user


async def count_active_break_glass_users(session: AsyncSession) -> int:
    """Count users with is_break_glass=True and status='active'."""
    stmt = (
        select(func.count())
        .select_from(User)
        .where(
            User.is_break_glass == True,
            User.status == "active",
        )
    )
    result = await session.execute(stmt)
    return result.scalar() or 0


async def count_active_admin_users(session: AsyncSession) -> int:
    """Count users with system_admin role and status='active' (approximate)."""
    stmt = (
        select(func.count())
        .select_from(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            User.status == "active",
            Role.code == "system_admin",
        )
    )
    result = await session.execute(stmt)
    return result.scalar() or 0


async def set_user_status(
    session: AsyncSession, user_id: str, status: str
) -> bool:
    """Set user.status to the given value. Returns True if row was updated."""
    from datetime import timezone

    result = await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(status=status, updated_at=datetime.now(timezone.utc))
    )
    return result.rowcount > 0


async def update_local_credential_password(
    session: AsyncSession, user_id: str, password_hash: str
) -> bool:
    """Update password_hash + must_change_password + password_changed_at."""
    from datetime import timezone

    now = datetime.now(timezone.utc)
    result = await session.execute(
        update(LocalCredential)
        .where(LocalCredential.user_id == user_id)
        .values(
            password_hash=password_hash,
            must_change_password=True,
            password_changed_at=now,
            updated_at=now,
        )
    )
    return result.rowcount > 0


# ---------------------------------------------------------------------------
# S-070 — Fleet / Device Health
# ---------------------------------------------------------------------------


async def list_devices(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
) -> tuple[list["PhysicalDevice"], int]:
    """Return paginated physical devices (newest first), with optional status filter."""
    from packages.domain.models import PhysicalDevice

    base = select(func.count()).select_from(PhysicalDevice)
    if status is not None:
        base = base.where(PhysicalDevice.status == status)
    total = await session.scalar(base)

    stmt = (
        select(PhysicalDevice)
        .order_by(PhysicalDevice.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status is not None:
        stmt = stmt.where(PhysicalDevice.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all()), total or 0


async def get_device(session: AsyncSession, device_id: str) -> "PhysicalDevice | None":
    """Get a single device by id."""
    from packages.domain.models import PhysicalDevice

    stmt = select(PhysicalDevice).where(PhysicalDevice.id == device_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_device_summary(session: AsyncSession) -> dict[str, int]:
    """Return fleet health summary counts."""
    from packages.domain.models import PhysicalDevice

    total = await session.scalar(select(func.count()).select_from(PhysicalDevice))
    active = await session.scalar(
        select(func.count()).select_from(PhysicalDevice).where(PhysicalDevice.status == "active")
    )
    inactive = await session.scalar(
        select(func.count()).select_from(PhysicalDevice).where(PhysicalDevice.status == "inactive")
    )
    error = await session.scalar(
        select(func.count()).select_from(PhysicalDevice).where(PhysicalDevice.status == "error")
    )
    unregistered = await session.scalar(
        select(func.count()).select_from(PhysicalDevice).where(PhysicalDevice.status == "unregistered")
    )
    return {
        "total": total or 0,
        "active": active or 0,
        "inactive": inactive or 0,
        "error": error or 0,
        "unregistered": unregistered or 0,
    }


# ---------------------------------------------------------------------------
# S-071 — Emergency Override
# ---------------------------------------------------------------------------


async def get_active_emergency_override(session: AsyncSession) -> "EmergencyOverride | None":
    """Get the currently active global emergency override, or None."""
    from packages.domain.models import EmergencyOverride

    stmt = (
        select(EmergencyOverride)
        .where(EmergencyOverride.level == "global")
        .where(EmergencyOverride.active.is_(True))
        .order_by(EmergencyOverride.activated_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def activate_emergency_override(
    session: AsyncSession,
    *,
    reason: str,
    activated_by: str,
) -> "EmergencyOverride":
    """Activate global emergency mode. Raises ValueError if already active."""
    from packages.domain.models import EmergencyOverride
    from datetime import timezone

    existing = await get_active_emergency_override(session)
    if existing:
        raise ValueError("Emergency mode is already active")

    override = EmergencyOverride(
        level="global",
        active=True,
        reason=reason,
        activated_by=activated_by,
        activated_at=datetime.now(timezone.utc),
    )
    session.add(override)
    return override


async def deactivate_emergency_override(
    session: AsyncSession,
    *,
    reason: str,
    deactivated_by: str,
) -> "EmergencyOverride":
    """Deactivate the active global emergency mode. Raises ValueError if not active."""
    from datetime import timezone

    existing = await get_active_emergency_override(session)
    if not existing:
        raise ValueError("No active emergency mode to deactivate")

    existing.active = False
    existing.deactivated_by = deactivated_by
    existing.deactivated_at = datetime.now(timezone.utc)
    existing.deactivated_reason = reason


# ---------------------------------------------------------------------------
# Inventory Domain (v0.7 Foundation — S-077)
# ---------------------------------------------------------------------------


# --- InventorySlot ---

async def get_or_create_inventory_slot(
    session: AsyncSession,
    *,
    display_surface_id: str,
    slot_date,
    slot_hour: int,
    total_capacity: int = 0,
) -> InventorySlot:
    """Return existing slot or create a new one (idempotent)."""
    from sqlalchemy import select as sa_select

    stmt = sa_select(InventorySlot).where(
        InventorySlot.display_surface_id == display_surface_id,
        InventorySlot.slot_date == slot_date,
        InventorySlot.slot_hour == slot_hour,
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is not None:
        return row
    slot = InventorySlot(
        display_surface_id=display_surface_id,
        slot_date=slot_date,
        slot_hour=slot_hour,
        total_capacity=total_capacity,
    )
    session.add(slot)
    return slot


async def list_inventory_slots(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    surface_id: str | None = None,
    slot_date=None,
) -> tuple[list[InventorySlot], int]:
    """Paginated list of inventory slots, optionally filtered."""
    from sqlalchemy import select as sa_select

    base = sa_select(InventorySlot)
    count_base = sa_select(func.count()).select_from(InventorySlot)

    if surface_id is not None:
        base = base.where(InventorySlot.display_surface_id == surface_id)
        count_base = count_base.where(InventorySlot.display_surface_id == surface_id)
    if slot_date is not None:
        base = base.where(InventorySlot.slot_date == slot_date)
        count_base = count_base.where(InventorySlot.slot_date == slot_date)

    base = base.order_by(InventorySlot.slot_date, InventorySlot.slot_hour).limit(limit).offset(offset)
    total = await session.scalar(count_base)
    result = await session.execute(base)
    return list(result.scalars().all()), total or 0


async def get_inventory_slot(
    session: AsyncSession, slot_id: str,
) -> InventorySlot | None:
    """Get a single slot by ID."""
    return await session.get(InventorySlot, slot_id)


# --- InventoryBooking ---

async def create_inventory_booking(
    session: AsyncSession,
    *,
    campaign_id: str | None = None,
    campaign_placement_id: str | None = None,
    inventory_slot_id: str,
    capacity_units: int,
    reserved_until=None,
) -> InventoryBooking:
    """Create a new booking (reserve). Caller must handle idempotency."""
    if capacity_units <= 0:
        raise ValueError("capacity_units must be > 0")
    booking = InventoryBooking(
        campaign_id=campaign_id,
        campaign_placement_id=campaign_placement_id,
        inventory_slot_id=inventory_slot_id,
        capacity_units=capacity_units,
        status="reserved",
        reserved_until=reserved_until,
    )
    session.add(booking)
    return booking


async def list_inventory_bookings(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    slot_id: str | None = None,
    status: str | None = None,
) -> tuple[list[InventoryBooking], int]:
    """Paginated list of bookings, optionally filtered."""
    from sqlalchemy import select as sa_select

    base = sa_select(InventoryBooking)
    count_base = sa_select(func.count()).select_from(InventoryBooking)

    if slot_id is not None:
        base = base.where(InventoryBooking.inventory_slot_id == slot_id)
        count_base = count_base.where(InventoryBooking.inventory_slot_id == slot_id)
    if status is not None:
        base = base.where(InventoryBooking.status == status)
        count_base = count_base.where(InventoryBooking.status == status)

    base = base.order_by(InventoryBooking.created_at.desc()).limit(limit).offset(offset)
    total = await session.scalar(count_base)
    result = await session.execute(base)
    return list(result.scalars().all()), total or 0


async def get_inventory_booking(
    session: AsyncSession, booking_id: str,
) -> InventoryBooking | None:
    """Get a single booking by ID."""
    return await session.get(InventoryBooking, booking_id)


# --- InventoryRule ---

async def create_inventory_rule(
    session: AsyncSession,
    *,
    scope_type: str = "global",
    scope_id: str | None = None,
    rule_type: str,
    priority: int = 100,
    value_json: dict | None = None,
    is_active: bool = True,
    starts_at=None,
    ends_at=None,
) -> InventoryRule:
    """Create a new inventory rule."""
    rule = InventoryRule(
        scope_type=scope_type,
        scope_id=scope_id,
        rule_type=rule_type,
        priority=priority,
        value_json=value_json or {},
        is_active=is_active,
        starts_at=starts_at,
        ends_at=ends_at,
    )
    session.add(rule)
    return rule


async def list_inventory_rules(
    session: AsyncSession,
    *,
    is_active: bool | None = None,
    rule_type: str | None = None,
) -> list[InventoryRule]:
    """List inventory rules, optionally filtered."""
    from sqlalchemy import select as sa_select

    stmt = sa_select(InventoryRule).order_by(InventoryRule.priority.desc())
    if is_active is not None:
        stmt = stmt.where(InventoryRule.is_active == is_active)
    if rule_type is not None:
        stmt = stmt.where(InventoryRule.rule_type == rule_type)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_inventory_rule(
    session: AsyncSession, rule_id: str,
) -> InventoryRule | None:
    """Get a single rule by ID."""
    return await session.get(InventoryRule, rule_id)


async def set_inventory_rule_active(
    session: AsyncSession,
    *,
    rule_id: str,
    is_active: bool,
) -> InventoryRule | None:
    """Toggle is_active on an inventory rule."""
    rule = await session.get(InventoryRule, rule_id)
    if rule is None:
        return None
    rule.is_active = is_active
    return rule
