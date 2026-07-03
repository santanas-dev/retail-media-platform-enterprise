"""
Retail Media Platform — Auth Internal DTOs.

Phase 3.2c: Success/failure result types for auth operations.
No password/token in repr except returned explicit token fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AuthSuccess:
    """Successful authentication result."""

    user_id: str
    auth_provider: str
    access_token: str
    refresh_token: str
    refresh_session_id: str


@dataclass
class AuthFailure:
    """Failed authentication result — generic public reason, internal detail."""

    public_reason: str
    internal_code: str

    # Optional debug context (never exposed to client)
    debug_context: dict | None = field(default=None, repr=False)


# Union type for service return values
AuthResult = AuthSuccess | AuthFailure


def auth_success(
    user_id: str,
    auth_provider: str,
    access_token: str,
    refresh_token: str,
    refresh_session_id: str,
) -> AuthSuccess:
    """Factory for success result."""
    return AuthSuccess(
        user_id=user_id,
        auth_provider=auth_provider,
        access_token=access_token,
        refresh_token=refresh_token,
        refresh_session_id=refresh_session_id,
    )


def auth_failure(
    public_reason: str = "Invalid credentials",
    internal_code: str = "AUTH_FAILED",
    debug_context: dict | None = None,
) -> AuthFailure:
    """Factory for failure result — generic public message, no user enumeration.

    debug_context is automatically sanitized before storage — passwords,
    tokens, secrets, and authorization headers are masked.
    """
    from packages.security.sanitize import sanitize_auth_details

    return AuthFailure(
        public_reason=public_reason,
        internal_code=internal_code,
        debug_context=sanitize_auth_details(debug_context),
    )
