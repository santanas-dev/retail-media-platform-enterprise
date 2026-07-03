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
