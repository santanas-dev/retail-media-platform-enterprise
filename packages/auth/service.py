"""
Retail Media Platform — Auth Service Layer.

Phase 3.2c: Business logic for authentication — login, session management,
password reset. Orchestrates repository + security helpers.
No HTTP routes, no middleware.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from packages.auth.ad_provider import ADAuthProvider, StubADAuthProvider
from packages.auth.repository import (
    count_active_sessions,
    count_recent_failed_attempts,
    create_login_attempt,
    create_password_reset_token,
    create_refresh_session,
    find_active_refresh_session,
    find_user_by_email,
    find_user_by_username,
    get_local_credential,
    hash_identifier,
    revoke_oldest_sessions,
    revoke_refresh_session,
)
from packages.auth.schemas import (
    AuthFailure,
    AuthResult,
    AuthSuccess,
    auth_failure,
    auth_success,
)
from packages.security.config import get_security_config
from packages.security.jwt import create_access_token
from packages.security.password import verify_password
from packages.security.sanitize import sanitize_auth_details
from packages.security.tokens import generate_token, hash_token


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Auth Service
# ---------------------------------------------------------------------------


class AuthService:
    """Authentication service — stateless, receives session from caller."""

    def __init__(self, ad_provider: ADAuthProvider | None = None):
        self._ad = ad_provider or StubADAuthProvider()

    # -----------------------------------------------------------------------
    # Login
    # -----------------------------------------------------------------------

    async def login(
        self,
        session: AsyncSession,
        *,
        username_or_email: str,
        password: str,
        ip_address: str | None = None,
        correlation_id: str | None = None,
    ) -> AuthResult:
        """Authenticate a user by username/email + password.

        Determines auth_provider from the user record and dispatches to
        the appropriate backend (AD or local credentials).

        Always records a login attempt. Never reveals whether the user exists.
        """
        identifier_hash = hash_identifier(username_or_email)

        # Rate limiting — check BEFORE user lookup / expensive verification
        cfg = get_security_config()
        recent_failures = await count_recent_failed_attempts(
            session, identifier_hash, cfg.login_rate_limit_window_minutes,
        )
        if recent_failures >= cfg.login_rate_limit_max_attempts:
            await create_login_attempt(
                session,
                username_or_email_hash=identifier_hash,
                auth_provider="unknown",
                success=False,
                failure_reason="rate_limited",
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            return auth_failure(
                internal_code="RATE_LIMITED",
                debug_context={"window_minutes": cfg.login_rate_limit_window_minutes},
            )

        # Normalize lookup: try username first, then email
        user = await find_user_by_username(session, username_or_email)
        if user is None:
            user = await find_user_by_email(session, username_or_email)

        if user is None:
            # Unknown user — record failure and return generic error
            await create_login_attempt(
                session,
                username_or_email_hash=identifier_hash,
                auth_provider="unknown",
                success=False,
                failure_reason="user_not_found",
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            return auth_failure(
                internal_code="AUTH_FAILED",
                debug_context={"reason": "user_not_found"},
            )

        # Dispatch by auth_provider
        provider = user.auth_provider

        if provider == "ad":
            return await self._login_ad(
                session, user, password, identifier_hash,
                ip_address, correlation_id,
            )
        elif provider in ("local_advertiser", "local_break_glass"):
            return await self._login_local(
                session, user, provider, password, identifier_hash,
                ip_address, correlation_id,
            )
        else:
            await create_login_attempt(
                session,
                username_or_email_hash=identifier_hash,
                auth_provider=provider,
                success=False,
                failure_reason="unknown_provider",
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            return auth_failure(
                internal_code="UNKNOWN_PROVIDER",
                debug_context={"provider": provider},
            )

    async def _login_ad(
        self,
        session: AsyncSession,
        user,
        password: str,
        identifier_hash: str,
        ip_address: str | None,
        correlation_id: str | None,
    ) -> AuthResult:
        """AD/LDAPS authentication path."""
        # Check user status
        if user.status != "active":
            await create_login_attempt(
                session,
                username_or_email_hash=identifier_hash,
                auth_provider="ad",
                success=False,
                failure_reason="user_inactive",
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            return auth_failure(internal_code="USER_INACTIVE")

        # Verify against AD
        result = await self._ad.verify_credentials(user.username, password)

        if not result.success:
            await create_login_attempt(
                session,
                username_or_email_hash=identifier_hash,
                auth_provider="ad",
                success=False,
                failure_reason=result.error_code or "ad_auth_failed",
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            return auth_failure(
                internal_code="AUTH_FAILED",
                debug_context={"ad_error": result.error_code},
            )

        # Success
        await create_login_attempt(
            session,
            username_or_email_hash=identifier_hash,
            auth_provider="ad",
            success=True,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )
        return await self._issue_session(
            session, user.id, "ad", ip_address,
        )

    async def _login_local(
        self,
        session: AsyncSession,
        user,
        provider: str,
        password: str,
        identifier_hash: str,
        ip_address: str | None,
        correlation_id: str | None,
    ) -> AuthResult:
        """Local credentials authentication path (advertiser or break-glass)."""
        # Check user status
        if user.status != "active":
            await create_login_attempt(
                session,
                username_or_email_hash=identifier_hash,
                auth_provider=provider,
                success=False,
                failure_reason="user_inactive",
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            return auth_failure(internal_code="USER_INACTIVE")

        # Get local credentials and validate type matches provider
        cred = await get_local_credential(session, user.id)
        if cred is None:
            await create_login_attempt(
                session,
                username_or_email_hash=identifier_hash,
                auth_provider=provider,
                success=False,
                failure_reason="no_credential",
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            return auth_failure(internal_code="AUTH_FAILED")

        if cred.credential_type != provider:
            await create_login_attempt(
                session,
                username_or_email_hash=identifier_hash,
                auth_provider=provider,
                success=False,
                failure_reason="credential_type_mismatch",
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            return auth_failure(internal_code="AUTH_FAILED")

        if cred.status != "active":
            await create_login_attempt(
                session,
                username_or_email_hash=identifier_hash,
                auth_provider=provider,
                success=False,
                failure_reason="credential_inactive",
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            return auth_failure(internal_code="AUTH_FAILED")

        # Verify password
        if not verify_password(password, cred.password_hash):
            await create_login_attempt(
                session,
                username_or_email_hash=identifier_hash,
                auth_provider=provider,
                success=False,
                failure_reason="wrong_password",
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            return auth_failure(internal_code="AUTH_FAILED")

        # Success
        await create_login_attempt(
            session,
            username_or_email_hash=identifier_hash,
            auth_provider=provider,
            success=True,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )
        return await self._issue_session(
            session, user.id, provider, ip_address,
        )

    # -----------------------------------------------------------------------
    # Session management
    # -----------------------------------------------------------------------

    async def _issue_session(
        self,
        session: AsyncSession,
        user_id: str,
        auth_provider: str,
        ip_address: str | None = None,
    ) -> AuthSuccess:
        """Issue access token + refresh token, persist refresh session."""
        cfg = get_security_config()

        # Enforce max sessions: revoke oldest if needed
        await revoke_oldest_sessions(
            session, user_id, keep=cfg.max_sessions_per_user,
        )

        # Generate tokens
        access_token = create_access_token(user_id, auth_provider)
        raw_refresh_token = generate_token()
        token_hash_val = hash_token(raw_refresh_token)
        token_family_id = str(uuid.uuid4())
        expires_at = _now() + timedelta(hours=cfg.refresh_session_ttl_hours)

        # Persist refresh session (hash only, never raw token)
        rs = await create_refresh_session(
            session,
            user_id=user_id,
            token_hash=token_hash_val,
            token_family_id=token_family_id,
            expires_at=expires_at,
            ip_address=ip_address,
        )

        return auth_success(
            user_id=user_id,
            auth_provider=auth_provider,
            access_token=access_token,
            refresh_token=raw_refresh_token,
            refresh_session_id=rs.id,
        )

    # -----------------------------------------------------------------------
    # Session refresh
    # -----------------------------------------------------------------------

    async def refresh_session(
        self,
        session: AsyncSession,
        raw_refresh_token: str,
        ip_address: str | None = None,
    ) -> AuthResult:
        """Rotate a refresh token — issue new access + refresh, invalidate old."""
        token_hash_val = hash_token(raw_refresh_token)
        rs = await find_active_refresh_session(session, token_hash_val)

        if rs is None:
            return auth_failure(
                internal_code="REFRESH_FAILED",
                debug_context={"reason": "token_not_found_or_revoked"},
            )

        # Check rotation replay: if already rotated, revoke family
        if rs.rotated_at is not None:
            await revoke_refresh_session(session, rs.id)
            return auth_failure(
                internal_code="REFRESH_REPLAY",
                debug_context={"reason": "token_already_rotated"},
            )

        # Get user for auth_provider
        from packages.domain.models import User as UserModel
        stmt = __import__("sqlalchemy").select(UserModel).where(
            UserModel.id == rs.user_id
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None or user.status != "active":
            await revoke_refresh_session(session, rs.id)
            return auth_failure(internal_code="USER_INACTIVE")

        # Rotate old token
        from packages.auth.repository import rotate_refresh_session
        await rotate_refresh_session(session, rs.id)

        # Issue new session (same family for detection)
        cfg = get_security_config()
        access_token = create_access_token(rs.user_id, user.auth_provider)
        raw_new_refresh = generate_token()
        new_hash = hash_token(raw_new_refresh)
        expires_at = _now() + timedelta(hours=cfg.refresh_session_ttl_hours)

        new_rs = await create_refresh_session(
            session,
            user_id=rs.user_id,
            token_hash=new_hash,
            token_family_id=rs.token_family_id,
            expires_at=expires_at,
            ip_address=ip_address,
        )

        return auth_success(
            user_id=rs.user_id,
            auth_provider=user.auth_provider,
            access_token=access_token,
            refresh_token=raw_new_refresh,
            refresh_session_id=new_rs.id,
        )

    # -----------------------------------------------------------------------
    # Logout
    # -----------------------------------------------------------------------

    async def logout(
        self,
        session: AsyncSession,
        raw_refresh_token: str,
    ) -> bool:
        """Revoke a refresh session by token."""
        token_hash_val = hash_token(raw_refresh_token)
        rs = await find_active_refresh_session(session, token_hash_val)
        if rs is None:
            return False
        await revoke_refresh_session(session, rs.id)
        return True

    # -----------------------------------------------------------------------
    # Password reset
    # -----------------------------------------------------------------------

    async def request_password_reset(
        self,
        session: AsyncSession,
        email: str,
    ) -> str | None:
        """Request a password reset token for an advertiser user.

        Returns the raw reset token (to send via email) or None if user not found.
        Generic response — caller must not reveal whether user exists.
        """
        user = await find_user_by_email(session, email)
        if user is None:
            return None

        if user.auth_provider not in ("local_advertiser", "local_break_glass"):
            return None

        cfg = get_security_config()
        raw_token = generate_token()
        token_hash_val = hash_token(raw_token)
        expires_at = _now() + timedelta(minutes=15)

        await create_password_reset_token(
            session,
            user_id=user.id,
            token_hash=token_hash_val,
            expires_at=expires_at,
        )

        return raw_token
