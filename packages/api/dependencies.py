"""
Retail Media Platform - API Dependencies.

Phase 3.0: Database session dependency.
Phase 3.2d: Auth service factory, token extraction, current-user dependency.
Phase 3.3: Active-user dependency, permission-gated dependency factory.
"""

from jwt import ExpiredSignatureError, InvalidTokenError

from fastapi import Depends, HTTPException, Request

from packages.auth.service import AuthService
from packages.domain import repository
from packages.domain.database import get_global_engine, get_session
from packages.domain.scopes import ScopeContext, resolve_scope_context
from packages.security.config import get_security_config
from packages.security.jwt import verify_access_token


async def get_db():
    """Yield an async SQLAlchemy session, auto-close on exit."""
    engine = get_global_engine()
    async with get_session(engine) as session:
        async with session.begin():
            yield session


def get_auth_service() -> AuthService:
    """Factory for AuthService - uses StubADAuthProvider by default."""
    return AuthService()


async def get_refresh_token(request: Request) -> str | None:
    """Extract refresh token from HttpOnly cookie."""
    cfg = get_security_config()
    return request.cookies.get(cfg.refresh_token_cookie_name)


async def get_access_token(request: Request) -> str | None:
    """Extract access token from the Authorization header."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


async def get_current_user(
    access_token: str | None = Depends(get_access_token),
) -> dict:
    """Require a valid JWT access token - returns decoded claims.

    Raises HTTPException(401) on missing, expired, or invalid token.
    Used as the foundation for RBAC-enforcing dependencies.
    """
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail={"code": "NOT_AUTHENTICATED", "message": "Missing Authorization header"},
        )
    try:
        claims = verify_access_token(access_token)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"code": "TOKEN_EXPIRED", "message": "Access token has expired"},
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_TOKEN", "message": "Invalid access token"},
        )
    return claims


# ---------------------------------------------------------------------------
# Phase 3.3 - RBAC-enforcing dependencies
# ---------------------------------------------------------------------------


async def get_current_active_user(
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
) -> dict:
    """Validate JWT + load user from DB, verify active status.

    Returns enriched claims dict with keys:
      sub, auth_provider, user_status

    Raises HTTPException(403) if user is deactivated/disabled.
    Raises HTTPException(401) if user not found in DB.
    """
    user = await repository.find_user_by_id(db, claims["sub"])
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "USER_NOT_FOUND", "message": "User no longer exists"},
        )
    if user.status != "active":
        raise HTTPException(
            status_code=403,
            detail={"code": "USER_DISABLED", "message": "User account is disabled"},
        )
    return {**claims, "user_status": user.status}


def require_permission(permission_code: str):
    """Factory: return a FastAPI dependency that enforces a specific permission.

    Uses get_current_active_user (JWT + active user check), then loads
    the user's permissions via their roles and verifies the required
    permission is present.

    Returns 403 if authenticated but missing the permission.
    Deny by default - no permission -> 403.
    """

    async def enforce(
        claims: dict = Depends(get_current_active_user),
        db=Depends(get_db),
    ) -> dict:
        perms = await repository.get_user_permissions(db, claims["sub"])
        if permission_code not in perms:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "PERMISSION_DENIED",
                    "message": f"Missing required permission: {permission_code}",
                },
            )
        return claims

    return enforce


# ---------------------------------------------------------------------------
# Phase 3.5b - Scope + RLS dependencies
# ---------------------------------------------------------------------------


async def get_scope_context(
    claims: dict = Depends(get_current_active_user),
    db=Depends(get_db),
) -> ScopeContext:
    """Resolve the current user's effective scopes from the database.

    Uses the same transaction as get_db() (session.begin is already
    active).  Returns ScopeContext.deny_all() for disabled users.
    """
    return await resolve_scope_context(db, claims["sub"])


async def set_rls_context(
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
) -> None:
    """Apply RLS session variables so tenant queries are filtered.

    Must execute AFTER the transaction starts (get_db) and AFTER
    scope resolution (get_scope_context).  Wired as a router-level
    dependency on tenant-scoped routers.
    """
    from sqlalchemy import text

    is_admin = "true" if scope.is_admin else "false"
    advertiser_csv = ",".join(sorted(scope.advertiser_scope_ids)) if scope.advertiser_scope_ids else ""

    await db.execute(text("SELECT set_config('app.rmp_user_id', :uid, true)"), {"uid": scope.user_id})
    await db.execute(text("SELECT set_config('app.rmp_is_admin', :a, true)"), {"a": is_admin})
    await db.execute(text("SELECT set_config('app.rmp_scope_advertiser_ids', :ids, true)"),
                     {"ids": advertiser_csv})


# ---------------------------------------------------------------------------
# Phase 3.5c - Scoped permission enforcement
# ---------------------------------------------------------------------------


def require_scoped_permission(permission_code: str, scope_type: str | None = None):
    """Factory: FastAPI dependency enforcing permission + optional scope.

    Combines ``require_permission`` semantics with ``ScopeContext``:
    - Global permission (unscoped role) → pass
    - Admin (unscoped system_admin/security_admin with the permission) → pass
    - Scoped access: if ``scope_type`` is specified, the user must have
      scope IDs for that type (e.g. advertiser_scope_ids for ``advertiser``).
      RLS handles which specific rows are visible.
    - Empty scopes → 403 SCOPE_RESTRICTED
    - No permission and no matching scope → 403 PERMISSION_DENIED
    - Scoped admin (system_admin with branch scope) is NOT a global admin
    """

    async def enforce(
        db=Depends(get_db),
        scope: ScopeContext = Depends(get_scope_context),
    ) -> ScopeContext:
        # 1. Admin bypass — unscoped admin with the permission
        if scope.is_admin and permission_code in scope.global_permissions:
            return scope

        # 2. Global permission — user has the perm from an unscoped role
        if permission_code in scope.global_permissions:
            return scope

        # 3. Scoped access — user has scope IDs AND the permission
        if scope_type == "advertiser":
            if scope.advertiser_scope_ids and permission_code in scope.all_permissions:
                return scope
            # Has scopes but missing the permission
            if scope.advertiser_scope_ids:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "code": "PERMISSION_DENIED",
                        "message": f"Missing required permission: {permission_code}",
                    },
                )
            # Scope type required but user has no scope IDs
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "SCOPE_RESTRICTED",
                    "message": f"Access requires {scope_type} scope",
                },
            )

        # 4. Scope type specified but not advertiser (branch, cluster, store deferred)
        if scope_type is not None:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "SCOPE_RESTRICTED",
                    "message": f"Access requires {scope_type} scope",
                },
            )

        # 5. No permission at all
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PERMISSION_DENIED",
                "message": f"Missing required permission: {permission_code}",
            },
        )

    return enforce


# ---------------------------------------------------------------------------
# Phase 4.3c — Device JWT auth for PoP ingestion
# ---------------------------------------------------------------------------


async def get_device_id_from_token(request: Request) -> str:
    """Extract physical_device_id from Authorization: Bearer ***    ADR-003/ADR-017: device JWT has sub=<device_id>, auth_provider="device".
    Rejects user/admin tokens, expired/invalid tokens.
    Returns physical_device_id (UUID string).
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"code": "NOT_AUTHENTICATED", "message": "Missing or invalid Authorization header"},
        )
    token = auth[7:]
    try:
        claims = verify_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired device token"},
        )
    if claims.get("auth_provider") != "device":
        raise HTTPException(
            status_code=403,
            detail={"code": "NOT_DEVICE_TOKEN", "message": "Token is not a device token"},
        )
    device_id = claims.get("sub")
    if not device_id:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_TOKEN", "message": "Token missing sub claim"},
        )
    return device_id


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

from dataclasses import dataclass
from packages.domain.schemas import DEFAULT_LIMIT, MAX_LIMIT


@dataclass
class PaginationParams:
    """Validated pagination parameters extracted from query string."""
    limit: int
    offset: int


async def get_pagination_params(
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> PaginationParams:
    """FastAPI dependency — extract and validate limit/offset from query params.

    Enforces: limit between 1 and MAX_LIMIT, offset >= 0.
    Returns PaginationParams dataclass.
    """
    if limit < 1:
        limit = 1
    if limit > MAX_LIMIT:
        limit = MAX_LIMIT
    if offset < 0:
        offset = 0
    return PaginationParams(limit=limit, offset=offset)
