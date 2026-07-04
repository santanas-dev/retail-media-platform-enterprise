"""
Retail Media Platform — Scope Resolution (Phase 3.5b).

Resolves a user's effective scopes from user_roles, role_permissions,
and advertiser_user_memberships.  Empty scopes = deny-all.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.domain.models import (
    AdvertiserUserMembership,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)

# Role codes that are considered "admin" when unscoped
ADMIN_ROLE_CODES = frozenset({"system_admin", "security_admin"})


@dataclass
class ScopeContext:
    """Resolved scopes for the current request.

    * ``is_admin`` is True ONLY for unscoped system_admin / security_admin.
    * ``global_permissions`` come from unscoped role assignments.
    * ``all_permissions`` is the union of permission codes from scoped
      AND unscoped roles.  Used only in scoped guard checks (never
      grants global access — see require_scoped_permission).
    * ``advertiser_scope_ids`` come from advertiser_user_memberships
      and scoped user_roles with scope_type='advertiser'.
    * ``role_codes`` is the set of role codes assigned to the user
      (for permission checks).

    Empty scopes with zero advertiser_scope_ids and no global permissions
    means deny-all.
    """

    user_id: str
    is_admin: bool = False
    role_codes: set[str] = field(default_factory=set)
    global_permissions: set[str] = field(default_factory=set)
    advertiser_scope_ids: set[str] = field(default_factory=set)
    all_permissions: set[str] = field(default_factory=set)

    def __bool__(self) -> bool:
        """False for deny-all (empty scopes, not admin)."""
        return self.is_admin or bool(self.global_permissions) or bool(self.advertiser_scope_ids)

    @classmethod
    def deny_all(cls, user_id: str = "") -> ScopeContext:
        """Return a context that denies everything."""
        return cls(user_id=user_id)

    @classmethod
    def admin(cls, user_id: str, permissions: set[str] | None = None) -> ScopeContext:
        """Return an admin context with all given permissions."""
        perms = permissions or set()
        return cls(
            user_id=user_id,
            is_admin=True,
            role_codes={"system_admin"},
            global_permissions=perms,
            all_permissions=perms,
        )


async def resolve_scope_context(
    session: AsyncSession, user_id: str,
) -> ScopeContext:
    """Resolve effective scopes for *user_id* from the database.

    Returns ``ScopeContext.deny_all()`` if the user is not found
    or inactive.

    Uses the raw connection to SET LOCAL before queries so RLS
    does not block visibility into advertiser_user_memberships
    (this resolver runs before set_rls_context in the dep chain).
    """
    from sqlalchemy import text

    # Bypass RLS for scope resolution: this needs to read
    # advertiser_user_memberships which is RLS-protected, but
    # the RLS context hasn't been set yet (circular dep).
    conn = await session.connection()
    await conn.execute(
        text("SELECT set_config('app.rmp_is_admin', 'true', true)")
    )

    # Verify user exists and is active
    user = await _get_user(session, user_id)
    if user is None or user.status != "active":
        return ScopeContext.deny_all(user_id)

    # Load role codes + permissions (scoped and unscoped)
    role_rows = await _load_user_roles(session, user_id)
    if not role_rows:
        return ScopeContext.deny_all(user_id)

    is_admin = False
    role_codes: set[str] = set()
    global_permissions: set[str] = set()
    all_permissions: set[str] = set()
    advertiser_scope_ids: set[str] = set()

    for ur in role_rows:
        scope_type = ur.scope_type  # None = unscoped
        perm_code = ur.perm_code
        role_code = ur.role_code

        role_codes.add(role_code)

        if perm_code is not None:
            all_permissions.add(perm_code)

        if scope_type is None:
            # Unscoped role → global permissions
            if perm_code is not None:
                global_permissions.add(perm_code)
            if role_code in ADMIN_ROLE_CODES:
                is_admin = True
        elif scope_type == "advertiser" and ur.scope_id:
            advertiser_scope_ids.add(ur.scope_id)
        # Other scope types (branch, cluster, store) are deferred to
        # future hierarchy expansion phases

    # Also load advertiser memberships (direct user→org link)
    membership_ids = await _load_advertiser_memberships(session, user_id)
    advertiser_scope_ids.update(membership_ids)

    return ScopeContext(
        user_id=user_id,
        is_admin=is_admin,
        role_codes=role_codes,
        global_permissions=global_permissions,
        all_permissions=all_permissions,
        advertiser_scope_ids=advertiser_scope_ids,
    )


# ---------------------------------------------------------------------------
# Internal queries
# ---------------------------------------------------------------------------


async def _get_user(session: AsyncSession, user_id: str) -> User | None:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_user_roles(session: AsyncSession, user_id: str):
    """Return rows with (scope_type, scope_id, role_code, perm_code).

    Uses LEFT JOIN so roles without permissions still appear.
    """
    stmt = (
        select(
            UserRole.scope_type,
            UserRole.scope_id,
            Role.code.label("role_code"),
            Permission.code.label("perm_code"),
        )
        .join(Role, Role.id == UserRole.role_id)
        .outerjoin(RolePermission, RolePermission.role_id == Role.id)
        .outerjoin(Permission, Permission.id == RolePermission.permission_id)
        .where(UserRole.user_id == user_id)
    )
    result = await session.execute(stmt)
    return result.fetchall()


async def _load_advertiser_memberships(
    session: AsyncSession, user_id: str,
) -> set[str]:
    """Return advertiser_organization_ids from direct memberships."""
    stmt = select(AdvertiserUserMembership.advertiser_organization_id).where(
        AdvertiserUserMembership.user_id == user_id,
        AdvertiserUserMembership.status == "active",
    )
    result = await session.execute(stmt)
    return {row[0] for row in result.fetchall()}
