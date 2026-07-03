"""
Retail Media Platform — API Dependencies.

Phase 3.0: Database session dependency.
Phase 3.2d: Auth service factory, token extraction, current-user dependency.

TODO(auth): Add JWT/SSO auth dependency when identity is implemented.
All endpoints are currently unprotected — open for development.
"""

from fastapi import Depends, HTTPException, Request

from packages.auth.service import AuthService
from packages.domain.database import get_global_engine, get_session
from packages.security.config import get_security_config
from packages.security.jwt import verify_access_token


async def get_db():
    """Yield an async SQLAlchemy session, auto-close on exit."""
    engine = get_global_engine()
    async with get_session(engine) as session:
        yield session


def get_auth_service() -> AuthService:
    """Factory for AuthService — uses StubADAuthProvider by default."""
    return AuthService()


async def get_refresh_token(request: Request) -> str | None:
    """Extract refresh token from HttpOnly cookie."""
    cfg = get_security_config()
    return request.cookies.get(cfg.refresh_token_cookie_name)


async def get_access_token(request: Request) -> str | None:
    """Extract access token from Authorization: Bearer header."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


async def get_current_user(
    access_token: str | None = Depends(get_access_token),
) -> dict:
    """Require a valid JWT access token — returns decoded claims.

    Raises HTTPException(401) on missing, expired, or invalid token.
    Does not perform DB/RBAC lookups yet.
    """
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail={"code": "NOT_AUTHENTICATED", "message": "Missing Authorization header"},
        )
    try:
        claims = verify_access_token(access_token)
    except __import__("jwt").ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"code": "TOKEN_EXPIRED", "message": "Access token has expired"},
        )
    except __import__("jwt").InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_TOKEN", "message": "Invalid access token"},
        )
    return claims
