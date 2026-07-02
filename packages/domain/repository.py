"""
Retail Media Platform — Async Repository Helpers.

Phase 3.0: Read-only query functions for identity/RBAC tables.
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from packages.domain.models import (
    AuditEventOperational,
    Permission,
    Role,
    User,
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
