"""
Retail Media Platform — Pydantic API Schemas.

Phase 3.0: Read-only identity/RBAC response models.
Phase 3.2d: Auth API request/response DTOs.
No secret/password fields exposed.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


class UserOut(BaseModel):
    """Public user representation — no password/secret fields."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    username: str
    email: str | None = None
    display_name: str
    auth_provider: str
    status: str
    is_break_glass: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    description: str = ""
    is_system: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    description: str = ""
    created_at: datetime | None = None


class AuditEventOut(BaseModel):
    """Operational audit event — details_json returned as-is (no secrets by contract)."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_user_id: str | None = None
    action: str
    target_type: str
    target_id: str | None = None
    correlation_id: str | None = None
    ip_address: str = ""
    details_json: Any | None = None
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

MAX_LIMIT = 100
DEFAULT_LIMIT = 20


class PaginatedUsers(BaseModel):
    items: list[UserOut]
    total: int
    limit: int
    offset: int


class PaginatedAuditEvents(BaseModel):
    items: list[AuditEventOut]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Auth API — Request / Response DTOs (Phase 3.2d)
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """Login request body."""
    username_or_email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=256)
    auth_provider: Literal["ad", "local_advertiser", "local_break_glass"]


class LoginResponse(BaseModel):
    """Login success response — never includes refresh_token in JSON."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: "UserRefOut"


class UserRefOut(BaseModel):
    """Minimal user reference returned in login/me responses."""
    sub: str  # user_id
    auth_provider: str
    username: str = ""
    display_name: str = ""


class RefreshResponse(BaseModel):
    """Token refresh success — access_token only, refresh goes to cookie."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class LogoutResponse(BaseModel):
    """Logout response — idempotent success."""
    message: str = "Logged out"


class MeResponse(BaseModel):
    """Current user claims from JWT."""
    sub: str
    auth_provider: str
    username: str = ""
    display_name: str = ""
