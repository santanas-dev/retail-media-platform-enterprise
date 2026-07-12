"""
Retail Media Platform — Auth Repository Layer.

Phase 3.2c: Async DB operations for auth persistence tables.
All token storage uses token_hash only — never raw tokens.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from packages.domain.models import (
    LocalCredential,
    LoginAttempt,
    PasswordResetToken,
    RefreshSession,
    User,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# User lookup
# ---------------------------------------------------------------------------


async def find_user_by_username(
    session: AsyncSession, username: str
) -> User | None:
    """Find user by exact username match (case-sensitive)."""
    stmt = select(User).where(User.username == username)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def find_user_by_email(
    session: AsyncSession, email: str
) -> User | None:
    """Find user by exact email (case-insensitive)."""
    if not email:
        return None
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Local credentials
# ---------------------------------------------------------------------------


async def get_local_credential(
    session: AsyncSession, user_id: str
) -> LocalCredential | None:
    """Get local_credentials row for a user."""
    stmt = select(LocalCredential).where(LocalCredential.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Login attempts
# ---------------------------------------------------------------------------


async def create_login_attempt(
    session: AsyncSession,
    *,
    username_or_email_hash: str,
    auth_provider: str,
    success: bool,
    failure_reason: str | None = None,
    ip_address: str | None = None,
    correlation_id: str | None = None,
) -> LoginAttempt:
    """Record a login attempt (success or failure).

    Only stores hashed identifier — never raw email/username.
    """
    attempt = LoginAttempt(
        id=_new_id(),
        username_or_email_hash=username_or_email_hash,
        auth_provider=auth_provider,
        success=success,
        failure_reason=failure_reason,
        ip_address=ip_address,
        correlation_id=correlation_id,
    )
    session.add(attempt)
    await session.flush()
    return attempt


def hash_identifier(value: str) -> str:
    """Hash a username/email for login_attempts storage.

    SHA-256 — consistent with token hashing.
    """
    return hashlib.sha256(value.lower().encode("utf-8")).hexdigest()


async def count_recent_failed_attempts(
    session: AsyncSession,
    identifier_hash: str,
    window_minutes: int,
) -> int:
    """Count failed login attempts for a hashed identifier within the window.

    Used for rate limiting — doesn't leak user existence.
    """
    from datetime import timedelta

    cutoff = _now() - timedelta(minutes=window_minutes)
    stmt = (
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            LoginAttempt.username_or_email_hash == identifier_hash,
            LoginAttempt.success == False,  # noqa: E712
            LoginAttempt.created_at > cutoff,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Refresh sessions
# ---------------------------------------------------------------------------


async def create_refresh_session(
    session: AsyncSession,
    *,
    user_id: str,
    token_hash: str,
    token_family_id: str,
    expires_at: datetime,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> RefreshSession:
    """Create a refresh session record (stores token_hash only)."""
    rs = RefreshSession(
        id=_new_id(),
        user_id=user_id,
        token_hash=token_hash,
        token_family_id=token_family_id,
        issued_at=_now(),
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(rs)
    await session.flush()
    return rs


async def find_active_refresh_session(
    session: AsyncSession, token_hash: str
) -> RefreshSession | None:
    """Find an active (not revoked, not rotated, not expired) refresh session
    by token_hash."""
    now = _now()
    stmt = (
        select(RefreshSession)
        .where(
            RefreshSession.token_hash == token_hash,
            RefreshSession.expires_at > now,
            RefreshSession.revoked_at.is_(None),
            RefreshSession.rotated_at.is_(None),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def revoke_refresh_session(
    session: AsyncSession, refresh_session_id: str
) -> None:
    """Mark a refresh session as revoked."""
    stmt = (
        update(RefreshSession)
        .where(RefreshSession.id == refresh_session_id)
        .values(revoked_at=_now())
    )
    await session.execute(stmt)


async def rotate_refresh_session(
    session: AsyncSession, refresh_session_id: str
) -> None:
    """Mark a refresh session as rotated (used once, new token issued)."""
    stmt = (
        update(RefreshSession)
        .where(RefreshSession.id == refresh_session_id)
        .values(rotated_at=_now())
    )
    await session.execute(stmt)


async def count_active_sessions(
    session: AsyncSession, user_id: str
) -> int:
    """Count active (non-revoked) refresh sessions for a user."""
    now = _now()
    stmt = select(RefreshSession).where(
        RefreshSession.user_id == user_id,
        RefreshSession.revoked_at.is_(None),
        RefreshSession.expires_at > now,
    )
    result = await session.execute(stmt)
    return len(result.scalars().all())


async def revoke_oldest_sessions(
    session: AsyncSession, user_id: str, keep: int
) -> int:
    """Revoke oldest active sessions, keeping only `keep` most recent.

    Returns number of sessions revoked.
    """
    now = _now()
    # Find active sessions, ordered oldest first
    stmt = (
        select(RefreshSession)
        .where(
            RefreshSession.user_id == user_id,
            RefreshSession.revoked_at.is_(None),
            RefreshSession.expires_at > now,
        )
        .order_by(RefreshSession.issued_at.asc())
    )
    result = await session.execute(stmt)
    active = list(result.scalars().all())

    if len(active) <= keep:
        return 0

    to_revoke = active[: len(active) - keep]
    for rs in to_revoke:
        rs.revoked_at = _now()
    await session.flush()
    return len(to_revoke)


# ---------------------------------------------------------------------------
# Password reset tokens
# ---------------------------------------------------------------------------


async def create_password_reset_token(
    session: AsyncSession,
    *,
    user_id: str,
    token_hash: str,
    expires_at: datetime,
) -> PasswordResetToken:
    """Create a password reset token (stores token_hash only)."""
    prt = PasswordResetToken(
        id=_new_id(),
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(prt)
    await session.flush()
    return prt


async def mark_reset_token_used(
    session: AsyncSession, token_hash: str
) -> bool:
    """Mark a password reset token as used.

    Returns True if a row was updated, False if token not found or already used.
    """
    now = _now()
    stmt = (
        update(PasswordResetToken)
        .where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .values(used_at=now)
    )
    result = await session.execute(stmt)
    return result.rowcount > 0


# ---------------------------------------------------------------------------
# S-033 — Session management for admin user operations
# ---------------------------------------------------------------------------


async def revoke_all_sessions_for_user(
    session: AsyncSession, user_id: str
) -> int:
    """Revoke all active refresh sessions for a user. Returns count revoked."""
    now = _now()
    result = await session.execute(
        update(RefreshSession)
        .where(
            RefreshSession.user_id == user_id,
            RefreshSession.revoked_at.is_(None),
            RefreshSession.expires_at > now,
        )
        .values(revoked_at=now)
    )
    return result.rowcount
