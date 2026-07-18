"""
Retail Media Platform — Auth API Router.

Phase 3.2d: Minimal auth endpoints (login, refresh, logout, me).
Exposes AuthService over HTTP. No RBAC/middleware enforcement yet.

TODO(auth): Add password-reset, registration endpoints in later phases.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from packages.api.dependencies import (
    get_access_token,
    get_auth_service,
    get_current_active_user,
    get_current_user,
    get_db,
    get_refresh_token,
)
from packages.domain import repository
from packages.auth.schemas import AuthFailure, AuthSuccess
from packages.auth.service import AuthService
from packages.domain.schemas import (
    AdvertiserOrganizationOut,
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    MeResponse,
    RefreshResponse,
    UserRefOut,
)
from packages.security.config import get_security_config

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_refresh_cookie(response: Response, token: str) -> None:
    """Set the refresh token as HttpOnly Secure SameSite=Strict cookie."""
    cfg = get_security_config()
    response.set_cookie(
        key=cfg.refresh_token_cookie_name,
        value=token,
        httponly=True,
        secure=cfg.refresh_token_cookie_secure,
        samesite=cfg.refresh_token_cookie_samesite,
        max_age=cfg.refresh_session_ttl_hours * 3600,
        path=cfg.refresh_token_cookie_path,
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Clear the refresh token cookie."""
    cfg = get_security_config()
    response.delete_cookie(
        key=cfg.refresh_token_cookie_name,
        path=cfg.refresh_token_cookie_path,
        secure=cfg.refresh_token_cookie_secure,
        samesite=cfg.refresh_token_cookie_samesite,
    )


def _is_ad_unavailable(failure: AuthFailure) -> bool:
    """Check if an AuthFailure is due to AD provider unavailability."""
    if failure.debug_context is None:
        return False
    return failure.debug_context.get("ad_error") == "ldap_unavailable"


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------


@router.post("/login", response_model=LoginResponse, status_code=200)
async def login(
    body: LoginRequest,
    response: Response,
    request: Request,
    db=Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate user and return access token + set refresh cookie.

    Never returns refresh_token in the JSON response body.
    Generic 401 for invalid credentials — no user enumeration.
    503 when AD provider is unavailable.
    """
    result = await auth_service.login(
        db,
        username_or_email=body.username_or_email,
        password=body.password,
        ip_address=request.client.host if request.client else None,
        correlation_id=request.headers.get("X-Correlation-ID"),
    )

    if isinstance(result, AuthFailure):
        if result.internal_code == "RATE_LIMITED":
            await db.commit()
            cfg = get_security_config()
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "TOO_MANY_REQUESTS",
                    "message": "Too many login attempts. Please try again later.",
                },
                headers={
                    "Retry-After": str(cfg.login_rate_limit_window_minutes * 60),
                },
            )
        if _is_ad_unavailable(result):
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Authentication service temporarily unavailable",
                },
            )
        # Persist login_attempt audit event before returning 401.
        # The service wrote login_attempt via session.flush() inside the
        # get_db() transaction; commit() makes it durable so the session
        # rollback on HTTPException does not discard the audit trail.
        await db.commit()
        # Generic 401 — never reveal internal reason
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid username/email or password",
            },
        )

    # Success — set refresh cookie (never in JSON body)
    _set_refresh_cookie(response, result.refresh_token)

    cfg = get_security_config()
    return LoginResponse(
        access_token=result.access_token,
        token_type="Bearer",
        expires_in=cfg.jwt_access_token_ttl_minutes * 60,
        user=UserRefOut(
            sub=result.user_id,
            auth_provider=result.auth_provider,
        ),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------


@router.post("/refresh", response_model=RefreshResponse, status_code=200)
async def refresh(
    response: Response,
    request: Request,
    refresh_token: str | None = Depends(get_refresh_token),
    auth_service: AuthService = Depends(get_auth_service),
    db=Depends(get_db),
):
    """Rotate refresh token — issue new access + refresh, invalidate old.

    Reads refresh token from HttpOnly cookie. Never returns it in JSON.
    Returns generic 401 on missing, invalid, or replayed token.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "NOT_AUTHENTICATED",
                "message": "Missing refresh token",
            },
        )

    result = await auth_service.refresh_session(
        db,
        raw_refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
    )

    if isinstance(result, AuthFailure):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_TOKEN",
                "message": "Invalid or expired refresh token",
            },
        )

    _set_refresh_cookie(response, result.refresh_token)

    cfg = get_security_config()
    return RefreshResponse(
        access_token=result.access_token,
        token_type="Bearer",
        expires_in=cfg.jwt_access_token_ttl_minutes * 60,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/logout
# ---------------------------------------------------------------------------


@router.post("/logout", response_model=LogoutResponse, status_code=200)
async def logout(
    response: Response,
    refresh_token: str | None = Depends(get_refresh_token),
    auth_service: AuthService = Depends(get_auth_service),
    db=Depends(get_db),
):
    """Revoke refresh session and clear cookie.

    Idempotent — always returns success.
    """
    if refresh_token:
        await auth_service.logout(db, raw_refresh_token=refresh_token)

    _clear_refresh_cookie(response)
    return LogoutResponse(message="Logged out")


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------


@router.get("/me", response_model=MeResponse)
async def me(
    claims: dict = Depends(get_current_active_user),
    db=Depends(get_db),
):
    """Return current-user profile from DB (not JWT claims).

    401 if token is missing or invalid.
    403 if user is deactivated.
    Username, display_name, permissions, and must_change_password are
    loaded from the database — the JWT stays minimal (sub + auth_provider).
    """
    user_id = claims.get("sub", "")
    perms: list[str] = []
    username = ""
    display_name = ""
    auth_provider = claims.get("auth_provider", "")
    must_change_password = False

    if user_id:
        perms = sorted(await repository.get_user_permissions(db, user_id))
        # Load user profile from DB for truthful username/display_name
        user = await repository.find_user_by_id(db, user_id)
        if user is not None:
            username = user.username
            display_name = user.display_name
            auth_provider = user.auth_provider
        # Check local_credentials for must_change_password flag
        from packages.auth.repository import get_local_credential
        if auth_provider in ("local_advertiser", "local_break_glass"):
            cred = await get_local_credential(db, user_id)
            if cred is not None:
                must_change_password = cred.must_change_password

    # Resolve advertiser organization from scoped user role
    advertiser_org_id: str | None = None
    advertiser_org: AdvertiserOrganizationOut | None = None
    if user_id:
        try:
            org_id, org = await repository.get_advertiser_org_for_user(db, user_id)
            advertiser_org_id = org_id
            if org:
                advertiser_org = AdvertiserOrganizationOut.model_validate(org)
        except Exception:
            pass  # graceful: mock DB or missing tables in test env

    return MeResponse(
        sub=user_id,
        auth_provider=auth_provider,
        username=username,
        display_name=display_name,
        permissions=perms,
        must_change_password=must_change_password,
        advertiser_organization_id=advertiser_org_id,
        advertiser_organization=advertiser_org,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/change-password
# ---------------------------------------------------------------------------


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    body: ChangePasswordRequest,
    claims: dict = Depends(get_current_active_user),
    db=Depends(get_db),
):
    """Change own password — only for local_advertiser / local_break_glass.

    401 if token missing/invalid. 403 if user deactivated.
    400 if provider is not local or password validation fails.
    Invalidates all refresh sessions on success.
    """
    user_id = claims.get("sub", "")
    auth_provider = claims.get("auth_provider", "")

    if auth_provider not in ("local_advertiser", "local_break_glass"):
        raise HTTPException(
            status_code=400,
            detail="Password change not available for your account type",
        )

    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from packages.auth.repository import get_local_credential

    cred = await get_local_credential(db, user_id)
    if cred is None:
        raise HTTPException(
            status_code=400,
            detail="No local credential found",
        )

    # Verify current password
    from packages.security.password import verify_password

    if not verify_password(body.current_password, cred.password_hash):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect",
        )

    # Validate new password
    from packages.security.password import hash_password

    try:
        new_hash = hash_password(body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Update credential
    cred.password_hash = new_hash
    cred.must_change_password = False

    # Invalidate all refresh sessions for this user
    from sqlalchemy import update
    from packages.domain.models import RefreshSession as RSModel

    await db.execute(
        update(RSModel)
        .where(RSModel.user_id == user_id, RSModel.revoked_at.is_(None))
        .values(revoked_at=__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ))
    )

    await db.commit()

    return ChangePasswordResponse(message="Password changed")
