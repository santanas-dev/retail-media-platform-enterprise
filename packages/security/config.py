"""
Retail Media Platform — Auth Security Configuration.

Phase 3.2b: Environment-based settings for auth, no hardcoded production secrets.
"""

import os
from dataclasses import dataclass, field


def _bool_env(name: str, default: bool = False) -> bool:
    val = os.environ.get(name, "").lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    return default


def _is_dev() -> bool:
    """Heuristic: dev environment if common dev indicators are present."""
    env = os.environ.get("ENVIRONMENT", "").lower()
    if env in ("dev", "development", "local"):
        return True
    if env in ("prod", "production", "staging"):
        return False
    return os.environ.get("PYTEST_CURRENT_TEST") is not None


# ---------------------------------------------------------------------------
# SecurityConfig
# ---------------------------------------------------------------------------


@dataclass
class SecurityConfig:
    """Auth security configuration — loaded from environment.

    Sensitive values (JWT_SECRET, etc.) are validated at load time.
    Dev/test mode allows relaxed validation.
    """

    # Environment
    dev_mode: bool = field(default_factory=_is_dev)

    # JWT
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_ttl_minutes: int = 15
    jwt_clock_skew_seconds: int = 30
    jwt_issuer: str = "rmp-control-api"
    jwt_audience: str = ""

    # Refresh sessions
    refresh_session_ttl_hours: int = 8
    refresh_token_bytes: int = 32
    max_sessions_per_user: int = 5

    # Login rate limiting
    login_rate_limit_max_attempts: int = 5
    login_rate_limit_window_minutes: int = 15

    # Password policy (local credentials)
    password_min_length: int = 8
    password_bcrypt_rounds: int = 12

    # Cookie (refresh token)
    refresh_token_cookie_name: str = "refresh_token"
    refresh_token_cookie_secure: bool = True  # overridden to False in dev
    refresh_token_cookie_samesite: str = "strict"
    refresh_token_cookie_path: str = "/api/v1/auth"

    # Audit
    audit_correlation_id_header: str = "X-Correlation-ID"

    def __post_init__(self) -> None:
        # Load JWT_SECRET from env if not provided
        if not self.jwt_secret:
            self.jwt_secret = os.environ.get("JWT_SECRET", "")
        # Load JWT_AUDIENCE from env if not provided
        if not self.jwt_audience:
            self.jwt_audience = os.environ.get("JWT_AUDIENCE", "")
        self._validate()

    def _validate(self) -> None:
        if self.dev_mode:
            self._validate_dev()
        else:
            self._validate_production()

    def _validate_dev(self) -> None:
        """Dev mode: allow default weak secret but warn."""
        if not self.jwt_secret or self.jwt_secret == "CHANGE_ME":
            self.jwt_secret = "dev-secret-do-not-use-in-production"
        if len(self.jwt_secret) < 16:
            self.jwt_secret = "dev-secret-do-not-use-in-production"
        if not self.jwt_audience:
            self.jwt_audience = self.jwt_issuer  # default: issuer = audience
        # In dev mode, allow non-HTTPS cookies
        if self.dev_mode:
            self.refresh_token_cookie_secure = False

    def _validate_production(self) -> None:
        """Production mode: require strong JWT secret."""
        if not self.jwt_secret or self.jwt_secret == "CHANGE_ME":
            raise ValueError(
                "JWT_SECRET must be set to a strong random value in production"
            )
        if len(self.jwt_secret) < 32:
            raise ValueError(
                f"JWT_SECRET must be at least 32 characters in production "
                f"(got {len(self.jwt_secret)})"
            )
        weak = {"secret", "changeme", "password", "test", "jwt_secret"}
        if self.jwt_secret.lower().strip() in weak:
            raise ValueError(
                "JWT_SECRET must not be a common weak value in production"
            )

    def __repr__(self) -> str:
        """Safe repr — never expose secret values."""
        return (
            f"SecurityConfig(dev_mode={self.dev_mode}, "
            f"jwt_secret='***', "
            f"jwt_algorithm={self.jwt_algorithm}, "
            f"jwt_access_token_ttl_minutes={self.jwt_access_token_ttl_minutes}, "
            f"refresh_session_ttl_hours={self.refresh_session_ttl_hours})"
        )


# Singleton — loaded once at import time
_config: SecurityConfig | None = None


def get_security_config() -> SecurityConfig:
    """Return the singleton SecurityConfig, creating it on first call."""
    global _config
    if _config is None:
        _config = SecurityConfig()
    return _config


def reset_security_config() -> None:
    """Reset singleton — useful for tests that modify env."""
    global _config
    _config = None
